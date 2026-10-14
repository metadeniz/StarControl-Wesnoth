"""Asteroid fields, dense asteroids and asteroid walls: original art.

Each rock is a small height field (a lumpy, sometimes elongated potato with
bumps and craters), lit from the upper left like the planets, with a faint
cool rim light on its dark side so it still reads against deep space. Rocks
are drawn 4x oversized and scaled down.

Rocks reach right up to the hex edges (and a few pixels past them) so a
field of several hexes reads as one field rather than a cluster per hex.
Where a field meets open space, loose gravel spills a little way into the
neighbouring hex (the *-spill images, drawn by terrain-graphics.cfg), so the
field frays out instead of stopping on a hex line."""
import math
import os
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HEX = 72
S = 4                                   # supersampling
LIGHT = np.array([-0.55, -0.55, 0.63])  # x right, y down, z toward the viewer
LIGHT /= np.linalg.norm(LIGHT)
RIM_COL = np.array([95, 115, 170], np.float32)

# Rock colours: (albedo RGB, how often)
ROCK_KINDS = [
    ((128, 122, 114), 0.34),    # grey stone
    ((126, 104, 84), 0.26),     # brown silicate
    ((92, 88, 86), 0.18),       # dark carbonaceous
    ((142, 100, 74), 0.12),     # rusty iron
    ((150, 150, 146), 0.07),    # pale
    ((150, 168, 182), 0.03),    # icy
]
WALL_KINDS = ROCK_KINDS[:4]     # walls: no big pale or icy boulders

HEX_VERTS = np.array([(18, 0), (54, 0), (72, 36), (54, 72), (18, 72), (0, 36)], np.float32)
EDGES = {"n": (0, 1), "ne": (1, 2), "se": (2, 3), "s": (3, 4), "sw": (4, 5), "nw": (5, 0)}


