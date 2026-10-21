"""Read pictures out of Star Control 1's (DOS) resource packages.

STARCON.PKG indexes the resources: from offset 0x18, 8-byte entries of
[package (0x00 SETUP.PKG, 0x20 TACTICS.PKG, ...)] [0] [3-byte LE offset]
[0xff] [a] [b]. At each offset is a chain of resources, one after the
other: each a 2-byte type (06 00 imploded, 00 00 stored), a 4-byte
big-endian unpacked size, then the data. Imploded data is PKZIP "implode"
with 2 trees, a 4K dictionary and 8-bit raw literals.

Pictures are "IANM" resources:
    "IANM", frame count n (BE word), bits per pixel (BE word: 4 or 1),
    n x (width, height) (BE words), then for each frame:
    hotspot x, y (signed BE words: the frame is drawn at -x, -y),
    flags (BE word: high byte 1 = 48 bytes of colour tables follow,
    low byte = the colour index left transparent when drawn over
    another frame), the tables, then the pixels, packed rows (4 bpp:
    high nibble first, rows padded to a byte).
The colour tables are 16 bytes each for CGA, EGA and Tandy/VGA; in the
EGA one, each of the 16 colours is a pair of EGA colours (high and low
nibble), dithered in a checkerboard, as the game shows them in EGA.

The planet scenes of the status panel's picture box (54x36) are the chain
at TACTICS.PKG 0x0ba37 (STARCON.PKG's 5th TACTICS entry), three resources
per scene: its still picture, then two animations drawn over it. Scenes
0 and 1 are the fortification on a dead world (0's second animation: it
destroyed), 2 and 3 the mine (2's second: destroyed), 4 and 5 the colony
(4's second: destroyed), 6 the starbase, 7 a Syreen taking a colony,
8 the Precursor artifact.
"""

import struct

from PIL import Image

EGA = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170),
       (170, 85, 0), (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85),
       (85, 255, 255), (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255)]
SCENES = 0x0ba37


def read_tree(d, p, nsym):
    n = d[p] + 1
    p += 1
    lens = []
    for b in d[p:p + n]:
        lens += [(b & 15) + 1] * ((b >> 4) + 1)
    p += n
    assert len(lens) == nsym, (len(lens), nsym)
    order = sorted(range(nsym), key=lambda i: (lens[i], i))
    codes = {}
    code = inc = last = 0
    for i in reversed(order):
        code = (code + inc) & 0xffff
        if lens[i] != last:
            last = lens[i]
            inc = 1 << (16 - last)
        codes[(lens[i], code >> (16 - lens[i]))] = i
    return codes, p


class Bits:
    def __init__(self, d, p):
        self.d, self.p, self.buf, self.n = d, p, 0, 0

    def get(self, k):
        while self.n < k:
            self.buf |= (self.d[self.p] if self.p < len(self.d) else 0) << self.n
            self.p += 1
            self.n += 8
        v = self.buf & ((1 << k) - 1)
        self.buf >>= k
        self.n -= k
        return v


def decode(bits, codes):
    c = 0
    for length in range(1, 17):
        c = (c << 1) | bits.get(1)
        if (length, c) in codes:
            return codes[(length, c)]
    raise ValueError("bad code")


def explode(d, p, size):
    """Unpack size bytes from p; also returns where the packed data ends."""
    lt, p = read_tree(d, p, 64)
    dt, p = read_tree(d, p, 64)
    b = Bits(d, p)
    out = bytearray()
    while len(out) < size:
        if b.get(1):
            out.append(b.get(8))
        else:
            low = b.get(6)
            dist = (decode(b, dt) << 6) | low
            n = decode(b, lt)
            if n == 63:
                n += b.get(8)
            for _ in range(n + 2):
                out.append(out[-dist - 1] if dist < len(out) else 0)
    return bytes(out[:size]), b.p


def chain(pkg, offset, count):
    """The first count resources of the chain at offset in pkg's bytes."""
    out = []
    for _ in range(count):
        kind, size = pkg[offset:offset + 2], struct.unpack(">I", pkg[offset + 2:offset + 6])[0]
        if kind == b"\x06\x00":
            data, offset = explode(pkg, offset + 6, size)
        else:
            data, offset = pkg[offset + 6:offset + 6 + size], offset + 6 + size
        out.append(data)
    return out


def frames(d):
    """An IANM resource's frames: dicts of x, y, w, h, key (transparent
    colour), ega (the colour table in force) and idx (rows of colours)."""
    assert d[:4] == b"IANM"
    n, bpp = struct.unpack(">HH", d[4:8])
    assert bpp == 4
    sizes = [struct.unpack(">HH", d[8 + 4 * i:12 + 4 * i]) for i in range(n)]
    p, ega, out = 8 + 4 * n, None, []
    for w, h in sizes:
        hx, hy, flags = struct.unpack(">hhH", d[p:p + 6])
        p += 6
        if flags >> 8:
            ega = d[p + 16:p + 32]
            p += 48
        row = (w + 1) // 2
        px = d[p:p + row * h]
        p += row * h
        idx = [[px[y * row + x // 2] >> 4 if x % 2 == 0 else px[y * row + x // 2] & 15
                for x in range(w)] for y in range(h)]
        out.append(dict(x=-hx, y=-hy, w=w, h=h, key=flags & 0xff, ega=ega, idx=idx))
    return out


def render(idx, ega):
    im = Image.new("RGB", (len(idx[0]), len(idx)))
    px = im.load()
    for y, row in enumerate(idx):
        for x, v in enumerate(row):
            c = ega[v]
            px[x, y] = EGA[c >> 4 if (x + y) % 2 == 0 else c & 15]
    return im


def scene(tactics, n, anim):
    """Planet scene n's still picture, then the picture after each frame of
    its animation anim (1 or 2) is drawn over it."""
    res = chain(tactics, SCENES, 3 * n + 3)[3 * n:]
    still = frames(res[0])[0]
    canvas, ega = [row[:] for row in still["idx"]], still["ega"]
    out = [render(canvas, ega)]
    for f in frames(res[anim]):
        for y, row in enumerate(f["idx"]):
            for x, v in enumerate(row):
                X, Y = f["x"] + x, f["y"] + y
                if v != f["key"] and 0 <= X < still["w"] and 0 <= Y < still["h"]:
                    canvas[Y][X] = v
        out.append(render(canvas, ega))
    return out
