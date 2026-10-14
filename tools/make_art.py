#!/usr/bin/env python3
"""Build every image and sound the Star Control TC add-on uses.

Two kinds of art come out of this script:

* UQM-derived (personal set): ship sprites, projectiles, explosions and
  sounds, converted from The Ur-Quan Masters content (CC BY-NC-SA 2.5).
  Every file of this kind is listed in art-manifest.txt so a future
  published build can tell exactly what has to be replaced.
* Original: all terrain (starfield, nebula, asteroids, planets, star,
  starbases) is generated procedurally here and is ours to publish.

Usage:
    make_art.py --uqm <UQM-MegaMod-Content checkout> --out <add-on dir>
                [--wesnoth-data /usr/share/games/wesnoth/1.16/data]
    make_art.py --only badlands --out <add-on dir>    (badlands art and rules only)
    make_art.py --only asteroids --out <add-on dir>   (asteroid fields, dense asteroids, walls)
    make_art.py --only fried --out <add-on dir>       (Kohr-Ah F.R.I.E.D. plumes)
    make_art.py --only terrain --out <add-on dir>     (all terrain, no UQM content needed)
"""

import argparse
import colorsys
import itertools
import math
import os
import shutil
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from make_alliance_starbase import build_alliance_starbase
from make_asteroids import build as build_asteroid_art
from make_barriers import build_objects as build_barrier_objects, gas_painters
from make_fried import build as build_fried_plumes
from make_starbase import build_hierarchy_starbase

HEX = 72
# Screen angle (degrees clockwise from north) of each Wesnoth hex facing.
# Neighbouring hex centres are 54px across and 36px up/down, not 60 degrees.
DIAG = math.degrees(math.atan2(54, 36))
FACINGS = {
    "n": 0.0,
    "ne": DIAG,
    "se": 180.0 - DIAG,
    "s": 180.0,
    "sw": 180.0 + DIAG,
    "nw": 360.0 - DIAG,
}

# unit image id -> (UQM ship dir, sprite stem)
SHIPS = {
    "earthling-cruiser": ("human", "cruiser"),
    "chenjesu-broodhome": ("chenjesu", "broodhome"),
    "mmrnmhrm-xform": ("mmrnmhrm", "xform"),
    "mmrnmhrm-ywing": ("mmrnmhrm", "ywing"),
    "yehat-terminator": ("yehat", "terminator"),
    "syreen-penetrator": ("syreen", "penetrator"),
    "arilou-skiff": ("arilou", "skiff"),
    "shofixti-scout": ("shofixti", "scout"),
    "urquan-dreadnought": ("urquan", "dreadnought"),
    "mycon-podship": ("mycon", "podship"),
    "spathi-eluder": ("spathi", "eluder"),
    "umgah-drone": ("umgah", "drone"),
    "vux-intruder": ("vux", "intruder"),
    "androsynth-guardian": ("androsynth", "guardian"),
    "androsynth-blazer": ("androsynth", "blazer"),
    "ilwrath-avenger": ("ilwrath", "avenger"),
    # Star Control II: the Kohr-Ah Death March
    "kohrah-marauder": ("kohrah", "marauder"),
    "druuge-mauler": ("druuge", "mauler"),
    "thraddash-torch": ("thraddash", "torch"),
    "slylandro-probe": ("slylandro", "probe"),
    "orz-nemesis": ("orz", "nemesis"),
    "melnorme-trader": ("melnorme", "trader"),
    # Star Control II: the New Alliance of Free Stars
    "chmmr-avatar": ("chmmr", "avatar"),
    "zoqfotpik-stinger": ("zoqfotpik", "stinger"),
    "pkunk-fury": ("pkunk", "fury"),
    "supox-blade": ("supox", "blade"),
    "utwig-jugger": ("utwig", "jugger"),
    "precursor-flagship": ("flagship", "flagship"),
}

# projectile id -> (UQM ship dir, sprite stem, frame, scale vs HD sprite)
PROJECTILES = {
    "nuke": ("human", "saturn", 0, 0.5),
    "crystal": ("chenjesu", "spark", 0, 0.6),
    "dogi": ("chenjesu", "doggy", 0, 0.45),
    "torpedo": ("mmrnmhrm", "torpedo", 0, 0.5),
    "pulse": ("yehat", "missile", 0, 0.6),
    "dagger": ("syreen", "dagger", 0, 0.5),
    "dart": ("shofixti", "missile", 0, 0.6),
    "fusion": ("urquan", "fusion", 0, 0.5),
    "fighter": ("urquan", "fighter", 0, 1.4),
    "plasmoid": ("mycon", "plasma", 0, 0.45),
    "spathi-missile": ("spathi", "missile", 0, 0.6),
    "butt": ("spathi", "butt", 0, 0.5),
    "limpet": ("vux", "limpets", 0, 0.8),
    "bubble": ("androsynth", "bubble", 0, 0.6),
    "hellfire": ("ilwrath", "fire", 0, 0.5),
    "cone": ("umgah", "cone", 0, 0.32),
    "buzzsaw": ("kohrah", "buzzsaw", 0, 0.5),
    "fried": ("kohrah", "gas", 0, 1.6),
    "mass-driver": ("druuge", "cannon", 0, 0.6),
    "horn": ("thraddash", "horn", 0, 0.6),
    "napalm": ("thraddash", "napalm", 0, 1.2),
    "howitzer": ("orz", "howitzer", 0, 0.9),
    "zapsat": ("chmmr", "satellite", 0, 0.4),
    "spit": ("zoqfotpik", "spit", 0, 1.4),
    "tongue": ("zoqfotpik", "proboscis", 0, 0.8),
    "bug": ("pkunk", "bug", 0, 0.8),
    "glob": ("supox", "glob", 0, 0.6),
    "lance": ("utwig", "lance", 0, 0.9),
    "blaster": ("flagship", "blaster", 0, 0.8),
    "charge-blue": ("melnorme", "pumpup", 6, 0.5),     # the Melnorme blaster, lightly charged
    "charge-red": ("melnorme", "pumpup", 16, 0.4),     # ...and fully charged
    "confuser": ("melnorme", "confuse", 0, 0.6),
}

# Laser bolts are lines in UQM, so these are drawn here: id -> RGB core colour.
LASERS = {
    "laser-white": (255, 255, 255),
    "laser-red": (255, 70, 60),
    "laser-green": (90, 255, 110),
    "laser-gold": (255, 220, 90),
    "laser-violet": (220, 120, 255),
    # Chmmr megawatt laser: UQM cycles its colour every battle frame while
    # it is held (chmmr.c cycle_array), which makes the beam shimmer.
    "chmmr-laser-1": (189, 0, 0),
    "chmmr-laser-2": (255, 25, 0),
    "chmmr-laser-3": (255, 140, 0),
    "chmmr-laser-4": (255, 25, 0),
    "lightning": (200, 220, 255),        # Slylandro probe
}

# sound id -> path inside the UQM content dir
SOUNDS = {
    "earthling-nuke": "base/ships/human/primary.wav",
    "earthling-pd": "base/ships/human/secondary.wav",
    "chenjesu-crystal": "base/ships/chenjesu/primary.wav",
    "chenjesu-dogi": "base/ships/chenjesu/secondary.wav",
    "mmrnmhrm-laser": "base/ships/mmrnmhrm/primaryx.wav",
    "mmrnmhrm-torpedo": "base/ships/mmrnmhrm/primaryy.wav",
    "mmrnmhrm-transform": "base/ships/mmrnmhrm/secondary.wav",
    "yehat-pulse": "base/ships/yehat/primary.wav",
    "yehat-shield": "base/ships/yehat/secondary.wav",
    "syreen-dagger": "base/ships/syreen/primary.wav",
    "syreen-song": "base/ships/syreen/secondary.wav",
    "arilou-laser": "base/ships/arilou/primary.wav",
    "arilou-jump": "base/ships/arilou/secondary.wav",
    "shofixti-dart": "base/ships/shofixti/primary.wav",
    "shofixti-glory": "base/ships/shofixti/secondary.wav",
    "urquan-fusion": "base/ships/urquan/primary.wav",
    "urquan-launch": "base/ships/urquan/secondary.wav",
    "urquan-fighter-laser": "base/ships/urquan/fighter_laser.wav",
    "urquan-fighter-dock": "base/ships/urquan/fighter_get.wav",
    "mycon-plasmoid": "base/ships/mycon/primary.wav",
    "mycon-regrow": "base/ships/mycon/secondary.wav",
    "spathi-missile": "base/ships/spathi/primary.wav",
    "spathi-butt": "base/ships/spathi/secondary.wav",
    "umgah-cone": "base/ships/umgah/primary.wav",
    "vux-laser": "base/ships/vux/primary.wav",
    "vux-limpets": "base/ships/vux/secondary.wav",
    "androsynth-bubbles": "base/ships/androsynth/primary.wav",
    "androsynth-blazer": "base/ships/androsynth/secondary.wav",
    "ilwrath-hellfire": "base/ships/ilwrath/primary.wav",
    "ilwrath-cloak": "base/ships/ilwrath/cloak.wav",
    "ilwrath-uncloak": "base/ships/ilwrath/uncloak.wav",
    "kohrah-buzzsaw": "base/ships/kohrah/primary.wav",
    "kohrah-fried": "base/ships/kohrah/secondary.wav",
    "druuge-cannon": "base/ships/druuge/primary.wav",
    "druuge-furnace": "base/ships/druuge/secondary.wav",
    "thraddash-horn": "base/ships/thraddash/primary.wav",
    "thraddash-afterburner": "base/ships/thraddash/secondary.wav",
    "slylandro-lightning": "base/ships/slylandro/primary.wav",
    "slylandro-harvest": "base/ships/slylandro/secondary.wav",
    "orz-howitzer": "base/ships/orz/primary.wav",
    "orz-marines": "base/ships/orz/zap.wav",
    "orz-go": "base/ships/orz/secondary.wav",          # the marines' "Go!"
    "chmmr-laser": "base/ships/chmmr/primary.wav",
    "chmmr-tractor": "base/ships/chmmr/secondary.wav",
    "zoqfotpik-spit": "base/ships/zoqfotpik/primary.wav",
    "zoqfotpik-tongue": "base/ships/zoqfotpik/secondary.wav",
    "pkunk-bug": "base/ships/pkunk/primary.wav",
    "pkunk-rebirth": "base/ships/pkunk/rebirth.wav",
    "supox-glob": "base/ships/supox/primary.wav",
    "utwig-lance": "base/ships/utwig/primary.wav",
    "utwig-shield": "base/ships/utwig/secondary.wav",
    "flagship-blaster": "base/ships/flagship/primary.wav",
    "melnorme-blaster": "base/ships/melnorme/primary.wav",
    "melnorme-confuser": "base/ships/melnorme/secondary.wav",
    "samatra-comet": "base/ships/samatra/primary.wav",       # comet launch
    "samatra-blob": "base/ships/samatra/secondary.wav",      # green sentinel hit
    "boom-small": "base/battle/boom1.wav",
    "boom-medium": "base/battle/boom23.wav",
    "boom-large": "base/battle/boom45.wav",
    "ship-dies": "base/battle/shipdies.wav",
    "artifact": "base/battle/getcrew.wav",
}

TRANSITION_COMBOS = [
    "n", "ne", "se", "s", "sw", "nw",
    "n-ne", "ne-se", "se-s", "s-sw", "sw-nw", "nw-n",
    "n-ne-se", "ne-se-s", "se-s-sw", "s-sw-nw", "sw-nw-n", "nw-n-ne",
    "s-sw-nw-n-ne", "sw-nw-n-ne-se", "s-sw-nw-n-ne-se",
]

