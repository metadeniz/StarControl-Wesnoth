#!/usr/bin/env python3
"""Draw the laser and lightning beams (original art).

Star Control II's lasers are not shots that fly: for one battle frame UQM
draws a line from the ship to the end of the laser's range, or to whatever
it hits. Here a beam runs from the ship's nose to the centre of the target
hex (or from its emitters, where SC2 has them away from the nose), so each
ship sprite gets beams of its own length. SC_BEAM_ANIM centres them halfway
between (SC_BEAM_MID_* in utils/beams.cfg) and flips them for the other
facings.

Writes images/projectiles/sc/beams/<ship sprite>-<beam>-<k>-<n|ne>.png and
utils/beams.cfg.
Run it after make_art.py, which draws the ship sprites.

Usage:
    make_beams.py --out <add-on dir>
"""

import argparse
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from make_noses import STEP, nose

# The NE facing, as an angle from north (neighbouring hexes are 54 px across
# and 36 px up).
DIAG = math.atan2(54, 36)
SS = 4  # supersampling


def rgb15(r, g, b):
    return tuple(round(v * 255 / 31) for v in (r, g, b))


# ship sprite stem (without -l<level>) -> (beam, colours, frames, beams side by
# side as fractions of the hull's width from its centre, line width, where
# they start as a fraction of the hull's length ahead of its centre, or None
# for the nose)
BEAMS = {
    # vux.c: one green laser to LASER_BASE, the longest in the game
    "vux-intruder": ("laser", [rgb15(0x0A, 0x1F, 0x0A)], 2, [0.0], 2.5, None),
    # mmrnmhrm.c: twin red lasers from the red emitters on the wingtips,
    # WING_OFFS (48 HD px) either side of the hull, starting at the
    # emitters' tips (row 43 of the 84 px HD sprite, 1 px ahead of its middle)
    "mmrnmhrm-xform": ("laser", [rgb15(0x1F, 0x0A, 0x0A)], 2, [-48 / 104, 48 / 104], 2.0, 1 / 84),
    # chmmr.c: the megawatt laser cycles its colour every frame (cycle_array)
    "chmmr-avatar": ("laser", [rgb15(0x17, 0, 0), rgb15(0x1F, 0x03, 0), rgb15(0x1F, 0x11, 0),
                               rgb15(0x1F, 0x03, 0)], 4, [0.0], 3.5, None),
    # human.c: point-defense lasers, white zaps from the middle of the ship
    "earthling-cruiser": ("laser", [rgb15(0x1F, 0x1F, 0x1F)], 2, [0.0], 2.0, 0.0),
    # ...and the Precursor ship's, in red
    "precursor-flagship": ("laser", [rgb15(0x1F, 0x05, 0x05)], 2, [0.0], 2.0, 0.0),
    # arilou.c: a yellow laser from the rim of the saucer
    "arilou-skiff": ("laser", [rgb15(0x1F, 0x1F, 0x0A)], 2, [0.0], 2.0, None),
    # slylandr.c: a crooked chain of short segments, each bolt white or one
    # of three blues
    "slylandro-probe": ("lightning", [rgb15(0x1F, 0x1F, 0x1F), rgb15(0x16, 0x17, 0x1F),
                                      rgb15(0x06, 0x07, 0x1F), rgb15(0, 0, 0x18)], 4, [0.0], 2.0, None),
}


# Beams that run on past the target's centre, as far as this fraction of the
# way to the next hex beyond it (the rest stop at its centre): the Chmmr's
# and the VUX's (the longest in SC2, LASER_BASE 150) go right through it.
REACH = {"chmmr-avatar": 1.45, "vux-intruder": 1.45}
# Twin beams that angle in to meet at the target's centre
CONVERGE = {"mmrnmhrm-xform"}
# Beams that start this fraction of the hull's length behind the nose: the
# Chmmr's emitter sits recessed between the two prongs of its bow
RECESS = {"chmmr-avatar": 0.07}

# Beams fired in quick bursts: an empty frame `<beam>-0` too, for the gaps
# between the shots (the Arilou's three zaps)
BURSTS = {"arilou-skiff"}

# ships whose sprites are not drawn per level, or not for every level
SPRITES = {"precursor-flagship": ["-l1"]}

# Sprites that look the same whichever way they face, with an emitter off
# their middle: their beams are drawn for each of the six directions, on a
# canvas centred on the ship, from the emitter (x, y px from the middle) to
# the centre of the next hex, for SC_FIXED_ZAP_ANIM.
# sprite -> (beam, colour, frames, emitter, line width)
FIXED = {
    # the Alliance Starbase's point defense, from the dome atop its saucer
    "alliance-starbase": ("zap", rgb15(0x1F, 0x1F, 0x1F), 2, (0, -21), 2.0),
}
HEXES = {"n": (0, -72), "ne": (54, -36), "se": (54, 36), "s": (0, 72), "sw": (-54, 36), "nw": (-54, -36)}


def draw_fixed(colour, start, end, width, dim):
    """A beam from `start` to `end` (px from the middle of the canvas)."""
    half = 80
    img = Image.new("RGBA", (2 * half * SS, 2 * half * SS), (0, 0, 0, 0))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    xy = [((half + x) * SS, (half + y) * SS) for x, y in (start, end)]
    k = 0.65 if dim else 1.0
    core = tuple(round(c + (255 - c) * 0.6) for c in colour)
    ImageDraw.Draw(glow).line(xy, fill=colour + (round(110 * k),), width=round(width * 3 * SS))
    d = ImageDraw.Draw(img)
    d.line(xy, fill=colour + (round(255 * k),), width=round(width * SS))
    d.line(xy, fill=core + (round(255 * k),), width=max(SS, round(width * SS / 3)))
    glow = glow.filter(ImageFilter.GaussianBlur(2 * SS))
    glow.alpha_composite(img)
    return glow.resize((2 * half, 2 * half), Image.LANCZOS)


