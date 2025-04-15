"""Convert spike rates into displacement."""
from cursor import Cursor

GAIN = 18.0
MAX_STEP = 18.0


class Controller:
    def __init__(self, cursor=None):
        self.cursor = cursor or Cursor()

    def tick(self, rates):
        """rates: dict of channel -> rate in [0, 1]."""
        dx = (rates.get("x_pos", 0.0) - rates.get("x_neg", 0.0)) * GAIN
        dy = (rates.get("y_pos", 0.0) - rates.get("y_neg", 0.0)) * GAIN
        dx = max(-MAX_STEP, min(MAX_STEP, dx))
        dy = max(-MAX_STEP, min(MAX_STEP, dy))
        return self.cursor.move_by(dx, dy)
