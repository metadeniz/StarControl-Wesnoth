#!/usr/bin/env python3
"""Draw the void (Yv): a region with no stars at all, black inside, with a
soft, wavy rim of pale blue where it meets space.

    tools/make_void.py [--out .] [--wesnoth-data /usr/share/games/wesnoth/1.16/data]

Writes images/terrain/sc/void/*.png and terrain/void.cfg.

The look is lifted from Dominion War Wesnoth's void() prototype
(tileset/src/imp_ideas.py, idea 9, VOY "Night"): the void hexes' shapes
blurred into a soft mask M (Gaussian, sigma 16 px), solid black where
M > 0.7, a rim band round M = 0.33 in (80, 95, 135), made wavy by noise.
That draws a whole map at once; here every void hex, and every hex next to
one, draws its own piece of the same mask, worked out from itself and its
six neighbours (a sigma of 16 px reaches no further), so the pieces join
up. The noise is lattice noise, which repeats exactly from one hex to the
next, in place of the prototype's fBm, so the rim has no seams.
One image per pattern of void neighbours, picked by terrain/void.cfg.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import make_art
from make_art import BANK_DIRS, BANK_OFFSETS, HEX, bank_code, bank_patterns, hex_mask, lattice_noise

LAYER = -200              # over every gas cloud and bank, under planets and asteroids
COLOUR = (80, 95, 135)     # the rim (Dominion War's void())
SIGMA = 16                 # px: how soft the outline is
SEED = 9
HEXV = [(18, 0), (54, 0), (72, 36), (54, 72), (18, 72), (0, 36)]
PAD = 3 * HEX // 2         # room round the hex for its neighbours and the blur


def gaussian_filter(a, sigma):
    """scipy.ndimage.gaussian_filter (mode reflect, truncate 4), in numpy."""
    r = int(4 * sigma + 0.5)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="symmetric"), k, "valid"), axis, a)
    return a


def void_mask(centre, neighbours):
    """The prototype's membership(): the void hexes filled in, then blurred.
    Returns M over the centre hex's 72x72 tile."""
    size = HEX + 2 * PAD
    im = Image.new("F", (size, size), 0.0)
    d = ImageDraw.Draw(im)
    spots = [(0, 0)] if centre else []
    spots += [BANK_OFFSETS[k] for k, v in zip(BANK_DIRS, neighbours) if v]
    for ox, oy in spots:
        d.polygon([(PAD + ox + vx, PAD + oy + vy) for vx, vy in HEXV], fill=1.0)
    m = gaussian_filter(np.asarray(im, np.float32), SIGMA)
    return np.clip(m[PAD:PAD + HEX, PAD:PAD + HEX], 0, 1)


def void_layer(m, noise, mask):
    """The prototype's void(), on one tile."""
    inner = np.clip((m - 0.35) / 0.35, 0, 1)
    rim = np.exp(-((m - 0.33) / 0.12) ** 2)
    ripple = 0.55 + 0.45 * np.sin(noise * 5)
    col = np.zeros(m.shape + (3,)) + np.array(COLOUR) * (rim * ripple)[..., None]
    a = np.clip(inner + rim * 0.75, 0, 1) * 255 * mask
    return Image.fromarray(np.dstack([np.clip(col, 0, 255), a]).astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--wesnoth-data", default="/usr/share/games/wesnoth/1.16/data")
    args = ap.parse_args()
    mask = hex_mask(args.wesnoth_data)
    make_art.hex_mask_cache = mask
    # seamless stand-in for the prototype's fBm (12 px, 2 octaves): waves down to ~13 px
    noise = lattice_noise(np.random.default_rng(SEED), max_k=4)

    img_dir = os.path.join(args.out, "images/terrain/sc/void")
    os.makedirs(img_dir, exist_ok=True)
    rules = []
    for centre, neighbours in bank_patterns():
        code = bank_code(centre, neighbours)
        void_layer(void_mask(centre, neighbours), noise, mask).save(os.path.join(img_dir, code + ".png"))
        kinds = ["Yv" if v else "!,Yv" for v in neighbours]
        rules.append("{SC_VOID_EDGE sc/void/%s (%s) %s}" % (
            code, "Yv" if centre else "!,Yv", " ".join(f"({k})" for k in kinds)))

    with open(os.path.join(args.out, "terrain/void.cfg"), "w") as f:
        f.write("""#textdomain wesnoth-Star_Control_Wesnoth
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
