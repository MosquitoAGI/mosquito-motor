import pytest

from fruitfly_motor.protocol import (
    MAX_COMMAND,
    MAX_PACKET,
    Command,
    MotorError,
    SequenceGate,
    Telemetry,
    encode_payload,
    make_command,
)


def test_command_round_trip():
    command = Command(left=12.5, right=-3.25, sequence=7, reason="track")
    again = Command.from_payload(command.payload())
    assert again.left == 12.5 and again.right == -3.25
    assert again.sequence == 7 and again.reason == "track"
    assert again.emergency_stop is False


def test_command_from_wire_is_clamped():
    again = Command.from_payload('{"type":"motor_command","left":500,"right":-500}')
    assert again.left == MAX_COMMAND and again.right == -MAX_COMMAND


def test_make_command_clamps():
    command = make_command(1000.0, -1000.0)
    assert command.left == MAX_COMMAND and command.right == -MAX_COMMAND


@pytest.mark.parametrize("payload", [
    "not json at all",
    "[]",
    '{"type":"telemetry"}',
    '{"type":"motor_command","right":0}',
    '{"type":"motor_command","left":NaN,"right":0}',
    '{"type":"motor_command","left":true,"right":0}',
    '{"type":"motor_command","left":"10","right":0}',
    '{"type":"motor_command","left":1e400,"right":0}',
    '{"type":"motor_command","left":0,"right":0,"sequence":-1}',
    '{"type":"motor_command","left":0,"right":0,"sequence":1.5}',
    '{"type":"motor_command","left":0,"right":0,"sequence":true}',
])
def test_command_rejects_malformed(payload):
    with pytest.raises(MotorError):
        Command.from_payload(payload)


def test_oversized_packet_is_rejected():
    with pytest.raises(MotorError):
        Command.from_payload("{" + "x" * (MAX_PACKET + 10) + "}")


def test_telemetry_round_trip():
    telemetry = Telemetry(sequence=3, left_speed=18.2, right_speed=-3.8,
                          gyro=(0.0, 0.0, 0.21), accel=(0.1, 0.2, 0.3), battery=0.93)
    again = Telemetry.from_payload(telemetry.payload())
    assert again.sequence == 3
    assert again.gyro[2] == pytest.approx(0.21)
    assert again.battery == pytest.approx(0.93)


@pytest.mark.parametrize("payload", [
    '{"type":"motor_command","left":0,"right":0}',
    '{"type":"telemetry","sequence":"1"}',
    '{"type":"telemetry","sequence":-1}',
    '{"type":"telemetry","sequence":1,"gyro":[0,0]}',
    '{"type":"telemetry","sequence":1,"accel":[0,0,null]}',
    '{"type":"telemetry","sequence":1,"battery":"half"}',
])
def test_telemetry_rejects_malformed(payload):
    with pytest.raises(MotorError):
        Telemetry.from_payload(payload)


def test_sequence_gate_accepts_in_order_once():
    gate = SequenceGate()
    assert gate.accept(1) and gate.accept(2)
    assert not gate.accept(2) and not gate.accept(1)
    assert gate.accept(3)
    assert gate.accepted == 3 and gate.rejected == 2


def test_encode_payload():
    assert encode_payload(make_command(1.0, 2.0)).startswith('{"type":"motor_command"')
    with pytest.raises(MotorError):
        encode_payload(42)