def edge_distance(x, y, edge):
    (x1, y1), (x2, y2) = HEX_VERTS[EDGES[edge][0]], HEX_VERTS[EDGES[edge][1]]
    dx, dy = x2 - x1, y2 - y1
    t = min(max(((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy), 0), 1)
    return math.hypot(x - x1 - t * dx, y - y1 - t * dy)


def inside_hex(x, y, margin=0.0):
    """True if (x, y) lies inside the hex and at least `margin` px from its
    border (a negative margin allows that much overhang)."""
    if not (0 <= x <= HEX and 0 <= y <= HEX) and margin >= 0:
        return False
    # the hex is convex: inside means on the inner side of every edge
    for i in range(6):
        (x1, y1), (x2, y2) = HEX_VERTS[i], HEX_VERTS[(i + 1) % 6]
        nx, ny = y2 - y1, -(x2 - x1)          # outward normal (clockwise verts)
        d = ((x - x1) * nx + (y - y1) * ny) / math.hypot(nx, ny)
        if d > -margin:
            return False
    return True


def value_noise(rng, size, octaves=4, base=3):
    total = np.zeros((size, size), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        grid = rng.random((cells, cells)).astype(np.float32)
        layer = Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        total += amp * np.asarray(layer, np.float32) / 255.0
        norm += amp
        amp *= 0.55
    total /= norm
    total -= total.min()
    return total / max(total.max(), 1e-6)


def rock(rng, radius, darken=1.0, kinds=ROCK_KINDS):
    """One lit rock about 2*radius px across, as RGBA, centred on its canvas."""
    R = radius * S
    n = int(2 * R + 6 * S)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) - (n - 1) / 2
    rot = rng.uniform(0, 2 * math.pi)
    squash = rng.uniform(0.6, 1.0) if radius > 2 else 1.0
    c, s = math.cos(rot), math.sin(rot)
    u, v = xx * c + yy * s, (-xx * s + yy * c) / squash
    theta = np.arctan2(v, u)
    # lumpy outline: a few low harmonics with random phases
    shape = np.ones_like(theta)
    for k, amp in ((2, 0.10), (3, 0.09), (4, 0.06), (5, 0.04), (7, 0.025)):
        shape += amp * rng.uniform(0.3, 1.0) * np.cos(k * theta + rng.uniform(0, 2 * math.pi))
    rho = np.sqrt(u * u + v * v) / (R * shape)
    inside = rho < 1
    h = np.sqrt(np.clip(1 - rho ** 2, 0, 1)) ** 0.85 * R * rng.uniform(0.55, 0.85)
    bumps = value_noise(rng, n, 4, 3) - 0.5
    h += bumps * R * 0.35 * (rho < 1.05)
    # craters on the bigger rocks: bowls with a slight raised rim
    crater_mask = np.zeros_like(h)
    if radius >= 5:
        for _ in range(int(rng.integers(0, 2 + radius // 6))):
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.7) * R
            cx, cy = d * math.cos(a), d * math.sin(a)
            cr = R * rng.uniform(0.1, 0.22)
            dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / cr
            bowl = np.clip(1 - dd ** 2, 0, 1)
            rim = np.exp(-((dd - 1.05) / 0.25) ** 2)
            h += cr * (-0.35 * bowl + 0.12 * rim)
            crater_mask = np.maximum(crater_mask, bowl)
    gy, gx = np.gradient(h)
    nrm = np.dstack([-gx, -gy, np.ones_like(h)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    lam = np.clip(nrm @ LIGHT, 0, 1)
    shade = 0.07 + 0.93 * lam ** 1.1
    spec = np.clip(nrm @ (LIGHT + np.array([0, 0, 1])) / np.linalg.norm(LIGHT + np.array([0, 0, 1])), 0, 1) ** 24
    rim = np.clip(1 - nrm[..., 2], 0, 1) ** 2.5 * np.clip(-(nrm[..., 0] * LIGHT[0] + nrm[..., 1] * LIGHT[1]) * 2, 0, 1)

    cols, p = zip(*kinds)
    kind = cols[int(rng.choice(len(cols), p=np.array(p) / sum(p)))]
    albedo = np.array(kind, np.float32) * rng.uniform(0.88, 1.08) * darken
    mottle = 0.82 + 0.36 * value_noise(rng, n, 5, 4)
    speck = 1 - 0.25 * (rng.random((n, n)) < 0.02)
    tone = (mottle * speck * (1 - 0.1 * crater_mask))[..., None]
    rgb = albedo * tone * shade[..., None] + 45 * spec[..., None] + RIM_COL * 0.35 * rim[..., None]

    # anti-aliased silhouette (the 4x supersample does the rest)
    edge = np.clip((1 - rho) * R / 1.5, 0, 1)
    alpha = edge * 255
    big = Image.fromarray(np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8), "RGBA")
    k = n // S
    return big.convert("RGBa").resize((k, k), Image.LANCZOS).convert("RGBA")


def shadowed(img, strength=0.45):
    """The rock plus a soft dark halo, offset away from the light, so rocks
    stay readable over bright gas and plasma and stand apart when they
    overlap."""
    pad = 3
    a = img.split()[3]
    canvas = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    halo = Image.new("L", canvas.size, 0)
    halo.paste(a, (pad + 1, pad + 1))
    halo = halo.filter(ImageFilter.GaussianBlur(1.3)).point(lambda v: int(v * strength))
    canvas.putalpha(halo)
    canvas.alpha_composite(img, (pad, pad))
    return canvas


def scatter(rng, sizes, min_gap, overhang, placed=None, tries=60):
    """Place rocks of the given radii inside the hex, no closer than
    `min_gap` (a fraction of the radii) to each other."""
    placed = [] if placed is None else placed
    for r in sizes:
        for _ in range(tries):
            x, y = rng.uniform(-overhang, HEX + overhang), rng.uniform(-overhang, HEX + overhang)
            if not inside_hex(x, y, r - overhang):
                continue
            if all((x - px) ** 2 + (y - py) ** 2 > (min_gap * (r + pr)) ** 2 for px, py, pr in placed):
                placed.append((x, y, r))
                break
    return placed


def rubble(rng, placed, pad, size):
    """Dark packed gravel filling the gaps between a wall's rocks. It
    follows the rocks' outline (not the hex), so a wall's edge stays
    ragged."""
    m = Image.new("L", (size * S, size * S), 0)
    d = ImageDraw.Draw(m)
    for x, y, r in placed:
        rr = r * 0.85 * S
        cx, cy = (x + pad) * S, (y + pad) * S
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
    # close the gaps between neighbouring rocks, but add no rim round them
    m = m.filter(ImageFilter.GaussianBlur(3 * S)).point(lambda v: 0 if v < 120 else min(255, (v - 120) * 6))
    m = m.resize((size, size), Image.LANCZOS)
    mask = np.asarray(m, np.float32) / 255
    tex = value_noise(rng, size, 5, 6)
    grain = rng.random((size, size)).astype(np.float32)
    base = 24 + 22 * tex + 8 * (grain > 0.85) - 6 * (grain < 0.15)
    rgb = np.dstack([base * 1.0, base * 0.95, base * 0.9])
    return Image.fromarray(np.dstack([rgb, mask * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def compose(rng, placed, pad, darken=1.0, kinds=ROCK_KINDS, shadow=0.45, fill=False):
    """Draw rocks back to front (top of the screen first) on a canvas that
    is the hex plus `pad` px on every side."""
    size = HEX + 2 * pad
    canvas = rubble(rng, placed, pad, size) if fill else Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for x, y, r in sorted(placed, key=lambda p: p[1] + p[2]):
        img = rock(rng, r, darken, kinds)
        if r >= 2.5:
            img = shadowed(img, shadow)
        canvas.alpha_composite(img, (int(round(x + pad - img.width / 2)), int(round(y + pad - img.height / 2))))
    return canvas


def gravel(rng, count):
    sizes = rng.choice([0.9, 1.2, 1.6, 2.0], size=count, p=[0.3, 0.3, 0.25, 0.15])
    return [float(s) for s in sizes]


def field_rocks(rng):
    """Asteroid field (hills): a few medium rocks, small ones and gravel."""
    big = sorted(rng.choice([9.0, 10.0, 11.5, 13.0], size=int(rng.integers(2, 5)), p=[0.35, 0.3, 0.2, 0.15]), reverse=True)
    small = rng.choice([4.0, 5.0, 6.0], size=int(rng.integers(4, 7)))
    placed = scatter(rng, [float(r) for r in big], 1.25, 2)
    placed = scatter(rng, [float(r) for r in small], 1.3, 3, placed)
    placed = scatter(rng, gravel(rng, int(rng.integers(5, 10))), 1.6, 1, placed)
    return placed


def dense_rocks(rng):
    """Dense asteroids (mountains): big boulders packed close, filled in
    with smaller rocks."""
    big = sorted(rng.choice([10.0, 11.0, 12.5, 14.0], size=int(rng.integers(5, 7))), reverse=True)
    mid = rng.choice([6.0, 7.0, 8.0], size=int(rng.integers(4, 7)))
    small = rng.choice([3.0, 3.5, 4.0], size=int(rng.integers(4, 7)))
    placed = scatter(rng, [float(r) for r in big], 0.75, 5)
    placed = scatter(rng, [float(r) for r in mid], 0.9, 4, placed)
    placed = scatter(rng, [float(r) for r in small], 1.0, 3, placed)
    placed = scatter(rng, gravel(rng, int(rng.integers(5, 9))), 1.2, 1, placed)
    return placed


def wall_rocks(rng):
    """Asteroid wall (impassable): huge rocks packed edge to edge and a bit
    past it, so neighbouring wall hexes join into one barrier."""
    big = sorted(rng.choice([15.0, 17.0, 19.0, 21.0], size=int(rng.integers(7, 10))), reverse=True)
    mid = rng.choice([7.0, 8.5, 10.0], size=10)
    small = rng.choice([3.5, 4.5, 5.5], size=14)
    placed = scatter(rng, [float(r) for r in big], 0.62, 7)
    placed = scatter(rng, [float(r) for r in mid], 0.72, 7, placed)
    placed = scatter(rng, [float(r) for r in small], 0.75, 5, placed)
    placed = scatter(rng, [float(r) for r in rng.choice([1.8, 2.3, 2.8], size=40)], 0.9, 4, placed)
    return placed


def swirl_rocks(rng, spin, arms, twist):
    """Debris disk: rocks of every size swept round the hex's centre along
    a few spiral arms, spaced apart rather than packed, thinning out
    towards the hex edge."""
    c = HEX / 2
    phase = rng.uniform(0, 2 * math.pi)
    placed = []

    def put(r, tries=80, rmin=11, rmax=34, gap=1.25):
        for _ in range(tries):
            d = rmin + (rmax - rmin) * rng.uniform(0, 1) ** 0.8
            j = int(rng.integers(arms))
            a = phase + 2 * math.pi * j / arms + spin * twist * math.log(d / rmin) + rng.normal(0, 0.28)
            x, y = c + d * math.cos(a), c + d * math.sin(a)
            if not inside_hex(x, y, r + 0.5):   # whole rocks: the overlay is cut at the hex edge
                continue
            if all((x - px) ** 2 + (y - py) ** 2 > (gap * (r + pr) + 1.5) ** 2 for px, py, pr in placed):
                placed.append((x, y, r))
                return

    for r in sorted(rng.choice([6.0, 7.0, 8.0, 9.0], size=int(rng.integers(4, 6))), reverse=True):
        put(float(r), rmin=14, rmax=31, gap=1.15)
    for r in rng.choice([3.0, 3.5, 4.0, 4.5, 5.0], size=int(rng.integers(13, 17))):
        put(float(r), gap=1.2)
    for r in rng.choice([1.2, 1.6, 2.0, 2.5], size=int(rng.integers(50, 65)), p=[0.3, 0.3, 0.25, 0.15]):
        put(float(r), rmin=9, rmax=37, gap=1.4)
    return placed


def dust_haze(rng, d, W):
    """A cloud of brown dust behind a debris disk, in the dust clouds'
    colours, thinning out just past the hex so neighbouring disks' clouds
    run together."""
    n1, n2, f2 = (np.asarray(Image.fromarray((value_noise(rng, W // S, o, b) * 255).astype(np.uint8))
                             .resize((W, W), Image.BICUBIC), np.float32) / 255
                  for o, b in ((5, 3), (4, 4), (4, 6)))
    streak = (1 - np.abs(2 * n1 - 1)) ** 3
    fine = (1 - np.abs(2 * f2 - 1)) ** 16
    col_a, col_b, col_hi = (np.array(c, np.float32) for c in ((150, 115, 75), (115, 90, 65), (200, 165, 115)))
    mix = (0.5 + 0.5 * (n2 - 0.5))[..., None]
    rgb = col_a * (1 - mix) + col_b * mix
    rgb = rgb * (0.75 + 0.5 * (n1 - 0.5) + 0.35 * streak)[..., None]
    rgb = rgb * (1 - 0.5 * fine[..., None]) + col_hi * 0.5 * fine[..., None]
    edge = np.clip((50 - d - 10 * (n2 - 0.5)) / 24, 0, 1)
    alpha = np.clip(0.3 + 0.12 * (n1 - 0.5) + 0.3 * streak + 0.2 * fine, 0, 0.85) * 0.45 * edge * edge * (3 - 2 * edge)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def debris_disk(rng, pad, spin, haze_rng=None):
    """One debris disk hex: an empty dark middle, faint dust streaming
    round it in a spiral, and loose rocks of every size swept
    along the same spiral, each trailing a little dust."""
    size = HEX + 2 * pad
    c = size / 2
    arms, twist = int(rng.integers(2, 4)), rng.uniform(1.6, 2.2)
    placed = swirl_rocks(rng, spin, arms, twist)
    W = size * S
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32) / S - c
    d = np.hypot(xx, yy); th = np.arctan2(yy, xx)
    # dust: soft spiral lanes, brighter near the centre, gone by the hex edge
    lanes = 0.5 + 0.5 * np.cos(arms * (th - spin * twist * np.log(np.maximum(d, 1) / 11)) - arms * 0.0)
    grain = np.asarray(Image.fromarray((value_noise(rng, size, 5, 5) * 255).astype(np.uint8))
                       .resize((W, W), Image.BICUBIC), np.float32) / 255
    inner = np.clip((d - 4) / 9, 0, 1)
    fade = np.clip((29 - d) / 9, 0, 1) * inner * inner * (3 - 2 * inner)   # gone before the hex edge and in the middle
    dust = lanes ** 3 * (0.45 + 0.55 * grain) * fade * 0.42
    dust_rgb = np.dstack([np.full_like(d, 120), np.full_like(d, 104), np.full_like(d, 92)])
    canvas = Image.fromarray(np.dstack([dust_rgb, dust * 255]).clip(0, 255).astype(np.uint8), "RGBA")
    if haze_rng is not None:
        canvas = dust_haze(haze_rng, d, W)
        canvas.alpha_composite(Image.fromarray(np.dstack([dust_rgb, dust * 255]).clip(0, 255).astype(np.uint8), "RGBA"))
    # each rock trails a short streak of dust behind it along its orbit
    trails = Image.new("L", (W, W), 0)
    dt = ImageDraw.Draw(trails)
    for x, y, r in placed:
        px, py = x + pad - c, y + pad - c
        rad, a0 = math.hypot(px, py), math.atan2(py, px)
        span = min(0.9, (r * 2.5 + 4) / max(rad, 1))
        pts = [((c + rad * math.cos(a0 - spin * span * k / 8)) * S, (c + rad * math.sin(a0 - spin * span * k / 8)) * S)
               for k in range(9)]
        for k in range(8):
            dt.line(pts[k:k + 2], fill=int(150 * (1 - k / 8)), width=max(1, int(r * 1.3 * S * (1 - k / 10))))
    trails = trails.filter(ImageFilter.GaussianBlur(1.5 * S))
    t = np.asarray(trails, np.float32) / 255 * 0.55
    trail_img = Image.fromarray(np.dstack([dust_rgb * 1.1, t * 255]).clip(0, 255).astype(np.uint8), "RGBA")
    canvas = canvas.resize((W, W), Image.LANCZOS) if canvas.size != (W, W) else canvas
    canvas.alpha_composite(trail_img)
    # the empty middle: a round, soft-edged void where the dust thins out
    # into darkness, with no rim, so it fades into the rest of the disk
    void_r = rng.uniform(4.5, 5.5) + 2.5
    rng.uniform(0, 6.3); rng.uniform(0, 6.3)   # keeps the random stream as it was
    void = 0.6 * np.exp(-(d / void_r) ** 2)
    canvas.alpha_composite(Image.fromarray(np.dstack([np.full_like(d, 3), np.full_like(d, 3), np.full_like(d, 8),
                                                      void * 255]).clip(0, 255).astype(np.uint8), "RGBA"))
    canvas = canvas.convert("RGBa").resize((size, size), Image.LANCZOS).convert("RGBA")
    canvas.alpha_composite(compose(rng, placed, pad, darken=0.9, kinds=WALL_KINDS, shadow=0.6))
    return canvas


def spill_rocks(rng, edge, sizes, reach):
    """Loose rocks in a band along one edge of the neighbouring hex, thinning
    out with distance from the edge."""
    placed = []
    for r in sizes:
        for _ in range(80):
            x, y = rng.uniform(0, HEX), rng.uniform(0, HEX)
            if not inside_hex(x, y, r + 0.5):
                continue
            d = edge_distance(x, y, edge)
            if d > reach or rng.random() > (1 - d / reach) ** 1.5:
                continue
            if all((x - px) ** 2 + (y - py) ** 2 > (1.5 * (r + pr) + 1) ** 2 for px, py, pr in placed):
                placed.append((x, y, r))
                break
    return placed


def build(rng, out, save, combos, hex_mask):
    def put(img, name):
        save(img, out, f"images/terrain/sc/{name}.png", False)

    def tile_icon(canvas, pad):
        # editor / help icon: the variant cropped to the hex
        return canvas.crop((pad, pad, pad + HEX, pad + HEX))

    pad = 4
    for v in range(10):
        canvas = compose(rng, field_rocks(rng), pad)
        put(canvas, "asteroids" if v == 0 else f"asteroids{v + 1}")
        if v == 0:
            put(tile_icon(canvas, pad), "asteroids-tile")
    for v in range(10):
        canvas = compose(rng, dense_rocks(rng), pad, shadow=0.55)
        put(canvas, "asteroids-dense" if v == 0 else f"asteroids-dense{v + 1}")
        if v == 0:
            put(tile_icon(canvas, pad), "asteroids-dense-tile")
    wpad = 9
    for v in range(8):
        # the old packed walls: still drawn so the art after them stays
        # the same, but replaced by the debris disks below
        compose(rng, wall_rocks(rng), wpad, darken=0.82, kinds=WALL_KINDS, shadow=0.6, fill=True)
    # Debris disks: loose rocks swirling round an empty middle, with
    # their own seed; half spin one way, half the other.
    # Each sits in a cloud of dust (its own seed too), drawn past the hex
    # so the clouds of neighbouring disks run together.
    drng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 1)
    hrng = np.random.default_rng(rng.bit_generator.seed_seq.entropy + 2)
    dpad = 18
    for v in range(8):
        canvas = debris_disk(drng, dpad, 1 if v % 2 == 0 else -1, hrng)
        put(canvas, "asteroid-wall" if v == 0 else f"asteroid-wall{v + 1}")
        if v == 0:
            put(tile_icon(canvas, dpad), "asteroid-wall-tile")

    # Spill: per edge, a fixed set of loose rocks; each combo image is the
    # union of its edges' sets, so neighbouring rule matches agree.
    field_edge, wall_edge, join_edge = {}, {}, {}
    for e in EDGES:
        n = int(rng.integers(5, 9))
        field_edge[e] = spill_rocks(rng, e, [float(r) for r in rng.choice([1.0, 1.4, 1.8, 2.4, 3.0], size=n,
                                                                           p=[0.25, 0.25, 0.2, 0.18, 0.12])], 15)
        wall_edge[e] = spill_rocks(rng, e, [float(r) for r in rng.choice([1.5, 2.5, 3.5, 5.0], size=6)], 11)
        join_edge[e] = spill_rocks(rng, e, [float(r) for r in rng.choice([3.0, 4.0, 5.0, 6.0], size=6)], 9)
    # (join_edge is still drawn so the spills after it stay the same; the
    # rubble joins between wall hexes went with the packed walls)
    for combo in combos:
        for stem, sets, dk, kinds in (("asteroids-spill", field_edge, 1.0, ROCK_KINDS),
                                      ("asteroid-wall-spill", wall_edge, 0.82, WALL_KINDS)):
            placed = []
            for e in combo.split("-"):
                placed += sets[e]
            canvas = compose(np.random.default_rng(zlib.crc32(f"{stem}-{combo}".encode())), placed, 0, darken=dk,
                             kinds=kinds)
            put(canvas, f"{stem}-{combo}")


def build_preview(path):
    """Contact sheet of every variant on a starfield-coloured background
    (handy when tuning; not used by the game)."""
    sc = "images/terrain/sc"
    names = [f"asteroids{'' if v == 0 else v + 1}" for v in range(10)] + \
            [f"asteroids-dense{'' if v == 0 else v + 1}" for v in range(10)] + \
            [f"asteroid-wall{'' if v == 0 else v + 1}" for v in range(8)]
    sheet = Image.new("RGBA", (10 * 100, 3 * 100), (22, 28, 58, 255))
    for i, n in enumerate(names):
        img = Image.open(os.path.join(sc, n + ".png"))
        row = 0 if i < 10 else (1 if i < 20 else 2)
        col = i if i < 10 else (i - 10 if i < 20 else i - 20)
        sheet.alpha_composite(img, (col * 100 + 50 - img.width // 2, row * 100 + 50 - img.height // 2))
    sheet.save(path)
