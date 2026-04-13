---
name: Feature request
about: Propose a change to the motor side
labels: enhancement
---

**What should change**

**Why**

**What it must not break**

The stop rules are the point of this package: a quiet link must end in a stopped
robot, and a malformed packet must never be partially applied. Changes that touch
the shaper order, the wire format or the watchdog need a test and a line in
`docs/VALIDATION.md`.