manifest = []


def save(img, out, rel, uqm):
    path = os.path.join(out, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    if uqm:
        manifest.append(rel)


# ---------------------------------------------------------------- UQM art


def hd_sprite(uqm, ship_dir, stem, frame=0):
    path = os.path.join(uqm, "addons/mm-hd/ships", ship_dir, f"{stem}-big-{frame:03d}.png")
    return Image.open(path).convert("RGBA")


def sd_size(uqm, ship_dir, stem):
    path = os.path.join(uqm, "base/ships", ship_dir, f"{stem}-big-000.png")
    return max(Image.open(path).size)


def rotated(img, angle):
    """Rotate clockwise by `angle` degrees, keeping the whole sprite."""
    return img.rotate(-angle, resample=Image.BICUBIC, expand=True)


def trim(img):
    box = img.getbbox()
    return img.crop(box) if box else img


def centred(img, size=HEX):
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def ship_scale(uqm, ship_dir, stem, hd):
    """Pixel length of the ship's long side in-game.

    Ships keep their relative sizes from Star Control (a Dreadnought dwarfs a
    Shofixti Scout) but squeezed so the small ones stay readable.
    """
    d = sd_size(uqm, ship_dir, stem)
    target = min(66.0, max(24.0, 30 + 1.55 * (d - 12)))
    scale = target / max(hd.size)
    # Shrink further if any facing would overflow the hex.
    for angle in FACINGS.values():
        r = trim(rotated(hd, angle))
        scale = min(scale, 70.0 / max(r.size))
    return scale


# A ship's level shows on its sprite: it grows, and from level 2 it glows.
# level -> (size relative to the level-3 sprite, glow (blur radius, strength))
LEVELS = {1: (0.82, None), 2: (0.91, (2.5, 1.0)), 3: (1.0, (3.5, 1.6))}
# Level 3 is up to this much bigger than the ship's base size, if it fits.
LEVEL_GROWTH = 1.12
# Ships whose level-1 sprite fills the whole hex instead (the Precursor
# Flagship leads with it, so it should look huge): facing north, its sides
# touch the hex's slanted edges and its nose and tail poke out top and bottom.
FILL_HEX = {"precursor-flagship"}


def hex_filling_scale(img):
    """Largest scale at which `img`, upright, stays inside the hex's slanted edges."""
    scale = HEX / 2 / max(img.size)
    for step in (0.1, 0.01, 0.001):
        while True:
            s = scale + step
            w, h = round(img.width * s), round(img.height * s)
            ys, xs = np.nonzero(np.array(img.resize((w, h), Image.LANCZOS))[..., 3] > 40)
            if (np.abs(xs + 0.5 - w / 2) + np.abs(ys + 0.5 - h / 2) / 2 > HEX / 2).any():
                break
            scale = s
    return scale


def glow_colour(img):
    """The ship's own dominant hue, made light: its glow colour."""
    a = np.array(img).astype(float) / 255
    rgb, alpha = a[..., :3], a[..., 3]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    w = alpha * (sat > 0.35) * (mx > 0.25) * sat
    if w.sum() < 20:  # grey hull: a pale blue-white glow
        return (200, 220, 255)
    mean = (rgb * w[..., None]).sum(axis=(0, 1)) / w.sum()
    h, _, _ = colorsys.rgb_to_hsv(*mean)
    return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, 0.55, 1.0))


def with_glow(img, colour, radius, strength):
    halo = img.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    halo = halo.point(lambda v: min(255, round(v * strength)))
    out = Image.new("RGBA", img.size, colour + (0,))
    out.putalpha(halo)
    out.alpha_composite(img)
    return out


def build_ships(uqm, out):
    for uid, (ship_dir, stem) in SHIPS.items():
        hd = hd_sprite(uqm, ship_dir, stem)
        fit = min(70.0 / max(trim(rotated(hd, a)).size) for a in FACINGS.values())
        top = min(ship_scale(uqm, ship_dir, stem, hd) * LEVEL_GROWTH, fit)
        colour = glow_colour(hd)
        for level, (size, glow) in LEVELS.items():
            scale = top * size
            if uid in FILL_HEX and level == 1:
                scale = hex_filling_scale(trim(hd))
            for facing, angle in FACINGS.items():
                r = trim(rotated(hd, angle))
                w = max(1, round(r.width * scale))
                h = max(1, round(r.height * scale))
                img = centred(r.resize((w, h), Image.LANCZOS), max(HEX, w + w % 2, h + h % 2))
                if glow:
                    img = with_glow(img, colour, *glow)
                save(img, out, f"images/units/sc/{uid}-l{level}-{facing}.png", True)
                if facing == "ne":
                    save(img, out, f"images/units/sc/{uid}-l{level}.png", True)


def build_projectiles(uqm, out):
    for pid, (ship_dir, stem, frame, scale) in PROJECTILES.items():
        hd = hd_sprite(uqm, ship_dir, stem, frame)
        w = max(2, round(hd.width * scale))
        h = max(2, round(hd.height * scale))
        if max(w, h) < 10:
            k = 10 / max(w, h)
            w, h = round(w * k), round(h * k)
        small = hd.resize((w, h), Image.LANCZOS)
        for facing in ("n", "ne"):
            img = trim(rotated(small, FACINGS[facing]))
            save(img, out, f"images/projectiles/sc/{pid}-{facing}.png", True)


def build_lasers(out):
    for lid, rgb in LASERS.items():
        w, h = 9, 30
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1, 0, w - 2, h - 1], radius=3, fill=rgb + (90,))
        d.rounded_rectangle([3, 1, w - 4, h - 2], radius=2, fill=rgb + (200,))
        d.line([w // 2, 2, w // 2, h - 3], fill=(255, 255, 255, 255), width=1)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        for facing in ("n", "ne"):
            save(trim(rotated(img, FACINGS[facing])), out,
                 f"images/projectiles/sc/{lid}-{facing}.png", False)


def build_effects(uqm, out):
    battle = os.path.join(uqm, "addons/mm-hd/battle")
    for i in range(9):
        img = Image.open(os.path.join(battle, f"boom-big-{i:03d}.png")).convert("RGBA")
        save(img.resize((img.width * 3, img.height * 3), Image.LANCZOS), out,
             f"images/halo/sc/boom-{i + 1}.png", True)
    for i in range(8):
        img = Image.open(os.path.join(battle, f"blast-big-{i:03d}.png")).convert("RGBA")
        save(img, out, f"images/halo/sc/blast-{i + 1}.png", True)
    # Shofixti Glory Device: blown up to cover the scout's neighbours.
    ddir = os.path.join(uqm, "addons/mm-hd/ships/shofixti")
    frames = sorted(f for f in os.listdir(ddir) if f.startswith("destruct-big-") and f.endswith(".png"))
    for i, f in enumerate(frames):
        img = Image.open(os.path.join(ddir, f)).convert("RGBA")
        k = 200 / max(img.size)
        save(img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS), out,
             f"images/halo/sc/glory-{i + 1}.png", True)
    # Ilwrath hellfire burst frames
    fdir = os.path.join(uqm, "addons/mm-hd/ships/ilwrath")
    frames = sorted(f for f in os.listdir(fdir) if f.startswith("fire-big-") and f.endswith(".png"))
    for i, f in enumerate(frames):
        img = Image.open(os.path.join(fdir, f)).convert("RGBA")
        k = 0.6
        save(img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS),
             out, f"images/halo/sc/hellfire-{i + 1}.png", True)
    return len(frames)


def build_samatra(uqm, out):
    """The Sa-Matra: cut out of Star Control II's final-battle picture,
    without the asteroid belt and shield around it. A battle platform has
    no front, so every facing uses the same picture."""
    im = Image.open(os.path.join(uqm, "addons/mm-hd/planets/samatra-final-000.png")).convert("RGBA")
    a = np.array(im).astype(float)
    rgb = a[..., :3]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    h, w = mx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    inside = ((xx - w / 2) / 250) ** 2 + ((yy - 138) / 105) ** 2 < 1
    keep = (sat > 0.35) & (mx > 30) & inside & (yy < 235)   # grey rocks and the shield bar go
    a[..., 3] = np.where(keep, a[..., 3], 0)
    body = trim(Image.fromarray(a.astype("uint8")))
    # Over twice a hex wide: it is huge, and spills over its neighbours.
    # Wesnoth centres an oversized sprite on its hex.
    w = 168
    body = body.resize((w, round(body.height * w / body.width)), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, max(HEX, body.height)), (0, 0, 0, 0))
    canvas.alpha_composite(body, (0, (canvas.height - body.height) // 2))
    for facing in FACINGS:
        save(canvas, out, f"images/units/sc/samatra-{facing}.png", True)
    save(canvas, out, "images/units/sc/samatra.png", True)
    build_samatra_comet(out)
    build_samatra_blobs(out)


def samatra_comet():
    """A yellow fiery comet heading north: a white-hot head, a flaming tail
    and a trail of shrinking fireballs, like UQM's (which it draws from
    masks)."""
    w, h = 26, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    hx, hy = w / 2 - 0.5, 11.0
    rng = np.random.default_rng(501)
    # tail: a cone widening back from the head, flickering along its length
    t = np.clip((yy - hy) / (h - hy - 4), 0, 1)
    flicker = 1 + 0.25 * np.sin(yy * 1.3 + rng.uniform(0, 6)) * t
    width = (8.0 * (1 - t) ** 0.7 + 0.5) * flicker
    tail = np.clip(1 - np.abs(xx - hx) / width, 0, 1) * (yy >= hy) * (1 - t) ** 1.2
    # head: a bright disc
    r = np.hypot(xx - hx, yy - hy)
    head = np.clip(1 - r / 8.5, 0, 1)
    heat = np.clip(np.maximum(head * 1.6, tail), 0, 1)
    # trailing fireballs, shrinking
    for cy, rad in ((34, 3.2), (44, 2.5), (53, 1.8)):
        heat = np.maximum(heat, 0.7 * np.clip(1 - np.hypot(xx - hx, yy - cy) / rad, 0, 1))
    # colour ramp: deep orange -> yellow -> white as heat rises
    red = np.full_like(heat, 255)
    green = 50 + 205 * np.clip(heat * 1.2, 0, 1) ** 1.5
    blue = 255 * np.clip((heat - 0.7) / 0.3, 0, 1)
    alpha = 255 * np.clip(heat * 1.8, 0, 1)
    img = np.dstack([red, green, blue, alpha]).astype("uint8")
    return Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.7))


def build_samatra_comet(out):
    comet = samatra_comet()
    for facing in ("n", "ne"):
        save(trim(rotated(comet, FACINGS[facing])), out,
             f"images/projectiles/sc/samatra-comet-{facing}.png", False)


def build_samatra_blobs(out):
    """The Sa-Matra's green blobs: lumpy glowing globs that ram ships off
    course. Drawn here, not taken from UQM."""
    blob = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(blob)
    lumps = ((12, 12, 1.0), (9, 10, 0.7), (15, 11, 0.65), (12, 15, 0.6), (11, 8, 0.55))
    for r, col in ((10, (40, 230, 60, 70)), (7, (60, 240, 80, 180)), (4, (190, 255, 170, 255))):
        for x, y, k in lumps:
            rr = r * k
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
    blob = blob.filter(ImageFilter.GaussianBlur(1))
    for facing in ("n", "ne"):
        save(rotated(blob, FACINGS[facing]) if facing == "ne" else blob, out,
             f"images/projectiles/sc/samatra-blob-{facing}.png", False)


