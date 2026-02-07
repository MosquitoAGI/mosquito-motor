# Changelog

All notable changes to this project are recorded here. Dates live in the
build log (docs/LOG.md); versions live here.

## [0.2.1]

- Slew limiting is on by default (300 units/s). Off, a step from 0 to the cap
  produced a current spike the simulated driver reported as a fault.

## [0.2.0]

- `robot_sim`: first-order wheel lag, yaw damping, battery decay, seeded noise.
- `replay`: recorded sessions can be re-sent to a robot at their original rates
  or as fast as possible.

## [0.1.0]

- Protocol, shaper, watchdog and the UDP transport.
