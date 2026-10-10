"""Alliance Starbase: an original isometric sprite for the Alliance of Free
Stars. It has the Hierarchy Starbase's form (command saucer, spindle,
habitat, collar, lower disc) in a different design language: smooth,
rounded white hull instead of dark facets, glowing blue light strips
instead of red rings, gold trim, swept docking pylons instead of spiky
antennae, and an engine glow underneath. Original art (not UQM-derived).

Built with the same stacked-ellipse renderer as make_starbase.py.

Usage: make_alliance_starbase.py <add-on dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import make_starbase as m

S, K, CX = m.S, m.K, m.CX
HULL = (205, 210, 222)
HULL_DARK = (128, 136, 152)
GOLD = (232, 188, 82)
GLOW = np.array([90, 190, 255.0])
WARM = np.array([255, 224, 150.0])


def col(rgb, shape):
    return np.broadcast_to(np.array(rgb, float), shape + (3,)).copy()


def strips(base_rgb, glow_at=(), gold_at=(), width=0.45):
    """Plain hull with glowing blue strips and gold trim at given heights."""
    def f(phi, h, rho, top):
        c = col(base_rgb, phi.shape)
        em = None
        if any(abs(h - g) < width for g in glow_at):
            c[:] = GLOW
            em = col(GLOW * 0.9, phi.shape)
        elif any(abs(h - g) < width for g in gold_at):
            c[:] = GOLD
        return c, em
    return f


def pylons(base, h, r0, r1, front, n=3, rot=0.5):
    """Docking pylons: a slim strut out to a capsule-shaped dock pod with a
    blue light at its tip."""
    layer = Image.new("RGBA", (m.W * S, m.H * S))
    d = ImageDraw.Draw(layer)

    def capsule(p, q, w, fill):
        a = m.line3(p, q, base, w, fill, d)
        b = m.line3(q, p, base, w, fill, d)
        for (x, y) in (a, b):
            d.ellipse([x - w * S / 2, y - w * S / 2, x + w * S / 2, y + w * S / 2], fill=fill)
        return a
    for k in range(n):
        ph = rot + k * 2 * math.pi / n
        if (math.sin(ph) > 0) != front:
            continue
        c, s_ = math.cos(ph), math.sin(ph)
        m.line3((r0 * c, r0 * s_, h), ((r1 - 4) * c, (r1 - 4) * s_, h - 1), base, 2.0, HULL_DARK + (255,), d)
        m.line3((r0 * c, r0 * s_, h), ((r1 - 4) * c, (r1 - 4) * s_, h - 1), base, 1.0, HULL + (255,), d)
        p, q = ((r1 - 7) * c, (r1 - 7) * s_, h - 1), (r1 * c, r1 * s_, h - 1)
        capsule(p, q, 4.2, HULL_DARK + (255,))
        capsule(p, q, 3.0, HULL + (255,))
        tip = m.line3(q, q, base, 0.1, (0, 0, 0, 0), d)
        g = tuple(int(v) for v in GLOW) + (255,)
        d.ellipse([tip[0] - 1.3 * S, tip[1] - 1.3 * S, tip[0] + 1.3 * S, tip[1] + 1.3 * S], fill=g)
    m.blit(layer)


def glow_layer(base, h, r, alpha):
    layer = Image.new("RGBA", (m.W * S, m.H * S))
    d = ImageDraw.Draw(layer)
    x, y = CX, m.sy(h, base)
    d.ellipse([x - r * S, y - r * S * 0.75, x + r * S, y + r * S * 0.75], fill=(110, 190, 255, alpha))
    m.blit(layer.filter(ImageFilter.GaussianBlur(S * 1.5)))


def build():
    m.img[:] = 0
    m.RIM_COL = np.array([70, 140, 255])       # cool blue rim light
    base = 88

    # --- engine glow under the stern
    glow_layer(base, -39, 7, 200)
    glow_layer(base, -39, 3.5, 255)

    # --- lower hull: a smooth teardrop stern under a white disc with a blue rim
    m.solid(lambda h: 7 * math.sqrt(max(0, 1 - ((h + 33) / 6) ** 2)), base, -38.5, -33,
            strips(HULL_DARK), cap=False)
    def lower_disc(h):
        t = (h + 33) / 4.0
        return 20 * math.sqrt(max(0, 1 - (2 * t - 1) ** 2)) ** 0.5 if 0 <= t <= 1 else 0
    m.solid(lower_disc, base, -33, -29, strips(HULL, glow_at=[-31], width=0.5), cap=False)

    # --- lower spindle with a glowing band, then a smooth flare to the collar
    m.solid(lambda h: 3.6, base, -29, -16, strips(HULL, glow_at=[-24]), cap=False)
    m.solid(lambda h: 7 + 16 * ((h + 16) / 14) ** 2, base, -16, -2, strips(HULL, gold_at=[-6]), cap=False)

    pylons(base, 0, 22, 40, front=False)

    # --- collar: a smooth white ring with a gold lip and a blue light strip
    def collar(h):
        t = (h + 2) / 6
        return 24 + 2.5 * math.sin(math.pi * t)
    m.solid(collar, base, -2, 4, strips(HULL, glow_at=[1], gold_at=[-1.6, 3.6], width=0.5), cap=False)

    # --- habitat: a smooth white dome with long horizontal window bands
    def dome(h):
        t = (h - 4) / 14
        return 23 * math.sqrt(max(0, 1 - t * t))
    def dome_col(phi, h, rho, top):
        c = col(HULL, phi.shape)
        em = np.zeros(phi.shape + (3,))
        t = (h - 4) / 14
        for lo, hi, light in ((0.10, 0.19, WARM), (0.28, 0.36, WARM), (0.45, 0.52, WARM), (0.62, 0.67, GLOW)):
            if lo < t < hi:
                win = np.mod(phi * 14 / math.pi, 1) < 0.62    # long windows, thin mullions
                c[win] = light
                em[win] = light * 0.8
        return c, em
    m.solid(dome, base, 4, 18, dome_col, cap=False, step=0.08)

    pylons(base, 0, 22, 40, front=True)

    # --- upper spindle with blue bands
    m.solid(lambda h: 4, base, 16, 40, strips(HULL, glow_at=[26, 34]), cap=False)

    # --- command saucer: a smooth white lens with a glowing blue rim
    def under(h):
        t = (h - 40) / 6
        return 12 + 42 * math.sin(t * math.pi / 2)
    m.solid(under, base, 40, 46, strips(HULL_DARK), cap=False)
    m.solid(lambda h: 54, base, 46, 47.6, strips(HULL, glow_at=[46.8], width=0.45), cap=False)
    def top_surf(h):
        t = (h - 47.6) / 6
        return 54 * math.cos(t * math.pi / 2) ** 0.6
    def top_col(phi, h, rho, top):
        c = col(HULL, phi.shape)
        em = np.zeros(phi.shape + (3,))
        rho = rho * top_surf(h) / 54          # radius across the whole saucer
        # sector panels in two tones, a gold ring, blue light lines, and a row
        # of lit windows near the rim
        sector = np.mod(phi * 4 / math.pi, 2) < 1
        c[sector & (rho > 0.38) & (rho < 0.86)] = (182, 188, 202)
        c[np.abs(rho - 0.38) < 0.016] = GOLD
        c[np.abs(rho - 0.86) < 0.02] = HULL_DARK
        ray = (np.mod(phi * 4 / math.pi, 1) < 0.04) & (rho > 0.38) & (rho < 0.86)
        c[ray] = GLOW
        em[ray] = GLOW * 0.8
        win = (np.abs(rho - 0.92) < 0.025) & (np.mod(phi * 24 / math.pi, 1) < 0.5)
        c[win] = WARM
        em[win] = WARM * 0.8
        return c, em
    m.solid(top_surf, base, 47.6, 53.6, top_col, cap=False, step=0.05)
    # bridge dome: blue glass
    m.solid(lambda h: 9 * math.sqrt(max(0, 1 - ((h - 53.6) / 4.5) ** 2)), base, 53.6, 58.1,
            strips((120, 190, 255)), cap=False, step=0.06)

    # --- running lights: a ring of white and green lights round the saucer rim
    layer = Image.new("RGBA", (m.W * S, m.H * S))
    d = ImageDraw.Draw(layer)
    for k in range(16):
        ph = k * math.pi / 8
        if math.sin(ph) < -0.3:
            continue
        x, y = CX + 54.5 * math.cos(ph) * S, m.sy(46.8, base) + 54.5 * math.sin(ph) * K * S
        c = (120, 255, 150, 255) if k % 4 == 0 else (255, 255, 255, 255)
        d.ellipse([x - 0.9 * S, y - 0.9 * S, x + 0.9 * S, y + 0.9 * S], fill=c)
    m.blit(layer)

    im = Image.fromarray(m.img.astype("uint8"), "RGBA").resize((m.W, m.H), Image.LANCZOS)
    a_ = im.getchannel("A")
    edge = a_.filter(ImageFilter.MaxFilter(3))
    outline = Image.new("RGBA", im.size, (8, 8, 14, 0))
    outline.putalpha(edge.point(lambda v: int(v * 0.7)))
    outline.alpha_composite(im)
    return outline.resize((m.OUT, m.OUT), Image.LANCZOS)


def build_alliance_starbase(out):
    im = build()
    for suffix in ("", "-n", "-ne", "-se", "-s", "-sw", "-nw"):
        im.save(os.path.join(out, f"images/units/sc/alliance-starbase{suffix}.png"))


if __name__ == "__main__":
    build_alliance_starbase(sys.argv[1])
