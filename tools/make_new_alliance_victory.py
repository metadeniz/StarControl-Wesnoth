"""New Alliance victory: the Captain in his old age, and Talana.

Combines two slides of Star Control II's ending, from the UQM MegaMod
content's HD art (cutscene/ending): the Captain, grown old on Unzervalt,
telling the children of the war (ending-004.png), and Talana's portrait
(ending-001.png) rising into the sunset sky above them like a memory, the
way he relishes the victory he shared with her. Talana is cut out of her
starry backdrop, warmed toward the sunset light, faded out below the chest
and laid over the sky at OPACITY; the leaves and trees stay in front of her.
The art is painted rather than pixel art, so unlike the Alliance and
Hierarchy victory pictures (tools/make_alliance_victory.py,
tools/make_hierarchy_victory.py) it is kept at the slides' own size.

tools/make_victory_portraits.py sizes it for the message window that
sc.victory_picture in lua/sc.lua shows when a New Alliance side wins.

Run from the repository root:
    python3 tools/make_new_alliance_victory.py <UQM-MegaMod-Content checkout>
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = "images/story/sc/new-alliance-victory.png"
ENDING = "addons/mm-hd/cutscene/ending"
SCALE = 0.62            # Talana's portrait in the sky
AT = (500, -12)         # where its top left corner goes
OPACITY = 0.78
FADE = (340, 540)       # portrait rows over which her body fades out
WARM = (255, 170, 90)   # sunset light she is tinted toward
WARMTH = 0.15


def talana_mask(pic):
    """Talana against her backdrop: black space and deep blue swirls."""
    a = np.asarray(pic).astype(int)
    r, b = a[..., 0], a[..., 2]
    fg = ~((a.max(axis=-1) < 70) | ((b - r > 50) & (r < 110)))
    m = Image.fromarray((fg * 255).astype(np.uint8))
    # opening drops the stars, closing seals her outline
    m = m.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    # fill the holes: whatever the backdrop around the edge can't reach is her
    m = m.convert("L")
    ImageDraw.floodfill(m, (0, 0), 128)
    m = Image.fromarray(np.where(np.asarray(m) == 128, 0, 255).astype(np.uint8))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(2))) / 255


def main(uqm):
    base = Image.open(os.path.join(uqm, ENDING, "ending-004.png")).convert("RGB")
    tal = Image.open(os.path.join(uqm, ENDING, "ending-001.png")).convert("RGB")
    mask = talana_mask(tal)
    rows = np.arange(tal.height)[:, None]
    mask = mask * np.clip((FADE[1] - rows) / (FADE[1] - FADE[0]), 0, 1)
    size = (int(tal.width * SCALE), int(tal.height * SCALE))
    t = np.asarray(tal.resize(size, Image.LANCZOS)).astype(float)
    t = t * (1 - WARMTH) + np.array(WARM) * WARMTH
    layer = Image.new("RGB", base.size)
    layer.paste(Image.fromarray(t.clip(0, 255).astype(np.uint8)), AT)
    alpha = Image.new("L", base.size, 0)
    alpha.paste(Image.fromarray((mask * 255).astype(np.uint8)).resize(size, Image.LANCZOS), AT)
    al = np.asarray(alpha) / 255 * OPACITY
    # the leaves and trees in front of the sky stay in front of her
    b = np.asarray(base).astype(int)
    front = Image.fromarray(((b[..., 1] > b[..., 0] + 5) * 255).astype(np.uint8))
    al = al * (1 - np.asarray(front.filter(ImageFilter.GaussianBlur(1.5))) / 255)
    pic = b * (1 - al[..., None]) + np.asarray(layer).astype(float) * al[..., None]
    pic = Image.fromarray(pic.clip(0, 255).astype(np.uint8))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pic.save(OUT, optimize=True)
    print(OUT, pic.size)


if __name__ == "__main__":
    main(sys.argv[1])
