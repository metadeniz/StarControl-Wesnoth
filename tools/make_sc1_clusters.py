#!/usr/bin/env python3
"""Star Control 1 style star clusters for the SC1 missions, laid on hexes.

    tools/make_sc1_clusters.py [count] [--maps DIR]

Writes lua/sc1_clusters.lua: `count` cluster layouts (default 100), each a
set of planets joined by lanes of open space through an impassable fill,
with a starbase at each end. lua/sc1.lua picks one at the start of a game
(mirrored left to right or not) and deals out the planet types, holdings
and ships. --maps DIR also writes each layout as a .map file (planet types
dealt at random) for previews with `wesnoth --screenshot`.

How a cluster is drawn, following D's notes on Star Control 1's maps: an X
shape, a short trunk through the middle (2 or 3 planets near the centre so
the middle is not always a one-planet choke) and two arms at each end.
Planets are linked to every planet within a fixed range, shortest links
first, never crossing another link; the two arms of one end only link near
their fork, arms of opposite ends never. A layout is kept only if

  - it is all connected, with 34-42 links and 2-5 dead ends, and every arm
    has 4 planets or more;
  - planets that look close are close in links too (share a neighbour);
  - no planet curls back: its route toward the centre gets closer to it;
  - a dead end is at most 2 links from a planet with 3+ links;
  - mostly 2+ links cross the middle (one in four may have a single choke);
  - the left and right halves differ by at most 2 planets;
  - each starbase, placed beyond the planet of its half farthest from the
    centre, is at most 2 jumps from a planet with 3+ links;

and, on hexes, if every planet keeps a ring of open space round it and no
lane runs into a planet or lane it is not linked to.

Needs numpy.
"""

import argparse
import math
import os
import sys
from multiprocessing import Pool

import numpy as np

N = 28                 # planets: 12 free worlds a side, plus a colony and a mine
L = 480                # cluster length (top tip to bottom tip)
DMIN = 46              # closest two planets may be
R = 76                 # link range
JITTER = 34            # how far planets stray from the skeleton
S = 16                 # cluster units per hex (row height)
W, H = 43, 46            # playable map size, in hexes
LANE = 0.6             # half-width of a lane, in hexes
MARGIN = 2             # open hexes kept clear of the map edge
PUSH = (28, 36, 44, 52)  # how far beyond its outermost planet a starbase sits
HOME = 10              # planets listed nearest each starbase, for holdings
RING = False           # open the hexes round each planet too


# ---- the cluster, in cluster units (y down: the Hierarchy end is -y) ------

