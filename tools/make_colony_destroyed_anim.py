"""Colony destroyed: the domes on a life world blown apart and left burning.

Takes the 1920x1080 recording of Star Control's "colony destroyed" scene and
cuts it down to the scene itself: the picture box in the status panel is
cropped out (a 108x74 picture is left), and only recording frames
START..END are kept, at 15 fps: from the colony standing intact, through the
blast and its shock ring, to the ruins still burning just before the panel
switches back to the menu. The last picture is held, then faded out over a
few frames.

sc.planet_captured in lua/sc.lua plays them as a halo when a ship destroys
an enemy's colony (life world), unless it's a Syreen filling its crew there.
A halo is drawn centred on its hex, so the frames are baked twice onto a
taller canvas with the picture one hex (72 px) off centre:
images/halo/sc/colony-destroyed-below-NNN.png shows it on the hex below the
planet, under its label, colony-destroyed-above-NNN.png on the hex above
(for planets on the bottom edge).

Needs ffmpeg. Run from the repository root:
    python3 tools/make_colony_destroyed_anim.py path/to/recording.mp4
"""

import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image

OUT = "images/halo/sc/colony-destroyed-{}-{:03d}.png"
HEX = 72                       # picture centre this far above / below the planet's
CROP = (523, 302, 631, 376)    # left, top, right, bottom: the panel's picture box
START, END = 5, 212            # recording frames kept (1-based, inclusive)
STEP = 2                       # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [Image.open(p).convert("RGB").crop(CROP) for p in paths[START - 1:END]]
    for old in glob.glob("images/halo/sc/colony-destroyed-*.png"):
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
