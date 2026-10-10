"""Hierarchy Starbase: an original isometric sprite, inspired by the Ur-Quan
starbase orbiting the slave-shielded Earth in Star Control II.

Solids of revolution are drawn as a stack of thin shaded ellipses (bottom to
top), seen from about 25 degrees above, then downsampled 4x."""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 4                       # supersampling
W = H = 144                 # final canvas
K = 0.42                    # ellipse squash (view elevation)
CV = math.sqrt(1 - K * K)   # vertical foreshortening of heights
CX = W * S / 2
OUT = 100                   # saved size: about 1.5 hexes

LIGHT = np.array([-0.55, 0.45, 0.70])      # x right, y toward viewer, z up
LIGHT /= np.linalg.norm(LIGHT)
RIM = np.array([-0.95, -0.1, 0.1])         # red slave-shield glow from the left
RIM /= np.linalg.norm(RIM)

img = np.zeros((H * S, W * S, 4), float)
yy, xx = np.mgrid[0:H * S, 0:W * S].astype(float)


def squash(h):
    # shorten the two spindles so the station stays chunky on a hex
    return float(np.interp(h, [-60, -29, -16, 16, 40, 80], [-54, -23, -16, 16, 36, 76]))


def sy(h, base):
    return (base - squash(h) * CV) * S


def shade(nx, ny, nz, col, spec=0.35, emissive=None):
    n = np.stack([nx, ny, nz], -1)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    d = np.clip(n @ LIGHT, 0, 1)
    r = np.clip(n @ RIM, 0, 1) ** 2
    half = LIGHT + np.array([0, 0.42, 0.9])
    half /= np.linalg.norm(half)
    s = np.clip(n @ half, 0, 1) ** 24 * spec
    c = np.asarray(col, float)
    out = c * (0.22 + 0.85 * d)[..., None] + s[..., None] * 255
    out += np.array([255, 40, 30]) * (0.30 * r)[..., None]
    if emissive is not None:
        out = np.maximum(out, emissive)
    return np.clip(out, 0, 255)


def solid(profile, base, h0, h1, colfn, sides=0, depth=1.0, step=0.12, cap=True, rot=0.0):
    """profile(h) -> radius; colfn(phi, h) -> (rgb array, emissive or None)."""
    hs = np.arange(h0, h1 + 1e-9, step)
    for i, h in enumerate(hs):
        r = profile(h)
        if r <= 0:
            continue
        dr = (profile(min(h + step, h1)) - profile(max(h - step, h0))) / (2 * step)
        yc = sy(h, base)
        rx, ry = r * S, r * S * K * depth
        x0, x1 = int(CX - rx - 2), int(CX + rx + 2)
        y0, y1 = int(yc - ry - 2), int(yc + ry + 2)
        X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        px, py = (X - CX) / rx, (Y - yc) / ry
        phi = np.arctan2(py, px)
        rho = np.hypot(px, py)
        if sides:
            seg = 2 * math.pi / sides
            a = np.mod(phi - rot, seg) - seg / 2
            lim = math.cos(seg / 2) / np.cos(a)
            fphi = phi - a          # facet centre angle
        else:
            lim = 1.0
            fphi = phi
        m = rho <= lim
        if not m.any():
            continue
        top = cap and i == len(hs) - 1
        if top:
            nx, ny, nz = np.zeros_like(px), np.zeros_like(px) + 0.05, np.ones_like(px)
        else:
            nx, ny = np.cos(fphi), np.sin(fphi) * depth
            nz = np.full_like(px, -dr)
        col, em = colfn(phi, h, rho / np.maximum(lim, 1e-6), top)
        c = shade(nx, ny, nz, col, emissive=em)
        sub = img[y0:y1, x0:x1]
        sub[m, :3] = c[m]
        sub[m, 3] = 255


def flat(rgb):
    def f(phi, h, rho, top):
        return np.broadcast_to(np.array(rgb, float), phi.shape + (3,)), None
    return f


def rings(rgb, red_at, width=0.5):
    def f(phi, h, rho, top):
        c = np.broadcast_to(np.array(rgb, float), phi.shape + (3,)).copy()
        em = None
        for hr in red_at:
            if abs(h - hr) < width:
                c[:] = (230, 30, 35)
                em = np.broadcast_to(np.array([150, 10, 15.0]), c.shape)
        return c, em
    return f


def line3(p, q, base, width, col, draw):
    (x1, y1, z1), (x2, y2, z2) = p, q
    a = (CX + x1 * S, sy(z1, base) + y1 * K * S)
    b = (CX + x2 * S, sy(z2, base) + y2 * K * S)
    draw.line([a, b], fill=col, width=int(width * S))
    return b


