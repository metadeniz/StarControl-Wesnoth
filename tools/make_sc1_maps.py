#!/usr/bin/env python3
"""Open maps for the Star Control 1 missions, drawn round Star Control 1's
own star clusters.

    tools/make_sc1_maps.py NAME HIERARCHY ALLIANCE SEED [SEED ...]

Writes maps/2p_SC1_NAME_1.map, _2.map, ... one per seed, each with a .lua
beside it. HIERARCHY and ALLIANCE are the mission's world counts (a star
per world, as in SC1). Each map is the cluster SC1 itself builds from that
seed (tools/sc1_cluster.py: SC1's generator, same stars, same links), laid
flat, on hexes, cropped to a rectangle round it:

  - lanes of open space about 4 hexes across along every link, and open
    space round every planet;
  - rough terrain outside the lanes: patches of nebula, light badlands,
    dust and asteroid fields, with open gaps through them, small red
    nebulae on the edges of the green, a debris disk (3 hexes) in every big
    asteroid field and a few lone stars, black holes, pulsars and brown
    dwarfs well away from the lanes;
  - cover in the lanes: small patches (1-4 hexes) of nebula, dust, light
    badlands, asteroids or red nebula, clear of planets and starbases;
  - the Hierarchy's starbase (start 1) just beyond the star of its half
    farthest from the centre, where SC1 puts it, the Alliance's (start 2)
    likewise at the south end, each with 3 docking rings, and two forward
    starbases, one each side of the middle, each with 3;
  - between the forward starbases, a third of the band made impassable
    dark nebula, furthest from the lanes first, to narrow the waist;
  - the map cropped to 2 hexes beyond the outermost planet, starbase or
    docking ring on every side (lanes running further are cut off).

The planet types drawn are First Encounter's; at the start of a game
lua/sc1.lua deals them again for the mission being played, as SC1 does,
using each star's place along SC1's cluster from the .lua file.

Needs numpy.
"""

import math
import os
import sys

import numpy as np

from sc1_cluster import MscRand, centre, flatten_cluster, generate_cluster, neighbours, seg_dist, snap

S = 6           # SC1 units per hex (SC1's links are 20-38 long)
LANE = 1.8      # lane half-width in hexes (about 4 across)
POCKET = 2.2    # open radius round planets
BASE = 16       # how far beyond its star (SC1 units) a starbase's keep sits
FORWARD = 34    # how far from the centre star (SC1 units) the forward keeps sit
WAIST = 1 / 3   # share of the middle band (between the forward keeps) made impassable
MARGIN = 2      # hexes kept beyond the outermost planet or starbase
PAD = 3         # hexes of rough terrain beyond the outermost open hex


