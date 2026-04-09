"""Convert spike rates into displacement."""
import time
from cursor import Cursor

GAIN = 18.0
MAX_STEP = 18.0
MIN_INTERVAL = 1.0 / 60.0  # never emit faster than 60 Hz


class Controller:
    def __init__(self, cursor=None):
        self.cursor = cursor or Cursor()
        self._last_emit = 0.0

    def displacement(self, rates):
        dx = (rates.get("x_pos", 0.0) - rates.get("x_neg", 0.0)) * GAIN
        dy = (rates.get("y_pos", 0.0) - rates.get("y_neg", 0.0)) * GAIN
        dx = max(-MAX_STEP, min(MAX_STEP, dx))
        dy = max(-MAX_STEP, min(MAX_STEP, dy))
        # a single tick may never teleport the cursor across the viewport;
        # sustained movement is many ticks, not one big step.
        return dx, dy

    def tick(self, rates, now=None):
        now = time.monotonic() if now is None else now
        if now - self._last_emit < MIN_INTERVAL:
            return self.cursor.position()
        self._last_emit = now
        dx, dy = self.displacement(rates)
        return self.cursor.move_by(dx, dy)
