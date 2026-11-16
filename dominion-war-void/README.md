# The Void (from Dominion War Wesnoth)

These files are copied unchanged from the Dominion War Wesnoth add-on (repo `metadeniz/dominion-war-wesnoth`, commit 9a0330f). The relative paths are the same as in that add-on.

The Void is a starless black region with a wavy pale-blue rim, based on VOY "Night". In Dominion War it exists **only as a prototype drawing**. The add-on has no `.cfg` files at all, so it has:

- no `[terrain_type]` definition and no terrain code,
- no `[terrain_graphics]` rules or macros,
- no tile, edge/transition or overlay images.

The look is made by one Python function, `void()` in `tileset/src/imp_ideas.py`. It draws the void as a single RGBA layer over a whole test map, not as per-hex tiles. A soft hex-membership mask (`badlands.membership`, sigma 16) is turned into an opaque black interior. The rim is a Gaussian band on the mask, coloured (80, 95, 135) and modulated by fBm noise (`badlands.fbm`) to make it wavy. That layer is composited over the starfield.

| File | Original path | Purpose |
|---|---|---|
| `tileset/src/imp_ideas.py` | `tileset/src/imp_ideas.py` | Prototype sheet of ten impassable-terrain ideas. Idea 9, `void()`, is the Void. Also holds the shared test layout, `starfield()` and `mask()`. |
| `tileset/src/badlands.py` | `tileset/src/badlands.py` | Helper module imported by `imp_ideas.py`. `void()` uses `fbm()` (noise) and `membership()` (hex mask). |
| `tileset/src/asteroids.py` | `tileset/src/asteroids.py` | Also imported by `imp_ideas.py` (used by other ideas such as the debris disk, not by `void()`). It is included so the script runs. |
| `tileset/impassable-ideas.png` | `tileset/impassable-ideas.png` | Rendered output of `imp_ideas.py`. Panel 9 (bottom left) is the Void. |

To run the script, start it from `tileset/src/` with numpy, Pillow and scipy installed. It writes `idea_*.png` and saves the sheet to `/mnt/project-files/tileset/impassable-ideas.png`, a path from the original environment, so edit that path first. It also loads DejaVu fonts from `/usr/share/fonts/...`.
