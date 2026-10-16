#!/usr/bin/env python3
"""Give every untyped planet on a map a type: life, mineral or dead world.

    tools/assign_planet_types.py maps/X.map [maps/Y.map ...] [--retype]

Untyped planets (^Vyp, and ^Vys out in the badlands) become ^Vyl, ^Vym or
^Vyd (^Vysl, ^Vysm, ^Vysd). Typed planets are left alone unless --retype.

The types follow the map's own symmetry: the script finds every mirror
and rotation (in steps of 60 degrees) that maps the planets onto each
other, and gives each set of matching planets the same type, so every
player gets the same mix. On a map that is only roughly symmetric it
follows the closest symmetry; on a map with three or six players it uses
the rotations only. First the script works out the mix of types closest to 40% life,
40% mineral and 20% dead that the sets can make; then, typing the sets nearest
the middle first, each takes the type furthest behind its count (ties broken
by a generator seeded with the map's name), so the types spread
from the middle to the edges. Same map, same result.

The map scripts (make_*.py, convert_map.py) call this on the maps they
write, so the types survive regenerating a map.
"""

import math
import os
import random
import sys

TYPES = ("l", "m", "d")             # life, mineral, dead
SHARE = {"l": 0.4, "m": 0.4, "d": 0.2}
UNTYPED = ("Vyp", "Vys")
SEA = "Vys"
TOL = 0.5                           # in hexes: an exact match
LOOSE = 3.0                         # a map that is only roughly symmetric


def parse(text):
    return [[c.strip() for c in row.split(",")] for row in text.splitlines() if row.strip()]


def overlay(code):
    """'1 Ys^Vyp' -> 'Vyp' (or None)."""
    terrain = code.split(" ")[-1]
    return terrain.split("^", 1)[1] if "^" in terrain else None


def is_planet(code):
    o = overlay(code)
    return o is not None and o.startswith("Vy")


def centre(x, y):
    """Hex centre on a regular grid, 1 = distance between neighbours."""
    s3 = math.sqrt(3)
    return x * s3 / 2, y + (0.5 if x % 2 == 0 else 0)


def transforms():
    """The 12 symmetries of a hex grid about a point: 6 rotations, 6 mirrors."""
    out = []
    for k in range(6):
        a = k * math.pi / 3
        c, s = math.cos(a), math.sin(a)
        out.append((f"rotation {k * 60}", (c, -s, s, c)))
    for k in range(6):
        a = k * math.pi / 3              # mirror axis at k * 30 degrees
        c, s = math.cos(a), math.sin(a)
        out.append((f"mirror {k * 30}", (c, s, s, -c)))
    # a quarter turn never fits a hex grid exactly, but a map traced with
    # four-way symmetry (Media Control) matches it to within a hex or two
    out += [("rotation 90", (0, -1, 1, 0)), ("rotation 270", (0, 1, -1, 0))]
    return out


