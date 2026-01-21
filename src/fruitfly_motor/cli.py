"""Command line: check, sim, bench, replay, send.

The subcommands are ordered by how much they need: ``check`` needs nothing,
``sim`` needs the robot model, ``bench`` needs two sockets on one machine,
``replay`` needs a session file, and ``send`` needs a robot.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time

from . import __version__
from .protocol import MAX_COMMAND, Command, MotorError, Telemetry
from .replay import Replayer, SessionError, dump_session, load_session
from .robot_sim import PROFILES, RobotConfig, run_session
from .shaper import CommandShaper, ShaperConfig
from .transport import Link
from .watchdog import Watchdog, WatchdogConfig

DEFAULT_TARGET = "127.0.0.1:9000"


def _target(text: str) -> tuple[str, int]:
    host, _, port = text.rpartition(":")
    if not host or not port.isdigit():
        raise argparse.ArgumentTypeError("target must look like host:port")
    return (host, int(port))


# ------------------------------------------------------------------- check

def _check_protocol() -> tuple[str, str]:
    command = Command(left=12.5, right=-3.25, sequence=7, reason="track")
    parsed = Command.from_payload(command.payload())
    same = parsed.left == command.left and parsed.right == command.right
    telemetry = Telemetry(sequence=3, left_speed=11.9, right_speed=-3.1, battery=0.97)
    back = Telemetry.from_payload(telemetry.payload())
    same = same and abs(back.left_speed - telemetry.left_speed) < 1e-6
    rejected = 0
    for bad in ('{"type":"motor_command","left":NaN,"right":0}',
                '{"type":"motor_command","left":true,"right":0}',
                '{"type":"other"}',
                "{" + "x" * 600 + "}"):
        try:
            Command.from_payload(bad)
        except MotorError:
            rejected += 1
    return ("ok" if same and rejected == 4 else "FAIL",
            "round trip ok, %d/4 malformed rejected, datagram %d bytes"
            % (rejected, len(command.payload())))


def _check_shaper() -> tuple[str, str]:
    shaper = CommandShaper(ShaperConfig(max_command=60.0, dead_zone=4.0,
                                        slew_per_s=300.0), timeout_ms=500.0)
    shaper.update(0.05, 0.05, False, 0.0, 33.0)          # inside the dead zone
    quiet = shaper.read(10.0)
    shaper.update(1.0, 1.0, False, 20.0, 33.0)           # full drive, slew limited
    first = shaper.read(30.0)
    for step in range(60):
        shaper.update(1.0, 1.0, False, 40.0 + step * 33.0, 33.0)
    settled = shaper.read(40.0 + 60 * 33.0)
    shaper.zero_now(3000.0)
    timed_out = shaper.read(3600.0)
    ok = (quiet.left == 0.0 and 0.0 < first.left < 12.0
          and abs(settled.left - 60.0) < 0.01 and timed_out.emergency_stop)
    return ("ok" if ok else "FAIL",
            "dead zone quiet, slew capped first step at %.1f, settled %.1f, "
            "timeout reason %r" % (first.left, settled.left, timed_out.reason))


def _check_watchdog() -> tuple[str, str]:
    watchdog = Watchdog(WatchdogConfig(timeout_ms=100.0, grace_ms=50.0))
    never = watchdog.reason(0.0)
    watchdog.feed(100.0)
    early = watchdog.expired(200.0)
    late = watchdog.reason(300.0)
    ok = never == "never-fed" and not early and late == "starved"
    return ("ok" if ok else "FAIL", "never-fed → stop, fed → ok, 150 ms later → %r" % late)


def cmd_check(args) -> int:
    rows = [("protocol",) + _check_protocol(),
            ("shaper",) + _check_shaper(),
            ("watchdog",) + _check_watchdog()]
    width = max(len(name) for name, _s, _n in rows)
    for name, state, note in rows:
        print("%-*s  %-4s  %s" % (width, name, state, note))
    failed = [name for name, state, _n in rows if state != "ok"]
    print("PASS" if not failed else "FAIL: %s" % ", ".join(failed))
    return 0 if not failed else 1


# --------------------------------------------------------------------- sim

def cmd_sim(args) -> int:
    robot_cfg = RobotConfig(seed=args.seed) if args.seed is not None else RobotConfig()
    result = run_session(args.profile, seconds=args.seconds, fps=args.fps,
                         robot_cfg=robot_cfg,
                         silence_after_s=args.silence_after)
    print("session: %s profile, %.1f s at %.0f fps, seed %s"
          % (args.profile, result.duration_s, args.fps, robot_cfg.seed))
    every = max(1, int(round(args.fps)))
    for index, frame in enumerate(result.frames):
        if index % every:
            continue
        note = "" if frame.telemetry else "   <-- telemetry lost"
        print("t=%5.1fs  cmd %+6.1f/%+6.1f  speed %+6.1f/%+6.1f  yaw %+5.2f rad  "
              "batt %5.1f%%%s" % (frame.t_ms / 1000.0, frame.cmd_left, frame.cmd_right,
                                  frame.speed_left, frame.speed_right, frame.yaw,
                                  100.0 * frame.battery, note))
    x, y, yaw = result.pose
    print("pose: x=%.1f y=%.1f yaw=%.2f rad   battery %.1f%%"
          % (x, y, yaw, 100.0 * result.battery))
    print("peak |command| %.1f   stops: %d (%s)"
          % (result.max_command, result.stops,
             result.stop_reason if result.stops else "none"))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as handle:
            handle.write("t_ms,left_in,right_in,cmd_left,cmd_right,speed_left,"
                         "speed_right,yaw,battery,telemetry\n")
            for frame in result.frames:
                handle.write("%.1f,%.4f,%.4f,%.3f,%.3f,%.3f,%.3f,%.5f,%.4f,%d\n"
                             % (frame.t_ms, frame.left_in, frame.right_in, frame.cmd_left,
                                frame.cmd_right, frame.speed_left, frame.speed_right,
                                frame.yaw, frame.battery, int(frame.telemetry)))
        print("wrote %s (%d frames)" % (args.csv, len(result.frames)))
    if args.record:
        count = dump_session(result.drives(), args.record)
        print("wrote %s (%d samples)" % (args.record, count))
    return 0


# ------------------------------------------------------------------- bench

def cmd_bench(args) -> int:
    stop = Link(timeout=1.0)
    robot = Link(timeout=1.0)
    stop.target = robot.address
    robot.target = stop.address
    ages = []
    lost = 0
    shaper = CommandShaper(ShaperConfig(), timeout_ms=500.0)
    try:
        for index in range(args.count):
            command = shaper.update(0.5, 0.5, False, index * 33.0, 33.0)
            start = time.perf_counter()
            stop.send_command(command)
            incoming = robot.recv_command()
            if incoming is None:
                lost += 1
                continue
            robot.send_telemetry(Telemetry(sequence=incoming.sequence,
                                           left_speed=incoming.left,
                                           right_speed=incoming.right))
            answer = stop.recv_telemetry()
            if answer is None:
                lost += 1
                continue
            ages.append((time.perf_counter() - start) * 1000.0)
    finally:
        stop.close()
        robot.close()
    if not ages:
        print("no round trips completed (%d lost)" % lost)
        return 1
    ages.sort()
    p50 = statistics.median(ages)
    p99 = ages[min(len(ages) - 1, int(round(0.99 * (len(ages) - 1))))]
    print("%d commands, %d lost, command age p50 %.2f ms, p99 %.2f ms, max %.2f ms"
          % (args.count, lost, p50, p99, ages[-1]))
    print("bridge side: %s" % stop.stats.summary())
    print("robot side:  %s" % robot.stats.summary())
    return 0


# ------------------------------------------------------------------ replay

def cmd_replay(args) -> int:
    try:
        samples = load_session(args.session)
    except (OSError, SessionError) as exc:
        print("cannot read session: %s" % exc, file=sys.stderr)
        return 1
    replayer = Replayer(samples)
    if args.dry_run:
        commands = replayer.run(realtime=False)
        print("session: %s" % args.session)
        print(replayer.summary(commands))
        for t_ms, command in commands[: args.preview]:
            print("t=%7.1f ms  %+7.2f/%+7.2f  %s"
                  % (t_ms, command.left, command.right, command.reason))
        if len(commands) > args.preview:
            print("... %d more" % (len(commands) - args.preview))
        return 0
    if args.target is None:
        print("replay needs --dry-run or --target host:port", file=sys.stderr)
        return 2
    link = Link(target=args.target)
    sent = 0
    try:
        for _t_ms, command in replayer.stream(realtime=args.realtime):
            link.send_command(command)
            sent += 1
    finally:
        link.close()
    print("sent %d commands to %s:%d (%s)"
          % (sent, args.target[0], args.target[1],
             "recorded timing" if args.realtime else "as fast as possible"))
    return 0


# -------------------------------------------------------------------- send

def cmd_send(args) -> int:
    command = Command(left=args.left, right=args.right, sequence=1,
                      emergency_stop=args.estop, reason="manual").clamped()
    for side, value in (("left", command.left), ("right", command.right)):
        if abs(value) > MAX_COMMAND:
            print("%s exceeds %.0f" % (side, MAX_COMMAND), file=sys.stderr)
            return 2
    link = Link(target=args.target)
    try:
        wrote = link.send_command(command)
    finally:
        link.close()
    print("%s → %s:%d  (%d bytes, %s)"
          % (command.payload(), args.target[0], args.target[1], wrote,
             "emergency stop" if command.emergency_stop else "normal"))
    return 0


# ---------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fruitfly-motor",
        description="Motor side of the bridge: commands out, telemetry in, "
                    "silence treated as stop.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="self-test the protocol, shaper and watchdog")
    check.set_defaults(func=cmd_check)

    sim = sub.add_parser("sim", help="run the plant model through the whole stack")
    sim.add_argument("--profile", choices=sorted(PROFILES), default="approach")
    sim.add_argument("--seconds", type=float, default=10.0)
    sim.add_argument("--fps", type=float, default=30.0)
    sim.add_argument("--seed", type=int, default=None)
    sim.add_argument("--silence-after", type=float, default=None, metavar="S",
                     help="cut telemetry at S seconds and watch both stop rules")
    sim.add_argument("--csv", default=None, metavar="PATH")
    sim.add_argument("--record", default=None, metavar="PATH",
                     help="write the drives as a replayable session")
    sim.set_defaults(func=cmd_sim)

    bench = sub.add_parser("bench", help="UDP round trip on the loopback")
    bench.add_argument("--count", type=int, default=200)
    bench.set_defaults(func=cmd_bench)

    replay = sub.add_parser("replay", help="re-send a recorded session")
    replay.add_argument("--session", required=True)
    replay.add_argument("--target", type=_target, default=None)
    replay.add_argument("--realtime", action="store_true")
    replay.add_argument("--dry-run", action="store_true")
    replay.add_argument("--preview", type=int, default=5)
    replay.set_defaults(func=cmd_replay)

    send = sub.add_parser("send", help="send one command")
    send.add_argument("--left", type=float, required=True)
    send.add_argument("--right", type=float, required=True)
    send.add_argument("--estop", action="store_true")
    send.add_argument("--target", type=_target,
                      default=_target(DEFAULT_TARGET))
    send.set_defaults(func=cmd_send)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
