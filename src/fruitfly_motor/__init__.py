"""FruitFlyMotor — the last hop before the wheels move.

Everything here exists to answer one question correctly: what happens when the
commands stop arriving? The answer is a stop, applied by whichever component
notices first, and the rest of the package is arranged around making that true
even when a cable is pulled, a process dies, or a packet is dropped.
"""

from .protocol import Command, MotorError, Telemetry, make_command
from .robot_sim import PROFILES, RobotConfig, RobotSim, run_session
from .shaper import CommandShaper, ShaperConfig
from .transport import Link, LinkStats
from .watchdog import Watchdog, WatchdogConfig

__version__ = "0.2.0"

SAFE_LEFT = 0.0
SAFE_RIGHT = 0.0

__all__ = [
    "Command",
    "CommandShaper",
    "Link",
    "LinkStats",
    "MotorError",
    "PROFILES",
    "RobotConfig",
    "RobotSim",
    "SAFE_LEFT",
    "SAFE_RIGHT",
    "ShaperConfig",
    "Telemetry",
    "Watchdog",
    "WatchdogConfig",
    "__version__",
    "make_command",
    "run_session",
]
