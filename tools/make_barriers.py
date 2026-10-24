"""Impassable barriers other than asteroid walls: original art.

Two kinds:

* Blobs, painted hex by hex in any shape: dark nebula, radiation zone,
  plasma storm and gravity eddy. They are drawn like the nebulae (see
  build_gas_nebula in make_art.py): each is one big cloud that wraps round
  every few hexes, each hex shows its own piece of it and spills wisps onto
  its neighbours, so a blob reads as one cloud with a soft edge. This file
  only paints the clouds; make_art.py cuts them into hexes.
* Single objects, drawn as overlays: black hole (four of them, picked per
  hex), pulsar, and five that span four hexes: brown dwarf, supergiant,
  supermassive black hole, globular cluster and red supergiant (in its
  debris disk); and the protostar in its protoplanetary disk.
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


# smaller, more numerous, more branched bolts (D asked for more of them)
STORM_BOLTS = dict(per=(2, 4), size=0.7, forks=(2, 4))


def _bolts(rng, w, h, n, S=3, per=(1, 2), size=1.0, forks=(1, 3)):
    """Fewer, bolder bolts for the plasma storm: n bolts, each in a hex of
    its own and fading out well inside it, so no bolt is ever cut off at a
    hex edge. A bolt is a thick jagged channel, zigzagging about one
    heading and thinning towards its ends, with a fork or two. Drawn S
    times larger and shrunk so the edges are soft. Returns the core and a
    wider glow, each as alpha in 0..1, over the w x h field that wraps."""
    core = Image.new("L", (w * S, h * S))
    halo = Image.new("L", (w * S, h * S))
    dc, dh = ImageDraw.Draw(core), ImageDraw.Draw(halo)

    def channel(x, y, a, steps, width, step):
        pts = [(x, y)]
        for _ in range(steps):
            t = a + rng.uniform(-0.75, 0.75)              # sharp zigzags about the heading
            x += step * math.cos(t); y += step * math.sin(t)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            k = i / max(len(pts) - 2, 1)
            wd = width * (1 - 0.6 * k)                    # thins towards the tip
            for ox in (-w, 0, w):                         # the field wraps round
                for oy in (-h, 0, h):
                    seg = [((px + ox) * S, (py + oy) * S) for px, py in pts[i:i + 2]]
                    dc.line(seg, fill=255, width=max(1, round(wd * S)), joint="curve")
                    dh.line(seg, fill=255, width=round((wd + 9) * S), joint="curve")
                    for (qx, qy), r in ((seg[0], wd * S / 2), (seg[1], wd * S / 2 * 0.85)):
                        dc.ellipse([qx - r, qy - r, qx + r, qy + r], fill=255)   # round joints
        return pts

    cols, rows = w // 54, h // 72
    hexes = [(c, r) for c in range(cols) for r in range(rows)]
    for i in rng.choice(len(hexes), n, replace=False):
        c, r = hexes[i]
        k = int(rng.integers(per[0], per[1]))
        for j in range(k):                                # per[0]..per[1]-1 bolts in the hex
            cx, cy = 54 * c + 36, 72 * r + 36 + (36 if c % 2 else 0)
            if k > 1:                                     # spread round the middle
                t = 2 * math.pi * j / k + rng.uniform(-0.5, 0.5)
                cx += 13 * math.cos(t); cy += 13 * math.sin(t)
            # each bolt runs roughly round the middle, not across it,
            # so bolts in one hex don't tangle
            a = (t + math.pi / 2 + rng.uniform(-0.5, 0.5)) if k > 1 else rng.uniform(0, 2 * math.pi)
            steps, step = int(rng.integers(4, 6)), 11.5 * size
            x0, y0 = cx - math.cos(a) * steps * step / 2, cy - math.sin(a) * steps * step / 2
            pts = channel(x0, y0, a, steps, rng.uniform(4.0, 5.0) * size, step)
            for _ in range(int(rng.integers(*forks))):    # forks, some forking again
                px, py = pts[int(rng.integers(1, len(pts) - 1))]
                fa = a + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9)
                fp = channel(px, py, fa, int(rng.integers(1, 3)), 2.5 * size, 9 * size)
                if size < 1 and len(fp) > 1 and rng.random() < 0.5:
                    channel(*fp[-1], fa + rng.choice([-1, 1]) * rng.uniform(0.4, 0.8), 1, 1.8 * size, 7 * size)
    # fade out towards the edge of each hex (wrapping round the field)
    pts = _hex_centres(w, h)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    best = np.full((h, w), 1e9, np.float32)
    for px, py, _ in pts:
        best = np.minimum(best, (xx - px) ** 2 + (yy - py) ** 2)
    fade = np.clip((33 - np.sqrt(best)) / 8, 0, 1)
    core = np.asarray(core.resize((w, h), Image.LANCZOS), np.float32) / 255 * fade
    halo = np.asarray(halo.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255 * fade
    return core, halo


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
    # (the old thin bolts are still drawn, so the clouds after them stay
    # the same, but no longer used: the bolts now are fewer and bolder,
    # with their own seed)
    _lightning(rng, w, h, w * h // 3600, (255, 205, 255))
    bolt, glow = _bolts(np.random.default_rng(rng.bit_generator.seed_seq.entropy + 1), w, h, 12, **STORM_BOLTS)

    def cloud(sl):
        """The storm's cloud itself: violet billows, lit in big soft
        patches, the same in every storm hex so they all run together."""
        a, b = p1[sl], p2[sl]
        rgb = _mix((60, 14, 82), (170, 60, 190), a)
        body = np.clip((b - 0.3) * 1.6, 0, 1)
        rgb = _mix(rgb, (210, 100, 245), body * 0.55)
        return rgb, 0.82 + 0.12 * (b - 0.5) + body * 0.1

    def lightning(sl, bolt, glow):
        rgb, alpha = cloud(sl)
        g = np.clip(glow[sl] * 1.6, 0, 1)
        rgb = _mix(rgb, (215, 95, 255), g * 0.7)
        rgb = _mix(rgb, (255, 235, 255), bolt[sl])
        return _rgba(rgb, np.clip(alpha + g * 0.3, 0, 0.97))

    def storm(sl, col, row):
        return lightning(sl, bolt, glow)
    painters["plasmastorm"] = storm

    # The hex holding a star or pulsar: the same cloud with no lightning
    def calm_storm(sl, col, row):
        rgb, alpha = cloud(sl)
        return _rgba(rgb, np.clip(alpha, 0, 0.97))
    painters["plasmastorm-calm"] = calm_storm

    # The storm hexes next to a star: a bolt in every one (its own seed),
    # each fading out inside its own hex, so the star's hex stays calm
    nbolt, nglow = _bolts(np.random.default_rng(rng.bit_generator.seed_seq.entropy + 2),
                          w, h, (w // 54) * (h // 72), **STORM_BOLTS)

    def near_storm(sl, col, row):
        return lightning(sl, nbolt, nglow)
    painters["plasmastorm-near"] = near_storm

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
    phase = r / 4.5 - spin * th * 3 + en * 4
    arms = (0.5 + 0.5 * np.sin(phase)) ** 4 * np.exp(-r / 34)
    core = np.clip(1 - r / 11, 0, 1)
    # faint wisps of starlight in the dark lanes between the arms, curving
    # with them, broken up by noise
    wn = noise(rng, w, h, 4, 18)
    lane = np.exp(-((1 + np.sin(phase)) / 0.09) ** 2)
    wisps = lane * np.clip((wn - 0.35) * 2.5, 0, 1) * np.clip((r - 9) / 6, 0, 1) * np.exp(-r / 40)

    def eddy(sl, col, row):
        a, k, c, st = arms[sl], core[sl], en[sl], wisps[sl]
        rgb = _mix((22, 12, 46), (170, 120, 255), np.clip(a * 1.1, 0, 1))
        rgb = _mix(rgb, (200, 175, 255), st * 0.8)
        rgb = _mix(rgb, (3, 1, 10), k)
        return _rgba(rgb, np.clip(0.62 + 0.15 * (c - 0.5) + a * 0.4 + st * 0.25 + k, 0, 0.97))
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
    """A white-blue neutron star sweeping two bright beams out to the edge of
    its hex, ringed by the wind nebula they stir up."""
    W = HEX * S
    x, y = _grid(W); x, y = x / S, y / S
    d = np.sqrt(x ** 2 + y ** 2)
    th = math.radians(rng.uniform(50, 75))
    along = x * math.cos(th) + y * math.sin(th); across = -x * math.sin(th) + y * math.cos(th)
    reach = np.clip(1 - (d / 34) ** 2, 0, 1)                      # the beams fade out inside the hex
    spine = np.clip(1 - np.abs(across) / (1.3 + np.abs(along) * 0.05), 0, 1) * reach
    cone = np.clip(1 - np.abs(across) / (1.8 + np.abs(along) * 0.2), 0, 1) ** 1.3 * reach
    glow = np.exp(-(across / (2.5 + np.abs(along) * 0.22)) ** 2) * reach ** 1.5
    knots = 0.85 + 0.15 * np.sin(np.abs(along) * 0.7)            # pulses running out along the beams
    beam = np.clip(spine + cone * 0.9 * knots + glow * 0.35, 0, 1)
    core = np.clip((9 - d) * 0.9, 0, 1)
    halo = np.clip(1 - d / 20, 0, 1) ** 2
    ring = np.clip(1 - np.abs(np.sqrt((along * 2.6) ** 2 + across ** 2) - 15) / 3, 0, 1) * 0.55
    neb = np.clip(1 - d / 32, 0, 1) ** 1.5 * (0.3 + 0.4 * _noise(rng, W, 3, 4)) * 0.6
    a = np.clip(np.maximum.reduce([core, halo * 0.95, beam, neb, ring]), 0, 1)
    w = np.clip(core + spine + cone * 0.55 * knots + halo * 0.3, 0, 1)
    rgb = np.dstack([80 + 175 * w, 150 + 105 * w, np.full_like(d, 255)])
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


# Brown dwarfs: failed stars, still glowing with the heat of their birth.
# Each look: dark band, light band, hot streak, white-hot core, corona.
BROWN_DWARFS = [
    # dark band, light band, hot streak, white-hot core, corona; then how
    # many bands (from, to) and how much of the deck breaks open (0..1)
    [(45, 8, 4), (175, 50, 14), (255, 125, 25), (255, 225, 130), (255, 150, 40), (5, 8), 0.5],     # ember
    [(55, 6, 4), (200, 35, 12), (255, 95, 20), (255, 215, 110), (255, 120, 30), (5, 8), 0.5],      # red-hot
    [(30, 14, 8), (110, 60, 28), (230, 140, 60), (255, 225, 160), (240, 150, 70), (5, 8), 0.5],    # brown, banded
    [(22, 4, 6), (100, 22, 22), (240, 80, 40), (255, 190, 110), (230, 90, 60), (5, 8), 0.5],       # dim
    [(38, 22, 8), (115, 72, 30), (255, 225, 40), (255, 252, 190), (255, 215, 60), (6, 9), 0.75],   # brown and bright yellow
    [(40, 8, 30), (140, 35, 95), (255, 95, 165), (255, 215, 235), (235, 95, 185), (4, 6), 0.4],    # magenta (the coolest)
    [(40, 22, 8), (195, 140, 50), (240, 200, 105), (255, 235, 170), (225, 100, 40), (3, 5), 0.0, "mottled"],  # mottled brown and ochre
    [(18, 10, 8), (70, 45, 30), (200, 95, 35), (255, 180, 100), (190, 90, 50), (3, 5), 0.25],      # dark, nearly cold
]
# the look kept for the maps: the dark, nearly cold one (the magenta one,
# 5, was dropped later)
BROWN_DWARFS_KEPT = [7]


def _stretched(rng, s, octaves, base, sx=4):
    """noise smeared sideways, sx times wider than tall"""
    n = _noise(rng, s, octaves, base)
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((s * sx, s), Image.BICUBIC)
    off = int(rng.integers(0, s * (sx - 1)))
    return np.asarray(im, np.float32)[:, off:off + s] / 255

def brown_dwarf(rng, style):
    """Lit from inside, not by a sun: dark bands and glowing ones, with hot
    streaks where the cloud deck breaks open, dimmer at the limb, and a
    ragged corona brightest on one side."""
    dark, mid, hot, core, glow = [np.array(c, np.float32) for c in style[:5]]
    (k0, k1), breaks = style[5], style[6]
    d = GIANT_D * 2; s = d + 8
    x, y = _grid(s); r = d / 2
    nx, ny = x / r, y / r; d2 = nx ** 2 + ny ** 2
    inside = d2 < 1
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    # latitude on the globe, so bands bunch up towards the poles
    lat = np.arcsin(np.clip(ny, -1, 1)) / (np.pi / 2)
    warp = _noise(rng, s, 4, 3) - 0.5
    lat = lat + 0.10 * warp + 0.06 * (_stretched(rng, s, 4, 5) - 0.5) + 0.03 * np.sin(nx * rng.uniform(5, 9) + rng.uniform(0, 6.3))
    # dark and light bands
    k = rng.uniform(k0, k1)
    bands = 0.5 + 0.5 * np.sin(lat * np.pi * k + rng.uniform(0, 6.3))
    bands = np.clip(bands * 0.6 + 0.6 * _stretched(rng, s, 5, 4) - 0.1, 0, 1)
    # hot streaks: ragged ridges of the smeared noise, glowing where the
    # cloud deck breaks open, mostly inside the light bands
    st = _ridged(_stretched(rng, s, 5, 6, 5))
    cut = 0.70 + 0.2 * (0.5 - breaks)
    streak = np.clip((st - cut) / 0.25, 0, 1) ** 1.1 * np.clip(bands * 1.8 - 0.35, 0, 1)
    flecks = np.clip((_stretched(rng, s, 3, 16, 3) - 0.78) / 0.22, 0, 1) * bands
    heat = np.clip(streak + flecks * 0.5, 0, 1)
    if style[7:] == ["mottled"]:
        # no glowing streaks: broad soft bands broken into blotches of
        # ochre and dark brown, the light patches a little paler
        blot = warp + 0.5
        sharp = np.clip((bands - 0.35) / 0.3, 0, 1)
        tone = 0.35 * sharp + 0.15 * st + 0.75 * blot - 0.2
        tone = (tone - 0.45) * 1.5 + 0.45 + 0.12 * (st - 0.5)
        bands = np.clip(tone, 0, 1)
        heat = np.clip((tone - 0.8) / 0.3, 0, 1) * 0.6
    rgb = dark + (mid - dark) * bands[..., None]
    rgb = rgb + (hot - rgb) * np.clip(heat * 1.4, 0, 1)[..., None]
    rgb = rgb + (core - rgb) * np.clip(heat * 2.2 - 1.3, 0, 1)[..., None]
    # self-lit: dimmer at the limb, a little brighter towards one side
    limb = 0.45 + 0.55 * nz ** 0.5
    side = 0.85 + 0.25 * np.clip(-nx * 0.6 - ny * 0.4, -1, 1)
    rgb = rgb * (limb * side)[..., None]
    # a hot rim: the edge glows as the light comes through the thin outer air
    glowside = np.clip(0.35 + 0.65 * (-nx * 0.7 - ny * 0.7), 0, 1)
    rim = np.clip((np.sqrt(d2) - 0.84) / 0.16, 0, 1) ** 2 * inside * glowside
    rgb = rgb + (glow - rgb) * (rim * 0.55)[..., None]
    a = np.clip((1 - np.sqrt(d2)) * r, 0, 1)
    globe = _rgba(rgb, a).resize((GIANT_D + 8, GIANT_D + 8), Image.LANCZOS)
    size = GIANT_D + 24
    out = Image.new("RGBA", (size, size))
    # the corona: a ragged glow just outside the limb
    gx, gy = _grid(size); gr = np.hypot(gx, gy) / (GIANT_D / 2)
    ang = np.arctan2(gy, gx)
    flick = _noise(rng, size, 4, 8)
    ring = np.exp(-((gr - 1.0) / (0.045 + 0.05 * flick)) ** 2) * (gr > 0.97)
    halo = np.exp(-np.clip(gr - 1, 0, None) / 0.08) * (gr > 1) * 0.5
    side = np.clip(0.25 + 0.75 * (-np.cos(ang) * 0.7 - np.sin(ang) * 0.7), 0.15, 1)
    ga = np.clip((ring * (0.5 + 1.0 * flick) + halo * 1.3) * side, 0, 1)
    out.alpha_composite(_rgba(np.broadcast_to(glow, (size, size, 3)), ga))
    out.alpha_composite(globe, ((size - globe.width) // 2,) * 2)
    return out

# Supergiants: the biggest stars, each filling four hexes. Their colour
# follows their surface heat, as on a star chart: blue (hottest, like
# Rigel), white (like Deneb), yellow (like Rho Cassiopeiae), orange and
# red (coolest, like Betelgeuse), and one green, which no real star shows
# (a star that shines brightest in green looks white to the eye).
# Each: core, middle, limb, glow; how big and bold its convection cells
# are (cells across the disc, contrast), and how far the glow reaches.
SUPERGIANT_D = 146             # a little bigger than a brown dwarf
SUPERGIANT_SIZE = 216          # room for the glow round it
SUPERGIANTS = [
    [(255, 255, 240), (255, 222, 110), (205, 120, 25), (255, 205, 80), (10, 0.45), 1.0],    # yellow
    [(240, 246, 255), (150, 182, 255), (70, 95, 225), (120, 165, 255), (32, 0.18), 1.5],    # blue
    [(255, 205, 150), (230, 85, 35), (105, 18, 8), (225, 55, 25), (6, 0.6), 0.9],           # red
    [(255, 255, 255), (228, 234, 255), (160, 175, 225), (215, 225, 255), (24, 0.18), 1.3],  # white
    [(235, 255, 230), (110, 235, 135), (20, 120, 60), (90, 235, 120), (20, 0.3), 1.1],      # green
    [(255, 240, 200), (255, 160, 65), (170, 65, 15), (255, 130, 45), (9, 0.45), 0.95],      # orange
]


def _cells(rng, s, n, R, warp):
    """Cellular noise over a disc of radius R, its grid warped by up to
    warp pixels so the cells are not straight-edged: (distance to the
    nearest of n random points minus to the next nearest, which is 0 on
    the lanes between cells; and each pixel's cell's own brightness)."""
    x, y = _grid(s)
    x = x + warp * (_noise(rng, s, 4, 4) - 0.5) * 2
    y = y + warp * (_noise(rng, s, 4, 4) - 0.5) * 2
    a = rng.uniform(0, 2 * np.pi, n); q = R * 1.1 * np.sqrt(rng.uniform(0, 1, n))
    px, py, lum = q * np.cos(a), q * np.sin(a), rng.uniform(0, 1, n)
    d = np.stack([np.hypot(x - u, y - v) for u, v in zip(px, py)])
    order = np.argsort(d, axis=0)[:2]
    d1 = np.take_along_axis(d, order[:1], 0)[0]
    d2 = np.take_along_axis(d, order[1:2], 0)[0]
    return d2 - d1, lum[order[0]]


def supergiant(rng, style):
    """A supergiant star: a bright disc dimming towards its limb, mottled
    by convection cells (few and huge in the cool red ones, fine in the
    hot blue ones), flares licking off its edge, and a wide soft glow."""
    core, mid, limb, glow = [np.array(c, np.float32) for c in style[:4]]
    (n, contrast), reach = style[4], style[5]
    s = SUPERGIANT_SIZE * S
    x, y = _grid(s)
    R = SUPERGIANT_D / 2 * S
    r = np.hypot(x, y)
    mu = np.sqrt(np.clip(1 - (r / R) ** 2, 0, 1))
    size = R * 1.8 / np.sqrt(n)                    # a cell's rough width
    lane, lum = _cells(rng, s, n, R, 0.35 * size)
    lane = np.clip(lane / (0.6 * size), 0, 1)
    lane = lane * lane * (3 - 2 * lane)
    wob = _noise(rng, s, 4, 10)
    gran = _fblur(np.clip(lane * (0.6 + 0.4 * lum) + 0.3 * (wob - 0.5), 0, 1), 0.08 * size)
    heat = np.clip(mu ** 0.5 * (1 - contrast + contrast * gran), 0, 1)
    rgb = np.where(heat[..., None] < 0.6,
                   _mix(limb, mid, np.clip(heat / 0.6, 0, 1)),
                   _mix(mid, core, np.clip((heat - 0.6) / 0.4, 0, 1) ** 1.3))
    disc = np.clip(R - r + 1, 0, 1)
    # flares: ragged tongues of glow just past the limb
    flick = _noise(rng, s, 4, 7)
    out_r = np.clip(r - R, 0, None)
    tongue = np.clip((flick - 0.5) / 0.3, 0, 1) * np.exp(-out_r / (0.07 * R))
    halo = 0.8 * np.exp(-out_r / (0.1 * R * reach)) + 0.4 * np.exp(-out_r / (0.3 * R * reach))
    edge = np.clip((s / 2 - r) / (0.1 * s), 0, 1) ** 1.5  # gone by the image's edge
    ga = np.clip(halo * (0.75 + 0.5 * flick) + tongue * 0.7, 0, 1) * (1 - disc) * edge
    grgb = _mix(glow, _mix(limb, mid, np.full_like(r, 0.6)), np.clip(np.exp(-out_r / (0.04 * R)), 0, 1) * 0.5)
    grgb = _mix(grgb, core, np.clip(tongue * 0.5, 0, 1))
    out = _rgba(rgb * disc[..., None] + grgb * (1 - disc)[..., None], np.clip(disc + ga, 0, 1))
    return out.resize((SUPERGIANT_SIZE, SUPERGIANT_SIZE), Image.LANCZOS)


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
# Four-hex centrepieces, drawn like the brown dwarfs over a diamond of four
# hexes, each to sit in the middle of a cluster of the matching cloud.

BIG = GIANT_D + 24     # the same size as a brown dwarf's image
BIG_BLACK_HOLES = [
    dict(),                                                                          # gold, edge-on
    dict(tilt=0.3, angle=-12, tint=(0.55, 0.7, 1.0), hot=(0.92, 0.96, 1.0)),        # blue-white, tilted
    dict(tilt=0.1, angle=8, tint=(1.0, 0.35, 0.2), hot=(1.0, 0.85, 0.7)),           # red, edge-on
    dict(tint=(1.0, 0.45, 0.12), hot=(1.0, 0.85, 0.5), eht=True),                    # orange ring, from the pole
]
# two more, added later (drawn with their own seed), so a map can show six
# different ones
BIG_BLACK_HOLES_MORE = [
    dict(tilt=0.22, angle=-20, tint=(1.0, 0.88, 0.62), hot=(1.0, 1.0, 0.95)),      # white-gold, tilted
    dict(tilt=0.4, angle=16, tint=(0.78, 0.5, 1.0), hot=(0.95, 0.9, 1.0)),          # violet, tilted
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


# The stars behind a debris disk: the colour ramp of the surface from cool
# to hot, the glow, how far it reaches (px before supersampling), how fine
# the convection cells are, and the light on the rocks (rim and body, on
# the star and past its edge).
DISK_STARS = {
    "red": dict(),
    # a young blue giant: hotter, so its surface is finely grained and
    # bright to the limb, its glow wide and its rocks rimmed blue-white
    "blue": dict(cols=[(25, 45, 140), (70, 120, 235), (140, 185, 255), (205, 228, 255), (252, 253, 255)],
                 glow_rgb=(90, 140, 255), reach=6, cells=9, grain=28, limb=0.35, boost=1.2, mottle=0.3, smooth=0.5,
                 rim=((215, 235, 255), (150, 175, 225)), body=((14, 18, 34), (62, 68, 92))),
}

# Single-hex stars behind a debris disk, drawn like the four-hex ones on the
# 128 px canvas of the plain star (^Yx). The smaller ones are dwarfs.
SMALL_DISK_STARS = [
    ("orange", dict(d=60, n_rocks=240, rock=0.7, cols=[(70, 22, 4), (160, 62, 12), (225, 118, 32), (252, 172, 75), (255, 225, 160)],
                    glow_rgb=(240, 115, 30), reach=5, cells=5, grain=16, limb=0.7, mottle=0.5, smooth=0.3,
                    rim=((255, 175, 95), (210, 150, 100)), body=((30, 22, 16), (92, 72, 58)))),
    ("red", dict(d=40, n_rocks=140, rock=0.7, reach=5)),
    # bluer than the blue giant: no white in its ramp
    ("blue", dict(d=60, n_rocks=240, rock=0.7, cols=[(8, 20, 110), (25, 60, 205), (60, 110, 255), (115, 160, 255), (185, 205, 255)],
                  glow_rgb=(45, 85, 255), reach=5, cells=8, grain=24, limb=0.4, boost=1.15, mottle=0.3, smooth=0.5,
                  rim=((170, 200, 255), (120, 145, 215)), body=((10, 14, 34), (58, 64, 92)))),
    ("white", dict(d=40, n_rocks=140, rock=0.7, cols=[(150, 155, 178), (200, 205, 226), (230, 233, 246), (246, 248, 255), (255, 255, 255)],
                   glow_rgb=(215, 222, 255), reach=5, cells=8, grain=24, limb=0.35, boost=1.1, mottle=0.25, smooth=0.55,
                   rim=((255, 255, 255), (200, 202, 218)), body=((22, 22, 30), (80, 80, 92)))),
]

SMALL_DISK_STAR_YELLOW = dict(d=50, n_rocks=190, rock=0.7, cols=[(80, 50, 6), (175, 120, 22), (235, 185, 55), (252, 225, 120), (255, 250, 210)],
                              glow_rgb=(240, 190, 60), reach=5, cells=6, grain=20, limb=0.55, mottle=0.4, smooth=0.4,
                              rim=((255, 228, 130), (210, 170, 110)), body=((30, 24, 14), (92, 78, 56)))

# and a green one and a purple one (^Yxd6, ^Yxd7), added later
SMALL_DISK_STARS_MORE = [
    ("green", dict(d=50, n_rocks=190, rock=0.7, cols=[(8, 60, 20), (25, 140, 50), (70, 210, 95), (150, 245, 160), (225, 255, 225)],
                   glow_rgb=(60, 220, 100), reach=5, cells=6, grain=20, limb=0.5, mottle=0.4, smooth=0.4,
                   rim=((170, 255, 185), (120, 190, 135)), body=((14, 28, 18), (60, 88, 66)))),
    ("purple", dict(d=50, n_rocks=190, rock=0.7, cols=[(45, 10, 75), (110, 35, 170), (170, 80, 235), (215, 150, 255), (245, 220, 255)],
                    glow_rgb=(165, 80, 255), reach=5, cells=6, grain=20, limb=0.5, mottle=0.4, smooth=0.4,
                    rim=((225, 180, 255), (160, 125, 205)), body=((24, 14, 34), (78, 62, 96)))),
]

# More supergiants behind debris disks, in the colours the red one and the
# blue giant leave out: orange, yellow and white (^Ysg2..^Ysg4). With the
# red one and the blue giant they make the five 3-hex ones (^Ytsg).
ROCKY_SUPERGIANTS = [
    ("orange", dict(cols=[(60, 16, 4), (150, 52, 10), (215, 105, 25), (245, 165, 60), (255, 220, 145)],
                    glow_rgb=(225, 105, 30), rim=((255, 175, 85), (200, 120, 90)))),
    ("yellow", dict(cols=[(75, 45, 5), (170, 115, 20), (230, 180, 50), (250, 222, 115), (255, 250, 205)],
                    glow_rgb=(235, 185, 60), rim=((255, 225, 125), (200, 120, 90)))),
    ("white", dict(cols=[(85, 90, 110), (155, 160, 182), (205, 210, 228), (238, 241, 250), (255, 255, 255)],
                   glow_rgb=(200, 212, 245), rim=((232, 238, 255), (200, 202, 218)), body=((22, 22, 30), (80, 80, 92)))),
]

# and a green one (^Ytd6), added later for Media Control, drawn last with
# its own seed so the art before it stays the same
ROCKY_SUPERGIANT_GREEN = dict(cols=[(8, 55, 18), (25, 130, 45), (70, 200, 90), (150, 240, 155), (225, 255, 225)],
                              glow_rgb=(60, 210, 95), rim=((170, 255, 185), (120, 190, 135)), body=((14, 28, 18), (60, 88, 66)))


def red_supergiant(rng, n_rocks=420, d=GIANT_D, canvas=BIG, rock=1.0, cols=((45, 4, 4), (120, 16, 10), (190, 40, 18), (235, 90, 35), (255, 165, 90)),
                   glow_rgb=(200, 35, 20), reach=7, cells=4, grain=14, limb=0.8, boost=1.15, mottle=0.6, smooth=0.2,
                   rim=((255, 110, 55), (200, 120, 90)), body=((32, 20, 18), (90, 68, 60))):
    """A red supergiant seen through the debris disk round it: a huge,
    dim, mottled red star (big convection cells, dark limb, a soft red
    glow) with a tilted band of rocks across its face and more strewn over
    it. Rocks against the star are dark, rimmed with its light on the side
    facing it; those past its edge are lit from the star. The keywords
    (see DISK_STARS) draw other stars behind the same kind of disk."""
    S = 3
    W = canvas * S
    x, y = _grid(W)
    R = d / 2 * S
    r = np.hypot(x, y)
    mu = np.sqrt(np.clip(1 - (r / R) ** 2, 0, 1))
    cells = _noise(rng, W, 3, cells)
    grain = _noise(rng, W, 4, grain)
    blobs = np.clip((cells - 0.35) * 2.2, 0, 1) ** 1.3
    heat = np.clip(mottle * blobs + 0.25 * grain + smooth * mu, 0, 1) * (0.35 + 0.65 * mu ** limb)
    cols = np.array(cols, np.float32)
    idx = np.clip(heat * boost * (len(cols) - 1), 0, len(cols) - 1.001); lo = np.floor(idx).astype(int)
    f = (idx - lo)[..., None]
    rgb = cols[lo] * (1 - f) + cols[lo + 1] * f
    disc = np.clip(R - r + 1, 0, 1)
    glow = np.exp(-np.clip(r - R, 0, None) / (reach * S)) * 0.75 * (1 - disc)
    glow_rgb = np.broadcast_to(np.array(glow_rgb, np.float32), rgb.shape)
    out = _rgba(rgb * disc[..., None] + glow_rgb * (1 - disc)[..., None], np.clip(disc + glow, 0, 1))
    # the rocks: most in a tilted band across the star, the rest strewn
    d = ImageDraw.Draw(out)
    tilt, ang = rng.uniform(0.25, 0.4), math.radians(rng.uniform(-25, -10))
    for i in range(n_rocks):
        if i < n_rocks * 0.7:                       # the band
            t = rng.uniform(-1, 1)
            u, v = t * R * 1.08, rng.normal(0, 0.16) * R * tilt * 2
            px = u * math.cos(ang) - v * math.sin(ang)
            py = u * math.sin(ang) + v * math.cos(ang)
        else:                                       # strewn over the star
            a, q = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.uniform(0, 1)) * 0.95
            px, py = q * math.cos(a), q * math.sin(a)
        size = S * min(0.7 + rng.pareto(2.6) * 1.0, 4.5) * rock
        k = int(rng.integers(6, 10))
        pts = [(px + math.cos(2 * math.pi * j / k) * size * rng.uniform(0.6, 1.25),
                py + math.sin(2 * math.pi * j / k) * size * rng.uniform(0.6, 1.25)) for j in range(k)]
        q = math.hypot(px, py)
        to_star = (-px / q, -py / q) if q > 1 else (0.0, -1.0)
        on_star = q < R
        shade = rng.uniform(0.7, 1.2)
        rim_c = tuple(int(v * shade) for v in rim[0 if on_star else 1])
        body_c = tuple(int(v * shade) for v in body[0 if on_star else 1])
        c = W / 2
        sh = size * 0.3
        d.polygon([(c + X + to_star[0] * sh, c + Y + to_star[1] * sh) for X, Y in pts], fill=rim_c + (255,))
        d.polygon([(c + X - to_star[0] * sh * 0.5, c + Y - to_star[1] * sh * 0.5) for X, Y in pts],
                  fill=body_c + (255,))
    return out.resize((canvas, canvas), Image.LANCZOS)


def _fblur(a, r):
    """Gaussian blur of a float array (2-D, or 3-D by channel) through the FFT."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * r) ** 2 * (fx ** 2 + fy ** 2))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * k))
    return np.dstack([np.real(np.fft.ifft2(np.fft.fft2(a[..., c]) * k)) for c in range(a.shape[2])])


