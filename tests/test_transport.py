import pytest

from fruitfly_motor.protocol import Telemetry, make_command
from fruitfly_motor.transport import Link


@pytest.fixture
def pair():
    left = Link(timeout=0.1)
    right = Link(timeout=0.1)
    left.target = right.address
    right.target = left.address
    yield left, right
    left.close()
    right.close()


def test_command_round_trip(pair):
    left, right = pair
    sent = left.send_command(make_command(10.0, -5.0, sequence=1))
    assert sent > 0
    command = right.recv_command()
    assert command is not None
    assert command.left == 10.0 and command.right == -5.0
    assert left.stats.commands_sent == 1
    assert right.stats.commands_received == 1


def test_telemetry_round_trip_and_gate(pair):
    left, right = pair
    right.send_telemetry(Telemetry(sequence=1, left_speed=3.0))
    first = left.recv_telemetry()
    assert first is not None and first.sequence == 1

    right.send_telemetry(Telemetry(sequence=1, left_speed=3.0))
    assert left.recv_telemetry() is None
    assert left.stats.dropped == 1

    right.send_telemetry(Telemetry(sequence=2, left_speed=4.0))
    second = left.recv_telemetry()
    assert second is not None and second.sequence == 2


def test_malformed_and_oversized_are_counted(pair):
    left, right = pair
    left.sock.sendto(b"garbage", right.address)
    assert right.recv_command() is None
    left.sock.sendto(b"x" * 600, right.address)
    assert right.recv_command() is None
    assert right.stats.malformed == 2


def test_quiet_link_returns_none():
    link = Link(timeout=0.05)
    try:
        assert link.recv_telemetry() is None
        assert link.recv_command() is None
    finally:
        link.close()
