#!/usr/bin/env python3
"""Turn a regular Wesnoth map into a space map, hex for hex.

Terrain is translated by role, so a converted map plays like the original:

    open ground (grass, sand, road...)  -> deep space           Ys
    forest, trees, mushrooms            -> nebula               Yn
    hills                               -> asteroid field       Ys^Ya
    mountains                           -> asteroids in nebula  Yn^Ya
    water, swamp                        -> ion storm            Yi
    bridge                              -> deep space (a lane)  Ys
    village                             -> planet               ^Vyp
    castle / keep                       -> docking ring / base  Yc / Yk
    impassable, chasm                   -> star                 Ys^Yx
    off-map                             -> unchanged

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

    if overlay.startswith("B"):          # bridges become open lanes
        return "Ys"
    if b == "K":
        return "Yk"
    if b == "C":
        return "Yc"
    if b in "XQ":
        return "Ys^Yx"

    if b in "WS":
        new_base = "Yi"
    elif b == "M":
        new_base = "Yn"
    else:
        new_base = "Ys"
    rough = b in "HM"
    if overlay.startswith(("F", "T")):   # forest-like cover
        new_base = "Yi" if new_base == "Yi" else "Yn"

    if overlay.startswith("V"):
        return new_base + "^Vyp"
    if rough:
        return new_base + "^Ya"
    return new_base


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rows = []
    counts = collections.Counter()
    for line in open(src):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        cells = []
        for cell in line.split(","):
            cell = cell.strip()
            m = re.match(r"^(\d+ )?(.*)$", cell)
            start, code = m.group(1) or "", m.group(2)
            new = convert(code)
            counts[new] += 1
            cells.append(start + new)
        rows.append(", ".join(cells))
    with open(dst, "w") as f:
        f.write("\n".join(rows) + "\n")
    for code, n in counts.most_common():
        print(f"  {code:12s} {n}")


if __name__ == "__main__":
    main()
