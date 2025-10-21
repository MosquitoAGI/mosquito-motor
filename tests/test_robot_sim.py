import pytest

from fruitfly_motor.protocol import Command
from fruitfly_motor.robot_sim import PROFILES, RobotConfig, RobotSim, run_session


def drive(left, right, estop=False):
    return Command(left=left, right=right, sequence=0,
                   emergency_stop=estop, reason="test")


def test_first_order_approach_is_monotonic():
    sim = RobotSim(RobotConfig(wheel_tau_ms=100.0, noise=0.0, seed=1))
    speeds = []
    for _ in range(60):
        speeds.append(sim.step(drive(60.0, 60.0), 33.0).left_speed)
    assert all(b >= a - 1e-9 for a, b in zip(speeds, speeds[1:]))
    assert speeds[0] < 60.0
    assert speeds[-1] == pytest.approx(60.0, abs=0.2)


def test_emergency_stop_decelerates_to_zero():
    sim = RobotSim(RobotConfig(noise=0.0))
    for _ in range(60):
        sim.step(drive(60.0, 60.0), 33.0)
    telemetry = sim.step(drive(60.0, 60.0, estop=True), 33.0)
    assert abs(telemetry.left_speed) < 60.0
    for _ in range(120):
        telemetry = sim.step(drive(60.0, 60.0, estop=True), 33.0)
    assert abs(telemetry.left_speed) < 0.1
    assert abs(telemetry.right_speed) < 0.1


def test_battery_drains_only_while_moving():
    idle = RobotSim(RobotConfig(noise=0.0))
    moving = RobotSim(RobotConfig(noise=0.0))
    for _ in range(60):
        idle.step(drive(0.0, 0.0), 33.0)
        moving.step(drive(60.0, 60.0), 33.0)
    assert idle.battery == 1.0
    assert moving.battery < 1.0


def test_runs_are_deterministic():
    def run():
        sim = RobotSim(RobotConfig(seed=7))
        return [(t.left_speed, t.right_speed)
                for t in (sim.step(drive(30.0, -10.0), 33.0) for _ in range(40))]
    assert run() == run()


def test_noise_stays_small():
    clean = RobotSim(RobotConfig(noise=0.0, seed=3))
    noisy = RobotSim(RobotConfig(noise=0.25, seed=3))
    worst = 0.0
    for _ in range(200):
        a = clean.step(drive(40.0, 40.0), 33.0)
        b = noisy.step(drive(40.0, 40.0), 33.0)
        worst = max(worst, abs(a.left_speed - b.left_speed))
    assert worst < 1.5


def test_yaw_is_damped_and_follows_the_sign():
    sim = RobotSim(RobotConfig(noise=0.0))
    first = sim.step(drive(10.0, 40.0), 33.0)
    raw = (sim.right_speed - sim.left_speed) / sim.cfg.wheel_base
    assert first.gyro[2] < raw
    for _ in range(300):
        telemetry = sim.step(drive(10.0, 40.0), 33.0)
    assert sim.yaw > 0.0
    assert telemetry.gyro[2] > 0.0


def test_run_session_stops_when_telemetry_dies():
    result = run_session("approach", seconds=8.0, fps=30.0, silence_after_s=4.0)
    assert result.stops == 1
    assert result.stop_reason == "starved"
    after = [f for f in result.frames if f.t_ms >= 6000.0]
    assert after and all(f.cmd_left == 0.0 and f.cmd_right == 0.0 for f in after)


def test_run_session_healthy_run_has_no_stops():
    result = run_session("wiggle", seconds=6.0, fps=30.0)
    assert result.stops == 0
    assert result.stop_reason == "ok"
    assert result.max_command > 0.0


def test_profiles_are_pure_functions_of_time():
    assert PROFILES["idle"](10.0) == (0.0, 0.0, False)
    assert PROFILES["startle"](2.4)[2] is True
    assert PROFILES["approach"](3.0) == (1.0, 1.0, False)
    with pytest.raises(ValueError):
        run_session("nope", seconds=1.0)