def _polar_noise(rng, W, r, th, n_th=24, n_r=3, octaves=4):
    """Noise wrapped round the angle: streaky when n_th >> n_r."""
    side = 256
    base = _noise(rng, side, octaves, 4)
    base = np.concatenate([base, base[:, ::-1]], 1)          # mirror so it wraps in angle
    u = ((th / (2 * np.pi)) % 1) * (2 * side - 1)
    v = np.clip(r / (W / 2), 0, 1) * (side - 1)
    # stretch: n_th cycles round, n_r along the radius
    u = (u * n_th / 4) % (2 * side - 1); v = (v * n_r / 4) % (side - 1)
    return base[v.astype(int), u.astype(int)]


def _tone(light):
    """Additive light (float rgb, 0..) to rgb + alpha on a transparent ground."""
    L = light.max(-1)
    T = 1 - np.exp(-L * 1.6)
    hue = light / np.maximum(L, 1e-4)[..., None]
    rgb = np.clip(hue * T[..., None] + np.clip(T - 0.75, 0, 1)[..., None] * 1.6, 0, 1) * 255
    return rgb, np.clip(T * 1.2, 0, 1)


def _layers(back_light, disc, globe_rgb, front_light):
    """Light behind the globe, the globe (black, rgb given), then light in front."""
    rgb, a = _tone(back_light)
    img = _rgba(rgb, a)
    img.alpha_composite(_rgba(globe_rgb, disc))
    rgb, a = _tone(front_light)
    img.alpha_composite(_rgba(rgb, a))
    return img


