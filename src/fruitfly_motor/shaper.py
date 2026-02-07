"""Shaping: spikes to something a motor driver will accept.

Order matters and is fixed: clamp, dead zone, slew limit, smoothing, invert.
Inverting last means the inversion never interacts with the dead zone — a trim
that flips a wheel should not also move the threshold at which it starts
turning.
"""

from __future__ import annotations

from dataclasses import dataclass

from .protocol import MAX_COMMAND, Command


@dataclass
class ShaperConfig:
    max_command: float = 60.0
    dead_zone: float = 4.0
    slew_per_s: float = 300.0
    smoothing: float = 0.0
    invert_left: bool = False
    invert_right: bool = False
    escape_command: float = 0.9

    def validate(self) -> "ShaperConfig":
        if not 1.0 <= self.max_command <= MAX_COMMAND:
            raise ValueError("max_command must be in 1..%d" % int(MAX_COMMAND))
        if self.dead_zone < 0 or self.dead_zone >= self.max_command:
            raise ValueError("dead_zone must be 0 <= dead_zone < max_command")
        if self.slew_per_s < 0:
            raise ValueError("slew_per_s must be >= 0")
        if not 0.0 <= self.smoothing < 1.0:
            raise ValueError("smoothing must be in [0, 1)")
        if not 0.0 < self.escape_command <= 1.0:
            raise ValueError("escape_command must be in (0, 1]")
        return self


class CommandShaper:
    """Turns drives in 0..1 into signed commands, with limits.

    ``update`` is called once per frame; ``read`` returns the current command
    and zeroes it if the caller went quiet for longer than ``timeout_ms``. The
    timeout lives here rather than in the transport so that a socket that is
    fine but idle still results in a stop.
    """

    def __init__(self, cfg: ShaperConfig | None = None, timeout_ms: float = 500.0):
        self.cfg = (cfg or ShaperConfig()).validate()
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        self.timeout_ms = timeout_ms
        self.reset()

    def reset(self) -> None:
        self.target = (0.0, 0.0)
        self.current = (0.0, 0.0)
        self.last_update_ms: float | None = None
        self._estop = False
        self.sequence = 0
        self.slew_limited = 0

    @property
    def stopped(self) -> bool:
        return self._estop

    def emergency_stop(self) -> None:
        self._estop = True
        self.target = (0.0, 0.0)
        self.current = (0.0, 0.0)

    def clear_emergency(self) -> None:
        self._estop = False

    def _shape(self, left: float, right: float) -> tuple[float, float]:
        cfg = self.cfg
        out = []
        for value, invert in ((left, cfg.invert_left), (right, cfg.invert_right)):
            scaled = max(0.0, min(1.0, float(value))) * cfg.max_command
            if scaled < cfg.dead_zone:
                scaled = 0.0
            out.append(-scaled if invert else scaled)
        return out[0], out[1]

    def update(self, left: float, right: float, escape: bool, now_ms: float, dt_ms: float = 33.0) -> Command:
        if escape:
            target = self._shape(self.cfg.escape_command, self.cfg.escape_command)
            reason = "escape"
        else:
            target = self._shape(left, right)
            reason = "track"

        previous = self.current
        dt_s = max(dt_ms, 1.0) / 1000.0
        step = self.cfg.slew_per_s * dt_s
        shaped = []
        for want, was in zip(target, previous):
            if self.cfg.slew_per_s and abs(want - was) > step:
                self.slew_limited += 1
                shaped.append(was + step * (1.0 if want > was else -1.0))
            else:
                shaped.append(want)
        alpha = 1.0 - self.cfg.smoothing
        smoothed = tuple(was + alpha * (want - was) for want, was in zip(shaped, previous))

        self.target = target
        self.current = smoothed
        self.last_update_ms = now_ms
        self.sequence += 1
        return Command(self.current[0], self.current[1], self.sequence, False, reason)

    def read(self, now_ms: float) -> Command:
        if self._estop:
            return Command(0.0, 0.0, self.sequence, True, "emergency-stop")
        if self.last_update_ms is None or (now_ms - self.last_update_ms) > self.timeout_ms:
            self.current = (0.0, 0.0)
            return Command(0.0, 0.0, self.sequence, True, "shaper-timeout")
        return Command(self.current[0], self.current[1], self.sequence, False, "track")

    def zero_now(self, now_ms: float) -> None:
        """Force the shaped state to zero without latching the e-stop."""
        self.target = (0.0, 0.0)
        self.current = (0.0, 0.0)
        self.last_update_ms = now_ms
