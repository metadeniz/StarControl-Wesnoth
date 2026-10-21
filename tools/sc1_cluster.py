"""Star Control 1's own star cluster generator, for the SC1 missions (used by
tools/make_sc1_maps.py), and Wesnoth hex helpers.

generate_cluster() is SC1's generator, ported from STARCON.EXE (0628:216C)
with the Microsoft C rand() it calls (214F:0112) by the starcon1-map-prototype
project (src/generation/sc1Cluster.ts); a given seed builds the same cluster
the game would. Stars are points in a cylinder: x runs along it (the
Hierarchy's half 10-94, the Alliance's 96-180, the first star at 95), y and z
lie in a disc of radius 118. Stars are placed one at a time, the sides taking
turns, by rejection sampling, and two stars are linked exactly when they are
closer than 38; none are closer than 20, no pair is 38-60 apart and no star
has more than 4 links.

flatten_cluster() is the prototype's flatLayout.ts: it only decides where the
stars are drawn. Links keep SC1's 20-38 lengths, every star stays in its own
half and roughly as near the middle as SC1 put it, and the first star sits in
the exact middle.
"""

import math


class MscRand:
    """Microsoft C runtime rand(): a 32-bit LCG returning bits 16-30."""

    def __init__(self, seed):
        self.state = seed & 0xFFFF   # srand() keeps a 16-bit seed

    def next(self):
        self.state = (self.state * 214013 + 2531011) & 0xFFFFFFFF
        return (self.state >> 16) & 0x7FFF


MIN_DIST = 20      # closer than this to any star: position rejected
LINK_MAX = 38      # at least MIN_DIST and closer than this: linked
GAP_MAX = 60       # at least LINK_MAX and closer than this: rejected
WINDOW = 40        # only stars within this on every axis are checked
MAX_NEW_LINKS = 3  # a new star links to at most this many...
MAX_LINKS = 4      # ...and no star ever has more than this many
RADIUS = 118
CENTRE = 95        # x of the first star, where the halves meet
FRONT = 47         # stars nearer the centre (in x) than this are a side's front


class Star:
    def __init__(self, index, x, y, z, side):
        self.index, self.x, self.y, self.z, self.side = index, x, y, z, side
        self.links = []

    def __repr__(self):
        return f"Star({self.index}, {self.x}, {self.y}, {self.z}, {self.side})"


def generate_cluster(rng, count_a, count_b):
    """SC1's cluster: count_a stars on the high-x half (A, the Alliance's),
    count_b on the low-x half (B, the Hierarchy's). Sides alternate
    placements (even ones go to A) until one runs out, as in SC1."""
    total = count_a + count_b
    if not 2 <= total <= 50:
        raise ValueError(f"SC1 clusters need 2-50 stars, got {total}")
    lst = []   # kept sorted by x, as the original scans it
    for i in range(total):
        first = i == 0
        while True:
            if first:
                x, y, z = CENTRE, 10, rng.next() % 20
                first = False
            else:
                x = rng.next() % 85 + 10
                if count_a != 0 and ((i & 1) == 0 or count_b == 0):
                    x += 86
                while True:
                    y = rng.next() % 236 - 118
                    z = rng.next() % 236 - 118
                    if not ((y == 0 and z == 0) or y * y + z * z > RADIUS ** 2):
                        break
            cand, insert_at, ok = [], -1, True
            for k, s in enumerate(lst):
                dx = s.x - x
                if dx < -WINDOW:
                    continue
                if dx == 0:
                    ok = False   # no two stars share an x
                    break
                if dx > 0:
                    if insert_at < 0:
                        insert_at = k
                    if dx > WINDOW:
                        break
                if abs(s.y - y) > WINDOW or abs(s.z - z) > WINDOW:
                    continue
                d2 = dx * dx + (s.y - y) ** 2 + (s.z - z) ** 2
                if d2 < MIN_DIST ** 2:
                    ok = False
                    break
                if d2 < LINK_MAX ** 2:
                    if len(cand) == MAX_NEW_LINKS or len(s.links) == MAX_LINKS:
                        ok = False
                        break
                    cand.append(s)
                elif d2 < GAP_MAX ** 2:
                    ok = False   # near miss
                    break
            if not ok:
                continue
            if i != 0:
                if not cand:
                    continue   # must connect to the cluster
                if i <= 4 and len(cand) < (i + 1) >> 1:
                    continue   # stars 3 and 4 need two links
            break
        if count_b != 0 and ((i & 1) != 0 or count_a == 0):
            count_b -= 1
            side = 'B'
        else:
            count_a -= 1
            side = 'A'
        star = Star(i, x, y, z, side)
        for c in cand:
            star.links.append(c)
            c.links.append(star)
        if insert_at < 0:
            lst.append(star)
        else:
            lst.insert(insert_at, star)
    # SC1 then rolls three name numbers per star; keep rand() in step
    for _ in range(len(lst) * 3):
        rng.next()
    return sorted(lst, key=lambda s: s.index)


