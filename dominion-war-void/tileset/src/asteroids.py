# Asteroid art, after Star Control's fields: lumpy cratered rocks in mixed colours,
# a wide range of sizes down to grit, fields that fray into neighbouring hexes,
# and dense fields / walls sitting in a faint dust haze.
# Lighting: design/lighting-preferences.md default (14soft): strong key from the right
# (upper right on screen), weak overhead, rim from back left, no sky fill.
import math, random
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter

def nrm(v): v = np.array(v, float); return v / np.linalg.norm(v)
KEY = nrm([1.0, -0.45, 0.42])      # screen x right, y down, z toward viewer
RIM = nrm([-0.75, -0.55, -0.25])
TOP = nrm([0.0, -0.2, 1.0])

ALBEDO = {  # base colour, colour variation
    'grey':  ((112, 109, 105), 0.22),
    'brown': ((128, 98, 74), 0.25),
    'dark':  ((72, 68, 66), 0.20),
    'rust':  ((140, 92, 64), 0.25),
    'pale':  ((158, 152, 142), 0.18),
}
MIX = [('grey', 0.48), ('brown', 0.22), ('dark', 0.18), ('rust', 0.06), ('pale', 0.06)]

def _noise(h, w, cells, rng, octaves=4, persist=0.5):
    out = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(octaves):
        c = cells * 2 ** o
        g = rng.standard_normal((c + 3, c + 3))
        ys = np.linspace(1, c + 1, h)[:, None] * np.ones((1, w)); xs = np.linspace(1, c + 1, w)[None, :] * np.ones((h, 1))
        out += amp * map_coordinates(g, [ys, xs], order=3, mode='nearest'); tot += amp; amp *= persist
    return out / tot

def pick_kind(r):
    x = r.random(); acc = 0
    for k, p in MIX:
        acc += p
        if x < acc: return k
    return 'grey'