def symmetries(pts, tol):
    """Transforms (other than identity) that map the planet set onto itself,
    each with where it sends every planet, and how far off the worst match is.
    Planets are paired one to one, closest pairs first."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    found = []
    for name, (a, b, c, d) in transforms()[1:]:
        imgs = [(mx + a * (px - mx) + b * (py - my), my + c * (px - mx) + d * (py - my)) for px, py in pts]
        pairs = sorted((math.hypot(pts[j][0] - qx, pts[j][1] - qy), i, j)
                       for i, (qx, qy) in enumerate(imgs) for j in range(n))
        image, used, worst = [None] * n, set(), 0.0
        for dist, i, j in pairs:
            if image[i] is None and j not in used:
                image[i] = j
                used.add(j)
                worst = max(worst, dist)
        if worst <= tol:
            found.append((name, image, worst))
    return found, (mx, my)


def order(image):
    """How many times the transform must be applied to come back round."""
    k, seen = 1, list(image)
    while seen != list(range(len(image))) and k < 12:
        seen = [image[i] for i in seen]
        k += 1
    return k


def orbits(n, syms):
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for _, image, _ in syms:
        for i, j in enumerate(image):
            parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def best_mix(count, sizes, total, rng):
    """Final type counts the sets can make that come closest to the shares."""
    reach = {(count["l"], count["m"])}
    for n in sizes:
        reach = {(l + dl, m + dm) for l, m in reach for dl, dm in ((n, 0), (0, n), (0, 0))}
    left = sum(sizes) + count["l"] + count["m"] + count["d"]
    def miss(lm):
        l, m = lm
        d = left - l - m
        return sum((v - SHARE[t] * total) ** 2 for t, v in zip(TYPES, (l, m, d)))
    best = min(miss(lm) for lm in reach)
    l, m = rng.choice(sorted(lm for lm in reach if miss(lm) - best < 1e-9))
    return {"l": l, "m": m, "d": left - l - m}


def assign(text, name, retype=False):
    """Returns the new map text and a one-line report."""
    rows = parse(text)
    cells = [(x, y) for y, row in enumerate(rows) for x, code in enumerate(row) if is_planet(code)]
    if not cells:
        return text, f"{name}: no planets"
    pts = [centre(x, y) for x, y in cells]
    syms, (mx, my) = symmetries(pts, TOL)
    how = "exact"
    if not syms:
        # a roughly symmetric map: follow one symmetry only, the one that
        # links the most planets (a quarter turn links four), then the closest
        syms, (mx, my) = symmetries(pts, LOOSE)
        syms = sorted(syms, key=lambda s: (-order(s[1]), s[2]))[:1]
        how = f"rough, off by up to {syms[0][2]:.1f} hexes" if syms else "none found"
    elif any(s[0] == "rotation 120" for s in syms):
        # three or six players: every player gets the same mix from the
        # rotations alone; leaving out the mirrors keeps the sets small
        # enough for the three types to come out even
        syms = [s for s in syms if s[0].startswith("rotation")]
        how = "exact, rotations only"
    groups = orbits(len(cells), syms)
    rng = random.Random(name)
    count = {t: 0 for t in TYPES}
    # keep the types already given, unless retyping
    todo = []
    for g in groups:
        given = {overlay(rows[cells[i][1]][cells[i][0]])[-1] for i in g} - {"p", "s"}
        if given and not retype:
            for t in given:
                count[t] += len(g)
        else:
            todo.append(g)
    dist = lambda g: min(math.hypot(pts[i][0] - mx, pts[i][1] - my) for i in g)
    todo.sort(key=lambda g: (round(dist(g), 3), min(cells[i] for i in g)))
    sizes = [len(g) for g in todo]
    target = best_mix(count, sizes, len(cells), rng)
    need = {t: target[t] - count[t] for t in TYPES}

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def fits(k, nl, nm):
        """Can sets k.. fill exactly nl life and nm mineral (dead the rest)?"""
        if k == len(sizes):
            return nl == 0 and nm == 0
        n = sizes[k]
        return ((nl >= n and fits(k + 1, nl - n, nm)) or (nm >= n and fits(k + 1, nl, nm - n))
                or fits(k + 1, nl, nm) and sum(sizes[k:]) - n >= nl + nm)

    got = {t: 0 for t in TYPES}
    for k, g in enumerate(todo):
        # the type furthest behind its target once this set is added, among
        # those that still let the remaining sets hit the target exactly
        n = len(g)
        options = []
        for t in TYPES:
            left = dict(need)
            if left[t] < n:
                continue
            left[t] -= n
            if fits(k + 1, left["l"], left["m"]):
                options.append(((got[t] + n) / max(target[t], 1), t))
        low = min(o[0] for o in options)
        t = rng.choice([t for v, t in options if v - low < 1e-9])
        need[t] -= n
        got[t] += n
        count[t] += n
        for i in g:
            x, y = cells[i]
            code = rows[y][x]
            head, ov = code.rsplit("^", 1)
            sea = ov.startswith(SEA)
            rows[y][x] = head + "^" + ("Vys" if sea else "Vy") + t
    out = "\n".join(", ".join(r) for r in rows) + "\n"
    kinds = ", ".join(sorted({s[0] for s in syms})) or "none"
    report = (f"{name}: {len(cells)} planets in {len(groups)} sets; "
              f"symmetry ({how}): {kinds}; life {count['l']}, mineral {count['m']}, dead {count['d']}")
    return out, report


def assign_file(path, retype=False, quiet=False):
    with open(path) as f:
        text = f.read()
    out, report = assign(text, os.path.splitext(os.path.basename(path))[0], retype)
    if out != text:
        with open(path, "w") as f:
            f.write(out)
    if not quiet:
        print(report)
    return report


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for p in args:
        assign_file(p, retype="--retype" in sys.argv)


if __name__ == "__main__":
    main()
