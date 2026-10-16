#!/usr/bin/env python3
"""Write maps/4p_Media_Control.map.

Traced from a screenshot (1093x1080 px) of a 4-player ground map with
four-way rotational symmetry: a start in each corner, each one boxed in by
a river, and a ringed objective in the centre. Only its north-west quarter
is traced, in the screenshot's own pixel coordinates; every feature is
turned by 90, 180 and 270 degrees about the centre to make the other three
quarters. A hex grid can't be turned by 90 degrees exactly, so each turned
feature lands on the hexes nearest to it: the four quarters match to within
a hex.

Cliffs became impassable terrain (asteroid walls by the starts, dark
nebula, radiation, plasma storms and gravity eddies elsewhere, with a gas
giant, star, pulsar and black hole among them), woods nebulae (more were
added on request), tiberium fields asteroid
fields with a planet at each tiberium tree (the blue field has no tree),
rivers light badlands with thin badlands at the fords, and the pond west
of the centre badlands in a ring of dust. The dirt road ringing the centre
is a ring of dust clouds; the centre building is a planet in a moat of
light badlands, with a keep with 2 docking rings west and east of it
(added on request). The ridges just inside the ring became badlands
(water) on request, and the four planets round the ring sea planets
(swamp villages); a keep with 1 docking ring stands on the centre side of
each gas giant. The other roads and the houses are open space. Each
player starts at the corner's player-start marker: a starbase with 6
docking rings (the one towards the centre a swamp castle in default
terrain).

Also writes maps/default-terrain/4p_Media_Control.map: the same map in
default Wesnoth terrain (grass, woods, hills, impassable ridges, rivers,
fords, roads, villages).

Usage: make_media_control.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

from assign_planet_types import assign_file

W, H = 35, 31                 # playable hexes; Wesnoth adds a one-hex border
CX, CY = 17, 15               # the centre hex
SX, SY = 547, 539             # the screenshot's centre of rotation
K = 2.01                      # map units per screenshot pixel
# Wesnoth draws hexes squeezed side to side: columns are 54 px apart but
# rows 72. Turning by 90 degrees in those pixels would give the players
# whose bases face east or west fewer hexes to cross than the others, so
# the map is laid out on regular hexes instead (columns 72 * sqrt(3) / 2
# apart); every player then has the same hex counts to the same places,
# and in Wesnoth the map looks about 13% narrower than the screenshot.
HX = 36 * math.sqrt(3)

T = {".": "Ys", "n": "Yn", "a": "Ys^Ya", "w": "Ys^Yw", "p": "Ys^Vyp",
     "K": "Yk", "c": "Yc", "r": "Yis", "f": "Yif", "B": "Yi", "d": "Yd",
     "e": "Yd", "o": "Ys",
     # impassable terrains that replace most of the asteroid walls
     "D": "Yqd", "R": "Yqr", "P": "Yqp", "E": "Yqe", "S": "Yqd^Yx",
     "U": "Yqr^Yxp", "X": "Yqe^Yxb", "G": "Yqd^Ygg", "q": "Yis^Vys", "C": "Yc"}
WESNOTH = {".": "Gg", "n": "Gs^Fp", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "r": "Ww", "f": "Wwf", "B": "Wo", "d": "Re",
           "e": "Ds", "o": "Re", "q": "Ss^Vhs", "C": "Chs"}
BARRIER = "wDRPESUXG"
WESNOTH.update({ch: "Md^Xm" for ch in BARRIER})
# the four black holes, each drawn with a different one of the four looks
T.update({str(n): f"Yqe^Yxb{n}" for n in range(1, 5)})
WESNOTH.update({str(n): "Md^Xm" for n in range(1, 5)})


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

def number_black_holes(grid):
    holes = sorted((y, x) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "X")
    assert len(holes) == 4, holes
    for n, (y, x) in enumerate(holes, 1):
        grid[y][x] = str(n)
    return grid
LEAFY = "Gg^Fds"                 # every third wood hex is deciduous

# The north-west quarter, in screenshot pixels (x < 547, y < 539)
FIELDS = [                       # tiberium fields: centre x, y, radius x, y
    (50, 15, 65, 32),            # the corner field by the start
    (20, 315, 40, 32),           # on the west edge
    (325, 10, 22, 18),           # on the north edge
    (542, 85, 18, 16),           # on the north-south axis
    (482, 362, 18, 16),          # by the ridge north-west of the centre
    (385, 365, 18, 18),          # the blue field (no tree)
]
PLANETS = [(97, 22), (25, 305), (325, 12), (542, 85), (482, 362)]
SWAMP_PLANETS = [(482, 362)]     # sea planets (swamp villages), on request
WOODS = [
    (240, 275, 45, 50), (190, 230, 35, 30), (390, 165, 32, 38),
    (480, 112, 30, 18), (475, 30, 20, 25), (450, 365, 40, 32),
    (405, 420, 30, 20), (100, 440, 50, 30), (25, 470, 25, 18),
    (205, 530, 22, 32), (510, 330, 35, 18),
    # added on request: more nebulae in the open
    (290, 140, 25, 20), (150, 330, 25, 20), (330, 475, 25, 18),
    (440, 250, 25, 20), (60, 100, 20, 18),
]
LONE_TREES = [(470, 463), (432, 487), (520, 445),   # inside the ring
              (250, 200), (290, 352),
              (300, 60), (270, 420), (350, 300), (190, 130), (400, 50),
              (110, 360), (520, 250)]
# Impassable features: (terrain, line). The ridges by each start stay
# asteroid walls; on request the rest became other impassable terrain
# (dark nebula, radiation, plasma storm, gravity eddies).
WALLS = [
    # the S-shaped ridge south-east of the start
    ("w", [(200, 228), (248, 228), (258, 255), (268, 270), (255, 292),
           (238, 310), (225, 335), (200, 350)]),
    # the cliffs on the far bank of the river north-east of the start
    ("w", [(233, 2), (234, 40), (230, 72)]),
    # the long ridge from the north edge, bending south-west
    ("P", [(470, 0), (483, 30), (493, 60), (498, 90)]),
    ("P", [(498, 45), (547, 50)]),
    ("D", [(498, 90), (458, 98), (446, 120), (445, 145), (410, 155),
           (375, 170), (356, 192), (348, 222)]),
    # the two ridges on the west side, above the pond
    ("R", [(152, 388), (145, 412), (128, 430), (100, 440), (70, 448),
           (62, 470), (65, 495)]),
    ("E", [(30, 475), (55, 492), (68, 515), (73, 545)]),
]
# a star, pulsar and black hole in the middle of their clouds
OBJECTS = [("S", "D", (375, 170)), ("U", "R", (100, 440)),
           ("X", "E", (55, 492))]
# Gaps opened on request (asked for at in-game 25,25 and 29,22 and their
# turned copies): the tip of the dark nebula, to open space, and the end
# of the S-shaped ridge, to nebula
OPENINGS = [((330, 226), "D", "."), ((206, 333), "w", "n")]
GAS_GIANT = (450, 125)
# keeps by the gas giants moved on request (0-based): the one at in-game
# 9,18 was too close to the centre and went to 5,14, and the one on the
# opposite side, at 29,15, to 31,18; then the north and south ones went to
# the same places turned by 90 degrees, 21,5 and 16,27, so each player has
# one keep near their base
# (by gas giant: 0 north-west, 1 north-east, 2 south-east, 3 south-west)
MOVED_KEEPS = {3: (4, 13), 1: (30, 17), 0: (20, 4), 2: (15, 26)}           # 4 hexes at the dark nebula's bend
RIVER = [(0, 192), (140, 192), (152, 175), (150, 110), (175, 88),
         (208, 70), (216, 40), (218, 0)]
FORDS = [(75, 192), (146, 192)]  # where the start's two roads cross it
# the L-shaped ridge north-west of the ring and the short one east of it:
# asteroid walls in the screenshot, turned into water (badlands) on request
INNER = [
    [(365, 405), (400, 405), (422, 395), (430, 370), (426, 348)],
    [(468, 342), (500, 325), (530, 312), (547, 310)],
]
ROADS = [                        # only drawn in the default-terrain map
    [(98, 150), (75, 170), (72, 195), (80, 225), (105, 247)],
    [(98, 150), (130, 150), (148, 175), (152, 195), (168, 205), (150, 218)],
]
RING = [(547, 409), (520, 418), (503, 440), (463, 446), (423, 463),
        (410, 490), (411, 530), (412, 539)]          # the road round the centre
POND = (250, 540)
START = (95, 145)                # the player-start marker


def centre(x, y):
    """A hex's centre in map units (regular hexes 72 units tall)."""
    return HX * x + 36, 72 * y + 36 + (36 if x % 2 else 0)


