#!/usr/bin/env python3
"""Extra looks for the three planet types (life, mineral and dead worlds),
next to planet.png, planet5.png and planet6.png from make_art.py. One is
made from a make_art.py planet:

    dead world     planet6.png -> planet-dead2.png     (cratered)

and drawn fresh:

    planet-life1.png     planet.png redrawn: green land, blue seas, cloud, haze
    planet-dead1.png     planet6.png redrawn: grey regolith, plains, old craters

    planet-life2.png     continents of forest, savanna and desert in teal
                         seas, small polar caps
    planet-life3.png     ocean world: scattered islands under swirling cloud
    planet-dead3.png     dusty brown-grey world with dark basins and a rayed crater
    planet-life4.png     jungle: emerald forest, small lakes and rivers
    planet-life5.png     archipelago: turquoise seas, small sandy islands
    planet-life6.png     green continents, brown uplands, small deserts

and six mineral worlds, all on the same rusty, Mars-like surface:

    planet-mineral1.png  lava seas in the lowlands
    planet-mineral2.png  thin lava rivers
    planet-mineral3.png  plates split by wandering lava cracks
    planet-mineral4.png  one long rift canyon with lava on its floor, ore, craters
    planet-mineral5.png  many small lava pools
    planet-mineral6.png  volcanoes: glowing calderas and lava flows

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




def textured_sphere(rgb, glow=None, lift=None, atmo=None, lit=False):
    """4x rgb on the sphere, lit, scaled down, on a hex canvas with an optional
    glow. `lift` (0..1) keeps bright parts like ice faintly visible at night."""
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    if lift is not None:
        s = s + (1 - s) * 0.22 * lift
    if not lit:                  # `lit`: rgb is already shaded
        rgb = rgb * s[..., None]
    if atmo is not None:         # a thin haze on the sunlit limb
        edge = np.clip((np.sqrt(nx ** 2 + ny ** 2) - 0.8) / 0.2, 0, 1) ** 2
        lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + 0.3, 0, 1)
        h = (edge * lam * 0.75)[..., None]
        rgb = rgb * (1 - h) + np.array(atmo, np.float32) * h
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


def limb_fade(nx, ny, start=0.82):
    """1 inside, falling to 0 at the planet's edge."""
    return np.clip((1 - np.sqrt(nx ** 2 + ny ** 2)) / (1 - start), 0, 1)




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


def life_world1(rng):
    """planet.png's green-and-blue world, redrawn: seas and green land with
    crisp coasts, darker forest, wisps of cloud and a hazy blue rim."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    land = noise(rng, n, base=4, octaves=6)
    coast = np.quantile(land[inside], 0.5)      # half land, half sea
    sea = ramp(np.clip((coast - land) / 0.3, 0, 1), [(36, 96, 170), (24, 70, 150), (16, 46, 120)])
    ground = ramp(noise(rng, n, base=7), [(40, 96, 46), (62, 124, 56), (96, 146, 70), (128, 150, 84)])
    m = np.clip((land - coast) * 40, 0, 1)[..., None]
    rgb = sea * (1 - m) + ground * m
    cloud = np.clip((noise(rng, n, base=6, octaves=6) - 0.62) * 3.2, 0, 0.7)[..., None]
    rgb = rgb * (1 - cloud) + np.array([232, 238, 246], np.float32) * cloud
    return textured_sphere(rgb, glow=(120, 170, 255), atmo=(140, 190, 255))




def dead_world1(rng):
    """planet6.png's grey world, redrawn: fine dusty regolith, pale highlands
    and darker plains, a few soft old craters."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    high = noise(rng, n, base=3, octaves=6)
    rgb = ramp(high, [(104, 104, 108), (136, 134, 132), (166, 164, 160), (198, 196, 192)])
    grain = noise(rng, n, base=32, octaves=3) - 0.5
    rgb *= (1 + 0.12 * grain)[..., None]
    plain = np.clip((0.45 - noise(rng, n, base=3, octaves=4)) * 4, 0, 0.5)[..., None]
    rgb = rgb * (1 - plain) + np.array([78, 78, 82], np.float32) * plain
    return craters(textured_sphere(rgb), rng, count=6)


