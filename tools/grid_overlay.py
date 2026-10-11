#!/usr/bin/env python3
"""Draw a hex grid with each hex's Wesnoth coordinates over a map render.

    wesnoth --screenshot maps/X.map shot.png
    tools/grid_overlay.py maps/X.map shot.png shot-grid.png

The labels are the coordinates Wesnoth shows in-game and in the editor
(1-based, x across, y down), so a hex can be named as "16,13" when asking
for a change. Needs Pillow.
"""

import math
import sys

from PIL import Image, ImageDraw, ImageFont


def overlay(map_path, shot_path, out_path):
    with open(map_path) as f:
        rows = [r for r in f.read().splitlines() if r.strip()]
    cols, nrows = len(rows[0].split(",")), len(rows)   # with the border
    im = Image.open(shot_path).convert("RGBA")
    # --screenshot crops half of the border hexes: work out the offset
    full_w, full_h = 54 * cols + 18, 72 * nrows + 36
    ox = (full_w - im.size[0]) / 2
    oy = (full_h - im.size[1]) / 2
    grid = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(grid)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for X in range(1, cols - 1):
        for Y in range(1, nrows - 1):
            cx = 54 * X + 36 - ox
            cy = 72 * Y + 36 + (36 if X % 2 == 0 else 0) - oy
            pts = [(cx + 36 * math.cos(math.radians(a)),
                    cy + 36 * math.sin(math.radians(a)))
                   for a in range(0, 360, 60)]
            d.polygon(pts, outline=(255, 255, 255, 110))
            label = f"{X},{Y}"
            w = d.textlength(label, font=font)
            d.text((cx - w / 2, cy + 12), label, font=font,
                   fill=(255, 255, 160, 235), stroke_width=2,
                   stroke_fill=(0, 0, 0, 200))
    Image.alpha_composite(im, grid).convert("RGB").save(out_path)


if __name__ == "__main__":
    overlay(*sys.argv[1:4])
