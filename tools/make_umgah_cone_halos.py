"""Umgah antimatter cone, held for a whole attack.

The cone is shown as an item halo on the attacking Drone's hex for the
whole fight (see sc.cone_hold in lua/sc.lua), so it stays lit between
strikes instead of flashing once per strike. A halo is drawn centred on
its hex and cannot be flipped, so this bakes one 144x144 image per facing
with the cone already where the attack animation used to put it: 0.55 of
the way to the target hex.

Run from the repository root: python3 tools/make_umgah_cone_halos.py
"""

from PIL import Image

SIZE = 144          # two hexes wide, centred on the Drone's hex
OFFSET = 0.55       # the old cone_frame's offset
# (direction, source image, flip horizontally, flip vertically, hex step)
FACINGS = [
    ("n", "n", False, False, (0, -72)),
    ("ne", "ne", False, False, (54, -36)),
    ("se", "ne", False, True, (54, 36)),
    ("s", "n", False, True, (0, 72)),
    ("sw", "ne", True, True, (-54, 36)),
    ("nw", "ne", True, False, (-54, -36)),
]


def main():
    for name, src, hflip, vflip, (dx, dy) in FACINGS:
        cone = Image.open(f"images/projectiles/sc/cone-{src}.png").convert("RGBA")
        if hflip:
            cone = cone.transpose(Image.FLIP_LEFT_RIGHT)
        if vflip:
            cone = cone.transpose(Image.FLIP_TOP_BOTTOM)
        cx = SIZE / 2 + OFFSET * dx
        cy = SIZE / 2 + OFFSET * dy
        out = Image.new("RGBA", (SIZE, SIZE))
        out.alpha_composite(cone, (round(cx - cone.width / 2), round(cy - cone.height / 2)))
        out.save(f"images/halo/sc/umgah-cone-{name}.png")


if __name__ == "__main__":
    main()
