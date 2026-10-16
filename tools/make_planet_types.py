#!/usr/bin/env python3
"""Extra looks for the three planet types (life, mineral and dead worlds),
next to planet.png, planet5.png and planet6.png from make_art.py. One is
made from a make_art.py planet:

    dead world     planet6.png -> planet-dead2.png     (cratered)

and drawn fresh:

    planet-life2.png     continents of forest, savanna and desert in teal
                         seas, small polar caps
    planet-mineral2.png  dark-red world with glowing veins
    planet-life3.png     ocean world: scattered islands under swirling cloud
    planet-mineral3.png  dark red crust in plates, some rich in copper ore,
                         with craters
    planet-dead3.png     dusty brown-grey world with dark basins and a rayed crater

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


def down_rgb(arr):
    return np.dstack([down(arr[..., i]) for i in range(arr.shape[2])])


def craters(src, rng, count=34, basins=0):
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


def textured_sphere(rgb, glow=None, lift=None):
    """4x rgb on the sphere, lit, scaled down, on a hex canvas with an optional
    glow. `lift` (0..1) keeps bright parts like ice faintly visible at night."""
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    if lift is not None:
        s = s + (1 - s) * 0.22 * lift
    rgb = rgb * s[..., None]
    alpha = down(inside.astype(np.float32)) * 255
    sphere = Image.fromarray(np.dstack([down_rgb(rgb), alpha]).clip(0, 255).astype(np.uint8), "RGBA")
    canvas = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", (HEX, HEX), (0, 0, 0, 0))
        e = R + 3
        ImageDraw.Draw(g).ellipse([CX - e - 0.5, CY - e - 0.5, CX + e - 0.5, CY + e - 0.5], fill=glow + (110,))
        canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(sphere)
    return canvas


def ramp(t, pal):
    pal = np.array(pal, np.float32)
    idx = np.clip(t * (len(pal) - 1), 0, len(pal) - 1.001)
    lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    return pal[lo] * (1 - f) + pal[lo + 1] * f


def life_world3(rng):
    """Mostly ocean: small green islands, wisps of cloud in bands."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    land = noise(rng, n, base=5)
    ocean = ramp(noise(rng, n, base=3), [(10, 40, 110), (18, 62, 150), (28, 86, 175)])
    isle = ramp(np.clip((land - 0.52) / 0.48, 0, 1), [(70, 130, 60), (110, 150, 75), (150, 160, 110)])
    m = np.clip((land - 0.52) * 25, 0, 1)[..., None]
    rgb = ocean * (1 - m) + isle * m
    # clouds: noise stretched along latitude bands
    c = noise(rng, n, base=4)
    warp = np.sin(ny * 8 + 9 * (c - 0.5)) * 0.5 + 0.5
    cloud = np.clip((noise(rng, n, base=6) * 0.7 + warp * 0.3 - 0.55) * 3, 0, 0.8)[..., None]
    rgb = rgb * (1 - cloud) + np.array([235, 240, 248], np.float32) * cloud
    return textured_sphere(rgb, glow=(130, 190, 255))