def is_front(star):
    return abs(star.x - CENTRE) < FRONT


# ---- flat layout (the prototype's flatLayout.ts) --------------------------

ANGLES = 36          # views round the long axis tried as starting points
TRIES = 4            # best starting views relaxed in full
SIDE_GAP = 6         # stars stay this far from the centre line, on their side
APART = 32           # stars that aren't linked stay this far apart
LINK_CLEARANCE = 14  # and this far from a link they aren't part of
LONG_LINK = 42


def _edges(stars):
    return [(s, t) for s in stars for t in s.links if t.index > s.index]


def _nearest_on_segment(p, a, b):
    da, dc = b[0] - a[0], b[1] - a[1]
    l2 = da * da + dc * dc or 1
    t = max(0, min(1, ((p[0] - a[0]) * da + (p[1] - a[1]) * dc) / l2))
    return a[0] + t * da, a[1] + t * dc


def _sign(v):
    return (v > 0) - (v < 0)


def _orient(p, q, r):
    return _sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))


def _crosses(a, b, c, d):
    return _orient(a, b, c) * _orient(a, b, d) < 0 and _orient(c, d, a) * _orient(c, d, b) < 0


def layout_flaws(stars, pos):
    """(long links, stars on links, crowded pairs, crossings)."""
    edges = _edges(stars)
    crossings = 0
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a, b = edges[i]
            c, d = edges[j]
            if a is c or a is d or b is c or b is d:
                continue
            if _crosses(pos[a], pos[b], pos[c], pos[d]):
                crossings += 1
    crowded = 0
    for i in range(len(stars)):
        for j in range(i + 1, len(stars)):
            if stars[j] not in stars[i].links and math.dist(pos[stars[i]], pos[stars[j]]) < 25:
                crowded += 1
    on_link = 0
    for s in stars:
        for a, b in edges:
            if s is a or s is b:
                continue
            p = pos[s]
            if math.dist(p, _nearest_on_segment(p, pos[a], pos[b])) < 10:
                on_link += 1
    long_links = sum(math.dist(pos[a], pos[b]) > LONG_LINK for a, b in edges)
    return long_links, on_link, crowded, crossings


def _score(stars, pos):
    long_links, on_link, crowded, crossings = layout_flaws(stars, pos)
    return long_links * 5 + on_link * 4 + crowded * 4 + crossings


def _view(stars, step):
    angle = step * math.pi / ANGLES
    c, s = math.cos(angle), math.sin(angle)
    return {t: (t.x - CENTRE, t.y * c - t.z * s) for t in stars}