def blit(layer):
    a = np.array(layer).astype(float)
    al = a[..., 3:4] / 255
    img[..., :3] = img[..., :3] * (1 - al) + a[..., :3] * al
    img[..., 3] = np.maximum(img[..., 3], a[..., 3])


def ball(draw, at, r, col, hi=(255, 210, 200, 255)):
    x, y = at
    draw.ellipse([x - r * S, y - r * S, x + r * S, y + r * S], fill=col)
    draw.ellipse([x - r * S * 0.55, y - r * S * 0.6, x - r * S * 0.05, y - r * S * 0.1], fill=hi)


def arms(base, h, r0, r1, front, n=6, rot=0.3):
    layer = Image.new("RGBA", (W * S, H * S))
    d = ImageDraw.Draw(layer)
    for k in range(n):
        ph = rot + k * 2 * math.pi / n
        if (math.sin(ph) > 0) != front:
            continue
        c, s_ = math.cos(ph), math.sin(ph)
        p = (r0 * c, r0 * s_, h)
        q = (r1 * c, r1 * s_, h + 1.5)
        line3(p, q, base, 1.6, (90, 95, 105, 255), d)
        end = line3(p, q, base, 0.8, (200, 205, 215, 255), d)
        ball(d, end, 2.0, (225, 25, 30, 255))
    blit(layer)


