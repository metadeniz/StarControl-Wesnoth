#!/usr/bin/env python3
"""Write maps/6p_Year_501.map.

Year 501: an original space map for 2 vs. 2 (or 3 vs. 3), west against
east, with three starting starbases on each side so a 2 vs. 2 game can
start from different places, and three small forward starbases a side
with one docking ring each (it began as the team version of Hegemony or
Survival, tools/make_hegemony_or_survival.py). Only the west half is laid out here; the east half is its mirror
image, hex for hex (the map is an odd number of hexes wide, so the middle
column mirrors onto itself and every hex keeps its neighbours).

Ideas taken from the mod's other maps:
- Media Control: the north-west start sits behind a river of light
  badlands with two fords out.
- Manufacturing Consent: a start on the west edge, screened by debris
  disks, and impassable clouds (dark nebula, radiation, plasma storm,
  gravity eddy) with a star, pulsar, black hole or dark star at their heart
  breaking the field into lanes.
- Understanding Power (Small): a long badland lake on the flank of the
  south-west start, and the richest planets in asteroid fields, here only
  on the side of each planet facing the centre.
- Weldyn Channel: a channel of badlands between the homes and the centre,
  crossed at a few calm (thin badlands) passages.
- Isar's Cross: a ring of light badlands round the central nebula, for
  close fighting round the middle.

Usage: make_year_501.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

from assign_planet_types import assign_file

W, H = 41, 29                 # playable hexes; Wesnoth adds a one-hex border
MID = W // 2                  # the middle column, its own mirror image

T = {".": "Ys", "n": "Yn", "r": "Yr", "d": "Yd", "B": "Yi", "b": "Yis",
     "f": "Yif", "a": "Ys^Ya", "A": "Ys^Yad", "m": "Yn^Ya", "p": "Ys^Vyp",
     "o": "Yn^Vyp", "q": "Yis^Vys", "K": "Yk", "c": "Yc", "w": "Ys^Yw",
     "x": "Ys^Yx",
     # impassable clouds, and what sits at their hearts
     "D": "Yqd", "R": "Yqr", "S": "Yqp", "E": "Yqe",
     "s": "Yqp^Yx", "u": "Yqr^Yxp", "h": "Yqe^Yxb"}
BARRIER = "wxDRSEsuhZ"        # Z: a hex of a four-hex object, see BIG

# a medium ship's moves into each terrain (README), for the balance check
COST = {".": 1, "n": 2, "r": 3, "d": 2, "B": 3, "b": 2, "f": 1, "a": 3,
        "A": 3, "m": 3, "p": 1, "o": 1, "q": 1, "K": 1, "c": 1}


def neighbours(x, y):
    up = y - 1 if x % 2 == 0 else y        # odd columns sit half a hex lower
    return [(x, y - 1), (x, y + 1), (x - 1, up), (x - 1, up + 1),
            (x + 1, up), (x + 1, up + 1)]


def cube(x, y):
    return x, y - (x - (x & 1)) // 2


def dist(a, b):
    (q1, r1), (q2, r2) = cube(*a), cube(*b)
    return max(abs(q1 - q2), abs(r1 - r2), abs((q1 + r1) - (q2 + r2)))


def from_cube(q, r):
    return q, r + (q - (q & 1)) // 2


def path(points):
    """The hexes along straight lines through points."""
    out = []
    for a, b in zip(points, points[1:]):
        n = dist(a, b)
        (q1, r1), (q2, r2) = cube(*a), cube(*b)
        for i in range(n + 1):
            t = i / n if n else 0
            q, r = q1 + (q2 - q1) * t + 1e-6, r1 + (r2 - r1) * t + 1e-6
            s = -q - r
            rq, rr, rs = round(q), round(r), round(s)
            dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
            if dq > dr and dq > ds:
                rq = -rr - rs
            elif dr > ds:
                rr = -rq - rs
            h = from_cube(rq, rr)
            if h not in out:
                out.append(h)
    return out


def mirror(x, y):
    return W - 1 - x, y


class Map:
    def __init__(self):
        self.g = [["." for _ in range(W)] for _ in range(H)]
        self.big = {}                      # (x, y) -> full terrain code

    def put(self, x, y, ch):
        """Put a hex and its mirror image."""
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = ch
            mx, my = mirror(x, y)
            self.g[my][mx] = ch

    def get(self, x, y):
        return self.g[y][x]

    def blob(self, cx, cy, r, ch, keep=""):
        for x in range(max(0, cx - r - 1), min(W, cx + r + 2)):
            for y in range(max(0, cy - r - 1), min(H, cy + r + 2)):
                if dist((x, y), (cx, cy)) <= r and self.g[y][x] not in keep:
                    self.put(x, y, ch)

    def hexes(self, pts, ch):
        for x, y in pts:
            self.put(x, y, ch)

    def big_object(self, hexes, code, under):
        """A four-hex object (supergiant, dark star, ...) on a diamond: three
        across and two down, or two by two slanting either way. code may be
        two codes, the west one and its mirror image (to show two looks)."""
        west, east = (code, code) if isinstance(code, str) else code
        for x, y in hexes:
            self.put(x, y, "Z")
            self.big[x, y] = f"{T[under]}^{west}"
            mx, my = mirror(x, y)
            self.big[mx, my] = f"{T[under]}^{east if mx != x else west}"


def diamond_across(x, y):
    """Three across and two down, the middle column x (even), rows y, y+1."""
    assert x % 2 == 0
    return [(x, y), (x, y + 1), (x - 1, y), (x + 1, y)]


def diamond_slant(x, y):
    """Two by two: x, y and x, y+1, and the two hexes east of them."""
    up = y - 1 if x % 2 == 0 else y
    return [(x, y), (x, y + 1), (x + 1, up), (x + 1, up + 1)]


def lake(m, line):
    """Badlands along line, edged with light badlands."""
    for x, y in line:
        m.put(x, y, "B")
    for x, y in line:
        for u, v in neighbours(x, y):
            if 0 <= u < W and 0 <= v < H and m.get(u, v) in ".nd":
                m.put(u, v, "b")


def keep(m, x, y, rings, skip=()):
    """A starbase with docking rings on its neighbours (rings: how many,
    skipping the neighbours in skip)."""
    m.put(x, y, "K")
    for u, v in [h for h in neighbours(x, y) if h not in skip][:rings]:
        if 0 <= u < W and 0 <= v < H:
            m.put(u, v, "c")


def build():
    m = Map()

    # ---------------------------------------------------------- nebulae
    for cx, cy, r in [(9, 1, 1), (6, 10, 1), (11, 8, 1), (16, 6, 1),
                      (8, 18, 1), (14, 11, 1), (15, 21, 1), (10, 26, 1),
                      (17, 26, 1), (3, 20, 0), (12, 4, 0), (18, 16, 0),
                      (6, 16, 0), (13, 17, 0)]:
        m.blob(cx, cy, r, "n")
    for cx, cy in [(12, 12), (5, 7), (14, 25)]:
        m.blob(cx, cy, 0, "r")                       # hot red nebula wisps

    # ---------------------------------------------------- the north-west
    # start, Media Control style: a river of light badlands round the
    # corner, two fords out
    keep(m, 4, 3, 6)
    m.hexes(path([(0, 7), (7, 7), (9, 4), (9, 0)]), "b")
    m.hexes([(3, 7), (9, 2)], "f")                   # the two fords
    m.hexes([(1, 1), (7, 1)], "p")                   # home planets
    m.blob(1, 1, 1, "a", keep="p")

    # -------------------------------------------- the west start, on the
    # edge, screened by debris disks (Manufacturing Consent)
    keep(m, 1, 14, 6)
    m.hexes([(5, 12), (5, 13), (6, 12)], "w")
    m.hexes([(5, 16), (5, 17), (6, 17)], "w")
    m.hexes([(1, 11), (1, 17), (4, 14)], "p")
    m.hexes([(0, 10), (2, 11), (0, 17), (2, 18)], "a")

    # ------------------------------------ the south-west start, by a long
    # badland lake reaching to the south edge (Understanding Power)
    keep(m, 4, 25, 6)
    lake(m, [(8, 23), (9, 24), (9, 25), (10, 26), (10, 27), (11, 28)])
    m.hexes([(9, 27)], "f")                          # a calm passage
    m.hexes([(10, 24)], "q")                         # a sea planet in it
    m.hexes([(1, 27), (6, 28), (1, 22)], "p")
    m.blob(1, 27, 1, "a", keep="pK")

    # ------------------------------------- the lanes between the homes
    # a dust lane between the north-west and west starts, a nebula one
    # between the west and south-west
    m.blob(3, 10, 1, "d", keep="bfpaK")
    m.hexes([(2, 20), (3, 21), (4, 20)], "n")

    # ----------------------------------- two badland lakes (Weldyn) in
    # front of the homes, each crossed at a calm passage, with open space
    # in front of the west start between them
    lake(m, [(10, 8), (10, 9), (11, 10), (11, 11)])
    m.hexes([(10, 9)], "f")
    m.hexes([(9, 11)], "q")
    lake(m, [(10, 17), (10, 18), (10, 19), (11, 20)])
    m.hexes([(10, 19)], "f")
    m.hexes([(9, 17)], "q")
    m.hexes([(8, 13)], "p")
    # an asteroid field with a planet north of the north lake
    m.blob(12, 5, 1, "a", keep="n")
    m.put(12, 5, "p")

    # ----------------------------------------------- the middle band
    # north: a plasma storm with a sun at its heart
    m.hexes([(13, 1), (14, 1), (14, 2), (15, 2), (13, 2), (15, 3)], "S")
    m.put(14, 2, "s")
    m.hexes([(12, 2), (16, 1)], "p")
    # a supergiant in a nebula, blue in the west and yellow in the east,
    # a planet in asteroids beside it
    m.blob(15, 8, 1, "n")
    m.big_object(diamond_slant(15, 8), ("Ysu2", "Ysu1"), "n")
    m.hexes([(13, 7)], "a")
    m.hexes([(13, 8)], "p")
    # south: a dark star in its dark nebula
    m.hexes([(14, 19), (15, 19), (16, 20), (14, 20), (13, 20)], "D")
    m.big_object(diamond_slant(14, 20), ("Yds1", "Yds3"), "D")
    m.hexes([(12, 22)], "p")
    m.hexes([(11, 22), (12, 23)], "a")
    # far south: a radiation zone round a pulsar
    m.hexes([(13, 26), (14, 27), (15, 27), (14, 28), (13, 27)], "R")
    m.put(14, 27, "u")
    m.hexes([(16, 24)], "p")
    m.blob(16, 24, 1, "a", keep="p")
    # gravity eddies with black holes, on the diagonals to the centre
    m.hexes([(16, 12), (16, 13), (17, 12)], "E")
    m.put(16, 12, "h")
    m.hexes([(16, 16), (17, 17)], "E")
    m.put(16, 16, "h")

    # ----------------------------------------------- the middle column
    # north: a supermassive black hole in a gravity eddy
    m.hexes([(19, 3), (21, 3), (20, 3), (19, 5), (20, 6), (18, 4)], "E")
    m.big_object(diamond_across(MID, 4), "Ybh2", "E")
    m.hexes([(20, 1)], "p")
    m.blob(20, 1, 1, "m", keep="pE")
    m.put(20, 1, "o")
    # a rich planet in an asteroid field on each side of the centre
    m.blob(20, 9, 1, "a")
    m.put(20, 9, "p")
    m.blob(20, 19, 1, "m")
    m.put(20, 19, "o")
    # the centre: a starbase in a nebula, ringed by light badlands
    # (Isar's Cross), with two planets
    for x in range(W):
        for y in range(H):
            if dist((x, y), (MID, 14)) == 3 and m.get(x, y) in ".n":
                m.put(x, y, "b")
    m.blob(MID, 14, 2, "n", keep="bEhZ")
    m.hexes([(MID, 14)], "K")
    m.hexes([(MID, 13), (MID, 15)], "c")
    m.hexes([(18, 14)], "p")
    m.hexes([(17, 11), (17, 17)], "f")                 # ways into the ring
    # south: a globular cluster in a radiation zone
    m.hexes([(19, 24), (21, 24), (20, 23), (20, 26), (19, 26)], "R")
    m.big_object(diamond_across(MID, 24), "Ygc", "R")
    m.hexes([(20, 28)], "p")
    m.blob(20, 28, 1, "a", keep="pR")
    # small starbases with one docking ring, three a side: in front of the
    # middle start, by the supergiant and by the dark star
    for (x, y), ring in [((7, 14), (8, 14)), ((17, 10), (18, 10)),
                         ((17, 21), (18, 21))]:
        m.put(x, y, "K")
        m.put(*ring, "c")
    half_fields(m)
    edits(m)
    return m


def edits(m):
    """D's hand edits, in Wesnoth's 1-based coordinates (each mirrored)."""
    def at(X, Y):
        return X - 1, Y - 1

    def clear(x, y):
        m.put(x, y, ".")
        for h in [(x, y), mirror(x, y)]:
            m.big.pop(h, None)
    # clear the north-west and south-west corners, from a line between two
    # hexes outwards
    for a, b, corner in [((1, 8), (15, 1), (1, 1)),
                         ((14, 29), (1, 22), (1, 29))]:
        a, b, corner = at(*a), at(*b), at(*corner)
        (ax, ay), (bx, by) = pixel(*a), pixel(*b)

        def side(h):
            hx, hy = pixel(*h)
            return (bx - ax) * (hy - ay) - (by - ay) * (hx - ax)
        out = side(corner) > 0
        for x in range(W):
            for y in range(H):
                if (side((x, y)) > 0) == out:
                    clear(x, y)
        for h in path([a, b]):
            clear(*h)
    for h in [(13, 3), (16, 3), (16, 4), (17, 2), (20, 27), (23, 5)]:
        clear(*at(*h))
    m.put(*at(18, 3), "p")
    m.put(*at(9, 16), "c")                # a second ring for the small base


def pixel(x, y):
    return 1.5 * x, math.sqrt(3) * (y + 0.5 * (x & 1))


def half_fields(m):
    """Thin each asteroid field round a planet to the half facing the
    centre: of the asteroid hexes round the planet, the half (rounded up)
    nearest the line from it to the centre stay and the rest become open
    space. The mirror keeps angles, so the east stays the west's image."""
    keep, clear = set(), set()
    cx, cy = pixel(MID, 14)
    for x in range(W):
        for y in range(H):
            if m.get(x, y) not in "poq":
                continue
            field = [(u, v) for u, v in neighbours(x, y)
                     if 0 <= u < W and 0 <= v < H and m.get(u, v) in "aAm"]
            if len(field) < 4:              # not ringed, leave it be
                continue
            px, py = pixel(x, y)
            to_c = math.atan2(cy - py, cx - px)

            def off(h):
                hx, hy = pixel(*h)
                a = math.atan2(hy - py, hx - px) - to_c
                return abs(math.atan2(math.sin(a), math.cos(a)))
            field.sort(key=off)
            n = (len(field) + 1) // 2
            if n < len(field):
                assert off(field[n]) - off(field[n - 1]) > 1e-6, (x, y)
            keep |= set(field[:n])
            clear |= set(field[n:])
    for x, y in clear - keep:
        m.g[y][x] = "."


