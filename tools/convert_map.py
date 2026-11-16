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
    a big block of debris disk or dark     -> void                Yv
      nebula that reaches the map's edge
    a big clump of debris disk, gravity    -> its centrepiece in the middle: a
      eddy, dark nebula or plasma storm       supergiant, a supermassive black
                                              hole, a dark star or a storm sun
                                              (4 hexes, or 3, or a one-hex star
                                              or black hole), following the
                                              map's symmetry (see centrepieces)

Starting positions are kept.

lua/space.lua does the same in-game, for any map played with the era;
keep the two in step.

Usage: convert_map.py <wesnoth .map> <output .map> [X,Y=CODE ...]

Each X,Y=CODE puts that terrain on hex X,Y (game coordinates) afterwards,
for things the original scenario placed as units: Caves of the Basilisk's
statues became black holes (Ys^Yxb).
"""

import collections
import math
import re
import sys

from assign_planet_types import assign_file


VOID_MIN = 6                                # play-area hexes in a block to void it
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


# Centrepieces. Every big clump of impassable cloud gets its matching object
# in the middle, as on the hand-made maps: a supergiant behind a debris
# disk, a supermassive black hole in a gravity eddy, a dark star in a dark
# nebula, a big storm sun in a plasma storm. The object fills a diamond of
# 4 hexes where one fits well inside the clump, else a triangle of 3, else
# it is a one-hex star or black hole. It only takes hexes of the clump,
# which are impassable either way, so the map plays the same. A clump of
# 2 * PER_PIECE hexes or more gets one more piece for each PER_PIECE, at
# least SPACING hexes apart. Void (Yv) is left alone, and so is a clump that
# already has a piece. The pieces follow the map's symmetry: where a mirror
# or a rotation maps the impassable hexes onto each other (to within a
# hex), the clumps that match each other get the same piece in the same
# look (each in its own kind of cloud), each at the matching place.
CLOUDS = {"Ys^Yw": "w", "Yqe": "e", "Yqd": "d", "Yqp": "p"}
PIECES = {                         # kind -> {hexes: looks}
    "w": {4: ["^Ysg", "^Ysg2", "^Ysg3", "^Ysg4"],
          3: ["^Ytd1", "^Ytd2", "^Ytd3", "^Ytd4", "^Ytd5", "^Ytd6"],
          1: ["^Yxd1", "^Yxd2", "^Yxd3", "^Yxd4", "^Yxd5"]},
    "e": {4: ["^Ybh1", "^Ybh2", "^Ybh3", "^Ybh4", "^Ybh5", "^Ybh6"],
          3: ["^Ytbh"], 1: ["^Yxb1", "^Yxb2", "^Yxb3", "^Yxb4"]},
    "d": {4: ["^Yds1", "^Yds2", "^Yds3", "^Yds4"], 3: ["^Ytds"], 1: ["^Yx"]},
    "p": {4: ["^Ygg"], 1: ["^Yxs1", "^Yxs2", "^Yxs3", "^Yxs4", "^Yxs5", "^Yxs6"]},
}
SIZES = (4, 3, 1)
MIN_CLUMP = {4: 8, 3: 6, 1: 5}     # clump hexes needed for each size of piece
PER_PIECE, SPACING = 25, 4
SYM_MIN = 0.7                      # share of impassable hexes a symmetry must match
S3 = math.sqrt(3)
# cos and sin of k * 60 degrees, exact (so the in-game copy rounds the same)
COS = (1, 0.5, -0.5, -1, -0.5, 0.5)
SIN = (0, S3 / 2, S3 / 2, 0, -S3 / 2, -S3 / 2)


def cloud_kind(code):
    """'w', 'e', 'd' or 'p' for an impassable cloud hex, or a piece already
    in one, else None."""
    if code in CLOUDS:
        return CLOUDS[code]
    base, _, overlay = code.partition("^")
    if base == "Ys" and overlay[:3] in ("Ysg", "Ytd", "Yxd"):
        return "w"
    if base in ("Yqe", "Yqd", "Yqp") and overlay:
        return CLOUDS[base]
    return None


def hex_distance(a, b):
    def cube(x, y):                    # odd columns sit higher
        return x, y - (x - (x & 1)) // 2
    (ax, az), (bx, bz) = cube(*a), cube(*b)
    return max(abs(ax - bx), abs(az - bz), abs(ax + az - bx - bz))


def centre(p):
    """A hex's middle, 1 = the distance between neighbours."""
    return p[0] * S3 / 2, p[1] + (p[0] + 1) % 2 / 2


