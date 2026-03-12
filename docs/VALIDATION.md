# Validation notes

Everything below was measured on this repository, on the bench machine, with
Python 3.11. Nothing here was copied from a datasheet. Where a number came from a
synthetic run, it says so.

## 1. Self-test

```text
$ fruitfly-motor check
protocol  ok    round trip ok, 4/4 malformed rejected, datagram 103 bytes
shaper    ok    dead zone quiet, slew capped first step at 9.9, settled 60.0, timeout reason 'shaper-timeout'
watchdog  ok    never-fed → stop, fed → ok, 150 ms later → 'starved'
PASS
```

The four malformed cases the self-test insists on: `NaN` in a drive, a boolean in a
drive, a packet of the wrong type, and a packet over the size limit. All four are
rejections, not clampings.

## 2. Slew and settle

With the default shaper (`max_command=60`, `slew_per_s=300`) a step from zero to full
drive moves the command to **9.9 units** on the first 33 ms step — exactly
`300 × 0.033` — and settles at **60.0** after roughly five steps. The dead zone is
checked before the limiter: a drive of 0.05 (3.0 units) stays at 0.0, a drive of 0.07
(4.2 units) moves.

## 3. Stop on silence

The demonstration run is `sim --seconds 8 --silence-after 5` (30 fps, default seed):

```text
t=  5.0s  cmd  +60.0/ +60.0 ...            <-- telemetry lost
t=  6.0s  cmd   +0.0/  +0.0  speed +0.9/ +0.8   <-- telemetry lost
pose: x=283.9 y=0.0 yaw=0.00 rad   battery 99.9%
peak |command| 60.0   stops: 1 (starved)
```

Measured behaviour, in order: the shaper's own timeout (500 ms) zeroes the wire
command at **t≈5.5 s**; the watchdog flips to `starved` shortly after (600 ms timeout,
so ≈5.63 s) and is counted **once** per episode; the wheels decay from 60 to about 1
unit/s within one second. `stops: 1` — the counter does not chatter while the link
stays dead.

`--profile startle` exercises the escape path instead: it stands still for 2 s, fires
the escape command for 0.8 s (`peak |command| 54.0` = 0.9 × 60), then walks. No stop
is counted, because nothing went quiet.

## 4. Bench round trip

`bench --count 200` on the loopback (macOS, Python 3.11):

```text
200 commands, 0 lost, command age p50 0.07 ms, p99 0.11 ms, max 0.19 ms
```

"Command age" is measured from the send call to the moment the echoed telemetry is
read back — it includes both Python sides, both syscalls and the JSON round trip. It
is a floor, not a promise: on a real network the numbers belong to the network.

## 5. Determinism and noise

- Two `RobotSim` instances with the same seed and the same commands produce
  identical telemetry sequences (asserted in the test suite, not just observed).
- The default noise level is σ = 0.25 units per wheel per step. Over 200 steps the
  worst deviation from a noiseless run stayed under 1.5 units, which is the bound the
  suite enforces.
- Battery drain is exactly zero while the commanded speed is zero (idle runs end at
  `battery == 1.0` exactly), and monotonic while moving.

## 6. What is not validated

- **No hardware.** The firmware scaffold in the fruitfly-brain repository has never
  been flashed from this branch; the plant model is not the chassis.
- **No real network.** Everything above ran on `127.0.0.1`. Packet loss, reordering
  and 300 ms of jitter are handled by design (gates, counters, timeouts) but were not
  measured on a real link.
- **No long-run numbers.** The longest continuous session tested is 12 seconds of
  simulated time; memory and drift over hours are unmeasured.
