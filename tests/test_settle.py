from controller import Controller
from cursor import Cursor


def test_rate_limit_drops_excess():
    c = Controller()
    c.tick({"x_pos": 1.0}, now=10.0)
    x1, _ = c.cursor.position()
    pos = c.tick({"x_pos": 1.0}, now=10.001)  # inside the 60 Hz window
    assert pos == (x1, 0)


def test_interpolate_settles():
    cur = Cursor()
    points = list(cur.interpolate(40, 40, steps=4))
    assert len(points) == 4
    assert cur.settled


def test_displacement_zero_at_rest():
    c = Controller()
    assert c.displacement({}) == (0.0, 0.0)
