"""UDP transport: one socket, two directions, one set of counters.

The motor side owns the socket. Commands leave through it, telemetry arrives on
it, and everything that is dropped is counted — a bench summary that says
"1,842 commands, 3 malformed, 11 duplicates" is worth more than one that says
"it worked".

Nothing here blocks forever. ``recv_telemetry`` returns ``None`` when there is
nothing to read, so the caller stays in control of its own loop.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

from .protocol import MAX_PACKET, Command, MotorError, SequenceGate, Telemetry


@dataclass
class LinkStats:
    commands_sent: int = 0
    commands_received: int = 0
    telemetry_sent: int = 0
    telemetry_received: int = 0
    malformed: int = 0
    dropped: int = 0
    last_error: str | None = None

    def summary(self) -> str:
        text = ("%d commands out, %d in; %d telemetry out, %d in; "
                "%d malformed, %d dropped"
                % (self.commands_sent, self.commands_received,
                   self.telemetry_sent, self.telemetry_received,
                   self.malformed, self.dropped))
        if self.last_error:
            text += " (last error: %s)" % self.last_error
        return text


class Link:
    """A datagram link to one robot, or to another process on the bench."""

    def __init__(self, bind: tuple[str, int] = ("127.0.0.1", 0),
                 target: tuple[str, int] | None = None, timeout: float = 0.05):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(bind)
        self.sock.settimeout(timeout)
        self.target = target if target is not None else ("127.0.0.1", self.port)
        self.stats = LinkStats()
        self.gate = SequenceGate()

    @property
    def port(self) -> int:
        return int(self.sock.getsockname()[1])

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.sock.getsockname()[:2]
        return str(host), int(port)

    def _recv(self) -> bytes | None:
        try:
            data, _peer = self.sock.recvfrom(MAX_PACKET + 1)
        except (BlockingIOError, TimeoutError):
            return None
        except OSError as exc:
            self.stats.last_error = str(exc)
            return None
        if len(data) > MAX_PACKET:
            self.stats.malformed += 1
            return None
        return data

    def send_command(self, command: Command) -> int:
        """Send one shaped command; returns the number of bytes on the wire."""
        data = command.payload().encode("utf-8")
        sent = self.sock.sendto(data, self.target)
        self.stats.commands_sent += 1
        return sent

    def send_telemetry(self, telemetry: Telemetry) -> int:
        """Used by simulators and test doubles, not by a real bridge."""
        data = telemetry.payload().encode("utf-8")
        sent = self.sock.sendto(data, self.target)
        self.stats.telemetry_sent += 1
        return sent

    def recv_command(self) -> Command | None:
        """One command packet, or ``None`` if the link is quiet."""
        data = self._recv()
        if data is None:
            return None
        try:
            command = Command.from_payload(data)
        except MotorError:
            self.stats.malformed += 1
            return None
        self.stats.commands_received += 1
        return command

    def recv_telemetry(self) -> Telemetry | None:
        """One telemetry packet, or ``None`` if the link is quiet."""
        data = self._recv()
        if data is None:
            return None
        try:
            telemetry = Telemetry.from_payload(data)
        except MotorError:
            self.stats.malformed += 1
            return None
        if not self.gate.accept(telemetry.sequence):
            self.stats.dropped += 1
            return None
        self.stats.telemetry_received += 1
        return telemetry

    def close(self) -> None:
        self.sock.close()

    def __enter__(self) -> "Link":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


__all__ = ["Link", "LinkStats"]
