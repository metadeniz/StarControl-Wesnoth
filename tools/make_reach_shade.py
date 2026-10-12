#!/usr/bin/env python3
"""Write reach/images/terrain/darken.png: the shade over unreachable hexes.

When a ship is selected, Wesnoth draws terrain/darken.png over every hex it
cannot reach this turn. The core image is thin dark stripes with clear rows
between them, made for grassland; on our starfield most stars are single
pixels, so a star on a clear row stays fully bright and the out-of-range
space hardly looks different. This shade is solid instead, so every star
dims by the same amount, and it is a deep blue-grey veil rather than black,
so dimmed space still reads as space, not as a hole in the map.

_main.cfg adds reach/ as a binary path only while the Star Control era is
played, so other eras keep the core stripes.

    tools/make_reach_shade.py [--wesnoth-data /usr/share/games/wesnoth/1.16/data]
"""

import argparse
import os

import numpy as np
from PIL import Image

# The veil's colour, and how much of what lies under it still shows
COLOUR = (3, 4, 9)
SHOW = 0.33


def build(wdata, out):
    core = Image.open(os.path.join(wdata, "core/images/terrain/darken.png")).convert("RGBA")
    inside = np.array(core)[:, :, 3] > 0     # the core shade's hex shape
    img = np.zeros(inside.shape + (4,), np.uint8)
    img[inside] = COLOUR + (round(255 * (1 - SHOW)),)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(img, "RGBA").save(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--wesnoth-data", default="/usr/share/games/wesnoth/1.16/data")
    ap.add_argument("--out", default=os.path.join(here, "reach/images/terrain/darken.png"))
    args = ap.parse_args()
    build(args.wesnoth_data, args.out)