def _ring_frame(x, y, tilt, angle):
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u = x * ca + y * sa; v = (-x * sa + y * ca) / tilt
    return u, v, np.hypot(u, v), np.arctan2(v, u)


def dark_star_eclipse(rng, light_angle=200, ring_tilt=0.22, ring_angle=-14,
                      rim=(1.0, 0.85, 1.0), edge=(0.75, 0.3, 1.0), flare=(0.35, 0.6, 1.0)):
    """A dark star eclipsing the light behind it: a black globe with a thin
    crescent of white-violet light round one side, blue flares licking off
    the crescent and its ends, and a thin tilted ring."""
    S = 3; W = BIG * S
    x, y = _grid(W); x, y = x / S, y / S
    r = np.hypot(x, y); th = np.arctan2(y, x)
    R = GIANT_D * 0.35
    face = np.cos(th - math.radians(light_angle))              # 1 on the lit side
    lit = np.clip(face + 0.2, 0, 1.2) / 1.2
    out_r = np.clip(r - R, 0, None)
    band = np.exp(-(out_r / (0.6 + 1.6 * lit)) ** 2)           # thicker mid-crescent
    crescent = band * lit ** 1.5 * 3.5 + np.exp(-out_r / 5) * lit ** 2.5 * 1.0
    ends = np.exp(-((face - 0.1) / 0.35) ** 2)                 # where the crescent thins out
    streak = _ridged(_polar_noise(rng, W, r * S, th, n_th=60, n_r=2)) ** 5
    wisp = _polar_noise(rng, W, r * S, th, n_th=14, n_r=3)
    flares = streak * np.exp(-out_r / (4 + 10 * wisp)) * (lit ** 1.5 * 0.6 + ends * 1.4)
    back = (crescent[..., None] * np.array(rim)
            + (np.exp(-out_r / 9) * lit ** 2 * 0.5)[..., None] * np.array(edge)
            + flares[..., None] * np.array(flare) * 1.8)
    back = back + _fblur(back, 2.5 * S) * 0.8
    u, v, rr, ang = _ring_frame(x, y, ring_tilt, ring_angle)
    ringl = sum(w * np.exp(-((rr - R * k) / 0.75) ** 2)
                for k, w in [(1.36, 1.0), (1.42, 0.5), (1.5, 0.8), (1.56, 0.3)])
    ringl = ringl * (0.45 + 0.55 * np.clip(np.cos(ang - math.radians(light_angle - ring_angle)) * 0.5 + 0.5, 0, 1))
    ring_light = ringl[..., None] * np.array([1.0, 0.8, 0.95]) * 1.3
    front = v > 0
    disc = np.clip(R - r + 0.7, 0, 1)
    sheen = np.exp(-(R - r) / 3) * lit ** 2 * 0.5
    globe = np.array([45, 12, 80])[None, None] * sheen[..., None]
    img = _layers(back + np.where(front[..., None], 0, ring_light), disc, globe,
                  np.where(front[..., None], ring_light, 0))
    return img.resize((BIG, BIG), Image.LANCZOS)


