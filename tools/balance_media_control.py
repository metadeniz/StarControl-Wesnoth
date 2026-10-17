#!/usr/bin/env python3
"""Find BALANCE for make_media_control_4x.py.

Turning the north-west quarter onto the north-east one can't keep every
distance on a hex grid, so this moves the north-east planets, small keep
and start and the north-west planets a hex at a time, and flips nebula
hexes in the north-east (each with its half-turned twin), keeping every
change that brings the moves from each start to the centre, to the other
starts, to each planet and to the keeps nearer to what the player a
quarter turn back has. Several seeds are worth a try; the lowest score
wins.

Usage: balance_media_control.py [seed] [tries]
Prints the score as it goes and BALANCE at the end, to paste into
make_media_control_4x.py.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_media_control_4x as mc4
M = mc4.M
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
g0, keeps, pairs0, info = mc4.assemble()
NE = [(x, y) for x in range(mc4.W) for y in range(mc4.H) if mc4.inside(x, y) and mc4.quad(x, y) == "NE"]
def ring(h): return mc4.ring_index(*h)[0]
FLIPPABLE = [h for h in NE if g0[h[1]][h[0]] in ".n" and 2 <= ring(h) <= 20]
def evaluate(over, flips, small, st=None, nwo=None):
    g, keeps, pairs, info = mc4.assemble(over, flips, small, st, nwo)
    D = [mc4.moves(g, k) for k in keeps]
    f = 0
    c = (mc4.CX, mc4.CY)
    f += 12 * abs(D[0].get(c, 99) - D[1].get(c, 99))
    f += 4 * abs(D[0].get(keeps[1], 99) - D[1].get(keeps[2], 99))
    f += 2 * abs(D[0].get(keeps[2], 99) - D[1].get(keeps[3], 99))
    for h, ne, ch, *_ in pairs:
        d = mc4.vec(D, h); e = mc4.vec(D, ne)
        want = [d[3], d[0], d[1], d[2]]
        f += 3 * abs(e[1] - want[1])
        # nearest rival
        f += 2 * abs(min(e[0], e[2], e[3]) - min(want[0], want[2], want[3]))
        f += 0.5 * sum(abs(e[a] - want[a]) for a in (0, 2, 3))
    ks = [(x, y) for y in range(mc4.H) for x in range(mc4.W) if g[y][x] == "K" and (x, y) not in keeps]
    a = sorted(D[0].get(k, 99) for k in ks); b = sorted(D[1].get(k, 99) for k in ks)
    f += 2 * sum(abs(x - y) for x, y in zip(a[:6], b[:6]))
    # the same for the planets as a whole: each player's sorted planet list
    pl = [(x, y) for y in range(mc4.H) for x in range(mc4.W) if g[y][x] in "pq"]
    pa = sorted(D[0].get(p, 99) for p in pl); pb = sorted(D[1].get(p, 99) for p in pl)
    f += sum(abs(x - y) for x, y in zip(pa[:8], pb[:8]))
    f += 0.4 * len(flips)
    return f, g
over = mc4.balance(rounds=2)
flips = {}; small = {}; st = None; nwo = {}
best, _ = evaluate(over, flips, small, st, nwo)
print("start", best)
for it in range(int(sys.argv[2]) if len(sys.argv) > 2 else 600):
    o2, f2, s2, st2, n2 = dict(over), dict(flips), dict(small), st, dict(nwo)
    r = random.random()
    if r < 0.12:
        h0 = random.choice([h for h, ch in info["planets"] if h not in mc4.FIXED_NE and h not in mc4.PLANET_MOVE.values()])
        cur = n2.get(h0, h0)
        c = random.choice(M.neighbours(*cur))
        if not mc4.inside(*c) or mc4.quad(*c) != "NW" or g0[c[1]][c[0]] not in ".an" or mc4.ring_index(*c)[0] > 0 and abs(sum(a-b for a,b in zip(c,h0)))>4: continue
        n2[h0] = c
    elif r < 0.18:
        cur = st2 or keeps[1]
        c = random.choice(M.neighbours(*cur))
        if not mc4.inside(*c) or mc4.quad(*c) != "NE": continue
        st2 = c
    elif r < 0.35:
        h = random.choice([k for k in o2 if k not in mc4.FIXED_NE]); cur = o2[h]
        c = random.choice(M.neighbours(*cur))
        if not mc4.inside(*c) or mc4.quad(*c) != "NE" or g0[c[1]][c[0]] not in ".an": continue
        o2[h] = c
    elif r < 0.45 and info["small"]:
        s = info["small"][0]; cur = s2.get(s, mc4.rot_ring(*s))
        c = random.choice(M.neighbours(*cur))
        if not mc4.inside(*c) or mc4.quad(*c) != "NE" or g0[c[1]][c[0]] not in ".n": continue
        s2[s] = c
    else:
        h = random.choice(FLIPPABLE)
        if h in f2: del f2[h]
        else: f2[h] = "n" if g0[h[1]][h[0]] == "." else "."
    v, _ = evaluate(o2, f2, s2, st2, n2)
    if v <= best:
        if v < best: print(it, v, len(f2))
        best, over, flips, small, st, nwo = v, o2, f2, s2, st2, n2
print("final", best)
print("BALANCE = " + repr({"over": [[list(k), list(v)] for k, v in over.items()],
                                 "flips": [[list(k), v] for k, v in flips.items()],
                                 "small": [[list(k), list(v)] for k, v in small.items()],
                                 "start": list(st) if st else None,
                                 "nwo": [[list(k), list(v)] for k, v in nwo.items()]}))
