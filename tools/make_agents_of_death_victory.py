"""Agents of Death victory: a Kohr-Ah standing over its pit of bones.

The picture is the Kohr-Ah's animated HD comm screen from the UQM MegaMod
content (addons/mm-hd/comm/kohrah: kohrah-000.png, 972x428, and 48 overlay
frames placed by kohrah.ani). The space behind it is swapped for the purple
nebula of the HD Game Over screen
(addons/mm-hd/cutscene/gameover/gameover-001.png), the same painting at
1280x564 with a richer starfield.

The Game Over painting is laid over the comm screen with the affine
transform that registers the two (WARP, found once with OpenCV's ECC
alignment). Space in the comm screen is what is very dark once the stars are
median-filtered away; it takes the nebula. Where the two paintings differ
(their arms are posed a little differently) the comm screen's space would
show the Game Over painting's arm, so those spots are filled from the
surrounding nebula instead. Each overlay frame is laid on the comm screen
and given the nebula the same way, so a claw moves in front of the new stars.

Writes images/story/sc/agents-of-death-victory/: 00.png, the whole
picture, and NN.png, overlay frame NN cut from the finished picture with that
frame laid on it, plus NN-rest.png for each group of overlay frames (the
eyes, the lights, the feelers, each claw): the same spot of 00.png, which
puts the group back at rest. Each is clear outside the pixels its group
changes. Frames 1-6 (a captive creature on a screen)
are left out. sc.victory_picture in lua/sc.lua plays them on a story screen;
its KOHRAH_ANIMATIONS table lists the groups by their frame numbers and
places.

Run from the repository root:
    python3 tools/make_agents_of_death_victory.py path/to/UQM-MegaMod-Content
"""

import os
import sys

import numpy as np
from PIL import Image, ImageFilter

COMM = "addons/mm-hd/comm/kohrah"
GAMEOVER = "addons/mm-hd/cutscene/gameover/gameover-001.png"
OUT = "images/story/sc/agents-of-death-victory"
SKIP = range(1, 7)  # the captive creature
# comm-screen (x, y) -> Game Over (x, y): x' = a x + b y + c, y' = d x + e y + f
WARP = (1.3162644, 0.0001362, 0.2684766, 0.0001230, 1.3151064, -0.1744464)
COMM_SPACE = 22     # median-filtered brightness below this is space in the comm screen
GAMEOVER_SPACE = 45  # ... and in the Game Over painting


def space(img, size, threshold):
    """Dark areas of img, with small specks (stars, crevices) removed."""
    grey = img.convert("L").filter(ImageFilter.MedianFilter(size))
    mask = grey.point(lambda v: 255 if v < threshold else 0)
    return mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))


def box_blur(a, r):
    """Mean over a (2r+1)-pixel square, edges clamped; a is (h, w) or (h, w, c)."""
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
        a = (np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
             - np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)) / (2 * r + 1)
    return a


def fill(img, holes):
    """Fill the holes from their surroundings: each hole pixel takes the mean
    of the known pixels around it, in the smallest neighbourhood that has
    enough of them."""
    a = np.asarray(img).astype(float)
    known = (np.asarray(holes) == 0).astype(float)
    out = a.copy()
    todo = known == 0
    for r in (2, 4, 8, 16, 32, 64):
        w = box_blur(known, r)
        guess = box_blur(a * known[..., None], r) / np.maximum(w, 1e-6)[..., None]
        take = todo & (w > 0.1)
        out[take] = guess[take]
        todo &= ~take
    return Image.fromarray(out.round().clip(0, 255).astype(np.uint8))


def overlays(uqm):
    """The comm screen's overlay frames: {number: (image, (x, y))}."""
    with open(os.path.join(uqm, COMM, "kohrah.ani")) as ani:
        rows = [line.split() for line in ani if line.strip()]
    frames = {}
    for i, row in enumerate(rows[1:], 1):
        if i not in SKIP:
            img = Image.open(os.path.join(uqm, COMM, row[0])).convert("RGBA")
            frames[i] = (img, (-int(row[3]), -int(row[4])))
    return frames


def main(uqm):
    comm = Image.open(os.path.join(uqm, COMM, "kohrah-000.png")).convert("RGBA")
    gameover = Image.open(os.path.join(uqm, GAMEOVER)).convert("RGB")
    frames = overlays(uqm)
    full = {0: comm.convert("RGB")}
    for i, (img, at) in frames.items():
        pic = comm.copy()
        pic.alpha_composite(img, at)
        full[i] = pic.convert("RGB")
    # The nebula, with every spot that any frame shows as space filled.
    nebula = gameover.transform(comm.size, Image.AFFINE, WARP, Image.BICUBIC)
    nebula_space = np.asarray(space(nebula, 9, GAMEOVER_SPACE)) > 0
    spaces = {i: np.asarray(space(pic, 7, COMM_SPACE)) > 0 for i, pic in full.items()}
    holes = np.logical_or.reduce(list(spaces.values())) & ~nebula_space
    holes = Image.fromarray((holes * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    nebula = np.asarray(fill(nebula, holes)).astype(float)
    os.makedirs(OUT, exist_ok=True)
    for i, pic in full.items():
        # A soft edge between the painting and the space behind it.
        edge = Image.fromarray((spaces[i] * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
        edge = np.asarray(edge.filter(ImageFilter.GaussianBlur(1.5)))[..., None] / 255.0
        pic = np.asarray(pic) * (1 - edge) + nebula * edge
        full[i] = Image.fromarray(pic.round().astype(np.uint8))
    full[0].save(f"{OUT}/00.png", optimize=True)
    # A group's frames share a box. Each is cut out where any frame of the
    # group differs from the picture at rest, and is clear elsewhere, so it
    # replaces the group's last frame and leaves neighbouring groups alone.
    groups = {}
    for i, (img, (x, y)) in frames.items():
        groups.setdefault((x, y, x + img.width, y + img.height), []).append(i)
    for box, numbers in groups.items():
        rest = np.asarray(full[0].crop(box)).astype(int)
        cut = np.zeros(rest.shape[:2], bool)
        for i in numbers:
            cut |= (np.abs(np.asarray(full[i].crop(box)).astype(int) - rest).sum(2) > 0)
        alpha = Image.fromarray((cut * 255).astype(np.uint8))
        for name, i in [(f"{numbers[0]:02d}-rest", 0)] + [(f"{i:02d}", i) for i in numbers]:
            patch = full[i].crop(box).convert("RGBA")
            patch.putalpha(alpha)
            patch.save(f"{OUT}/{name}.png", optimize=True)
        print(f"frames {numbers[0]}-{numbers[-1]} at {box[0]},{box[1]}")
    print(OUT)


if __name__ == "__main__":
    main(sys.argv[1])