def life_world4(rng):
    """Jungle world: dense emerald forest with small dark lakes and winding
    rivers, thin cloud."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    rgb = ramp(noise(rng, n, base=6, octaves=6), [(20, 70, 34), (34, 100, 42), (58, 128, 50), (90, 150, 62)])
    lake = noise(rng, n, base=14, octaves=3)
    lakes = np.clip((lake - np.quantile(lake[inside], 0.93)) * 30, 0, 1)
    r = noise(rng, n, base=4, octaves=5)
    river = np.clip(1 - np.abs(r - 0.5) / 0.018, 0, 1) * np.clip((noise(rng, n, base=3) - 0.4) * 4, 0, 1)
    water = np.maximum(lakes, river * 0.9)[..., None]
    rgb = rgb * (1 - water) + np.array([22, 58, 110], np.float32) * water
    cloud = np.clip((noise(rng, n, base=8, octaves=5) - 0.7) * 3, 0, 0.5)[..., None]
    rgb = rgb * (1 - cloud) + np.array([230, 240, 235], np.float32) * cloud
    return textured_sphere(rgb, glow=(120, 210, 140), atmo=(150, 220, 170))


def life_world5(rng):
    """Archipelago: shallow turquoise seas scattered with small sandy,
    green-topped islands."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    land = 0.8 * noise(rng, n, base=14, octaves=3) + 0.2 * noise(rng, n, base=3)
    coast = np.quantile(land[inside], 0.84)
    depth = np.clip((coast - land) / 0.25, 0, 1)
    rgb = ramp(depth, [(70, 200, 200), (34, 150, 180), (20, 92, 150), (14, 60, 120)])
    isle = np.clip((land - coast) * 40, 0, 1)
    green = np.clip((land - coast - 0.03) * 30, 0, 1)
    ground = np.array([214, 196, 140], np.float32) * (1 - green[..., None]) + np.array([70, 140, 60], np.float32) * green[..., None]
    rgb = rgb * (1 - isle[..., None]) + ground * isle[..., None]
    cloud = np.clip((noise(rng, n, base=5, octaves=6) - 0.72) * 3, 0, 0.55)[..., None]
    rgb = rgb * (1 - cloud) + np.array([240, 244, 250], np.float32) * cloud
    return textured_sphere(rgb, glow=(110, 210, 230), atmo=(150, 230, 240))


def life_world6(rng):
    """Green continents with brown uplands and small yellow deserts, in
    blue seas."""
    nx, ny, nz, inside = sphere_coords()
    n = HEX * SS
    land = noise(rng, n, base=4, octaves=6)
    coast = np.quantile(land[inside], 0.3)
    sea = ramp(np.clip((coast - land) / 0.3, 0, 1), [(40, 110, 175), (26, 78, 155), (18, 52, 125)])
    rgb = ramp(noise(rng, n, base=7), [(46, 110, 44), (70, 136, 54), (96, 150, 64)])
    up = np.clip((land - coast - 0.12) * 8, 0, 0.8)[..., None]            # brown uplands inland
    rgb = rgb * (1 - up) + np.array([118, 94, 60], np.float32) * up
    dry = noise(rng, n, base=9, octaves=4)
    desert = np.clip((dry - np.quantile(dry[inside], 0.8)) * 20, 0, 1)[..., None]
    rgb = rgb * (1 - desert) + np.array([212, 190, 120], np.float32) * desert
    m = np.clip((land - coast) * 40, 0, 1)[..., None]
    rgb = sea * (1 - m) + rgb * m
    cloud = np.clip((noise(rng, n, base=6, octaves=6) - 0.7) * 3, 0, 0.55)[..., None]
    rgb = rgb * (1 - cloud) + np.array([240, 244, 250], np.float32) * cloud
    return textured_sphere(rgb, glow=(120, 180, 255), atmo=(150, 200, 255))








# The mineral worlds all share a Mars-like rusty surface (mars()), each with
# its own kind of lava on it.
MARS_GLOW = (210, 90, 50)

def mars(rng):
    n = HEX * SS
    """Mineral v4's rusty base: oxide plains, dark iron highlands, pale dust."""
    rgb = ramp(noise(rng, n, base=4, octaves=6), [(70, 26, 16), (118, 48, 24), (156, 70, 32), (182, 98, 50)])
    high = np.clip((noise(rng, n, base=3, octaves=5) - 0.55) * 4, 0, 0.6)[..., None]
    rgb = rgb * (1 - high) + np.array([52, 34, 30], np.float32) * high
    dust = np.clip((noise(rng, n, base=5, octaves=4) - 0.62) * 3, 0, 0.35)[..., None]
    rgb = rgb * (1 - dust) + np.array([200, 130, 80], np.float32) * dust
    return rgb

