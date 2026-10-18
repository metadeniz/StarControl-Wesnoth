"""Umgah antimatter cone, held for a whole attack.

The cone is shown as an item halo on the attacking Drone's hex for the
whole fight (see sc.cone_hold in lua/sc.lua), so it stays lit between
strikes instead of flashing once per strike. A halo is drawn centred on
its hex and cannot be flipped, so this bakes one image per Drone level and
facing, with the narrow end of the cone on the ship's nose. The nose is
found from the ship sprite of that level, since bigger hulls reach further.

Run from the repository root: python3 tools/make_umgah_cone_halos.py
"""

import math

import numpy as np
from PIL import Image

SIZE = 180          # two and a half hexes wide, centred on the Drone's hex
LEVELS = (1, 2, 3)
# (direction, source image, flip horizontally, flip vertically, hex step)
FACINGS = [
    ("n", "n", False, False, (0, -72)),
    ("ne", "ne", False, False, (54, -36)),
    ("se", "ne", False, True, (54, 36)),
    ("s", "n", False, True, (0, 72)),
    ("sw", "ne", True, True, (-54, 36)),
    ("nw", "ne", True, False, (-54, -36)),
]


def opaque_points(img, threshold):
    """Pixel centres of img where alpha is above threshold, as (x, y) arrays."""
    ys, xs = np.nonzero(np.array(img)[..., 3] > threshold)
    return xs + 0.5, ys + 0.5


def nose_distance(level, facing, unit):
    """How far the ship's nose sits from the hex centre along unit."""
    ship = Image.open(f"images/units/sc/umgah-drone-l{level}-{facing}.png").convert("RGBA")
    xs, ys = opaque_points(ship, 60)
    return float(((xs - ship.width / 2) * unit[0] + (ys - ship.height / 2) * unit[1]).max())


def build_cones():
    for level in LEVELS:
        for name, src, hflip, vflip, (dx, dy) in FACINGS:
            unit = (dx / math.hypot(dx, dy), dy / math.hypot(dx, dy))
            nose = nose_distance(level, name, unit)
            cone = Image.open(f"images/projectiles/sc/cone-{src}.png").convert("RGBA")
            if hflip:
                cone = cone.transpose(Image.FLIP_LEFT_RIGHT)
            if vflip:
                cone = cone.transpose(Image.FLIP_TOP_BOTTOM)
            # the cone's narrow end: its pixels furthest back along the facing
            xs, ys = opaque_points(cone, 0)
            along = xs * unit[0] + ys * unit[1]
            back = along <= along.min() + 3
            apex = (xs[back].mean(), ys[back].mean())
            x = SIZE / 2 + unit[0] * nose - apex[0]
            y = SIZE / 2 + unit[1] * nose - apex[1]
            out = Image.new("RGBA", (SIZE, SIZE))
            out.alpha_composite(cone, (round(x), round(y)))
            out.save(f"images/halo/sc/umgah-cone-l{level}-{name}.png")


def main():
    build_cones()


if __name__ == "__main__":
    main()
