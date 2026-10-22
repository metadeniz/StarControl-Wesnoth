"""Agents of Death victory: a Kohr-Ah standing over its pit of bones.

The picture is the Kohr-Ah's HD comm screen from the UQM MegaMod content
(addons/mm-hd/comm/kohrah/kohrah-000.png, 972x428). The space behind it is
swapped for the purple nebula of the HD Game Over screen
(addons/mm-hd/cutscene/gameover/gameover-001.png), the same painting at
1280x564 with a richer starfield.

The Game Over painting is laid over the comm screen with the affine
transform that registers the two (WARP, found once with OpenCV's ECC
alignment). Space in the comm screen is what is very dark once the stars are
median-filtered away; it takes the nebula. Where the two paintings differ
(their arms are posed a little differently) the comm screen's space would
show the Game Over painting's arm, so those spots are filled from the
surrounding nebula instead.

sc.victory_picture in lua/sc.lua shows the picture, resampled to the message
window's 500-pixel portrait width, when an Agents of Death side wins.

Run from the repository root:
    python3 tools/make_agents_of_death_victory.py path/to/UQM-MegaMod-Content
"""

import os
import sys

import numpy as np
from PIL import Image, ImageFilter

COMM = "addons/mm-hd/comm/kohrah/kohrah-000.png"
GAMEOVER = "addons/mm-hd/cutscene/gameover/gameover-001.png"
OUT = "images/portraits/sc/agents-of-death-victory.png"
WIDTH = 500         # the message window's full portrait width
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


def main(uqm):
    comm = Image.open(os.path.join(uqm, COMM)).convert("RGB")
    gameover = Image.open(os.path.join(uqm, GAMEOVER)).convert("RGB")
    nebula = gameover.transform(comm.size, Image.AFFINE, WARP, Image.BICUBIC)
    comm_space = np.asarray(space(comm, 7, COMM_SPACE)) > 0
    nebula_space = np.asarray(space(nebula, 9, GAMEOVER_SPACE)) > 0
    holes = Image.fromarray(((comm_space & ~nebula_space) * 255).astype(np.uint8))
    holes = holes.filter(ImageFilter.MaxFilter(5))
    nebula = fill(nebula, holes)
    # A soft edge between the painting and the space behind it.
    edge = Image.fromarray((comm_space * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    edge = np.asarray(edge.filter(ImageFilter.GaussianBlur(1.5))) / 255.0
    pic = np.asarray(comm) * (1 - edge[..., None]) + np.asarray(nebula) * edge[..., None]
    pic = Image.fromarray(pic.round().astype(np.uint8))
    pic = pic.resize((WIDTH, round(pic.height * WIDTH / pic.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
