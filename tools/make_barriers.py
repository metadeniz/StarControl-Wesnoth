"""Impassable barriers other than asteroid walls: original art.

Two kinds:

* Blobs, painted hex by hex in any shape: dark nebula, radiation zone,
  plasma storm and gravity eddy. They are drawn like the nebulae (see
  build_gas_nebula in make_art.py): each is one big cloud that wraps round
  every few hexes, each hex shows its own piece of it and spills wisps onto
  its neighbours, so a blob reads as one cloud with a soft edge. This file
  only paints the clouds; make_art.py cuts them into hexes.
* Single objects, drawn as overlays: black hole, pulsar, and a gas giant
  that spans four hexes.
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

    # Dark nebula: dust so thick it blots out the stars, with faint warm folds.
    n1, n2, f = noise(rng, w, h, 5, 40), noise(rng, w, h, 4, 70), noise(rng, w, h, 5, 22)

    def dark(sl, col, row):
        a, b, fold = n1[sl], n2[sl], _ridged(f[sl])
        rgb = _mix((8, 5, 8), (80, 44, 44), np.clip(a * 0.75 + fold ** 2 * 0.35, 0, 1))
        rgb = _mix(rgb, (175, 110, 80), np.clip((a - 0.5) * 2.5, 0, 1) * fold ** 2 * 0.6)   # lit billows
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



def black_hole(rng):
    """Dead-black core in a lensed, glowing accretion disc."""
    W = HEX * S
    x, y = _grid(W); x, y = x / S, y / S
    tilt = 0.32
    rd = np.sqrt(x ** 2 + (y / tilt) ** 2)
    ang = np.arctan2(y / tilt, x)
    tex = _noise(rng, W, 4, 5)
    swirl = 0.55 + 0.45 * np.sin(ang * 3 + rd * 0.55 + tex * 4)
    disc = np.clip((rd - 12) / 3, 0, 1) * np.clip((31 - rd) / 9, 0, 1) * swirl
    d = np.sqrt(x ** 2 + y ** 2)
    ring = np.clip(1 - np.abs(d - 13.5) / 2.5, 0, 1) * (0.6 + 0.4 * np.clip(-y / 13, 0, 1))
    hot = np.clip(1 - rd / 30, 0, 1)
    doppler = np.clip(1 + x / 40, 0.6, 1.4)
    rgb = np.dstack([255 * np.ones_like(d), 120 + 120 * hot, 40 + 180 * hot ** 2]) * doppler[..., None]
    img = _rgba(rgb, np.clip(disc + ring, 0, 1) * doppler)
    core = np.clip((11 - d) * 1.5, 0, 1)
    front = (y > 0) & (rd > 12)                 # the near half of the disc passes in front
    img.alpha_composite(_rgba(np.zeros((W, W, 3)), core * np.where(front, 1 - np.clip(disc * 1.4, 0, 1), 1)))
    glow = Image.new("RGBA", (W, W), (255, 140, 60, 0))
    ImageDraw.Draw(glow).ellipse([W / 2 - 26 * S, W / 2 - 12 * S, W / 2 + 26 * S, W / 2 + 12 * S], fill=(255, 140, 60, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(5 * S))
    glow.alpha_composite(img)
    return glow.resize((HEX, HEX), Image.LANCZOS)


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
]
GIANT_D = 134          # fits the diamond of four hexes it stands on


def gas_giant(rng, palette):
    g = sphere(rng, GIANT_D * 2, palette, "gas").resize((GIANT_D + 8, GIANT_D + 8), Image.LANCZOS)
    size = GIANT_D + 24
    out = Image.new("RGBA", (size, size))
    halo = Image.new("RGBA", (size, size)); c = size / 2
    ImageDraw.Draw(halo).ellipse([c - GIANT_D / 2 - 2, c - GIANT_D / 2 - 2, c + GIANT_D / 2 + 2, c + GIANT_D / 2 + 2],
                                 fill=tuple(palette[2]) + (90,))
    out.alpha_composite(halo.filter(ImageFilter.GaussianBlur(5)))
    out.alpha_composite(g, ((size - g.width) // 2,) * 2)
    return out


def build_objects(rng, out, save, apply_mask, starfield, mask):
    for name, make in [("black-hole", black_hole), ("pulsar", pulsar)]:
        img = make(rng)
        save(img, out, f"images/terrain/sc/{name}.png", False)
        tile = apply_mask(starfield(rng), mask); tile.alpha_composite(img)
        save(apply_mask(tile, mask), out, f"images/terrain/sc/{name}-tile.png", False)
    for i, pal in enumerate(GAS_GIANTS):
        img = gas_giant(rng, pal)
        save(img, out, f"images/terrain/sc/gas-giant{'' if i == 0 else i + 1}.png", False)
        if i == 0:
            tile = apply_mask(starfield(rng), mask)
            tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
            save(apply_mask(tile, mask), out, "images/terrain/sc/gas-giant-tile.png", False)
