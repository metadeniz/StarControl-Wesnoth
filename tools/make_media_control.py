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

Cliffs became asteroid walls, woods nebulae, tiberium fields asteroid
fields with a planet at each tiberium tree (the blue field has no tree),
rivers light badlands with thin badlands at the fords, and the pond west
of the centre badlands in a ring of dust. The dirt road ringing the centre
is a ring of dust clouds; the centre building is a planet in a moat of
light badlands. The other roads and the houses are open space. Each player
starts at the corner's player-start marker: a starbase with 5 docking
rings.

Also writes maps/default-terrain/4p_Media_Control.map: the same map in
default Wesnoth terrain (grass, woods, hills, impassable ridges, rivers,
fords, roads, villages).

Usage: make_media_control.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

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
     "e": "Yd", "o": "Ys"}
WESNOTH = {".": "Gg", "n": "Gs^Fp", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "r": "Ww", "f": "Wwf", "B": "Wo", "d": "Re",
           "e": "Ds", "o": "Re"}
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
WOODS = [
    (240, 275, 45, 50), (190, 230, 35, 30), (390, 165, 32, 38),
    (480, 112, 30, 18), (475, 30, 20, 25), (450, 365, 40, 32),
    (405, 420, 30, 20), (100, 440, 50, 30), (25, 470, 25, 18),
    (205, 530, 22, 32), (510, 330, 35, 18),
]
LONE_TREES = [(470, 463), (432, 487), (520, 445),   # inside the ring
              (250, 200), (290, 352)]
WALLS = [
    # the S-shaped ridge south-east of the start
    [(200, 228), (248, 228), (258, 255), (268, 270), (255, 292),
     (238, 310), (225, 335), (200, 350)],
    # the long ridge from the north edge, bending south-west
    [(470, 0), (483, 30), (493, 60), (498, 90), (458, 98), (446, 120),
     (445, 145), (410, 155), (375, 170), (356, 192), (348, 222)],
    [(498, 45), (547, 50)],
    # the two ridges on the west side, above the pond
    [(152, 388), (145, 412), (128, 430), (100, 440), (70, 448), (62, 470),
     (65, 495)],
    [(30, 475), (55, 492), (68, 515), (73, 545)],
    # the L-shaped ridge north-west of the ring, and the short one east of it
    [(365, 405), (400, 405), (422, 395), (430, 370), (426, 348)],
    [(468, 342), (500, 325), (530, 312), (547, 310)],
    # the cliffs on the far bank of the river north-east of the start
    [(233, 2), (234, 40), (230, 72)],
]
RIVER = [(0, 192), (140, 192), (152, 175), (150, 110), (175, 88),
         (208, 70), (216, 40), (218, 0)]
FORDS = [(75, 192), (146, 192)]  # where the start's two roads cross it
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
        "p": 1, "K": 1, "c": 1, "o": 1}       # a medium ship's moves


def moves(grid, start):
    """Moves a medium ship needs from start to every hex it can reach."""
    dist, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > dist[x, y]:
            continue
        for u, v in neighbours(x, y):
            if 0 <= u < W and 0 <= v < H and grid[v][u] != "w":
                n = d + COST[grid[v][u]]
                if n < dist.get((u, v), n + 1):
                    dist[u, v] = n
                    heapq.heappush(todo, (n, (u, v)))
    return dist


def place_planet(grid, keeps, p):
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
        grid[y][x] = "p"
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
    for w in WALLS:
        line("w", w)
    for x in range(W):               # walls stay off the edges, so ships
        for y in range(H):           # can pass along them
            if grid[y][x] == "w" and (x in (0, W - 1) or y in (0, H - 1)):
                grid[y][x] = "."
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
        # 5 docking rings: every neighbour but the one towards the centre
        ring = sorted(neighbours(x, y),
                      key=lambda n: (n[0] - CX) ** 2 + (n[1] - CY) ** 2)
        for u, v in ring[1:]:
            grid[v][u] = "c"
    for p in PLANETS:
        place_planet(grid, keeps, p)
    grid[CY][CX] = "p"                               # the centre building
    for u, v in neighbours(CX, CY):                  # in its moat
        grid[v][u] = "r"
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


if __name__ == "__main__":
    grid, keeps = build()
    write(grid, keeps, os.path.join(sys.argv[1], "maps/4p_Media_Control.map"))
    write(grid, keeps, os.path.join(
        sys.argv[1], "maps/default-terrain/4p_Media_Control.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in sys.argv:
        for row in grid:
            print("".join(row))
