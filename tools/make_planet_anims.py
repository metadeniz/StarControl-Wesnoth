"""Planet animations: Star Control's scenes from the status panel's picture box.

Takes a 1920x1080 recording of one of the scenes and cuts it down to the
scene itself: the picture box in the status panel is cropped out (a 107x72
picture is left), and only the scene's recording frames START..END are
kept, at 15 fps. The last picture is held, then faded out over a few frames.
  colony-destroyed  the domes on a life world blown apart and left burning,
                    up to just before the panel switches back to the menu
  mine-destroyed    the mining vehicle on a mineral world, the blast, and
                    the screen whiting out, up to the moment it is all white
  syreen-capture    the captain watching her ship fill up with the planet's
                    colonists, from the cut to the planet up to the cut away
  artifact          the Precursor device's screen filling with glyphs

lua/sc.lua plays them as halos: sc.planet_captured when a ship destroys an
enemy's colony (life world, unless it's a Syreen filling its crew there) or
mine (mineral world), sc.syreen_captured when a Syreen fills its crew, and
sc.check_artifact when a ship finds an artifact. A halo is drawn centred on
its hex, so the frames are baked twice onto a taller canvas with the picture
a little over a hex (84 px) off centre, clear of the label at the bottom of
the planet's hex: images/halo/sc/SCENE-below-NNN.png shows it below the
planet, SCENE-above-NNN.png above it (for planets near the bottom edge).
The colony and mine scenes also carry their text ("Colony destroyed",
"Mine destroyed") where Wesnoth puts a map label, at the bottom of the
planet's hex, so it fades out and goes with the scene.

Needs ffmpeg. Run from the repository root:
    python3 tools/make_planet_anims.py SCENE path/to/recording.mp4
"""

import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

OUT = "images/halo/sc/{}-{}-{:03d}.png"
HEX = 84                       # picture centre this far above / below the planet's
CROP = (523, 302, 630, 374)    # left, top, right, bottom: inside the box's grey rim
# recording frames kept (1-based, inclusive): START, END
SCENES = {
    "colony-destroyed": (5, 212),
    "mine-destroyed": (54, 188),
    "syreen-capture": (139, 344),
    "artifact": (3, 207),
}
TEXT = {"colony-destroyed": "Colony destroyed", "mine-destroyed": "Mine destroyed"}
FONT = "/usr/share/games/wesnoth/1.16/fonts/Lato-Regular.ttf"   # Wesnoth's own
SIZE = 15
COLOR = (255, 128, 96)         # as "Planet destroyed"
TEXT_TOP = 22                  # px below the hex centre, as a map label
STEP = 2                       # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)


def text_image(text):
    font = ImageFont.truetype(FONT, SIZE)
    l, t, r, b = font.getbbox(text)
    im = Image.new("RGBA", (r - l + 4, b + 4))
    ImageDraw.Draw(im).text((2 - l, 2), text, font=font, fill=COLOR + (255,),
                            stroke_width=1, stroke_fill=(0, 0, 0, 160))
    return im


def main(scene, clip):
    start, end = SCENES[scene]
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [Image.open(p).convert("RGB").crop(CROP) for p in paths[start - 1:end]]
    for old in glob.glob(f"images/halo/sc/{scene}-above-*.png") + glob.glob(f"images/halo/sc/{scene}-below-*.png"):
        os.remove(old)
    kept = frames[::STEP]
    w, h = kept[0].size
    text = text_image(TEXT[scene]) if scene in TEXT else None
    cw = max(w, text.width) if text else w
    shown = [(f, 1.0) for f in kept] + [(kept[-1], a) for a in FADE]
    for n, (rgb, a) in enumerate(shown, 1):
        pic = rgb.convert("RGBA")
        pic.putalpha(int(round(a * 255)))
        for where, top in (("above", 0), ("below", 2 * HEX)):
            canvas = Image.new("RGBA", (cw, h + 2 * HEX))
            canvas.paste(pic, ((cw - w) // 2, top))
            if text:
                faded = text.copy()
                faded.putalpha(faded.getchannel("A").point(lambda v: round(v * a)))
                canvas.alpha_composite(faded, ((cw - text.width) // 2, canvas.height // 2 + TEXT_TOP))
            canvas.save(OUT.format(scene, where, n))
    print(f"{len(shown)} frames ({len(kept)} + {len(FADE)} fading) of {w}x{h}, above and below")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