# the middle of the map, a quarter of a hex below the centre hex's middle;
# turning about it takes each edge onto the next
MID = ((W - 1) * HX / 2 + 36, (72 * H + 36) / 2)


def to_map(sx, sy, turn=0):
    """A screenshot pixel, turned clockwise by turn * 90 degrees about the
    centre, in map units."""
    dx, dy = sx - SX, sy - SY
    for _ in range(turn):
        dx, dy = -dy, dx
    return MID[0] + dx * K, MID[1] + dy * K


def to_shot(mx, my, turn=0):
    """A map pixel turned anticlockwise by turn * 90 degrees, in screenshot
    pixels: the point of the traced quarter that lands on it."""
    dx, dy = (mx - MID[0]) / K, (my - MID[1]) / K
    for _ in range(turn):
        dx, dy = dy, -dx
    return SX + dx, SY + dy


def nearest(mx, my):
    best = None
    for x in range(max(0, int(mx / HX) - 2), min(W, int(mx / HX) + 3)):
        for y in range(max(0, int(my / 72) - 2), min(H, int(my / 72) + 3)):
            cx, cy = centre(x, y)
            d = (cx - mx) ** 2 + (cy - my) ** 2
            if best is None or d < best[0]:
                best = (d, x, y)
    if best is None or best[0] > 40 ** 2:
        return None                                  # off the map
    return best[1:]