def dark_star_halo(rng, ring_tilt=0.42, ring_angle=-28, haze=(0.42, 0.32, 0.95), ring=(0.55, 0.95, 1.0)):
    """A dark star in a lensed violet haze: a black globe edged with a
    violet photon ring, the light round it smeared into a swirl, and a
    wispy cyan ring of gas circling it, half behind and half in front."""
    S = 3; W = BIG * S
    x, y = _grid(W); x, y = x / S, y / S
    r = np.hypot(x, y); th = np.arctan2(y, x)
    R = GIANT_D * 0.29
    swirl = _polar_noise(rng, W, r * S, th + r / 12, n_th=12, n_r=4)
    fine = _polar_noise(rng, W, r * S, th + r / 9, n_th=60, n_r=6)
    blob = _noise(rng, W, 3, 2)
    hz = (np.exp(-np.clip(r - R, 0, None) / 14) * (0.3 + 0.7 * swirl) * (0.75 + 0.35 * fine)
          * (0.4 + 1.1 * np.clip(blob - 0.25, 0, 1)) * np.clip((W / S / 2 - 4 - r) / 10, 0, 1))
    photon = np.exp(-((r - R * 1.03) / 1.2) ** 2) * 1.2 + np.exp(-((r - R * 1.15) / 3.5) ** 2) * 0.4
    back = hz[..., None] * np.array(haze) * 1.1 + photon[..., None] * np.array([0.72, 0.62, 1.0])
    u, v, rr, ang = _ring_frame(x, y, ring_tilt, ring_angle)
    width = (1.4 + 2.4 * _polar_noise(rng, W, rr * S * 0.6, ang, n_th=10, n_r=1)) * (0.6 + 0.4 * np.abs(np.sin(ang)))
    wobble = 2.5 * (_polar_noise(rng, W, rr * S * 0.6, ang + 1, n_th=7, n_r=1) - 0.5)
    tuft = _ridged(_polar_noise(rng, W, rr * S, ang, n_th=90, n_r=8)) ** 3
    ringl = np.exp(-((rr - R * 1.85 - wobble) * ring_tilt ** 0.5 / width) ** 2) * (0.7 + 0.6 * tuft)
    ringl = ringl * (1 - 0.35 * np.cos(ang - 2.4))                # one side brighter
    ring_light = ringl[..., None] * np.array(ring) * 2.2
    ring_light = ring_light + _fblur(ring_light, 4 * S) * 1.4
    front = v > 0
    disc = np.clip(R - r + 0.7, 0, 1)
    globe = np.array([60, 55, 78])[None, None] * (0.05 + 0.12 * np.clip(r / R, 0, 1) ** 4)[..., None]
    img = _layers(back + np.where(front[..., None], 0, ring_light), disc, globe,
                  np.where(front[..., None], ring_light, 0))
    return img.resize((BIG, BIG), Image.LANCZOS)