def life_world2(rng):
    """Continents of forest, savanna and desert in teal seas, with small
    polar caps square to the axis."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    land = noise(rng, n, base=3)
    coast = 0.56
    sea = ramp(np.clip((coast - land) / 0.25, 0, 1), [(40, 150, 150), (22, 105, 130), (14, 60, 105)])
    biome = noise(rng, n, base=5)
    # drier towards the equator, greener towards the poles
    dry = np.clip(biome * 0.75 + (1 - np.abs(ny)) * 0.35 - 0.38, 0, 1)
    ground = ramp(dry, [(38, 82, 40), (72, 112, 50), (128, 132, 64), (176, 150, 88), (198, 172, 118)])
    m = np.clip((land - coast) * 30, 0, 1)[..., None]
    rgb = sea * (1 - m) + ground * m
    wob = noise(rng, n, base=7) - 0.5
    cap = np.clip((np.abs(ny) - 0.84 - 0.10 * wob) * 18, 0, 1)[..., None]
    rgb = rgb * (1 - cap) + np.array([238, 244, 252], np.float32) * cap
    return textured_sphere(rgb, glow=(120, 200, 215), lift=cap[..., 0])


def mineral_world3(rng):
    """Dark red crust broken into plates, a few of them rich with copper ore,
    pocked by craters."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    pts = rng.normal(size=(70, 3))
    pts /= np.linalg.norm(pts, axis=1, keepdims=True)
    normals = np.stack([nx, ny, nz], -1).reshape(-1, 3)
    ang = np.arccos(np.clip(normals @ pts.T, -1, 1))
    order = np.argsort(ang, axis=1)
    first = order[:, 0]
    a1 = np.take_along_axis(ang, order[:, :1], 1)[:, 0]
    a2 = np.take_along_axis(ang, order[:, 1:2], 1)[:, 0]
    tone = rng.random(len(pts))[first].reshape(n, n)
    ore = (rng.random(len(pts)) < 0.3)[first].reshape(n, n).astype(np.float32)
    grain = noise(rng, n, base=8, octaves=4)
    rgb = ramp(np.clip(0.65 * tone + 0.35 * grain, 0, 1),
               [(44, 12, 12), (70, 18, 16), (98, 28, 20), (124, 40, 26)])
    crack = np.clip(1 - (a2 - a1).reshape(n, n) / 0.045, 0, 1)
    rgb *= (1 - 0.75 * crack)[..., None]
    speck = np.clip((noise(rng, n, base=40, octaves=2) - 0.58) * 6, 0, 0.8) * ore
    rgb = rgb * (1 - speck[..., None]) + np.array([215, 120, 60], np.float32) * speck[..., None]
    return craters(textured_sphere(rgb, glow=(200, 50, 40)), rng, count=10)


def spend(rng, *bases):
    """Make the draws an earlier look made, so the looks after it stay the same."""
    for b in bases:
        if b is None:
            rng.random((HEX * SS, HEX * SS))
        else:
            noise(rng, HEX * SS, base=b)


def dead_world3(rng):
    """Dusty brown-grey: dark lava basins, a few craters, one bright rayed crater."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    rgb = ramp(noise(rng, n, base=5), [(82, 74, 64), (118, 108, 94), (150, 140, 124), (176, 166, 150)])
    basin = np.clip((noise(rng, n, base=3, octaves=4) - 0.5) * 5, 0, 0.75)[..., None]
    rgb = rgb * (1 - basin) + np.array([52, 48, 46], np.float32) * basin
    # rays from one young crater, upper right
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    px, py = (xx + 0.5) / SS, (yy + 0.5) / SS
    rx, ry = CX + 0.30 * R, CY - 0.22 * R
    ang = np.arctan2(py - ry, px - rx)
    dist = np.hypot(px - rx, py - ry)
    spokes = np.clip(np.cos(ang * 9 + 2.0 * noise(rng, n, base=3)) * 1.6 - 0.6, 0, 1)
    ray = spokes * np.clip(1 - dist / 14, 0, 1) * 0.55
    rgb = rgb * (1 - ray[..., None]) + np.array([225, 220, 210], np.float32) * ray[..., None]
    sphere = textured_sphere(rgb)
    return craters(sphere, rng, count=14)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    d = os.path.join(args.out, "images/terrain/sc")
    rng = np.random.default_rng(args.seed)
    life_world2(np.random.default_rng(args.seed + 1)).save(os.path.join(d, "planet-life2.png"))
    spend(rng, 6)                         # the first life world v2
    mineral_world(rng).save(os.path.join(d, "planet-mineral2.png"))
    craters(Image.open(os.path.join(d, "planet6.png")).convert("RGBA"), rng).save(
        os.path.join(d, "planet-dead2.png"))
    life_world3(rng).save(os.path.join(d, "planet-life3.png"))
    mineral_world3(np.random.default_rng(args.seed + 2)).save(os.path.join(d, "planet-mineral3.png"))
    spend(rng, 3, 6, None, 4)             # the first mineral world v3
    dead_world3(rng).save(os.path.join(d, "planet-dead3.png"))


if __name__ == "__main__":
    main()
