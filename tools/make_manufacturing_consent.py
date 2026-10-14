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
     "H": "Yqr^Ygc", "X": "Yqe^Yxb", "U": "Yqr^Yxp", "S": "Ys^Yx", "M": "Ys^Ysg",
     "o": "Ys^Yxd1", "y": "Yd^Yxd5",
     "O": "Yqe^Ybh", "T": "Yqp^Yx", "V": "Yqp^Yxp",
     **{str(n): f"Yqe^Ybh{n}" for n in range(1, 7)},
     "Y": "Ys^Ytu5", "Z": "Ys^Ytu2",
     "q": "Ys^Yxd7", "g": "Yd^Yxd6", "b": "Ys^Ysb"}
WESNOTH = {".": "Gg", "n": "Gs^Fp", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "r": "Re", "B": "Wo", "f": "Wo^Bsb\\",
           "s": "Ss", "m": "Gg^Tf"}
WESNOTH.update({ch: "Md^Xm" for ch in "DRPEGHXUSOTVMoy123456YZqgb"})
LEAFY = "Gg^Fds"                 # every third wood hex is deciduous

# The dark stars: each diamond of "G" (gas giant in dark nebula) becomes one
# of the four dark star looks, in reading order, so each shows once
DARK_STARS = "JLNQ"
T.update({ch: f"Yqd^Yds{n}" for n, ch in enumerate(DARK_STARS, 1)})
WESNOTH.update({ch: "Md^Xm" for ch in DARK_STARS})


def number_dark_stars(grid):
    cells = sorted((y, x) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "G")
    groups = []
    for y, x in cells:
        for g in groups:
            if any(abs(y - gy) <= 1 and abs(x - gx) <= 1 for gy, gx in g):
                g.append((y, x)); break
        else:
            groups.append([(y, x)])
    assert len(groups) <= len(DARK_STARS) and all(len(g) == 4 for g in groups), groups
    for ch, g in zip(DARK_STARS, groups):
        for y, x in g:
            grid[y][x] = ch
    return grid


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


# Added on request: every cluster of barriers has a centrepiece. Each
# cluster of gravity eddies has a supermassive black hole (4 hexes, which
# takes one more hex, open before, to make the diamond), each plasma storm a
# star or a pulsar at its corner (stars in storms are red, blue or green), and the radiation zones round
# the south gas giants hold globular clusters instead (see "H" in T).
# In-game coordinates, both halves.
CENTREPIECES = [
    # (each a different one of the six looks, 1-6)
    ("1", [(16, 9), (17, 9), (17, 10), (18, 9)]),       # north-west eddies
    ("2", [(24, 9), (25, 9), (25, 10), (26, 9)]),       # north-east
    ("3", [(16, 19), (17, 19), (17, 20), (18, 19)]),    # south-west
    ("4", [(24, 19), (25, 19), (25, 20), (26, 19)]),    # south-east
    ("5", [(20, 12), (21, 12), (22, 12), (21, 13)]),    # the centre ring's north arc
    ("6", [(20, 16), (21, 16), (22, 16), (21, 17)]),    # and south arc
    ("T", [(18, 3)]), ("V", [(24, 3)]),                 # the plasma storms
    ("V", [(18, 25)]), ("T", [(24, 25)]),
]


def centrepieces(grid):
    for ch, hexes in CENTREPIECES:
        cloud = "E" if ch in "O123456" else "P"
        for X, Y in hexes:
            assert grid[Y - 1][X - 1] in (cloud, "X", "."), (X, Y, grid[Y - 1][X - 1])
            grid[Y - 1][X - 1] = ch
    return grid


# Added on request: loose asteroids gather round the big rocks. An open hex
# next to a gas giant becomes an asteroid field, and so do some of the open
# hexes next to a debris disk (asteroid wall). Picked by a fixed hash on
# the west half and mirrored, so both teams get the same.
NEAR_GIANT, NEAR_DISK = 1.0, 0.3