def asteroid(seed, R, kind='grey', craters=True, tint=None, ss=2):
    """One rock, R = mean radius in game pixels. Returns RGBA, about 2.6R across."""
    rng = np.random.default_rng(seed)
    Rs = R * ss; S = int(Rs * 2.7) + 8
    yy, xx = np.mgrid[0:S, 0:S].astype(float) - S / 2
    a = rng.uniform(0, math.pi); el = rng.uniform(1.0, 1.7)
    u = (xx * math.cos(a) + yy * math.sin(a)) / el; v = -xx * math.sin(a) + yy * math.cos(a)
    th = np.arctan2(v, u); d = np.hypot(u, v)
    # potato silhouette: several harmonics, plus a bite or two
    rad = np.ones_like(d)
    for k in range(2, 8):
        rad += rng.uniform(0.03, 0.13) / (k - 0.8) * np.sin(k * th + rng.uniform(0, 6.3))
    Rt = Rs * rad
    for _ in range(rng.integers(0, 3)):
        ang = rng.uniform(0, 6.3); bx, by = math.cos(ang) * Rs * 0.95, math.sin(ang) * Rs * 0.95; br = Rs * rng.uniform(0.25, 0.45)
        Rt = Rt - np.clip(br - np.hypot(u - bx, v - by), 0, None) * 0.7
    inside = np.clip((Rt - d) / ss + 0.5, 0, 1)
    h = np.sqrt(np.clip(Rt ** 2 - d ** 2, 0, None)) * rng.uniform(0.7, 0.95)
    lump = _noise(S, S, 2, rng, 2) * Rs * 0.22
    bump = _noise(S, S, 4, rng, 4) * Rs * 0.11
    grit = rng.standard_normal((S, S)); grit = gaussian_filter(grit, 0.8 * ss) * Rs * 0.012 * ss
    h = h + (lump + bump + grit) * np.clip(h / (Rs * 0.25), 0, 1)
    pit = gaussian_filter(rng.standard_normal((S, S)), 1.6 * ss); pit /= pit.std() + 1e-9
    h = h - np.clip(pit - 1.1, 0, None) * ss * 0.9 * inside * (R > 2.5)   # pitted, grainy surface
    cmark = np.zeros_like(h)
    if craters and R > 3.5:
        n = int(rng.integers(1, 2 + int(R / 6)))
        for _ in range(n):
            rc = Rs * rng.uniform(0.15, 0.4)
            ang = rng.uniform(0, 6.3); rr = Rs * math.sqrt(rng.uniform(0, 0.75))
            cx, cy = math.cos(ang) * rr, math.sin(ang) * rr
            dc = np.hypot(xx - cx, yy - cy) / rc
            bowl = -np.clip(1 - dc ** 2, 0, 1) ** 1.5 * rc * 0.38
            rim = np.exp(-((dc - 1.0) / 0.3) ** 2) * rc * 0.12
            h = h + (bowl + rim) * inside
            cmark += np.clip(1 - dc, 0, 1) * 0.4 - np.exp(-((dc - 1.0) / 0.25) ** 2) * 0.2
    # normals and light
    gy, gx = np.gradient(gaussian_filter(h, 0.6))
    n = np.dstack([-gx, -gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    dot = lambda L: np.clip((n * L).sum(2), 0, 1)
    # self-shadow: march toward the key light over the height map
    lx, ly = KEY[0], KEY[1]; hl = math.hypot(lx, ly); dx, dy = lx / hl, ly / hl; slope = KEY[2] / hl
    shadow = np.ones_like(h); Y, X = np.mgrid[0:S, 0:S].astype(float)
    for s in range(1, int(Rs * 1.6), max(1, ss)):
        hs = map_coordinates(h, [Y + dy * s, X + dx * s], order=1, mode='constant')
        shadow = np.minimum(shadow, np.clip(1 - (hs - h - s * slope) / (2.0 * ss), 0, 1))
    key = dot(KEY) * shadow
    rimv = dot(RIM) * (1 - n[..., 2]) ** 1.2
    light = 0.03 + 1.05 * key + 0.12 * dot(TOP) + 0.45 * rimv
    base, var = ALBEDO[kind]
    alb = np.array(base, float) * (1 + var * _noise(S, S, 3, rng, 3))[..., None]
    alb = alb * (1 - 0.18 * cmark)[..., None]        # crater floors darker, fresh rims lighter
    hl_ = np.clip((n * nrm(KEY + np.array([0, 0, 1]))).sum(2), 0, 1) ** 18 * 0.12 * shadow
    col = alb * light[..., None] + 255 * hl_[..., None]
    if tint is not None:  # glow of a surrounding nebula on the shadow side
        col = col + np.array(tint, float) * (0.55 * (1 - key) * inside)[..., None]
    out = np.dstack([np.clip(col, 0, 255), inside * 255]).astype(np.uint8)
    im = Image.fromarray(out, 'RGBA')
    if ss > 1: im = im.resize((S // ss, S // ss), Image.LANCZOS)
    return im

# ---------- field layout ----------
# Per hex, like Wesnoth will draw it: every rock of a hex fits an image ~90px square centred on
# the hex (so rocks lean over the hex edge), plus "spill" grit in the neighbouring hexes.
SPEC = {  # (count, Rmin, Rmax, spread) per size class; GAP: minimum gap between rocks, as a factor of R1+R2
    # Passable fields are open like Star Control's: separate rocks with black space between them,
    # so you can see a ship can fly through. Impassable rubble is the opposite: a solid pile in thick dust.
    'hills': [(1, 10.0, 12.5, 16), (2, 6.5, 8.5, 26), (1, 3.0, 4.0, 28), (2, 1.0, 1.6, 30)],
    'mount': [(3, 12.0, 15.0, 20), (3, 7.0, 9.0, 27), (1, 3.0, 4.0, 30), (2, 1.0, 1.8, 32)],
    'wall':  [(1, 20.0, 23.0, 2), (7, 13.0, 17.0, 25), (9, 8.0, 11.0, 31), (10, 3.0, 5.0, 35), (10, 0.9, 1.9, 38)],
}
GAP = {'hills': 1.4, 'mount': 1.0, 'wall': 0.0}

class Cache(dict):
    def get_rock(self, seed, R, kind, craters, tint):
        k = (seed % 64, round(R * 2) / 2, kind, craters, tint)
        if k not in self: self[k] = asteroid(seed % 64 * 7 + int(R * 10), round(R * 2) / 2, kind, craters, tint)
        return self[k]
CACHE = Cache()

def place(hexes, is_rock, neighbours, is_blocked):
    """hexes: list of (x, y, px, py, field, tint). Returns (under, over) lists of (im, ax, ay), sorted
    back to front. 'over' holds rocks inside nebulae (drawn over the cloud)."""
    under, over = [], []; grid = {}
    def add(lst, im, cx, cy, R):
        lst.append((cy, im, int(round(cx - im.width / 2)), int(round(cy - im.height / 2))))
        grid.setdefault((int(cx // 40), int(cy // 40)), []).append((cx, cy, R))
    def free(cx, cy, R, gap):
        if gap <= 0: return True
        gx, gy = int(cx // 40), int(cy // 40)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for (ox, oy, oR) in grid.get((gx + i, gy + j), ()):
                    if math.hypot(cx - ox, cy - oy) < gap * (R + oR) + 1.5: return False
        return True
    for (x, y, px, py, field, tint) in hexes:
        r = random.Random(x * 7919 + y * 104729)
        dest = over if tint is not None else under
        field_kind = pick_kind(r)                     # each hex leans to one rock type, with others mixed in
        for (cnt, rmin, rmax, spread) in SPEC[field]:
            for _ in range(cnt):
                R = r.uniform(rmin, rmax)
                for attempt in range(40):
                    ang = r.uniform(0, 6.283); rr = spread * math.sqrt(r.random())
                    cx = px + 36 + math.cos(ang) * rr; cy = py + 36 + math.sin(ang) * rr * 0.92
                    if free(cx, cy, R, GAP[field]): break
                else:
                    continue                          # no room: leave it out rather than crowd the field
                kind = field_kind if r.random() < 0.55 else pick_kind(r)
                add(dest, CACHE.get_rock(r.randrange(10 ** 6), R, kind, R > 3.5, tint), cx, cy, R)
        if field != 'wall': continue
        # rubble walls spill a few stones into open neighbours
        for dI, (nx, ny) in enumerate(neighbours(x, y)):
            if is_rock(nx, ny) or is_blocked(nx, ny): continue
            ang0 = [-90, -30, 30, 90, 150, 210][dI] * math.pi / 180
            for i in range(3):
                R = r.uniform(0.8, 1.8) if i > 0 else r.uniform(2.0, 3.5)
                dd = r.uniform(36, 48); aa = ang0 + r.uniform(-0.5, 0.5)
                cx = px + 36 + math.cos(aa) * dd; cy = py + 36 + math.sin(aa) * dd
                add(under, CACHE.get_rock(r.randrange(10 ** 6), R, pick_kind(r), False, None), cx, cy, R)
    under.sort(key=lambda t: t[0]); over.sort(key=lambda t: t[0])
    return [t[1:] for t in under], [t[1:] for t in over]

DUSTPAL = ((12, 11, 10), (58, 54, 50), (125, 118, 108))
WALLPAL = ((22, 15, 10), (95, 68, 45), (185, 140, 95))   # impassable rubble: thick brown dust, as Star Control's asteroid wall

# ---------- spiral debris disk (one impassable hex), after Star Control's ^Yw "Debris Disk" ----------
def debris_disk(seed, size=118, ss=2):
    """Rocks and bright dust spiralling round a dim dead-star core. Drawn centred on the hex, reaching past it."""
    import badlands as B
    rng = np.random.default_rng(seed); r = random.Random(seed)
    S = size * ss; c = S / 2
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    tilt = 0.86; rot = r.uniform(0, math.pi)
    X = (xx - c) * math.cos(rot) + (yy - c) * math.sin(rot); Y = (-(xx - c) * math.sin(rot) + (yy - c) * math.cos(rot)) / tilt
    rad = np.hypot(X, Y) / ss; th = np.arctan2(Y, X)
    r0, w = 27.0, 13.0
    ring = np.exp(-((rad - r0) / w) ** 2) * np.clip((rad - 7) / 8, 0, 1) * np.clip((52 - rad) / 10, 0, 1)
    pitch = 2.2; arms = 0.5 + 0.5 * np.cos(2 * (th - pitch * np.log(rad + 1)) + r.uniform(0, 6.3))
    # fine streaks smeared along the orbit
    vx = -np.sin(np.arctan2(yy - c, xx - c) + 0.25); vy = np.cos(np.arctan2(yy - c, xx - c) + 0.25)
    streak = B.smear(B.fbm(S, S, 3 * ss, 2, rng), vx, vy, 16, 1.5 * ss)
    lump = B.fbm(S, S, 14 * ss, 3, rng)
    dens = ring * (0.35 + 0.65 * arms) * np.clip(0.75 + 0.25 * lump + 0.22 * streak, 0, 1.6)
    lit = 0.7 + 0.45 * np.clip(np.cos(np.arctan2(yy - c, xx - c) + 0.45), -1, 1)   # key light from the right
    t = np.clip(dens * 1.05 * lit + 0.12 * np.clip(streak - 0.8, 0, 2), 0, 1)
    rgb = B.ramp(t, [(0.0, (30, 18, 10)), (0.35, (105, 66, 38)), (0.7, (190, 135, 85)), (1.0, (245, 205, 150))])
    a = np.clip(dens * 1.25, 0, 0.92)
    # dim dead-star core: a small dull ember with a soft glow
    d0 = np.hypot(xx - c, yy - c) / ss
    glow = np.exp(-(d0 / 7.0) ** 2) * 0.55; core = np.clip((3.2 - d0) * 1.2, 0, 1)
    rgb = rgb * (1 - glow[..., None]) + np.array([255, 120, 50]) * glow[..., None]
    rgb = rgb * (1 - core[..., None]) + np.array([255, 205, 150]) * core[..., None]
    a = np.clip(a + glow * 0.8 + core, 0, 1)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA').resize((size, size), Image.LANCZOS)
    # rocks strung along the orbit, spiral-offset, back to front
    rocks = []
    for i in range(30):
        big = i < 11
        ang = (i / 11 * 2 * math.pi + r.uniform(-0.25, 0.25)) if big else r.uniform(0, 2 * math.pi); rr = r0 + r.gauss(0, 4.5 if big else 8) + (6 * math.sin(2 * ang) if big else 0)
        if rr < 12: continue
        x0, y0 = rr * math.cos(ang), rr * math.sin(ang) * tilt
        px = size / 2 + x0 * math.cos(rot) - y0 * math.sin(rot); py = size / 2 + x0 * math.sin(rot) + y0 * math.cos(rot)
        R = r.uniform(2.6, 5.5) if big else r.uniform(0.9, 2.0)
        rocks.append((py, px, R))
    rocks.sort()
    for (py, px, R) in rocks:
        rk = CACHE.get_rock(r.randrange(10 ** 6), R, pick_kind(r), R > 3.5, None)
        im.alpha_composite(rk, (int(px - rk.width / 2), int(py - rk.height / 2)))
    return im
