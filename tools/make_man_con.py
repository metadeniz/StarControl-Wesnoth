#!/usr/bin/env python3
"""Write maps/4p_Man_Con.map.

Traced from a screenshot (1124x971 px) of a 4-player ground map that is
mirror-symmetric left to right and top to bottom. Only its north-west
quarter is traced, in the screenshot's own pixel coordinates; the
south-west quarter is that quarter flipped top to bottom, and the east half
is the west half flipped left to right. The width is odd, so the flip is
exact on Wesnoth's hex grid and both teams get the same map; north and
south match to within a hex.

Cliffs became asteroid walls, woods nebulae, tiberium fields asteroid
fields with a planet at each tiberium tree, and the two buildings on the
west and east edges and the one in the centre planets. Roads, houses and
dirt are open space. Each team starts at the two player-start markers on
its edge: a starbase with 5 docking rings.

Also writes maps/default-terrain/4p_Man_Con.map: the same map in default
Wesnoth terrain (grass, woods, hills, impassable ridges, roads, villages).

Usage: make_man_con.py <add-on dir>
"""

import math
import os
import sys

W, H = 41, 26            # playable hexes; Wesnoth adds a one-hex border
IW, IH = 1124, 971       # the screenshot

T = {".": "Ys", "n": "Yn", "a": "Ys^Ya", "w": "Ys^Yw", "p": "Ys^Vyp",
     "K": "Yk", "c": "Yc", "r": "Ys"}
WESNOTH = {".": "Gg", "n": "Gs^Fp", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "r": "Re"}
LEAFY = "Gg^Fds"                 # every third wood hex is deciduous

# The north-west quarter, in screenshot pixels (x < 562, y < 485)
WALLS = [
    # the S-shaped ridge in the north-west, with its hook at the top
    [(335, 52), (305, 40), (275, 32), (272, 50), (280, 75), (295, 100),
     (308, 125), (305, 145), (290, 170), (278, 190), (268, 205), (250, 208)],
    # the ridge along the east side of the north tiberium field
    [(425, 63), (455, 62), (485, 65), (495, 85), (500, 115), (505, 150),
     (500, 165)],
    # the L-shaped ridge north of the centre
    [(368, 290), (400, 300), (440, 305), (475, 305), (490, 285),
     (500, 262), (515, 238)],
    # the long ridge above the west edge's middle field
    [(30, 405), (80, 405), (130, 407), (165, 410), (185, 415)],
    # the short ridge west of the centre (its south half is the flip)
    [(238, 452), (242, 465), (240, 485)],

]
# The ring round the centre, set hex by hex so a one-hex gap is left at
# each corner as in the screenshot: its north arc and its west arc
RING = [(20, 10), (19, 10), (17, 11), (17, 12)]
ROADS = [                        # only drawn in the default-terrain map
    [(500, 30), (530, 55), (562, 75), (562, 290)],
]
WOODS = [                        # ellipses: centre x, y, radius x, y
    (155, 20, 26, 22), (330, 135, 18, 40), (475, 45, 18, 14),
    (380, 318, 24, 16), (445, 322, 16, 12), (35, 180, 24, 18),
    (85, 175, 16, 14), (78, 222, 20, 16), (280, 470, 26, 45),
    (530, 393, 35, 16),
]
FIELDS = [                       # tiberium fields: ellipses
    (57, 125, 32, 30), (248, 140, 30, 28), (466, 138, 24, 64),
    (82, 488, 32, 30), (452, 487, 14, 14),
]
BIG_FIELD = [(0, 275), (30, 275), (80, 325), (122, 375), (122, 400),
             (0, 400)]           # the big field on the west edge
PLANETS = [(57, 117), (248, 142), (467, 105), (467, 155), (68, 345),
           (82, 485), (452, 485),
           (18, 485),            # the building on the west edge
           (562, 485)]           # the building in the centre
START = (133, 210)               # the player-start marker


def centre(x, y):
    """A hex's centre in screenshot pixels."""
    px, py = 54 * x + 36, 72 * y + 36 + (36 if x % 2 else 0)
    return px * IW / (54 * W + 18), py * IH / (72 * H + 36)


def north(x, y):
    """Hexes drawn from the screenshot; the rest are their flip. Row 12 of
    the odd columns lies on the axis and flips onto itself."""
    return y <= 12 or (x % 2 and y == H - 1)