def build(seed, hier, ally):
    rng = np.random.default_rng(seed)
    stars = generate_cluster(MscRand(seed), ally, hier)
    flat = flatten_cluster(stars)
    n = len(stars)
    # x across, y along SC1's axis: the Hierarchy's half (B) on top
    nodes = [(flat[s][1], flat[s][0]) for s in stars]
    links = [(s.index, t.index) for s in stars for t in s.links if t.index > s.index]
    # the starbases: SC1 puts each on the star of its half farthest from
    # the centre; here the keep sits just beyond that star, linked to it
    ends = {}
    for end, side, far in (('H', 'B', min), ('A', 'A', max)):
        anchor = far((s for s in stars if s.side == side), key=lambda s: s.x).index
        ax, ay = nodes[anchor]
        d = math.hypot(ax, ay)
        ends[end] = len(nodes)
        nodes.append((ax + ax / d * BASE, ay + ay / d * BASE))
        links.append((anchor, ends[end]))
    pts = np.array(nodes) / S
    minx, miny = pts.min(0); maxx, maxy = pts.max(0)
    ox = -minx + 0.75 * (PAD + 2); oy = -miny + PAD + 2
    hexes = [snap(px + ox, py + oy) for px, py in pts]
    W = int((maxx + ox + 0.75 * (PAD + 2)) / 0.75) + 1
    H = int(maxy + oy + PAD + 2) + 1
    # the centre star's hex: where the forward keeps are measured from
    ox, oy = centre(*hexes[0])
    cen = [centre(*h) for h in hexes]
    open_ = set()
    for x in range(1, W + 1):
        for y in range(1, H + 1):
            p = centre(x, y)
            if any(math.dist(p, q) <= POCKET for q in cen) or \
               any(seg_dist(p, cen[i], cen[j]) <= LANE for i, j in links):
                open_.add((x, y))
    # rough terrain outside the lanes: smooth random fields, the largest wins
    kinds = ['Yn', 'Yis', 'Yd', 'Ys^Ya', 'Ys']
    weights = [1.0, 0.8, 0.45, 0.4, 0.6]   # 'Ys': open gaps through the rough
    blobs = []
    for k in kinds:
        for _ in range(int(W * H / 60)):
            blobs.append((k, rng.uniform(0, 0.75 * W), rng.uniform(0, H), rng.uniform(1.5, 3.5)))
    grid = [['Ys'] * (W + 2) for _ in range(H + 2)]
    rough = []
    for x in range(0, W + 2):
        for y in range(0, H + 2):
            if (x, y) in open_: continue
            p = centre(x, y)
            score = {k: 0.0 for k in kinds}
            for k, bx, by, r in blobs:
                d = math.dist(p, (bx, by))
                if d < 2 * r: score[k] += math.exp(-(d / r) ** 2)
            for i, k in enumerate(kinds): score[k] *= weights[i]
            grid[y][x] = max(kinds, key=lambda k: score[k])
            if 1 <= x <= W and 1 <= y <= H: rough.append((x, y))
    in_map = lambda h: 1 <= h[0] <= W and 1 <= h[1] <= H
    # red nebula: small patches on the edges of green nebula
    edges = [h for h in rough if grid[h[1]][h[0]] == 'Yn' and
             any(in_map(nb) and nb not in open_ and grid[nb[1]][nb[0]] not in ('Yn',) for nb in neighbours(*h))]
    rng.shuffle(edges)
    for h in edges[:max(3, W * H // 300)]:
        size, patch, q = int(rng.integers(3, 7)), [], [h]
        while q and len(patch) < size:
            a = q.pop(int(rng.integers(len(q))))
            if a in patch or not in_map(a) or a in open_ or grid[a[1]][a[0]] == 'Yr':
                continue
            patch.append(a)
            q += neighbours(*a)
        for x, y in patch:
            grid[y][x] = 'Yr'
    # a debris disk (a star behind rocks, 3 hexes) in every big asteroid field
    ast = {h for h in rough if grid[h[1]][h[0]] == 'Ys^Ya'}
    seen = set()
    for h0 in sorted(ast):
        if h0 in seen:
            continue
        comp, q = [], [h0]
        seen.add(h0)
        while q:
            a = q.pop()
            comp.append(a)
            for nb in neighbours(*a):
                if nb in ast and nb not in seen:
                    seen.add(nb); q.append(nb)
        if len(comp) < 15:
            continue
        cs = set(comp)
        mx = sum(centre(*c)[0] for c in comp) / len(comp)
        my = sum(centre(*c)[1] for c in comp) / len(comp)
        best = None
        for x, y in comp:
            if x % 2:
                continue
            tri = [(x, y), (x + 1, y), (x + 1, y + 1)]
            if not all(t in cs for t in tri):
                continue
            ring = {nb for t in tri for nb in neighbours(*t)} - set(tri)
            if any(nb in open_ for nb in ring):
                continue
            d = math.dist(centre(x + 1, y + 0.5), (mx, my))
            if best is None or d < best[0]:
                best = (d, tri)
        if best:
            look = int(rng.integers(1, 7))
            for x, y in best[1]:
                grid[y][x] = f'Ys^Ytd{look}'
    # a few lone obstacles, well away from lanes
    far = [h for h in rough if all((n not in open_) for n in neighbours(*h)) and
           all(math.dist(centre(*h), centre(*o)) > 2.5 for o in open_ if abs(o[0]-h[0]) < 6 and abs(o[1]-h[1]) < 6)]
    rng.shuffle(far)
    obst = ['^Yx', '^Yxb', '^Yxp', '^Ybd']
    placed = []
    for h in far:
        if '^Yt' in grid[h[1]][h[0]]:
            continue
        if len(placed) >= max(3, W * H // 400): break
        if all(math.dist(centre(*h), centre(*q)) > 8 for q in placed):
            base = grid[h[1]][h[0]].split('^')[0]
            grid[h[1]][h[0]] = base + obst[len(placed) % len(obst)]
            placed.append(h)
    # planets: First Encounter's deal (lua/sc1.lua deals again each game)
    for side in 'BA':
        half = [t.index for t in stars if t.side == side]
        deck = ['l', 'm'] + ['m'] * 6 + ['l'] * 6
        deck = deck[:len(half)] + ['d'] * max(0, len(half) - len(deck))
        rng.shuffle(deck)
        for i, t in zip(half, deck):
            grid[hexes[i][1]][hexes[i][0]] = 'Ys^Vy' + t
    for side, end in ((1, 'H'), (2, 'A')):
        x, y = hexes[ends[end]]
        grid[y][x] = f'{side} Yk'
        mx, my = 0.75 * (W + 1) / 2, (H + 1) / 2
        nb = sorted(neighbours(x, y), key=lambda h: math.dist(centre(*h), (mx, my)))[:3]
        for hx, hy in nb: grid[hy][hx] = 'Yc'
    # forward keeps: one on each side of the middle, on the trunk just
    # before the centre planets, each with 3 docking rings
    planet_hex = set(hexes[:n])
    near_planet = {nb for h in planet_hex for nb in neighbours(*h)} | planet_hex
    used = set()
    forward_y = []
    for sy in (-1, 1):
        target = (ox, oy + sy * FORWARD / S)
        best = None
        for h in open_:
            if h in near_planet or h in used:
                continue
            ring = [nb for nb in neighbours(*h) if nb in open_ and nb not in near_planet and nb not in used]
            if len(ring) < 3:
                continue
            d = math.dist(centre(*h), target)
            if best is None or d < best[0]:
                best = (d, h, ring)
        _, (x, y), ring = best
        grid[y][x] = 'Yk'
        ring = sorted(ring, key=lambda r: math.dist(centre(*r), target))[:3]
        for rx, ry in ring:
            grid[ry][rx] = 'Yc'
        used |= {(x, y)} | set(ring) | set(neighbours(x, y))
        forward_y.append(y)
    # cover in the lanes: small patches (1-4 hexes) to hide in or fight from,
    # clear of planets, starbases and docking rings
    def busy(h):
        t = grid[h[1]][h[0]]
        return any(k in t for k in ('Vy', 'Yk', 'Yc'))
    cand = [h for h in sorted(open_) if grid[h[1]][h[0]] == 'Ys'
            and not any(busy(nb) for nb in neighbours(*h) if in_map(nb))]
    rng.shuffle(cand)
    cover_kinds = ['Yn', 'Yd', 'Yis', 'Ys^Ya', 'Yr']
    cover_p = [0.3, 0.2, 0.2, 0.2, 0.1]
    seeds = []
    for h in cand:
        if len(seeds) >= len(links) * 2 // 3:
            break
        if all(math.dist(centre(*h), centre(*q)) > 4.5 for q in seeds):
            seeds.append(h)
    cs = set(cand)
    for h in seeds:
        kind = cover_kinds[rng.choice(len(cover_kinds), p=cover_p)]
        size, patch, q = int(rng.integers(1, 5)), [], [h]
        while q and len(patch) < size:
            a = q.pop(int(rng.integers(len(q))))
            if a in patch or a not in cs:
                continue
            patch.append(a)
            q += neighbours(*a)
        for x, y in patch:
            grid[y][x] = kind
    # the hourglass's waist: between the forward keeps, the third of the
    # hexes furthest from any lane becomes impassable dark nebula
    top, bottom = min(forward_y), max(forward_y)
    band = [(x, y) for x in range(1, W + 1) for y in range(top, bottom + 1)]
    dist = {h: 0 for h in open_}
    q = list(open_)
    for a in q:
        for nb in neighbours(*a):
            if in_map(nb) and nb not in dist:
                dist[nb] = dist[a] + 1
                q.append(nb)
    walls = [h for h in band if h not in open_ and '^Y' not in grid[h[1]][h[0]]
             and not any(k in grid[h[1]][h[0]] for k in ('Vy', 'Yk', 'Yc'))]
    mid = 0.75 * (W + 1) / 2
    walls.sort(key=lambda h: (-dist.get(h, 99), -abs(centre(*h)[0] - mid), h))
    for x, y in walls[:round(len(band) * WAIST)]:
        grid[y][x] = 'Yqd'
    # crop to MARGIN hexes beyond the outermost planet, starbase or docking
    # ring on every side; columns go in even numbers on the left so the
    # hexes keep their places (even columns sit half a hex lower)
    things = [(x, y) for y in range(1, H + 1) for x in range(1, W + 1)
              if any(k in grid[y][x] for k in ('Vy', 'Yk', 'Yc'))]
    top = max(1, min(y for _, y in things) - MARGIN)
    bottom = min(H, max(y for _, y in things) + MARGIN)
    left = max(1, min(x for x, _ in things) - MARGIN)
    left -= (left - 1) % 2
    right = min(W, max(x for x, _ in things) + MARGIN)
    rows = [grid[0]] + grid[top:bottom + 1] + [grid[H + 1]]
    grid = [[r[0]] + r[left:right + 1] + [r[W + 1]] for r in rows]
    W, H = right - left + 1, bottom - top + 1
    # what lua/sc1.lua needs to set up the game as SC1 does: each star's
    # hex and its place along SC1's axis
    sc1 = [(hexes[t.index][0] - left + 1, hexes[t.index][1] - top + 1, t.x) for t in stars]
    return W, H, "\n".join(", ".join(r) for r in grid) + "\n", sc1


def main():
    name, hier, ally = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    seeds = [int(s) for s in sys.argv[4:]]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for k, seed in enumerate(seeds, 1):
        w, h, data, sc1 = build(seed, hier, ally)
        base = os.path.join(here, "maps", f"2p_SC1_{name}_{k}")
        with open(base + ".map", "w") as f:
            f.write(data)
        with open(base + ".lua", "w") as f:
            f.write(f"-- made by tools/make_sc1_maps.py, SC1 seed {seed}: each star's hex and\n"
                    "-- its x along Star Control 1's cluster (the Hierarchy's half below 95)\n"
                    "return {\n")
            for x, y, sx in sc1:
                f.write(f"\t{{ {x}, {y}, {sx} }},\n")
            f.write("}\n")
        print(f"{base}.map: seed {seed}, {w}x{h}")


if __name__ == "__main__":
    main()
