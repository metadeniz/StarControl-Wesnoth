"""New Alliance victory: Talana and the Captain, the morning after.

Takes Star Control II's ending slide from the UQM content
(base/cutscene/ending/ending-003.png, 320x200, the original game's pixel
art): the Captain waking up in bed with Talana beside him, pointing out of
the window at the freed Earth. The picture is blown up SCALE times with no
smoothing, like the Alliance and Hierarchy victory pictures
(tools/make_alliance_victory.py, tools/make_hierarchy_victory.py): Wesnoth's
story screen scales its background to fit the screen, and at about its final
size the pixels stay sharp.

tools/make_victory_portraits.py sizes it for the message window that
sc.victory_picture in lua/sc.lua shows when a New Alliance side wins.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import os
import sys

from PIL import Image

OUT = "images/story/sc/new-alliance-victory.png"
SRC = "base/cutscene/ending/ending-003.png"
SCALE = 5               # 320x200 -> 1600x1000, about 1080p


def main(uqm):
    pic = Image.open(os.path.join(uqm, SRC)).convert("RGB")
    pic = pic.resize((pic.width * SCALE, pic.height * SCALE), Image.NEAREST)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