def flip(x, y):
    """The hex mirroring (x, y) top to bottom. A flip of the hex grid moves
    the south half up half a hex, which keeps every hex's neighbours."""
    return x, H - 1 - y - x % 2


def nearest(ix, iy, test=north):
    """The west-half hex nearest a screenshot pixel."""
    best = None
    for x in range(W // 2 + 1):
        for y in range(H):
            if not test(x, y):
                continue
            cx, cy = centre(x, y)
            d = (cx - ix) ** 2 + (cy - iy) ** 2
            if best is None or d < best[0]:
                best = (d, x, y)
    return best[1:]


def along(line, step=3):
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n + 1):
            yield x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n


def inside(px, py, poly):
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > py) != (y1 > py) and px < x0 + (x1 - x0) * (py - y0) / (y1 - y0):
            hit = not hit
    return hit


def neighbours(x, y):
    up = y - 1 if x % 2 == 0 else y        # odd columns sit half a hex lower
    return [(x, y - 1), (x, y + 1), (x - 1, up), (x - 1, up + 1),
            (x + 1, up), (x + 1, up + 1)]


def build():
    grid = [["." for _ in range(W)] for _ in range(H)]

    def paint(ch, test):
        for x in range(W // 2 + 1):
            for y in range(H):
                ix, iy = centre(x, y)
                if north(x, y) and test(ix, min(iy, IH - iy)):
                    grid[y][x] = ch

    def ellipse(cx, cy, rx, ry):
        return lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1

    for e in WOODS:
        paint("n", ellipse(*e))
    for e in FIELDS:
        paint("a", ellipse(*e))
    paint("a", lambda x, y: inside(x, y, BIG_FIELD))
    for kind, lines in (("r", ROADS), ("w", WALLS)):
        for line in lines:
            for ix, iy in along(line):
                x, y = nearest(ix, iy)
                grid[y][x] = kind
    for x, y in RING:
        grid[y][x] = "w"
    for ix, iy in PLANETS + [START]:
        if iy < 480:
            x, y = nearest(ix, iy)
            grid[y][x] = "p" if (ix, iy) != START else "K"
    x, y = keep = nearest(*START)
    # 5 docking rings: every neighbour but the one towards the centre
    ring = sorted(neighbours(x, y),
                  key=lambda n: (n[0] - W // 2) ** 2 + (n[1] - H / 2) ** 2)
    for u, v in ring[1:]:
        grid[v][u] = "c"
    for x in range(W // 2 + 1):                      # flip the north half
        for y in range(H):
            if not north(x, y):
                u, v = flip(x, y)
                grid[y][x] = grid[v][u]
    for ix, iy in PLANETS:                           # those on the axis
        if iy >= 480:
            x, y = nearest(ix, iy, lambda x, y: True)
            grid[y][x] = "p"
    keeps = [keep, flip(*keep)]
    for y in range(H):                               # flip the west half
        for x in range(W // 2):
            grid[y][W - 1 - x] = grid[y][x]
    return grid, keeps


def write(grid, keeps, path, table=T, base_only=("Yk", "Ys^Vyp")):
    H, W = len(grid), len(grid[0])
    (wx0, wy0), (wx1, wy1) = sorted(keeps, key=lambda k: k[1])
    # sides 1 and 3 west (north, south), 2 and 4 east (north, south)
    starts = {(wx0, wy0): 1, (W - 1 - wx0, wy0): 2,
              (wx1, wy1): 3, (W - 1 - wx1, wy1): 4}
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x = min(max(X - 1, 0), W - 1)
            y = min(max(Y - 1, 0), H - 1)
            code = table[grid[y][x]]
            if table is WESNOTH and code == "Gs^Fp":
                u = min(x, W - 1 - x)
                if (u * 7 + y * 3) % 3 == 0:
                    code = LEAFY
            border = (X - 1, Y - 1) != (x, y)
            if border and code in base_only:
                code = table["c"] if grid[y][x] == "K" else table["."]
            elif (x, y) in starts:
                code = f"{starts[x, y]} {code}"
            row.append(code)
        rows.append(", ".join(row))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    grid, keeps = build()
    write(grid, keeps, os.path.join(sys.argv[1], "maps/4p_Man_Con.map"))
    write(grid, keeps, os.path.join(sys.argv[1],
                                    "maps/default-terrain/4p_Man_Con.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in sys.argv:
        for row in grid:
            print("".join(row))
