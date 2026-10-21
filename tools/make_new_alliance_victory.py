"""New Alliance victory: Earth's slave shield falls.

Star Control II's ending slides from the UQM content (base/cutscene/ending,
320x200, the original game's pixel art): the Captain wakes up in Sick Bay
with Talana beside him, over Earth glowing the sick red of the Ur-Quan slave
shield (ending-002.png); the shield is neutralized "right about... Now!", the
screen flashes white and fades back in on the free, blue Earth
(ending-003.png). The game's ending script (final.txt) fades to white in
700 ms and back in over 1200 ms; this makes that transition as frames of
FRAME_MS each, which sc.victory_picture in lua/sc.lua plays once as a story
screen's floating images over the red slide.

Each frame is blown up SCALE times with no smoothing, like the Alliance and
Hierarchy victory pictures (tools/make_alliance_victory.py,
tools/make_hierarchy_victory.py): Wesnoth's story screen scales its
background to fit the screen, and at about its final size the pixels stay
sharp.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import glob
import os
import sys

from PIL import Image

OUT = "images/story/sc/new-alliance-victory"
ENDING = "base/cutscene/ending"
SCALE = 5               # 320x200 -> 1600x1000, about 1080p
FRAME_MS = 100
TO_WHITE = 700          # the ending script's fade to white...
FROM_WHITE = 1200       # ...and back in on the blue Earth


def main(uqm):
    red = Image.open(os.path.join(uqm, ENDING, "ending-002.png")).convert("RGB")
    blue = Image.open(os.path.join(uqm, ENDING, "ending-003.png")).convert("RGB")
    white = Image.new("RGB", red.size, (255, 255, 255))
    out = TO_WHITE // FRAME_MS
    back = FROM_WHITE // FRAME_MS
    frames = [red]
    frames += [Image.blend(red, white, i / out) for i in range(1, out + 1)]
    frames += [Image.blend(white, blue, i / back) for i in range(1, back + 1)]
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, "*.png")):
        os.remove(old)
    for i, pic in enumerate(frames):
        pic = pic.resize((pic.width * SCALE, pic.height * SCALE), Image.NEAREST)
        path = os.path.join(OUT, f"{i:02d}.png")
        pic.save(path, optimize=True)
    print(OUT, len(frames), "frames", pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
