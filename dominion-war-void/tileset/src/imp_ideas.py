# Prototype sheet: impassable-terrain ideas from Star Trek canon, each drawn on the same test layout
# (lone hexes, a pair, a zigzag line, a vertical line, a 7-hex cluster) to judge how it repeats.
import sys, math, random
sys.path.insert(0, '.')
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import badlands as B
import asteroids as A

W, H = 18, 8
def pix(x, y): return x * 54, y * 72 + (36 if x % 2 == 0 else 0)
def ctr(q): px, py = pix(*q); return px + 36, py + 36
def neighbours(x, y):
    if x % 2 == 0: return [(x, y - 1), (x + 1, y), (x + 1, y + 1), (x, y + 1), (x - 1, y + 1), (x - 1, y)]
    return [(x, y - 1), (x + 1, y - 1), (x + 1, y), (x, y + 1), (x - 1, y), (x - 1, y - 1)]
HEXES = [(1, 2), (16, 6), (17, 6)]                                   # lone, pair
HEXES += [(x, 1) for x in range(4, 11)]                             # zigzag line
HEXES += [(14, y) for y in range(1, 5)]                             # vertical line
HEXES += [(6, 5)] + neighbours(6, 5)                                # cluster
HEXES += [(11, 6)]                                                  # lone
HS = set(HEXES)
SIZE = (W * 54 + 18, H * 72 + 36)
HEXV = [(18, 0), (54, 0), (72, 36), (54, 72), (18, 72), (0, 36)]

def starfield(seed=1):
    r = np.random.default_rng(seed); a = np.zeros((SIZE[1], SIZE[0], 3)); a[...] = (5, 6, 12)
    for _ in range(900):
        x, y = r.integers(0, SIZE[0]), r.integers(0, SIZE[1]); b = r.uniform(60, 230)
        a[y, x] = (b, b, min(255, b * 1.1))
    return Image.fromarray(a.astype(np.uint8)).convert('RGBA')

def mask(sigma=6):
    return np.clip(B.membership(SIZE, [(*pix(*q), 1.0) for q in HEXES], sigma), 0, 1)

def glow_lines(segs, core, glow, wcore=1.6, wglow=5, blur=4, ss=2):
    big = Image.new('RGBA', (SIZE[0] * ss, SIZE[1] * ss)); d = ImageDraw.Draw(big)
    for (a, b) in segs: d.line([(a[0] * ss, a[1] * ss), (b[0] * ss, b[1] * ss)], fill=glow, width=int(wglow * ss))
    big = big.filter(ImageFilter.GaussianBlur(blur * ss))
    d = ImageDraw.Draw(big)
    for (a, b) in segs: d.line([(a[0] * ss, a[1] * ss), (b[0] * ss, b[1] * ss)], fill=core, width=max(1, int(wcore * ss)))
    return big.resize(SIZE, Image.LANCZOS)

