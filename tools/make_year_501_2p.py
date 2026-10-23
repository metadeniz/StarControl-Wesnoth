#!/usr/bin/env python3
"""Write maps/2p_Year_501.map.

Year 501 for 1 vs. 1: the 6p map from tools/make_year_501.py with D's hand
edits on top (see edits(), in Wesnoth's 1-based coordinates, each mirrored
west to east). The north-west and south-west corners are cut off the map
with their starts, so only the middle starts, on the west and east edges,
are left.

Usage: make_year_501_2p.py <add-on dir> [-v]
"""

import os
import sys

import make_year_501 as y
from make_year_501 import H, W, mirror, path, pixel


def at(X, Y):
    return X - 1, Y - 1


def edits(m):
    def clear(x, y, ch="."):
        m.put(x, y, ch)
        for h in [(x, y), mirror(x, y)]:
            m.big.pop(h, None)
    # cut the north-west and south-west corners off the map, from a line
    # between two hexes outwards
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
                    clear(x, y, " ")
        for h in path([a, b]):
            clear(*h, " ")
    for h in [(13, 3), (16, 3), (16, 4), (17, 2), (20, 27), (23, 5)]:
        clear(*at(*h))
    m.put(*at(18, 3), "p")
    m.put(*at(9, 16), "c")                # a second ring for the small base
    # the 4-hex supergiants become 3-hex ones (blue in the west, yellow in
    # the east) on 16,9, 17,9 and 17,10; 16,10 goes back to nebula
    for h in [at(16, 10), mirror(*at(16, 10))]:
        m.big.pop(h, None)
    m.put(*at(16, 10), "n")
    m.big_object([at(16, 9), at(17, 9), at(17, 10)], ("Ytu2", "Ytu1"), "n")
    # planets at 6,21 and 8,7, and the one at 9,14 moved to 14,15
    m.put(*at(9, 14), ".")
    for h in [(6, 21), (8, 7), (14, 15)]:
        m.put(*at(*h), "p")
    # the pulsar's radiation zone one hex south: 14,27, 15,28 (the pulsar)
    # and 16,28 move down (14,28 stays, its own move would leave the map)
    for h in [(14, 27), (15, 28), (16, 28)]:
        m.put(*at(*h), ".")
    for h, ch in [((14, 28), "R"), ((15, 29), "u"), ((16, 29), "R")]:
        m.put(*at(*h), ch)


def build():
    m = y.build()
    edits(m)
    return m


if __name__ == "__main__":
    y.STARTS = [(1, 14)]                   # west: side 1, east: side 2
    m = build()
    y.write(m, os.path.join(sys.argv[1], "maps/2p_Year_501.map"))
    y.report(m)
    if "-v" in sys.argv:
        for row in m.g:
            print("".join(row))