STARTS = [(4, 3), (1, 14), (4, 25)]        # west: sides 1, 3, 5


def moves(m, start):
    best, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > best[x, y]:
            continue
        for u, v in neighbours(x, y):
            if 0 <= u < W and 0 <= v < H and m.get(u, v) not in BARRIER:
                n = d + COST[m.get(u, v)]
                if n < best.get((u, v), n + 1):
                    best[u, v] = n
                    heapq.heappush(todo, (n, (u, v)))
    return best


def write(m, path):
    side = {}
    for n, (x, y) in enumerate(STARTS):
        side[x, y] = 2 * n + 1                     # west: 1, 3, 5
        side[mirror(x, y)] = 2 * n + 2             # east: 2, 4, 6
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x = min(max(X - 1, 0), W - 1)
            y = min(max(Y - 1, 0), H - 1)
            ch = m.get(x, y)
            code = m.big.get((x, y), T.get(ch))
            if ch == "s":           # each storm's sun its own look
                code = "Yqp^Yxs3" if x < MID else "Yqp^Yxs6"
            border = (X - 1, Y - 1) != (x, y)
            if border:
                # the border shows the terrain next to it, but no
                # planets, starbases or objects
                code = {"K": "Yc", "p": "Ys", "o": "Yn", "q": "Yis"}.get(
                    ch, code)
                if "^" in code and ch not in "amA":
                    code = code.split("^")[0]
            elif (x, y) in side:
                code = f"{side[x, y]} {code}"
            row.append(code)
        rows.append(", ".join(row))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")
    assign_file(path, quiet=True)          # life, mineral and dead worlds


def report(m):
    planets = [(x, y) for y in range(H) for x in range(W)
               if m.get(x, y) in "poq"]
    print(f"{len(planets)} planets")
    open_hexes = {(x, y) for y in range(H) for x in range(W)
                  if m.get(x, y) not in BARRIER}
    cut_off = open_hexes - set(moves(m, STARTS[0]))
    print("unreachable:", sorted(cut_off) or "none")
    ds = [moves(m, s) for s in STARTS + [mirror(*s) for s in STARTS]]
    for s, d in zip(STARTS, ds):
        own = sorted(d.get(p, 99) for p in planets
                     if d.get(p, 99) == min(e.get(p, 99) for e in ds))
        print(f"start {s}: nearest planets {own}, centre {d.get((MID, 14))}")


if __name__ == "__main__":
    m = build()
    write(m, os.path.join(sys.argv[1], "maps/6p_Year_501.map"))
    report(m)
    if "-v" in sys.argv:
        for row in m.g:
            print("".join(row))
