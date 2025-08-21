from controller import Controller


def test_displacement_caps():
    c = Controller()
    dx, dy = c.displacement({"x_pos": 1.0, "y_neg": 1.0})
    assert abs(dx) <= 18.0
    assert abs(dy) <= 18.0


def test_opposite_rates_cancel():
    c = Controller()
    dx, dy = c.displacement({"x_pos": 1.0, "x_neg": 1.0})
    assert dx == 0.0 and dy == 0.0


def test_tick_moves_cursor():
    c = Controller()
    c.tick({"x_pos": 0.5}, now=10.0)
    x, y = c.cursor.position()
    assert x == 9
