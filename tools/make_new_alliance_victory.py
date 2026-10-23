"""New Alliance victory: Earth's slave shield falls.

Star Control II's ending slides from the UQM content (base/cutscene/ending,
320x200, the original game's pixel art): the Captain in Sick Bay with
Talana beside him, over Earth glowing the sick red of the Ur-Quan slave
shield (ending-002.png), until the shield is neutralized "right about...
Now!", the screen flashes white and fades back in on the free, blue Earth
(ending-003.png). The game's ending script (final.txt) fades to white in
700 ms and back in over 1200 ms; this makes that flash as frames FRAME_MS
apart, which sc.victory_picture in lua/sc.lua plays once over the map before
the victory message window opens. The last frame is the message window's
portrait, the blue Earth, like the Alliance and Hierarchy pictures
(tools/make_victory_portraits.py): resampled from the game's own pixels to
the window's 500-pixel portrait width, and the frames are the same size.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import glob
import os
import sys

from PIL import Image

ENDING = "base/cutscene/ending"
OUT = "images/portraits/sc/new-alliance-victory.png"
FRAMES = "images/misc/sc/new-alliance-victory"
WIDTH = 500             # the message window's full portrait width
FRAME_MS = 100
TO_WHITE = 700          # the ending script's fade to white...
FROM_WHITE = 1200       # ...and back in on the blue Earth


def sized(pic):
    return pic.resize((WIDTH, round(pic.height * WIDTH / pic.width)), Image.LANCZOS)


def main(uqm):
    red = Image.open(os.path.join(uqm, ENDING, "ending-002.png")).convert("RGB")
    blue = Image.open(os.path.join(uqm, ENDING, "ending-003.png")).convert("RGB")
    white = Image.new("RGB", red.size, (255, 255, 255))
    out, back = TO_WHITE // FRAME_MS, FROM_WHITE // FRAME_MS
    frames = [red]
    frames += [Image.blend(red, white, i / out) for i in range(1, out + 1)]
    frames += [Image.blend(white, blue, i / back) for i in range(1, back)]
    os.makedirs(FRAMES, exist_ok=True)
    for old in glob.glob(os.path.join(FRAMES, "*.png")):
        os.remove(old)
    for i, pic in enumerate(frames):
        sized(pic).save(os.path.join(FRAMES, f"{i:02d}.png"), optimize=True)
    pic = sized(blue)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(FRAMES, len(frames), "frames, then", OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
