import pytest

from fruitfly_motor.protocol import MAX_COMMAND
from fruitfly_motor.shaper import CommandShaper, ShaperConfig


def build(**kw):
    return CommandShaper(ShaperConfig(**kw), timeout_ms=500.0)


@pytest.mark.parametrize("kw", [
    {"max_command": 0.0},
    {"max_command": MAX_COMMAND + 1},
    {"dead_zone": -1.0},
    {"dead_zone": 60.0},
    {"slew_per_s": -1.0},
    {"smoothing": 1.0},
    {"escape_command": 0.0},
    {"escape_command": 1.5},
])
def test_config_validation(kw):
    with pytest.raises(ValueError):
        ShaperConfig(**kw).validate()


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        CommandShaper(timeout_ms=0)


def test_dead_zone_zeroes_small_input():
    shaper = build()
    command = shaper.update(0.05, 0.05, False, 0.0, 33.0)
    assert command.left == 0.0 and command.right == 0.0


def test_dead_zone_edge_keeps_input_above_threshold():
    shaper = build()
    command = shaper.update(0.07, 0.07, False, 0.0, 33.0)
    assert command.left > 0.0


def test_slew_limits_the_first_step():
    shaper = build()  # 300 units/s over 33 ms is 9.9 units
    command = shaper.update(1.0, 1.0, False, 0.0, 33.0)
    assert command.left == pytest.approx(9.9)


def test_settles_at_the_scaled_target():
    shaper = build()
    for index in range(60):
        shaper.update(1.0, 1.0, False, index * 33.0, 33.0)
    command = shaper.read(59 * 33.0)
    assert command.left == pytest.approx(60.0)


def test_smoothing_softens_each_step():
    shaper = build(smoothing=0.5)
    command = shaper.update(1.0, 1.0, False, 0.0, 33.0)
    assert command.left == pytest.approx(4.95)


def test_invert_flips_the_sign():
    shaper = build(invert_left=True)
    for index in range(60):
        command = shaper.update(0.5, 0.5, False, index * 33.0, 33.0)
    assert command.left == pytest.approx(-30.0)
    assert command.right == pytest.approx(30.0)


def test_escape_overrides_both_sides():
    shaper = build(slew_per_s=0.0, escape_command=1.0)
    command = shaper.update(0.1, 0.1, True, 0.0, 33.0)
    assert command.reason == "escape"
    assert command.left == pytest.approx(60.0)
    assert command.right == pytest.approx(60.0)


def test_timeout_zeroes_and_flags():
    shaper = build()
    shaper.update(1.0, 1.0, False, 0.0, 33.0)
    assert shaper.read(0.0).reason == "track"
    quiet = shaper.read(600.0)
    assert quiet.left == 0.0 and quiet.right == 0.0
    assert quiet.emergency_stop and quiet.reason == "shaper-timeout"


def test_zero_now_is_not_an_estop():
    shaper = build()
    shaper.update(1.0, 1.0, False, 0.0, 33.0)
    shaper.zero_now(10.0)
    command = shaper.read(20.0)
    assert command.left == 0.0
    assert not command.emergency_stop and command.reason == "track"


def test_estop_latches_until_cleared():
    shaper = build()
    shaper.update(0.5, 0.5, False, 1000.0, 33.0)
    shaper.emergency_stop()
    assert shaper.read(1010.0).reason == "emergency-stop"
    shaper.clear_emergency()
    assert shaper.read(1020.0).reason == "track"


def test_sequence_increments():
    shaper = build()
    first = shaper.update(0.5, 0.5, False, 0.0, 33.0)
    second = shaper.update(0.5, 0.5, False, 33.0, 33.0)
    assert second.sequence == first.sequence + 1


def test_reset_zeroes_the_wire_state():
    shaper = build()
    shaper.update(1.0, 1.0, False, 0.0, 33.0)
    shaper.reset()
    command = shaper.read(10.0)
    assert command.left == 0.0
