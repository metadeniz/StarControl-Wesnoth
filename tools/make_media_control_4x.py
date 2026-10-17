#!/usr/bin/env python3
"""Write maps/4p_Media_Control.map, turned four ways as nearly as hexes allow.

make_media_control.py traces the north-west quarter of the screenshot; this
script builds the whole map from that trace on a 37 x 37 map:

- The south half is the north half turned 180 degrees, which is exact on
  hexes.
- The north-east quarter is the north-west quarter turned a quarter of the
  way round. A hex grid can't be turned by 90 degrees exactly, so within 9
  hexes of the centre each hex goes a quarter of the way round its own ring
  (it stays as many hexes from the centre), and further out it goes to the
  nearest hex, counting a column across and a row down as one move each.
- The starts, keeps, planets, stars and objects are put back on top of the
  turned terrain, each on the turned hex as many hexes from the centre as
  the original. The north-east planets, keep and start, and a few nebula
  hexes, were then moved by tools/balance_media_control.py so each player
  is as many moves from the centre, from each other, from their own
  planets and keeps and from their rivals' as the others are (BALANCE).
- On request: walls kept 2 hexes off the edges, so any lane round the
  outside is at least 2 hexes wide; no rock walls; a 3-hex star with rocks
  floating in front of it (a debris disk, a different colour on each side)
  and 2 hexes of debris disk before it on each side; a small keep near each
  start; no planet 4 hexes from a start; the hexes in CLEAR, SOURCE_CLEAR,
  FINAL_CLEAR and FINAL_SWAP cleared or swapped.

Players are 1 north-west, 2 north-east, 3 south-east, 4 south-west.

Also writes maps/default-terrain/4p_Media_Control.map: the same map in
default Wesnoth terrain.

Usage: make_media_control_4x.py <add-on dir> [-v]
"""
import heapq
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_media_control as M

N = 37
M.W = M.H = N
M.CX = M.CY = 18
M.MID = M.centre(18, 18)
W = H = N
CX = CY = 18
# the trace in moves: 547 px across the screenshot's half = 18 columns,
# 539 px down = 18 rows
KX = 18 * M.HX / 547
KY = 18 * 72 / 539


def to_map(sx, sy, turn=0):
    dx, dy = sx - M.SX, sy - M.SY
    for _ in range(turn):
        dx, dy = -dy, dx
    return M.MID[0] + dx * KX, M.MID[1] + dy * KY


def to_shot(mx, my, turn=0):
    dx, dy = (mx - M.MID[0]) / KX, (my - M.MID[1]) / KY
    for _ in range(turn):
        dx, dy = dy, -dx
    return M.SX + dx, M.SY + dy


M.to_map, M.to_shot = to_map, to_shot
M.MOVED_KEEPS = {}
M.RIVER = [(-150, 192)] + M.RIVER + [(218, -150)]   # the river runs off the bigger map
M.T["#"] = M.WESNOTH["#"] = "Xv"                      # the hexes off the map's bottom edge
M.WESNOTH.update({ch: "Md^Xm" for ch in "!@$%"})

