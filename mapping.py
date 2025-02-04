"""Motor actions and their wiring to spike channels."""
from enum import Enum


class Action(Enum):
    MOTOR_X = "motor_x"
    MOTOR_Y = "motor_y"
    CLICK = "click"
    SCROLL = "scroll"
    BACK = "back"


CHANNELS = {
    "x_pos": Action.MOTOR_X,
    "x_neg": Action.MOTOR_X,
    "y_pos": Action.MOTOR_Y,
    "y_neg": Action.MOTOR_Y,
    "click": Action.CLICK,
    "scroll": Action.SCROLL,
    "back": Action.BACK,
}


def action_of(channel):
    return CHANNELS.get(channel)