def build():
    base = 88   # screen y of world h=0 (the mid collar)
    # --- purple sensor spines under the bottom (behind everything)
    layer = Image.new("RGBA", (W * S, H * S))
    d = ImageDraw.Draw(layer)
    for dx, dy, ln in ((-2.5, 1, 11), (0.5, 2.5, 14), (2.8, -0.5, 10), (1, -2, 12)):
        line3((dx, dy, -36), (dx * 1.3, dy * 1.3, -36 - ln), base, 1.3, (130, 70, 220, 255), d)
        end = line3((dx * 1.3, dy * 1.3, -36 - ln), (dx * 1.3, dy * 1.3, -36 - ln), base, 0.1, (0, 0, 0, 0), d)
        ball(d, end, 1.3, (230, 40, 50, 255))
    blit(layer)

    # --- lower hub: small sphere, then the red-rimmed lower disc
    solid(lambda h: 8 * math.sqrt(max(0, 1 - ((h + 33) / 4.5) ** 2)), base, -37.5, -33, flat((120, 115, 125)), cap=False)
    def lower_disc(h):
        t = (h + 33) / 4.0
        return 21 * (1 - 0.35 * t) if 0 <= t <= 1 else 0
    def disc_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([112, 86, 92.0]), phi.shape + (3,)).copy()
        stripes = (np.mod(phi * 12 / math.pi, 2) < 0.25) & (rho > 0.55)
        c[stripes] = (90, 60, 65)
        return c, None
    solid(lower_disc, base, -33, -29, disc_col)

    # --- lower spindle with a red ring, then the taper up to the collar
    solid(lambda h: 3.2, base, -29, -16, rings((110, 112, 120), [-24]), cap=False)
    def taper(h):
        t = (h + 16) / 14
        return 7 + 16 * t ** 1.3
    def taper_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([125, 128, 136.0]), phi.shape + (3,)).copy()
        c[np.mod(phi * 16 / math.pi, 2) < 0.18] = (70, 72, 80)
        return c, None
    solid(taper, base, -16, -2, taper_col, sides=16, cap=False)

    # --- arms behind the collar
    arms(base, 1.5, 26, 39, front=False)

    # --- collar: faceted ring with a glowing cyan band above and below
    def cyan(phi, h, rho, top):
        c = np.broadcast_to(np.array([60, 230, 240.0]), phi.shape + (3,))
        return c, np.broadcast_to(np.array([40, 200, 215.0]), phi.shape + (3,))
    solid(lambda h: 25, base, -2, -1, cyan, cap=False)
    def collar_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([150, 140, 145.0]), phi.shape + (3,)).copy()
        if top:
            c[:] = (175, 110, 115)
        return c, None
    solid(lambda h: 28, base, -1, 3, collar_col, sides=8, rot=math.pi / 8)
    solid(lambda h: 25.5, base, 3, 4, cyan, cap=False)

    # --- the habitat dome: rows of lit windows
    def dome(h):
        t = (h - 4) / 14
        return 25 * math.sqrt(max(0, 1 - t * t))
    def dome_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([150, 152, 162.0]), phi.shape + (3,)).copy()
        em = np.zeros(phi.shape + (3,))
        t = (h - 4) / 14
        row = (t * 5) % 1
        col = np.mod(phi * 11 / math.pi, 1)
        win = (row > 0.18) & (row < 0.82) & (col > 0.15) & (col < 0.85) & (t < 0.8)
        c[win] = (70, 210, 230)
        em[win] = (40, 150, 170)
        return c, em
    solid(dome, base, 4, 18, dome_col, cap=False, step=0.08)

    # --- arms in front
    arms(base, 1.5, 26, 39, front=True)

    # --- upper spindle with red rings, up to the saucer
    solid(lambda h: 3.6, base, 16, 40, rings((105, 108, 116), [24, 33]), cap=False)

    # --- the command saucer: a wide, dark, faceted wing, longer than deep
    DEP = 0.7
    def under(h):
        t = (h - 39) / 7          # 0..1
        return 12 + 46 * t ** 0.8
    def saucer_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([70, 72, 80.0]), phi.shape + (3,)).copy()
        panel = np.mod(phi * 20 / math.pi, 2) < 0.12
        c[panel] = (55, 56, 62)
        return c, None
    solid(under, base, 39, 46, saucer_col, sides=12, depth=DEP, cap=False)
    solid(lambda h: 58, base, 45.5, 48, rings((120, 120, 128), [47], 0.25), sides=12, depth=DEP, cap=False)
    def top_surf(h):
        t = (h - 48) / 11
        return 58 - 46 * t ** 0.75
    def top_col(phi, h, rho, top):
        c = np.broadcast_to(np.array([82, 84, 94.0]), phi.shape + (3,)).copy()
        panel = np.mod(phi * 12 / math.pi, 2) < 0.07
        c[panel] = (60, 62, 70)
        bands = (np.abs(rho - 0.62) < 0.015) | (np.abs(rho - 0.85) < 0.012)
        c[bands] = (64, 66, 74)
        return c, None
    solid(top_surf, base, 48, 59, top_col, sides=12, depth=DEP, cap=False, step=0.05)
    # blue command dome
    def cdome(h):
        t = (h - 59) / 5
        return 9 * math.sqrt(max(0, 1 - t * t))
    solid(cdome, base, 59, 64, flat((50, 60, 200)), cap=False, step=0.06)

    # --- running lights on the saucer: white specks along the rim, red beacons
    rng = np.random.default_rng(7)
    layer = Image.new("RGBA", (W * S, H * S))
    d = ImageDraw.Draw(layer)
    for _ in range(45):
        ph = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.35, 0.95)
        hh = 48 + 11 * ((1 - rr) * 58 / 46) ** (1 / 0.75) if rr < 0.97 else 47.5
        r = rr * 58
        x, y = CX + r * math.cos(ph) * S, sy(hh, base) + r * math.sin(ph) * K * DEP * S
        if math.sin(ph) < -0.2 and rr > 0.9:
            continue
        a = int(rng.uniform(140, 255))
        d.rectangle([x - 0.5 * S, y - 0.25 * S, x + rng.uniform(0.5, 2) * S, y + 0.25 * S], fill=(235, 240, 255, a))
    for ph in (0.4, 1.3, 2.3, 3.0, 4.4, 5.6):
        r = 36
        hh = 48 + 11 * ((1 - r / 58) * 58 / 46) ** (1 / 0.75)
        x, y = CX + r * math.cos(ph) * S, sy(hh, base) + r * math.sin(ph) * K * DEP * S
        ball(d, (x, y), 1.4, (235, 30, 35, 255), hi=(255, 170, 160, 255))
    for ph in (0.0, math.pi):
        x, y = CX + 58 * math.cos(ph) * S, sy(47, base)
        ball(d, (x, y), 1.5, (235, 30, 35, 255), hi=(255, 170, 160, 255))
    blit(layer)

    im = Image.fromarray(img.astype("uint8"), "RGBA").resize((W, H), Image.LANCZOS)
    # a thin dark outline so it reads against bright terrain
    a = im.getchannel("A")
    edge = a.filter(ImageFilter.MaxFilter(3))
    outline = Image.new("RGBA", im.size, (8, 8, 14, 0))
    outline.putalpha(edge.point(lambda v: int(v * 0.7)))
    outline.alpha_composite(im)
    return outline.resize((OUT, OUT), Image.LANCZOS)


def build_hierarchy_starbase(out):
    """Write the sprite into the add-on dir `out`, one copy per facing."""
    import os
    im = build()
    for suffix in ("", "-n", "-ne", "-se", "-s", "-sw", "-nw"):
        im.save(os.path.join(out, f"images/units/sc/hierarchy-starbase{suffix}.png"))


if __name__ == "__main__":
    build_hierarchy_starbase(sys.argv[1])
