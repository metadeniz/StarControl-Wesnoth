#!/usr/bin/env python3
"""Write maps/2p_Necessary_Illusions.map.

Necessary Illusions: a small original 1 vs. 1 space map, west against
east, about half the hexes of Isar's Cross. Only the west half is laid
out here; the east half is its mirror image, hex for hex (the map is an
odd number of hexes wide, so the middle column mirrors onto itself and
every hex keeps its neighbours).

Ideas taken from the mod's other maps:
- Media Control: the start sits behind a bend of light badlands with two
  fords out.
- Hegemony or Survival: a small arc of three impassable hexes (a plasma
  storm with a sun at its heart) in front of the start, so the way to the
  centre bends round it.
- Understanding Power (Small): the richest planets in asteroid fields, only
  on the side of each planet facing the centre.
- Isar's Cross: a ring of light badlands round the central nebula, for
  close fighting round the middle.
- Manufacturing Consent: a small starbase with one docking ring on each
  side, out on the flank.

Usage: make_necessary_illusions.py <add-on dir> [-v]
"""

import heapq
import math
import os
import sys

from assign_planet_types import assign_file

W, H = 17, 11                 # playable hexes; Wesnoth adds a one-hex border
MID = W // 2                  # the middle column, its own mirror image
CY = H // 2                   # the centre row

T = {".": "Ys", "n": "Yn", "r": "Yr", "d": "Yd", "B": "Yi", "b": "Yis",
     "f": "Yif", "a": "Ys^Ya", "A": "Ys^Yad", "m": "Yn^Ya", "p": "Ys^Vyp",
     "o": "Yn^Vyp", "q": "Yis^Vys", "K": "Yk", "c": "Yc", "w": "Ys^Yw",
     # impassable clouds, and what sits at their hearts
     "D": "Yqd", "R": "Yqr", "S": "Yqp", "E": "Yqe",
     "s": "Yqp^Yx", "u": "Yqr^Yxp", "h": "Yqe^Yxb"}
BARRIER = "wDRSEsuh"

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


def mirror(x, y):
    return W - 1 - x, y


class Map:
    def __init__(self):
        self.g = [["." for _ in range(W)] for _ in range(H)]

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


START = (1, CY)                            # west: side 1, east: side 2


def build():
    m = Map()

    # ---------------------------------------------------------- nebulae
    for cx, cy, r in [(3, 0, 1), (3, 10, 0), (2, 9, 0), (6, 2, 0),
                      (6, 8, 0), (5, 2, 0), (4, 7, 0)]:
        m.blob(cx, cy, r, "n")
    m.hexes([(5, 10)], "r")                          # a hot red wisp
    m.hexes([(0, 0), (1, 0), (2, 1), (2, 2)], "d")   # a dust lane north

    # -------------------- the start, Media Control style: a bend of light
    # badlands two hexes out, with a ford north-east and south-east
    m.put(*START, "K")
    for h in [(1, CY - 1), (1, CY + 1), (2, CY), (2, CY + 1)]:
        m.put(*h, "c")
    for x in range(W):
        for y in range(H):
            if dist((x, y), START) == 2 and x >= 2:
                m.put(x, y, "b")
    m.hexes([(3, 3), (3, 6)], "f")                   # the two fords
    m.hexes([(0, 2), (0, 8)], "p")                   # home planets

    # -------------------- a plasma storm round a sun in front of the start
    # (Hegemony or Survival): the way to the centre bends round it
    m.hexes([(5, 4), (5, 5), (4, 4)], "S")
    m.put(5, 5, "s")

    # ------------------------ the flanks: a rich planet in an asteroid
    # field (Understanding Power), a small starbase with one docking ring
    # (Manufacturing Consent)
    m.blob(4, 1, 1, "a")
    m.put(4, 1, "p")
    m.blob(4, 9, 1, "a")
    m.put(4, 9, "p")

    # ------------------------------------------------ the middle column
    # the centre: a planet in a nebula, ringed by light badlands (Isar's
    # Cross), crossed by thin badlands west and east
    for x in range(W):
        for y in range(H):
            if dist((x, y), (MID, CY)) == 2:
                m.put(x, y, "b")
    m.blob(MID, CY, 1, "n")
    m.put(MID, CY, "o")
    m.hexes([(6, 4), (6, 5)], "f")                   # ways into the ring
    # north and south: a planet in dense asteroids
    m.put(MID, 1, "p")
    m.hexes([(MID, 0), (MID - 1, 0), (MID - 1, 1)], "A")
    m.put(MID, 9, "p")
    m.hexes([(MID, 10), (MID - 1, 9), (MID - 1, 10)], "A")
    # the small starbase on the south flank, just outside the ring
    m.put(6, 7, "K")
    m.put(7, 7, "c")
    half_fields(m)
    return m


def pixel(x, y):
    return 1.5 * x, math.sqrt(3) * (y + 0.5 * (x & 1))


def half_fields(m):
    """Thin each asteroid field round a planet to the half facing the
    centre (as on Hegemony or Survival): of the asteroid hexes round the planet, the
    half (rounded up) nearest the line from it to the centre stay and the
    rest become open space."""
    keep, clear = set(), set()
    cx, cy = pixel(MID, CY)
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
            keep |= set(field[:n])
            clear |= set(field[n:])
    for x, y in clear - keep:
        m.g[y][x] = "."


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
    side = {START: 1, mirror(*START): 2}
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x = min(max(X - 1, 0), W - 1)
            y = min(max(Y - 1, 0), H - 1)
            ch = m.get(x, y)
            code = T[ch]
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
    print(f"{len(planets)} planets, {W * H} hexes")
    open_hexes = {(x, y) for y in range(H) for x in range(W)
                  if m.get(x, y) not in BARRIER}
    cut_off = open_hexes - set(moves(m, START))
    print("unreachable:", sorted(cut_off) or "none")
    west, east = moves(m, START), moves(m, mirror(*START))
    own = sorted(west[p] for p in planets if west[p] < east[p])
    print(f"west start: own planets {own}, centre {west[MID, CY]}, "
          f"enemy start {west[mirror(*START)]}")


if __name__ == "__main__":
    m = build()
    write(m, os.path.join(sys.argv[1], "maps/2p_Necessary_Illusions.map"))
    report(m)
    if "-v" in sys.argv:
        for row in m.g:
            print("".join(row))
