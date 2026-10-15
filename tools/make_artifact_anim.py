"""Precursor artifact found: the Star Control II device screen booting up.

Cuts the frames of a short clip (100x66, 30 fps: the device on a starfield,
its display filling with Precursor glyphs) out of their background, at
15 fps, into images/halo/sc/artifact-NNN.png, plus a few frames fading the
finished screen out. sc.check_artifact in lua/sc.lua plays them as an item
halo on the planet where the artifact was found.

The device never moves, so one alpha mask serves every frame: the part of
the clip's median frame that is not dark background connected to the
border, keeping only the largest piece (so stray stars drop out), with the
outermost two pixels faded by brightness for a soft rim.

Needs ffmpeg. Run from the repository root:
    python3 tools/make_artifact_anim.py path/to/clip.mp4
"""

import collections
import glob
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

OUT = "images/halo/sc/artifact-{:03d}.png"
STEP = 2            # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)


def flood(passable, seeds):
    h, w = passable.shape
    seen = np.zeros((h, w), bool)
    q = collections.deque(seeds)
    while q:
        y, x = q.popleft()
        if 0 <= y < h and 0 <= x < w and passable[y, x] and not seen[y, x]:
            seen[y, x] = True
            q.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return seen


def erode(a):
    b = a.copy()
    b[1:] &= a[:-1]
    b[:-1] &= a[1:]
    b[:, 1:] &= a[:, :-1]
    b[:, :-1] &= a[:, 1:]
    return b


def alpha_mask(frames):
    med = np.median(np.stack(frames), 0)
    h, w = med.shape[:2]
    dark = (med[..., 2] < 45) & (med.sum(-1) < 120)
    border = [(y, x) for x in range(w) for y in (0, h - 1)] + \
             [(y, x) for y in range(h) for x in (0, w - 1)]
    fg = ~flood(dark, border)
    # largest connected piece of foreground
    best, todo = None, fg.copy()
    while todo.any():
        y, x = np.argwhere(todo)[0]
        piece = flood(todo, [(y, x)])
        todo &= ~piece
        if best is None or piece.sum() > best.sum():
            best = piece
    core = erode(erode(best))
    rim = np.clip((med[..., 2] + med.sum(-1) / 3) / 140, 0, 1)
    return np.where(core, 1.0, np.where(best, rim, 0.0))


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [np.asarray(Image.open(p).convert("RGB")) for p in paths]
    alpha = alpha_mask([f.astype(int) for f in frames])
    for old in glob.glob(OUT.replace("{:03d}", "*")):
        os.remove(old)
    kept = frames[::STEP]
    n = 0
    for rgb in kept:
        n += 1
        Image.fromarray(np.dstack([rgb, (alpha * 255).astype("uint8")]), "RGBA").save(OUT.format(n))
    for f in FADE:
        n += 1
        Image.fromarray(np.dstack([kept[-1], (alpha * f * 255).astype("uint8")]), "RGBA").save(OUT.format(n))
    print(f"{n} frames ({len(kept)} + {len(FADE)} fading)")


if __name__ == "__main__":
    main(sys.argv[1])
