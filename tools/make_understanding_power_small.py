#!/usr/bin/env python3
"""Write maps/2p_Understanding_Power_Small.map (and its default-terrain copy).

Understanding Power shrunk to WxH: every feature of the north half is moved
to the nearest hex of the smaller grid (by its position on screen, so the
shapes keep their proportions), lines that were joined stay joined, and
every castle keeps its rings in the same directions. The south half is the
north half turned 180 degrees, as in the full map.

Usage: make_understanding_power_small.py <add-on dir> [W H]
"""

import os
import sys

import make_understanding_power as full

# lowest first: later layers win where two features land on one hex
LAYERS = ["n", "a", "d", "r", "B", "s", "l", "f", "w", "p", "K", "k", "c", "h"]


def pixel(x, y):
    return x * 54.0, y * 72.0 + (36 if x % 2 else 0)


def to_cube(x, y):
    q = x
    r = y - (x - (x & 1)) // 2
    return q, r, -q - r


def from_cube(q, r, s):
    return q, r + (q - (q & 1)) // 2


def cube_round(q, r, s):
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    else:
        rs = -rq - rr
    return rq, rr, rs


def distance(a, b):
    a, b = to_cube(*a), to_cube(*b)
    return max(abs(a[i] - b[i]) for i in range(3))


def line(a, b):
    n = distance(a, b)
    ca, cb = to_cube(*a), to_cube(*b)
    out = []
    for i in range(n + 1):
        t = i / n if n else 0
        out.append(from_cube(*cube_round(*(ca[k] + (cb[k] - ca[k]) * t + 1e-6
                                         for k in range(3)))))
    return out


# The full map's barriers, placed by hand on the small grid (game
# coordinates, north half; the south half follows, with its own stars):
# see BARRIERS in make_understanding_power.py.
BARRIERS = {
    "R": [(3, 5)], "U": [(3, 6)],                       # west cliffs
    "M": [(8, 6), (9, 6), (10, 6), (9, 7)],             # the long ridge
    "w": [(7, 7), (12, 5)],
    "Z": [(7, 8)], "A": [(11, 6)],
    "P": [(16, 1), (19, 2), (19, 4)], "T": [(19, 3)],   # stream banks
    "D": [(23, 6)], "S": [(24, 5)],                     # north-east ridges
    "a": [(20, 5)],
    "E": [(16, 9), (15, 10)], "X": [(16, 10)],          # the centre
    "V": [(15, 9)],
}
CLEARED = [(4, 7), (17, 2), (19, 1), (3, 7), (3, 8), (8, 5), (21, 6), (13, 10)]


def barriers(grid):
    H, W = len(grid), len(grid[0])
    for ch, hexes in list(BARRIERS.items()) + [(".", CLEARED)]:
        for x, y in hexes:
            x, y = x - 1, y - 1
            assert y < H // 2, (ch, x, y)
            grid[y][x] = ch
            grid[H - 1 - y][W - 1 - x] = full.SOUTH.get(ch, ch)
    return grid


def shrink(W, H):
    fx = (W - 1) / (full.W - 1)
    fy = (H - 1) / (full.H - 1)

    def place(x, y):
        px, py = pixel(x, y)
        tx, ty = px * fx, py * fy
        best = min(((X, Y) for X in range(W) for Y in range(H // 2)),
                   key=lambda h: (pixel(*h)[0] - tx) ** 2 + (pixel(*h)[1] - ty) ** 2)
        return best

    grid = [["." for _ in range(W)] for _ in range(H)]
    new = {}

    def put(ch, h):
        x, y = h
        if 0 <= x < W and 0 <= y < H // 2:
            grid[y][x] = ch
            new.setdefault(ch, []).append(h)

    keeps = {}
    for ch in LAYERS:
        hexes = full.FEATURES.get(ch, [])
        if ch in "ch":                      # rings keep their direction
            for h in hexes:
                keep = min(full.FEATURES["K" if ch == "c" else "k"],
                           key=lambda k: distance(k, h))
                dq = [a - b for a, b in zip(to_cube(*h), to_cube(*keep))]
                kq = to_cube(*keeps[keep])
                put(ch, from_cube(*(kq[i] + dq[i] for i in range(3))))
            continue
        for h in hexes:
            p = place(*h)
            if ch in "Kk":
                keeps[h] = p
            put(ch, p)
        if ch in "pKk":
            continue
        for a in hexes:                     # rejoin what was joined
            for b in hexes:
                if a < b and distance(a, b) == 1:
                    for h in line(place(*a), place(*b)):
                        if grid[h[1]][h[0]] not in "pKkch" or ch == grid[h[1]][h[0]]:
                            put(ch, h)
    for y in range(H // 2, H):
        for x in range(W):
            grid[y][x] = grid[H - 1 - y][W - 1 - x]
    return full.shallows(barriers(grid)), keeps[(5, 3)]


if __name__ == "__main__":
    out = sys.argv[1]
    W, H = (int(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else (26, 20)
    grid, start = shrink(W, H)
    full.write(grid, os.path.join(out, "maps/2p_Understanding_Power_Small.map"),
               start=start)
    full.write(grid, os.path.join(out,
               "maps/default-terrain/2p_Understanding_Power_Small.map"),
               full.WESNOTH, ("Kh", "Gg^Vh", "Khw"), start=start)
    for row in grid:
        print("".join(row))
