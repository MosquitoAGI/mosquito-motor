"""Replay recorded sessions.

A session is JSONL, one object per line: a timestamp and two drives in 0..1 —
the numbers the bridge's decoder would hand to the motor side. ``load_session``
validates every line; a session with a bad line is rejected whole, because a
replay that silently skips steps is a replay of a different run.

A replay goes through a real :class:`CommandShaper`, so the commands it emits
are shaped exactly like the live ones. Timing can be preserved or ignored.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .protocol import Command
from .shaper import CommandShaper, ShaperConfig


class SessionError(ValueError):
    """Raised when a session file does not match the replay format."""


@dataclass
class Sample:
    t_ms: float
    left: float
    right: float
    escape: bool = False


def _number(value, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SessionError("%s must be a number" % what)
    return float(value)


def parse_session(text: str) -> list[Sample]:
    samples: list[Sample] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            body = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SessionError("line %d: invalid JSON: %s" % (number, exc)) from exc
        if not isinstance(body, dict):
            raise SessionError("line %d: must be a JSON object" % number)
        for key in ("t_ms", "left", "right"):
            if key not in body:
                raise SessionError("line %d: missing %r" % (number, key))
        sample = Sample(
            t_ms=_number(body["t_ms"], "t_ms"),
            left=_number(body["left"], "left"),
            right=_number(body["right"], "right"),
            escape=bool(body.get("escape", False)),
        )
        if sample.t_ms < 0:
            raise SessionError("line %d: t_ms must be >= 0" % number)
        if samples and sample.t_ms < samples[-1].t_ms:
            raise SessionError("line %d: t_ms went backwards" % number)
        samples.append(sample)
    if not samples:
        raise SessionError("session is empty")
    return samples


def load_session(path: str | Path) -> list[Sample]:
    return parse_session(Path(path).read_text(encoding="utf-8"))


def dump_session(samples, path: str | Path) -> int:
    """Write ``(t_ms, left, right[, escape])`` tuples or Samples to JSONL."""
    lines = []
    for item in samples:
        if isinstance(item, Sample):
            t_ms, left, right, escape = item.t_ms, item.left, item.right, item.escape
        else:
            t_ms, left, right = item[0], item[1], item[2]
            escape = item[3] if len(item) > 3 else False
        lines.append(json.dumps(
            {"t_ms": round(float(t_ms), 1), "left": round(float(left), 4),
             "right": round(float(right), 4), "escape": bool(escape)},
            separators=(",", ":")))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


class Replayer:
    """Feeds recorded drives through a shaper, optionally in real time."""

    def __init__(self, samples: list[Sample], shaper: CommandShaper | None = None):
        if not samples:
            raise SessionError("nothing to replay")
        self.samples = samples
        self.shaper = shaper if shaper is not None else CommandShaper(ShaperConfig())

    def stream(self, realtime: bool = False, sleep=time.sleep):
        """Yield ``(t_ms, Command)``; sleeps between samples when realtime."""
        previous_ms = None
        for sample in self.samples:
            if realtime and previous_ms is not None:
                gap = max(0.0, (sample.t_ms - previous_ms) / 1000.0)
                if gap:
                    sleep(gap)
            dt_ms = 33.0
            if previous_ms is not None:
                dt_ms = max(1.0, sample.t_ms - previous_ms)
            command = self.shaper.update(sample.left, sample.right, sample.escape,
                                         sample.t_ms, dt_ms)
            previous_ms = sample.t_ms
            yield sample.t_ms, command

    def run(self, realtime: bool = False, sleep=time.sleep) -> list[tuple[float, Command]]:
        return list(self.stream(realtime=realtime, sleep=sleep))

    def summary(self, commands: list[tuple[float, Command]]) -> str:
        if not commands:
            return "no commands"
        peak = max(max(abs(c.left), abs(c.right)) for _t, c in commands)
        duration = (commands[-1][0] - commands[0][0]) / 1000.0
        escapes = sum(1 for _t, c in commands if c.reason == "escape")
        return ("%d samples, %.1f s, peak |command| %.1f, %d escape frames"
                % (len(commands), duration, peak, escapes))


__all__ = ["Replayer", "Sample", "SessionError", "dump_session", "load_session", "parse_session"]