def lava_blend(rgb, heat, s, nx, ny, pal=None, k=1.8):
    """Lava over rgb where heat > 0, faded off the limb, glowing at night too."""
    heat = heat * limb_fade(nx, ny)
    pal = pal or [(120, 24, 8), (195, 56, 12), (236, 100, 22), (252, 160, 46)]
    lava = ramp(heat, pal)
    h = np.clip(heat * k, 0, 1)[..., None]
    return rgb * (1 - h) + lava * (0.7 + 0.3 * s)[..., None] * h

def mineral_world1(rng):
    """Mars with a few lava seas in its lowlands (v1)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    rgb = mars(rng) * s[..., None]
    melt = 0.6 * noise(rng, n, base=6, octaves=5) + 0.4 * noise(rng, n, base=3)
    shore = np.quantile(melt[inside], 0.78)
    heat = np.clip((melt - shore) / 0.18, 0, 1)
    rgb = lava_blend(rgb, np.clip(heat * 0.85 + (melt > shore) * 0.15, 0, 1), s, nx, ny, k=6)
    return craters(textured_sphere(rgb, glow=MARS_GLOW, lit=True), rng, count=6)

def mineral_world2(rng):
    """Mars cut by thin orange-red lava rivers (v2)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    rgb = mars(rng) * s[..., None]
    river = np.zeros((n, n), np.float32)
    for b, w in ((4, 0.04), (7, 0.028)):
        r = noise(rng, n, base=b, octaves=4)
        river = np.maximum(river, np.clip(1 - np.abs(r - 0.5) / w, 0, 1))
    river *= np.clip((noise(rng, n, base=3) - 0.2) * 3, 0, 1)
    return textured_sphere(lava_blend(rgb, river, s, nx, ny, k=2.2), glow=MARS_GLOW, lit=True)

def mineral_world3(rng):
    """Mars in huge plates split by thin glowing cracks (v3)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    w = 0.26
    wx, wy, wz = (noise(rng, n, base=4, octaves=6) - 0.5 for _ in range(3))
    v = np.stack([nx + w * wx, ny + w * wy, nz + w * wz], -1).reshape(-1, 3)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    pts = rng.normal(size=(30, 3)); pts /= np.linalg.norm(pts, axis=1, keepdims=True)
    ang = np.arccos(np.clip(v @ pts.T, -1, 1)); order = np.argsort(ang, axis=1)
    gap = (np.take_along_axis(ang, order[:, 1:2], 1) - np.take_along_axis(ang, order[:, :1], 1))[:, 0]
    k = len(pts); opened = rng.random((k, k)) < 0.75; opened = opened | opened.T
    op = opened[order[:, 0], order[:, 1]]
    crack = (op * np.clip(1 - gap / 0.025, 0, 1)).reshape(n, n)
    warm = (op * np.clip(1 - gap / 0.07, 0, 1)).reshape(n, n)
    tone = (rng.random(k)[order[:, 0]].reshape(n, n) - 0.5) * 0.12 + 0.95
    rgb = mars(rng) * tone[..., None]
    rgb = rgb * (1 - 0.4 * warm[..., None]) + np.array([150, 44, 18], np.float32) * 0.4 * warm[..., None]
    rgb = rgb * s[..., None]
    return textured_sphere(lava_blend(rgb, crack, s, nx, ny, pal=[(230, 80, 18), (255, 135, 36)], k=3),
                           glow=MARS_GLOW, lit=True)

def mineral_world5(rng):
    """Mars pocked with small lava pools (v5)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    rgb = mars(rng) * s[..., None]
    pools = noise(rng, n, base=20, octaves=2)
    edge = np.quantile(pools[inside], 0.88)
    heat = np.clip((pools - edge) / 0.08, 0, 1)
    return craters(textured_sphere(lava_blend(rgb, heat, s, nx, ny, k=3), glow=MARS_GLOW, lit=True), rng, count=5)

