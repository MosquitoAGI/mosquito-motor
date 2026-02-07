"""Run a session and render it to assets/sim-run.png.

The trace is produced by the real stack: the real shaper shapes, the real plant
model moves, the telemetry cut at eight seconds trips the real stop rules. The
picture is a render of that run, not an illustration.
"""

from __future__ import annotations

import pathlib
import sys

try:
    from fruitfly_motor.robot_sim import run_session
except ImportError:  # running from a checkout without installing the package
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
    from fruitfly_motor.robot_sim import run_session

from PIL import Image, ImageDraw

BG = (13, 18, 28)
PANEL = (20, 28, 44)
GRID = (38, 52, 78)
TEXT = (200, 214, 240)
DIM = (120, 140, 176)
ACCENT = (55, 211, 153)
WARN = (232, 168, 74)
LEFT = (121, 204, 232)
RIGHT = (200, 148, 232)

WIDTH, HEIGHT = 1000, 560
MARGIN_X, TOP = 64, 92
LANES = 3
LANE_H = 118
LANE_GAP = 26


def scale_y(value, low, high, top, height):
    frac = (value - low) / (high - low) if high > low else 0.5
    return top + height - frac * height


def polyline(draw, points, colour):
    if len(points) > 1:
        draw.line(points, fill=colour, width=3)


def draw_lane(draw, result, index, title, accessor, low, high, colours):
    top = TOP + index * (LANE_H + LANE_GAP)
    draw.rounded_rectangle([MARGIN_X, top, WIDTH - MARGIN_X, top + LANE_H],
                           radius=10, fill=PANEL, outline=GRID)
    draw.text((MARGIN_X + 14, top + 8), title, fill=DIM)
    draw.text((WIDTH - MARGIN_X - 120, top + 8),
              "%+.0f … %+.0f" % (low, high), fill=DIM)
    mid = scale_y((low + high) / 2.0, low, high, top, LANE_H)
    draw.line([MARGIN_X + 8, mid, WIDTH - MARGIN_X - 8, mid], fill=GRID, width=1)

    span = WIDTH - 2 * MARGIN_X - 24
    frames = result.frames
    for values, colour in accessor(frames):
        points = []
        for i, value in enumerate(values):
            x = MARGIN_X + 12 + span * i / max(1, len(values) - 1)
            points.append((x, scale_y(value, low, high, top, LANE_H)))
        polyline(draw, points, colour)


def main() -> int:
    result = run_session("approach", seconds=12.0, fps=30.0, silence_after_s=8.0)
    quiet_at = [f for f in result.frames if not f.telemetry]
    silence_x = None
    if quiet_at:
        span = WIDTH - 2 * MARGIN_X - 24
        first_quiet = result.frames.index(quiet_at[0])
        silence_x = MARGIN_X + 12 + span * first_quiet / max(1, len(result.frames) - 1)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((MARGIN_X, 26), "fruitfly-motor sim — approach, telemetry dies at 8.0 s",
              fill=TEXT)
    draw.text((MARGIN_X, 50),
              "commands, wheel speeds and battery, straight from the stop rules",
              fill=DIM)

    draw_lane(draw, result, 0, "commands (units)",
              lambda fr: [([f.cmd_left for f in fr], LEFT),
                          ([f.cmd_right for f in fr], RIGHT)],
              -63, 63, (LEFT, RIGHT))
    draw_lane(draw, result, 1, "wheel speed (units/s)",
              lambda fr: [([f.speed_left for f in fr], LEFT),
                          ([f.speed_right for f in fr], RIGHT)],
              -63, 63, (LEFT, RIGHT))
    draw_lane(draw, result, 2, "battery (%)",
              lambda fr: [([100.0 * f.battery for f in fr], ACCENT)],
              99.0, 100.0, (ACCENT,))

    if silence_x is not None:
        draw.line([silence_x, TOP - 6, silence_x, TOP + LANES * (LANE_H + LANE_GAP) - LANE_GAP],
                  fill=WARN, width=2)
        draw.text((silence_x + 8, TOP - 22), "telemetry lost", fill=WARN)

    footer = ("%d frames · stops %d (%s) · peak |command| %.0f · x=%.0f y=%.0f"
              % (len(result.frames), result.stops, result.stop_reason,
                 result.max_command, result.pose[0], result.pose[1]))
    draw.text((MARGIN_X, HEIGHT - 30), footer, fill=DIM)

    target = pathlib.Path(__file__).resolve().parents[1] / "assets" / "sim-run.png"
    image.save(target)
    print("wrote %s" % target)
    print(footer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
