# mosquito-motor

The motor layer of Mosquito AI: spikes in, movement out.

    MOTOR_X  - horizontal displacement
    MOTOR_Y  - vertical displacement
    CLICK    - contact
    SCROLL   - travel through a page
    BACK     - retreat

Motor neurons fire in rates; the controller converts rates into per-tick
displacement. One tick is one control step, not one millisecond.

Part of the Mosquito AI project.
