# Badlands prototypes: one map-wide plasma field, masked to the Badlands hexes.
# (In Wesnoth this becomes a periodic texture cut per hex plus edge "banks", as Star Control does.)
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates, gaussian_filter

def fbm(h, w, scale_px, octaves, rng, persist=0.5):
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        s = scale_px / 2 ** o
        gh, gw = int(h / s) + 4, int(w / s) + 4
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        ys = np.arange(h)[:, None] / s + 1; xs = np.arange(w)[None, :] / s + 1
        out += amp * map_coordinates(g, [np.broadcast_to(ys, (h, w)), np.broadcast_to(xs, (h, w))], order=3, mode='nearest'); tot += amp; amp *= persist
    out /= tot
    return (out - out.mean()) / (out.std() + 1e-6)

def flow_field(h, w, rng, drift=(1.0, 0.35), swirl=0.7, vortices=()):
    psi = fbm(h, w, 110, 3, rng)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for (cx, cy, r, s) in vortices:
        psi += s * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    vx = np.gradient(psi, axis=0); vy = -np.gradient(psi, axis=1)
    m = np.sqrt(vx * vx + vy * vy).mean() + 1e-6
    vx = swirl * vx / m + drift[0]; vy = swirl * vy / m + drift[1]
    n = np.maximum(np.sqrt(vx * vx + vy * vy), 1e-6)
    return vx / n, vy / n

def _walk(vx, vy, steps, step):
    h, w = vx.shape; y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    for i in range(steps):
        cx = map_coordinates(vx, [y, x], order=1, mode='nearest'); cy = map_coordinates(vy, [y, x], order=1, mode='nearest')
        x = x + step * cx; y = y + step * cy
        yield i, x, y

def smear(noise, vx, vy, length, step=1.5):
    acc = noise.copy(); ws = np.ones_like(noise)
    for sign in (1, -1):
        for i, x, y in _walk(vx, vy, length, sign * step):
            wgt = 0.5 * (1 + math.cos(math.pi * (i + 1) / (length + 1)))
            acc += wgt * map_coordinates(noise, [y, x], order=1, mode='nearest'); ws += wgt
    out = acc / ws
    return (out - out.mean()) / (out.std() + 1e-6)

HEXV = [(18, 0), (54, 0), (72, 36), (54, 72), (18, 72), (0, 36)]
def membership(size, hexes, sigma=20):
    W, H = size; im = Image.new('F', (W, H), 0.0); d = ImageDraw.Draw(im)
    for (px, py, wgt) in hexes:
        d.polygon([(px + vx, py + vy) for vx, vy in HEXV], fill=float(wgt))
    a = np.asarray(im, np.float32)
    return gaussian_filter(a, sigma)

def ramp(t, stops):
    t = np.clip(t, 0, 1); out = np.zeros(t.shape + (3,), np.float32)
    xs = [s[0] for s in stops]; cs = [np.array(s[1], np.float32) for s in stops]
    for k in range(3): out[..., k] = np.interp(t, xs, [c[k] for c in cs])
    return out

DEEPFIRE = [(0.0, (20, 2, 10)), (0.35, (70, 6, 26)), (0.6, (125, 22, 36)), (0.82, (190, 70, 50)), (1.0, (240, 160, 120))]
FIRE = [(0.0, (40, 4, 10)), (0.35, (130, 20, 30)), (0.6, (215, 70, 40)), (0.82, (255, 150, 70)), (1.0, (255, 235, 180))]