def mineral_world6(rng):
    """Mars with a few big volcanoes, glowing calderas and lava flows (v6)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    rgb = mars(rng)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    heat = np.zeros((n, n), np.float32); cone = np.zeros((n, n), np.float32)
    wob = noise(rng, n, base=12, octaves=3)
    for _ in range(4):
        while True:
            u, v = rng.uniform(-0.75, 0.75, 2)
            if u * u + v * v < 0.55: break
        cx, cy = (CX + u * R) * SS, (CY + v * R) * SS
        d = np.hypot(xx - cx, yy - cy)
        cone = np.maximum(cone, np.clip(1 - d / 26, 0, 1))
        heat = np.maximum(heat, np.clip(1 - d / rng.uniform(6, 9), 0, 1))
        for _ in range(int(rng.integers(3, 6))):
            a = rng.uniform(0, 2 * np.pi); ln = rng.uniform(16, 30)
            dx, dy = xx - cx, yy - cy
            along = dx * np.cos(a) + dy * np.sin(a)
            across = -dx * np.sin(a) + dy * np.cos(a) + 6 * (wob - 0.5)
            heat = np.maximum(heat, 0.75 * np.clip(1 - np.abs(across) / 2.2, 0, 1) * np.clip(1 - along / ln, 0, 1) * (along > 0))
    rgb = rgb * 1.3
    rgb = rgb * (1 - 0.2 * cone[..., None]) + np.array([150, 84, 56], np.float32) * 0.2 * cone[..., None]
    rgb = rgb * (0.25 + 0.75 * s)[..., None]
    return textured_sphere(lava_blend(rgb, np.clip(heat * 1.2, 0, 1), s, nx, ny,
                                      pal=[(170, 40, 10), (230, 80, 18), (252, 130, 34), (255, 190, 70)]),
                           glow=(230, 110, 60), lit=True)

def mineral_world4(rng):
    """Mars split by one great glowing rift canyon, with ore flecks and craters (v4)."""
    n = HEX * SS
    nx, ny, nz, inside = sphere_coords()
    s = shade(nx, ny, nz)
    rgb = mars(rng)
    wob = noise(rng, n, base=6, octaves=4) - 0.5
    a = rng.uniform(-0.5, 0.5)
    across = (-nx * np.sin(a) + ny * np.cos(a)) - 0.12 + 0.18 * wob
    along = nx * np.cos(a) + ny * np.sin(a)
    span = np.clip(1 - np.abs(along + 0.05) / 0.85, 0, 1) ** 0.3
    canyon = np.clip(1 - np.abs(across) / 0.13, 0, 1) ** 0.7 * span
    rgb = rgb * (1 - 0.8 * canyon[..., None]) + np.array([30, 12, 10], np.float32) * 0.8 * canyon[..., None]
    floor = np.clip(1 - np.abs(across) / 0.04, 0, 1) * span
    fl = (rng.random((n, n)) < 0.003).astype(np.float32)
    fl = np.asarray(Image.fromarray((fl * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), np.float32) / 255
    fl *= np.clip((noise(rng, n, base=5) - 0.4) * 3, 0, 1)
    rgb = rgb * (1 - fl[..., None]) + np.array([235, 160, 80], np.float32) * fl[..., None]
    rgb = rgb * s[..., None]
    return craters(textured_sphere(lava_blend(rgb, floor, s, nx, ny, k=1.6), glow=MARS_GLOW, lit=True), rng, count=7)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    d = os.path.join(args.out, "images/terrain/sc")
    rng = np.random.default_rng(args.seed)
    life_world2(np.random.default_rng(args.seed + 1)).save(os.path.join(d, "planet-life2.png"))
    spend(rng, 6)                         # the first life world v2
    spend(rng, 3)                         # the old mineral world v2
    for b in (4, 7):
        noise(rng, HEX * SS, base=b, octaves=4)
    spend(rng, 3)
    craters(Image.open(os.path.join(d, "planet6.png")).convert("RGBA"), rng).save(
        os.path.join(d, "planet-dead2.png"))
    life_world3(rng).save(os.path.join(d, "planet-life3.png"))
    spend(rng, 3, 6, None, 4)             # the first mineral world v3
    dead_world3(rng).save(os.path.join(d, "planet-dead3.png"))
    life_world1(np.random.default_rng(args.seed + 3)).save(os.path.join(d, "planet-life1.png"))
    dead_world1(np.random.default_rng(args.seed + 5)).save(os.path.join(d, "planet-dead1.png"))
    for k, make in enumerate((life_world4, life_world5, life_world6)):
        kind, v = make.__name__.split("_world")
        make(np.random.default_rng(args.seed + 10 + k)).save(os.path.join(d, f"planet-{kind}{v}.png"))
    for k, make in enumerate((mineral_world1, mineral_world2, mineral_world3,
                              mineral_world4, mineral_world5, mineral_world6)):
        make(np.random.default_rng(3030 + k)).save(os.path.join(d, f"planet-mineral{k + 1}.png"))


if __name__ == "__main__":
    main()
