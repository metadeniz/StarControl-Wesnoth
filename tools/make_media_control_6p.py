#!/usr/bin/env python3
"""Write maps/6p_Media_Control.map: Media Control for six players.

The north-west quarter of maps/4p_Media_Control.map (one player's corner,
from the centre out to the map's north and west edges) is stretched onto
one sixth of a hexagon of space, a start in each of its corners, and
turned six ways. Hex grids turn by 60 degrees exactly, so all six sixths
match hex for hex and every start has the same hex counts to the same
places.

The quarter is a square in moves (a column across and a row down count
as one move each): the centre, the middle of the north edge, the corner
and the middle of the west edge. Its sixth of the hexagon has the same
four points: the centre, the middle of the edge clockwise of the corner,
the corner and the middle of the edge anticlockwise of it, and the square
is laid onto it by bilinear interpolation, so the north axis (bordering
the next player clockwise in the 4p map) becomes the line to the edge
clockwise of the corner and the west axis the line anticlockwise. Terrain
is copied from the nearest hex of the quarter; the starts, keeps,
planets, stars and other objects are put back whole on the hex nearest to
where they land:

- each start with 6 docking rings, and its small starbase with 1;
- the five planets, keeping their types (life, mineral, sea);
- the star in dark nebula and the pulsar in radiation;
- the 3-hex supergiant with rocks in front of it (a debris disk), each
  sixth its own colour, and two hexes of debris disk on its centre side;
- the 4-hex dark star (whose diamond can only stand one way on the grid,
  so it can't be turned by 60 degrees) as a 3-hex dark star;
- in the middle, the centre planet in its moat, and a small starbase with
  2 docking rings on each line between two players, where the 4p map has
  one on each axis.

Players are numbered 1 to 6 clockwise from the north. Outside the hexagon
is the void (off the map).

Usage: make_media_control_6p.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

R = 22                        # the hexagon's radius in hexes, centre to corner
W = H = 2 * R + 1             # playable hexes; Wesnoth adds a one-hex border
CX, CY = R, R                 # the centre hex (an even column)
VOID = "_off^_usr"
SOURCE = "maps/4p_Media_Control.map"
N4, C4 = 37, 18               # the 4p map's size and centre

# the 4p objects in the north-west quarter (in-game x,y there)
START = (4, 5)
SMALL_KEEP = (8, 14)          # with 1 docking ring
AXIS_KEEP = (15, 19)          # on the west axis, 2 docking rings
SUPERGIANT = [(10, 10), (10, 11), (11, 11)]
DARK_STAR = [(16, 5), (17, 5), (16, 6), (17, 6)]
# supergiant colours (^Ytd1..6) clockwise from the north: the 4p map's blue,
# green, orange and red, then yellow and white
COLOURS = [5, 6, 2, 1, 3, 4]

# lines one hex wide: the river round each start and its fords, the
# badlands and the dust ring round the centre
LINES = {"Yis": "Yis", "Yif": "Yis", "Yi": "Yi", "Yd": "Yd"}

# a medium ship's moves into each terrain; anything else is impassable
COST = {"Ys": 1, "Yn": 2, "Ys^Ya": 2, "Yis": 3, "Yif": 1, "Yi": 3, "Yd": 2,
        "Yk": 1, "Yc": 1}


# ------------------------------------------------------------- hex geometry
def to_cube(x, y):
    return x, y - (x - (x & 1)) // 2


def to_offset(q, r):
    return q, r + (q - (q & 1)) // 2


C = to_cube(CX, CY)


def dist(a, b):
    (q1, r1), (q2, r2) = to_cube(*a), to_cube(*b)
    return max(abs(q1 - q2), abs(r1 - r2), abs(q1 + r1 - q2 - r2))


def inside(x, y):
    return 0 <= x < W and 0 <= y < H and dist((x, y), (CX, CY)) <= R


def neighbours(x, y):
    up = y - 1 if x % 2 == 0 else y        # odd columns sit half a hex lower
    return [(x, y - 1), (x, y + 1), (x - 1, up), (x - 1, up + 1),
            (x + 1, up), (x + 1, up + 1)]


def turn(x, y, k=1):
    """The hex turned k sixths clockwise about the centre."""
    q, r = to_cube(x, y)
    q, r = q - C[0], r - C[1]
    s = -q - r
    for _ in range(k % 6):
        q, r, s = -r, -s, -q
    return to_offset(q + C[0], r + C[1])


def six(h):
    return [turn(*h, k) for k in range(6)]


def pixel(x, y):
    """A hex's centre, from the map's centre; neighbours are sqrt(3) apart."""
    return 1.5 * (x - CX), math.sqrt(3) * (y - CY + 0.5 * (x & 1))


def sixth(x, y):
    """Which start's sixth a hex is in: 0 north, then clockwise. A hex on
    the line between two sixths goes to the clockwise one."""
    px, py = pixel(x, y)
    angle = math.degrees(math.atan2(px, -py)) % 360
    return int((angle + 30 + 1e-6) // 60) % 6


# ------------------------------------------- the 4p quarter onto the sixth
# the north sixth's corners: the middle of the edge clockwise of the corner
# (a, where the 4p north axis goes), the corner, and the middle of the edge
# anticlockwise of it (b, the 4p west axis)
MA = (1.5 * R * 0.5, -1.5 * R * math.sqrt(3) / 2)
MB = (-MA[0], MA[1])
CORNER = (0, -math.sqrt(3) * R)


def forward(u, v):
    """Where (u, v) of the quarter lands: u from the centre to the north
    edge, v from the centre to the west edge, both 0 to 1."""
    return tuple(u * (1 - v) * a + (1 - u) * v * b + u * v * c
                 for a, b, c in zip(MA, MB, CORNER))


def backward(px, py):
    u = v = 0.5
    for _ in range(50):                    # Newton's method
        fx, fy = forward(u, v)
        ex, ey = fx - px, fy - py
        dux = (1 - v) * MA[0] - v * MB[0] + v * CORNER[0]
        duy = (1 - v) * MA[1] - v * MB[1] + v * CORNER[1]
        dvx = -u * MA[0] + (1 - u) * MB[0] + u * CORNER[0]
        dvy = -u * MA[1] + (1 - u) * MB[1] + u * CORNER[1]
        det = dux * dvy - dvx * duy
        u -= (ex * dvy - dvx * ey) / det
        v -= (dux * ey - ex * duy) / det
    return u, v


def ms(x, y):
    """A 4p hex (0-based) in moves from the 4p centre."""
    return x - C4, ((2 * y + (x & 1)) - 2 * C4) / 2


def uv_of(X, Y):
    """A 4p hex (in-game x,y) as (u, v) of the quarter."""
    dc, dr = ms(X - 1, Y - 1)
    return -dr / C4, -dc / C4


def path(a, b):
    """The hexes on a straight line from a to b."""
    (q1, r1), (q2, r2) = to_cube(*a), to_cube(*b)
    n = dist(a, b)
    out = []
    for i in range(n + 1):
        t = i / n if n else 0
        q, r = q1 + (q2 - q1) * t + 1e-6, r1 + (r2 - r1) * t + 2e-6
        s = -q - r
        rq, rr, rs = round(q), round(r), round(s)
        dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
        if dq > dr and dq > ds:
            rq = -rr - rs
        elif dr > ds:
            rr = -rq - rs
        out.append(to_offset(rq, rr))
    return out


def nearest_hex(p, ok=lambda h: True):
    return min(((x, y) for x in range(W) for y in range(H)
                if inside(x, y) and ok((x, y))),
               key=lambda h: (math.dist(pixel(*h), p), h))


def land(X, Y):
    """The hex a 4p hex (in-game x,y) lands on."""
    return nearest_hex(forward(*uv_of(X, Y)))


# ---------------------------------------------------------- the 4p terrain
def read_source(addon):
    rows = [[c.strip() for c in r.split(",")]
            for r in open(os.path.join(addon, SOURCE)).read().splitlines()
            if r.strip()]
    return [row[1:-1] for row in rows[1:-1]]


# objects are taken off the copied terrain and put back whole
BASE = {"Yk": "Ys", "Yc": "Ys", "Ys^Yw": "Ys", "Yqd^Yx": "Yqd",
        "Yqr^Yxp": "Yqr"}


def base(code):
    code = code.split(" ")[-1]
    if code in BASE:
        return BASE[code]
    if "^V" in code or "^Ytd" in code:
        return code.split("^")[0]
    if "^Yds" in code:
        return "Yqd"
    return code


def quarter_hexes():
    """The 4p hexes of the north-west quarter (with the axes' ends)."""
    out = []
    for x in range(N4):
        for y in range(N4):
            dc, dr = ms(x, y)
            if dc <= 0 and dr <= 0:
                out.append((x, y))
    return out


def sample(src, quarter, x, y):
    u, v = backward(*pixel(x, y))
    want = (-C4 * v, -C4 * u)
    sx, sy = min(quarter, key=lambda h: (math.dist(ms(*h), want), h))
    return base(src[sy][sx])


# ----------------------------------------------------------------- build
def triangles_at(h):
    nb = neighbours(*h)
    return [tuple(sorted([h, a, b])) for a in nb for b in nb
            if a < b and b in neighbours(*a)]


def centroid(hs):
    pts = [pixel(*h) for h in hs]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def triangle_near(p):
    """The triangle of three hexes whose middle is nearest p."""
    cands = {t for x in range(W) for y in range(H) if inside(x, y)
             for t in triangles_at((x, y)) if all(inside(*h) for h in t)}
    return min(cands, key=lambda t: (math.dist(centroid(t), p), t))


def from_centre(h):
    return sum(c * c for c in pixel(*h))


def build(src):
    g = [[VOID] * W for _ in range(H)]
    quarter = quarter_hexes()
    # terrain: each hex of the north sixth from the 4p quarter, then turned
    canon = {}
    for x in range(W):
        for y in range(H):
            if not inside(x, y):
                continue
            k = sixth(x, y)
            h0 = turn(x, y, -k)
            if h0 not in canon:
                canon[h0] = sample(src, quarter, *h0)
            g[y][x] = canon[h0]

    def put(h, code):
        for k, (x, y) in enumerate(six(h)):
            g[y][x] = code(k) if callable(code) else code

    def code_at(X, Y):
        return src[Y - 1][X - 1]
    # copying from the nearest hex breaks up the lines one hex wide where
    # the quarter is stretched: draw them again, hex to neighbouring hex,
    # from where each lands (the fords on top)
    for X in range(1, N4 + 1):
        for Y in range(1, N4 + 1):
            c = code_at(X, Y)
            if c not in LINES or ms(X - 1, Y - 1)[0] >= 0:
                continue
            for u, v in neighbours(X - 1, Y - 1):
                if 0 <= u < N4 and 0 <= v < N4 and ms(u, v)[0] < 0 \
                        and ms(u, v)[1] <= 0 and code_at(u + 1, v + 1) in LINES:
                    for h in path(land(X, Y), land(u + 1, v + 1)):
                        put(h, LINES[c] if LINES[c] == LINES[code_at(u + 1, v + 1)] else "Yis")
    for X in range(1, N4 + 1):
        for Y in range(1, N4 + 1):
            if code_at(X, Y) == "Yif" and ms(X - 1, Y - 1)[0] < 0 and ms(X - 1, Y - 1)[1] <= 0:
                put(land(X, Y), "Yif")
    # the centre: the 4p centre planet in its moat
    g[CY][CX] = src[C4][C4]
    for h in neighbours(CX, CY):
        g[h[1]][h[0]] = src[C4 - 1][C4]
    # the 3-hex supergiant with two hexes of debris disk on its centre side
    tri = triangle_near(centroid([land(*h) for h in SUPERGIANT]))
    for h in tri:
        put(h, lambda k: f"Ys^Ytd{COLOURS[k]}")
    front = sorted({m for h in tri for m in neighbours(*h)
                    if inside(*m) and m not in tri}, key=from_centre)[:2]
    for m in front:
        put(m, "Ys^Yw")
    # the dark star, three hexes in dark nebula
    tri = triangle_near(centroid([land(*h) for h in DARK_STAR]))
    for h in tri:
        put(h, "Yqd^Ytds")
    # single-hex objects and planets, keeping their codes
    for X in range(1, N4 + 1):
        for Y in range(1, N4 + 1):
            c = code_at(X, Y)
            dc, dr = ms(X - 1, Y - 1)
            if not (dc < 0 and dr <= 0):
                continue
            if "^V" in c or c in ("Yqd^Yx", "Yqr^Yxp"):
                put(land(X, Y), c)
    # starts with 6 docking rings, numbered clockwise from the north
    start = land(*START)
    for k, (x, y) in enumerate(six(start)):
        g[y][x] = f"{k + 1} Yk"
    for h in neighbours(*start):
        put(h, "Yc")
    # the small starbase near each start, its ring towards the centre
    small = land(*SMALL_KEEP)
    put(small, "Yk")
    put(min(neighbours(*small), key=from_centre), "Yc")
    # a small starbase on each line between two players, as far out as the
    # 4p axis keeps land (an even number of hexes, so it sits on the line),
    # with a docking ring either side of the line
    n = 2 * round(math.hypot(*forward(*uv_of(*AXIS_KEEP))) / 3)
    q, r = C[0] + n // 2, C[1] - n            # n hexes out at 30 degrees
    keep = to_offset(q, r)
    put(keep, "Yk")
    put(to_offset(q - 1, r), "Yc")
    put(to_offset(q + 1, r), "Yc")
    return g, six(start)


# ------------------------------------------------------------ write, check
def write(g, path, top=0, bottom=H - 1):
    """Write rows top to bottom of the grid."""
    rows = []
    for Y in range(bottom - top + 3):
        row = []
        for X in range(W + 2):
            x, y = X - 1, Y - 1 + top
            row.append(g[y][x] if 0 <= x < W and top <= y <= bottom else VOID)
        rows.append(", ".join(row))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")


def cost(code):
    code = code.split(" ")[-1]
    if "^V" in code:
        return 1
    return COST.get(code)


def moves(g, start):
    best, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > best[x, y]:
            continue
        for u, v in neighbours(x, y):
            if inside(u, v) and cost(g[v][u]):
                n = d + cost(g[v][u])
                if n < best.get((u, v), n + 1):
                    best[u, v] = n
                    heapq.heappush(todo, (n, (u, v)))
    return best


# ------------------------------------------------------------- the 4p cut
EXTRA_ROWS = 2       # rows kept beyond that line, on request
PLANET_MOVE = [((14, 9), (15, 10)), ((18, 4), (18, 5))]


def cut(g, starts):
    """Shave off the north and south corners: everything beyond the line
    between the middles of the two edges either side of each goes, start
    and all. The other four sixths stay whole, and so does the inner half
    of the north and south sixths (its supergiant, star and planets now
    shared). The map keeps its half turn, so the starts are alike in pairs
    across the centre; the sides are renumbered 1 to 4 clockwise from the
    northeast."""
    g = [row[:] for row in g]
    edge = abs(MA[1]) + EXTRA_ROWS * math.sqrt(3) + 1e-6
    rows = [y for y in range(H) for x in range(W)
            if inside(x, y) and abs(pixel(x, y)[1]) <= edge]
    for y in range(H):
        for x in range(W):
            if abs(pixel(x, y)[1]) > edge:
                g[y][x] = VOID
    top = min(rows)
    # docking rings left without their starbase go too
    for y in range(H):
        for x in range(W):
            if g[y][x] == "Yc" and not any(
                    inside(*h) and g[h[1]][h[0]].endswith("Yk")
                    for h in neighbours(x, y)):
                g[y][x] = "Ys"
    # two planets left from the north sixth are a move nearer the
    # northwest start than their counterparts are to the northeast: each
    # moved a hex (in-game x,y on the 6p map), and its half-turned twin
    for (X0, Y0), (X1, Y1) in PLANET_MOVE:
        a, b = (X0 - 1, Y0 - 1), (X1 - 1, Y1 - 1)
        for k in (0, 3):
            (ax, ay), (bx, by) = turn(*a, k), turn(*b, k)
            g[by][bx], g[ay][ax] = g[ay][ax], "Ys"
    kept = [starts[k] for k in (1, 2, 4, 5)]
    for n, (x, y) in enumerate(kept, 1):
        g[y][x] = f"{n} Yk"
    return g, kept, top, max(rows)


def report(g, starts, top=0):
    planets = [(x, y) for y in range(H) for x in range(W) if "^V" in g[y][x]]
    keeps = [(x, y) for y in range(H) for x in range(W)
             if g[y][x] == "Yk"]
    print(f"{len(planets)} planets, {len(keeps)} small starbases")
    ds = [moves(g, s) for s in starts]
    open_hexes = {(x, y) for y in range(H) for x in range(W)
                  if inside(x, y) and cost(g[y][x])}
    print("unreachable:", sorted((x + 1, y + 1 - top) for x, y in open_hexes - set(ds[0])) or "none")
    for s, d in zip(starts, ds):
        own = sorted(d.get(p, 99) for p in planets
                     if d.get(p, 99) < min(e.get(p, 99) for e in ds if e is not d))
        print(f"start {s[0] + 1},{s[1] + 1 - top}: own planets {own}, centre "
              f"{d.get((CX, CY))}, others {[d.get(o) for o in starts]}, "
              f"small starbases {sorted(d.get(b) for b in keeps)[:4]}")


def main(argv):
    g, starts = build(read_source(argv[1]))
    write(g, os.path.join(argv[1], "maps/6p_Media_Control.map"))
    if "-v" in argv:
        report(g, starts)
    g, starts, top, bottom = cut(g, starts)
    write(g, os.path.join(argv[1], "maps/4p_Media_Control_Hexagon.map"), top, bottom)
    if "-v" in argv:
        report(g, starts, top)


if __name__ == "__main__":
    main(sys.argv)