def render(size, hexes, style, seed=3):
    """hexes: (px, py, kind) with kind in shallow/deep/reef/swamp. Returns an RGBA image."""
    W, H = size; rng = np.random.default_rng(seed)
    wmap = {'shallow': 1.0, 'reef': 1.0, 'deep': 1.0, 'swamp': 1.0}
    dmap = {'shallow': 0.0, 'reef': 0.0, 'deep': 1.0, 'swamp': 0.0}
    smap = {'shallow': 0.0, 'reef': 0.0, 'deep': 0.0, 'swamp': 1.0}
    M = np.clip(membership(size, [(x, y, wmap[k]) for x, y, k in hexes]), 0, 1)
    DEEP = np.clip(membership(size, [(x, y, dmap[k]) for x, y, k in hexes], 26), 0, 1)
    SW = np.clip(membership(size, [(x, y, smap[k]) for x, y, k in hexes], 18), 0, 1)
    edge = np.clip((M - 0.15) / 0.55, 0, 1); edge = edge * edge * (3 - 2 * edge)
    # vortices ("funnels") at a few deep / shallow hexes
    r = np.random.default_rng(seed + 1); cand = [(x + 36, y + 36) for x, y, k in hexes if k in ('deep', 'shallow')]
    vort = [(cx, cy, r.uniform(30, 55), r.choice([-1, 1]) * r.uniform(2.5, 4)) for cx, cy in (r.permutation(cand)[:max(1, len(cand) // 40)] if cand else [])]
    vx, vy = flow_field(H, W, rng, swirl=(0.6 if style == 'currents' else 1.1), vortices=vort)
    body = fbm(H, W, 45, 4, rng)
    strands = smear(fbm(H, W, 4, 2, rng), vx, vy, 30)
    patch = fbm(H, W, 30, 3, rng)
    swampmask = 1 - SW * np.clip(0.55 - 0.45 * patch, 0, 1)        # swamp: patchier, with holes
    if style == 'currents':        # Star Control's flowing current, in reds
        bodyd = smear(body, vx, vy, 20, 2.0)
        glint = np.clip((strands - 1.0) / 1.4, 0, 1) ** 1.5
        t = 0.36 + 0.10 * bodyd + 0.05 * strands + 0.30 * glint
        a = np.clip(0.42 + 0.16 * bodyd + 0.07 * strands + 0.48 * DEEP, 0, 0.95)
        D3 = DEEP[..., None]
        rgb = ramp(t, FIRE) * (1 - D3) + ramp(t - 0.22 * glint + 0.04 * strands, DEEPFIRE) * D3
    elif style == 'thin':          # DS9, filaments over black
        f = np.clip((strands - 0.2) / 1.6, 0, 1)
        a = 0.10 + 0.85 * f ** 1.2 + 0.15 * DEEP * np.clip(0.5 + 0.3 * body, 0, 1)
        t = 0.36 + 0.42 * f
        rgb = ramp(t, FIRE)
    elif style == 'thick':         # DS9, billowing clouds with gaps
        bodyw = smear(body, vx, vy, 10, 2.0)
        c = np.clip(0.5 + 0.35 * bodyw + 0.25 * DEEP, 0, 1)
        f = np.clip((strands - 0.4) / 1.6, 0, 1)
        a = np.clip((c - 0.25) * 1.6, 0, 1) * 0.9 + 0.25 * f
        t = 0.3 + 0.45 * c + 0.4 * f - 0.15 * DEEP
        rgb = ramp(t, FIRE)
    else:                          # 'full': a sea of plasma, little or no black
        bodyw = smear(body, vx, vy, 12, 2.0)
        f = np.clip((strands - 0.3) / 1.6, 0, 1)
        a = 0.9 + 0.1 * f
        t = 0.38 + 0.18 * bodyw + 0.35 * f - 0.18 * DEEP
        rgb = ramp(t, FIRE)
    alpha = np.clip(a, 0, 1) * edge * swampmask
    if style != 'full':
        alpha = alpha * (1 - 0.0 * DEEP)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), 'RGBA')

def render_gas(size, hexes, palette, seed=11, dens=1.0, dark=False):
    """A nebula as one map-wide cloud: soft billows with wisps, masked to its hexes (no per-hex puffs)."""
    W, H = size; rng = np.random.default_rng(seed)
    M = np.clip(membership(size, [(x, y, 1.0) for x, y in hexes], 18), 0, 1)
    edge = np.clip((M - 0.12) / 0.6, 0, 1); edge = edge * edge * (3 - 2 * edge)
    vx, vy = flow_field(H, W, rng, drift=(0.3, -0.2), swirl=0.9)
    body = smear(fbm(H, W, 38, 5, rng), vx, vy, 8, 2.0)
    wisp = smear(fbm(H, W, 6, 2, rng), vx, vy, 14, 1.5)
    c = np.clip(0.5 + 0.28 * body + 0.12 * wisp, 0, 1)
    a = np.clip((c - 0.18) * 1.25, 0, 0.85) * edge * dens
    t = np.clip(c * 0.9 + 0.15 * np.clip(wisp - 0.8, 0, 2), 0, 1)
    rgb = ramp(t, [(0.0, palette[0]), (0.55, palette[1]), (1.0, palette[2])])
    if dark:  # dark matter: mostly a light-swallowing veil, with a glowing purple rim
        rim = np.clip(1 - np.abs(edge - 0.45) / 0.3, 0, 1)
        rgb = rgb * (0.35 + 0.9 * rim[..., None])
        a = np.clip(a * 1.15, 0, 0.92)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8), 'RGBA')