def axial(x, y):
    return x - CX, (y - (x - (x & 1)) // 2) - (CY - CX // 2)
def from_axial(q, r):
    x = q + CX
    return x, r + (CY - CX // 2) + (x - (x & 1)) // 2
DIRS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]   # walk from N corner clockwise
def ring_index(x, y):
    q, r = axial(x, y); s = -q - r
    k = max(abs(q), abs(r), abs(s))
    if k == 0: return 0, 0
    cq, cr = 0, -k
    for side, (dq, dr) in enumerate(DIRS):
        for step in range(k):
            if (cq, cr) == (q, r): return k, side * k + step
            cq += dq; cr += dr
    raise ValueError
def ring_hex(k, i):
    if k == 0: return CX, CY
    i %= 6 * k
    side, step = divmod(i, k)
    cq, cr = 0, -k
    for s in range(side):
        cq += DIRS[s][0] * k; cr += DIRS[s][1] * k
    return from_axial(cq + DIRS[side][0] * step, cr + DIRS[side][1] * step)
def inside(x, y): return 0 <= x < W and 0 <= y < H and not (x % 2 and y == H - 1)
def rot180(x, y): return (W - 1 - x, H - 1 - y if x % 2 == 0 else H - 2 - y)
# ---- quarter turns in "move space": a column across and a row down both
# count as one move, so the map is a square 37 x 37 and the turn takes the
# north edge onto the east edge exactly
def ms(x, y):
    return x - CX, ((2 * y + (x & 1)) - 2 * CY) / 2
def quad(x, y):
    dc, dr = ms(x, y)
    if (dc, dr) == (0, 0): return "C"
    if rot180(x, y) == (x, y): return "C"
    if dc < 0 and dr <= 0: return "NW"
    if dc >= 0 and dr < 0: return "NE"
    if dc > 0 and dr >= 0: return "SE"
    return "SW"
def nearest_in(dc, dr, want):
    best = None
    for x in range(W):
        for y in range(H):
            if inside(x, y) and quad(x, y) == want:
                c, r = ms(x, y)
                d = (c - dc) ** 2 + (r - dr) ** 2
                if best is None or d < best[0] - 1e-9 or (abs(d - best[0]) < 1e-9 and (x, y) < best[1]):
                    best = (d, (x, y))
    return best[1]
_src = {}
INNER = 9            # rings up to this many hexes out turn round their ring
def source2(x, y):
    if (x, y) in _src: return _src[x, y]
    q = quad(x, y); h = (x, y)
    if q in ("SE", "SW"):
        h = rot180(x, y); q = quad(*h)
    k, i = ring_index(*h)
    if q == "NE" and 0 < k <= INNER:
        j = i - 1.5 * k
        for jj in sorted({math.floor(j), math.ceil(j)}, key=lambda v: abs(v - j - 0.01)):
            c = ring_hex(k, jj)
            if quad(*c) == "NW":
                h = c; break
        else:
            h = nearest_in(ms(*h)[1], -ms(*h)[0], "NW")
        _src[x, y] = h
        return h
    if q == "NE":
        dc, dr = ms(*h)
        h = nearest_in(dr, -dc, "NW")
    _src[x, y] = h
    return h

# ---- rebuild: terrain by mapping, structures re-placed on top
STRUCT_BASE = {"K": ".", "c": ".", "C": ".", "p": ".", "q": "B", "G": "D",
               "S": "D", "U": "R", "X": "E"}
def rot_cw(x, y):
    """The north-east hex nearest to a north-west hex turned a quarter."""
    dc, dr = ms(x, y)
    return nearest_in(-dr, dc, "NE")
def rot_ring(x, y):
    """Like rot_cw, but as many hexes from the centre as the original."""
    k = ring_index(x, y)[0]
    dc, dr = ms(x, y)
    tc, tr = -dr, dc
    cands = [(u, v) for u in range(W) for v in range(H) if inside(u, v) and quad(u, v) == "NE"
             and ring_index(u, v)[0] == k]
    return min(cands, key=lambda h: ((ms(*h)[0] - tc) ** 2 + (ms(*h)[1] - tr) ** 2, h))
def four(h):
    ne = rot_ring(*h)
    return [h, ne, rot180(*h), rot180(*ne)]
EDGE = 2
CLEAR = [(35, 19), (35, 20), (35, 21), (21, 35), (17, 34), (17, 35), (18, 34), (18, 35), (19, 35), (16, 35)]
SMALL_KEEP = (7, 13)        # in-game 8,14
# the corner planet would be 4 hexes from the start, which lets a Precursor
# ship but not a starbase reach it: one hex nearer
PLANET_MOVE = {(3, 0): (3, 1),
               (11, 0): (10, 1)}   # off the north edge, on request (in-game 12,1 -> 11,2)
# north-east planets placed by hand, kept out of the balancing: in-game 37,13 -> 36,12
FIXED_NE = {(10, 1): (35, 11)}
# in-game x,y; each is cleared on all four sides
SOURCE_CLEAR = [(6, 13), (6, 23), (7, 24), (8, 24), (7, 25), (8, 25), (14, 6), (13, 8)]
FINAL_CLEAR = [(16, 34), (22, 3), (3, 16), (3, 21), (35, 22), (35, 17)]
FINAL_SWAP = [((34, 22), (33, 23)), ((5, 15), (4, 15))]
STAR = (9, 9)          # in-game 10,10: a 3-hex supergiant, rocks in front
def nw_rep(h):
    """The north-west hex that h is a turned copy of."""
    if quad(*h) in ("SE", "SW"): h = rot180(*h)
    if quad(*h) == "NE":
        dc, dr = ms(*h)
        h = nearest_in(dr, -dc, "NW")
    return h
def triangles_at(h):
    nb = [n for n in M.neighbours(*h)]
    out = []
    for a in nb:
        for b in nb:
            if a < b and b in M.neighbours(*a):
                out.append(tuple(sorted([h, a, b])))
    return out
# the 3-hex star with rocks floating in front of it (a 3-hex debris disk)
# north-west blue, north-east green, south-east orange, south-west red
for _ch, _n in zip("!@$%", (5, 6, 2, 1)):
    M.T[_ch] = f"Ys^Ytd{_n}"
M.BARRIER += "!@$%"
def rebuild():
    g, keeps = M.build()
    nw = [(x, y) for x in range(W) for y in range(H) if inside(x, y) and quad(x, y) == "NW"]
    # walls two hexes off the edges, so any outer lane is at least 2 wide
    for x, y in nw:
        if g[y][x] in M.BARRIER and (min(x, W - 1 - x) < EDGE or min(y, H - 1 - y) < EDGE):
            g[y][x] = "."
    # on request: no more rock walls anywhere (a 3-hex star with rocks in
    # front takes their place, see assemble), and some hexes cleared
    for x, y in nw:
        if g[y][x] == "w": g[y][x] = "."
    for X, Y in SOURCE_CLEAR:
        u, v = nw_rep((X - 1, Y - 1))
        if g[v][u] not in "KcSUXG": g[v][u] = "."   # the stars stay
    start = [k for k in keeps if quad(*k) == "NW"][0]
    small = [h for h in nw if g[h[1]][h[0]] == "K" and h != start]
    # as asked before, each player's small keep sits near their own base,
    # not by the axis (where the next player's turned planet lands)
    for h in small:
        g[h[1]][h[0]] = "."
        for n in M.neighbours(*h):
            if inside(*n) and g[n[1]][n[0]] == "c": g[n[1]][n[0]] = "."
    small = [SMALL_KEEP]
    planets = [(PLANET_MOVE.get(h, h), g[h[1]][h[0]]) for h in nw if g[h[1]][h[0]] in "pq"]
    objects = [(h, g[h[1]][h[0]]) for h in nw if g[h[1]][h[0]] in "SUX"]
    giants = [h for h in nw if g[h[1]][h[0]] == "G"]
    base = [[STRUCT_BASE.get(c, c) for c in row] for row in g]
    out = [["#" if not inside(x, y) else (lambda s: base[s[1]][s[0]])(source2(x, y))
            for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(W):
            if out[y][x] in M.BARRIER and (min(x, W - 1 - x) < EDGE or min(y, H - 1 - y) < EDGE):
                out[y][x] = "."
    info = dict(start=start, small=small, planets=planets, objects=objects, giants=giants)
    return out, info

def diamond(x, y):
    up = y - 1 if x % 2 == 0 else y
    return [(x, y), (x, y + 1), (x + 1, up), (x + 1, up + 1)]
def centroid(hs):
    pts = [ms(*h) for h in hs]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
def ring_toward_centre(k):
    return min(M.neighbours(*k), key=lambda h: sum(v * v for v in ms(*h)))
def put_keep(g, k, rings):
    g[k[1]][k[0]] = "K"
    nb = sorted([h for h in M.neighbours(*k) if inside(*h)], key=lambda h: sum(v * v for v in ms(*h)))
    if rings == 6:
        for h in nb[1:]: g[h[1]][h[0]] = "c"
        g[nb[0][1]][nb[0][0]] = "C"
    else:
        for h in nb[:rings]: g[h[1]][h[0]] = "c"
_base = None
def assemble(planet_override=None, flips=None, small_override=None, start_override=None, nw_override=None):
    global _base
    planet_override = planet_override or {}
    if _base is None: _base = rebuild()
    g = [r[:] for r in _base[0]]; info = _base[1]
    for (x, y), ch in (flips or {}).items():
        for u, v in ((x, y), rot180(x, y)):
            g[v][u] = ch
    pairs = []
    # dark stars
    gc = centroid(info["giants"])
    dc, dr = gc
    best = min(((x, y) for x in range(W - 1) for y in range(1, H - 1)
                if all(inside(*h) and quad(*h) == "NE" for h in diamond(x, y))),
               key=lambda h: (centroid(diamond(*h))[0] + dr) ** 2 + (centroid(diamond(*h))[1] - dc) ** 2)
    for d in (info["giants"], diamond(*best)):
        for h in d + [rot180(*v) for v in d]:
            g[h[1]][h[0]] = "G"
    for h, ch in info["objects"]:
        for v in four(h): g[v[1]][v[0]] = ch
    # the 3-hex supergiants: one triangle of hexes pointing at the centre
    # on each side, each its own colour, with two hexes of rocks in front
    tri = max(triangles_at(STAR), key=lambda t: -sum(sum(v * v for v in ms(*h)) for h in t))
    cx, cy = centroid(tri)
    cands = {t for x in range(W) for y in range(H) if inside(x, y) and quad(x, y) == "NE"
             for t in triangles_at((x, y)) if all(inside(*h) for h in t)}
    tne = min(cands, key=lambda t: ((centroid(t)[0] + cy) ** 2 + (centroid(t)[1] - cx) ** 2, t))
    for n, t in enumerate([tri, tne, tuple(rot180(*h) for h in tri), tuple(rot180(*h) for h in tne)], 1):
        for h in t: g[h[1]][h[0]] = "!@$%"[n - 1]
        # and two hexes of debris disk beside it, on the side facing the centre
        front = sorted({m for h in t for m in M.neighbours(*h) if inside(*m) and m not in t},
                       key=lambda m: sum(v * v for v in ms(*m)))[:2]
        for m in front: g[m[1]][m[0]] = "w"

    keeps = four(info["start"])
    if start_override:
        keeps = [keeps[0], start_override, keeps[2], rot180(*start_override)]
    for k in keeps: put_keep(g, k, 6)
    for s in info["small"]:
        ne = (small_override or {}).get(s, rot_ring(*s))
        for v in (s, ne, rot180(*s), rot180(*ne)): put_keep(g, v, 1)
    for h0, ch in info["planets"]:
        h = (nw_override or {}).get(h0, h0)
        ne = FIXED_NE.get(h0) or planet_override.get(h0, rot_ring(*h))
        for v in (h, ne, rot180(*h), rot180(*ne)): g[v[1]][v[0]] = ch
        pairs.append((h, ne, ch, h0))
    # the centre: a planet in a moat, and a keep with 2 rings on each axis
    g[CY][CX] = "p"
    for h in M.neighbours(CX, CY): g[h[1]][h[0]] = "r"
    for k, rs in (((14, 18), [(14, 17), (14, 19)]), ((18, 14), [(17, 14), (19, 14)])):
        for kk, rr in ((k, rs), (rot180(*k), [rot180(*r) for r in rs])):
            g[kk[1]][kk[0]] = "K"
            for r in rr: g[r[1]][r[0]] = "c"
    # cleared on request (in-game x,y), each with its half-turned twin; the
    # east and south ones are the turned copies of the west and north ones
    for X, Y in CLEAR + SOURCE_CLEAR:
        for u, v in ((X - 1, Y - 1), rot180(X - 1, Y - 1)):
            if g[v][u] in M.BARRIER + "n.": g[v][u] = "."
    # hexes named one by one on request (in-game x,y), as given
    for X, Y in FINAL_CLEAR:
        g[Y - 1][X - 1] = "."
    for (X0, Y0), (X1, Y1) in FINAL_SWAP:
        g[Y0 - 1][X0 - 1], g[Y1 - 1][X1 - 1] = g[Y1 - 1][X1 - 1], g[Y0 - 1][X0 - 1]
    return g, keeps, pairs, info

def moves(g, start):
    dist, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > dist[x, y]: continue
        for u, v in M.neighbours(x, y):
            if inside(u, v) and g[v][u] not in M.BARRIER + "#1234JLNQ":
                n = d + M.COST[g[v][u]]
                if n < dist.get((u, v), n + 1):
                    dist[u, v] = n; heapq.heappush(todo, (n, (u, v)))
    return dist
def write(g, keeps, path, pairs=(), table=M.T, base_only=("Yk", "Ys^Vyp")):
    gg = M.number_dark_stars([r[:] for r in g])
    holes = sorted((y, x) for y, r in enumerate(gg) for x, c in enumerate(r) if c == "X")
    for n, (y, x) in enumerate(holes, 1): gg[y][x] = str(n)
    M.write(gg, keeps, path, table, base_only)
    # the type script follows the exact half turn only: give each
    # north-east planet (and its half-turned twin) its north-west twin's type
    rows = [[c.strip() for c in r.split(",")] for r in open(path).read().splitlines() if r.strip()]
    def cell(h): return rows[h[1] + 1][h[0] + 1]
    for h, ne, ch, *_ in pairs:
        t = cell(h).split("^")[-1]
        for v in (ne, rot180(*ne)):
            c = cell(v); rows[v[1] + 1][v[0] + 1] = c.rsplit("^", 1)[0] + "^" + t
    with open(path, "w") as f:
        f.write("\n".join(", ".join(r) for r in rows) + "\n")
def report(g, keeps):
    D = [moves(g, k) for k in keeps]
    print("keeps", [(x + 1, y + 1) for x, y in keeps])
    for a in range(4): print(" P%d" % (a + 1), [D[a].get(k) for k in keeps], "centre", D[a].get((CX, CY)))
    pl = [(x, y) for y in range(H) for x in range(W) if g[y][x] in "pq"]
    for a in range(4):
        own = sorted(D[a].get(p, 99) for p in pl if D[a].get(p, 99) < min(D[b].get(p, 99) for b in range(4) if b != a))
        tie = sorted(D[a].get(p, 99) for p in pl if D[a].get(p, 99) == min(D[b].get(p, 99) for b in range(4) if b != a))
        print(" P%d own" % (a + 1), own, "tied", tie)
    ks = [(x, y) for y in range(H) for x in range(W) if g[y][x] == "K" and (x, y) not in keeps]
    for a in range(4):
        print(" P%d keeps" % (a + 1), sorted(D[a].get(k, 99) for k in ks)[:4])
    return D

def vec(D, h):
    return [D[a].get(h, 99) for a in range(4)]
def balance(rounds=3, radius=2):
    """Pick each north-east planet's hex so it is as far from each player
    as its north-west twin is from the player a quarter turn back."""
    over = {}
    for _ in range(rounds):
        g, keeps, pairs, info = assemble(over)
        D = [moves(g, k) for k in keeps]
        for h, ne, ch, h0 in pairs:
            d = vec(D, h)
            want = [d[3], d[0], d[1], d[2]]        # from P1..P4
            start = rot_ring(*h)
            cands = {start}
            frontier = {start}
            for _ in range(radius):
                frontier = {n for f in frontier for n in M.neighbours(*f) if inside(*n)}
                cands |= frontier
            def score(c):
                v = vec(D, c)
                own = abs(v[1] - want[1])
                rest = sorted(abs(v[a] - want[a]) for a in (0, 2, 3))
                return (own + sum(rest), own, sum(abs(a - b) for a, b in zip(ms(*c), ms(*start))))
            ok = [c for c in cands if quad(*c) == "NE" and (g[c[1]][c[0]] in ".an" or c == ne)]
            over[h0] = min(ok, key=score)
    return over


# found by tools/balance_media_control.py (written out by its last line):
# the north-east hex of each planet ({north-west hex: north-east hex}),
# nebula hexes flipped in the north-east and their half-turned twins, the
# north-east small keep and start, and north-west planets moved a hex
BALANCE = {"over": [[[1, 9], [25, 4]], [[3, 1], [34, 3]], [[4, 18], [18, 5]], [[10, 1], [36, 8]], [[16, 12], [24, 16]]], "flips": [[[32, 13], "n"], [[20, 14], "n"], [[20, 10], "n"], [[24, 6], "n"], [[18, 12], "n"], [[20, 13], "n"], [[27, 17], "n"]], "small": [[[7, 13], [21, 8]]], "start": None, "nwo": [[[16, 12], [15, 12]], [[4, 18], [3, 17]]]}


def balanced():
    b = BALANCE
    return assemble({tuple(k): tuple(v) for k, v in b.get("over", [])},
                    {tuple(k): v for k, v in b.get("flips", [])},
                    {tuple(k): tuple(v) for k, v in b.get("small", [])},
                    tuple(b["start"]) if b.get("start") else None,
                    {tuple(k): tuple(v) for k, v in b.get("nwo", [])})


def main(argv):
    g, keeps, pairs, info = balanced()
    write(g, keeps, os.path.join(argv[1], "maps/4p_Media_Control.map"), pairs)
    write(g, keeps, os.path.join(argv[1], "maps/default-terrain/4p_Media_Control.map"), pairs,
          M.WESNOTH, ("Kh", "Gg^Vh"))
    if "-v" in argv:
        report(g, keeps)
        for row in g:
            print("".join(row))


if __name__ == "__main__":
    main(sys.argv)
