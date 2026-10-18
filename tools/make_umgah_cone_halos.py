"""Umgah antimatter cone, held for a whole attack, and its hit flash.

The cone is shown as an item halo on the attacking Drone's hex for the
whole fight (see sc.cone_hold in lua/sc.lua), so it stays lit between
strikes instead of flashing once per strike. A halo is drawn centred on
its hex and cannot be flipped, so this bakes images per facing with the
cone already where the attack animation used to put it: 0.55 of the way
to the target hex.

The UQM cone sprite is a sparse spray of dim speckles that all but
vanishes against the starfield, so it is brightened here: the speckles
are pushed to full brightness, the spray is thickened, and a soft violet
glow fills the cone underneath. FRAMES shimmer frames recolour the
speckles so the cone crackles while it is held.

Each strike that hits ends in an antimatter burst on the target (original
art): a white flash, a violet shock ring and a spray of prismatic sparks,
bigger and longer than the generic blast.

Run from the repository root: python3 tools/make_umgah_cone_halos.py
"""

import colorsys
import math

import numpy as np
from PIL import Image, ImageFilter

SIZE = 144          # two hexes wide, centred on the Drone's hex
OFFSET = 0.55       # the old cone_frame's offset
FRAMES = 4          # shimmer frames of the held cone
GLOW = (190, 150, 255)
# (direction, source image, flip horizontally, flip vertically, hex step)
FACINGS = [
    ("n", "n", False, False, (0, -72)),
    ("ne", "ne", False, False, (54, -36)),
    ("se", "ne", False, True, (54, 36)),
    ("s", "n", False, True, (0, 72)),
    ("sw", "ne", True, True, (-54, 36)),
    ("nw", "ne", True, False, (-54, -36)),
]

HIT_SIZE = 96
HIT_FRAMES = 8
SS = 4              # supersampling for the hit


def bright_cone(cone, frame):
    """The cone sprite with speckles at full brightness, thickened, over a glow."""
    rng = np.random.default_rng(1000 + frame)
    a = np.array(cone, np.float32) / 255
    alpha = a[..., 3]
    # where the spray is: the speckles, smeared into a solid shape
    body = np.array(Image.fromarray((alpha * 255).astype(np.uint8))
                    .filter(ImageFilter.MaxFilter(3))
                    .filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
    body = np.clip(body * 1.8, 0, 1)
    h, w = alpha.shape
    # speckles: the original ones plus as many again scattered through the body
    speck = (alpha > 0.05) | (rng.random((h, w)) < body * 0.3)
    hue = rng.random((h, w))
    rgb = np.zeros((h, w, 3), np.float32)
    for y, x in zip(*np.nonzero(speck)):
        rgb[y, x] = colorsys.hsv_to_rgb(hue[y, x], 0.7, 1.0)
    speck_a = speck * np.clip(0.75 + 0.25 * rng.random((h, w)), 0, 1)
    glow = np.array(Image.fromarray((body * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    glow_a = np.clip(glow * 0.55, 0, 0.55)
    out_a = speck_a + glow_a * (1 - speck_a)
    out_rgb = (rgb * speck_a[..., None]
               + np.array(GLOW, np.float32)[None, None] / 255 * (glow_a * (1 - speck_a))[..., None])
    out_rgb = np.where(out_a[..., None] > 0, out_rgb / np.maximum(out_a, 1e-6)[..., None], 0)
    img = np.dstack([out_rgb, out_a]) * 255
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA")


def build_cones():
    for name, src, hflip, vflip, (dx, dy) in FACINGS:
        base = Image.open(f"images/projectiles/sc/cone-{src}.png").convert("RGBA")
        # room for the glow round the edge
        pad = Image.new("RGBA", (base.width + 12, base.height + 12))
        pad.alpha_composite(base, (6, 6))
        for f in range(FRAMES):
            cone = bright_cone(pad, f)
            if hflip:
                cone = cone.transpose(Image.FLIP_LEFT_RIGHT)
            if vflip:
                cone = cone.transpose(Image.FLIP_TOP_BOTTOM)
            cx = SIZE / 2 + OFFSET * dx
            cy = SIZE / 2 + OFFSET * dy
            out = Image.new("RGBA", (SIZE, SIZE))
            out.alpha_composite(cone, (round(cx - cone.width / 2), round(cy - cone.height / 2)))
            out.save(f"images/halo/sc/umgah-cone-{name}-{f + 1}.png")


def build_hit():
    n = HIT_SIZE * SS
    c = n / 2
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.hypot(xx - c, yy - c) / SS
    ang = np.arctan2(yy - c, xx - c)
    rng = np.random.default_rng(7)
    sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.45, 1.0), rng.random(), rng.uniform(1.4, 2.4))
              for _ in range(46)]
    for f in range(HIT_FRAMES):
        t = (f + 0.5) / HIT_FRAMES
        rgb = np.zeros((n, n, 3), np.float32)
        a = np.zeros((n, n), np.float32)

        def add(colour, alpha):
            nonlocal rgb, a
            alpha = np.clip(alpha, 0, 1)
            under = a * (1 - alpha)
            total = alpha + under
            rgb = ((np.array(colour, np.float32) / 255 * alpha[..., None] + rgb * under[..., None])
                   / np.maximum(total, 1e-6)[..., None])
            a = total

        # violet haze
        add((170, 110, 255), np.exp(-(r / (10 + 18 * t)) ** 2) * 0.7 * (1 - t))
        # shock ring
        ring_r = 5 + 34 * t ** 0.7
        add((215, 190, 255), np.exp(-((r - ring_r) / (1.6 + 2 * t)) ** 2) * (1 - t) ** 1.2)
        # flare spikes, early on
        if t < 0.6:
            spikes = np.abs(np.cos(3 * ang + 0.4)) ** 40 + np.abs(np.cos(2 * ang - 0.9)) ** 60
            add((235, 225, 255), spikes * np.exp(-r / (6 + 14 * t)) * (1 - t / 0.6))
        # prismatic sparks flying out
        for th, speed, hue, size in sparks:
            d = speed * 40 * t ** 0.8
            sx, sy = c + math.cos(th) * d * SS, c + math.sin(th) * d * SS
            dist = np.hypot(xx - sx, yy - sy) / SS
            col = tuple(v * 255 for v in colorsys.hsv_to_rgb(hue, 0.6, 1.0))
            add(col, np.clip(1.2 - dist / size, 0, 1) * (1 - t ** 1.5))
        # white-hot core
        core_r = 3 + 9 * math.sin(math.pi * min(t * 1.6, 1)) if t < 0.62 else 3 * (1 - t) / 0.38
        add((255, 255, 255), np.clip(1.3 - r / max(core_r, 0.3), 0, 1) * min(1, 1.6 * (1 - t)))
        img = Image.fromarray(np.clip(np.dstack([rgb, a]) * 255, 0, 255).astype(np.uint8), "RGBA")
        img.resize((HIT_SIZE, HIT_SIZE), Image.LANCZOS).save(f"images/halo/sc/antimatter-hit-{f + 1}.png")


def main():
    build_cones()
    build_hit()


if __name__ == "__main__":
    main()