# race id -> the ship's victory ditty (a tracker module) in the UQM content
DITTIES = {
    "earthling": "human/cruiser.mod", "chenjesu": "chenjesu/broodhome.mod",
    "mmrnmhrm": "mmrnmhrm/xform.mod", "yehat": "yehat/terminator.mod",
    "syreen": "syreen/penetrator.mod", "arilou": "arilou/skiff.mod",
    "shofixti": "shofixti/scout.mod", "urquan": "urquan/dreadnought.mod",
    "mycon": "mycon/podship.mod", "spathi": "spathi/eluder.mod",
    "umgah": "umgah/drone.mod", "vux": "vux/intruder.mod",
    "androsynth": "androsynth/guardian.mod", "ilwrath": "ilwrath/avenger.mod",
    "kohrah": "kohrah/marauder.mod", "druuge": "druuge/mauler.mod",
    "thraddash": "thraddash/torch.mod", "slylandro": "slylandro/probe.mod",
    "orz": "orz/nemesis.mod", "chmmr": "chmmr/avatar.mod",
    "zoqfotpik": "zoqfotpik/stinger.mod", "pkunk": "pkunk/fury.mod",
    "supox": "supox/blade.mod", "utwig": "utwig/jugger.mod",
    "precursor": "flagship/flagship.mod", "melnorme": "melnorme/trader.mod",
}


DITTY_LUFS = -6.0        # target loudness (EBU R128); the music is about -12 to -15
DITTY_MAX_BOOST = 12.0   # dB of gain at most past where the peaks reach the limiter
DITTY_DELAY_MS = 400     # starts after the ship's explosion, not on top of it


def build_ditties(uqm, out, remix=None):
    """Victory ditties: rendered from the .mod files with ffmpeg (libopenmpt),
    capped at 8 seconds in case a module loops, brought to the same loudness
    and delayed slightly so the explosion doesn't mask the start. A limiter
    catches the peaks, so the gain is corrected over a few passes; ditties
    with sharp peaks stop short of the target rather than being crushed.
    The Sa-Matra has no ditty of its own in UQM; it gets the Precursors'
    remix of the Kohr-Ah ditty."""
    import re
    import subprocess
    os.makedirs(os.path.join(out, "sounds/sc"), exist_ok=True)
    base = ["ffmpeg", "-hide_banner", "-y"]
    fade = "afade=t=out:st=7:d=1"

    def measure(path, af):
        probe = subprocess.run(base + ["-i", path, "-t", "9", "-af", af + "volumedetect,ebur128=framelog=quiet",
                                       "-f", "null", "-"], capture_output=True, text=True, check=True)
        peak = float(re.search(r"max_volume: (-?[\d.]+) dB", probe.stderr).group(1))
        lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", probe.stderr)[-1])
        return peak, lufs

    sources = {race: os.path.join(uqm, "base/ships", rel) for race, rel in DITTIES.items()}
    if remix:
        sources["samatra"] = os.path.join(remix, "remix/1/ditties/kohrah.ogg")
    for race, src in sources.items():
        dest = f"sounds/sc/ditty-{race}.ogg"
        peak, lufs = measure(src, fade + ",")
        max_gain = -1.0 - peak + DITTY_MAX_BOOST
        gain = min(DITTY_LUFS - lufs, max_gain)
        for _ in range(4):
            subprocess.run(base + ["-loglevel", "error", "-i", src, "-t", "8", "-af",
                                   f"{fade},volume={gain:.2f}dB,alimiter=limit=0.89:level=disabled,"
                                   f"adelay={DITTY_DELAY_MS}|{DITTY_DELAY_MS}",
                                   "-ac", "2", "-ar", "44100", "-q:a", "4", os.path.join(out, dest)],
                           check=True)
            miss = DITTY_LUFS - measure(os.path.join(out, dest), "")[1]
            if miss < 0.2 or gain >= max_gain:
                break
            gain = min(gain + miss, max_gain)
        manifest.append(dest)


# Music: each faction's races' Star Control II themes, plus SC2's victory music.
MUSIC = {
    # Alliance playlist
    "1. commander": "base/comm/commander/commander.mod",   # Earthlings
    "1. yehat": "base/comm/yehat/yehat.mod",
    "1. syreen": "base/comm/syreen/syreen.mod",
    "1. arilou": "base/comm/arilou/arilou.mod",
    "1. shofixti": "base/comm/shofixti/shofixti.mod",
    "1. intro": "base/cutscene/intro/introx.mod",          # SC2 opening
    "1. ending": "base/cutscene/ending/victoryf.mod",      # SC2 ending (final slideshow)
    "victory-fanfare": "base/cutscene/ending/victory1.mod",
    "1. quasispace": "base/nav/quasispace.mod",
    # Alliance and Hierarchy
    "0. starbase": "base/ui/starbase.mod",
    "1. outfit": "base/ui/outfit.mod",
    # Hierarchy playlist
    "2. urquan": "base/comm/urquan/urquan.mod",
    "2. mycon": "base/comm/mycon/mycon.mod",
    "2. spathi": "base/comm/spathi/spathi.mod",
    "2. umgah": "base/comm/umgah/umgah.mod",
    "2. vux": "base/comm/vux/vux.mod",
    "2. ilwrath": "base/comm/ilwrath/ilwrath.mod",
    "2. thraddash": "base/comm/thraddash/thraddash.mod",
    # (the New Alliance and the Death March play Precursors remixes: REMIXES)
}

MUSIC_GAIN_DB = {"0. starbase": 4, "1. quasispace": -2}   # match the other tracks' loudness

# Precursors' UQM Remix Packs (sourceforge.net/projects/sc2, "UQM Remix
# Packs"): the disc .uqm files unzipped into one directory, and packs 2 and
# 3's extras zips into its "extras2" and "extras3" subdirectories. They are mastered louder than
# the tracker modules, so each is brought to the same loudness.
REMIX_LOUDNESS = -16.7   # mean volume, dB, like the other music
REMIXES = {
    # Death March
    "4. kohrah-eternal-doctrine": "extras3/aliens/blackur-the_eternal_doctrine.ogg",
    "4. kohrah-battle": "extras3/battle/battle-Kohr-Ah.ogg",
    "4. kohrah-cleansing-required": "remix/3/07_-_Kohr-Ah_-_Cleansing_Required.ogg",
    "4. slylandro-we-come-in-peace": "remix/2/03_-_Slylandro_Probes_-_We_Come_In_Peace.ogg",
    "4. samatra-battle": "remix/1/05_-_Melee_-_The_Battle_of_the_Sa-Matra.ogg",
    "4. orz-squeezing-the-juice": "remix/4/10_-_Orz_-_Squeezing_the_Juice.ogg",
    "0. mycon-rebirth": "remix/3/05_-_Mycon_-_Rebirth.ogg",
    "0. ilwrath-all-evil": "remix/3/02_-_Ilwrath_-_All_Evil.ogg",
    "4. druuge-crimson-corporation": "remix/2/07_-_Druuge_-_Property_of_the_Crimson_Corporation.ogg",
    "0. thraddash-culture-19": "remix/3/06_-_Thraddash_-_Culture_19.ogg",
    # Hierarchy
    "2. urquan-now-and-forever": "remix/3/01_-_Ur-Quan_-_Now_and_Forever.ogg",
    "2. urquan-erol-otus": "extras3/aliens/urquan-Ur-Quan_by_Erol_Otus.ogg",
    "2. remix-spathi": "remix/2/08_-_Spathi_-_Safe_Haven.ogg",
    "2. remix-spathi-fwiffo": "remix/4/13_-_Spathi_-_Fwiffos_Starrunner.ogg",
    "2. remix-umgah": "remix/3/04_-_Umgah_-_Genetic_Modification.ogg",
    "2. remix-vux": "remix/3/03_-_VUX_-_Ultra-gross.ogg",
    "2. remix-vux-acid": "extras3/aliens/vux-acid_in_the_eye.ogg",
    # Alliance (Remixes and Both music modes)
    "1. remix-yehat": "remix/4/06_-_Yehat_-_Years_Late_Mix.ogg",
    "1. remix-shofixti": "remix/4/04_-_Shofixti_-_Bonsai!.ogg",
    # New Alliance: every track a remix
    "3. remix-chmmr": "remix/4/03_-_Chmmr_-_Photosynthesis.ogg",
    "3. remix-zoqfotpik": "remix/4/09_-_Zoq-Fot-Pik_-_Frungy_Party.ogg",
    "3. remix-pkunk": "remix/4/07_-_Pkunk_-_Pkunks_Not_Dead.ogg",
    "3. remix-supox": "remix/4/12_-_Supox_-_Shake_Yer_Rootz.ogg",
    "3. remix-utwig": "remix/4/08_-_Utwig_-_Mask_of_Ultimate_Embarrassment_and_Shame.ogg",
    "3. remix-utwig-ultron": "remix/4/11_-_Utwig_-_The_Ultron.ogg",
    "0. remix-commander": "remix/1/02_-_Starbase_Commander_-_Corridor_Nine.ogg",
    "0. remix-arilou": "remix/2/02_-_Arilou_-_Welcome_to_Falayalaralfali.ogg",
    "3. remix-melnorme": "remix/2/10_-_Melnorme_-_Turning_Purple.ogg",
    "0. remix-syreen": "remix/4/05_-_Syreen_-_Close_Encounters_of_the_Seventh_Kind.ogg",
    "0. remix-mystic-shadows": "extras2/extraspack/Bonus/arispace_bonus.ogg",   # quasispace
    "0. remix-quasispace": "remix/2/01_-_Quasispace_-_Through_the_Angles_of_Space.ogg",

    "0. remix-intro": "remix/4/02_-_Intro_-_Into_the_Void.ogg",
    "0. remix-ending": "remix/4/16_-_Outro_-_Awaking_Dreams.ogg",
    "0. remix-starbase": "remix/1/01_-_Starbase_-_Under_a_Red_Sky.ogg",
    "3. remix-outfit": "remix/1/06_-_Outfit_-_Outfit_the_Vindicator.ogg",
}


# Star Control II's 3DO soundtrack (UQM's "3domusic" add-on,
# uqm-0.8.0-3domusic.uqm), unzipped into one directory.
THREEDO = {
    "1. quasispace-3do": "3domusic/quasispace.ogg",
}


# Victory themes are played as sound effects (they follow the sound volume,
# not the music volume), so they go with the sounds.
VICTORY_THEMES = {"victory-fanfare"}


def music_dest(name):
    return f"{'sounds' if name in VICTORY_THEMES else 'music'}/sc/{name}.ogg"


def build_remixes(remix, out, only=None, table=None):
    """Remixes (or, with table=THREEDO, 3DO tracks) at REMIX_LOUDNESS."""
    import re
    import subprocess
    for name, rel in (table or REMIXES).items():
        if only and name not in only:
            continue
        src = os.path.join(remix, rel)
        probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True, check=True)
        mean = float(re.search(r"mean_volume: (-?[\d.]+) dB", probe.stderr).group(1))
        dest = music_dest(name)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src,
                        "-af", f"volume={REMIX_LOUDNESS - mean:.1f}dB", "-q:a", "4",
                        os.path.join(out, dest)], check=True)
        manifest.append(dest)


