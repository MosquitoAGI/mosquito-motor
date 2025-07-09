"""Wheel deltas with clamps."""

MAX_WHEEL = 400.0


def scroll(page, dy):
    dy = max(-MAX_WHEEL, min(MAX_WHEEL, float(dy)))
    page.mouse.wheel(0, dy)
    return dy
