"""Impassable barriers other than asteroid walls: original art.

Two kinds:

* Blobs, painted hex by hex in any shape: dark nebula, radiation zone,
  plasma storm and gravity eddy. They are drawn like the nebulae (see
  build_gas_nebula in make_art.py): each is one big cloud that wraps round
  every few hexes, each hex shows its own piece of it and spills wisps onto
  its neighbours, so a blob reads as one cloud with a soft edge. This file
  only paints the clouds; make_art.py cuts them into hexes.
* Single objects, drawn as overlays: black hole (four of them, picked per
  hex), pulsar, and three that span four hexes: gas giant, supermassive
  black hole and globular cluster.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HEX = 72
S = 4                                   # supersampling for the objects


# ---------------------------------------------------------------- blobs


def _ridged(n):
    return 1 - np.abs(2 * n - 1)


def _mix(a, b, t):
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    return a * (1 - t[..., None]) + b * t[..., None]


def _rgba(rgb, alpha):
    return Image.fromarray(np.dstack([rgb, np.clip(alpha, 0, 1) * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def _hex_centres(w, h):
    """Centres of the hexes of one gas period, plus copies one period away
    on every side, so the nearest centre is right across the wrap."""
    pts = []
    for col in range(w // 54):
        for row in range(h // 72):
            x, y = 54 * col + 36, 72 * row + 36 + (36 if col % 2 else 0)
            for dx in (-w, 0, w):
                for dy in (-h, 0, h):
                    pts.append((x + dx, y + dy, (col + row) % 2))
    return np.array(pts, np.float32)


def _lightning(rng, w, h, n, colour):
    """Forked lightning drawn on a w x h canvas that wraps round."""
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, 2 * math.pi)
        path = [(x, y)]
        for _ in range(int(rng.integers(4, 9))):
            a += rng.uniform(-0.9, 0.9)
            x += 9 * math.cos(a); y += 9 * math.sin(a)
            path.append((x, y))
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.line([(px + ox, py + oy) for px, py in path], fill=colour + (255,), width=2)
    return img


def gas_painters(rng, w, h, noise):
    """For each blob, a painter(sl, col, row) that returns hex (col, row) of
    its cloud as a 72x72 RGBA layer; sl indexes the hex in a w x h field.
    `noise(rng, w, h, octaves, cell)` is make_art's wrapping fractal noise."""
    painters = {}

    # Dark nebula: dust so thick it blots out the stars, in dark purple
    # folds, darker than the plasma storm.
    n1, n2, f = noise(rng, w, h, 5, 40), noise(rng, w, h, 4, 70), noise(rng, w, h, 5, 22)

    def dark(sl, col, row):
        a, b, fold = n1[sl], n2[sl], _ridged(f[sl])
        rgb = _mix((6, 3, 10), (52, 24, 70), np.clip(a * 0.75 + fold ** 2 * 0.35, 0, 1))
        rgb = _mix(rgb, (115, 70, 150), np.clip((a - 0.5) * 2.5, 0, 1) * fold ** 2 * 0.6)   # lit billows
        return _rgba(rgb, np.clip(0.9 + 0.1 * (b - 0.5) + 0.06 * fold, 0, 0.97))
    painters["darknebula"] = dark

    # Radiation zone: sickly green glow with white-hot filaments.
    r1, r2, rf = noise(rng, w, h, 5, 36), noise(rng, w, h, 4, 60), noise(rng, w, h, 5, 24)
    specks = np.zeros((h, w), np.float32)
    for _ in range(w * h // 1400):
        specks[int(rng.integers(h)), int(rng.integers(w))] = 1

    def radiation(sl, col, row):
        a, b, fil = r1[sl], r2[sl], _ridged(rf[sl])
        rgb = _mix((45, 75, 12), (170, 220, 40), np.clip(a * 0.8 + fil ** 3 * 0.5, 0, 1))
        rgb = _mix(rgb, (250, 255, 190), np.clip(fil ** 12 * 2 + specks[sl], 0, 1))
        return _rgba(rgb, np.clip(0.55 + 0.3 * (b - 0.3) + 0.35 * fil ** 6 + specks[sl], 0, 0.95))
    painters["radiation"] = radiation

    # Plasma storm: purple-black cloud full of lightning.
    p1, p2 = noise(rng, w, h, 5, 40), noise(rng, w, h, 4, 60)
    bolts = _lightning(rng, w, h, w * h // 3600, (255, 205, 255))
    glow = np.asarray(bolts.filter(ImageFilter.GaussianBlur(4)), np.float32)[..., 3] / 255
    bolt = np.asarray(bolts, np.float32)[..., 3] / 255

    def storm(sl, col, row):
        a, b = p1[sl], p2[sl]
        rgb = _mix((32, 6, 42), (125, 35, 125), a)
        g = np.clip(glow[sl] * 3, 0, 1)
        rgb = _mix(rgb, (230, 90, 255), g * 0.8)
        rgb = _mix(rgb, (255, 225, 255), bolt[sl])
        return _rgba(rgb, np.clip(0.75 + 0.2 * (b - 0.5) + g * 0.3, 0, 0.97))
    painters["plasmastorm"] = storm

    # Gravity eddy: a whirl in every hex, neighbours turning opposite ways,
    # pulling the light of the stars into violet arcs round a dark core.
    pts = _hex_centres(w, h)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    best = np.full((h, w), 1e9, np.float32); cx = np.zeros_like(best); cy = np.zeros_like(best)
    spin = np.zeros_like(best)
    for px, py, s in pts:
        d2 = (xx - px) ** 2 + (yy - py) ** 2
        near = d2 < best
        best = np.where(near, d2, best); cx = np.where(near, px, cx); cy = np.where(near, py, cy)
        spin = np.where(near, 1.0 if s else -1.0, spin)
    r = np.sqrt(best); th = np.arctan2(yy - cy, xx - cx)
    en = noise(rng, w, h, 4, 50)
    arms = (0.5 + 0.5 * np.sin(r / 4.5 - spin * th * 3 + en * 4)) ** 4 * np.exp(-r / 34)
    core = np.clip(1 - r / 11, 0, 1)
    # streaks: stars smeared into short arcs about the nearest whirl
    streak = Image.new("L", (w, h)); sd = ImageDraw.Draw(streak)
    for _ in range(w * h // 260):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        i = int(np.argmin((pts[:, 0] - x) ** 2 + (pts[:, 1] - y) ** 2))
        px, py, s = pts[i]
        rad = math.hypot(x - px, y - py); a0 = math.degrees(math.atan2(y - py, x - px))
        if rad < 6:
            continue
        sweep = rng.uniform(15, 45)
        sd.arc([px - rad, py - rad, px + rad, py + rad], a0, a0 + sweep, fill=int(rng.uniform(90, 230)), width=1)
    streaks = np.asarray(streak, np.float32) / 255

    def eddy(sl, col, row):
        a, k, c, st = arms[sl], core[sl], en[sl], streaks[sl]
        rgb = _mix((22, 12, 46), (170, 120, 255), np.clip(a * 1.1, 0, 1))
        rgb = _mix(rgb, (225, 215, 255), st)
        rgb = _mix(rgb, (3, 1, 10), k)
        return _rgba(rgb, np.clip(0.62 + 0.15 * (c - 0.5) + a * 0.4 + st * 0.4 + k, 0, 0.97))
    painters["eddy"] = eddy
    return painters


# ---------------------------------------------------------------- objects


def _noise(rng, size, octaves=4, base=4):
    t = np.zeros((size, size), np.float32); amp = 1.0; n = 0.0
    for o in range(octaves):
        c = base * 2 ** o
        g = Image.fromarray((rng.random((c, c)) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        t += amp * np.asarray(g, np.float32) / 255; n += amp; amp *= 0.5
    t /= n; t -= t.min()
    return t / max(t.max(), 1e-6)


def _grid(size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    return xx - c, yy - c


def sphere(rng, d, palette, kind, light=(-0.55, -0.55, 0.63)):
    """A lit sphere of diameter d on a transparent (d + 8) square."""
    s = d + 8
    x, y = _grid(s); r = d / 2
    nx, ny = x / r, y / r; d2 = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    L = np.array(light); L /= np.linalg.norm(L)
    shade = 0.1 + 0.9 * np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    tex = _noise(rng, s, 5, 3)
    t = np.sin((ny + 0.12 * (tex - 0.5)) * 11) * 0.5 + 0.5 if kind == "gas" else tex
    cols = np.array(palette, np.float32)
    idx = np.clip(t * (len(cols) - 1), 0, len(cols) - 1.001); lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    rgb = (cols[lo] * (1 - f) + cols[lo + 1] * f) * shade[..., None]
    return _rgba(rgb, np.clip((1 - np.sqrt(d2)) * r, 0, 1))



# Disc colours for the black holes: (red, green, blue) as base + span * heat ** power,
# heat being 1 at the inner edge of the disc and 0 at the outer.
BLACK_HOLES = [
    dict(),                                                                        # orange, the first one
    dict(tilt=0.5, angle=-24, rgb=((150, 70), (190, 60, 1), (255, 0, 1)), glow=(120, 170, 255)),    # blue-white
    dict(tilt=0.17, angle=18, rgb=((200, 55), (40, 120, 1.5), (30, 60, 2)), glow=(255, 70, 40), jets=True),  # red, edge-on
    dict(tilt=0.72, angle=40, rgb=((170, 85), (60, 150, 1.5), (230, 25, 1)), glow=(190, 90, 255), arms=2),  # violet, face-on
]


def black_hole(rng, tilt=0.32, angle=0, rgb=((255, 0), (120, 120, 1), (40, 180, 2)),
               glow=(255, 140, 60), jets=False, arms=3):
    """Dead-black core in a lensed, glowing accretion disc. The disc is seen
    at `tilt` (1 face-on, 0 edge-on) and turned `angle` degrees; `jets`
    adds two faint beams along the axis."""
    W = HEX * S
    x, y = _grid(W); x, y = x / S, y / S
    rd = np.sqrt(x ** 2 + (y / tilt) ** 2)
    ang = np.arctan2(y / tilt, x)
    tex = _noise(rng, W, 4, 5)
    swirl = 0.55 + 0.45 * np.sin(ang * arms + rd * 0.55 + tex * 4)
    disc = np.clip((rd - 12) / 3, 0, 1) * np.clip((31 - rd) / 9, 0, 1) * swirl
    d = np.sqrt(x ** 2 + y ** 2)
    ring = np.clip(1 - np.abs(d - 13.5) / 2.5, 0, 1) * (0.6 + 0.4 * np.clip(-y / 13, 0, 1))
    hot = np.clip(1 - rd / 30, 0, 1)
    doppler = np.clip(1 + x / 40, 0.6, 1.4)
    if rgb == ((255, 0), (120, 120, 1), (40, 180, 2)):     # the first black hole, kept exactly as drawn
        col = np.dstack([255 * np.ones_like(d), 120 + 120 * hot, 40 + 180 * hot ** 2])
    else:
        col = np.dstack([c[0] + (c[1] if len(c) > 1 else 0) * hot ** (c[2] if len(c) > 2 else 1) for c in rgb])
    img = _rgba(col * doppler[..., None], np.clip(disc + ring, 0, 1) * doppler)
    if jets:
        beam = np.clip(1 - np.abs(x) / (0.8 + np.abs(y) * 0.06), 0, 1) * np.clip(1 - np.abs(y) / 34, 0, 1) * (np.abs(y) > 9)
        jet = _rgba(np.dstack([np.full_like(d, 200), np.full_like(d, 225), np.full_like(d, 255)]), beam * 0.8)
        jet.alpha_composite(img); img = jet
    core = np.clip((11 - d) * 1.5, 0, 1)
    front = (y > 0) & (rd > 12)                 # the near half of the disc passes in front
    img.alpha_composite(_rgba(np.zeros((W, W, 3)), core * np.where(front, 1 - np.clip(disc * 1.4, 0, 1), 1)))
    halo = Image.new("RGBA", (W, W), tuple(glow) + (0,))
    gh = 12 + 14 * (tilt - 0.32) if tilt > 0.32 else 12
    ImageDraw.Draw(halo).ellipse([W / 2 - 26 * S, W / 2 - gh * S, W / 2 + 26 * S, W / 2 + gh * S], fill=tuple(glow) + (70,))
    halo = halo.filter(ImageFilter.GaussianBlur(5 * S))
    halo.alpha_composite(img)
    if angle:
        halo = halo.rotate(angle, Image.BICUBIC)
    return halo.resize((HEX, HEX), Image.LANCZOS)


def pulsar(rng):
    """A tiny white-blue neutron star sweeping two beams, in a faint wind nebula."""
    W = HEX * S
    x, y = _grid(W); x, y = x / S, y / S
    d = np.sqrt(x ** 2 + y ** 2)
    th = math.radians(rng.uniform(50, 75))
    along = x * math.cos(th) + y * math.sin(th); across = -x * math.sin(th) + y * math.cos(th)
    beam = np.clip(1 - np.abs(across) / (1.4 + np.abs(along) * 0.1), 0, 1) * np.clip(1 - np.abs(along) / 40, 0, 1)
    core = np.clip((7 - d) * 0.8, 0, 1)
    halo = np.clip(1 - d / 19, 0, 1) ** 2
    neb = np.clip(1 - d / 32, 0, 1) ** 1.5 * (0.3 + 0.4 * _noise(rng, W, 3, 4)) * 0.6
    a = np.clip(np.maximum.reduce([core, halo * 0.9, beam, neb]), 0, 1)
    w = np.clip(core + beam * 0.6, 0, 1)
    rgb = np.dstack([110 + 145 * w, 160 + 95 * w, np.full_like(d, 255)])
    return _rgba(rgb, a).resize((HEX, HEX), Image.LANCZOS)


GAS_GIANTS = [
    [(150, 100, 60), (210, 170, 110), (240, 220, 180), (190, 130, 80), (230, 200, 150)],   # tan
    [(40, 70, 150), (70, 120, 200), (150, 190, 235), (60, 100, 180), (120, 170, 225)],     # blue
    [(120, 140, 110), (170, 190, 150), (220, 225, 200), (140, 160, 120), (200, 210, 180)],  # sage
    [(110, 25, 20), (175, 55, 35), (235, 150, 115), (145, 40, 30), (210, 95, 65)],         # red
]
GIANT_D = 134          # fits the diamond of four hexes it stands on


def banded_sphere(rng, d, palette, light=(-0.55, -0.55, 0.63)):
    """A gas giant's globe: bands of uneven width and contrast, some broad
    and soft, some thin and sharp, with wavy, turbulent edges, a few
    eddies along them and now and then a big oval storm. Every call draws
    a different pattern."""
    s = d + 8
    x, y = _grid(s); r = d / 2
    nx, ny = x / r, y / r; d2 = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    L = np.array(light); L /= np.linalg.norm(L)
    shade = 0.1 + 0.9 * np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    # latitude, bent by turbulence and by waves running along the bands
    tex = _noise(rng, s, 5, 3)
    fine = _noise(rng, s, 4, 9)
    waves = sum(rng.uniform(0.005, 0.02) * np.sin(nx * rng.uniform(4, 14) + rng.uniform(0, 6.3)
                                                    + ny * rng.uniform(-3, 3)) for _ in range(3))
    lat = ny + 0.07 * (tex - 0.5) + 0.025 * (fine - 0.5) + waves
    # the band profile: a random walk of band edges, each band its own colour
    edges = np.sort(rng.uniform(-1.1, 1.1, int(rng.integers(7, 13))))
    edges = np.concatenate([[-1.5], edges, [1.5]])
    values = rng.uniform(0, 1, len(edges) - 1)
    soft = rng.uniform(0.01, 0.06, len(edges))           # how sharp each edge is
    t = np.full_like(lat, values[0])
    for i in range(1, len(values)):
        step = np.clip((lat - edges[i]) / soft[i] * 0.5 + 0.5, 0, 1)
        t = t * (1 - step) + values[i] * step
    # thin streaks inside the bands
    streaks = np.sin(lat * rng.uniform(30, 60) + 6 * tex) * 0.5 + 0.5
    patchy = np.clip(fine * 2 - 0.5, 0, 1)          # streaks come and go
    t = np.clip(t + (streaks - 0.5) * patchy * rng.uniform(0.05, 0.14), 0, 1)
    # small eddies along band edges, and maybe one big storm
    spots = []
    for e in rng.choice(edges[1:-1], size=min(3, len(edges) - 2), replace=False):
        spots.append((rng.uniform(-0.7, 0.7), e, rng.uniform(0.06, 0.12), rng.uniform(0.03, 0.06)))
    if rng.uniform() < 0.7:
        spots.append((rng.uniform(-0.4, 0.4), rng.uniform(-0.55, 0.55),
                      rng.uniform(0.18, 0.28), rng.uniform(0.08, 0.13)))
    for sx, sy, rx, ry in spots:
        q = ((nx - sx) / rx) ** 2 + ((ny - sy) / ry) ** 2
        swirl = np.clip(1 - q, 0, 1)
        ring = np.clip(1 - np.abs(q - 0.8) / 0.25, 0, 1)
        t = t * (1 - swirl) + rng.choice([0.0, 1.0]) * swirl * 0.8 + t * swirl * 0.2
        t = np.clip(t - ring * 0.25, 0, 1)
    cols = np.array(palette, np.float32)
    idx = np.clip(t * (len(cols) - 1), 0, len(cols) - 1.001); lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    rgb = (cols[lo] * (1 - f) + cols[lo + 1] * f) * shade[..., None]
    return _rgba(rgb, np.clip((1 - np.sqrt(d2)) * r, 0, 1))


def gas_giant(rng, palette):
    g = banded_sphere(rng, GIANT_D * 2, palette).resize((GIANT_D + 8, GIANT_D + 8), Image.LANCZOS)
    size = GIANT_D + 24
    out = Image.new("RGBA", (size, size))
    halo = Image.new("RGBA", (size, size)); c = size / 2
    ImageDraw.Draw(halo).ellipse([c - GIANT_D / 2 - 2, c - GIANT_D / 2 - 2, c + GIANT_D / 2 + 2, c + GIANT_D / 2 + 2],
                                 fill=tuple(palette[2]) + (90,))
    out.alpha_composite(halo.filter(ImageFilter.GaussianBlur(5)))
    out.alpha_composite(g, ((size - g.width) // 2,) * 2)
    return out


# ---------------------------------------------------------------- big objects
# Four-hex centrepieces, drawn like the gas giants over a diamond of four
# hexes, each to sit in the middle of a cluster of the matching cloud.

BIG = GIANT_D + 24     # the same size as a gas giant's image
BIG_BLACK_HOLES = [
    dict(),                                                                          # gold, edge-on
    dict(tilt=0.3, angle=-12, tint=(0.55, 0.7, 1.0), hot=(0.92, 0.96, 1.0)),        # blue-white, tilted
    dict(tilt=0.1, angle=8, tint=(1.0, 0.35, 0.2), hot=(1.0, 0.85, 0.7)),           # red, edge-on
    dict(tint=(1.0, 0.45, 0.12), hot=(1.0, 0.85, 0.5), eht=True),                    # orange ring, from the pole
]
GLOBULAR_CLUSTERS = [dict(), dict(rc=9, warm=0.9), dict(rc=16, warm=0.3, n=20000), dict(rc=11, warm=0.75, rt=64)]


def big_black_hole(rng, tilt=0.16, angle=0, tint=(1.0, 0.72, 0.42), hot=(1.0, 0.97, 0.9), beam=0.7, rs=23, lens_k=2.2, eht=False):
    """A black hole as the simulations and photographs show it: a round
    black shadow edged by a thin photon ring, the accretion disc seen nearly
    edge-on across it, and the far side of the disc bent by gravity into
    bands over the top and under the bottom of the shadow. The side of the
    disc turning towards us is brighter. `eht` instead draws it seen down
    the pole, a blurred ring of light as in the first photographs."""
    S = 3
    W = BIG * S
    x, y = _grid(W); x, y = x / S, y / S
    d = np.hypot(x, y); th = np.arctan2(y, x)
    tex = _noise(rng, W, 5, 6)
    rin, rout = rs * 1.45, 72
    # the disc's own brightness at disc radius r and azimuth a: hot inside,
    # fading out, in fine concentric streaks
    def emis(r, a):
        f = np.clip((r - rin) / 2.5, 0, 1) * np.clip((rout - r) / 25, 0, 1)
        streak = 0.8 + 0.2 * np.sin(r * 0.9 + 5 * tex + a * 0.5) + 0.15 * (tex - 0.5)
        return 1.7 * f * (rin / np.maximum(r, 1)) ** 1.3 * streak
    # primary image: the disc seen nearly edge-on
    X, Y = x, y / tilt
    r = np.hypot(X, Y); a = np.arctan2(Y, X)
    dop = np.clip(1 - beam * X / np.maximum(r, 1), 0.25, 2)
    prim = emis(r, a) * dop
    near = Y > 0
    # lensed image of the far side, bent over the top of the shadow, and a
    # fainter one of the underside, wrapped under it
    w = (1 - tilt) * np.abs(np.sin(th)) ** 0.6 + tilt
    rr = rin + (d - rs * 1.1) * lens_k / np.maximum(w, 0.05)
    lens = emis(rr, th) * np.where(y < 0, 1.0, 0.55) * np.clip(1 - beam * np.cos(th), 0.25, 2) * (d > rs)
    ring = np.exp(-((d - rs * 1.04) / 0.9) ** 2) * (1.0 + 0.3 * np.clip(-np.cos(th), 0, 1))
    def colour(I):
        I = np.clip(I, 0, None)
        t = np.clip(I, 0, 1)[..., None]
        base = np.array(tint)[None, None] * 255
        white = np.array(hot)[None, None] * 255
        return base * np.clip(I * 1.6, 0, 1)[..., None] * (1 - t ** 2) + white * t ** 2
    def layer(I):
        return _rgba(colour(I), np.clip(I * 1.8, 0, 1))
    shadow = np.clip((rs - d) * 1.5, 0, 1)
    img = Image.new("RGBA", (W, W))
    if eht:     # seen from above the pole, as in the first photographs: a blurred ring of light
        I = np.exp(-((d - rs * 1.3) / 7) ** 2) * (0.35 + 0.65 * np.clip(np.sin(th + 0.4), -0.6, 1) + 0.25) * (0.8 + 0.4 * tex) * 0.6
        I = I + np.exp(-((d - rs * 1.3) / 16) ** 2) * 0.25
        g = layer(I).filter(ImageFilter.GaussianBlur(2.5 * S))
        img.alpha_composite(g)
        img.alpha_composite(_rgba(np.zeros((W, W, 3)), np.clip((rs * 0.95 - d) * 0.25, 0, 1) * 0.92))
        return img.resize((BIG, BIG), Image.LANCZOS)
    back = layer(prim * ~near + lens)
    glow_src = layer((prim + lens) * 0.9 + ring)
    glow = glow_src.filter(ImageFilter.GaussianBlur(7 * S))
    ga = np.asarray(glow, np.float32); ga[..., 3] *= 0.55
    img.alpha_composite(Image.fromarray(ga.astype(np.uint8)))
    img.alpha_composite(back)
    img.alpha_composite(_rgba(np.zeros((W, W, 3)), shadow))
    img.alpha_composite(layer(ring * 1.2))
    img.alpha_composite(layer(prim * near))
    if angle:
        img = img.rotate(angle, Image.BICUBIC)
    return img.resize((BIG, BIG), Image.LANCZOS)


def globular_cluster(rng, rc=13, rt=70, n=16000, warm=0.6):
    """A ball of countless old stars, packed tight towards a blazing core."""
    S = 3
    W = BIG * S
    acc = np.zeros((W, W, 3), np.float32)
    # Plummer-like profile: radius from the cumulative distribution, cut at rt
    u = rng.uniform(0, 0.97, n)
    r = rc * u ** (1 / 3) / np.sqrt(1 - u ** (2 / 3))
    r = r[r < rt]
    a = rng.uniform(0, 2 * np.pi, len(r))
    xs = W / 2 + r * np.cos(a) * S; ys = W / 2 + r * np.sin(a) * S
    lum = rng.pareto(2.5, len(r)) * 0.3 + 0.1
    kind = rng.uniform(0, 1, len(r))
    col = np.where((kind < 0.12)[:, None], [[255, 150, 90]],                 # red giants
          np.where((kind > 0.96)[:, None], [[170, 200, 255]],               # blue stragglers
                   [[255, 235 - 25 * warm, 200 - 60 * warm]])).astype(np.float32)
    xi = np.clip(xs.astype(int), 0, W - 1); yi = np.clip(ys.astype(int), 0, W - 1)
    np.add.at(acc, (yi, xi), col * lum[:, None])
    fy = np.fft.fftfreq(W)[:, None]; fx = np.fft.fftfreq(W)[None, :]

    def blur(a, r):         # gaussian blur in float, through the FFT
        k = np.exp(-2 * (np.pi * r) ** 2 * (fx ** 2 + fy ** 2))
        return np.dstack([np.real(np.fft.ifft2(np.fft.fft2(a[..., c]) * k)) for c in range(3)])
    stars = blur(acc, 0.65 * S) * 2 * np.pi * (0.65 * S) ** 2 / 255
    halo = blur(acc, 5 * S) * 8 / 255
    x, y = _grid(W); d = np.hypot(x, y) / S
    # the unresolved glow of the fainter stars, falling off like the stars do
    core = (1 + (d / rc) ** 2)[..., None] ** -2 * np.array([1.0, 0.88, 0.66]) * 0.9 * np.clip((rt - d) / 15, 0, 1)[..., None]
    light = stars + halo + core                     # 1 = full white
    L = light.max(axis=2)
    T = 1 - np.exp(-L * 1.1)                        # tone-mapped brightness
    alpha = np.clip(T * 1.25, 0, 1)
    hue = light / np.maximum(L, 1e-4)[..., None]
    rgb = np.clip(hue * (0.6 + 0.4 * T)[..., None] + np.clip(T - 0.8, 0, 1)[..., None] * 1.5, 0, 1) * 255
    out = _rgba(rgb, alpha)
    return out.resize((BIG, BIG), Image.LANCZOS)


# A gas giant standing in a cloud has wisps of that cloud drifting in front
# of it: (dark, light) colours of each cloud's veil, and its terrain code.
GIANT_VEILS = {
    "darknebula": ("Yqd", (22, 9, 34), (80, 46, 110)),
    "plasmastorm": ("Yqp", (55, 12, 70), (160, 60, 175)),
    "radiation": ("Yqr", (50, 85, 15), (160, 210, 55)),
    "eddy": ("Yqe", (35, 22, 75), (140, 105, 220)),
    "nebula": ("Yn", (40, 140, 90), (120, 200, 90)),
    "rednebula": ("Yr", (150, 35, 40), (220, 80, 50)),
    "dust": ("Yd", (110, 85, 60), (170, 140, 100)),
}


def veiled(rng, giant, dark, light):
    """`giant` with patches of cloud in front of it: thick in places, gone
    in others, fading out just past the planet's rim."""
    size = giant.width
    x, y = _grid(size)
    r = np.hypot(x, y)
    patch = np.clip(_noise(rng, size, 4, 3) * 2.3 - 0.95, 0, 1)
    wisp = _ridged(_noise(rng, size, 4, 6)) ** 4
    shade = _noise(rng, size, 3, 4)
    a = np.clip(patch * 0.8 + wisp * patch * 0.3, 0, 0.88) * np.clip((GIANT_D / 2 + 5 - r) / 9, 0, 1)
    veil = _rgba(_mix(dark, light, np.clip(shade * 0.8 + wisp * 0.5, 0, 1)), a)
    out = giant.copy()
    out.alpha_composite(veil)
    return out


def build_objects(rng, out, save, apply_mask, starfield, mask):
    for name, make in [("black-hole", black_hole), ("pulsar", pulsar)]:
        img = make(rng)
        save(img, out, f"images/terrain/sc/{name}.png", False)
        tile = apply_mask(starfield(rng), mask); tile.alpha_composite(img)
        save(apply_mask(tile, mask), out, f"images/terrain/sc/{name}-tile.png", False)
    giants = []
    for i, pal in enumerate(GAS_GIANTS):
        img = gas_giant(rng, pal)
        giants.append(img)
        save(img, out, f"images/terrain/sc/gas-giant{'' if i == 0 else i + 1}.png", False)
        if i == 0:
            tile = apply_mask(starfield(rng), mask)
            tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
            save(apply_mask(tile, mask), out, "images/terrain/sc/gas-giant-tile.png", False)
    # More black holes, added later with their own seed so the art above stays the same.
    brng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 1)
    for i, style in enumerate(BLACK_HOLES[1:]):
        save(black_hole(brng, **style), out, f"images/terrain/sc/black-hole{i + 2}.png", False)
    # Gas giants veiled by the cloud they stand in, with their own seed too.
    vrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 3)
    for name, (code, dark, light) in GIANT_VEILS.items():
        for i, img in enumerate(giants):
            save(veiled(vrng, img, dark, light), out,
                 f"images/terrain/sc/gas-giant-{name}{'' if i == 0 else i + 1}.png", False)
    # The four-hex black holes and globular clusters, also with their own seed.
    grng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 2)
    for name, make, styles in [("black-hole-big", big_black_hole, BIG_BLACK_HOLES),
                               ("globular-cluster", globular_cluster, GLOBULAR_CLUSTERS)]:
        for i, style in enumerate(styles):
            img = make(grng, **style)
            save(img, out, f"images/terrain/sc/{name}{'' if i == 0 else i + 1}.png", False)
            if i == 0:
                tile = apply_mask(starfield(grng), mask)
                tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
                save(apply_mask(tile, mask), out, f"images/terrain/sc/{name}-tile.png", False)