def build_music(uqm, out):
    import subprocess
    os.makedirs(os.path.join(out, "music/sc"), exist_ok=True)
    os.makedirs(os.path.join(out, "sounds/sc"), exist_ok=True)
    for name, rel in MUSIC.items():
        dest = music_dest(name)
        gain = MUSIC_GAIN_DB.get(name, 0)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", os.path.join(uqm, rel), "-t", "600", "-af", f"volume={gain}dB", "-q:a", "4",
                        os.path.join(out, dest)], check=True)
        manifest.append(dest)


def build_sounds(uqm, out):
    for sid, rel in SOUNDS.items():
        dest = f"sounds/sc/{sid}.wav"
        os.makedirs(os.path.join(out, "sounds/sc"), exist_ok=True)
        shutil.copyfile(os.path.join(uqm, rel), os.path.join(out, dest))
        manifest.append(dest)
    build_chmmr_sounds(out)


def read_wav(path):
    """8-bit mono UQM sample -> (float samples in -1..1, rate)."""
    with wave.open(path) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), np.uint8)
        return (raw.astype(np.float32) - 128) / 128, w.getframerate()


def write_wav(path, data, rate):
    data = np.clip(np.round(data * 128 + 128), 0, 255).astype(np.uint8)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def held(sample, rate, seconds, tail):
    """A weapon held down in UQM: the sample restarts every battle frame
    (24 per second), which turns the Chmmr laser into a long buzz. When the
    button is let go the last restart rings out for `tail` seconds."""
    step = rate // 24
    frames = int(seconds * 24)
    end = sample[:int(tail * rate)].copy()
    end *= np.linspace(1, 0, len(end)) ** 2
    return np.concatenate([sample[:step]] * frames + [end])


