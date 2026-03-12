# Contributing

Small project, small process.

1. Open an issue describing what you want to change, or what broke.
2. Keep pull requests scoped to one thing. I would rather merge three small patches
   than one that touches the shaper, the wire format and the simulator.
3. Run the suite before you push:

   ```bash
   python3.11 -m venv .venv && . .venv/bin/activate
   pip install -e ".[dev]"
   pytest -q
   ruff check .
   fruitfly-motor check
   ```

4. If you change anything in the wire format, update the packet examples in
   `docs/ARCHITECTURE.md` and the firmware scaffold in the fruitfly-brain repository
   in the same pull request. A protocol that only exists on one side of the link is
   a protocol that will silently disagree with the robot.

## What gets rejected

- New dependencies. This package is standard library only, and that is a feature.
- Anything that lets a stop rule be bypassed, or makes a malformed packet partially
  applied.
- New configuration knobs without validation and without a test.
