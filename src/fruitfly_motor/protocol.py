"""The wire format, as this side sees it.

Two datagram types, both UTF-8 JSON objects, both under 512 bytes:

    {"type":"motor_command","sequence":42,"left":18.5,"right":-4.0,
     "emergency_stop":false,"reason":"track"}

    {"type":"telemetry","sequence":17,"left_speed":18.2,"right_speed":-3.8,
     "gyro":[0,0,0.21],"accel":[0,0,0],"battery":0.93}

Validation is strict in both directions. A malformed packet is counted and
dropped; it is never partially applied, because half a motor command is a
direction nobody asked for.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

MAX_COMMAND = 100.0
MAX_PACKET = 512
MAX_SEQUENCE = 2**31 - 1
VECTOR_KEYS = ("gyro", "accel")


class MotorError(ValueError):
    """Raised for anything that does not match the wire format."""


def _finite(value, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MotorError("%s must be a number" % what)
    number = float(value)
    if not math.isfinite(number):
        raise MotorError("%s must be finite" % what)
    return number


def _clamp(value: float) -> float:
    return float(max(-MAX_COMMAND, min(MAX_COMMAND, value)))


def _load(text: bytes | str) -> dict:
    data = text.decode("utf-8") if isinstance(text, bytes) else text
    if len(data.encode("utf-8")) > MAX_PACKET:
        raise MotorError("packet exceeds %d bytes" % MAX_PACKET)
    try:
        body = json.loads(data)
    except json.JSONDecodeError as exc:
        raise MotorError("invalid JSON: %s" % exc) from exc
    if not isinstance(body, dict):
        raise MotorError("packet must be a JSON object")
    return body


@dataclass
class Command:
    """One motor command, already shaped."""

    left: float = 0.0
    right: float = 0.0
    sequence: int = 0
    emergency_stop: bool = False
    reason: str = "track"

    def clamped(self) -> "Command":
        return Command(_clamp(self.left), _clamp(self.right), self.sequence,
                       self.emergency_stop, self.reason)

    def payload(self) -> str:
        return json.dumps(
            {
                "type": "motor_command",
                "sequence": int(self.sequence),
                "left": round(float(self.left), 3),
                "right": round(float(self.right), 3),
                "emergency_stop": bool(self.emergency_stop),
                "reason": self.reason,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_payload(cls, data: bytes | str) -> "Command":
        body = _load(data)
        if body.get("type") != "motor_command":
            raise MotorError("not a motor_command packet")
        for key in ("left", "right"):
            if key not in body:
                raise MotorError("motor_command is missing %r" % key)
        sequence = body.get("sequence", 0)
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise MotorError("sequence must be a non-negative integer")
        return cls(
            left=_finite(body["left"], "left"),
            right=_finite(body["right"], "right"),
            sequence=sequence,
            emergency_stop=bool(body.get("emergency_stop", False)),
            reason=str(body.get("reason", "track")),
        ).clamped()


@dataclass
class Telemetry:
    sequence: int = 0
    left_speed: float = 0.0
    right_speed: float = 0.0
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0)
    accel: tuple[float, float, float] = (0.0, 0.0, 0.0)
    battery: float = 1.0
    age_ms: float = 0.0  # filled in by the watchdog, not carried on the wire

    def to_dict(self) -> dict:
        return {
            "type": "telemetry",
            "sequence": int(self.sequence),
            "left_speed": round(float(self.left_speed), 3),
            "right_speed": round(float(self.right_speed), 3),
            "gyro": [round(float(v), 4) for v in self.gyro],
            "accel": [round(float(v), 4) for v in self.accel],
            "battery": round(float(self.battery), 4),
        }

    def payload(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_payload(cls, data: bytes | str) -> "Telemetry":
        body = _load(data)
        if body.get("type") != "telemetry":
            raise MotorError("not a telemetry packet")
        sequence = body.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise MotorError("sequence must be an integer")
        if not 0 <= sequence <= MAX_SEQUENCE:
            raise MotorError("sequence out of range")
        vectors = {}
        for key in VECTOR_KEYS:
            values = body.get(key, [0.0, 0.0, 0.0])
            if not isinstance(values, (list, tuple)) or len(values) != 3:
                raise MotorError("%s must be three numbers" % key)
            vectors[key] = tuple(_finite(v, key) for v in values)
        return cls(
            sequence=sequence,
            left_speed=_finite(body.get("left_speed", 0.0), "left_speed"),
            right_speed=_finite(body.get("right_speed", 0.0), "right_speed"),
            gyro=vectors["gyro"],
            accel=vectors["accel"],
            battery=_finite(body.get("battery", 1.0), "battery"),
        )


class SequenceGate:
    """Accepts each telemetry sequence number once, in order.

    Telemetry is best-effort: duplicates and reorderings are dropped with a
    counter, not an exception, because the link is UDP and a control loop that
    dies on a reordering is worse than one that skips a sample.
    """

    def __init__(self) -> None:
        self.last: int | None = None
        self.accepted = 0
        self.rejected = 0

    def accept(self, sequence: int) -> bool:
        if self.last is not None and sequence <= self.last:
            self.rejected += 1
            return False
        self.last = sequence
        self.accepted += 1
        return True


def make_command(left: float, right: float, **kw) -> Command:
    return Command(left=left, right=right, **kw).clamped()


def encode_payload(obj) -> str:
    """Anything with ``payload()`` becomes wire text."""
    if hasattr(obj, "payload"):
        return obj.payload()
    raise MotorError("cannot encode %r" % type(obj).__name__)


__all__ = [
    "MAX_COMMAND",
    "MAX_PACKET",
    "Command",
    "MotorError",
    "SequenceGate",
    "Telemetry",
    "encode_payload",
    "make_command",
]
