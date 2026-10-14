"""Green and red nebulae: original art.

Two looks, both soft gas with no bright filaments:

* veils (the default): broad, gauzy streamers that bend and flow through
  a thin glow, so plenty of stars show through.
* soft: billowing glowing gas, brighter where it is dense, fading out at
  its fringe (the alternate look; make_art.py --nebula-style soft).

Each nebula is one big cloud that wraps round every few hexes, painted
here as a w x h field; make_art.py cuts it into hexes (see
build_gas_nebula there).
"""
import numpy as np

# fringe, body and core colour of each nebula
PALETTES = {
    "nebula": ((15, 75, 75), (40, 160, 95), (130, 225, 135)),     # teal fringe, green body, pale green core
    "rednebula": ((90, 10, 35), (195, 35, 40), (250, 115, 70)),    # crimson fringe, red body, orange-red core
}
STYLES = ("veils", "soft")


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _ramp(colours, t):
    """Colour ramp: fringe at 0, body at 0.5, core at 1."""
    c0, c1, c2 = (np.array(c, np.float32) for c in colours)
    t = t[..., None]
    lo = c0 + (c1 - c0) * np.clip(t * 2, 0, 1)
    return np.where(t < 0.5, lo, c1 + (c2 - c1) * np.clip(t * 2 - 1, 0, 1))


def _sample(f, x, y):
    """f at (x, y), bilinear and wrapping round the field's edges."""
    h, w = f.shape
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    x0, y0 = x0 % w, y0 % h
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    return (f[y0, x0] * (1 - fx) * (1 - fy) + f[y0, x1] * fx * (1 - fy)
            + f[y1, x0] * (1 - fx) * fy + f[y1, x1] * fx * fy)


def _blur(f, r):
    """Gaussian blur that wraps round the field's edges."""
    k = np.arange(-int(3 * r) - 1, int(3 * r) + 2)
    g = np.exp(-k * k / (2 * r * r))
    g /= g.sum()
    out = sum(wt * np.roll(f, s, 1) for s, wt in zip(k, g))
    return sum(wt * np.roll(out, s, 0) for s, wt in zip(k, g))


def nebula_field(rng, w, h, noise, name, style, density):
    """The whole cloud of nebula `name` ("nebula" or "rednebula") as an
    h x w x 4 uint8 RGBA array. `noise(rng, w, h, octaves, cell, cell_x)`
    is make_art's wrapping fractal noise; density scales the opacity."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    def warp(f, amount, cell=90):
        """f pushed around by a slow, wobbly flow, so it billows."""
        qx, qy = noise(rng, w, h, 4, cell) - 0.5, noise(rng, w, h, 4, cell) - 0.5
        return _sample(f, xx + amount * qx, yy + amount * qy)

    if style == "veils":
        # streamers: noise stretched along x, bent by a big warp, and the
        # middle of each band softly lit
        flow = warp(noise(rng, w, h, 5, 26, 70), 140, 110)
        streak = _blur(1 - np.abs(2 * flow - 1), 2.2) ** 2.5
        body = _smoothstep(0.2, 0.85, warp(noise(rng, w, h, 4, 80), 60))
        tone = noise(rng, w, h, 3, 120)
        glow = np.clip(0.5 * body + 0.6 * streak * (0.4 + 0.6 * body), 0, 1)
        rgb = _ramp(PALETTES[name], np.clip(0.1 + 0.85 * glow + 0.2 * (tone - 0.5), 0, 1))
        rgb = rgb * (0.55 + 0.6 * glow)[..., None]
        alpha = np.clip(0.12 + 0.75 * glow, 0, 0.93)
    elif style == "soft":
        body = _smoothstep(0.18, 0.85, warp(noise(rng, w, h, 5, 70), 70))
        tone = noise(rng, w, h, 3, 120)
        rgb = _ramp(PALETTES[name], np.clip(0.15 + 0.75 * body + 0.25 * (tone - 0.5), 0, 1))
        rgb = rgb * (0.55 + 0.6 * body)[..., None]
        alpha = np.clip(0.18 + 0.72 * body ** 1.2, 0, 0.95)
    else:
        raise ValueError(f"unknown nebula style {style!r}")
    return np.dstack([rgb, alpha * density * 255]).clip(0, 255).astype(np.uint8)
