"""Alliance victory: Star Control's "The Alliance humbles the Hierarchy" picture.

Takes the clip of Star Control 1's Alliance victory screen (1920x1080, the
640x400 game screen in its top left corner) and keeps one frame of the
picture: Earth ringed by the Alliance races. The grey bevelled frame and the
caption box under it are cropped off (sc.alliance_victory puts the caption
in the story text instead), leaving the 308x163 picture at the game's own
resolution. The clip shows it doubled and compressed, so each 2x2 block is
averaged back to one pixel, then the picture is blown up SCALE times with no
smoothing: Wesnoth's story screen scales its background to fit the screen,
and at about its final size the pixels stay sharp.

sc.alliance_victory in lua/sc.lua shows it as a story screen when an Alliance
side wins, while Star Control 1's Alliance victory theme plays.

Needs ffmpeg. Run from the repository root:
    python3 tools/make_alliance_victory.py path/to/clip.mp4
"""

import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

OUT = "images/story/sc/alliance-victory.png"
CROP = (10, 10, 626, 336)   # left, top, right, bottom: inside the grey frame
AT = "0.5"                  # seconds into the clip (it barely moves)
SCALE = 6                   # 308x163 -> 1848x978, about 1080p


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        frame = os.path.join(tmp, "frame.png")
        subprocess.run(["ffmpeg", "-v", "error", "-ss", AT, "-i", clip,
                        "-frames:v", "1", frame], check=True)
        a = np.asarray(Image.open(frame).convert("RGB").crop(CROP), float)
    h, w = a.shape[0] // 2, a.shape[1] // 2
    a = a.reshape(h, 2, w, 2, 3).mean(axis=(1, 3))
    pic = Image.fromarray(np.clip(a.round(), 0, 255).astype(np.uint8))
    pic = pic.resize((w * SCALE, h * SCALE), Image.NEAREST)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
