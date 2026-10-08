#!/usr/bin/env python3
"""Turn a regular Wesnoth map into a space map, hex for hex.

Terrain is translated by role, so a converted map plays like the original:

    open ground (grass, road, cave floor)  -> deep space          Ys
    sand, desert                           -> dust cloud          Yd
    forest, trees                          -> nebula              Yn
    mushroom grove                         -> red nebula          Yr
    hills, rockbound cave                  -> asteroid field      Ys^Ya
    dunes (sandy hills)                    -> asteroids in dust   Yd^Ya
    forested hills                         -> asteroids in nebula Yn^Ya
    mountains                              -> dense asteroids     Ys^Yad
    deep water                             -> badlands           Yi
    shallow water, reef, swamp             -> light badlands     Yis
    ford                                   -> thin badlands      Yif
    bridge                                 -> deep space (a lane) Ys
    village                                -> planet              ^Vyp
    castle / keep (also ruins in water or  -> docking ring / base Yc / Yk
      swamp: no penalty for anyone)
    impassable (walls, ^Xm...), chasm      -> star                Ys^Yx
        ...but where impassable hexes touch,  -> asteroid wall       Ys^Yw
        so a wall doesn't become a row of suns
    off-map                                -> unchanged

Starting positions are kept.

Usage: convert_map.py <wesnoth .map> <output .map>
"""

import collections
import re
import sys


def convert(code):
    if code.startswith("_off"):
        return code
    base, _, overlay = code.partition("^")
    b = base[:1]

    if overlay.startswith("X") or b in "XQ":   # impassable, chasm
        return "Ys^Yx"
    if overlay.startswith("B"):                # bridges become open lanes
        return "Ys"
    if b == "K":
        return "Yk"
    if b == "C":
        return "Yc"
    if base.startswith("Uh"):                  # rockbound cave (rough, like hills)
        return "Ys^Vyp" if overlay.startswith("V") else "Ys^Ya"
    if base.startswith("Wwf"):                 # ford
        return "Yif^Vyp" if overlay.startswith("V") else "Yif"

    if base.startswith("Wo"):                  # deep water
        new_base = "Yi"
    elif b in "WS":                            # shallow water, reef, swamp
        new_base = "Yis"
    elif b == "D" or base.startswith("Hd"):    # sand, dunes
        new_base = "Yd"
    else:
        new_base = "Ys"
    if overlay.startswith("T") or b == "T":    # mushroom grove
        new_base = "Yr"
    elif overlay.startswith("F"):              # forest
        new_base = new_base if new_base in ("Yi", "Yis") else "Yn"

    if overlay.startswith("V"):
        return new_base + "^Vyp"
    if b == "M":
        return new_base + "^Yad"
    if b == "H":
        return new_base + "^Ya"
    return new_base


def neighbours(x, y):
    """Wesnoth hex neighbours (columns with an odd x sit half a hex higher)."""
    if x % 2:
        return [(x, y - 1), (x, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y), (x + 1, y)]
    return [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y), (x - 1, y + 1), (x + 1, y + 1)]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    grid = []
    for line in open(src):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        row = []
        for cell in line.split(","):
            m = re.match(r"^(\d+ )?(.*)$", cell.strip())
            row.append([m.group(1) or "", convert(m.group(2))])
        grid.append(row)
    # Impassable hexes that touch another one become an asteroid wall.
    star = {(x, y) for y, row in enumerate(grid) for x, (_, c) in enumerate(row) if c == "Ys^Yx"}
    for x, y in star:
        if any(n in star for n in neighbours(x, y)):
            grid[y][x][1] = "Ys^Yw"
    rows = []
    counts = collections.Counter()
    for row in grid:
        rows.append(", ".join(start + code for start, code in row))
        counts.update(code for _, code in row)
    with open(dst, "w") as f:
        f.write("\n".join(rows) + "\n")
    for code, n in counts.most_common():
        print(f"  {code:12s} {n}")


if __name__ == "__main__":
    main()