def nearest_hex(px, py):
    x = math.floor(px / (S3 / 2) + 0.5)
    return x, math.floor(py - (x + 1) % 2 / 2 + 0.5)


def symmetry(w, h, imp):
    """The powers (but the identity) of the mirror or rotation of the play
    area that best maps the impassable hexes `imp` onto or next to
    impassable hexes, as functions (x, y) -> (x, y) on points; [] if none
    matches SYM_MIN of them. w, h include the border."""
    play = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1)]
    mx = sum(centre(p)[0] for p in play) / len(play)
    my = sum(centre(p)[1] for p in play) / len(play)

    def make(a, b, c, d):
        return lambda px, py: (mx + a * (px - mx) + b * (py - my), my + c * (px - mx) + d * (py - my))
    groups = []
    for k in range(1, 6):              # rotations by k * 60 degrees
        groups.append([make(COS[j * k % 6], -SIN[j * k % 6], SIN[j * k % 6], COS[j * k % 6])
                       for j in range(1, 6 // math.gcd(k, 6))])
    for k in range(6):                 # mirrors, the axis at k * 30 degrees
        groups.append([make(COS[k], SIN[k], SIN[k], -COS[k])])
    near = imp | {q for p in imp for q in neighbours(*p)}
    best, best_score = [], SYM_MIN * len(imp)
    for g in groups:
        score = sum(1 for p in imp if nearest_hex(*g[0](*centre(p))) in near)
        if score > best_score:
            best, best_score = g, score
    return best


def shapes(clump, size):
    """Every diamond (4), triangle (3) or single hex (1) inside a set of
    hexes, each a tuple of hexes in reading order."""
    def key(h):
        return h[1], h[0]
    if size == 1:
        return sorted(((p,) for p in clump), key=lambda s: key(s[0]))
    out = set()
    for p in clump:
        ns = [q for q in neighbours(*p) if q in clump]
        for q in ns:
            common = [r for r in neighbours(*q) if r in ns]
            if size == 3:
                out.update(tuple(sorted((p, q, r), key=key)) for r in common)
            elif len(common) == 2:
                out.add(tuple(sorted((p, q, *common), key=key)))
    return sorted(out, key=lambda s: [key(h) for h in s])


def centrepieces(grid):
    h, w = len(grid), len(grid[0])

    def playable(p):
        return 1 <= p[0] <= w - 2 and 1 <= p[1] <= h - 2
    kind = {}
    for y in range(h):
        for x in range(w):
            k = cloud_kind(grid[y][x][1])
            if k:
                kind[x, y] = k
    clump_of, clumps = {}, []
    for y in range(h):
        for x in range(w):
            if (x, y) not in kind or (x, y) in clump_of:
                continue
            block = [(x, y)]
            clump_of[x, y] = len(clumps)
            for p in block:
                for q in neighbours(*p):
                    if q not in clump_of and kind.get(q) == kind[x, y]:
                        clump_of[q] = len(clumps)
                        block.append(q)
            clumps.append(block)
    maps = symmetry(w, h, {p for p in kind if playable(p)})
    placed, looks = [], collections.Counter()

    def candidates(i, size):
        """Where a piece of this size can go in clump i, best first: well
        inside the clump, near its middle, away from the other pieces."""
        clump = clumps[i]
        n = len(clump)
        if n < MIN_CLUMP[size] or size not in PIECES[kind[clump[0]]]:
            return []
        sx = sum(x for x, y in clump)
        sy = sum(2 * y + (x + 1) % 2 for x, y in clump)
        out = []
        for s in shapes({p for p in clump if playable(p)}, size):
            if any(hex_distance(p, q) < SPACING for p in s for q in placed):
                continue
            ring = {q for p in s for q in neighbours(*p)} - set(s)
            cover = sum(1 for q in ring if clump_of.get(q) == i)
            if 2 * cover < len(ring) if size > 1 else cover < 2:
                continue
            mid = (3 * (n * sum(x for x, y in s) - size * sx) ** 2
                   + (n * sum(2 * y + (x + 1) % 2 for x, y in s) - size * sy) ** 2)
            out.append(((-cover, mid), s))
        out.sort(key=lambda c: c[0])
        return [s for _, s in out]

    def put(s, look):
        for x, y in s:
            grid[y][x][1] = grid[y][x][1].partition("^")[0] + look
        placed.extend(s)

    # the clumps that match each other under the symmetry, biggest first
    done = {i for i, c in enumerate(clumps) if any(grid[y][x][1] not in CLOUDS for x, y in c)}
    for i in sorted(range(len(clumps)), key=lambda i: (-len(clumps[i]), clumps[i][0][1], clumps[i][0][0])):
        if i in done:
            continue
        mates = []                    # (clump, map) for each image
        for m in maps:
            hits = collections.Counter(
                clump_of.get(nearest_hex(*m(*centre(p)))) for p in clumps[i] if playable(p))
            hits.pop(None, None)
            j = min(hits, key=lambda j: (-hits[j], j)) if hits else None
            if j is not None and j not in done:
                mates.append((j, m))
        done.add(i)
        done.update(j for j, _ in mates)
        for _ in range(max(1, len(clumps[i]) // PER_PIECE)):
            for size in SIZES:
                cands = candidates(i, size)
                if not cands:
                    continue
                s = cands[0]
                copies = []
                for j, m in mates:
                    # the mate's spot nearest the image of this piece's middle
                    tx, ty = m(sum(centre(p)[0] for p in s) / size, sum(centre(p)[1] for p in s) / size)
                    theirs = [c for c in candidates(j, size) if not set(c) & set(s)]
                    if not theirs:
                        break
                    def miss(c):
                        dx = sum(centre(p)[0] for p in c) / size - tx
                        dy = sum(centre(p)[1] for p in c) / size - ty
                        return dx * dx + dy * dy
                    copies.append((kind[clumps[j][0]], min(theirs, key=miss)))
                else:
                    pieces = [(kind[clumps[i][0]], s)] + copies
                    for k, c in pieces:
                        if any(hex_distance(p, q) < SPACING for p in c for q in placed):
                            continue          # a self-symmetric clump: one piece
                        options = PIECES[k][size]
                        put(c, options[looks[size] % len(options)])
                    looks[size] += 1
                    break
            else:
                break

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
    # Big blocks of debris disk or dark nebula that reach the edge of the
    # map become void (cols, rows here include the border).
    voidable = {"Ys^Yw", "Yqd", "Yv"}
    h, w = len(grid), len(grid[0])
    seen = set()
    for sy in range(h):
        for sx in range(w):
            if grid[sy][sx][1] not in voidable or (sx, sy) in seen:
                continue
            block, edge, inside = [(sx, sy)], False, 0
            seen.add((sx, sy))
            for x, y in block:
                edge |= x <= 1 or y <= 1 or x >= w - 2 or y >= h - 2
                inside += 1 <= x <= w - 2 and 1 <= y <= h - 2
                for nx, ny in neighbours(x, y):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen \
                            and grid[ny][nx][1] in voidable:
                        seen.add((nx, ny))
                        block.append((nx, ny))
            if edge and inside >= VOID_MIN:
                for x, y in block:
                    grid[y][x][1] = "Yv"
    centrepieces(grid)
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
