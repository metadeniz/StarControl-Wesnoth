"""Kohr-Ah F.R.I.E.D. plumes (original art).

Three flame plumes fanning out from the ship's bow, drawn as a short
animation: two frames of the flames shooting out, then two frames of them
flickering at full length. Each image points north with the plumes' base
at the bottom centre, so the attack anim can place them in front of the
ship with a fixed offset.
"""

import math

import numpy as np
from PIL import Image, ImageFilter

W, H = 88, 88           # final image size
SS = 4                  # supersampling
ORIGIN = (W / 2, H - 3)
PLUMES = [(-25.0, 0.88), (0.0, 1.0), (25.0, 0.88)]   # (angle, relative length)
LENGTH = 62.0
WIDTH = 9.5             # half-width at the widest point
FRAMES = [0.45, 0.78, 1.0, 1.0]   # plume length of each frame

# intensity -> RGB, from the cool edge to the white-hot core
PALETTE = [
    (0.00, (120, 10, 0)),
    (0.25, (215, 45, 5)),
    (0.50, (255, 130, 20)),
    (0.75, (255, 220, 90)),
    (1.00, (255, 255, 235)),
]


def _palette(v):
    xs = [p[0] for p in PALETTE]
    return np.stack([np.interp(v, xs, [p[1][i] for p in PALETTE]) for i in range(3)], -1)


def _noise(rng, h, w, cell):
    """Smooth value noise in [-1, 1]."""
    gh, gw = h // cell + 2, w // cell + 2
    g = Image.fromarray(((rng.random((gh, gw)) * 255)).astype(np.uint8))
    g = g.resize((gw * cell, gh * cell), Image.BICUBIC).crop((0, 0, w, h))
    return np.asarray(g, dtype=np.float32) / 127.5 - 1.0


def frame(rng, grow):
    h, w = H * SS, W * SS
    y, x = np.mgrid[0:h, 0:w].astype(np.float32) / SS
    ox, oy = ORIGIN
    heat = np.zeros((h, w), np.float32)
    wobble = _noise(rng, h, w, 9 * SS) * 0.35 + _noise(rng, h, w, 4 * SS) * 0.2
    for angle, rel in PLUMES:
        a = math.radians(angle + rng.uniform(-2.5, 2.5))
        ux, uy = math.sin(a), -math.cos(a)          # along the plume
        dx, dy = x - ox, y - oy
        t = dx * ux + dy * uy
        d = np.abs(dx * uy - dy * ux)
        length = LENGTH * rel * grow
        s = np.clip(t / length, 0, None)
        # narrow at the bow, fattest two thirds out, rounded tip
        prof = WIDTH * (0.25 + 0.75 * np.sin(np.pi * np.clip(s, 0, 1) ** 0.75 * 0.92))
        prof *= 0.8 + 0.2 * grow
        r = d / np.maximum(prof, 0.1)
        inside = (t > 0) & (s < 1.15)
        v = (1.0 - r + wobble * (0.3 + s)) * (1.0 - np.clip((s - 0.75) / 0.4, 0, 1))
        v = np.where(inside, v, 0.0)
        heat = np.maximum(heat, v)
    heat = np.clip(heat, 0, 1)
    rgb = _palette(heat)
    alpha = np.clip(heat * 3.0, 0, 1) * 255
    img = Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")
    img = img.resize((W, H), Image.LANCZOS)
    glow = Image.new("RGBA", img.size, (255, 90, 10, 0))
    glow.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(3)).point(lambda v: v * 0.7))
    glow.alpha_composite(img)
    return glow


def build(out, save, rotated, diag, seed=1990):
    rng = np.random.default_rng(seed + 31)
    for i, grow in enumerate(FRAMES, 1):
        img = frame(rng, grow)
        save(img, out, f"images/projectiles/sc/fried-plumes-{i}-n.png", False)
        save(rotated(img, diag), out, f"images/projectiles/sc/fried-plumes-{i}-ne.png", False)
