"""A plant model small enough to read in one sitting.

First-order wheel lag, differential-drive yaw with a low-pass on the rate, a
battery that drains while the wheels turn, and seeded noise so a run is
reproducible. It is not a physics engine. It exists so ``fruitfly-motor sim``
produces numbers, so a replay has something to answer, and so the stop rules
can be watched without a robot on the bench.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .protocol import Command, Telemetry
from .shaper import CommandShaper, ShaperConfig
from .watchdog import Watchdog, WatchdogConfig


@dataclass
class RobotConfig:
    wheel_tau_ms: float = 120.0
    wheel_base: float = 90.0
    max_speed: float = 60.0
    battery_hours: float = 1.5
    yaw_damping: float = 0.3
    noise: float = 0.25
    seed: int = 11

    def validate(self) -> "RobotConfig":
        if self.wheel_tau_ms <= 0:
            raise ValueError("wheel_tau_ms must be positive")
        if self.wheel_base <= 0:
            raise ValueError("wheel_base must be positive")
        if self.max_speed <= 0:
            raise ValueError("max_speed must be positive")
        if self.battery_hours <= 0:
            raise ValueError("battery_hours must be positive")
        if not 0.0 <= self.yaw_damping < 1.0:
            raise ValueError("yaw_damping must be in [0, 1)")
        if self.noise < 0:
            raise ValueError("noise must be >= 0")
        return self


class RobotSim:
    """Steps a robot forward by ``dt_ms`` and answers with telemetry."""

    def __init__(self, cfg: RobotConfig | None = None):
        self.cfg = (cfg or RobotConfig()).validate()
        self.rng = random.Random(self.cfg.seed)
        self.reset()

    def reset(self) -> None:
        self.t_ms = 0.0
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.yaw_rate = 0.0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.battery = 1.0
        self.sequence = 0

    @property
    def pose(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.yaw)

    def _clip(self, value: float) -> float:
        limit = self.cfg.max_speed
        return float(max(-limit, min(limit, value)))

    def step(self, command: Command, dt_ms: float = 33.0) -> Telemetry:
        dt_s = max(float(dt_ms), 0.0) / 1000.0
        left_target = 0.0 if command.emergency_stop else self._clip(command.left)
        right_target = 0.0 if command.emergency_stop else self._clip(command.right)
        alpha = 1.0 - math.exp(-float(dt_ms) / self.cfg.wheel_tau_ms)
        self.left_speed += (left_target - self.left_speed) * alpha
        self.right_speed += (right_target - self.right_speed) * alpha

        mean_speed = 0.5 * (self.left_speed + self.right_speed)
        raw_rate = (self.right_speed - self.left_speed) / self.cfg.wheel_base
        damp = self.cfg.yaw_damping
        self.yaw_rate = raw_rate * (1.0 - damp) + self.yaw_rate * damp
        self.yaw += self.yaw_rate * dt_s
        self.x += mean_speed * math.cos(self.yaw) * dt_s
        self.y += mean_speed * math.sin(self.yaw) * dt_s

        load = 0.5 * (abs(self.left_speed) + abs(self.right_speed)) / self.cfg.max_speed
        self.battery = max(0.0, self.battery - load * dt_s / (self.cfg.battery_hours * 3600.0))

        self.t_ms += dt_ms
        self.sequence += 1
        noise = self.cfg.noise
        return Telemetry(
            sequence=self.sequence,
            left_speed=self.left_speed + self.rng.gauss(0.0, noise),
            right_speed=self.right_speed + self.rng.gauss(0.0, noise),
            gyro=(0.0, 0.0, self.yaw_rate),
            accel=(0.0, 0.0, 0.0),
            battery=self.battery,
        )


# --------------------------------------------------------------------- profiles

def profile_approach(t: float) -> tuple[float, float, bool]:
    """Walk forward, reaching full drive after 1.5 s."""
    v = min(1.0, t / 1.5)
    return (v, v, False)


def profile_square(t: float) -> tuple[float, float, bool]:
    """Strait runs interrupted by wider turns — the classic bench square."""
    if (t % 4.0) < 2.0:
        return (0.8, 0.8, False)
    return (0.55, 0.9, False)


def profile_idle(t: float) -> tuple[float, float, bool]:
    return (0.0, 0.0, False)


PROFILES = {
    "approach": profile_approach,
    "square": profile_square,
    "idle": profile_idle,
}


# ---------------------------------------------------------------- full session

@dataclass
class Frame:
    t_ms: float
    left_in: float
    right_in: float
    escape: bool
    cmd_left: float
    cmd_right: float
    speed_left: float
    speed_right: float
    yaw: float
    battery: float
    telemetry: bool


@dataclass
class SessionResult:
    frames: list = field(default_factory=list)
    stops: int = 0
    stop_reason: str = "ok"
    stop_at_s: float | None = None
    max_command: float = 0.0
    pose: tuple[float, float, float] = (0.0, 0.0, 0.0)
    battery: float = 1.0
    duration_s: float = 0.0

    def drives(self) -> list:
        """The recorded inputs, in the replay session format."""
        return [(f.t_ms, f.left_in, f.right_in, f.escape) for f in self.frames]


def run_session(profile: str = "approach", seconds: float = 10.0, fps: float = 30.0,
                robot_cfg: RobotConfig | None = None,
                shaper_cfg: ShaperConfig | None = None,
                silence_after_s: float | None = None) -> SessionResult:
    """Drive the whole stack: profile → shaper → robot → telemetry → watchdog.

    ``silence_after_s`` cuts the telemetry link at that moment; the watchdog
    and the shaper's own timeout must both bring the commands to zero. The
    result reports which one noticed first.
    """
    if profile not in PROFILES:
        raise ValueError("unknown profile %r (have: %s)" % (profile, ", ".join(sorted(PROFILES))))
    fn = PROFILES[profile]
    robot = RobotSim(robot_cfg)
    shaper = CommandShaper(shaper_cfg, timeout_ms=500.0)
    watchdog = Watchdog(WatchdogConfig(timeout_ms=600.0))
    dt_ms = 1000.0 / fps
    result = SessionResult()
    command = Command(0.0, 0.0, 0, False, "init")
    prev_state = "ok"

    for i in range(max(1, int(round(seconds * fps)))):
        t_ms = i * dt_ms
        t_s = t_ms / 1000.0
        left_in, right_in, escape = fn(t_s)

        linked = silence_after_s is None or t_s < silence_after_s
        telemetry = robot.step(command, dt_ms)
        if linked:
            watchdog.feed(t_ms)
            state = watchdog.poll(t_ms)
            command = shaper.update(left_in, right_in, escape, t_ms, dt_ms)
        else:
            state = watchdog.poll(t_ms)
            command = shaper.read(t_ms)

        if state != "ok" and prev_state == "ok":
            result.stops += 1
            result.stop_reason = state
            result.stop_at_s = t_s
        prev_state = state

        result.max_command = max(result.max_command, abs(command.left), abs(command.right))
        result.frames.append(
            Frame(t_ms, left_in, right_in, escape, command.left, command.right,
                  telemetry.left_speed, telemetry.right_speed, robot.yaw,
                  robot.battery, linked)
        )

    result.pose = robot.pose
    result.battery = robot.battery
    result.duration_s = seconds
    return result


__all__ = ["PROFILES", "Frame", "RobotConfig", "RobotSim", "SessionResult", "run_session"]
