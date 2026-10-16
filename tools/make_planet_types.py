#!/usr/bin/env python3
"""Second looks for the three planet types, made from the planets that
make_art.py draws:

    life world     planet.png  -> planet-life2.png     (small polar caps)
    mineral world  planet5.png -> planet-mineral2.png  (new dark-red world
                                                        with glowing veins)
    dead world     planet6.png -> planet-dead2.png     (cratered)

    tools/make_planet_types.py [--out ADDON_DIR]

The edits are worked out at 4x and scaled down, so caps and craters are
smooth at the 72px hex size. Needs numpy and Pillow.
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HEX = 72
SS = 4                      # supersampling
CX = CY = 36.0              # sphere centre and radius in hex pixels
R = 19.0                    # (make_art.py: 38px sphere, centred)
LIGHT = np.array([-0.55, -0.55, 0.63]) / np.linalg.norm([-0.55, -0.55, 0.63])


def sphere_coords():
    """Unit-sphere normal for every 4x subpixel; inside mask."""
    n = HEX * SS
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    nx = ((xx + 0.5) / SS - CX) / R
    ny = ((yy + 0.5) / SS - CY) / R
    d2 = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    return nx, ny, nz, d2 <= 1


def down(field):
    """Average 4x field down to hex size."""
    n = field.shape[0] // SS
    return field.reshape(n, SS, n, SS).mean(axis=(1, 3))


def noise(rng, n, base=4, octaves=5):
    total, amp, norm = np.zeros((n, n), np.float32), 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        g = rng.random((cells, cells)).astype(np.float32)
        layer = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        total += amp * np.asarray(layer, np.float32) / 255
        norm += amp
        amp *= 0.5
    total /= norm
    total -= total.min()
    return total / max(total.max(), 1e-6)


def shade(nx, ny, nz):
    lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    return 0.12 + 0.88 * lam


def polar_caps(src, rng):
    nx, ny, nz, inside = sphere_coords()
    wob = noise(rng, HEX * SS, base=6) - 0.5
    # latitude along a slightly tilted axis; caps reach about 30 degrees
    tilt = np.radians(12)
    lat = ny * np.cos(tilt) + nx * np.sin(tilt)
    north = np.clip((-lat - 0.80 - 0.14 * wob) * 16, 0, 1)
    south = np.clip((lat - 0.80 - 0.14 * wob) * 16, 0, 1)
    cap = np.where(inside, np.maximum(north, south), 0)
    s = shade(nx, ny, nz)
    ice = np.array([236, 244, 255], np.float32)
    cap_rgb = ice[None, None, :] * (0.22 + 0.78 * s)[..., None]   # ice shows a little on the night side
    a = down(cap)[..., None]
    rgb = down_rgb(cap_rgb * cap[..., None]) / np.maximum(a, 1e-6)
    img = np.asarray(src, np.float32).copy()
    img[..., :3] = img[..., :3] * (1 - a) + rgb * a
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")


def down_rgb(arr):
    return np.dstack([down(arr[..., i]) for i in range(arr.shape[2])])


def craters(src, rng, count=34):
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    px, py = (xx + 0.5) / SS, (yy + 0.5) / SS
    mult = np.ones((n, n), np.float32)
    lx, ly = -0.7071, -0.7071
    for i in range(count):
        # spread over the visible half, a few big, many small
        while True:
            u, v = rng.uniform(-0.95, 0.95, 2)
            if u * u + v * v < 0.9:
                break
        rad = float(rng.choice([1.2, 1.5, 1.8, 2.2, 2.8, 3.6, 4.6],
                               p=[0.2, 0.2, 0.18, 0.16, 0.12, 0.09, 0.05]))
        cz = np.sqrt(1 - u * u - v * v)
        ccx, ccy = CX + u * R, CY + v * R
        # foreshorten along the radial direction towards the limb
        rr = np.hypot(u, v)
        ru, rv = (u / rr, v / rr) if rr > 1e-3 else (1.0, 0.0)
        dx, dy = px - ccx, py - ccy
        radial = (dx * ru + dy * rv) / max(cz, 0.25)
        tang = -dx * rv + dy * ru
        d = np.hypot(radial, tang) / rad
        ux = np.where(d > 1e-6, dx / np.maximum(np.hypot(dx, dy), 1e-6), 0)
        uy = np.where(d > 1e-6, dy / np.maximum(np.hypot(dx, dy), 1e-6), 0)
        toward = ux * lx + uy * ly           # >0 on the side facing the light
        bowl = d < 1
        f = np.ones_like(mult)
        # inner wall facing away from the light is lit, the near one shadowed
        f = np.where(bowl, 0.86 - 0.42 * toward * d ** 1.4, f)
        rim = (d >= 1) & (d < 1.35)
        w = np.clip(1 - (d - 1) / 0.35, 0, 1)
        f = np.where(rim, 1 + w * (0.30 * np.clip(toward, 0, 1) - 0.12 * np.clip(-toward, 0, 1)), f)
        mult *= f
    mult = np.where(inside, mult, 1)
    m = down(mult)[..., None]
    img = np.asarray(src, np.float32).copy()
    img[..., :3] *= m
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")


def mineral_world(rng):
    """Dark red rock seamed with glowing ore veins, in planet5's red glow."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    base = noise(rng, n, base=3)
    pal = np.array([(26, 8, 8), (52, 14, 12), (86, 22, 16), (120, 34, 22), (96, 26, 20)], np.float32)
    idx = np.clip(base * (len(pal) - 1), 0, len(pal) - 1.001)
    lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    rgb = pal[lo] * (1 - f) + pal[lo + 1] * f
    # veins: thin ridges of two noise fields
    vein = np.zeros((n, n), np.float32)
    for b, wdt in ((4, 0.035), (7, 0.025)):
        r = noise(rng, n, base=b, octaves=4)
        vein = np.maximum(vein, np.clip(1 - np.abs(r - 0.5) / wdt, 0, 1))
    vein *= np.clip((noise(rng, n, base=3) - 0.35) * 3, 0, 1)   # broken up
    glow = np.array([255, 96, 40], np.float32)
    s = shade(nx, ny, nz)
    rgb = rgb * s[..., None]
    # ore glows on its own, a little dimmer on the night side
    rgb = rgb * (1 - vein[..., None] * 0.85) + glow * (vein * (0.55 + 0.45 * s))[..., None]
    rgb = down_rgb(rgb)
    d = np.sqrt(down(nx ** 2 + ny ** 2))
    alpha = down(inside.astype(np.float32)) * 255
    sphere = Image.fromarray(np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8), "RGBA")
    canvas = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
    g = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
    dia = 2 * R
    ImageDraw.Draw(g).ellipse([36 - dia / 2 - 3.5, 36 - dia / 2 - 3.5, 36 + dia / 2 + 2.5, 36 + dia / 2 + 2.5],
                              fill=(220, 60, 40, 110))
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(sphere)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    d = os.path.join(args.out, "images/terrain/sc")
    rng = np.random.default_rng(args.seed)
    polar_caps(Image.open(os.path.join(d, "planet.png")).convert("RGBA"), rng).save(
        os.path.join(d, "planet-life2.png"))
    mineral_world(rng).save(os.path.join(d, "planet-mineral2.png"))
    craters(Image.open(os.path.join(d, "planet6.png")).convert("RGBA"), rng).save(
        os.path.join(d, "planet-dead2.png"))


if __name__ == "__main__":
    main()
