"""Cursor position state with interpolation."""
import numpy as np


class Cursor:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        self.settled = True

    def move_by(self, dx, dy):
        self.x += dx
        self.y += dy
        self.settled = abs(dx) < 1e-6 and abs(dy) < 1e-6
        return self.x, self.y

    def interpolate(self, target_x, target_y, steps=4):
        """Yield intermediate points so movement is not teleportation."""
        xs = np.linspace(self.x, target_x, steps + 1)[1:]
        ys = np.linspace(self.y, target_y, steps + 1)[1:]
        for x, y in zip(xs, ys):
            self.x, self.y = float(x), float(y)
            yield self.x, self.y
        self.settled = True

    def position(self):
        return round(self.x), round(self.y)