def seg_cross(p1, p2, p3, p4):
    def o(a, b, c):
        return np.sign((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    return o(p1, p2, p3) != o(p1, p2, p4) and o(p3, p4, p1) != o(p3, p4, p2)


def cluster(rng):
    """One try at a cluster; None if it breaks a rule."""
    n = N
    fork = rng.uniform(0.18, 0.32) * L          # trunk half-length
    segs = {'trunk': (np.array([0, -fork]), np.array([0, fork]))}
    for end, sy in (('H', -1), ('A', 1)):
        for side, sx in (('L', -1), ('R', 1)):
            tip = np.array([sx * rng.uniform(110, 200), sy * L / 2 * rng.uniform(0.85, 1.0)])
            segs[end + side] = (np.array([0, sy * fork]), tip)
    lens = {k: np.linalg.norm(b - a) for k, (a, b) in segs.items()}
    keys = list(segs)
    w = np.array([lens[k] * (1.5 if k == 'trunk' else 1) for k in keys])
    w /= w.sum()
    pts, lab, tpos = [], [], []
    ncentre = int(rng.choice([2, 3]))
    dx, dy = rng.uniform(28, 40), rng.normal(0, 12)
    pts += [np.array([-dx, dy]), np.array([dx, -dy])]
    if ncentre == 3:
        pts.append(np.array([rng.normal(0, 10), rng.choice([-1, 1]) * rng.uniform(50, 60)]))
    lab += ['trunk'] * ncentre
    tpos += [0.5] * ncentre
    tries = 0
    while len(pts) < n and tries < 30000:
        tries += 1
        k = keys[rng.choice(len(keys), p=w)]
        a, b = segs[k]
        t = rng.uniform(0, 1)
        d = (b - a) / lens[k]
        nrm = np.array([-d[1], d[0]])
        p = a + d * lens[k] * t + nrm * rng.normal(0, JITTER * (0.6 if k == 'trunk' else 1))
        if all(np.linalg.norm(p - q) >= DMIN for q in pts):
            pts.append(p)
            lab.append(k)
            tpos.append(t)
    if len(pts) < n:
        return None
    P = np.array(pts)
    D = np.linalg.norm(P[:, None] - P[None], axis=2)

    def allowed(i, j):
        a, b = lab[i], lab[j]
        if a != b and a != 'trunk' and b != 'trunk' and a[0] == b[0]:
            return tpos[i] < 0.3 and tpos[j] < 0.3     # two arms of one end
        if a != b and a != 'trunk' and b != 'trunk':
            return False                               # arms of opposite ends
        return True

    E = sorted((D[i, j], i, j) for i in range(n) for j in range(i + 1, n)
               if D[i, j] <= R and allowed(i, j))
    keep = []
    for d, i, j in E:
        if any(len({i, j, a, b}) == 4 and seg_cross(P[i], P[j], P[a], P[b]) for _, a, b in keep):
            continue
        keep.append((d, i, j))
    par = list(range(n))

    def f(a):
        while par[a] != a:
            a = par[a]
        return a
    for _, i, j in keep:
        par[f(i)] = f(j)
    if len({f(i) for i in range(n)}) > 1:
        return None
    deg = np.bincount(np.array([[i, j] for _, i, j in keep]).ravel(), minlength=n)
    if not (34 <= len(keep) <= 42 and 2 <= (deg == 1).sum() <= 5):
        return None
    if min(lab.count(k) for k in keys if k != 'trunk') < 4:
        return None
    adj = [set() for _ in range(n)]
    for _, i, j in keep:
        adj[i].add(j)
        adj[j].add(i)
    h = [99] * n
    q = list(range(ncentre))
    for c in q:
        h[c] = 0
    while q:
        a = q.pop(0)
        for b in adj[a]:
            if h[b] > h[a] + 1:
                h[b] = h[a] + 1
                q.append(b)
    r = np.linalg.norm(P, axis=1)
    for i in range(n):
        for j in range(i + 1, n):
            if j not in adj[i] and D[i, j] < 0.85 * R and not (adj[i] & adj[j]):
                return None
    if any(h[i] > 0 and min(r[j] for j in adj[i] if h[j] == h[i] - 1) > r[i] + 10 for i in range(n)):
        return None

    def tail(i):
        prev, cur, k = None, i, 0
        while deg[cur] < 3 and k < 5:
            nxt = [x for x in adj[cur] if x != prev]
            if not nxt:
                return 99
            prev, cur, k = cur, nxt[0], k + 1
        return k
    if any(deg[i] == 1 and tail(i) > 2 for i in range(n)):
        return None
    across = sum((P[i, 1] < 0) != (P[j, 1] < 0) for _, i, j in keep)
    if across < 2 and rng.random() < 0.75:
        return None
    if abs(int((P[:, 0] < -10).sum()) - int((P[:, 0] > 10).sum())) > 2:
        return None
    bases = {}
    for end, sy in (('H', -1), ('A', 1)):
        half = [i for i in range(n) if lab[i] != 'trunk' and lab[i][0] == end]
        anchor = max(half, key=lambda i: np.linalg.norm(P[i]))
        arm = lab[anchor]
        idx = [i for i in range(n) if lab[i] == arm]
        out = P[anchor] / np.linalg.norm(P[anchor])
        bp = P[anchor] + out * 28
        if np.linalg.norm(P - bp, axis=1).min() < 24:
            return None
        near = sorted(idx, key=lambda i: np.linalg.norm(P[i] - bp))[:2]
        links = [i for i in near if np.linalg.norm(P[i] - bp) <= R] or near[:1]
        bases[end] = (P[anchor], out, links)

    def hub_dist(starts):
        seen = {x: 1 for x in starts}
        q = list(starts)
        while q:
            a = q.pop(0)
            if deg[a] >= 3:
                return seen[a]
            for b in adj[a]:
                if b not in seen:
                    seen[b] = seen[a] + 1
                    q.append(b)
        return 99
    if any(hub_dist(links) > 2 for _, _, links in bases.values()):
        return None
    return P, [(i, j) for _, i, j in keep], bases


# ---- hexes ---------------------------------------------------------------
# Wesnoth's hexes sit on a grid 3/4 of a hex apart across and 1 apart down,
# even columns half a hex lower; distances here are in hexes (row heights).

def centre(x, y):
    return 0.75 * x, y + (0.5 if x % 2 == 0 else 0)


def neighbours(x, y):
    d = 0 if x % 2 == 0 else -1
    return [(x, y - 1), (x, y + 1), (x - 1, y + d), (x - 1, y + d + 1),
            (x + 1, y + d), (x + 1, y + d + 1)]


def snap(px, py):
    """The hex whose centre is nearest a point given in hexes."""
    best = None
    x0 = round(px / 0.75)
    for x in range(x0 - 1, x0 + 2):
        for y in range(math.floor(py) - 1, math.floor(py) + 2):
            cx, cy = centre(x, y)
            d = (cx - px) ** 2 + (cy - py) ** 2
            if best is None or d < best[0]:
                best = (d, x, y)
    return best[1], best[2]


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def on_hexes(P, E, bases, push):
    """The cluster laid on the map: planets, starbases and the open hexes,
    or None if it doesn't fit."""
    ox, oy = 0.75 * (W + 1) / 2, (H + 1) / 2

    def to_hex(p):
        return snap(p[0] / S + ox, p[1] / S + oy)
    planets = [to_hex(p) for p in P]
    ends = {}
    nodes = list(planets)          # planets, then the two starbases
    links = list(E)
    for end in ('H', 'A'):
        anchor, out, blinks = bases[end]
        bp = anchor + out * push[end]
        k = len(nodes)
        nodes.append(to_hex(bp))
        ends[end] = k
        links += [(i, k) for i in blinks]
    if len(set(nodes)) < len(nodes):
        return None

    # what each open hex belongs to: a node (its ring of open space, or a
    # starbase and its docking rings) or a link (its lane)
    owner = {}

    def claim(hexes, tag):
        for hx in hexes:
            owner.setdefault(hx, set()).add(tag)
    rings = {}
    for k, (x, y) in enumerate(nodes):
        claim([(x, y)] + (neighbours(x, y) if RING or k >= len(planets) else []), ("n", k))
    for end, k in ends.items():
        # docking rings: the 3 hexes round the starbase nearest the centre
        x, y = nodes[k]
        cx, cy = centre(x, y)
        nb = sorted(neighbours(x, y),
                    key=lambda h: math.hypot(centre(*h)[0] - ox, centre(*h)[1] - oy))
        rings[end] = nb[:3]
    for li, (i, j) in enumerate(links):
        a, b = centre(*nodes[i]), centre(*nodes[j])
        xs = sorted([a[0], b[0]])
        ys = sorted([a[1], b[1]])
        lane = []
        for x in range(int(xs[0] / 0.75) - 2, int(xs[1] / 0.75) + 3):
            for y in range(int(ys[0]) - 2, int(ys[1]) + 3):
                if seg_dist(centre(x, y), a, b) <= LANE:
                    lane.append((x, y))
        claim(lane, ('l', li))
    for (x, y) in owner:
        if not (1 + MARGIN <= x <= W - MARGIN and 1 + MARGIN <= y <= H - MARGIN):
            return None

    # every open hex, and every two open hexes side by side, may only join
    # things that are linked: a node and its own links, links that share a
    # node, a link and its own nodes
    def related(s, t):
        if s == t:
            return True
        if s[0] == 'n' and t[0] == 'n':
            return False
        if s[0] == 'l' and t[0] == 'l':
            return bool(set(links[s[1]]) & set(links[t[1]]))
        n_, l_ = (s, t) if s[0] == 'n' else (t, s)
        return n_[1] in links[l_[1]]

    for hx, tags in owner.items():
        tl = list(tags)
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                if not related(tl[i], tl[j]):
                    return None
        for nb in neighbours(*hx):
            for s in tags:
                for t in owner.get(nb, ()):
                    if not related(s, t):
                        return None
    # each half of the map: the 14 planets nearest each starbase's end
    order = sorted(range(len(planets)), key=lambda i: P[i][1])
    top = set(order[:len(planets) // 2])
    # holdings: the planets nearest the starbase in jumps, then in distance
    adj = {}
    for i, j in links:
        adj.setdefault(i, set()).add(j)
        adj.setdefault(j, set()).add(i)

    def home_order(end):
        k = ends[end]
        hop = {k: 0}
        q = [k]
        while q:
            a = q.pop(0)
            for b in adj[a]:
                if b not in hop:
                    hop[b] = hop[a] + 1
                    q.append(b)
        bx, by = centre(*nodes[k])
        return sorted(range(len(planets)), key=lambda i: (hop[i], math.hypot(
            centre(*planets[i])[0] - bx, centre(*planets[i])[1] - by)))
    return {
        'planets': planets,
        'top': top,
        'keeps': {end: nodes[k] for end, k in ends.items()},
        'rings': rings,
        'home': {end: home_order(end)[:HOME] for end in ends},
        'open': sorted(owner),
        'links': links,
    }


def make(seed):
    rng = np.random.default_rng(seed)
    for _ in range(4000):
        c = cluster(rng)
        if c is None:
            continue
        # starbases just beyond the outermost planet, pushed further out if
        # their docking rings would touch a planet or lane
        for ph, pa in sorted(((ph, pa) for ph in PUSH for pa in PUSH), key=sum):
            m = on_hexes(*c, {'H': ph, 'A': pa})
            if m is not None:
                return seed, m
    return seed, None


# ---- output --------------------------------------------------------------

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def crop(layouts):
    """Shrink the map to fit every layout, mirrored or not, MARGIN hexes
    clear of the edge. Columns move by an even number so the hexes keep
    their places; the width stays odd so a mirror image is exact."""
    xs = [x for m in layouts for x, _ in m['open']]
    ys = [y for m in layouts for _, y in m['open']]
    # mirrored, x goes to w + 1 - x, which stays clear of the edges as
    # long as x does
    dx = (min(xs) - (1 + MARGIN)) // 2 * 2
    w = max(xs) - dx + MARGIN
    w += 1 - w % 2
    dy = min(ys) - (1 + MARGIN)
    h = max(ys) - dy + MARGIN

    def mv(hx):
        return (hx[0] - dx, hx[1] - dy)
    out = []
    for m in layouts:
        out.append({
            'planets': [mv(p) for p in m['planets']],
            'top': m['top'],
            'keeps': {e: mv(k) for e, k in m['keeps'].items()},
            'rings': {e: [mv(r) for r in rs] for e, rs in m['rings'].items()},
            'home': m['home'],
            'open': [mv(o) for o in m['open']],
        })
    return out, w, h


def enc(hexes):
    return "".join(ALPHABET[x] + ALPHABET[y] for x, y in hexes)


def lua(layouts, w, h):
    out = ["-- Star Control 1 clusters for the SC1 missions, written by",
           "-- tools/make_sc1_clusters.py: do not edit by hand. Hexes are strings",
           "-- of 2-character x,y pairs (0-9, A-Z, a-z = 0..61).",
           "--   planets  every planet; top: those in the Hierarchy's (north) half",
           f"--   home_h, home_a  the {HOME} planets nearest each starbase, nearest first",
           "--   keep_h, keep_a  the starbases; rings_h, rings_a  their docking rings",
           "--   open  every hex of open space: planets, lanes and starbases",
           "return {",
           f"\twidth = {w}, height = {h},", "\tclusters = {"]
    for m in layouts:
        pl = m['planets']
        out.append("\t\t{")
        out.append(f'\t\t\tplanets = "{enc(pl)}",')
        out.append(f'\t\t\ttop = "{enc([pl[i] for i in sorted(m["top"])])}",')
        for end in ('H', 'A'):
            e = end.lower()
            out.append(f'\t\t\thome_{e} = "{enc([pl[i] for i in m["home"][end]])}",')
            out.append(f'\t\t\tkeep_{e} = "{enc([m["keeps"][end]])}",')
            out.append(f'\t\t\trings_{e} = "{enc(m["rings"][end])}",')
        out.append(f'\t\t\topen = "{enc(m["open"])}",')
        out.append("\t\t},")
    out += ["\t},", "}", ""]
    return "\n".join(out)


def map_file(m, w, h, rng):
    """A map of one layout as First Encounter deals it: each side a colony
    and a mine nearest its starbase, the other planets of its half half
    life, half mineral."""
    grid = [["Yqd"] * (w + 2) for _ in range(h + 2)]
    for x, y in m['open']:
        grid[y][x] = "Ys"
    pl = m['planets']
    holdings = {pl[i] for end in ('H', 'A') for i in m['home'][end][:2]}
    for half in (m['top'], set(range(len(pl))) - m['top']):
        free = [i for i in sorted(half) if pl[i] not in holdings]
        types = ["l", "m"] * (len(free) // 2) + ["l"] * (len(free) % 2)
        rng.shuffle(types)
        for i, t in zip(free, types):
            x, y = pl[i]
            grid[y][x] = "Ys^Vy" + t
    for end in ('H', 'A'):
        a, b = (pl[i] for i in m['home'][end][:2])
        grid[a[1]][a[0]] = "Ys^Vyl"
        grid[b[1]][b[0]] = "Ys^Vym"
        x, y = m['keeps'][end]
        grid[y][x] = ("1 " if end == 'H' else "2 ") + "Yk"
        for x, y in m['rings'][end]:
            grid[y][x] = "Yc"
    return "\n".join(", ".join(r) for r in grid) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("count", nargs="?", type=int, default=100)
    ap.add_argument("--maps", help="also write every layout as a .map file here")
    ap.add_argument("--first-seed", type=int, default=1)
    a = ap.parse_args()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    layouts = []
    seed = a.first_seed
    with Pool() as pool:
        while len(layouts) < a.count:
            batch = range(seed, seed + 2 * (a.count - len(layouts)) + 4)
            seed = batch[-1] + 1
            for s, m in pool.imap(make, batch):
                if m is not None and len(layouts) < a.count:
                    layouts.append(m)
                    print(f"seed {s}: cluster {len(layouts)}", file=sys.stderr)
    layouts, w, h = crop(layouts)
    with open(os.path.join(here, "lua", "sc1_clusters.lua"), "w") as f:
        f.write(lua(layouts, w, h))
    # the map the lobby shows: the first layout (each game draws its own)
    rng = np.random.default_rng(0)
    with open(os.path.join(here, "maps", "2p_SC1_Cluster.map"), "w") as f:
        f.write(map_file(layouts[0], w, h, rng))
    if a.maps:
        os.makedirs(a.maps, exist_ok=True)
        for i, m in enumerate(layouts, 1):
            with open(os.path.join(a.maps, f"cluster-{i:03d}.map"), "w") as f:
                f.write(map_file(m, w, h, rng))


if __name__ == "__main__":
    main()
