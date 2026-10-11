#!/usr/bin/env python3
"""Write maps/4p_Manufacturing_Consent.map.

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
its edge: a starbase with 5 docking rings. Added on request: two nebulae
inside the centre's ring of walls, a small starbase with 2 docking rings
north and south of the ring on the centre column, and no wall touching the
top or bottom edge; a channel of badlands with one crossing beyond each
of those keeps, fed by swamps, a small keep with 1 docking ring on each
team's side, and red nebulae (mushroom groves) by the ring.

Also writes maps/default-terrain/4p_Manufacturing_Consent.map: the same
map in default Wesnoth terrain (grass, woods, hills, impassable ridges,
roads, villages).

Usage: make_manufacturing_consent.py <add-on dir>
"""

import math
import os
import sys

W, H = 41, 26            # playable hexes; Wesnoth adds a one-hex border
IW, IH = 1124, 971       # the screenshot

T = {".": "Ys", "n": "Yn", "a": "Ys^Ya", "w": "Ys^Yw", "p": "Ys^Vyp",
     "K": "Yk", "c": "Yc", "r": "Ys", "B": "Yi", "f": "Yif",
     "s": "Yis", "m": "Yr",
     # barriers that replace most of the asteroid walls (see BARRIERS)
     "D": "Yqd", "R": "Yqr", "P": "Yqp", "E": "Yqe", "G": "Yqd^Ygg",
     "H": "Yqr^Ygg", "X": "Yqe^Yxb", "U": "Yqr^Yxp", "S": "Ys^Yx"}
WESNOTH = {".": "Gg", "n": "Gs^Fp", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "r": "Re", "B": "Wo", "f": "Wo^Bsb\\",
           "s": "Ss", "m": "Gg^Tf"}
WESNOTH.update({ch: "Md^Xm" for ch in "DRPEGHXUS"})
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
RING_WOODS = [(19, 12)]          # nebulae inside the ring, beside its planet
# A small keep on the centre column north of the ring (and south, by the
# flip), as far from the west starts as from the east, with 2 recruit
# hexes, one west and one east; no side starts there
MID_KEEP, MID_RINGS = (20, 8), [(19, 8)]
# Asked for by hex, in these 0-based coordinates (in-game ones are 1 more),
# all set in the north half and flipped like the rest:
# badlands down the centre column north of the north keep (in-game 21,2 to
# 21,7, and 21,20 to 21,25 in the south), with a crossing of thin badlands
# (a bridge in default terrain) at in-game 21,5 and 21,22
CHANNEL = [(20, y) for y in range(1, 7)]
CROSSING = (20, 4)
# swamp (light badlands) joining the channel at in-game 19,2 / 19,25 and
# 23,2 / 23,25
SWAMP = [(18, 0), (18, 1), (19, 0)]
# a keep at in-game 10,13 on the north-south axis, in the gap of the short
# west ridge, with 1 recruit hex towards the centre (in-game 11,13);
# mirrored east at 32,13
WEST_KEEP, WEST_RINGS = (9, 12), [(10, 12)]
# mushroom forest (red nebula) at in-game 19,16 and its flip 19,11, and at
# 17,13 (whose flip, 17,14, is a planet); mirrored east
MUSHROOMS = [(18, 15), (18, 10), (16, 12)]
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
    for x in range(W // 2 + 1):      # walls stay off the top and bottom
        if grid[0][x] == "w":        # edges, so ships can pass along them
            grid[0][x] = "."
    for x, y in RING_WOODS:
        grid[y][x] = "n"
    grid[MID_KEEP[1]][MID_KEEP[0]] = "K"
    for x, y in MID_RINGS:
        grid[y][x] = "c"
    for x, y in SWAMP:
        grid[y][x] = "s"
    for x, y in CHANNEL:
        grid[y][x] = "B"
    grid[CROSSING[1]][CROSSING[0]] = "f"
    grid[WEST_KEEP[1]][WEST_KEEP[0]] = "K"
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
    for x, y in WEST_RINGS:       # one hex, so it is not flipped north-south
        grid[y][x] = "c"
    for x, y in MUSHROOMS:
        grid[y][x] = "m"
    for y in range(H):                               # flip the west half
        for x in range(W // 2):
            grid[y][W - 1 - x] = grid[y][x]
    return grid, keeps


# Added on request: most asteroid walls became other barriers. In-game
# coordinates (after pad_top), west half; the east half is the mirror
# image, x -> 42 - x. Every hex listed must be a wall.
BARRIERS = [
    # the big north and south rock masses: a gas giant (4 hexes) wrapped
    # in a dark nebula, and in a radiation zone
    ("G", [(11, 4), (11, 5), (12, 4), (12, 5)]),
    ("D", [(10, 3), (11, 3), (10, 6), (11, 6), (10, 7), (11, 7), (9, 7)]),
    ("H", [(11, 23), (11, 24), (12, 23), (12, 24)]),
    ("R", [(9, 22), (10, 21), (10, 22), (11, 22), (10, 25), (11, 25), (11, 26)]),
    # beside the badlands channel: plasma storms
    ("P", [(16, 3), (17, 3), (18, 3), (19, 4), (19, 5), (19, 6)]),
    ("P", [(16, 25), (17, 26), (18, 25), (19, 23), (19, 24), (19, 25)]),
    # the long diagonals: gravity eddies
    ("E", [(14, 9), (15, 10), (16, 9), (17, 10), (18, 9), (19, 8), (19, 9)]),
    ("E", [(14, 19), (15, 19), (16, 19), (17, 19), (18, 19), (19, 20), (19, 21)]),
    # the centre ring's west arc: a pulsar in its own radiation
    ("U", [(18, 14)]),
    ("R", [(18, 13), (18, 15)]),
    # lone rocks near the top and bottom: stars
    ("S", [(13, 3), (13, 26)]),
]
# the centre ring's north and south arcs: a black hole in its eddy
CENTRE_BARRIERS = [("X", [(21, 12), (21, 17)]), ("E", [(20, 12), (22, 12), (20, 16), (22, 16)])]


def barriers(grid):
    W = len(grid[0])
    for ch, hexes in BARRIERS + CENTRE_BARRIERS:
        for X, Y in hexes:
            for x in {X - 1, W - X}:       # 0-based, and its mirror
                assert grid[Y - 1][x] in ("w", ch), (X, Y, grid[Y - 1][x])
                grid[Y - 1][x] = ch
    return grid


def pad_top(grid, keeps):
    """Add a row along the top, a copy of the bottom one. The flip leaves the
    bottom of the odd columns half a hex lower than the top of the even
    ones, so the map looked roomier in the south; with this row the odd
    columns flip exactly and the even ones reach half a hex higher at the
    top instead. Every in-game row number goes up by 1."""
    return [list(grid[-1])] + grid, [(x, y + 1) for x, y in keeps]


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
    grid, keeps = pad_top(*build())
    grid = barriers(grid)
    write(grid, keeps,
          os.path.join(sys.argv[1], "maps/4p_Manufacturing_Consent.map"))
    write(grid, keeps, os.path.join(
        sys.argv[1], "maps/default-terrain/4p_Manufacturing_Consent.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in sys.argv:
        for row in grid:
            print("".join(row))
