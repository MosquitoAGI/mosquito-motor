"""Silence detection.

The watchdog answers one question: has telemetry arrived recently enough that we
believe the other end is alive? It never sends anything itself — it reports, and
the caller decides to stop. That keeps it testable with no sockets and no clock.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WatchdogConfig:
    timeout_ms: float = 600.0
    grace_ms: float = 0.0

    def validate(self) -> "WatchdogConfig":
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        if self.grace_ms < 0:
            raise ValueError("grace_ms must be >= 0")
        return self


class Watchdog:
    """Feeds on telemetry and expires on silence.

    ``reason`` distinguishes two failure modes that look the same on the wire
    and are not the same problem: ``never-fed`` means nothing has ever arrived
    (a wiring or address mistake), ``starved`` means it used to arrive and
    stopped (a control problem, a dead process, a yanked cable).
    """

    def __init__(self, cfg: WatchdogConfig | None = None):
        self.cfg = (cfg or WatchdogConfig()).validate()
        self.reset()

    def reset(self) -> None:
        self.last_feed_ms: float | None = None
        self.feeds = 0
        self.expirations = 0
        self._expired = False

    def feed(self, now_ms: float) -> None:
        self.last_feed_ms = now_ms
        self.feeds += 1
        self._expired = False

    def age_ms(self, now_ms: float) -> float | None:
        if self.last_feed_ms is None:
            return None
        return max(0.0, now_ms - self.last_feed_ms)

    def expired(self, now_ms: float) -> bool:
        age = self.age_ms(now_ms)
        if age is None:
            return True
        return age > (self.cfg.timeout_ms + self.cfg.grace_ms)

    def reason(self, now_ms: float) -> str:
        if not self.expired(now_ms):
            return "ok"
        return "never-fed" if self.last_feed_ms is None else "starved"

    def poll(self, now_ms: float) -> str:
        """Update the counters and return the current state."""
        if self.expired(now_ms):
            if not self._expired:
                self._expired = True
                self.expirations += 1
            return self.reason(now_ms)
        self._expired = False
        return "ok"
