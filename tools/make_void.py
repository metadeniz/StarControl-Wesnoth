#!/usr/bin/env python3
"""Draw the void (Yv): a region with no stars at all, black inside, with a
soft, wavy rim of pale blue where it meets space.

    tools/make_void.py [--out .] [--wesnoth-data /usr/share/games/wesnoth/1.16/data]

Writes images/terrain/sc/void/*.png and terrain/void.cfg.

The void's outline is drawn like the badlands' banks (make_art.py): every
void hex, and every hex next to one, draws its piece of a smooth field over
its own and its neighbours' centres, and the void is where the field is
positive. Two hexes agree on the field along the edge they share, so the
outline runs on from hex to hex, rounded: one void hex is a disc, a row of
them a sausage, a block a rounded blob. The rim's swirls repeat exactly
from one hex to the next (lattice noise), so they have no seams either.
One image per pattern of void neighbours, picked by terrain/void.cfg.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

import make_art
from make_art import (BANK_PAD, BANK_DIRS, HEX, _BankGeometry, _smoothstep, bank_code,
                      bank_patterns, hex_mask, lattice_noise)

LAYER = -200              # over every gas cloud and bank, under planets and asteroids
BLACK = (1, 1, 4)
RIM = (150, 170, 215)      # the swirls
GLOW = (55, 70, 115)       # the haze under them
RIM_WIDTH = 7.0            # px either side of the outline
SEED = 909


def void_layer(f, swirl, mask):
    gy, gx = np.gradient(f)
    d = f / np.maximum(np.sqrt(gx * gx + gy * gy), 1e-4)    # ~ px inside the void
    p = BANK_PAD
    d = d[p:-p, p:-p]
    rgb = np.zeros(d.shape + (3,), np.float32)
    a = np.zeros(d.shape, np.float32)

    def over(colour, alpha):
        nonlocal rgb, a
        alpha = np.clip(alpha, 0, 1)
        out_a = alpha + a * (1 - alpha)
        rgb = (np.array(colour, np.float32) * alpha[..., None] + rgb * (a * (1 - alpha))[..., None]) \
            / np.maximum(out_a, 1e-6)[..., None]
        a = out_a

    # black from just inside the outline in
    over(BLACK, _smoothstep((d + 1.0) / 5.0))
    # the rim: a band across the outline, wobbling in and out with the swirls
    shift = 2.5 * swirl[1]
    band = np.exp(-(((d + shift) / RIM_WIDTH) ** 2))
    over(GLOW, 0.45 * band)
    lines = (0.5 + 0.5 * np.cos(np.pi * (2.2 * swirl[0] + 0.12 * d))) ** 5
    over(RIM, 0.95 * band * lines)
    img = np.dstack([rgb, a * 255 * mask])
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--wesnoth-data", default="/usr/share/games/wesnoth/1.16/data")
    args = ap.parse_args()
    mask = hex_mask(args.wesnoth_data)
    make_art.hex_mask_cache = mask
    rng = np.random.default_rng(SEED)
    # two seamless fields: one the swirl lines follow, one that wobbles the band
    swirl = (lattice_noise(rng, max_k=5), lattice_noise(rng, max_k=3))
    geo = _BankGeometry()

    img_dir = os.path.join(args.out, "images/terrain/sc/void")
    os.makedirs(img_dir, exist_ok=True)
    rules = []
    for centre, neighbours in bank_patterns():
        code = bank_code(centre, neighbours)
        void_layer(geo.field(centre, neighbours), swirl, mask).save(os.path.join(img_dir, code + ".png"))
        kinds = ["Yv" if v else "!,Yv" for v in neighbours]
        rules.append("{SC_VOID_EDGE sc/void/%s (%s) %s}" % (
            code, "Yv" if centre else "!,Yv", " ".join(f"({k})" for k in kinds)))

    with open(os.path.join(args.out, "terrain/void.cfg"), "w") as f:
        f.write("""#textdomain wesnoth-Star_Control_TC
# The void (Yv): its black and its rim, one image per pattern of void
# neighbours. Written by tools/make_void.py: don't edit by hand.

#define SC_VOID_EDGE IMAGE C N NE SE S SW NW
    [terrain_graphics]
        map="
,  2
7,   3
,  1
6,   4
,  5"
        [tile]
            pos=1
            type={C}
            set_no_flag=sc_void_edge
            [image]
                name={IMAGE}.png
                layer=%d
            [/image]
        [/tile]
        [tile]
            pos=2
            type={N}
        [/tile]
        [tile]
            pos=3
            type={NE}
        [/tile]
        [tile]
            pos=4
            type={SE}
        [/tile]
        [tile]
            pos=5
            type={S}
        [/tile]
        [tile]
            pos=6
            type={SW}
        [/tile]
        [tile]
            pos=7
            type={NW}
        [/tile]
    [/terrain_graphics]
#enddef

""" % LAYER)
        f.write("\n".join(rules) + "\n\n#undef SC_VOID_EDGE\n")
    print(f"{len(rules)} void images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
