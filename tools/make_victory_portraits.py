"""Victory pictures sized for Wesnoth's message window.

sc.victory_picture in lua/sc.lua shows Star Control 1's Alliance and
Hierarchy victory pictures as the portrait of a narrator [message], like a
scripted scenario event. The message window draws a portrait 500 pixels wide
at its full reserved width (it shrinks it on small screens), so each picture
is cut back from the 6x story-screen version (tools/make_alliance_victory.py,
tools/make_hierarchy_victory.py) to the game's own pixels and resampled to
500 pixels wide.

Run from the repository root:
    python3 tools/make_victory_portraits.py
"""

import os

from PIL import Image

SCALE = 6       # the story-screen pictures are the game's pixels blown up 6x
WIDTH = 500     # the message window's full portrait width

for side in ("alliance", "hierarchy"):
    big = Image.open(f"images/story/sc/{side}-victory.png").convert("RGB")
    native = big.resize((big.width // SCALE, big.height // SCALE), Image.BOX)
    height = round(native.height * WIDTH / native.width)
    pic = native.resize((WIDTH, height), Image.LANCZOS)
    out = f"images/portraits/sc/{side}-victory.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pic.save(out, optimize=True)
    print(out, pic.size)
