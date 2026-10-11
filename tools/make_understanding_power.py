#!/usr/bin/env python3
"""Write maps/2p_Understanding_Power.map.

Traced hex by hex from a screenshot of a 2-player ground map: rivers became
light badlands (thin badlands where roads forded them), one ridge a swamp
line of light badlands, lakes badlands
ringed by dust, cliffs asteroid walls, woods nebulae, ore fields asteroid
fields with a planet at each mine, gem patches asteroid fields, buildings
planets. Only the north half (rows 0-13) is drawn; the south half is the
north half turned 180 degrees, so both players get exactly the same map.

Also writes maps/default-terrain/2p_Understanding_Power.map: the same map
in default Wesnoth terrain (grass, woods, hills, impassable ridges, shallow
water, villages), for the editor or a non-space game.

Usage: make_understanding_power.py <add-on dir>
"""

import os
import sys

W, H = 38, 28            # playable hexes; Wesnoth adds a one-hex border

T = {".": "Ys", "s": "Yis", "n": "Yn", "d": "Yd", "r": "Yd", "B": "Yi", "l": "Yis", "f": "Yif",
     "a": "Ys^Ya", "w": "Ys^Yw", "p": "Ys^Vyp", "K": "Yk", "c": "Yc", "k": "Yk", "h": "Yc"}

# The same map in default Wesnoth terrain, closer to the original screenshot
WESNOTH = {".": "Gg", "s": "Ss", "n": "Gs^Fp", "d": "Ds", "r": "Re", "B": "Ww",
           "l": "Ww", "f": "Wwf", "a": "Hh", "w": "Md^Xm", "p": "Gg^Vh",
           "K": "Kh", "c": "Ch", "k": "Khw", "h": "Chw"}
LEAFY = "Gg^Fds"                 # every third wood hex is deciduous

FEATURES = {
    # river across the north-west, fords where roads crossed it
    "l": [(0, 6), (2, 6), (3, 5), (4, 5), (6, 5), (7, 5), (8, 5), (10, 5),
          (11, 5), (11, 4), (12, 4), (13, 4), (14, 4), (15, 3), (16, 3),
          (16, 2), (17, 1), (17, 0),
          (25, 0), (25, 1), (25, 2)],               # stream into the pond
    "f": [(1, 5), (5, 5), (9, 5)],
    # swamp line where the original had a ridge by the gem field
    "s": [(24, 9), (24, 10), (25, 10), (26, 11), (27, 11), (28, 11),
          (29, 11), (30, 12)],
    # pond in the north, the two long lakes on the flanks
    "B": [(22, 4), (23, 3), (24, 4), (25, 3)]
         + [(x, y) for x in (35, 36, 37) for y in range(8, 14)
            if (x, y) not in ((36, 9), (35, 8), (35, 9))]
         + [(x, y) for x in (0, 1, 2) for y in range(11, 14)],
    "d": [(21, 3), (21, 4), (22, 3), (23, 4), (24, 3), (25, 4), (26, 3),
          (35, 7), (36, 7), (37, 7), (1, 10)]
         + [(34, y) for y in range(11, 14)] + [(3, y) for y in range(10, 14)]
         ,
    "r": [(7, 7), (19, 1), (32, 4), (31, 9)],    # dirt patches
    # cliffs
    "w": [(1, 7), (2, 7), (3, 7), (3, 8), (3, 9), (4, 9), (5, 9),
          (10, 7), (10, 8), (9, 8), (9, 9), (9, 10),
          (11, 7), (12, 7), (13, 7), (14, 7), (15, 6), (16, 6), (17, 6),
          (23, 0), (23, 1), (24, 2),
          (26, 0), (26, 1), (27, 1), (27, 2), (27, 3), (27, 4),
          (28, 7), (29, 7), (32, 7), (33, 6), (34, 6),
          # the spiral in the middle
          (19, 11), (19, 12), (18, 13), (20, 13), (21, 11), (22, 12),
          (22, 13)],
    # woods
    "n": [(0, 4), (1, 4), (2, 5), (3, 4), (1, 8), (11, 3), (24, 0),
          (23, 5), (28, 0), (29, 0), (32, 0), (33, 4), (34, 4), (35, 3),
          (35, 6), (34, 7),
          (13, 11), (14, 11), (14, 12), (15, 12), (15, 13), (16, 11),
          (16, 12), (16, 13), (17, 11), (18, 11), (18, 12), (19, 10),
          (20, 11), (22, 11), (23, 12), (23, 13), (24, 13)],
    # ore fields and gem patches
    "a": [(10, 1), (11, 1), (4, 7), (4, 8), (5, 7), (13, 8), (13, 9),
          (15, 9), (21, 1), (22, 1), (29, 10), (28, 6)],
    # ore mines and buildings
    "p": [(10, 0), (10, 2), (4, 6), (14, 9), (22, 0), (22, 2), (32, 2),
          (33, 13), (2, 8), (20, 12),
          (37, 0), (28, 10)],                     # corner, gem patch
    "K": [(5, 3),
          (15, 12)],                 # a small keep in the central woods

    "c": [(4, 3), (4, 4), (5, 2), (6, 3), (6, 4),
          (15, 13)],                 # its one recruit hex
    # a second, smaller castle in the east lake (west lake in the south
    # half, about hex 2,19 in game coordinates), no starting side; the
    # shore beside it is open space so it is easy to reach
    "k": [(36, 9)],
    "h": [(35, 8), (35, 9)],
}


def build():
    grid = [["." for _ in range(W)] for _ in range(H)]
    for ch, hexes in FEATURES.items():
        for x, y in hexes:
            assert y < H // 2, (ch, x, y)
            grid[y][x] = ch
    for y in range(H // 2, H):                       # turn the north half
        for x in range(W):
            grid[y][x] = grid[H - 1 - y][W - 1 - x]
    return grid


def write(grid, path, table=T, base_only=("Yk", "Ys^Vyp")):
    starts = {(5, 3): 1, (W - 1 - 5, H - 1 - 3): 2}
    rows = []
    for Y in range(H + 2):
        row = []
        for X in range(W + 2):
            x = min(max(X - 1, 0), W - 1)
            y = min(max(Y - 1, 0), H - 1)
            code = table[grid[y][x]]
            if table is WESNOTH and code == "Gs^Fp":
                u, v = (x, y) if y < H // 2 else (W - 1 - x, H - 1 - y)
                if (u * 7 + v * 3) % 3 == 0:
                    code = LEAFY
            border = (X - 1, Y - 1) != (x, y)
            if border and code in base_only + ("Khw",):
                code = table["c"] if grid[y][x] == "K" else table["."]
            elif (x, y) in starts:
                code = f"{starts[x, y]} {code}"
            row.append(code)
        rows.append(", ".join(row))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    grid = build()
    write(grid, os.path.join(sys.argv[1], "maps/2p_Understanding_Power.map"))
    write(grid, os.path.join(sys.argv[1],
                             "maps/default-terrain/2p_Understanding_Power.map"),
          WESNOTH, ("Kh", "Gg^Vh"))
