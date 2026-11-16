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
    ford                                   -> deep space          Ys
    bridge                                 -> deep space (a lane) Ys
    village                                -> planet              ^Vyp
    village in water (not swamp)           -> sea planet          ^Vys
    castle / keep                          -> docking ring / base Yc / Yk
    castle in water or swamp (sunken or    -> docking ring out in  Yci
      swamp ruin, aquatic castle)             the badlands (plays as Yc)
    cave and stone walls, impassable       -> debris disk         Ys^Yw
      mountains, the ^Xo overlay
    void (Xv)                              -> dark nebula         Yqd
    lava, volcano                          -> star                Ys^Yx
        ...but lava that touches more lava -> plasma storm        Yqp
    chasm                                  -> black hole          Ys^Yxb
        ...but chasm touching more chasm   -> gravity eddy        Yqe
      (so a lava field or a chasm doesn't become a row of suns)
    off-map                                -> unchanged, but holes cut into
                                              the play area -> dark nebula Yqd
    fake map edge (^_fme)                  -> kept, over the converted base

Starting positions are kept.

lua/space.lua does the same in-game, for any map played with the era;
keep the two in step.

Usage: convert_map.py <wesnoth .map> <output .map> [X,Y=CODE ...]

Each X,Y=CODE puts that terrain on hex X,Y (game coordinates) afterwards,
for things the original scenario placed as units: Caves of the Basilisk's
statues became black holes (Ys^Yxb).
"""

import collections
import re
import sys

from assign_planet_types import assign_file


LONE = {"#lava": "Ys^Yx", "#chasm": "Ys^Yxb"}
FIELD = {"#lava": "Yqp", "#chasm": "Yqe"}


def convert(code):
    if code.startswith("_off"):
        return code
    if code.endswith("^_fme"):                 # fake map edge: keep it over the new base
        under = convert(code[:-len("^_fme")])
        under = FIELD.get(under, under)
        return under.partition("^")[0] + "^_fme"
    base, _, overlay = code.partition("^")
    b = base[:1]

    if overlay.startswith("B"):                # bridges become open lanes
        return "Ys"
    # impassable terrain; lava and chasms are settled by what they touch
    if base == "Xv":                           # void
        return "Yqd"
    if overlay.startswith("X") or b == "X":
        return "Ys^Yw"
    if base.startswith("Ql"):
        return "#lava"
    if b == "Q" or overlay.startswith("Q"):
        return "#chasm"
    if base == "Mv":                           # volcano
        return "Ys^Yx"
    if b == "K":
        return "Yk"
    if b == "C":
        # sunken (Chw) and swamp (Chs) ruins, aquatic castles (Cm, Cme)
        return "Yci" if re.match(r"C(h[ws]|me?)$", base) else "Yc"
    if base.startswith("Uh"):                  # rockbound cave (rough, like hills)
        return "Ys^Vyp" if overlay.startswith("V") else "Ys^Ya"
    if base.startswith("Wwf"):                 # ford: open space, like a bridge
        return "Ys^Vyp" if overlay.startswith("V") else "Ys"

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
        return new_base + ("^Vys" if b == "W" else "^Vyp")
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
    # Off-map holes cut into the play area become dark nebula.
    for y, row in enumerate(grid[1:-1], 1):
        for x, cell in enumerate(row[1:-1], 1):
            if cell[1].startswith("_off"):
                cell[1] = "Yqd"
    # A lone lava hex is a star, a lone chasm a black hole; where they touch
    # more of the same they are a plasma storm or a gravity eddy.
    kind = {(x, y): c for y, row in enumerate(grid) for x, (_, c) in enumerate(row) if c in LONE}
    for (x, y), c in kind.items():
        field = any(kind.get(n) == c for n in neighbours(x, y))
        grid[y][x][1] = FIELD[c] if field else LONE[c]
    for arg in sys.argv[3:]:
        xy, code = arg.split("=")
        x, y = (int(v) for v in xy.split(","))
        grid[y][x][1] = code
    rows = []
    counts = collections.Counter()
    for row in grid:
        rows.append(", ".join(start + code for start, code in row))
        counts.update(code for _, code in row)
    with open(dst, "w") as f:
        f.write("\n".join(rows) + "\n")
    assign_file(dst, quiet=True)          # life, mineral and dead worlds
    for code, n in counts.most_common():
        print(f"  {code:12s} {n}")


if __name__ == "__main__":
    main()