# Dark stars, for the dark nebulae (where gas giants used to stand): one
# black globe eclipsing the light behind it, ringed; one in a lensed haze
# with a wispy ring of gas round it. Two of each look.
DARK_STARS = [
    ("eclipse", dict()),
    ("halo", dict()),
    ("eclipse", dict(light_angle=-30, ring_tilt=0.3, ring_angle=18,
                     rim=(0.9, 0.95, 1.0), edge=(0.4, 0.5, 1.0), flare=(0.3, 0.75, 1.0))),
    ("halo", dict(ring_tilt=0.32, ring_angle=22, haze=(0.55, 0.28, 0.9), ring=(0.7, 0.85, 1.0))),
]


# A brown dwarf standing in a cloud has wisps of that cloud drifting in
# front of it: (dark, light) colours of each cloud's veil, and its terrain
# code. Only the clouds ships can fly through: brown dwarfs never stand in
# the impassable ones (see terrain-graphics.cfg). The impassable ones are
# still listed, as the gas giants were once veiled by them, so the same
# random draws keep the veils below byte-identical.
GIANT_VEILS = {
    "darknebula": ("Yqd", (38, 15, 58), (105, 60, 145)),
    "plasmastorm": ("Yqp", (55, 12, 70), (160, 60, 175)),
    "radiation": ("Yqr", (50, 85, 15), (160, 210, 55)),
    "eddy": ("Yqe", (35, 22, 75), (140, 105, 220)),
    "nebula": ("Yn", (40, 140, 90), (120, 200, 90)),
    "rednebula": ("Yr", (150, 35, 40), (220, 80, 50)),
    "dust": ("Yd", (110, 85, 60), (170, 140, 100)),
}


