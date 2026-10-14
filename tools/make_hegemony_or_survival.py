#!/usr/bin/env python3
"""Write maps/6p_Hegemony_or_Survival.map.

An original space map for six players on one giant hexagon of space, a
start in each of its six corners. Hex grids turn by 60 degrees exactly, so
the map has full six-way symmetry, hex for hex: one twelfth of it is laid
out here (half of the sixth between two corners) and copied by turning it
six ways and mirroring each copy. Every start has the same hex counts to
the same places. Only the looks of the impassable clouds change from one
corner to the next (they all block alike).

Ideas taken from the mod's other maps:
- Media Control: each start sits in its corner behind a bend of light
  badlands with two fords out.
- Manufacturing Consent and Media Control: impassable clouds (dark nebula,
  radiation, plasma storm, gravity eddy) with a star, pulsar or black hole
  at their heart, here a small arc of three hexes in front of each
  start, so the way to the centre bends round it.
- Understanding Power (Small): the richest planets in asteroid fields,
  here only on the side of each planet facing the centre.
- Weldyn Channel: a badland lake between each two neighbouring starts,
  crossed at a calm passage by a sea planet both want.
- Isar's Cross: a ring of light badlands round the central nebula, for
  close fighting round the middle, where a starbase waits.

Six supergiants, one of each colour and three hexes each, stand in nebulae
between neighbours, each with a small starbase (two docking rings) beside it. Six more small
starbases, also with two docking rings, wait just outside the central ring
on the line from each start to the centre, beside the start's cloud. Like
everything else they are turned six ways and mirrored, so every start
still has the same hex counts to everything. Outside the hexagon is the
void (off the map).

Usage: make_hegemony_or_survival.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

R = 18                        # the hexagon's radius in hexes, centre to corner
W = H = 2 * R + 1             # playable hexes; Wesnoth adds a one-hex border
CX, CY = R, R                 # the centre hex (an even column)

T = {".": "Ys", "n": "Yn", "r": "Yr", "d": "Yd", "B": "Yi", "b": "Yis",
     "f": "Yif", "a": "Ys^Ya", "A": "Ys^Yad", "m": "Yn^Ya", "p": "Ys^Vyp",
     "o": "Yn^Vyp", "q": "Yis^Vys", "K": "Yk", "c": "Yc", "w": "Ys^Yw",
     " ": "_off^_usr"}
# the impassable clouds, by corner: X is the cloud, O its heart. They all
# block alike, so the six-way symmetry of play holds.
FLAVOURS = [("Yqe", "Yqe^Yxb1"),      # gravity eddy round a black hole
            ("Yqp", "Yqp^Yxs4"),      # plasma storm round a big cyan sun
            ("Yqr", "Yqr^Yxp"),       # radiation zone round a pulsar
            ("Yqd", "Yqd^Yx"),        # dark nebula round a star
            ("Yqe", "Yqe^Yxb3"),      # gravity eddy round a red black hole
            ("Yqp", "Yqp^Yxs5")]      # plasma storm round a pink sun
BARRIER = "wXOZ "

# a medium ship's moves into each terrain (README), for the balance check
COST = {".": 1, "n": 2, "r": 3, "d": 2, "B": 3, "b": 2, "f": 1, "a": 3,
        "A": 3, "m": 3, "p": 1, "o": 1, "q": 1, "K": 1, "c": 1}

# the six corners, clockwise from the north (flat-topped hexes: q, r)
DIRS = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]


def to_cube(x, y):
    return x, y - (x - (x & 1)) // 2


def to_offset(q, r):
    return q, r + (q - (q & 1)) // 2


C = to_cube(CX, CY)


def dist(a, b):
    (q1, r1), (q2, r2) = to_cube(*a), to_cube(*b)
    return max(abs(q1 - q2), abs(r1 - r2), abs(q1 + r1 - q2 - r2))


def at(a, b, k=0):
    """The hex a steps towards corner k and b towards corner k+1."""
    (dq0, dr0), (dq1, dr1) = DIRS[k % 6], DIRS[(k + 1) % 6]
    return to_offset(C[0] + a * dq0 + b * dq1, C[1] + a * dr0 + b * dr1)


def images(x, y):
    """The hex and its copies under the twelve symmetries of the hexagon."""
    q, r = to_cube(x, y)
    q, r = q - C[0], r - C[1]
    s = -q - r
    out = set()
    for _ in range(6):
        q, r, s = -r, -s, -q                      # turn 60 degrees clockwise
        for mq, mr in ((q, r), (-q, -s)):         # and its mirror image
            out.add(to_offset(mq + C[0], mr + C[1]))
    return out


def neighbours(x, y):
    up = y - 1 if x % 2 == 0 else y        # odd columns sit half a hex lower
    return [(x, y - 1), (x, y + 1), (x - 1, up), (x - 1, up + 1),
            (x + 1, up), (x + 1, up + 1)]


def inside(x, y):
    return 0 <= x < W and 0 <= y < H and dist((x, y), (CX, CY)) <= R


def corner_of(x, y):
    """Which corner's sixth of the map a hex is nearest."""
    px, py = 1.5 * (x - CX), math.sqrt(3) * (y - CY + 0.5 * (x & 1))
    angle = math.degrees(math.atan2(px, -py)) % 360
    return round(angle / 60) % 6


