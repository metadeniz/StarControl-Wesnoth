"""Starbase destroyed: an Alliance or Hierarchy starbase blowing apart.

Takes the 1920x1080 recording of Star Control's "starbase destroyed" scene
and cuts it down to the scene itself: the picture box in the status panel
is cropped out (a 108x72 picture is left), and only recording frames
START..END are kept, at 15 fps: from the starbase standing over its
starfield, through the blasts tearing it apart, to the last embers dying
out on the empty starfield. The last picture is held briefly, then faded
out over a few frames.

sc.starbase_destroyed in lua/sc.lua plays them in the sidebar box above End
Turn when a side's leader is destroyed, once its death explosion is over:
images/halo/sc/starbase-destroyed-NNN.png.

Needs ffmpeg. Run from the repository root:
    python3 tools/make_starbase_destroyed_anim.py path/to/recording.mp4
"""

import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image

OUT = "images/halo/sc/starbase-destroyed-{:03d}.png"
CROP = (522, 302, 630, 374)    # left, top, right, bottom: the panel's picture box
START, END = 51, 141           # recording frames kept (1-based, inclusive)
STEP = 2                       # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [Image.open(p).convert("RGB").crop(CROP) for p in paths[START - 1:END]]
    for old in glob.glob("images/halo/sc/starbase-destroyed-*.png"):
        os.remove(old)
    kept = frames[::STEP]
    w, h = kept[0].size
    shown = [(f, 1.0) for f in kept] + [(kept[-1], a) for a in FADE]
    for n, (rgb, a) in enumerate(shown, 1):
        pic = rgb.convert("RGBA")
        pic.putalpha(int(round(a * 255)))
        pic.save(OUT.format(n))
    print(f"{len(shown)} frames ({len(kept)} + {len(FADE)} fading) of {w}x{h}")


if __name__ == "__main__":
    main(sys.argv[1])