def along(line, step=2):
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n + 1):
            yield x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n


def neighbours(x, y):
    up = y - 1 if x % 2 == 0 else y        # odd columns sit half a hex lower
    return [(x, y - 1), (x, y + 1), (x - 1, up), (x - 1, up + 1),
            (x + 1, up), (x + 1, up + 1)]


COST = {".": 1, "n": 2, "a": 2, "r": 3, "f": 1, "B": 3, "d": 2, "e": 2,
        "p": 1, "K": 1, "c": 1, "o": 1, "q": 1, "C": 1}       # a medium ship's moves


def moves(grid, start):
    """Moves a medium ship needs from start to every hex it can reach."""
    dist, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > dist[x, y]:
            continue
        for u, v in neighbours(x, y):
            if 0 <= u < W and 0 <= v < H and grid[v][u] not in BARRIER:
                n = d + COST[grid[v][u]]
                if n < dist.get((u, v), n + 1):
                    dist[u, v] = n
                    heapq.heappush(todo, (n, (u, v)))
    return dist


def place_planet(grid, keeps, p, ch="p"):
    """Put a planet and its three turned copies on the map. Turning lands
    them on slightly different hexes for each player, so each copy may
    move up to two hexes to put it as many moves from its own player's
    base as the others are from theirs."""
    spots = []
    for turn, keep in enumerate(keeps):
        dist = moves(grid, keep)
        x, y = nearest(*to_map(*p, turn))
        ring1 = [h for h in neighbours(x, y)]
        ring2 = {h for r in ring1 for h in neighbours(*r)} - set(ring1)
        near = [(0, (x, y))] + [(1, h) for h in ring1] + \
            [(2, h) for h in ring2 if h != (x, y)]
        spots.append([(dist[h], step, h) for step, h in near
                      if h in dist and (grid[h[1]][h[0]] in ".an"
                                        or step == 0)])
    target = round(sum(s[0][0] for s in spots) / 4)
    placed = []
    for s in spots:
        d, step, (x, y) = min(s, key=lambda c: (abs(c[0] - target), c[1]))
        grid[y][x] = ch
        placed.append(((x, y), d))
    return placed


