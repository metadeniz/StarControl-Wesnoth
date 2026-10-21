"""New Alliance victory: Talana, the Syreen captain, the morning after.

Takes Star Control II's Syreen communication screen from the UQM MegaMod
content's HD art (comm/syreen/syreen-000.png, the 972x428 backdrop the
animations play on): Talana lounging on her couch as the lights come back
up when you wake up, "several hours later", after her seduction scene. The
HD art is painted rather than pixel art, so unlike the Alliance and
Hierarchy victory pictures (tools/make_alliance_victory.py,
tools/make_hierarchy_victory.py) it is kept at its own size, not blown up.

tools/make_victory_portraits.py sizes it for the message window that
sc.victory_picture in lua/sc.lua shows when a New Alliance side wins.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import os
import sys

from PIL import Image

OUT = "images/story/sc/new-alliance-victory.png"
SRC = "addons/mm-hd/comm/syreen/syreen-000.png"


def main(uqm):
    pic = Image.open(os.path.join(uqm, SRC)).convert("RGB")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
