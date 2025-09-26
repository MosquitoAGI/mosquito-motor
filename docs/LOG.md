# Build log

Short dated notes from the bench, oldest first. Not a changelog —
[CHANGELOG.md](../CHANGELOG.md) has releases; this file has days. Quiet weeks
have no line, which is most weeks.

- 2025-02-18 — the motor side becomes its own package today. the first commit is mostly an apology to the shaper.
- 2025-03-03 — the dead zone is not a fudge; it is the part where the motor hums and does not turn. keep it at 4.
- 2025-03-16 — tested the shaper on a single spare wheel. the slew limit is the difference between a robot and a catapult.
- 2025-04-09 — blew a fuse on the bench supply. the shaper was innocent; the wiring was not.
- 2025-04-23 — read every stop rule out loud tonight. two of them overlapped in a way I did not like; one got simplified.
- 2025-05-07 — the bench hub browns out under two servos. lab supply ordered.
- 2025-05-21 — replay drifts about 4 ms per minute at realtime. acceptable for a bench; noted.
- 2025-06-05 — counters in the summary save arguments: malformed, dropped, sent, received. no adjectives.
- 2025-06-19 — quiet month on this side; the bridge got the attention. motor side kept its tests green.
- 2025-07-03 — added p99 to the bench output because a max over 200 samples is one unlucky syscall.
- 2025-07-18 — measured the loopback round trip before the robot exists. 0.1 ms. the network will never be this honest.
- 2025-07-31 — collected every magic number in the shaper into a config with a note per field. the notes took longer than the code.
- 2025-08-13 — the sim says 1.5 hours of full-speed driving. treat it as a number from a sim, not a promise.
- 2025-08-26 — spent twenty minutes in the drawer of adapters. the right one was at the bottom. it always is.
- 2025-09-26 — drew the stop rules on paper: board, watchdog, shaper timeout. three arrows into one box that says zero.