def build_chmmr_sounds(out):
    """Long laser (ranged) and tractor beam + laser (melee) for the Chmmr
    Avatar, made from the Chmmr's own laser and tractor samples."""
    snd = os.path.join(out, "sounds/sc")
    laser, rate = read_wav(os.path.join(snd, "chmmr-laser.wav"))
    tractor, _ = read_wav(os.path.join(snd, "chmmr-tractor.wav"))

    long_laser = held(laser, rate, 0.6, 0.3)
    write_wav(os.path.join(snd, "chmmr-laser-long.wav"), long_laser, rate)

    # The tractor beam hums under the whole shot, its sample looped end to
    # end; the laser joins once the beam has locked on.
    lead = int(0.15 * rate)
    mix = np.zeros(lead + len(long_laser), np.float32)
    hum = np.tile(tractor, len(mix) // len(tractor) + 1)[:len(mix)]
    hum[-len(tractor):] *= np.linspace(1, 0, len(tractor))
    mix += 1.2 * hum
    mix[lead:] += 0.8 * long_laser
    write_wav(os.path.join(snd, "chmmr-tractor-laser.wav"), mix, rate)
    manifest.extend(["sounds/sc/chmmr-laser-long.wav", "sounds/sc/chmmr-tractor-laser.wav"])


# ------------------------------------------------------- original terrain


def hex_mask(wdata):
    a = Image.open(os.path.join(wdata, "core/images/terrain/grass/green.png")).convert("RGBA")
    return np.array(a)[:, :, 3].astype(np.float32) / 255.0


def transition_masks(wdata):
    masks = {}
    for combo in TRANSITION_COMBOS:
        a = Image.open(os.path.join(wdata, f"core/images/terrain/grass/green-{combo}.png")).convert("RGBA")
        masks[combo] = np.array(a)[:, :, 3].astype(np.float32) / 255.0
    return masks


def fractal_noise(rng, size, octaves=5, base=4):
    """Smooth value noise in [0,1], `size` x `size`, tileable."""
    total = np.zeros((size, size), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        grid = rng.random((cells, cells)).astype(np.float32)
        layer = Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        # BICUBIC on a tiny grid is not wrap-aware; good enough for hex crops.
        total += amp * np.asarray(layer, np.float32) / 255.0
        norm += amp
        amp *= 0.5
    total /= norm
    total -= total.min()
    total /= max(total.max(), 1e-6)
    return total


HEX_VERTS = [(18, 0), (54, 0), (72, 36), (54, 72), (18, 72), (0, 36)]
# edge between vertex i and i+1, named by the neighbour it faces
HEX_EDGES = {"n": (0, 1), "ne": (1, 2), "se": (2, 3), "s": (3, 4), "sw": (4, 5), "nw": (5, 0)}


def _edge_distances():
    yy, xx = np.mgrid[0:HEX, 0:HEX].astype(np.float32) + 0.5
    out = {}
    for name, (i, j) in HEX_EDGES.items():
        (x1, y1), (x2, y2) = HEX_VERTS[i], HEX_VERTS[j]
        dx, dy = x2 - x1, y2 - y1
        t = np.clip(((xx - x1) * dx + (yy - y1) * dy) / (dx * dx + dy * dy), 0, 1)
        out[name] = np.sqrt((xx - x1 - t * dx) ** 2 + (yy - y1 - t * dy) ** 2)
    return out


EDGE_DIST = _edge_distances()
BORDER_DIST = np.minimum.reduce(list(EDGE_DIST.values()))


def calm_edges(noise, width=12.0):
    """Pull a [0,1] noise field to 0.5 near the hex border, so neighbouring
    tiles (picked at random) meet at the same value and no seam shows."""
    w = np.clip(BORDER_DIST / width, 0, 1)
    return 0.5 + (noise - 0.5) * w


def wavy_mask(rng, combo, peak, reach=34.0):
    """Fade that starts at strength `peak` on the hex edges in `combo` and
    dies out a random, wavy distance inside the hex."""
    out = np.zeros((HEX, HEX), np.float32)
    wobble = fractal_noise(rng, HEX, 3, 3)
    r = reach * (0.45 + 1.0 * wobble)
    for d in combo.split("-"):
        out = np.maximum(out, np.clip(1 - EDGE_DIST[d] / r, 0, 1) ** 1.3)
    return out * peak


def starfield(rng, density=1.0):
    """72x72 RGBA, opaque, deep-space colour with stars."""
    img = np.zeros((HEX, HEX, 4), np.float32)
    n = calm_edges(fractal_noise(rng, HEX, octaves=3, base=2))
    # Near-black with a faint cool tint, so space reads as a dark starfield.
    # (Wesnoth darkens hexes a selected ship cannot reach; on this dark a
    # base that shows mostly in the stars and gas, which still dim.)
    img[:, :, 0] = 7 + 5 * n
    img[:, :, 1] = 8 + 5 * n
    img[:, :, 2] = 13 + 8 * n
    img[:, :, 3] = 255
    pil = Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(pil)
    for _ in range(int(rng.integers(14, 24) * density)):
        x, y = rng.integers(0, HEX, 2)
        b = int(rng.choice([70, 90, 120, 160, 210], p=[0.35, 0.25, 0.2, 0.12, 0.08]))
        tint = rng.choice(["w", "b", "y", "r"], p=[0.6, 0.2, 0.15, 0.05])
        col = {"w": (b, b, b), "b": (b * 3 // 4, b * 4 // 5, b), "y": (b, b * 9 // 10, b * 3 // 4),
               "r": (b, b * 3 // 4, b * 3 // 4)}[tint]
        d.point((int(x), int(y)), fill=col + (255,))
        if b >= 200 and rng.random() < 0.6:
            dim = tuple(c // 3 for c in col) + (255,)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((int(x) + dx, int(y) + dy), fill=dim)
    return pil


def apply_mask(img, mask):
    a = np.array(img).astype(np.float32)
    a[:, :, 3] *= mask
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


NEBULA_A = np.array([60, 210, 120], np.float32)    # emerald
NEBULA_B = np.array([150, 230, 80], np.float32)    # lime


def nebula_layer(field, x0, y0):
    """Cloud-only RGBA crop from the big nebula field.

    Hexes are drawn independently, so the colour stays close to one mean
    value (no visible seams between neighbouring nebula hexes) and the
    variation is fine-grained wisps inside each hex.
    """
    n1, n2 = field
    a = n1[y0:y0 + HEX, x0:x0 + HEX]
    b = n2[y0:y0 + HEX, x0:x0 + HEX]
    mix = 0.45 + 0.25 * (b - 0.5)
    rgb = NEBULA_A[None, None] * (1 - mix[..., None]) + NEBULA_B[None, None] * mix[..., None]
    bright = 0.75 + 0.45 * (a - 0.5)
    rgb = rgb * bright[..., None]
    alpha = (0.62 + 0.2 * (a - 0.5)) * 255
    out = np.dstack([rgb, alpha])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def build_space(rng, mask, out):
    for v in range(11):
        name = "space" if v == 0 else f"space{v + 1}"
        save(apply_mask(starfield(rng), mask), out, f"images/terrain/sc/{name}.png", False)
    save(apply_mask(starfield(rng), mask), out, "images/terrain/sc/space-tile.png", False)


def build_nebula(rng, mask, tmasks, out):
    size = 512
    field = (fractal_noise(rng, size, 5, 24), fractal_noise(rng, size, 4, 12))
    for v in range(11):
        x0, y0 = rng.integers(0, size - HEX, 2)
        img = starfield(rng, 0.7)
        img.alpha_composite(nebula_layer(field, x0, y0))
        name = "nebula" if v == 0 else f"nebula{v + 1}"
        save(apply_mask(img, mask), out, f"images/terrain/sc/{name}.png", False)
        if v == 0:
            save(apply_mask(img, mask), out, "images/terrain/sc/nebula-tile.png", False)
    for combo, m in tmasks.items():
        x0, y0 = rng.integers(0, size - HEX, 2)
        layer = nebula_layer(field, x0, y0)
        # Soften the grass-shaped edge so it reads as gas, not a cut-out.
        soft = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)),
                        np.float32) / 255.0
        save(apply_mask(layer, soft * 0.9), out, f"images/terrain/sc/nebula-{combo}.png", False)


NEBULA_EDGE = 0.5   # gas strength exactly on a nebula/space hex edge
GAS_DENSITY = 0.7   # overall opacity of nebulae and dust (1 = original); lower shows more space

# name -> (base colour A, base colour B, highlight colour)
GAS_NEBULAE = {
    "nebula": ((60, 210, 120), (150, 230, 80), (90, 170, 255)),       # green, blue wisps
    "rednebula": ((225, 55, 40), (150, 25, 70), (255, 160, 50)),      # red, orange wisps
    "dust": ((150, 115, 75), (115, 90, 65), (200, 165, 115)),          # brown dust, pale streaks
}


GAS_PERIOD = (6, 4)    # gas clouds repeat every 6 columns and 4 rows of hexes
GAS_TERRAIN = {"nebula": "Yn", "rednebula": "Yr", "dust": "Yd"}
# Impassable blobs drawn the same way (their clouds are painted in
# make_barriers.py): dark nebula, radiation zone, plasma storm, gravity eddy.
BARRIER_GASES = {"darknebula": "Yqd", "radiation": "Yqr", "plasmastorm": "Yqp", "eddy": "Yqe"}
GAS_TERRAIN.update(BARRIER_GASES)
# hex offsets of each neighbour, for even and odd columns (odd ones sit lower)
NEIGHBOUR_OFFSETS = {
    0: {"n": (0, -1), "ne": (1, -1), "se": (1, 0), "s": (0, 1), "sw": (-1, 0), "nw": (-1, -1)},
    1: {"n": (0, -1), "ne": (1, 0), "se": (1, 1), "s": (0, 1), "sw": (-1, 1), "nw": (-1, 0)},
}


def _spill_wedges(soft=4.0):
    """Split the hex into soft wedges, one per edge, adding up to 1. A hex
    with several gas neighbours stacks one spill per neighbour; keeping each
    to its own wedge stops them adding up to a bright rim round the hex."""
    e = {d: np.exp(-EDGE_DIST[d] / soft) for d in HEX_EDGES}
    total = sum(e.values())
    return {d: e[d] / total for d in HEX_EDGES}


SPILL_WEDGE = _spill_wedges()


def periodic_fractal_noise(rng, width, height, octaves, cell):
    """fractal_noise over a width x height field that wraps round at its
    edges, with cells of about `cell` pixels in its coarsest octave."""
    total = np.zeros((height, width), np.float32)
    amp, norm = 1.0, 0.0
    cx, cy = max(1, round(width / cell)), max(1, round(height / cell))
    for o in range(octaves):
        grid = rng.random((cy << o, cx << o)).astype(np.float32)
        tiled = np.tile(grid, (3, 3))
        layer = Image.fromarray((tiled * 255).astype(np.uint8)).resize((3 * width, 3 * height), Image.BICUBIC)
        total += amp * np.asarray(layer, np.float32)[height:2 * height, width:2 * width] / 255.0
        norm += amp
        amp *= 0.5
    total /= norm
    total -= total.min()
    total /= max(total.max(), 1e-6)
    return total


def gas_hex_slice(col, row):
    """Pixel rows and columns of hex (col, row) of the gas field, wrapping."""
    w, h = GAS_PERIOD[0] * 54, GAS_PERIOD[1] * 72
    x0, y0 = 54 * col, 72 * row + (36 if col % 2 else 0)
    return np.ix_((np.arange(HEX) + y0) % h, (np.arange(HEX) + x0) % w)


def build_gas_nebula(rng, out, name, colours, painter=None, terrain=None):
    """Thin, wispy nebula: mostly transparent haze with brighter streaks and
    fine highlight filaments, so the dark of space shows through.

    Seamless: the gas is one big cloud that wraps round every GAS_PERIOD hexes,
    and each hex of a gas terrain shows the piece of it at its own place on
    the map (picked by the mod_x/mod_y rules in terrain/gas-tiles.cfg, which
    this script also writes). Neighbouring hexes are neighbouring pieces, so
    wisps run on across every hex edge, and no edge pattern repeats from hex
    to hex. Where gas meets anything else its edge thins out (the *-edge
    images) and wisps of it spill onto the neighbour, again cut from the
    cloud at the neighbour's place.
    """
    pc, pr = GAS_PERIOD
    w, h = pc * 54, pr * 72
    if painter is not None:
        return _cut_gas(rng, out, name, lambda col, row: painter(gas_hex_slice(col, row), col, row), terrain)
    col_a, col_b, col_hi = (np.array(c, np.float32) for c in colours)
    field = (periodic_fractal_noise(rng, w, h, 5, 33), periodic_fractal_noise(rng, w, h, 4, 66),
             periodic_fractal_noise(rng, w, h, 4, 26.5))
    mask = hex_mask_cache

    def gas(col, row):
        sl = gas_hex_slice(col, row)
        n1, n2, f2 = (f[sl] for f in field)
        streak = (1 - np.abs(2 * n1 - 1)) ** 3       # soft wisps
        fine = (1 - np.abs(2 * f2 - 1)) ** 22         # thin filaments
        mix = 0.5 + 0.5 * (n2 - 0.5)
        rgb = col_a[None, None] * (1 - mix[..., None]) + col_b[None, None] * mix[..., None]
        rgb = rgb * (0.75 + 0.5 * (n1 - 0.5) + 0.35 * streak)[..., None]
        rgb = rgb * (1 - 0.55 * fine[..., None]) + col_hi[None, None] * 0.55 * fine[..., None]
        alpha = np.clip(0.3 + 0.12 * (n1 - 0.5) + 0.3 * streak + 0.22 * fine, 0, 0.85) * GAS_DENSITY * 255
        return Image.fromarray(np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8), "RGBA")

    return _cut_gas(rng, out, name, gas, terrain)


def _cut_gas(rng, out, name, gas, terrain=None):
    """Cut a gas cloud into hex tiles, spills and edges, and return its rules.
    terrain, if given, is (terrains of the gas, terrains it spills onto,
    spill layer) for a gas that is not one of GAS_TERRAIN."""
    pc, pr = GAS_PERIOD
    mask = hex_mask_cache
    if terrain:
        types, others, layer = terrain
    else:
        code = GAS_TERRAIN[name]
        types = f"{code}*^*"
        others = ",".join(f"{t}*^*" for t in GAS_TERRAIN.values() if t != code)
        others = f"Ys*^*,Yif*^*,Yis*^*,Yk,Yc,Yi,Yi^*,{others}"
        layer = {"nebula": -310, "rednebula": -305, "dust": -320, "darknebula": -300,
                 "radiation": -302, "plasmastorm": -304, "eddy": -306}[name]
    rules = []
    for col in range(pc):
        for row in range(pr):
            img = starfield(rng, 0.9)
            img.alpha_composite(gas(col, row))
            stem = f"sc/gas/{name}-{col}-{row}"
            save(apply_mask(img, mask), out, f"images/terrain/{stem}.png", False)
            if (col, row) == (0, 0):
                save(apply_mask(img, mask), out, f"images/terrain/sc/{name}-tile.png", False)
            rules.append(f"{{SC_GAS_BASE ({types}) {col} {row} {stem}.png}}")
            layer_img = gas(col, row)
            for d, (dx, dy) in NEIGHBOUR_OFFSETS[col % 2].items():
                save(apply_mask(layer_img, wavy_mask(rng, d, NEBULA_EDGE) * SPILL_WEDGE[d] * mask), out,
                     f"images/terrain/{stem}-{d}.png", False)
                # one period on, so no position is negative (the rules
                # don't match with negative positions)
                rules.append(f"{{SC_GAS_SPILL ({others}) ({types}) {col + pc} {row + pr} "
                             f"{col + pc + dx} {row + pr + dy} "
                             f"{name}_spill_{d} {layer} {stem}-{d}.png}}")
    for combo in TRANSITION_COMBOS:
        save(apply_mask(starfield(rng, 0.9), wavy_mask(rng, combo, NEBULA_EDGE) * mask), out,
             f"images/terrain/sc/{name}-edge-{combo}.png", False)
    return rules


GAS_MACROS = """#define SC_GAS_BASE TERRAIN X Y IMAGE
    [terrain_graphics]
        mod_x={pc}
        mod_y={pr}
        [tile]
            x,y={{X}},{{Y}}
            type={{TERRAIN}}
            set_no_flag=base
            [image]
                name={{IMAGE}}
                layer=-1000
            [/image]
        [/tile]
    [/terrain_graphics]
#enddef

#define SC_GAS_CALM STORM STARS X Y NX NY IMAGE
    [terrain_graphics]
        mod_x={pc}
        mod_y={pr}
        [tile]
            x,y={{X}},{{Y}}
            type={{STORM}}
            set_no_flag=base
            [image]
                name={{IMAGE}}
                layer=-1000
            [/image]
        [/tile]
        [tile]
            x,y={{NX}},{{NY}}
            type={{STARS}}
        [/tile]
    [/terrain_graphics]
#enddef

#define SC_GAS_SPILL OTHERS GAS X Y NX NY FLAG LAYER IMAGE
    [terrain_graphics]
        mod_x={pc}
        mod_y={pr}
        [tile]
            x,y={{X}},{{Y}}
            type={{OTHERS}}
            set_no_flag={{FLAG}}
            [image]
                name={{IMAGE}}
                layer={{LAYER}}
            [/image]
        [/tile]
        [tile]
            x,y={{NX}},{{NY}}
            type={{GAS}}
        [/tile]
    [/terrain_graphics]
#enddef

"""


def build_gas(seed, out):
    rules = []
    for i, (name, colours) in enumerate(GAS_NEBULAE.items()):
        rules += build_gas_nebula(np.random.default_rng(seed + 10 + i), out, name, colours)
    # added later, with their own seeds, so the nebulae above stay the same
    w, h = GAS_PERIOD[0] * 54, GAS_PERIOD[1] * 72
    painters = gas_painters(np.random.default_rng(seed + 30), w, h, periodic_fractal_noise)
    for i, name in enumerate(BARRIER_GASES):
        rules += build_gas_nebula(np.random.default_rng(seed + 31 + i), out, name, None, painters[name])
    # Plasma storm hexes holding a star (a sun, a pulsar, or a big star over
    # several hexes), and the storm hexes next to them, show the storm
    # without its lightning, so no bolt comes near the star. Their own seed;
    # these rules come first so they win.
    crng = np.random.default_rng(seed + 40)
    calm, near = [], []
    stars = "Yqp^Yx*,Yqp^Ygg*,Yqp^Ysu*,Yqp^Ytsu"
    pc, pr = GAS_PERIOD
    for col in range(pc):
        for row in range(pr):
            img = starfield(crng, 0.9)
            img.alpha_composite(painters["plasmastorm-calm"](gas_hex_slice(col, row), col, row))
            stem = f"sc/gas/plasmastorm-calm-{col}-{row}"
            save(apply_mask(img, hex_mask_cache), out, f"images/terrain/{stem}.png", False)
            calm.append(f"{{SC_GAS_BASE ({stars}) {col} {row} {stem}.png}}")
            for dx, dy in NEIGHBOUR_OFFSETS[col % 2].values():
                near.append(f"{{SC_GAS_CALM (Yqp*^*) ({stars}) {col + pc} {row + pr} "
                            f"{col + pc + dx} {row + pr + dy} {stem}.png}}")
    rules = calm + near + rules
    with open(os.path.join(out, "terrain/gas-tiles.cfg"), "w") as f:
        f.write("#textdomain wesnoth-Star_Control_TC\n")
        f.write("# Generated by tools/make_art.py (build_gas); do not edit by hand.\n")
        f.write("# Nebulae, dust and the cloud-like barriers: each hex shows the piece of the cloud at its own place\n")
        f.write("# on the map, and spills wisps onto its neighbours, so clouds run on across\n")
        f.write("# hex edges.\n\n")
        f.write(GAS_MACROS.format(pc=GAS_PERIOD[0], pr=GAS_PERIOD[1]))
        f.write("\n".join(rules) + "\n\n#undef SC_GAS_BASE\n#undef SC_GAS_CALM\n#undef SC_GAS_SPILL\n")


# ---- badlands: a blue nebula, with plasma shallows ----
#
# All badlands are one blue nebula, drawn like the other gas clouds (see
# build_gas_nebula): a seamless cloud that thins out at its edges and spills
# wisps onto its neighbours. The badlands proper (Yi) glow brighter inside
# it, and in the thin badlands (Yif) a veil of dark space dims it. The glow
# and the veil are drawn as banks (below) that run on from hex to hex, so a
# stretch reads as one.
#
# Every hex near badlands draws its piece of a smooth field
#   f(p) = sum_k w(|p - c_k|) s_k / sum_k w(|p - c_k|)
# over the hex centres c_k around it, with s_k = +1 for badlands and -1 for
# anything else, and the bank is the line f = 0. The kernel w reaches 68px,
# less than the 72px from any point of a hex to the nearest centre beyond its
# six neighbours, so a hex can work out f exactly from itself and its
# neighbours, and two hexes agree on f along the edge they share: the lines
# join. One image per pattern of badlands neighbours (127 per bank), picked
# by the rules in terrain/badlands-banks.cfg, which this script also writes.
#
# The banks wobble two ways without breaking the joins: a fixed wiggle along
# each kind of hex edge (the same on both sides of every edge), and random
# meanders inside the hex that fade out before its border.
# Neither bank has a bank line: the thin badlands' veil and the badlands'
# glow just fade in across the border.

BANK_DIRS = ["n", "ne", "se", "s", "sw", "nw"]
BANK_OFFSETS = {"n": (0, -72), "ne": (54, -36), "se": (54, 36), "s": (0, 72), "sw": (-54, 36), "nw": (-54, -36)}
BANK_REACH = 68.0
BANK_PAD = 4          # extra pixels round the hex so gradients are exact at its edge
BANK_VARIATIONS = 2
# name -> (terrains inside, line, glow, haze colour, line, glow, haze opacity,
#          inner flow lines, layer, seed, plasma inside (lightning, wisps) or None)
BANKS = {
    "thin": ("Yif,Yif^*", (150, 205, 245), (70, 140, 220), (9, 10, 17),
             0.0, 0.0, 0.45, [], -300, 21, None),
    "deep": ("Yi,Yi^*", (170, 210, 255), (110, 160, 255), (60, 110, 220),
             0.0, 0.32, 0.19, [], -299, 31, None),
}
# The badlands' nebula: deep blue, violet, pale blue wisps
BADLANDS_NEBULA = ((40, 90, 210), (70, 60, 190), (140, 200, 255))
NEBULA_BADLANDS = "Yi,Yi^*,Yis,Yis^*,Yif,Yif^*"
NOT_NEBULA_BADLANDS = "Ys*^*,Yk,Yc,Yn*^*,Yr*^*,Yd*^*,Yqd*^*,Yqr*^*,Yqp*^*,Yqe*^*"


def _smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class _BankGeometry:
    def __init__(self):
        p = BANK_PAD
        yy, xx = np.mgrid[-p:HEX + p, -p:HEX + p].astype(np.float32) + 0.5
        self.px, self.py = xx - HEX / 2, yy - HEX / 2

        def kern(dx, dy):
            r2 = ((self.px - dx) ** 2 + (self.py - dy) ** 2) / BANK_REACH ** 2
            return np.clip(1 - r2, 0, None) ** 2
        self.kc = kern(0, 0)
        self.kn = {d: kern(*o) for d, o in BANK_OFFSETS.items()}
        self.ksum = self.kc + sum(self.kn.values())
        verts = [(-18, -36), (18, -36), (36, 0), (18, 36), (-18, 36), (-36, 0)]
        self.edist, self.et = {}, {}
        for d, (i, j) in HEX_EDGES.items():
            a, b = verts[i], verts[j]
            # measure along the edge from its upper (then left) end, so the
            # two hexes sharing an edge agree on where along it a point is
            if (a[1], a[0]) > (b[1], b[0]):
                a, b = b, a
            (x1, y1), (x2, y2) = a, b
            dx, dy = x2 - x1, y2 - y1
            t = np.clip(((self.px - x1) * dx + (self.py - y1) * dy) / (dx * dx + dy * dy), 0, 1)
            self.edist[d] = np.sqrt((self.px - x1 - t * dx) ** 2 + (self.py - y1 - t * dy) ** 2)
            self.et[d] = t
        self.border = np.minimum.reduce(list(self.edist.values()))

    def edge_wobble(self, rng, amp, width=9.0):
        """The same wiggle on every edge of one orientation (n/s, ne/sw,
        nw/se). Zero near the corners and flat across the edge itself."""
        out = np.zeros_like(self.px)
        waves = [(rng.uniform(1.0, 2.0), rng.uniform(2.0, 3.5), *rng.uniform(0, 2 * np.pi, 2),
                  rng.choice([-1, 1])) for _ in range(3)]
        kind = {"n": 0, "s": 0, "ne": 1, "sw": 1, "nw": 2, "se": 2}
        for d in BANK_DIRS:
            k1, k2, p1, p2, sign = waves[kind[d]]
            t = self.et[d]
            bump = _smoothstep((t - 0.2) / 0.15) * _smoothstep((0.8 - t) / 0.15)
            g = sign * (0.7 * np.sin(np.pi * k1 * t + p1) + 0.3 * np.sin(np.pi * k2 * t + p2)) * bump
            band = np.where(self.edist[d] < width, 0.5 * (1 + np.cos(np.pi * self.edist[d] / width)), 0)
            out += band * g
        return out * amp

    def meander(self, rng, amp):
        """Random wobble inside the hex, gone (with a flat slope) at its border."""
        size, n = 200, HEX + 2 * BANK_PAD
        noise = fractal_noise(rng, size, 2, 3)
        x0, y0 = rng.integers(0, size - n, 2)
        noise = noise[y0:y0 + n, x0:x0 + n] - 0.5
        return noise * 2 * amp * _smoothstep((self.border - 2) / 16) ** 2

    def field(self, centre, neighbours):
        f = self.kc * (1 if centre else -1)
        for d, inside in zip(BANK_DIRS, neighbours):
            f = f + self.kn[d] * (1 if inside else -1)
        return f / self.ksum


def bank_layer(f, style, plasma=None):
    """RGBA image of the bank, from the field f (positive inside), with the
    plasma alpha (if any) fading in across it."""
    line_c, glow_c, haze_c, line_a, glow_a, haze_a, flows = style
    gy, gx = np.gradient(f)
    d = f / np.maximum(np.sqrt(gx * gx + gy * gy), 1e-4)    # ~ pixels from the bank
    p = BANK_PAD
    d = d[p:-p, p:-p]
    rgb = np.zeros(d.shape + (3,), np.float32)
    a = np.zeros(d.shape, np.float32)

    def over(colour, alpha):
        nonlocal rgb, a
        alpha = np.clip(alpha, 0, 1)
        out_a = alpha + a * (1 - alpha)
        rgb = (np.array(colour, np.float32) * alpha[..., None] + rgb * (a * (1 - alpha))[..., None]) \
            / np.maximum(out_a, 1e-6)[..., None]
        a = out_a

    over(haze_c, haze_a * _smoothstep(d / 6.0))
    if plasma is not None:
        over(PLASMA_COLOUR, plasma * _smoothstep((d + 2) / 9.0))
    # glow reaches well inside the bank and only a little outside it
    over(glow_c, glow_a * np.exp(-np.abs(d) / np.where(d > 0, 7.0, 2.0)))
    for offset, alpha in flows:
        over(line_c, alpha * np.exp(-((d - offset) / 0.8) ** 2))
    over(line_c, line_a * np.exp(-(d / 1.4) ** 2))
    img = np.dstack([rgb, a * 255 * hex_mask_cache])
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")


def bank_patterns():
    """(centre inside?, neighbours inside? n..nw) for every hex that has a
    piece of a bank: badlands hexes, and other hexes next to badlands."""
    for centre in (True, False):
        for neighbours in itertools.product((False, True), repeat=6):
            if centre or any(neighbours):
                yield centre, neighbours


def bank_code(centre, neighbours):
    return ("in" if centre else "out") + "-" + "".join("1" if v else "0" for v in neighbours)


PLASMA_COLOUR = (175, 215, 255)
# Sharpness of the plasma: higher powers draw thinner lightning (ridge) and
# narrower wisps (streak), so less of the starfield is covered.
PLASMA_RIDGE, PLASMA_STREAK = 16, 5


def lattice_noise(rng, max_k=4):
    """72x72 noise that repeats exactly from one hex to the next: a sum of
    waves whose wavelengths fit the hex lattice (steps of 54,36 and 0,72),
    so it runs on across any hex border without a seam. Returns z-scores."""
    yy, xx = np.mgrid[0:HEX, 0:HEX].astype(np.float32) + 0.5
    out = np.zeros((HEX, HEX), np.float32)
    for m in range(-max_k, max_k + 1):
        for n in range(-max_k, max_k + 1):
            kx, ky = 2 * np.pi * (m / 54 - n / 108), 2 * np.pi * n / 72
            k = math.hypot(kx, ky)
            if k == 0 or (m, n) < (0, 0):
                continue
            out += rng.normal() / k ** 1.3 * np.cos(kx * xx + ky * yy + rng.uniform(0, 2 * np.pi))
    return (out - out.mean()) / out.std()


_LATTICE = {}


def plasma_alpha(rng, field, strength, wisps):
    """Alpha of the white plasma inside badlands: soft wisps plus sharp
    lightning. Each tile's own noise takes over from a shared noise that
    repeats from hex to hex, so the plasma flows across hex borders with no
    seam, and every tile's noise is scaled alike so all look equally stormy."""
    if not _LATTICE:
        lrng = np.random.default_rng(77)
        _LATTICE["a"], _LATTICE["b"] = lattice_noise(lrng), lattice_noise(lrng)
    size = field[0].shape[0]
    x0, y0 = rng.integers(0, size - HEX, 2)
    w = _smoothstep(BORDER_DIST / 20.0)
    blended = []
    for f, key in ((field[0], "a"), (field[1], "b")):
        own = f[y0:y0 + HEX, x0:x0 + HEX]
        own = (own - own.mean()) / max(float(own.std()), 1e-4)
        z = (w * own + (1 - w) * _LATTICE[key]) / np.sqrt(w * w + (1 - w) ** 2)
        blended.append(np.clip(0.5 + 0.17 * z, 0, 1))
    a, b = blended
    ridge = (1 - np.abs(2 * a - 1)) ** PLASMA_RIDGE
    streak = (1 - np.abs(2 * b - 1)) ** PLASMA_STREAK
    return np.clip(0.75 * ridge * strength + streak * wisps * 1.25, 0, 1)


def build_badlands(rng, out):
    sc = "images/terrain/sc"
    geo = _BankGeometry()
    rules = []
    tiles = {}
    field = (fractal_noise(rng, 512, 5, 10), fractal_noise(rng, 512, 4, 12))
    for name, (inside, *style) in BANKS.items():
        style, layer, seed, plasma = tuple(style[:7]), style[7], style[8], style[9]
        brng = np.random.default_rng(seed)
        wobble = geo.edge_wobble(brng, 0.25)
        meanders = [geo.meander(brng, 0.35) for _ in range(BANK_VARIATIONS)]
        plasmas = [plasma_alpha(brng, field, *plasma) if plasma else None for _ in range(BANK_VARIATIONS)]
        outside = "!," + inside
        for centre, neighbours in bank_patterns():
            code = bank_code(centre, neighbours)
            f = geo.field(centre, neighbours) + wobble
            for v, (m, pl) in enumerate(zip(meanders, plasmas)):
                save(bank_layer(f + m, style, pl), out, f"{sc}/badlands/{name}-{code}-{v + 1}.png", False)
            types = [inside if centre else outside] + [inside if n else outside for n in neighbours]
            rules.append(f"{{SC_BANK sc_bank_{name} {layer} sc/badlands/{name}-{code} "
                         + " ".join(f"({t})" for t in types) + "}")
        tiles[name] = bank_layer(geo.field(True, (False,) * 6) + wobble, style, plasmas[0])

    # The blue nebula (its own seed, so the banks above don't change with it).
    nebula = build_gas_nebula(np.random.default_rng(555), out, "badlands", BADLANDS_NEBULA,
                              terrain=(NEBULA_BADLANDS, NOT_NEBULA_BADLANDS, -309))

    # Symbol images for the editor and help: one lone hex of each kind.
    tile = lambda rel: Image.open(os.path.join(out, f"{sc}/{rel}.png")).convert("RGBA")
    img = tile("badlands-tile")
    img.alpha_composite(tiles["thin"])
    save(apply_mask(img, hex_mask_cache), out, f"{sc}/ionstorm-thin-tile.png", False)
    save(tile("badlands-tile"), out, f"{sc}/ionstorm-light-tile.png", False)
    img = tile("badlands-tile")
    img.alpha_composite(tiles["deep"])
    save(apply_mask(img, hex_mask_cache), out, f"{sc}/ionstorm-tile.png", False)

    build_planet_halos(rng, out)

    with open(os.path.join(out, "terrain/badlands-banks.cfg"), "w") as f:
        f.write("#textdomain wesnoth-Star_Control_TC\n")
        f.write("# Generated by tools/make_art.py (build_badlands); do not edit by hand.\n")
        f.write("# One rule per pattern of badlands around a hex: the hex itself, then\n")
        f.write("# its n, ne, se, s, sw and nw neighbours.\n\n")
        f.write(BANK_MACRO)
        f.write("\n".join(rules) + "\n\n#undef SC_BANK\n\n")
        f.write("# The blue nebula of all badlands: its edge thins out to whatever is\n")
        f.write("# next to it, then each hex shows its piece of the cloud and spills\n")
        f.write("# wisps of it onto its neighbours (as in gas-tiles.cfg).\n")
        f.write(f"{{TRANSITION_COMPLETE_LF ({NOT_NEBULA_BADLANDS}) ({NEBULA_BADLANDS}) -341 badlands_edge sc/badlands-edge}}\n\n")
        f.write(GAS_MACROS.format(pc=GAS_PERIOD[0], pr=GAS_PERIOD[1]))
        f.write("\n".join(nebula) + "\n\n#undef SC_GAS_BASE\n#undef SC_GAS_SPILL\n")


def build_planet_halos(rng, out, count=3):
    """Sea planets (^Vys, out in the badlands): a crackling ring of white plasma just outside the
    planet (drawn behind it), so they stand apart from planets in open space."""
    yy, xx = np.mgrid[0:HEX, 0:HEX].astype(np.float32) + 0.5
    dx, dy = xx - HEX / 2, yy - HEX / 2
    r = np.sqrt(dx * dx + dy * dy)
    ang = (np.arctan2(dy, dx) + np.pi) / (2 * np.pi)          # 0..1 round the ring
    for v in range(count):
        n = fractal_noise(rng, 256, 4, 6)
        # sample the noise along the ring (wrapping), so the flicker is seamless
        idx = (ang * 255).astype(int) % 256
        flick = n[idx, (np.clip(r, 0, 35) * 7).astype(int) % 256]
        wobble = 5.0 * (n[idx, 40] - 0.5)
        ridge = (1 - np.abs(2 * flick - 1)) ** 3
        ring = np.exp(-((r - 30 - wobble) / 1.3) ** 2)
        glow = np.exp(-((r - 29) / 4.0) ** 2)
        alpha = np.clip(ring * (0.1 + 0.9 * ridge) + glow * 0.22, 0, 1)
        rgb = np.zeros((HEX, HEX, 3), np.float32)
        rgb[..., 0] = 170 + 80 * ring
        rgb[..., 1] = 210 + 45 * ring
        rgb[..., 2] = 255
        img = np.dstack([rgb, alpha * 255 * hex_mask_cache])
        name = "planet-halo" if v == 0 else f"planet-halo{v + 1}"
        save(Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA"), out, f"images/terrain/sc/{name}.png", False)


BANK_MACRO = """#define SC_BANK FLAG LAYER IMAGESTEM C N NE SE S SW NW
    [terrain_graphics]
        map="
,  2
7,   3
,  1
6,   4
,  5"
        [tile]
            pos=1
            type={C}
            set_no_flag={FLAG}
            [image]
                name={IMAGESTEM}-@V.png
                variations="1;2"
                layer={LAYER}
            [/image]
        [/tile]
        [tile]
            pos=2
            type={N}
        [/tile]
        [tile]
            pos=3
            type={NE}
        [/tile]
        [tile]
            pos=4
            type={SE}
        [/tile]
        [tile]
            pos=5
            type={S}
        [/tile]
        [tile]
            pos=6
            type={SW}
        [/tile]
        [tile]
            pos=7
            type={NW}
        [/tile]
    [/terrain_graphics]
#enddef

"""



def shaded_sphere(rng, diameter, palette, kind):
    """Lit planet sphere on a transparent square canvas."""
    s = diameter + 8
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    c = (s - 1) / 2
    r = diameter / 2
    nx, ny = (xx - c) / r, (yy - c) / r
    d2 = nx ** 2 + ny ** 2
    inside = d2 <= 1
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    light = np.array([-0.55, -0.55, 0.63])
    light /= np.linalg.norm(light)
    lam = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    shade = 0.12 + 0.88 * lam
    tex = fractal_noise(rng, s, 5, 3)
    if kind == "gas":
        bands = np.sin((ny + 0.15 * (tex - 0.5)) * 9.0) * 0.5 + 0.5
        t = bands
    else:
        t = tex
    cols = np.array(palette, np.float32)
    idx = np.clip(t * (len(cols) - 1), 0, len(cols) - 1.001)
    lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    rgb = cols[lo] * (1 - f) + cols[lo + 1] * f
    rgb *= shade[..., None]
    alpha = np.where(inside, 255, 0).astype(np.float32)
    # anti-alias the rim
    edge = np.clip((1 - np.sqrt(d2)) * r, 0, 1)
    alpha = np.where(d2 <= 1.2, 255 * edge, 0)
    img = Image.fromarray(np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8), "RGBA")
    return img


PLANETS = [
    ("terran", "rock", [(20, 60, 140), (30, 90, 170), (60, 130, 70), (110, 150, 80), (200, 200, 190)], (120, 170, 255)),
    ("desert", "rock", [(120, 60, 25), (180, 110, 50), (220, 170, 90), (240, 210, 150)], (255, 190, 120)),
    ("ice", "rock", [(140, 170, 200), (190, 215, 235), (235, 245, 255), (255, 255, 255)], (200, 230, 255)),
    ("gas", "gas", [(150, 100, 60), (210, 170, 110), (240, 220, 180), (190, 130, 80), (230, 200, 150)], (255, 220, 170)),
    ("lava", "rock", [(30, 15, 15), (60, 25, 20), (200, 60, 10), (255, 170, 40)], (255, 120, 60)),
    ("barren", "rock", [(70, 70, 75), (110, 105, 100), (150, 145, 140), (190, 185, 180)], None),
]


def build_planets(rng, out):
    for i, (name, kind, pal, glow) in enumerate(PLANETS):
        dia = 38 if kind != "gas" else 46
        sphere = shaded_sphere(rng, dia, pal, kind)
        canvas = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
        if glow:
            g = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse([36 - dia / 2 - 3, 36 - dia / 2 - 3, 36 + dia / 2 + 3, 36 + dia / 2 + 3],
                                      fill=glow + (110,))
            canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(3)))
        canvas.alpha_composite(sphere, ((HEX - sphere.width) // 2, (HEX - sphere.height) // 2))
        if kind == "gas" and rng.random() < 2:
            ring = Image.new("RGBA", (HEX * 2, HEX * 2), (0, 0, 0, 0))
            rd = ImageDraw.Draw(ring)
            rd.ellipse([18, 52, HEX * 2 - 18, HEX * 2 - 52], outline=(220, 200, 160, 170), width=4)
            ring = ring.resize((HEX, HEX), Image.LANCZOS).rotate(-18, resample=Image.BICUBIC)
            # draw ring in front only on the lower half
            front = np.array(ring)
            front[: HEX // 2 + 2, :, 3] = 0
            back = np.array(ring)
            back[HEX // 2 + 2:, :, 3] = 0
            base = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
            base.alpha_composite(Image.fromarray(back))
            base.alpha_composite(canvas)
            base.alpha_composite(Image.fromarray(front))
            canvas = base
        if kind == "gas":
            # drawn (so the planets after it stay the same) but not used:
            # gas giants are impassable four-hex barriers, not planets to capture
            continue
        vname = "planet" if i == 0 else f"planet{i + 1}"
        save(canvas, out, f"images/terrain/sc/{vname}.png", False)
        if i == 0:
            save(canvas, out, "images/terrain/sc/planet-tile.png", False)


def spend_old_asteroid_draws(rng):
    """The asteroid art now comes from make_asteroids.py with its own seed.
    The first asteroid fields were drawn from the shared generator here, so
    make the same random draws they did, keeping the star and starbase art
    that is drawn after them byte-identical."""
    for _v in range(6):
        placed = []
        for _ in range(int(rng.integers(7, 11))):
            size = int(rng.choice([5, 6, 8, 10, 12, 14], p=[0.15, 0.2, 0.2, 0.2, 0.15, 0.1]))
            for _try in range(30):
                x, y = rng.uniform(10, 62), rng.uniform(9, 63)
                if abs(x - 36) + abs(y - 36) * 0.6 > 32:
                    continue
                if all((x - px) ** 2 + (y - py) ** 2 > (size + ps + 2) ** 2 for px, py, ps in placed):
                    break
            placed.append((x, y, size))
            # the old rock(): outline points, texture noise, rotation
            n = int(rng.integers(7, 11))
            for _k in range(n):
                rng.uniform(-0.2, 0.2)
                rng.uniform(0.65, 1.0)
            fractal_noise(rng, size * 2 + 4, 3, 2)
            rng.uniform(0, 360)


STAR_SIZE = 128   # bigger than a hex, so the glow fades out past the hex edge


# Coloured suns for plasma storms: (corona rgb, core rgb), picked per hex.
STORM_STARS = [((90, 150, 255), (220, 235, 255)),    # blue
               ((80, 235, 120), (215, 255, 220))]    # green
# ...a purple one for gravity eddies and an orange one for dust clouds
OTHER_STARS = {"star-eddy": ((185, 90, 255), (235, 210, 255)),
               "star-dust": ((255, 140, 30), (255, 220, 160))}
# The suns at the heart of plasma storms, each its own: corona and core
# colours, the core's radius and how many rays the corona has (^Yxs1 to
# ^Yxs6 always draw the same one; a plain ^Yx in a plasma storm picks one).
PLASMA_STARS = [((90, 150, 255), (220, 235, 255), 17, (11, 7)),     # blue giant
                ((235, 240, 255), (255, 255, 255), 11, (13, 5)),    # small white dwarf
                ((150, 110, 255), (225, 215, 255), 15, (9, 4)),     # violet
                ((60, 220, 255), (210, 250, 255), 20, (7, 11)),     # big cyan
                ((255, 110, 200), (255, 220, 240), 14, (11, 3)),    # pink
                ((255, 205, 120), (255, 245, 215), 13, (15, 6))]    # pale gold


def star_image(tex, corona_rgb=None, core_rgb=None, core_r=17, rays=(11, 7)):
    """A sun on a STAR_SIZE square: a white-hot core in a rayed corona and a
    soft glow that fades out beyond its hex. Yellow unless given colours."""
    s = STAR_SIZE
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    c = (s - 1) / 2
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    ang = np.arctan2(yy - c, xx - c)
    rays = 0.5 + 0.5 * np.sin(ang * rays[0] + 1.3) * np.sin(ang * rays[1])
    corona = np.clip(1 - (d - core_r) / (11 + 9 * rays), 0, 1) ** 1.6
    glow = np.clip(1 - (d - core_r) / (s / 2 - core_r - 2), 0, 1) ** 2.4 * 0.55
    core = np.clip(core_r + 1 - d, 0, 1)
    rgb = np.zeros((s, s, 3), np.float32)
    if corona_rgb is None:
        rgb[..., 0] = 255
        rgb[..., 1] = 150 + 100 * core * (0.6 + 0.4 * tex) + 40 * (1 - core) * np.maximum(corona, glow)
        rgb[..., 2] = 40 + 170 * core * np.clip(1 - d / core_r, 0, 1) ** 0.7
    else:
        hot = (core * (0.75 + 0.25 * tex) * np.clip(1 - d / core_r, 0, 1) ** 0.5)[..., None]
        rim = core[..., None] * (1 - hot)
        rgb = (np.array(corona_rgb, np.float32) * (1 - core[..., None])
               + np.array(core_rgb, np.float32) * 0.85 * rim + 255 * hot)
    alpha = 255 * np.maximum.reduce([core, corona * 0.85, glow])
    return Image.fromarray(np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8), "RGBA")


def build_star(rng, out):
    """The yellow sun and the coloured storm suns, drawn centred on their
    hex (terrain-graphics.cfg)."""
    s = STAR_SIZE
    # (the same draws as before, so the art built after the star stays the same)
    tex = np.asarray(Image.fromarray((fractal_noise(rng, HEX, 4, 4) * 255).astype(np.uint8))
                     .resize((s, s), Image.BICUBIC), np.float32) / 255
    img = star_image(tex)
    save(img, out, "images/terrain/sc/star.png", False)
    for i, (corona_rgb, core_rgb) in enumerate(STORM_STARS):
        save(star_image(tex, corona_rgb, core_rgb), out,
             f"images/terrain/sc/star-storm{i + 2}.png", False)
    for name, (corona_rgb, core_rgb) in OTHER_STARS.items():
        save(star_image(tex, corona_rgb, core_rgb), out, f"images/terrain/sc/{name}.png", False)
    for i, (corona_rgb, core_rgb, core_r, rays) in enumerate(PLASMA_STARS):
        save(star_image(tex, corona_rgb, core_rgb, core_r, rays), out,
             f"images/terrain/sc/star-plasma{i + 1}.png", False)
    tile = apply_mask(starfield(rng), hex_mask_cache)
    o = (s - HEX) // 2
    tile.alpha_composite(img.crop((o, o, o + HEX, o + HEX)))
    save(apply_mask(tile, hex_mask_cache), out, "images/terrain/sc/star-tile.png", False)


def build_starbase(rng, mask, out):
    # Keep: a station - outer ring, spokes, glowing hub.
    big = 4
    S = HEX * big
    st = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    c = S / 2
    R = 25 * big
    for k in range(6):
        a = math.radians(30 + 60 * k)
        d.line([c, c, c + R * math.cos(a), c + R * math.sin(a)], fill=(120, 130, 150, 255), width=3 * big)
    d.ellipse([c - R, c - R, c + R, c + R], outline=(150, 160, 180, 255), width=5 * big)
    d.ellipse([c - R + 4 * big, c - R + 4 * big, c + R - 4 * big, c + R - 4 * big], outline=(70, 80, 100, 255),
              width=1 * big)
    d.ellipse([c - 8 * big, c - 8 * big, c + 8 * big, c + 8 * big], fill=(90, 100, 125, 255),
              outline=(170, 180, 200, 255), width=big)
    d.ellipse([c - 4 * big, c - 4 * big, c + 4 * big, c + 4 * big], fill=(120, 220, 255, 255))
    for k in range(12):
        a = math.radians(15 + 30 * k)
        x, y = c + R * math.cos(a), c + R * math.sin(a)
        col = (255, 80, 80, 255) if k % 3 == 0 else (255, 230, 150, 255)
        d.ellipse([x - 1.5 * big, y - 1.5 * big, x + 1.5 * big, y + 1.5 * big], fill=col)
    st = st.resize((HEX, HEX), Image.LANCZOS)
    glow = st.filter(ImageFilter.GaussianBlur(2))
    keep = starfield(rng)
    keep.alpha_composite(glow)
    keep.alpha_composite(st)
    save(apply_mask(keep, mask), out, "images/terrain/sc/starbase.png", False)
    save(apply_mask(keep, mask), out, "images/terrain/sc/starbase-tile.png", False)

    # Dock (castle): a lit hexagonal docking frame.
    for v in range(3):
        dock = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dock)
        r1 = 30 * big
        pts = [(c + r1 * math.cos(math.radians(60 * k)), c + r1 * math.sin(math.radians(60 * k))) for k in range(6)]
        dd.polygon(pts, outline=(70, 160, 210, 230), width=2 * big)
        r2 = 22 * big
        pts2 = [(c + r2 * math.cos(math.radians(60 * k)), c + r2 * math.sin(math.radians(60 * k))) for k in range(6)]
        dd.polygon(pts2, outline=(50, 90, 130, 160), width=big)
        for (x, y) in pts:
            dd.ellipse([x - 2 * big, y - 2 * big, x + 2 * big, y + 2 * big], fill=(140, 230, 255, 255))
        dock = dock.resize((HEX, HEX), Image.LANCZOS)
        tile = starfield(rng)
        tile.alpha_composite(dock.filter(ImageFilter.GaussianBlur(1.5)))
        tile.alpha_composite(dock)
        name = "dock" if v == 0 else f"dock{v + 1}"
        save(apply_mask(tile, mask), out, f"images/terrain/sc/{name}.png", False)
        if v == 0:
            save(apply_mask(tile, mask), out, "images/terrain/sc/dock-tile.png", False)


def build_attack_icons(out):
    """60x60 attack icons: the projectile on a dark disc."""
    sources = {pid: (f"images/projectiles/sc/{pid}-ne.png", True) for pid in PROJECTILES}
    sources.update({lid: (f"images/projectiles/sc/{lid}-ne.png", False) for lid in LASERS})
    sources["blazer"] = ("images/units/sc/androsynth-blazer-l1-ne.png", True)
    sources["samatra-comet"] = ("images/projectiles/sc/samatra-comet-ne.png", False)
    sources["samatra-blob"] = ("images/projectiles/sc/samatra-blob-ne.png", False)
    for iid, (rel, uqm) in sources.items():
        item = trim(Image.open(os.path.join(out, rel)).convert("RGBA"))
        k = 44 / max(item.size)
        item = item.resize((max(1, round(item.width * k)), max(1, round(item.height * k))), Image.LANCZOS)
        icon = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(icon)
        d.ellipse([1, 1, 58, 58], fill=(8, 10, 28, 255), outline=(90, 110, 160, 255), width=2)
        icon.alpha_composite(item, ((60 - item.width) // 2, (60 - item.height) // 2))
        save(icon, out, f"images/attacks/sc/{iid}.png", uqm)


hex_mask_cache = None


def build_terrain(rng, mask, tmasks, args):
    """All terrain art (original, needs no UQM content)."""
    build_space(rng, mask, args.out)
    build_nebula(rng, mask, tmasks, args.out)
    build_planets(rng, args.out)
    spend_old_asteroid_draws(rng)
    build_star(rng, args.out)
    build_starbase(rng, mask, args.out)
    # Added later with its own seed so the art above stays byte-identical.
    build_gas(args.seed, args.out)
    build_badlands(np.random.default_rng(args.seed + 4), args.out)
    build_asteroid_art(np.random.default_rng(args.seed + 20), args.out, save, TRANSITION_COMBOS, mask)
    build_barrier_objects(np.random.default_rng(args.seed + 40), args.out, save, apply_mask, starfield, mask)


def main():
    global hex_mask_cache
    ap = argparse.ArgumentParser()
    ap.add_argument("--uqm", help="UQM-MegaMod-Content checkout (needed unless --only)")
    ap.add_argument("--out", required=True, help="add-on directory")
    ap.add_argument("--remix", help="unzipped UQM Remix Packs (optional)")
    ap.add_argument("--threedo", help="unzipped UQM 3DO music add-on (optional)")
    ap.add_argument("--wesnoth-data", default="/usr/share/games/wesnoth/1.16/data")
    ap.add_argument("--seed", type=int, default=1990)
    ap.add_argument("--only", choices=["badlands", "gas", "asteroids", "fried", "barriers", "terrain"],
                    help="rebuild just this terrain (barriers: all gas clouds and the barrier objects)")
    args = ap.parse_args()
    if not args.only and not args.uqm:
        ap.error("--uqm is required unless --only is given")

    if args.only == "fried":
        build_fried_plumes(args.out, save, rotated, DIAG, args.seed)
        return 0
    rng = np.random.default_rng(args.seed)
    mask = hex_mask(args.wesnoth_data)
    hex_mask_cache = mask
    tmasks = transition_masks(args.wesnoth_data)
    if args.only == "badlands":
        build_badlands(np.random.default_rng(args.seed + 4), args.out)
        return 0
    if args.only == "gas":
        build_gas(args.seed, args.out)
        return 0
    if args.only == "barriers":
        build_gas(args.seed, args.out)
        build_barrier_objects(np.random.default_rng(args.seed + 40), args.out, save, apply_mask, starfield, mask)
        return 0
    if args.only == "asteroids":
        build_asteroid_art(np.random.default_rng(args.seed + 20), args.out, save, TRANSITION_COMBOS, mask)
        return 0

    if args.only == "terrain":
        build_terrain(rng, mask, tmasks, args)
        return 0

    build_ships(args.uqm, args.out)
    build_samatra(args.uqm, args.out)
    build_hierarchy_starbase(args.out)   # original art
    build_alliance_starbase(args.out)    # original art
    build_projectiles(args.uqm, args.out)
    build_lasers(args.out)
    build_fried_plumes(args.out, save, rotated, DIAG, args.seed)   # original art
    build_attack_icons(args.out)
    nfire = build_effects(args.uqm, args.out)
    build_sounds(args.uqm, args.out)
    build_ditties(args.uqm, args.out, args.remix)
    build_music(args.uqm, args.out)
    if args.remix:
        build_remixes(args.remix, args.out)
    if args.threedo:
        build_remixes(args.threedo, args.out, table=THREEDO)

    build_terrain(rng, mask, tmasks, args)

    # Added by hand, not built here: Chenjesu and Mmrnmhrm themes by Titus
    # (supplied as MP3s, loudness-matched to the other music).
    manifest.extend(["music/sc/1. chenjesu-titus.ogg", "music/sc/1. mmrnmhrm-titus.ogg"])
    # ...and Star Control 1's Alliance and Hierarchy victory themes (MP3s;
    # played as sound effects).
    manifest.extend(["sounds/sc/alliance-victory.ogg", "sounds/sc/hierarchy-victory.ogg"])
    # ...an Androsynth theme by TheMisterCat (DUOLED), and the Melnorme theme
    # re-imagined by DJ Yan Yan Lipavsky (MP3s).
    manifest.extend(["music/sc/2. androsynth-duoled.ogg", "music/sc/3. melnorme-lipavsky.ogg"])
    # ...and Ramen Rider's cover of the Syreen theme (MP3).
    manifest.append("music/sc/3. syreen-ramen-rider.ogg")
    # ...and the Death March victory theme, the opening phrase of Chopin's
    # Funeral March (MP3, trimmed with a fade-out; played as a sound effect).
    manifest.append("sounds/sc/funeral-march.ogg")
    with open(os.path.join(args.out, "art-manifest.txt"), "w") as f:
        f.write("# Files derived from The Ur-Quan Masters content (CC BY-NC-SA 2.5).\n")
        f.write("# A published build must replace every one of these.\n")
        for rel in sorted(manifest):
            f.write(rel + "\n")
    print(f"ok: {len(manifest)} UQM-derived files, hellfire frames={nfire}")


if __name__ == "__main__":
    sys.exit(main())