def asteroid_skirts(grid):
    H, W = len(grid), len(grid[0])
    for y in range(H):
        for x in range(W // 2 + 1):
            if grid[y][x] != ".":
                continue
            near = [grid[v][u] for u, v in neighbours(x, y) if 0 <= u < W and 0 <= v < H]
            chance = NEAR_GIANT if "G" in near else NEAR_DISK if "w" in near else 0
            if chance and (x * 7919 + y * 104729) % 100 < chance * 100:
                grid[y][x] = grid[y][W - 1 - x] = "a"
    return grid


# Hand edits asked for by hex, in-game coordinates, each with its copies on
# the other three sides: (hex, new terrain letter).
def mirrored4(X, Y):
    """An in-game hex and its copies mirrored west-east and north-south."""
    def flip(X, Y):
        return X, (29 - Y if X % 2 else 28 - Y)
    return list(dict.fromkeys([(X, Y), (42 - X, Y), flip(X, Y), flip(42 - X, Y)]))


HAND_EDITS = [
    # one-hex stars behind debris disks: orange at 5,13, yellow at 4,16
    # beside the red supergiant (copied west to east only)
    ((5, 13), "o"), ((37, 13), "o"), ((4, 16), "y"), ((38, 16), "y"),
    # the badlands channel opens at 21,21 and 21,8
    *[((21, y), ".") for y in (21, 8)],
    # the planets at 24,24 and its copies move two hexes outwards
    *[((x, y), ".") for x in (24, 18) for y in (24, 4)],
    *[((x, y), "p") for x in (26, 16) for y in (24, 4)],
    # the planet at 24,23 and the asteroid field at 25,23 swap
    ((24, 23), "a"), ((25, 23), "p"), ((18, 23), "a"), ((17, 23), "p"),
    ((24, 5), "a"), ((25, 6), "p"), ((18, 5), "a"), ((17, 6), "p"),
    # debris disks at 2,16 and 7,16 opened
    *[((x, y), ".") for x in (2, 40) for y in (16, 12)],
    *[((x, y), ".") for x in (7, 35) for y in (16, 13)],
    # the planet at 1,15 moves to 7,14 (copied west to east only)
    ((1, 15), "."), ((41, 15), "."), ((7, 14), "p"), ((35, 14), "p"),
    # the plasma storm at 23,23 opened, the gravity eddy at 23,21 badlands
    *[((x, y), ".") for x in (23, 19) for y in (23, 6)],
    *[((x, y), "B") for x in (23, 19) for y in (21, 8)],
    # 1,16 kept open
    *[((x, y), ".") for x in (1, 41) for y in (16, 13)],
    # a red supergiant in its debris disk, its top at 5,16 and 6,16
    # (mirrored west to east only)
    *[((x, y), "M") for x in (5, 6, 36, 37) for y in (16, 17)],
    # red nebula in the channel at 21,22, and its north-south mirror 21,7
    ((21, 22), "m"), ((21, 7), "m"),
    # asteroid field at 16,25 and 19,24, open space at 17,25, 17,24 and
    # 18,23, light badlands (swamp) at 15,20, 16,20, 17,21 and 18,20; all
    # mirrored four ways
    *[(h, ch) for xy, ch in [((16, 25), "a"), ((19, 24), "a"),
                             ((17, 25), "."), ((17, 24), "."), ((18, 23), "."),
                             ((15, 20), "s"), ((16, 20), "s"), ((17, 21), "s"), ((18, 20), "s")]
      for h in mirrored4(*xy)],
    # the asteroid field at 7,15 moves to 9,16, and 8,14 opens (mirrored
    # west to east)
    ((7, 15), "."), ((35, 15), "."), ((9, 16), "a"), ((33, 16), "a"),
    ((8, 14), "."), ((34, 14), "."),
    # the middle fortresses become two keeps with a docking ring between
    # them: keeps at 20,10 and 22,10, ring at 21,10 (mirrored north-south)
    *[((x, y), "K") for x in (20, 22) for y in (10, 18)],
    ((21, 10), "c"), ((21, 19), "c"),
    # the planet at 26,24 and the asteroid field at 26,25 swap (mirrored
    # four ways)
    *[(h, ch) for xy, ch in [((26, 24), "a"), ((26, 25), "p")]
      for h in mirrored4(*xy)],
    # a keep at 21,1 with a docking ring at 21,2, and their north-south
    # copy at the bottom edge: keep at 21,27, ring at 21,26
    ((21, 1), "K"), ((21, 2), "c"), ((21, 27), "K"), ((21, 26), "c"),
    # the asteroid field at 9,5 and the planet at 10,5 swap (mirrored four
    # ways)
    *[(h, ch) for xy, ch in [((9, 5), "p"), ((10, 5), "a")]
      for h in mirrored4(*xy)],
    # the south-east black hole takes the look of the centre's south one,
    # and the two centre black holes become 3-hex supergiants (green
    # north, blue south) in open space, turned half a circle from each other
    *[((x, y), "6") for x, y in [(24, 19), (25, 19), (25, 20), (26, 19)]],
    *[((x, y), ".") for x, y in [(20, 12), (21, 12), (22, 12), (21, 13),
                                 (20, 16), (21, 16), (22, 16), (21, 17)]],
    *[((x, y), "Y") for x, y in [(20, 12), (21, 12), (21, 13)]],
    *[((x, y), "Z") for x, y in [(21, 16), (21, 17), (22, 16)]],
    # 2,15 and 4,14 open, 1,16 an asteroid field (mirrored west to east)
    ((2, 15), "."), ((40, 15), "."), ((4, 14), "."), ((38, 14), "."),
    ((1, 16), "a"), ((41, 16), "a"),
    # the east side's stars get colours of their own: a purple star at
    # 37,13, and at 37,16 a blue giant with a green star beside it
    ((37, 13), "q"), ((38, 16), "g"),
    *[((x, y), "b") for x in (36, 37) for y in (16, 17)],
    # green nebula at 28,19 and 28,9, red nebula at 24,13 (mirrored west
    # to east)
    *[((x, y), "n") for x in (28, 14) for y in (19, 9)],
    ((24, 13), "m"), ((18, 13), "m"),
]


def hand_edits(grid):
    for (X, Y), ch in HAND_EDITS:
        grid[Y - 1][X - 1] = ch
    return swap_east_clusters(grid)


def swap_east_clusters(grid):
    """On the east side only, the dark nebula with its gas giant (north) and
    the radiation zone with its globular cluster (south) trade places: the
    clouds flipped north to south, and each 4-hex object moved onto the
    other's diamond, so both keep their shape."""
    east = [(X, Y) for X in range(28, 35) for Y in range(1, 28)]
    giant = [(X, Y) for X, Y in east if grid[Y - 1][X - 1] == "G"]
    cluster = [(X, Y) for X, Y in east if grid[Y - 1][X - 1] == "H"]
    for X, Y in giant:
        grid[Y - 1][X - 1] = "D"
    for X, Y in cluster:
        grid[Y - 1][X - 1] = "R"
    for X in range(28, 35):
        for Y in range(3, 9):
            Y2 = 29 - Y if X % 2 else 28 - Y
            a, b = grid[Y - 1][X - 1], grid[Y2 - 1][X - 1]
            if a in "DR" or b in "DR":
                grid[Y - 1][X - 1], grid[Y2 - 1][X - 1] = b, a
    for X, Y in giant:
        grid[Y - 1][X - 1] = "H"
    for X, Y in cluster:
        grid[Y - 1][X - 1] = "G"
    return grid


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
                code = table["."]
            elif (x, y) in starts:
                code = f"{starts[x, y]} {code}"
            row.append(code)
        rows.append(", ".join(row))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    grid, keeps = pad_top(*build())
    grid = number_dark_stars(hand_edits(asteroid_skirts(centrepieces(barriers(grid)))))
    write(grid, keeps,
          os.path.join(sys.argv[1], "maps/4p_Manufacturing_Consent.map"))
    write(grid, keeps, os.path.join(
        sys.argv[1], "maps/default-terrain/4p_Manufacturing_Consent.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in sys.argv:
        for row in grid:
            print("".join(row))
