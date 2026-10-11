#!/usr/bin/env python3
"""Write maps/4p_Manufacturing_Consent_Small.map (and its default-terrain
copy).

Manufacturing Consent shrunk to WxH: every hex of the full map's north-west
quarter is moved to the nearest hex of the smaller grid (by its position on
screen, so the shapes keep their proportions), lines that were joined stay
joined (the centre's ring of walls is redrawn, to keep its gaps), and every castle keeps its rings in the same directions. The rest
is flipped as in the full map, west to east exactly and north to south to
within half a hex; the few hexes the full map does not flip north to south
(a planet beside a mushroom grove, the planets on the middle row, the
recruit hex of the keep in the west ridge) are carried over one by one.

Usage: make_manufacturing_consent_small.py <add-on dir> [W H]
W must be odd, so the west-east flip is exact.
"""

import os
import sys

import make_manufacturing_consent as full

# lowest first: later layers win where two features land on one hex
LAYERS = [".", "n", "m", "a", "s", "r", "B", "f", "w", "p", "K", "c"]
JOINED = "nmasrBw"              # lines and patches that must stay joined


# Changes asked for on the 29x18 map, west half (the east is its flip):
# open space at in-game 13,15 and 13,4 (17,15 and 17,4 in the east)
CLEAR = [(12, 14), (12, 3)]
# planets moved from in-game 1,9 to 11,7 (29,9 to 19,7 in the east) and
# from 12,9 to 11,11 (18,9 to 19,11)
PLANET_MOVES = [((0, 8), (10, 6)), ((11, 8), (10, 10))]


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


def shrink(W, H):
    src, (start, _) = full.build()
    FW, FH = full.W, full.H

    def north(x, y, h=H):
        return y <= h // 2 - 1 or (x % 2 and y == h - 1)

    def flip(x, y, h=H):
        return x, h - 1 - y - x % 2

    # scale so the centre column and the north-south axis (row H/2 - 1 of
    # the odd columns) land on the small map's centre column and axis
    fx = (W // 2) / (FW // 2)
    fy = pixel(1, H // 2 - 1)[1] / pixel(1, FH // 2 - 1)[1]
    targets = [(x, y) for x in range(W // 2 + 1) for y in range(H)
               if north(x, y) and y < H - 1]

    def place(x, y):
        px, py = pixel(x, y)
        tx, ty = px * fx, py * fy
        return min(targets, key=lambda h: (pixel(*h)[0] - tx) ** 2
                   + (pixel(*h)[1] - ty) ** 2)

    quarter = [(x, y) for x in range(FW // 2 + 1) for y in range(FH)
               if north(x, y, FH) and y < FH - 1]
    grid = [["." for _ in range(W)] for _ in range(H)]
    moved = {}
    rank = {ch: i for i, ch in enumerate(LAYERS)}

    def put(ch, h, force=True):
        x, y = h
        if force or rank[ch] >= rank[grid[y][x]]:
            grid[y][x] = ch

    # the centre's ring is too small to shrink and keep its gaps, so it is
    # left out and drawn again below
    ring = set(full.RING)
    for x, y in full.RING:
        ring.add(flip(x, y, FH))
    for ch in LAYERS[1:]:
        hexes = [h for h in quarter if src[h[1]][h[0]] == ch
                 and not (ch == "w" and h in ring)]
        for h in hexes:
            if ch == "c":                   # rings keep their direction
                keep = next(k for k in full.neighbours(*h)
                            if src[k[1]][k[0]] == "K")
                d = [a - b for a, b in zip(to_cube(*h), to_cube(*keep))]
                k = to_cube(*moved[keep])
                moved[h] = from_cube(*(k[i] + d[i] for i in range(3)))
            else:
                moved[h] = place(*h)
            put(ch, moved[h])
        if ch in JOINED:
            for a in hexes:                 # rejoin what was joined
                for b in hexes:
                    if a < b and distance(a, b) == 1:
                        for h in line(moved[a], moved[b]):
                            put(ch, h, force=False)
    c, a = W // 2, H // 2 - 1               # the ring, drawn small by hand:
    for x, y in ((c, a - 1), (c - 2, a)):   # its north arc and west arc
        put("w", (x, y))
    for x in range(W):                      # walls stay off the edges
        if grid[0][x] == "w":
            grid[0][x] = "."
    for x in range(W // 2 + 1):             # flip the north half
        for y in range(H):
            if not north(x, y) or y == H - 1:
                u, v = flip(x, y)
                if 0 <= v:
                    grid[y][x] = grid[v][u]
    for x, y in quarter:                    # hexes not flipped north-south
        u, v = flip(x, y, FH)
        if src[v][u] != src[y][x]:
            put(src[v][u], flip(*moved.get((x, y)) or flip(*place(x, y))),
                force=src[y][x] != ".")
    if (W, H) == (29, 18):                  # asked for by hex, in-game
        for x, y in CLEAR:                  # coordinates less 1
            grid[y][x] = "."
        for (x, y), (u, v) in PLANET_MOVES:
            grid[y][x], grid[v][u] = ".", "p"
    for y in range(H):                      # flip the west half
        for x in range(W // 2):
            grid[y][W - 1 - x] = grid[y][x]
    keep = moved[start]
    return grid, [keep, flip(*keep)]


if __name__ == "__main__":
    out = sys.argv[1]
    W, H = (int(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else (29, 18)
    grid, keeps = shrink(W, H)
    full.write(grid, keeps,
               os.path.join(out, "maps/4p_Manufacturing_Consent_Small.map"))
    full.write(grid, keeps, os.path.join(
        out, "maps/default-terrain/4p_Manufacturing_Consent_Small.map"),
        full.WESNOTH, ("Kh", "Gg^Vh"))
    for row in grid:
        print("".join(row))
