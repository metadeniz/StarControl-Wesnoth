"""Syreen capture: the captain watching her ship fill up with new crew.

Takes a short clip (120x82, 30 fps) of the Star Control scene, with a grey
bevelled frame around it, and cuts it down to the scene itself: the frame is
cropped off (a 106x70 picture is left), and only clip frames START..END are
kept, at 15 fps: the whole clip, from the captain standing hands on hips,
through her folding her arms, up to the elevator's fifth return into the ship
with its doorway empty. sc.syreen_captured plays them at 1.2x speed; the
last picture is held, then faded out over a few frames.

sc.syreen_captured in lua/sc.lua plays them as a halo when a Syreen takes an
enemy planet and refills its crew. A halo is drawn centred on its hex, so
the frames are baked twice onto a taller canvas with the picture one hex
(72 px) off centre: images/halo/sc/syreen-capture-above-NNN.png shows it on
the hex above the planet, syreen-capture-below-NNN.png on the hex below (for
planets on the top edge).

Needs ffmpeg. Run from the repository root:
    python3 tools/make_syreen_capture_anim.py path/to/clip.mp4
"""

import glob
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

OUT = "images/halo/sc/syreen-capture-{}-{:03d}.png"
HEX = 72                    # picture centre this far above / below the planet's
CROP = (6, 6, 112, 76)      # left, top, right, bottom: inside the grey frame
START, END = 1, 191         # clip frames kept (1-based, inclusive)
STEP = 2                    # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [Image.open(p).convert("RGB").crop(CROP) for p in paths[START - 1:END]]
    for old in glob.glob("images/halo/sc/syreen-capture-*.png"):
        os.remove(old)
    kept = frames[::STEP]
    w, h = kept[0].size
    shown = [(f, 1.0) for f in kept] + [(kept[-1], a) for a in FADE]
    for n, (rgb, a) in enumerate(shown, 1):
        pic = rgb.convert("RGBA")
        pic.putalpha(int(round(a * 255)))
        for where, top in (("above", 0), ("below", 2 * HEX)):
            canvas = Image.new("RGBA", (w, h + 2 * HEX))
            canvas.paste(pic, (0, top))
            canvas.save(OUT.format(where, n))
    print(f"{len(shown)} frames ({len(kept)} + {len(FADE)} fading) of {w}x{h}, above and below")


if __name__ == "__main__":
    main(sys.argv[1])