# 1. Tholian web (TOS "The Tholian Web", ENT "In a Mirror, Darkly"): a glowing orange-red mesh spun across the hexes
def tholian():
    r = random.Random(3); M = B.membership(SIZE, [(*pix(*q), 1.0) for q in HEXES], 3)
    pts = []; s = 15
    for j in range(-1, SIZE[1] // s + 2):
        for i in range(-1, SIZE[0] // s + 2):
            x = i * s + (s / 2 if j % 2 else 0) + r.uniform(-3, 3); y = j * s * 0.866 + r.uniform(-3, 3)
            if 0 <= int(y) < SIZE[1] and 0 <= int(x) < SIZE[0] and M[int(y), int(x)] > 0.45: pts.append((x, y))
    segs = []
    P = np.array(pts)
    for k, p in enumerate(pts):
        d = np.hypot(P[:, 0] - p[0], P[:, 1] - p[1])
        for m in np.argsort(d)[1:5]:
            if m > k and d[m] < s * 1.35 and r.random() < 0.88: segs.append((p, tuple(P[m])))
    # long anchor strands, as the Tholian ships spin it
    for q in HEXES:
        c = ctr(q)
        for v in HEXV[::2]:
            if r.random() < 0.5: segs.append((c, (pix(*q)[0] + v[0], pix(*q)[1] + v[1])))
    sheen = Image.fromarray(np.dstack([np.full(M.shape, 255), np.full(M.shape, 90), np.full(M.shape, 30), np.clip(M, 0, 1) * 38]).astype(np.uint8), 'RGBA')
    out = Image.new('RGBA', SIZE); out.alpha_composite(sheen)
    out.alpha_composite(glow_lines(segs, (255, 210, 140, 235), (255, 80, 20, 150), 1.1, 4, 3))
    return out

# 2. Dominion self-replicating minefield (DS9 "Call to Arms"): cloaked mines, half-seen, with blinking lights
def minefield():
    r = random.Random(5); out = Image.new('RGBA', SIZE); M = B.membership(SIZE, [(*pix(*q), 1.0) for q in HEXES], 2)
    shimmer = B.fbm(SIZE[1], SIZE[0], 8, 2, np.random.default_rng(2))
    sh = np.clip(M, 0, 1) * np.clip(0.5 + 0.35 * shimmer, 0, 1) * 34
    out.alpha_composite(Image.fromarray(np.dstack([np.full(M.shape, 120), np.full(M.shape, 140), np.full(M.shape, 255), sh]).astype(np.uint8), 'RGBA'))
    pts = []
    for _ in range(6000):
        x, y = r.uniform(0, SIZE[0]), r.uniform(0, SIZE[1])
        if M[int(y), int(x)] < 0.6: continue
        if all(math.hypot(x - a, y - b) > 17 for a, b in pts): pts.append((x, y))
    mine = {}
    for k, (x, y) in enumerate(pts):
        cloaked = r.random() < 0.45
        key = (cloaked, k % 4)
        if key not in mine:
            S = 40; ss = 4; im = Image.new('RGBA', (S * ss, S * ss)); d = ImageDraw.Draw(im); c = S * ss / 2
            for a in range(6):   # spines
                ang = a * math.pi / 3 + 0.3
                d.line([(c, c), (c + math.cos(ang) * 9 * ss, c + math.sin(ang) * 9 * ss)], fill=(110, 105, 100, 255), width=ss)
            d.ellipse([c - 5 * ss, c - 5 * ss, c + 5 * ss, c + 5 * ss], fill=(70, 66, 62, 255))
            d.ellipse([c - 3 * ss, c - 4.5 * ss, c + 4.5 * ss, c + 2 * ss], fill=(125, 118, 110, 255))   # lit from the right
            col = [(255, 60, 40), (60, 255, 120), (255, 60, 40), (255, 190, 60)][k % 4]
            g = Image.new('RGBA', im.size); ImageDraw.Draw(g).ellipse([c - 4 * ss, c - 4 * ss, c + 4 * ss, c + 4 * ss], fill=col + (200,))
            g = g.filter(ImageFilter.GaussianBlur(3 * ss)); im = Image.alpha_composite(im, g)
            ImageDraw.Draw(im).ellipse([c - 1.3 * ss, c - 1.3 * ss, c + 1.3 * ss, c + 1.3 * ss], fill=(255, 255, 230, 255))
            im = im.resize((S, S), Image.LANCZOS)
            if cloaked:
                a_ = np.asarray(im).astype(float); a_[..., 3] *= 0.35; a_[..., 2] = np.clip(a_[..., 2] * 1.3 + 30, 0, 255); im = Image.fromarray(a_.astype(np.uint8), 'RGBA')
            mine[key] = im
        im = mine[key]; out.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    return out

# 3. Starship graveyard (TNG "The Best of Both Worlds" / DS9 "Emissary": Wolf 359): wrecked hulls, burning and venting
def hull_piece(r, kind, ss=3):
    S = 64 * ss; im = Image.new('RGBA', (S, S)); d = ImageDraw.Draw(im); c = S / 2
    rot = r.uniform(0, 360)
    if kind == 'saucer':   # a broken slice of a saucer section, with window rows
        R = r.uniform(22, 28) * ss; a0 = r.uniform(0, 360); a1 = a0 + r.uniform(70, 130)
        d.pieslice([c - R, c - R, c + R, c + R], a0, a1, fill=(150, 152, 158, 255))
        d.pieslice([c - R * 0.4, c - R * 0.4, c + R * 0.4, c + R * 0.4], a0, a1, fill=(0, 0, 0, 0))
        for rr in (0.62, 0.8):
            for t in np.linspace(a0 + 5, a1 - 5, 14):
                x, y = c + math.cos(math.radians(t)) * R * rr, c + math.sin(math.radians(t)) * R * rr
                d.rectangle([x - ss, y - ss * 0.6, x + ss, y + ss * 0.6], fill=(255, 225, 150, 255) if r.random() < 0.5 else (40, 40, 45, 255))
        for _ in range(4):   # jagged break
            t = math.radians(r.choice([a0, a1])); rr = r.uniform(0.45, 0.95) * R
            x, y = c + math.cos(t) * rr, c + math.sin(t) * rr
            d.ellipse([x - 4 * ss, y - 4 * ss, x + 4 * ss, y + 4 * ss], fill=(0, 0, 0, 0))
    elif kind == 'nacelle':
        L, Wd = r.uniform(24, 32) * ss, r.uniform(5, 6.5) * ss
        d.rounded_rectangle([c - L, c - Wd, c + L * 0.6, c + Wd], radius=Wd, fill=(140, 142, 150, 255))
        d.rounded_rectangle([c - L * 0.8, c - Wd * 0.45, c + L * 0.4, c + Wd * 0.45], radius=Wd * 0.4, fill=(60, 80, 130, 255))   # dead warp coils
        d.ellipse([c - L - 2 * ss, c - Wd, c - L + 2 * Wd, c + Wd], fill=(150, 50, 40, 255))   # bussard collector, dark
        d.polygon([(c + L * 0.6, c - Wd), (c + L * 0.75, c - Wd * 0.3), (c + L * 0.62, c + Wd * 0.2), (c + L * 0.8, c + Wd)], fill=(0, 0, 0, 0))
    else:   # hull plate / spar
        pts = [(c + math.cos(t) * r.uniform(8, 20) * ss, c + math.sin(t) * r.uniform(5, 12) * ss) for t in np.linspace(0, 2 * math.pi, 9)[:-1]]
        d.polygon(pts, fill=(125, 125, 132, 255))
        d.line([pts[0], pts[4]], fill=(80, 80, 88, 255), width=ss)
    im = im.rotate(rot, resample=Image.BICUBIC)
    a = np.asarray(im).astype(float)
    # shading: brighter on the right (key light), scorch marks
    xs = np.linspace(-1, 1, S)[None, :]; ys = np.linspace(-1, 1, S)[:, None]
    lit = 0.55 + 0.5 * np.clip(xs * 0.9 - ys * 0.4, -1, 1)
    sc = B.fbm(S, S, 10 * ss, 3, np.random.default_rng(r.randrange(999)))
    burn = np.clip((sc - 0.6) * 1.2, 0, 0.85)
    a[..., :3] = a[..., :3] * lit[..., None] * (1 - burn[..., None])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    return im.resize((64, 64), Image.LANCZOS)

def graveyard():
    r = random.Random(9); out = Image.new('RGBA', SIZE)
    M = B.membership(SIZE, [(*pix(*q), 1.0) for q in HEXES], 14)
    haze = B.fbm(SIZE[1], SIZE[0], 20, 3, np.random.default_rng(4))
    a = np.clip(M, 0, 1) * np.clip(0.45 + 0.3 * haze, 0, 1) * 70
    out.alpha_composite(Image.fromarray(np.dstack([np.full(M.shape, 120), np.full(M.shape, 100), np.full(M.shape, 90), a]).astype(np.uint8), 'RGBA'))
    items = []
    for q in HEXES:
        cx, cy = ctr(q)
        for kind in [r.choice(['saucer', 'saucer', 'nacelle']), r.choice(['nacelle', 'plate']), 'plate']:
            im = hull_piece(r, kind)
            items.append((cy, im, cx + r.uniform(-14, 14), cy + r.uniform(-12, 12), r.random() < 0.6))
        for _ in range(6):
            R = r.uniform(1, 2.5)
            items.append((cy, A.CACHE.get_rock(r.randrange(10 ** 6), R, 'grey', False, None), cx + r.uniform(-30, 30), cy + r.uniform(-28, 28), False))
    items.sort(key=lambda t: t[0])
    fire = Image.new('RGBA', SIZE); fd = ImageDraw.Draw(fire)
    for (_, im, x, y, burning) in items:
        out.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
        if burning:
            fx, fy = x + r.uniform(-10, 10), y + r.uniform(-8, 8); fd.ellipse([fx - 5, fy - 5, fx + 5, fy + 5], fill=(255, 120, 40, 200))
    out.alpha_composite(fire.filter(ImageFilter.GaussianBlur(4)))
    return out

# 4. Galactic barrier (TOS "Where No Man Has Gone Before", "By Any Other Name"): a curtain of pink-violet energy
def barrier():
    g = B.render_gas(SIZE, [pix(*q) for q in HEXES], ((40, 5, 45), (205, 70, 190), (255, 220, 250)), 41, 1.35)
    a = np.asarray(g).astype(float)
    rng = np.random.default_rng(8); vx = np.ones((SIZE[1], SIZE[0])) * 0.15; vy = np.ones((SIZE[1], SIZE[0]))
    n = np.hypot(vx, vy); streak = B.smear(B.fbm(SIZE[1], SIZE[0], 3, 2, rng), vx / n, vy / n, 22, 1.5)
    M = mask(10)
    st = np.clip((streak - 0.9) / 1.4, 0, 1) * np.clip((M - 0.35) / 0.4, 0, 1)
    a[..., :3] = a[..., :3] * (1 - st[..., None]) + np.array([255, 235, 255]) * st[..., None]
    a[..., 3] = np.clip(a[..., 3] * 1.15 + st * 200, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

# 5. Subspace rift (TNG "Force of Nature", VOY "Twisted"/"Parallax"): glowing tears in space, branching through the hexes
def rift():
    r = random.Random(12); segs = []
    def crack(a, b, depth):
        if depth == 0 or math.hypot(b[0] - a[0], b[1] - a[1]) < 6: segs.append((a, b)); return
        mx, my = (a[0] + b[0]) / 2 + r.uniform(-6, 6), (a[1] + b[1]) / 2 + r.uniform(-6, 6)
        crack(a, (mx, my), depth - 1); crack((mx, my), b, depth - 1)
        if r.random() < 0.25:
            ang = math.atan2(b[1] - a[1], b[0] - a[0]) + r.choice([-1, 1]) * r.uniform(0.6, 1.2); L = r.uniform(8, 16)
            crack((mx, my), (mx + math.cos(ang) * L, my + math.sin(ang) * L), 2)
    for q in HEXES:
        c = ctr(q); lone = not any(n in HS for n in neighbours(*q))
        for n in neighbours(*q):
            if n in HS and n > q: crack(c, ctr(n), 4)
        if lone:
            ang = r.uniform(0, math.pi); crack((c[0] - math.cos(ang) * 30, c[1] - math.sin(ang) * 26), (c[0] + math.cos(ang) * 30, c[1] + math.sin(ang) * 26), 5)
    M = mask(14); out = Image.new('RGBA', SIZE)
    out.alpha_composite(Image.fromarray(np.dstack([np.full(M.shape, 20), np.full(M.shape, 120), np.full(M.shape, 170), np.clip(M, 0, 1) * 45]).astype(np.uint8), 'RGBA'))
    out.alpha_composite(glow_lines(segs, (230, 255, 255, 255), (40, 200, 255, 170), 1.8, 7, 5))
    return out

# 6. Star Control's own Debris Disk (^Yw), one per hex, for comparison
def sc_disk():
    out = Image.new('RGBA', SIZE)
    SCD = '/mnt/user-data/uploads/Star_Control_TC/images/terrain/sc/'
    for i, q in enumerate(sorted(HEXES)):
        im = Image.open(SCD + 'asteroid-wall' + ('' if i % 8 == 0 else str(i % 8 + 1)) + '.png').convert('RGBA')
        cx, cy = ctr(q); out.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
    return out


SF = None   # the starfield, for ideas that bend or swallow it

# 7. Gravitational eddy (Star Control's Gravity Eddy; Trek: gravimetric shear, VOY "The Haunting of Deck Twelve"):
#    whirlpools of tidal shear that bend the starlight behind them into rings and arcs
def eddy():
    r = random.Random(21); H_, W_ = SIZE[1], SIZE[0]
    M = mask(12); yy, xx = np.mgrid[0:H_, 0:W_].astype(float)
    centres = []
    for q in HEXES:
        c = ctr(q)
        if all(math.hypot(c[0] - a, c[1] - b) > 80 for a, b, _ in centres): centres.append((c[0], c[1], r.choice([-1, 1])))
    for q in HEXES:   # every hex needs some eddy nearby
        c = ctr(q)
        if all(math.hypot(c[0] - a, c[1] - b) > 50 for a, b, _ in centres): centres.append((c[0], c[1], r.choice([-1, 1])))
    dx = np.zeros_like(xx); dy = np.zeros_like(xx); vx = np.zeros_like(xx) + 1e-6; vy = np.zeros_like(xx)
    for (cx, cy, sgn) in centres:
        ddx, ddy = xx - cx, yy - cy; d = np.hypot(ddx, ddy) + 1e-3
        fall = np.exp(-(d / 34) ** 2)
        ang = sgn * 2.2 * fall                     # swirl the background: lensing
        dx += ddx * (np.cos(ang) - 1) - ddy * np.sin(ang); dy += ddx * np.sin(ang) + ddy * (np.cos(ang) - 1)
        vx += sgn * -ddy / d * np.exp(-(d / 45) ** 2); vy += sgn * ddx / d * np.exp(-(d / 45) ** 2)
    bg = np.asarray(SF.convert('RGB')).astype(float)
    from scipy.ndimage import map_coordinates
    warped = np.dstack([map_coordinates(bg[..., k], [yy + dy * M, xx + dx * M], order=1, mode='reflect') for k in range(3)])
    n = np.hypot(vx, vy) + 1e-6
    streak = B.smear(B.fbm(H_, W_, 4, 2, np.random.default_rng(3)), vx / n, vy / n, 26, 1.5)
    st = np.clip((streak - 0.4) / 1.6, 0, 1) * M
    col = warped * (1 - 0.25 * M[..., None]) + np.array([150, 185, 255]) * (st * 0.8)[..., None]
    a = np.clip(M * 1.2, 0, 1) * 255
    return Image.fromarray(np.dstack([np.clip(col, 0, 255), a]).astype(np.uint8), 'RGBA')

# 8. Radiation zone (Star Control's Radiation Zone; Trek: theta / metaphasic / ionising radiation): a sickly glare with sparks
def radiation():
    g = B.render_gas(SIZE, [pix(*q) for q in HEXES], ((40, 35, 5), (190, 185, 50), (255, 255, 190)), 51, 1.15)
    a = np.asarray(g).astype(float); r = np.random.default_rng(6); M = mask(8)
    sp = (r.random(M.shape) < 0.012) * (M > 0.5)
    from scipy.ndimage import gaussian_filter
    spk = np.clip(gaussian_filter(sp.astype(float), 0.8) * 6, 0, 1)
    a[..., :3] = a[..., :3] * (1 - spk[..., None]) + 255 * spk[..., None]; a[..., 3] = np.clip(a[..., 3] + spk * 255, 0, 255)
    out = Image.fromarray(a.astype(np.uint8), 'RGBA')
    # trefoil-free hazard read: a faint pulsing ring at each cluster's middle
    return out

# 9. The Void (VOY "Night"): a starless region; nothing to navigate by, and theta-radiation dumped in it
def void():
    M = mask(16); H_, W_ = SIZE[1], SIZE[0]
    inner = np.clip((M - 0.35) / 0.35, 0, 1)
    rim = np.exp(-((M - 0.33) / 0.12) ** 2)
    ripple = 0.55 + 0.45 * np.sin(B.fbm(H_, W_, 12, 2, np.random.default_rng(9)) * 5)
    col = np.zeros((H_, W_, 3)) + np.array([80, 95, 135]) * (rim * ripple)[..., None]
    a = np.clip(inner + rim * 0.75, 0, 1) * 255
    return Image.fromarray(np.dstack([np.clip(col, 0, 255), a]).astype(np.uint8), 'RGBA')

# 10. Dangerous nebula: the Briar Patch (Star Trek: Insurrection), metaphasic radiation, too thick to fly through
def briar():
    g = B.render_gas(SIZE, [pix(*q) for q in HEXES], ((45, 15, 10), (220, 120, 70), (255, 230, 190)), 61, 1.45)
    g2 = B.render_gas(SIZE, [pix(*q) for q in HEXES], ((30, 5, 25), (200, 60, 120), (255, 190, 220)), 63, 0.8)
    out = Image.alpha_composite(g2, g)
    a = np.asarray(out).astype(float); r = np.random.default_rng(7); M = mask(8)
    from scipy.ndimage import gaussian_filter
    sp = (r.random(M.shape) < 0.006) * (M > 0.55); spk = np.clip(gaussian_filter(sp.astype(float), 1.0) * 9, 0, 1)
    a[..., :3] = a[..., :3] * (1 - spk[..., None]) + np.array([255, 245, 220]) * spk[..., None]
    a[..., 3] = np.clip(a[..., 3] * 1.1 + spk * 255, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

IDEAS = [('1  Tholian web', 'TOS "The Tholian Web"', tholian), ('2  Dominion minefield', 'DS9 "Call to Arms" (some mines cloaked)', minefield),
         ('3  Wolf 359 ship graveyard', 'TNG "The Best of Both Worlds", DS9 "Emissary"', graveyard), ('4  Galactic barrier', 'TOS "Where No Man Has Gone Before"', barrier),
         ('5  Subspace rift', 'TNG "Force of Nature", VOY', rift), ('6  Star Control Debris Disk (for comparison)', 'asteroid-wall 1-8, one per hex', sc_disk),
         ('7  Gravitational eddy', 'Star Control Gravity Eddy; Trek gravimetric shear', eddy), ('8  Radiation zone', 'Star Control Radiation Zone; Trek theta radiation', radiation),
         ('9  The Void', 'VOY "Night": a region with no stars', void), ('10  Briar Patch (dangerous nebula)', 'Star Trek: Insurrection, metaphasic radiation', briar)]

if __name__ == '__main__':
    F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    sf = starfield(); SF = sf
    panels = []
    for t, sub, fn in IDEAS:
        p = sf.copy(); p.alpha_composite(fn()); panels.append((t, sub, p.convert('RGB'))); p.convert('RGB').save('idea_%s.png' % t.split()[0])
        print('done', t, flush=True)
    w, h = SIZE; out = Image.new('RGB', (w * 2 + 30, (h + 70) * 5 + 10), (20, 20, 24)); d = ImageDraw.Draw(out)
    for i, (t, sub, p) in enumerate(panels):
        x = 10 + (i % 2) * (w + 10); y = 10 + (i // 2) * (h + 70)
        d.text((x, y), t, fill=(240, 240, 240), font=F); d.text((x, y + 28), sub, fill=(165, 165, 165), font=f)
        out.paste(p, (x, y + 58))
    out.save('/mnt/project-files/tileset/impassable-ideas.png'); print(out.size)
