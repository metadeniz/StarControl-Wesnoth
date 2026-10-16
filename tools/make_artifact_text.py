"""Precursor artifact found: the floating text, rising slowly.

Wesnoth 1.16's floating text (wesnoth.interface.float_label) always rises
fast and is gone within a second, too quick to read. So the text is baked
into halo frames instead: "Precursor Artifact!" in gold over "Crew gets
+8 XP" in white, outlined like Wesnoth's own floating text, starting on the
planet and rising RISE pixels over RISE_MS, then fading out.
sc.check_artifact in lua/sc.lua plays them (images/halo/sc/artifact-text-NNN.png,
FPS frames a second). A halo is drawn centred on its hex, so each frame is
a canvas symmetric about the hex centre with the text moved up inside it.

Run from the repository root: python3 tools/make_artifact_text.py
"""

import glob
import os

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/games/wesnoth/1.16/fonts/Lato-Bold.ttf"   # Wesnoth's own
SIZE = 15
LINES = [("Precursor Artifact!", (255, 216, 74)), ("Crew gets +8 XP", (255, 255, 255))]
OUTLINE = 2
FPS = 20
RISE = 24           # px, from the planet's centre
RISE_MS = 3000
FADE_MS = 600
OUT = "images/halo/sc/artifact-text-{:03d}.png"


def text_image():
    font = ImageFont.truetype(FONT, SIZE)
    boxes = [font.getbbox(t) for t, _ in LINES]
    w = max(b[2] - b[0] for b in boxes) + 2 * OUTLINE
    line_h = SIZE + 3
    h = line_h * len(LINES) + 2 * OUTLINE
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for i, ((text, color), b) in enumerate(zip(LINES, boxes)):
        x = (w - (b[2] - b[0])) / 2 - b[0]
        y = OUTLINE + i * line_h
        d.text((x, y), text, font=font, fill=color + (255,),
               stroke_width=OUTLINE, stroke_fill=(0, 0, 0, 200))
    return im


def main():
    text = text_image()
    w, h = text.size
    canvas_h = 2 * (RISE + h // 2 + 1)
    for old in glob.glob(OUT.replace("{:03d}", "*")):
        os.remove(old)
    rise_frames = RISE_MS * FPS // 1000
    fade_frames = FADE_MS * FPS // 1000
    for n in range(rise_frames + fade_frames):
        t = min(n / (rise_frames - 1), 1.0)
        # ease out: quick off the planet, then drifting
        dy = round(RISE * (1 - (1 - t) ** 2))
        alpha = 1.0 if n < rise_frames else 1 - (n - rise_frames + 1) / (fade_frames + 1)
        frame = text.copy()
        frame.putalpha(frame.getchannel("A").point(lambda a: round(a * alpha)))
        canvas = Image.new("RGBA", (w, canvas_h))
        canvas.alpha_composite(frame, (0, canvas_h // 2 - h // 2 - dy))
        canvas.save(OUT.format(n + 1))
    print(f"{rise_frames + fade_frames} frames ({rise_frames} rising + {fade_frames} fading), {w}x{canvas_h}")


if __name__ == "__main__":
    main()