def veiled(rng, giant, dark, light, sun=(-0.55, -0.55, 0.63)):
    """`giant` with patches of cloud in front of it: thick in places, gone
    in others, fading out just past the planet's rim. The cloud follows the
    planet's light: thin and see-through on the sunlit side, thick and dark
    over the shadowed side."""
    size = giant.width
    x, y = _grid(size)
    r = np.hypot(x, y)
    R = GIANT_D / 2
    # how sunlit the planet is behind each pixel (as in banded_sphere)
    nx, ny = x / R, y / R
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    L = np.array(sun) / np.linalg.norm(sun)
    lit = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1) * (r < R)
    patch = np.clip(_noise(rng, size, 4, 3) * 2.4 - 0.7, 0, 1)
    wisp = _ridged(_noise(rng, size, 4, 6)) ** 4
    shade = _noise(rng, size, 3, 4)
    a = np.clip(patch * 0.85 + wisp * patch * 0.3, 0, 0.9) * np.clip((R + 5 - r) / 9, 0, 1)
    a = np.clip(a * (0.2 + 1.15 * (1 - lit ** 1.6)), 0, 0.9)
    rgb = _mix(dark, light, np.clip(shade * 0.8 + wisp * 0.5, 0, 1)) * (0.55 + 0.45 * lit)[..., None]
    out = giant.copy()
    out.alpha_composite(_rgba(rgb, a))
    return out


def _violet(img):
    """img recoloured in the plasma storm's violet: its dim parts violet,
    its brightest still white-hot."""
    px = np.asarray(img, np.float32)
    lum = px[..., :3].max(axis=2) / 255
    rgb = _mix((175, 70, 255), (250, 225, 255), np.clip(lum, 0, 1) ** 5) * np.clip(lum * 1.3, 0, 1)[..., None]
    return Image.fromarray(np.dstack([rgb, px[..., 3]]).clip(0, 255).astype(np.uint8), "RGBA")


# Protostars in their protoplanetary disks (^Ypd, four hexes; ^Ytpd, three):
# an amber one, a young red one deep in its cocoon, and a hot white one in
# cold grey dust.
PROTOSTARS = [
    dict(),
    dict(dust=((40, 10, 8), (115, 35, 20), (190, 75, 40), (240, 140, 85), (255, 220, 190)), haze=(140, 55, 40), haze_lit=(255, 170, 120),
         glare=(255, 205, 170), rim=(255, 160, 110), tilt=0.42, angle=-12, star_r=8,
         gaps=((0.45, 0.05, 0.7), (0.75, 0.04, 0.55))),
    dict(dust=((25, 25, 32), (80, 78, 88), (150, 145, 155), (210, 210, 225), (250, 252, 255)), haze=(105, 100, 115), haze_lit=(220, 222, 238),
         glare=(235, 242, 255), jet=(170, 200, 255), rim=(225, 232, 255), tilt=0.28, angle=-26, star_r=10,
         gaps=((0.33, 0.04, 0.8), (0.55, 0.04, 0.65), (0.74, 0.03, 0.55), (0.9, 0.03, 0.4))),
]