def build():
    grid = [["." for _ in range(W)] for _ in range(H)]

    def put(ch, sx, sy):
        hexes = set()
        for turn in range(4):
            h = nearest(*to_map(sx, sy, turn))
            if h:
                grid[h[1]][h[0]] = ch
                hexes.add(h)
        return hexes

    def line(ch, pts):
        for sx, sy in along(pts):
            put(ch, sx, sy)

    def area(ch, e):
        cx, cy, rx, ry = e
        for x in range(W):
            for y in range(H):
                for turn in range(4):
                    sx, sy = to_shot(*centre(x, y), turn)
                    if ((sx - cx) / rx) ** 2 + ((sy - cy) / ry) ** 2 <= 1:
                        grid[y][x] = ch

    for e in WOODS:
        area("n", e)
    for p in LONE_TREES:
        put("n", *p)
    for e in FIELDS:
        area("a", e)
    line("d", RING)
    for r in ROADS:
        line("o", r)
    for ch, w in WALLS:
        line(ch, w)
    for x in range(W):               # walls stay off the edges, so ships
        for y in range(H):           # can pass along them
            if grid[y][x] in BARRIER and (x in (0, W - 1)
                                          or y in (0, H - 1)):
                grid[y][x] = "."
    for ch, cloud, p in OBJECTS:
        for turn in range(4):
            x, y = nearest(*to_map(*p, turn))
            if grid[y][x] == cloud:
                grid[y][x] = ch
    for p, kind, ch in OPENINGS:
        for turn in range(4):    # the hex of that feature nearest the point
            mx, my = to_map(*p, turn)
            near = [h for h in [nearest(mx, my)] + neighbours(*nearest(mx, my))
                    if 0 <= h[0] < W and 0 <= h[1] < H
                    and grid[h[1]][h[0]] == kind]
            x, y = min(near, key=lambda h: math.dist(centre(*h), (mx, my)))
            grid[y][x] = ch
    giants = []
    for turn in range(4):        # a diamond: 2 hexes and the 2 beside them
        x, y = nearest(*to_map(*GAS_GIANT, turn))
        up = y - 1 if x % 2 == 0 else y
        diamond = [(x, y), (x, y + 1), (x + 1, up), (x + 1, up + 1)]
        for u, v in diamond:
            grid[v][u] = "G"
        giants.append(diamond)
    for w in INNER:
        line("B", w)
    line("r", RIVER)
    for p in FORDS:
        put("f", *p)
    area("e", POND + (34, 30))
    put("B", *POND)
    keeps = []
    for turn in range(4):
        x, y = nearest(*to_map(*START, turn))
        grid[y][x] = "K"
        keeps.append((x, y))
        # 6 docking rings; on request the one towards the centre is a
        # swamp castle in the default-terrain map
        ring = sorted(neighbours(x, y),
                      key=lambda n: (n[0] - CX) ** 2 + (n[1] - CY) ** 2)
        for u, v in ring[1:]:
            grid[v][u] = "c"
        grid[ring[0][1]][ring[0][0]] = "C"
    for p in PLANETS:
        place_planet(grid, keeps, p, "q" if p in SWAMP_PLANETS else "p")
    dists = [moves(grid, k) for k in keeps]
    for turn, diamond in enumerate(giants):
        # added on request: a keep with 1 docking ring two hexes from the
        # gas giant on its centre side, the ring towards the centre
        gx = sum(centre(*h)[0] for h in diamond) / 4
        gy = sum(centre(*h)[1] for h in diamond) / 4
        dx, dy = MID[0] - gx, MID[1] - gy
        r = math.hypot(dx, dy)
        kx, ky = nearest(gx + dx / r * 150, gy + dy / r * 150)
        # it lies between two players' bases: move it a hex if that puts
        # it as many moves from the one as from the other
        def gap(h):
            a, b = sorted(d.get(h, 99) for d in dists)[:2]
            return b - a, h != (kx, ky)
        kx, ky = min([(kx, ky)] + [h for h in neighbours(kx, ky)
                                   if grid[h[1]][h[0]] in ".n"], key=gap)
        kx, ky = MOVED_KEEPS.get(turn, (kx, ky))
        ring = min(neighbours(kx, ky), key=lambda h: math.dist(centre(*h), MID))
        grid[ky][kx] = "K"
        grid[ring[1]][ring[0]] = "c"
    grid[CY][CX] = "p"                               # the centre building
    for u, v in neighbours(CX, CY):                  # in its moat
        grid[v][u] = "r"
    # added on request: a keep west and east of the moat, each with 2
    # docking rings (north and south of it); no side starts there
    for x in (CX - 3, CX + 3):
        grid[CY][x] = "K"
        grid[CY - 1][x] = grid[CY + 1][x] = "c"
    return grid, keeps


def write(grid, keeps, path, table=T, base_only=("Yk", "Ys^Vyp")):
    # sides clockwise from the north-west corner; 1 & 3 and 2 & 4 face
    # each other across the centre
    order = sorted(keeps, key=lambda k: math.atan2(
        centre(*k)[1] - MID[1], centre(*k)[0] - MID[0]))
    nw = min(order, key=lambda k: k[0] + k[1])
    i = order.index(nw)
    starts = {k: n + 1 for n, k in enumerate(order[i:] + order[:i])}
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x = min(max(X - 1, 0), W - 1)
            y = min(max(Y - 1, 0), H - 1)
            code = table[grid[y][x]]
            if table is WESNOTH and code == "Gs^Fp":
                if (x * 7 + y * 3) % 3 == 0:
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
    assign_file(path, quiet=True)          # life, mineral and dead worlds


if __name__ == "__main__":
    grid, keeps = build()
    grid = number_dark_stars(number_black_holes(grid))
    write(grid, keeps, os.path.join(sys.argv[1], "maps/4p_Media_Control.map"))
    write(grid, keeps, os.path.join(
        sys.argv[1], "maps/default-terrain/4p_Media_Control.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in sys.argv:
        for row in grid:
            print("".join(row))
