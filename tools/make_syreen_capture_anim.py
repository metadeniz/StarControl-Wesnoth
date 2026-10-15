"""Syreen capture: the captain watching her ship fill up with new crew.

Takes a short clip (120x82, 30 fps) of the Star Control scene, with a grey
bevelled frame around it, and cuts it down to the scene itself: the frame is
cropped off (a 106x70 picture is left), and only clip frames START..END are
kept, at 15 fps, from the captain standing hands on hips, through her folding
her arms, to the end of one full loop of the crew walking aboard. The last
picture is held, then faded out over a few frames. A caption, "Syreen gains
full crew.", is drawn on the side of the picture away from the planet.

sc.syreen_captured in lua/sc.lua plays them as a halo when a Syreen takes an
enemy planet and refills its crew. A halo is drawn centred on its hex, so
the frames are baked twice onto a taller canvas with the picture one hex
(72 px) off centre: images/halo/sc/syreen-capture-above-NNN.png shows it on
the hex above the planet, syreen-capture-below-NNN.png on the hex below (for
planets on the top edge).

Needs ffmpeg, and Lato Bold (Wesnoth's own UI font) for the caption. Run
from the repository root:
    python3 tools/make_syreen_capture_anim.py path/to/clip.mp4
"""

import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

OUT = "images/halo/sc/syreen-capture-{}-{:03d}.png"
HEX = 72                    # picture centre this far above / below the planet's
CROP = (6, 6, 112, 76)      # left, top, right, bottom: inside the grey frame
START, END = 1, 117         # clip frames kept (1-based, inclusive)
STEP = 2                    # keep every 2nd frame: 30 fps -> 15 fps
FADE = (0.8, 0.6, 0.4, 0.2)
CAPTION = "Syreen gains full crew."
CAPTION_COLOR = (255, 128, 208)
FONTS = ("/usr/share/games/wesnoth/1.16/fonts/Lato-Bold.ttf",
         "/usr/share/fonts/truetype/lato/Lato-Bold.ttf")
FONT_SIZE = 13
CAP_H = 18                  # caption strip height


def caption(width):
    """The caption, light pink with a dark outline, centred in a strip."""
    font = ImageFont.truetype(next(f for f in FONTS if os.path.exists(f)), FONT_SIZE)
    strip = Image.new("RGBA", (width, CAP_H))
    d = ImageDraw.Draw(strip)
    l, t, r, b = d.textbbox((0, 0), CAPTION, font=font)
    xy = ((width - (r - l)) // 2 - l, (CAP_H - (b - t)) // 2 - t)
    d.text(xy, CAPTION, font=font, fill=CAPTION_COLOR + (255,),
           stroke_width=2, stroke_fill=(20, 0, 20, 255))
    return strip


def main(clip):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", clip, os.path.join(tmp, "%04d.png")], check=True)
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        frames = [Image.open(p).convert("RGB").crop(CROP) for p in paths[START - 1:END]]
    for old in glob.glob("images/halo/sc/syreen-capture-*.png"):
        os.remove(old)
    kept = frames[::STEP]
    w, h = kept[0].size
    cw = max(w, 150)                        # wide enough for the caption
    cap = caption(cw)
    ch = 2 * (HEX + h // 2 + CAP_H)         # centred on the planet's hex
    shown = [(f, 1.0) for f in kept] + [(kept[-1], a) for a in FADE]
    for n, (rgb, a) in enumerate(shown, 1):
        pic = rgb.convert("RGBA")
        for where in ("above", "below"):
            block = Image.new("RGBA", (cw, h + CAP_H))
            pic_top, cap_top = (CAP_H, 0) if where == "above" else (0, h)
            block.paste(pic, ((cw - w) // 2, pic_top))
            block.alpha_composite(cap, (0, cap_top))
            if a < 1:
                block.putalpha(block.getchannel("A").point(lambda v: int(round(v * a))))
            canvas = Image.new("RGBA", (cw, ch))
            # picture centre one hex above / below the canvas centre
            pic_centre = ch // 2 - HEX if where == "above" else ch // 2 + HEX
            canvas.paste(block, (0, pic_centre - h // 2 - pic_top))
            canvas.save(OUT.format(where, n))
    print(f"{len(shown)} frames ({len(kept)} + {len(FADE)} fading) of {w}x{h} + caption, above and below")


if __name__ == "__main__":
    main(sys.argv[1])
