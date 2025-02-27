"""Cursor position state."""


class Cursor:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def move_by(self, dx, dy):
        self.x += dx
        self.y += dy
        return self.x, self.y

    def position(self):
        return round(self.x), round(self.y)