def sixth_of(x, y):
    """Which sixth between two corners a hex lies in: 0 between corners 0
    and 1, and so on clockwise."""
    px, py = 1.5 * (x - CX), math.sqrt(3) * (y - CY + 0.5 * (x & 1))
    angle = math.degrees(math.atan2(px, -py)) % 360
    return int(angle // 60) % 6


def path(a, b):
    """The hexes on a straight line from a to b (offset coordinates)."""
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
        h = to_offset(rq, rr)
        if h not in out:
            out.append(h)
    return out


class Map:
    def __init__(self):
        self.g = [["." if inside(x, y) else " " for x in range(W)]
                  for y in range(H)]
        self.big = {}

    def get(self, x, y):
        return self.g[y][x]

    def put(self, h, ch):
        for x, y in images(*h):
            if inside(x, y):
                self.g[y][x] = ch

    def blob(self, h, r, ch, keep=""):
        for x in range(W):
            for y in range(H):
                if inside(x, y) and dist((x, y), h) <= r \
                        and self.g[y][x] not in keep:
                    self.put((x, y), ch)

    def line(self, a, b, ch):
        for h in path(a, b):
            self.put(h, ch)

    def edge(self, hexes, ch, over=".nd"):
        """Edge a set of hexes with ch."""
        for x, y in hexes:
            for u, v in neighbours(x, y):
                if inside(u, v) and self.g[v][u] in over:
                    self.put((u, v), ch)


def build():
    m = Map()
    # (a, b): a steps towards a corner, b towards the next one; a >= b

    # ------------------------------------------------- scattered nebulae
    for h, r in [((5, 2), 1), ((13, 4), 1), ((9, 6), 1), ((3, 6), 0),
                 ((15, 2), 0), ((10, 0), 0)]:
        m.blob(at(*h), r, "n")
    m.blob(at(7, 3), 0, "r")                         # a wisp of hot nebula
    m.blob(at(12, 5), 1, "d")                        # a dust cloud

    # ------------------------------------------- the start in each corner
    keep = at(15, 0)
    m.put(keep, "K")
    for h in neighbours(*keep):
        m.put(h, "c")
    # home planets, one in an asteroid field by the corner
    m.blob(at(16, 2), 1, "a", keep="Kc")
    m.put(at(16, 2), "p")
    m.put(at(12, 1), "p")
    # the bend of light badlands round the corner, two fords out
    m.line(at(11, 0), at(11, 7), "b")
    m.put(at(11, 3), "f")

    # ------------------------------ between two neighbours: a badland lake
    # with a sea planet at its calm passage
    lake = path(at(7, 8), at(9, 9))
    for h in lake:
        m.put(h, "B")
    m.edge([g for h in lake for g in images(*h)], "b")
    m.put(at(8, 8), "q")
    # a supergiant in a nebula, nearer the centre, each its own colour:
    # yellow, blue, red, white, green, orange (^Ytu1..6), clockwise. It
    # fills a triangle of three hexes that the mirror through the middle of
    # the sixth maps onto itself, pointing in towards the centre.
    m.blob(at(5, 5), 1, "n")
    for h in [at(5, 5), at(4, 5), at(5, 4)]:
        for x, y in images(*h):
            m.g[y][x] = "Z"
            m.big[x, y] = f"{T['n']}^Ytu{sixth_of(x, y) + 1}"
    # and a small starbase beside it, two docking rings (a mirror pair, as
    # one ring cannot sit on the mirror line)
    m.put(at(6, 6), "K")
    m.put(at(5, 6), "c")

    # -------------------------------- rich planets in asteroid fields
    m.blob(at(9, 3), 1, "a", keep="bfn")
    m.put(at(9, 3), "p")

    # ---------------- an impassable cloud in front of each start: three
    # hexes in an arc across the way to the centre, its heart in the middle
    m.put(at(6, 1), "X")
    m.put(at(7, 0), "O")

    # ---------------------------------------------------------- the centre
    for x in range(W):
        for y in range(H):
            d = dist((x, y), (CX, CY))
            if d == 4:
                m.put((x, y), "b")
            elif d == 2:
                m.put((x, y), "n")
    m.put(at(2, 2), "f")                             # ways into the ring
    m.put(at(3, 0), "o")                             # its six planets
    m.put((CX, CY), "K")
    for h in neighbours(CX, CY):
        m.put(h, "c")
    # a small starbase in front of each start, just outside the ring and
    # beside the start's cloud, with two docking rings (a mirror pair)
    m.put(at(5, 0), "K")
    m.put(at(4, 1), "c")
    half_fields(m)
    return m


def pixel(x, y):
    return 1.5 * x, math.sqrt(3) * (y + 0.5 * (x & 1))


def half_fields(m):
    """Thin each asteroid field round a planet to the half facing the
    centre: of the asteroid hexes round the planet, the half (rounded up)
    nearest the line from it to the centre stay and the rest become open
    space. Turns and mirrors keep angles, so every corner stays alike."""
    keep, clear = set(), set()
    cx, cy = pixel(CX, CY)
    for x in range(W):
        for y in range(H):
            if not inside(x, y) or m.get(x, y) not in "poq":
                continue
            field = [h for h in neighbours(x, y)
                     if inside(*h) and m.get(*h) in "aAm"]
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


def keeps():
    return [at(15, 0, k) for k in range(6)]


def moves(m, start):
    best, todo = {start: 0}, [(0, start)]
    while todo:
        d, (x, y) = heapq.heappop(todo)
        if d > best[x, y]:
            continue
        for u, v in neighbours(x, y):
            if inside(u, v) and m.get(u, v) not in BARRIER:
                n = d + COST[m.get(u, v)]
                if n < best.get((u, v), n + 1):
                    best[u, v] = n
                    heapq.heappush(todo, (n, (u, v)))
    return best


def code(m, x, y):
    ch = m.get(x, y)
    if (x, y) in m.big:
        return m.big[x, y]
    if ch in "XO":
        cloud, heart = FLAVOURS[corner_of(x, y)]
        return cloud if ch == "X" else heart
    return T[ch]


def write(m, path_):
    side = {k: n + 1 for n, k in enumerate(keeps())}   # clockwise from north
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x, y = X - 1, Y - 1
            if not (0 <= x < W and 0 <= y < H) or not inside(x, y):
                row.append(T[" "])
                continue
            c = code(m, x, y)
            if (x, y) in side:
                c = f"{side[x, y]} {c}"
            row.append(c)
        rows.append(", ".join(row))
    with open(path_, "w") as f:
        f.write("\n".join(rows) + "\n")


def report(m):
    planets = [(x, y) for y in range(H) for x in range(W)
               if m.get(x, y) in "poq"]
    print(f"{len(planets)} planets")
    ks = keeps()
    ds = [moves(m, k) for k in ks]
    small = [(x, y) for y in range(H) for x in range(W)
             if m.get(x, y) == "K" and (x, y) not in ks and (x, y) != (CX, CY)]
    print(f"{len(small)} small starbases")
    open_hexes = {(x, y) for y in range(H) for x in range(W)
                  if inside(x, y) and m.get(x, y) not in BARRIER}
    print("unreachable:", sorted(open_hexes - set(ds[0])) or "none")
    for k, d in zip(ks, ds):
        own = sorted(d.get(p, 99) for p in planets
                     if d.get(p, 99) == min(e.get(p, 99) for e in ds))
        print(f"start {k[0] + 1},{k[1] + 1}: nearest planets {own}, "
              f"centre {d.get((CX, CY))}, neighbours "
              f"{sorted(d.get(o) for o in ks if o != k)}, small starbases "
              f"{sorted(d.get(b) for b in small)}")


if __name__ == "__main__":
    m = build()
    write(m, os.path.join(sys.argv[1], "maps/6p_Hegemony_or_Survival.map"))
    report(m)
    if "-v" in sys.argv:
        for row in m.g:
            print("".join(row))