def hull_axis(path, angle):
    """How far the hull's centre line sits to the side of the sprite's
    middle, facing `angle`: make_art.py centres it, so this is only the
    pixel or so that rounding leaves on the diagonals."""
    a = np.array(Image.open(path).convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a >= 128)
    dx, dy = xs + 0.5 - a.shape[1] / 2, ys + 0.5 - a.shape[0] / 2
    return float((dx * math.cos(angle) + dy * math.sin(angle)).mean())


def hull_size(path):
    alpha = Image.open(path).split()[3].point(lambda a: 255 if a >= 128 else 0)
    box = alpha.getbbox()
    return box[2] - box[0], box[3] - box[1]


def lightning_path(length, rng):
    """Points of a crooked bolt along the beam axis: (along, sideways)."""
    pts, along, side = [(-length / 2, 0.0)], -length / 2, 0.0
    while True:
        along += rng.uniform(4, 10)
        if along >= length / 2 - 3:
            break
        side = 0.5 * side + rng.uniform(-4.5, 4.5)
        pts.append((along, side))
    pts.append((length / 2, 0.0))
    return pts


def draw(kind, colour, length, laterals, width, angle, rng, dim, converge=False):
    """One beam frame, centred on the image, along `angle` (0 = north); with
    `converge`, side-by-side beams close in to meet at the far end."""
    ux, uy = math.sin(angle), -math.cos(angle)   # along the beam
    vx, vy = math.cos(angle), math.sin(angle)    # sideways
    strands = []
    for lat in laterals:
        pts = lightning_path(length, rng) if kind == "lightning" else [(-length / 2, 0.0), (length / 2, 0.0)]
        side = (lambda a: lat * (0.5 - a / length)) if converge else (lambda a: lat)
        strands.append([(a * ux + (s + side(a)) * vx, a * uy + (s + side(a)) * vy) for a, s in pts])
    half = max(max(abs(x), abs(y)) for strand in strands for x, y in strand) + 6
    size = 2 * math.ceil(half)
    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    centre = size * SS / 2
    k = 0.65 if dim else 1.0
    core = tuple(round(c + (255 - c) * 0.6) for c in colour)
    for strand in strands:
        xy = [(centre + x * SS, centre + y * SS) for x, y in strand]
        ImageDraw.Draw(glow).line(xy, fill=colour + (round(110 * k),), width=round(width * 3 * SS), joint="curve")
        d = ImageDraw.Draw(img)
        d.line(xy, fill=colour + (round(255 * k),), width=round(width * SS), joint="curve")
        d.line(xy, fill=core + (round(255 * k),), width=max(SS, round(width * SS / 3)), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(2 * SS))
    glow.alpha_composite(img)
    return glow.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="add-on directory")
    args = ap.parse_args()
    units = os.path.join(args.out, "images/units/sc")
    beams = os.path.join(args.out, "images/projectiles/sc/beams")
    os.makedirs(beams, exist_ok=True)
    n = 0
    lines = [
        "#textdomain wesnoth-Star_Control_TC",
        "# Generated by tools/make_beams.py: where each beam is centred, halfway",
        "# from where it starts to where it ends, as a fraction of the way to the target",
        "# (missile_offset), facing straight (n, s) and diagonally. Used by",
        "# SC_BEAM_ANIM.",
        "",
    ]
    for ship, (kind, colours, frames, laterals, width, start) in BEAMS.items():
        for suffix in SPRITES.get(ship, ["-l1", "-l2", "-l3"]):
            stem = f"{ship}{suffix}"
            w, h = hull_size(os.path.join(units, f"{stem}-n.png"))
            for facing, angle in (("n", 0.0), ("ne", DIAG)):
                path = os.path.join(units, f"{stem}-{facing}.png")
                if start is None:
                    frac = round(min(0.7, nose(path, facing) / STEP[facing]), 2)
                    frac -= RECESS.get(ship, 0) * h / STEP[facing]
                else:
                    frac = start * h / STEP[facing]
                reach = REACH.get(ship, 1.0)
                length = (reach - frac) * STEP[facing]
                name = "SC_BEAM_MID" if facing == "n" else "SC_BEAM_MID_DIAG"
                lines.append(f"#define {name}_{stem}\n{(reach + frac) / 2:.3f}#enddef")
                rng = random.Random(f"{stem}-{facing}")
                for k in range(frames):
                    if kind == "lightning":
                        colour, dim = rng.choice(colours), False
                    else:
                        colour, dim = colours[k % len(colours)], len(colours) == 1 and k % 2 == 1
                    side = hull_axis(path, angle)
                    img = draw(kind, colour, length, [lat * w + side for lat in laterals], width, angle, rng, dim,
                               ship in CONVERGE)
                    img.save(os.path.join(beams, f"{stem}-{kind}-{k + 1}-{facing}.png"), optimize=True)
                    n += 1
                if ship in BURSTS:
                    Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(os.path.join(beams, f"{stem}-{kind}-0-{facing}.png"))
                    n += 1
    for stem, (kind, colour, frames, start, width) in FIXED.items():
        for facing, end in HEXES.items():
            for k in range(frames):
                img = draw_fixed(colour, start, end, width, k % 2 == 1)
                img.save(os.path.join(beams, f"{stem}-{kind}-{k + 1}-{facing}.png"), optimize=True)
                n += 1
    with open(os.path.join(args.out, "utils/beams.cfg"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"ok: {n} beam frames")


if __name__ == "__main__":
    main()
