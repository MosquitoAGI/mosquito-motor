# Security

The motor side is an experimental bench tool which speaks unauthenticated UDP to a
robot, by design — see `docs/ARCHITECTURE.md` for the wire format and what is
enforced.

## What not to do

- Do not expose the robot port to the internet. There is no authentication, no
  session ID and no replay protection. Anyone who can reach the port can drive the
  motors.
- Do not run a `--realtime` replay against real motors before the stop rules have
  been tested on blocks. The watchdog protects against a *quiet* link; it does not
  protect against a link that is cheerfully sending the wrong commands.
- Do not remove the board-side stop in the firmware scaffold and rely on this side
  alone. A process that hangs cannot send the packet that says "stop".

## Reporting

Open an issue for anything that could move hardware unexpectedly, and include the
session file and the link counters (`bench` prints them). Safety-relevant reports
get priority.