def protostar(rng, size=SUPERGIANT_SIZE, A=92, tilt=0.34, angle=-20, star_r=9,
              dust=((40, 20, 10), (120, 62, 28), (200, 120, 55), (245, 195, 120), (255, 245, 215)),
              haze=(150, 85, 45), haze_lit=(255, 205, 140), glare=(255, 240, 205), jet=(150, 190, 255), rim=(255, 200, 130),
              n_rocks=380, gaps=((0.38, 0.05, 0.75), (0.62, 0.04, 0.6), (0.82, 0.03, 0.5))):
    """A protostar in its protoplanetary disk: a newborn star, still
    wrapped in the dusty cocoon it formed from, with jets blown out of its
    poles. The disk round it is seen tilted, ringed with the gaps young
    planets sweep clear and strewn with rocks; its near half crosses in
    front of the star as a dark lane of dust, and the star's glare shines
    through over everything."""
    S = 3
    W = size * S
    x, y = _grid(W)
    a = math.radians(angle)
    u = x * math.cos(a) + y * math.sin(a)          # along the disk
    v = -x * math.sin(a) + y * math.cos(a)         # across it (down = near side)
    R = A * S
    rho = np.hypot(u, v / tilt) / R                 # 1 at the disk's rim
    r = np.hypot(x, y) / R
    dust = np.array(dust, np.float32)

    def ramp(t):
        idx = np.clip(t * (len(dust) - 1), 0, len(dust) - 1.001); lo = np.floor(idx).astype(int)
        f = (idx - lo)[..., None]
        return dust[lo] * (1 - f) + dust[lo + 1] * f

    # the envelope: a dusty cocoon, thicker along the disk, a cavity blown
    # out along the poles
    n1 = _noise(rng, W, 5, 3)
    n2 = _noise(rng, W, 5, 6)
    env_r = np.hypot(u / 1.12, v / 0.78) / R
    pole = np.exp(-(u / (0.16 * R + 0.45 * np.abs(v))) ** 2) * np.clip(np.abs(v) / (0.12 * R), 0, 1)
    wisp = 1 - np.abs(2 * _noise(rng, W, 5, 4) - 1)          # ridged: filaments
    env = np.exp(-env_r ** 2 * 1.1) * (0.3 + 0.6 * n1 + 0.5 * wisp ** 3) * (1 - 0.7 * pole)
    edge = np.clip((W / 2 - np.hypot(x, y)) / (0.12 * W), 0, 1) ** 1.5
    env_a = np.clip(env * 1.25, 0, 0.95) * edge
    light = np.exp(-r * 2.0)
    env_rgb = _mix(np.array(haze, np.float32) * 0.45, np.array(haze_lit, np.float32), np.clip(light * 1.2 + 0.35 * wisp ** 2 * light ** 0.3, 0, 1))
    out = np.zeros((W, W, 3), np.float32); al = np.zeros((W, W), np.float32)

    def over(rgb, a_):
        nonlocal out, al
        a_ = np.clip(a_, 0, 1)
        out = rgb * a_[..., None] + out * (1 - a_[..., None])
        al = a_ + al * (1 - a_)

    over(env_rgb, env_a)
    # jets: thin bipolar beams out of the poles
    along = np.abs(v) / R
    jet_a = np.exp(-(u / (0.025 * R + 0.05 * np.abs(v))) ** 2) * np.exp(-along / 0.45) * np.clip(along / 0.08, 0, 1) * (0.5 + 0.5 * n2) * 0.8
    over(np.broadcast_to(np.array(jet, np.float32), out.shape), jet_a * edge * 1.3)

    # the disk: rings and gaps, mottled, lit by the star
    warp = (_noise(rng, W, 4, 5) - 0.5) * 0.05
    q = rho + warp
    dens = np.clip((1 - q) / 0.18, 0, 1) * np.clip((q - 0.13) / 0.06, 0, 1)
    for c, w, g in gaps:
        dens *= 1 - g * np.exp(-((q - c) / w) ** 2)
    mott = _noise(rng, W, 5, 8)
    dens *= 0.75 + 0.45 * mott
    heat = np.clip(np.exp(-q * 2.0) * 1.1 + 0.15 * mott, 0, 1)
    disk_rgb = ramp(heat)
    front = v > 0
    back_a = np.clip(dens * 1.15, 0, 1) * (~front)
    over(disk_rgb, back_a)

    # the protostar and its glare
    rs = star_r * S
    rr = np.hypot(x, y)
    core = np.clip(rs - rr + 1, 0, 1)
    glow = np.exp(-rr / (rs * 1.4)) * 1.0 + np.exp(-rr / (rs * 4)) * 0.55
    star_rgb = _mix(np.array((255, 170, 80), np.float32), np.array((255, 252, 235), np.float32), np.clip(np.exp(-rr / (rs * 1.8)), 0, 1))
    over(star_rgb, np.clip(glow + core, 0, 1))

    # the near half of the disk passes in front of the star: dark dust,
    # silhouetted against its glare near the middle, lit further out
    sil = np.exp(-(q / 0.4) ** 2)
    front_rgb = _mix(disk_rgb, dust[0] * 0.6, np.clip(sil * 0.9, 0, 1))
    front_a = np.clip(dens * (1.1 + 0.4 * sil), 0, 1) * front
    over(front_rgb, front_a)

    img = _rgba(out, al)
    # rocks, strewn through the disk: lit on the side facing the star
    d = ImageDraw.Draw(img)
    c0 = W / 2
    rocks = []
    for i in range(n_rocks):
        t = rng.uniform(0, 2 * math.pi)
        qq = 0.16 + 0.9 * rng.beta(1.6, 1.4)
        if rng.random() < 0.25:
            qq = rng.uniform(0.16, 1.08)
        pu, pv = qq * R * math.cos(t), qq * R * math.sin(t) * tilt + rng.normal(0, 0.025 * R)
        px = pu * math.cos(a) - pv * math.sin(a)
        py = pu * math.sin(a) + pv * math.cos(a)
        rocks.append((pv, px, py, qq))
    rocks.sort()                                   # far side first
    for pv, px, py, qq in rocks:
        size_ = S * min(0.5 + rng.pareto(2.8) * 0.9, 3.6) * (1.15 - 0.4 * qq)
        k = int(rng.integers(6, 10))
        pts = [(px + math.cos(2 * math.pi * j / k) * size_ * rng.uniform(0.6, 1.25),
                py + math.sin(2 * math.pi * j / k) * size_ * rng.uniform(0.6, 1.25)) for j in range(k)]
        dist = math.hypot(px, py)
        to_star = (-px / dist, -py / dist) if dist > 1 else (0.0, -1.0)
        lit = max(0.25, min(1.0, 1.25 - qq))
        shade = rng.uniform(0.75, 1.15)
        rim_c = tuple(int(min(255, cc * lit * shade)) for cc in rim)
        body_c = tuple(int(cc * shade) for cc in (38, 26, 20))
        sh = size_ * 0.35
        d.polygon([(c0 + X + to_star[0] * sh, c0 + Y + to_star[1] * sh) for X, Y in pts], fill=rim_c + (255,))
        d.polygon([(c0 + X - to_star[0] * sh * 0.5, c0 + Y - to_star[1] * sh * 0.5) for X, Y in pts], fill=body_c + (255,))
    # the star's glare shines through, over the rocks too
    gl = np.exp(-rr / (rs * 0.9)) * 0.9 + np.exp(-rr / (rs * 3)) * 0.18
    arr = np.asarray(img, np.float32)
    add = np.array(glare, np.float32) * gl[..., None]
    rgb = np.clip(arr[..., :3] + add * (1 - arr[..., :3] / 255), 0, 255)
    a2 = np.clip(arr[..., 3] / 255 + gl, 0, 1)
    img = _rgba(rgb, a2)
    return img.resize((size, size), Image.LANCZOS)


