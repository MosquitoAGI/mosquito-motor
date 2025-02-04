<div align="center">

# FruitFlyMotor

**The last hop: shaped commands out, telemetry back.**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-79cce8?style=flat-square)
![Tests](https://img.shields.io/badge/tests-52_passing-38c172?style=flat-square)
[![License: MIT](https://img.shields.io/badge/License-MIT-60dfb3?style=flat-square)](LICENSE)

</div>

This is the actuator side of the fruitfly-brain bridge, extracted so the
command path can be shaped, benched and reasoned about without a camera.

One rule shapes everything in here: when the commands stop arriving, the robot
stops. The watchdog, the shaper's timeout and the counters all exist to make
that true and audible.

Personal bench project. It runs against a laptop before it runs against a
robot.

## What it does

- Shapes drives into commands in a fixed order: clamp, dead zone, slew limit.
- Speaks strict JSON/UDP in both directions; nothing malformed is applied.
- Stops on silence, and says why.
- Standard library only.

## Quick start

Requires Python 3.11+.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m fruitfly_motor check
```

## Current limitations

- No hardware validation yet.
- UDP without authentication.
- One robot per process.

## License

MIT — see [LICENSE](LICENSE).
