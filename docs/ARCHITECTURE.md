# Architecture

The motor side is deliberately small. Its job is to turn two drives into commands a
robot will accept, and to make a stop happen when the drives stop arriving.

## Data flow

```text
profile / replay / CLI ── drives ──→ Shaper ── Command ──→ Link ── UDP :9000 ──→ robot
                                                             ↑
robot ──→ telemetry ── UDP ──→ Link ──→ Watchdog ──→ stop rule ┘
```

One socket carries both directions. Commands are shaped before they are encoded;
telemetry is validated before it is admitted; the watchdog sits between the link and
the shaper and can zero the wire command at any time.

## Modules

| module | job |
|---|---|
| `protocol` | The two packet types, strict validation, sequence gate. |
| `shaper` | drives → commands: clamp, dead zone, slew, smoothing, invert; timeout stop. |
| `watchdog` | Telemetry age and failure naming (`never-fed` / `starved`). |
| `transport` | UDP link with counters: sent, received, malformed, dropped. |
| `robot_sim` | First-order plant model, named drive profiles, the whole-stack session. |
| `replay` | Session files (JSONL), replay through a real shaper. |
| `cli` | `check`, `sim`, `bench`, `replay`, `send`. |

## The shaper order

`clamp → dead zone → slew → smoothing → invert`, and each position is load-bearing:

- **Clamp** first: everything downstream assumes a drive in 0..1.
- **Dead zone** second: a command below `dead_zone` units is set to zero *before*
  the slew limiter, so a slow ramp does not spend a second crawling through values
  that the motors cannot act on anyway.
- **Slew limit** third: the change per step is capped at `slew_per_s * dt`. This is
  the only place that keeps a step change from being applied as a step change.
- **Smoothing** fourth: an optional low-pass on the shaped value, for chassis that
  ring. The default is 0 — off — because a filter you did not ask for is a delay
  you did not ask for.
- **Invert** last: a sign flip. It is applied after everything that is sensitive to
  magnitude so that inverting a side cannot change when its dead zone ends.

The escape path replaces the target (`escape_command`, 0.9 by default) and is still
slew-limited and still smoothed: the wheels cannot teleport.

## Stop rules

| condition | where it is detected | what goes on the wire | reason |
|---|---|---|---|
| caller went quiet | `shapless timeout` | zeros, `emergency_stop=true` | `shaper-timeout` |
| telemetry died | `watchdog` | caller decides (see `sim`) | `starved` |
| telemetry never arrived | `watchdog` | caller decides | `never-fed` |
| explicit stop | `shaper.emergency_stop()` | zeros, latched | `emergency-stop` |

The watchdog and the shaper timeout are independent on purpose. One protects against
a quiet *remote side*, the other against a hung *local side*, and a bench summary
that conflates them sends you debugging the wrong machine.

## Wire format

Two JSON objects, UTF-8, at most 512 bytes each:

```json
{"type":"motor_command","sequence":42,"left":18.5,"right":-4.0,
 "emergency_stop":false,"reason":"track"}
```

```json
{"type":"telemetry","sequence":17,"left_speed":18.2,"right_speed":-3.8,
 "gyro":[0,0,0.21],"accel":[0,0,0],"battery":0.93}
```

Rules that are enforced, not suggested:

- Commands carry drives between -100 and 100; anything outside is clamped on decode.
- Sequences are non-negative integers; telemetry sequences must arrive strictly
  increasing. Duplicates and reorderings are dropped with a counter.
- A packet that is not valid UTF-8 JSON, is not an object, is the wrong type, or is
  over 512 bytes is counted `malformed` and never applied.
- `left`/`right`/`battery`/`gyro`/`accel` must be finite numbers (booleans excluded —
  `true` is not 1).

## Replay sessions

One JSON object per line:

```json
{"t_ms":0,"left":0.0,"right":0.0,"escape":false}
{"t_ms":33.1,"left":0.42,"right":0.42,"escape":false}
```

`load_session` rejects a file with a single bad line, a backwards timestamp, or a
non-numeric drive — whole-file rejection, not skip-and-warn, because a replay that
silently skips steps is a replay of a different run. `sim --record` writes exactly
this format, so a simulation can be re-sent to a robot.

## The plant model

```text
speed ← speed + (target - speed) · (1 - e^(-dt/τ))     first-order wheel lag
yaw_rate ← raw · (1 - damping) + yaw_rate · damping     damped turn rate
yaw ← yaw + yaw_rate · dt                               differential drive
x, y ← ∫ mean_speed over the heading                    dead reckoning
battery ← battery - load · dt / (battery_hours · 3600)  drain scales with load
```

Noise is `gauss(0, σ)` per wheel per step, seeded, so a "flaky" run is a number in a
test, not a mystery on a bench.

## Testing

88 tests, no sleeps, no real network beyond UDP on the loopback. Every time value
that matters is a parameter (`dt_ms`, `now_ms`), which is what makes a 500 ms timeout
testable in microseconds.
