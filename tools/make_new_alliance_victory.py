"""New Alliance victory: Earth, free of its slave shield.

Star Control II's ending slide from the UQM content (base/cutscene/ending,
320x200, the original game's pixel art): the Captain in Sick Bay with
Talana beside him, over the free, blue Earth once the Ur-Quan slave shield
has fallen (ending-003.png). sc.victory_picture in lua/sc.lua shows it as
the portrait of the victory message window, like the Alliance and Hierarchy
pictures (tools/make_victory_portraits.py): resampled from the game's own
pixels to the window's 500-pixel portrait width.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import os
import sys

from PIL import Image

SLIDE = "base/cutscene/ending/ending-003.png"
OUT = "images/portraits/sc/new-alliance-victory.png"
WIDTH = 500     # the message window's full portrait width


def main(uqm):
    pic = Image.open(os.path.join(uqm, SLIDE)).convert("RGB")
    pic = pic.resize((WIDTH, round(pic.height * WIDTH / pic.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