def _relax(stars, start):
    n = len(stars)
    along = [start[s][0] for s in stars]
    across = [start[s][1] for s in stars]
    home = [s.x - CENTRE for s in stars]
    side_a = [s.side == 'A' for s in stars]
    fixed = [s.index == 0 for s in stars]
    slot = {s: i for i, s in enumerate(stars)}
    linked = [[False] * n for _ in range(n)]
    target = [[0.0] * n for _ in range(n)]
    edges = []
    for a, b in _edges(stars):
        i, j = slot[a], slot[b]
        linked[i][j] = linked[j][i] = True
        target[i][j] = target[j][i] = math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)
        edges.append((i, j))
    for i in range(n):
        if fixed[i]:
            along[i] = across[i] = 0.0

    def keep_to_side(i):
        along[i] = max(along[i], SIDE_GAP) if side_a[i] else min(along[i], -SIDE_GAP)

    def nearest(k, i, j):
        da, dc = along[j] - along[i], across[j] - across[i]
        t = max(0, min(1, ((along[k] - along[i]) * da + (across[k] - across[i]) * dc) / (da * da + dc * dc or 1)))
        return along[i] + t * da, across[i] + t * dc

    # 1. springs: links pull toward their SC1 length, other stars push apart,
    #    every star drawn gently back toward its SC1 distance from the centre
    rounds = 150
    for rnd in range(rounds):
        step = 1 - rnd / rounds + 0.1
        fa = [0.0] * n
        fc = [0.0] * n
        for i in range(n):
            for j in range(i + 1, n):
                d = math.hypot(along[j] - along[i], across[j] - across[i]) or 0.01
                if linked[i][j]:
                    k = (d - target[i][j]) * 0.5
                elif d < 48:
                    k = -(48 - d) * 0.3
                else:
                    continue
                if k == 0:
                    continue
                ua = (along[j] - along[i]) / d * k
                uc = (across[j] - across[i]) / d * k
                fa[i] += ua
                fc[i] += uc
                fa[j] -= ua
                fc[j] -= uc
        for k in range(n):
            for i, j in edges:
                if k == i or k == j:
                    continue
                qa, qc = nearest(k, i, j)
                d = math.hypot(along[k] - qa, across[k] - qc) or 0.01
                if d >= 16:
                    continue
                ua = (along[k] - qa) / d * (16 - d) * 0.3
                uc = (across[k] - qc) / d * (16 - d) * 0.3
                fa[k] += ua
                fc[k] += uc
                fa[i] -= ua / 2
                fc[i] -= uc / 2
                fa[j] -= ua / 2
                fc[j] -= uc / 2
        for i in range(n):
            if fixed[i]:
                continue
            fa[i] += (home[i] - along[i]) * 0.02
            size = math.hypot(fa[i], fc[i])
            scale = (6 / size if size > 6 else 1) * step
            along[i] += fa[i] * scale
            across[i] += fc[i] * scale
            keep_to_side(i)

    # 2. hard limits: stars apart and off other links, links within 20-38
    def move(i, da, dc):
        if fixed[i]:
            return
        along[i] += da
        across[i] += dc
        keep_to_side(i)

    def hold(i, j, lo, hi):
        d = math.hypot(along[j] - along[i], across[j] - across[i]) or 0.01
        goal = min(max(d, lo), hi)
        if goal == d:
            return
        share = (d - goal) / d / (1 if fixed[i] or fixed[j] else 2)
        da, dc = (along[j] - along[i]) * share, (across[j] - across[i]) * share
        move(i, da, dc)
        move(j, -da, -dc)

    for _ in range(80):
        for i in range(n):
            for j in range(i + 1, n):
                if not linked[i][j]:
                    hold(i, j, APART, math.inf)
        for k in range(n):
            for i, j in edges:
                if k == i or k == j:
                    continue
                qa, qc = nearest(k, i, j)
                d = math.hypot(along[k] - qa, across[k] - qc) or 0.01
                if d >= LINK_CLEARANCE:
                    continue
                f = (LINK_CLEARANCE - d) / d / 2
                da, dc = (along[k] - qa) * f, (across[k] - qc) * f
                move(k, da, dc)
                move(i, -da / 2, -dc / 2)
                move(j, -da / 2, -dc / 2)
        for i, j in edges:
            hold(i, j, MIN_DIST, LINK_MAX)
    return {s: (along[i], across[i]) for i, s in enumerate(stars)}


def flatten_cluster(stars):
    """{star: (along, across)} in SC1 units, the first star at (0, 0);
    along is SC1's x (the Alliance's half positive)."""
    def key(step):
        long_links, on_link, crowded, crossings = layout_flaws(stars, _view(stars, step))
        return crossings * 3 + crowded + on_link
    starts = sorted(range(ANGLES), key=key)[:TRIES]
    best, best_score = None, math.inf
    for step in starts:
        pos = _relax(stars, _view(stars, step))
        s = _score(stars, pos)
        if s < best_score:
            best, best_score = pos, s
    return best


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
