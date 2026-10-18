"""Star Control 1 style star clusters for the SC1 missions (used by
tools/make_sc1_maps.py), and Wesnoth hex helpers.

How a cluster is drawn, following D's notes on Star Control 1's maps: an X
shape, a short trunk through the middle (2 or 3 planets near the centre so
the middle is not always a one-planet choke) and two arms at each end.
Planets are linked to every planet within a fixed range, shortest links
first, never crossing another link; the two arms of one end only link near
their fork, arms of opposite ends never. A cluster is kept only if

  - it is all connected, with 34-42 links and 2-5 dead ends, and every arm
    has 4 planets or more;
  - planets that look close are close in links too (share a neighbour);
  - no planet curls back: its route toward the centre gets closer to it;
  - a dead end is at most 2 links from a planet with 3+ links;
  - mostly 2+ links cross the middle (one in four may have a single choke);
  - the left and right halves differ by at most 2 planets;
  - each starbase, placed beyond the planet of its half farthest from the
    centre, is at most 2 jumps from a planet with 3+ links.

Needs numpy.
"""

import math

import numpy as np

N = 28                 # planets: 12 free worlds a side, plus a colony and a mine
L = 480                # cluster length (top tip to bottom tip)
DMIN = 46              # closest two planets may be
R = 76                 # link range
JITTER = 34            # how far planets stray from the skeleton


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
