"""Hierarchy victory: Star Control's "The Hierarchy creams the Alliance" picture.

Takes a screenshot of Star Control 1's Hierarchy victory screen (600x375, the
320x200 game screen scaled 1.875 times) and keeps the picture: an Ur-Quan
reaching out its tentacles. The grey bevelled frame and the caption box under
it are cropped off (sc.victory_picture puts the caption in its message
instead), and the purple-to-white floor glow along the bottom is painted
black, keeping the tentacle in front of it. Each 1.875x1.875 block is
averaged back to one pixel, giving the 310x163 picture at the game's own resolution, which is then
blown up SCALE times with no smoothing, like the Alliance victory picture
(tools/make_alliance_victory.py): Wesnoth's story screen scales its
background to fit the screen, and at about its final size the pixels stay
sharp.

tools/make_victory_portraits.py sizes it for the message window that
sc.victory_picture in lua/sc.lua shows when a Hierarchy side wins.

Run from the repository root:
    python3 tools/make_hierarchy_victory.py path/to/screenshot.png
"""

import os
import sys

import numpy as np
from PIL import Image

OUT = "images/story/sc/hierarchy-victory.png"
CROP = (9, 9, 591, 315)     # left, top, right, bottom: inside the grey frame
SIZE = (310, 163)           # the picture at the game's own resolution
SCALE = 6                   # 310x163 -> 1860x978, about 1080p
FLOOR = 146                 # first row of the purple-to-white floor glow
FLOOR_MATCH = 50            # how close (summed RGB) a pixel is to its row's floor


def main(shot):
    pic = Image.open(shot).convert("RGB").crop(CROP)
    pic = pic.resize(SIZE, Image.BOX)
    # Paint out the floor glow, keeping the tentacle that crosses it: the
    # floor is one colour per row, so a pixel near its row's median is floor.
    a = np.asarray(pic).astype(int)
    for y in range(FLOOR, SIZE[1]):
        floor = np.median(a[y], axis=0)
        a[y][np.abs(a[y] - floor).sum(axis=1) < FLOOR_MATCH] = 0
    pic = Image.fromarray(a.astype(np.uint8))
    pic = pic.resize((SIZE[0] * SCALE, SIZE[1] * SCALE), Image.NEAREST)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