def build_objects(rng, out, save, apply_mask, starfield, mask):
    for name, make in [("black-hole", black_hole), ("pulsar", pulsar)]:
        img = make(rng)
        save(img, out, f"images/terrain/sc/{name}.png", False)
        tile = apply_mask(starfield(rng), mask); tile.alpha_composite(img)
        save(apply_mask(tile, mask), out, f"images/terrain/sc/{name}-tile.png", False)
        if name == "pulsar":            # in a plasma storm it burns violet
            save(_violet(img), out, "images/terrain/sc/pulsar-storm.png", False)
    for pal in GAS_GIANTS:
        # drawn (so the art after them stays the same) but not saved: the
        # gas giants became brown dwarfs, drawn below with their own seed
        gas_giant(rng, pal)
    # Brown dwarfs, with their own seed. All eight looks are still drawn,
    # so the two kept stay the same, but only those two are saved.
    wrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 7)
    dwarfs = []
    for i, pal in enumerate(BROWN_DWARFS):
        img = brown_dwarf(wrng, pal)
        dwarfs.append(img)
        if i == 0:
            tile = apply_mask(starfield(wrng), mask)
    for n, i in enumerate(BROWN_DWARFS_KEPT):
        save(dwarfs[i], out, f"images/terrain/sc/brown-dwarf{'' if n == 0 else n + 1}.png", False)
    tile.alpha_composite(dwarfs[BROWN_DWARFS_KEPT[0]].resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
    save(apply_mask(tile, mask), out, "images/terrain/sc/brown-dwarf-tile.png", False)
    # More black holes, added later with their own seed so the art above stays the same.
    brng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 1)
    for i, style in enumerate(BLACK_HOLES[1:]):
        save(black_hole(brng, **style), out, f"images/terrain/sc/black-hole{i + 2}.png", False)
    # The veils were drawn over the gas giants: still drawn, so the art
    # after them stays the same, but now over the brown dwarfs, and saved
    # only for the clouds ships can fly through.
    vrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 3)
    for name, (code, dark, light) in GIANT_VEILS.items():
        for i, img in enumerate(dwarfs):
            veil = veiled(vrng, img, dark, light)
            if code in ("Yn", "Yd") or code.startswith("Yq") or i not in BROWN_DWARFS_KEPT:
                continue        # no brown dwarfs in nebulae, dust or impassable clouds
            n = BROWN_DWARFS_KEPT.index(i)
            save(veil, out, f"images/terrain/sc/brown-dwarf-{name}{'' if n == 0 else n + 1}.png", False)
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
    # The red supergiant in its debris disk, with its own seed.
    srng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 5)
    img = red_supergiant(srng)
    save(img, out, "images/terrain/sc/red-supergiant.png", False)
    tile = apply_mask(starfield(srng), mask)
    tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
    save(apply_mask(tile, mask), out, "images/terrain/sc/red-supergiant-tile.png", False)
    # The blue giant in its debris disk, the red one's partner, with its own seed.
    brng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 9)
    img = red_supergiant(brng, **DISK_STARS["blue"])
    save(img, out, "images/terrain/sc/blue-giant.png", False)
    tile = apply_mask(starfield(brng), mask)
    tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
    save(apply_mask(tile, mask), out, "images/terrain/sc/blue-giant-tile.png", False)
    # The single-hex stars behind debris disks, with their own seed.
    krng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 10)
    for name, style in SMALL_DISK_STARS:
        img = red_supergiant(krng, canvas=128, **style)
        save(img, out, f"images/terrain/sc/disk-star-{name}.png", False)
        tile = apply_mask(starfield(krng), mask)
        tile.alpha_composite(img.crop((28, 28, 100, 100)))
        save(apply_mask(tile, mask), out, f"images/terrain/sc/disk-star-{name}-tile.png", False)
    # a yellow one too (^Yxd5), with its own seed so the others stay the same
    yrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 12)
    img = red_supergiant(yrng, canvas=128, **SMALL_DISK_STAR_YELLOW)
    save(img, out, "images/terrain/sc/disk-star-yellow.png", False)
    tile = apply_mask(starfield(yrng), mask)
    tile.alpha_composite(img.crop((28, 28, 100, 100)))
    save(apply_mask(tile, mask), out, "images/terrain/sc/disk-star-yellow-tile.png", False)
    # green and purple ones (^Yxd6, ^Yxd7), with their own seed
    grng2 = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 13)
    for name, style in SMALL_DISK_STARS_MORE:
        img = red_supergiant(grng2, canvas=128, **style)
        save(img, out, f"images/terrain/sc/disk-star-{name}.png", False)
        tile = apply_mask(starfield(grng2), mask)
        tile.alpha_composite(img.crop((28, 28, 100, 100)))
        save(apply_mask(tile, mask), out, f"images/terrain/sc/disk-star-{name}-tile.png", False)
    mrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 4)
    for i, style in enumerate(BIG_BLACK_HOLES_MORE):
        save(big_black_hole(mrng, **style), out,
             f"images/terrain/sc/black-hole-big{len(BIG_BLACK_HOLES) + i + 1}.png", False)
    # The dark stars, with their own seed.
    drng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 6)
    for i, (kind, style) in enumerate(DARK_STARS):
        img = (dark_star_eclipse if kind == "eclipse" else dark_star_halo)(drng, **style)
        save(img, out, f"images/terrain/sc/dark-star{'' if i == 0 else i + 1}.png", False)
        if i == 0:
            tile = apply_mask(starfield(drng), mask)
            tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
            save(apply_mask(tile, mask), out, "images/terrain/sc/dark-star-tile.png", False)
    # The supergiants, with their own seed.
    urng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 8)
    for i, style in enumerate(SUPERGIANTS):
        img = supergiant(urng, style)
        save(img, out, f"images/terrain/sc/supergiant{i + 1}.png", False)
        if i == 0:
            tile = apply_mask(starfield(urng), mask)
            tile.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
            save(apply_mask(tile, mask), out, "images/terrain/sc/supergiant-tile.png", False)
    # The three-hex objects, with their own seed.
    build_small_objects(np.random.default_rng(rng.bit_generator.seed_seq.entropy + 11), out, save, apply_mask, starfield, mask)
    # The protostars, added later with their own seed.
    build_protostars(np.random.default_rng(rng.bit_generator.seed_seq.entropy + 14), out, save, apply_mask, starfield, mask)


# ---------------------------------------------------------------- three-hex objects
# Smaller kin of the four-hex centrepieces, each filling a triangle of
# three hexes round the corner they share, and one-hex brown dwarfs. Drawn
# as the big ones, with their own seed so they are not the same globes,
# then shrunk to fit. Also the rocky supergiants in their other colours.
SMALL = 0.82            # 3 hexes against 4: a supergiant 120 px across
ONE = 0.5               # a brown dwarf in one hex, 67 px across


def _shrunk(img, k):
    w = round(img.width * k)
    return img.resize((w, w), Image.LANCZOS)


def build_small_objects(rng, out, save, apply_mask, starfield, mask):
    def put(img, name, k=SMALL):
        save(_shrunk(img, k), out, f"images/terrain/sc/{name}.png", False)

    def tile(img, name, t=None):
        t = t or apply_mask(starfield(rng), mask)
        t.alpha_composite(img.resize((HEX - 12, HEX - 12), Image.LANCZOS), (6, 6))
        save(apply_mask(t, mask), out, f"images/terrain/sc/{name}-tile.png", False)

    # the magenta look is still drawn (with its tile's stars), so the art
    # after it stays the same, but only the dark one is kept
    brown_dwarf(rng, BROWN_DWARFS[5])
    stars = apply_mask(starfield(rng), mask)
    img = brown_dwarf(rng, BROWN_DWARFS[7])
    put(img, "brown-dwarf-one", ONE)
    tile(img, "brown-dwarf-one", stars)
    for i, style in enumerate(SUPERGIANTS):
        img = supergiant(rng, style)
        put(img, f"supergiant-small{i + 1}")
        if i == 0:
            tile(img, "supergiant-small")
    for i, style in enumerate(BIG_BLACK_HOLES + BIG_BLACK_HOLES_MORE):
        img = big_black_hole(rng, **style)
        put(img, f"black-hole-small{'' if i == 0 else i + 1}")
        if i == 0:
            tile(img, "black-hole-small")
    for i, style in enumerate(GLOBULAR_CLUSTERS):
        img = globular_cluster(rng, **style)
        put(img, f"globular-cluster-small{'' if i == 0 else i + 1}")
        if i == 0:
            tile(img, "globular-cluster-small")
    rocky = [("red", DISK_STARS["red"])] + ROCKY_SUPERGIANTS + [("blue", DISK_STARS["blue"])]
    for i, (name, style) in enumerate(rocky):
        img = red_supergiant(rng, **style)
        put(img, f"rocky-supergiant-small{'' if i == 0 else i + 1}")
        if i == 0:
            tile(img, "rocky-supergiant-small")
        elif name in dict(ROCKY_SUPERGIANTS):     # the big ones in the new colours
            save(img, out, f"images/terrain/sc/rocky-supergiant{i + 1}.png", False)
            t = apply_mask(starfield(rng), mask)
            t.alpha_composite(img.resize((HEX - 4, HEX - 4), Image.LANCZOS), (2, 2))
            save(apply_mask(t, mask), out, f"images/terrain/sc/rocky-supergiant{i + 1}-tile.png", False)
    for i, (kind, style) in enumerate(DARK_STARS):
        img = (dark_star_eclipse if kind == "eclipse" else dark_star_halo)(rng, **style)
        put(img, f"dark-star-small{'' if i == 0 else i + 1}")
        if i == 0:
            tile(img, "dark-star-small")
    grng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 13)
    put(red_supergiant(grng, **ROCKY_SUPERGIANT_GREEN), "rocky-supergiant-small6")


def build_protostars(rng, out, save, apply_mask, starfield, mask):
    for i, style in enumerate(PROTOSTARS):
        img = protostar(rng, **style)
        n = "" if i == 0 else i + 1
        save(img, out, f"images/terrain/sc/protostar{n}.png", False)
        save(_shrunk(img, SMALL), out, f"images/terrain/sc/protostar-small{n}.png", False)
        if i == 0:
            tile = apply_mask(starfield(rng), mask)
            tile.alpha_composite(img.resize((HEX + 8, HEX + 8), Image.LANCZOS).crop((4, 4, HEX + 4, HEX + 4)))
            save(apply_mask(tile, mask), out, "images/terrain/sc/protostar-tile.png", False)
