#!/usr/bin/env python3
"""Write the Star Control TC multiplayer maps.

Each map is drawn as the left half plus the centre column, as text; the
right half is the mirror image, so both sides get exactly the same map.
Starbases get their docking rings added automatically.

Legend:   .  deep space          n  nebula
          a  asteroid field      A  asteroids inside nebula
          p  planet              P  planet inside nebula
          *  star                K  starbase (player start)

Usage: make_maps.py <add-on dir>
"""

import os
import sys

from assign_planet_types import assign_file

TERRAIN = {
    ".": "Ys", "n": "Yn", "a": "Ys^Ya", "A": "Yn^Ya",
    "p": "Ys^Vyp", "P": "Yn^Vyp", "*": "Ys^Yx", "K": "Yk",
}

# Each row: columns 0..C, where column C is the centre line. Row/column 0
# and the last row are the off-map border Wesnoth keeps around every map.
MAPS = {
    "2p_Procyon_Front": """
..............
...nn....a....
..nnnp...aa..p
..nn......a...
.....p........
..........n..n
........nnp..n
.p.........n..
..............
...K.....p....
.............*
.....a........
..p..aa.......
.....a......nn
.........nnp..
..p....n......
......a..n...p
...nn.aa......
..nn..........
..............
""",
    "2p_Vela_Nebula": """
..............
.......nnnnnnn
..p...nnnPnnnn
.....nnn...nn.
....a.nn.p...a
...aa...a...aa
..a...p......*
.......nn....a
..p...nnnn....
...K...nnnp...
.......nnn....
..p.....n.....
.......a......
.....p..aa...p
...a...a.....a
..aa.....nn..*
....nnp.nnnn.a
...nnnn..nPnnn
..nnn....nnnnn
..............
""",
}

DESCRIPTIONS = {}


def neighbours(x, y):
    """Wesnoth hex neighbours (file coordinates, border included)."""
    # Odd file columns are the "raised" ones in Wesnoth's layout.
    if x % 2 == 1:
        return [(x, y - 1), (x + 1, y - 1), (x + 1, y), (x, y + 1), (x - 1, y), (x - 1, y - 1)]
    return [(x, y - 1), (x + 1, y), (x + 1, y + 1), (x, y + 1), (x - 1, y + 1), (x - 1, y)]


def build(text):
    rows = [r for r in text.strip("\n").split("\n")]
    half = len(rows[0])
    assert all(len(r) == half for r in rows), "ragged map rows"
    width = 2 * half - 1  # centre column shared
    assert width % 2 == 1  # odd width keeps the mirror hex-exact
    height = len(rows)
    grid = [[None] * width for _ in range(height)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            grid[y][x] = ch
            grid[y][width - 1 - x] = ch

    starts = []
    for y in range(height):
        for x in range(width):
            if grid[y][x] == "K":
                starts.append((x, y))
    starts.sort()
    assert len(starts) == 2, starts

    # Docking rings: the three neighbours of each starbase nearest the centre.
    centre = (width - 1) / 2
    docks = set()
    for (kx, ky) in starts:
        ring = sorted(neighbours(kx, ky), key=lambda p: (abs(p[0] - centre), abs(p[1] - ky)))
        for p in ring[:3]:
            docks.add(p)

    lines = []
    for y in range(height):
        cells = []
        for x in range(width):
            code = "Yc" if (x, y) in docks else TERRAIN[grid[y][x]]
            if (x, y) in starts:
                code = f"{starts.index((x, y)) + 1} {code}"
            cells.append(code)
        lines.append(", ".join(cells))
    return "\n".join(lines) + "\n", width, height


def main():
    out = os.path.join(sys.argv[1], "maps")
    os.makedirs(out, exist_ok=True)
    for name, text in MAPS.items():
        data, w, h = build(text)
        with open(os.path.join(out, name + ".map"), "w") as f:
            f.write(data)
        assign_file(os.path.join(out, name + ".map"), quiet=True)   # life, mineral and dead worlds
        planets = data.count("^Vyp")
        print(f"{name}: {w - 2}x{h - 2} playable, {planets} planets")


if __name__ == "__main__":
    main()
