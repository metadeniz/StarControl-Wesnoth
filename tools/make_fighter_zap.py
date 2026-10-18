"""Ur-Quan fighter laser strafing (original art).

The swarm's fighters circle the target and fire short laser bolts into
it from all sides. Each frame shows a few thin bolts streaking in toward
the centre, with a bright spark where each one strikes the hull. The
bolts come from fixed angles all round, so the halo reads right whatever
direction the attack comes from, and it is drawn on the target hex.
"""

import math

import numpy as np
from PIL import Image

W, H = 64, 64           # final image size
SS = 4                  # supersampling
CENTRE = (W / 2, H / 2)
FRAMES = 6
OUT = "images/halo/sc/fighter-zap-{}.png"

# (frame, angle in degrees, distance of the strike point from the centre)
# Two or three bolts per frame, never two from the same side in a row.
BOLTS = [
    (0, 200, 6), (0, 340, 9),
    (1, 80, 7), (1, 250, 10), (1, 20, 4),
    (2, 140, 8), (2, 300, 5),
    (3, 30, 9), (3, 180, 6), (3, 270, 8),
    (4, 110, 5), (4, 320, 7),
    (5, 230, 9), (5, 60, 6),
]
BOLT_LEN = 13.0
CORE = (255, 255, 225)
GLOW = (255, 190, 60)


def _layer(frame):
    glow = np.zeros((H * SS, W * SS), np.float32)
    core = np.zeros((H * SS, W * SS), np.float32)
    yy, xx = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32) / SS
    for f, ang, dist in BOLTS:
        if f != frame:
            continue
        a = math.radians(ang)
        ux, uy = math.cos(a), -math.sin(a)
        tip = (CENTRE[0] + ux * dist, CENTRE[1] + uy * dist)
        tail = (tip[0] + ux * BOLT_LEN, tip[1] + uy * BOLT_LEN)
        # distance from every pixel to the bolt segment
        px, py = xx - tail[0], yy - tail[1]
        dx, dy = tip[0] - tail[0], tip[1] - tail[1]
        t = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.hypot(px - t * dx, py - t * dy)
        fade = 0.35 + 0.65 * t                      # brighter toward the tip
        core = np.maximum(core, np.clip(1.1 - d / 0.7, 0, 1) * fade)
        glow = np.maximum(glow, np.clip(1 - d / 2.2, 0, 1) * fade * 0.8)
        # spark where the bolt strikes
        r = np.hypot(xx - tip[0], yy - tip[1])
        core = np.maximum(core, np.clip(1.2 - r / 1.6, 0, 1))
        glow = np.maximum(glow, np.clip(1 - r / 4.5, 0, 1))
    rgb = np.zeros((H * SS, W * SS, 3), np.float32)
    for i in range(3):
        rgb[..., i] = GLOW[i] * glow * (1 - core) + CORE[i] * core
    alpha = np.clip(np.maximum(glow, core), 0, 1) * 255
    arr = np.dstack([np.clip(rgb / np.maximum(np.maximum(glow, core), 1e-3)[..., None], 0, 255), alpha])
    big = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return big.resize((W, H), Image.LANCZOS)


def main():
    for frame in range(FRAMES):
        _layer(frame).save(OUT.format(frame + 1))


if __name__ == "__main__":
    main()
