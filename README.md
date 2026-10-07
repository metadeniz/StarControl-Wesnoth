# Star Control TC for Battle for Wesnoth

A total conversion of Battle for Wesnoth into the Star Control 1 war: the
Alliance of Free Stars against the Ur-Quan Hierarchy, seven ships a side,
fought over space maps with nebulae, asteroid fields, planets and stars.

**Status: prototype, development paused.** Personal use only: the ship
sprites, projectiles, explosions and sounds come from The Ur-Quan Masters
(CC BY-NC-SA 2.5). The terrain art is original.

## Install and play

Tested with Wesnoth 1.16.11; it should also work on 1.18.

This repository *is* the add-on: its root holds `_main.cfg`. Wesnoth
needs the folder to be called `Star_Control_TC`, inside your add-ons
folder:

- Windows: `Documents\My Games\Wesnoth1.18\data\add-ons\`
- macOS: `~/Library/Application Support/Wesnoth_1.18/data/add-ons/`
- Linux: `~/.local/share/wesnoth/1.18/data/add-ons/`

(Use `1.16` in those paths for Wesnoth 1.16. In-game,
*Preferences → General → Paths* shows the exact location.)

**With git (stays up to date):** open a terminal in the add-ons folder and run

    git clone https://github.com/metadeniz/StarControl-Wesnoth.git Star_Control_TC

then `git pull` inside `Star_Control_TC` to get new versions.

**Without git:** download the repository as a ZIP and unpack it into the
add-ons folder as `Star_Control_TC`.

Then restart Wesnoth, choose **Multiplayer → Local game**, pick one of the
maps below and the era **Star Control: The Ur-Quan War**.

| Map | Players |
|---|---|
| 2p — Procyon Front | 1 vs 1 |
| 2p — Vela Nebula | 1 vs 1 |
| 4p — Isar’s Cross (Deep Space) | 2 vs 2 (players 1 & 4 vs 2 & 3) |

## Music

Each player hears their own faction's Star Control II race themes in
rotation: the Alliance gets Commander (Earthlings), Chmmr, Yehat, Syreen,
Arilou and Shofixti plus Star Control II's victory theme; the Hierarchy
gets Ur-Quan, Mycon, Spathi, Umgah, VUX and Ilwrath. The victory fanfare
plays when you win. When a ship destroys
another, its race's victory ditty plays (the music dips while it does).

## The ships

| Alliance of Free Stars | | Ur-Quan Hierarchy | |
|---|---|---|---|
| Earthling Cruiser | homing nukes, point-defense (fighters hit it at most 50%) | Ur-Quan Dreadnought | close-range fusion blast; fighters at any range (**swarm**: fewer as crew is lost) |
| Chenjesu Broodhome | photon crystal (ranged; lighter shards close up), DOGI (slows) | Mycon Podship | homing plasmoids at range, heavier plasmoids close up; regrows crew |
| Mmrnmhrm X-Wing / Y-Wing | recruit either; lasers or torpedoes, transforms | Spathi Eluder | missiles, B.U.T.T. |
| Yehat Terminator | pulse cannons, force shield | Umgah Drone | antimatter cone, skirmisher |
| Syreen Penetrator | ranged particle dagger; close-range Syreen song (drains) | VUX Intruder | laser, limpets (slow) |
| Arilou Skiff | auto-aim laser, hyperjump | Androsynth Guardian | acid bubbles (poison), Blazer ram |
| Shofixti Scout | dart gun; **Glory Device**: one unavoidable fire strike (16 / 20 / 24 by level) on one ship, destroying the Scout | Ilwrath Avenger | Hellfire, cloaking device |

**Hull size.** Every ship shows its hull class (large, medium, small or
tiny) as a trait in the side panel; hover over it for that hull's moves and
defense on every terrain.

**Promotions.** Every ship can rise from level 1 to **Veteran** (level 2)
and **Elite** (level 3) by gaining experience. Cheap, small ships promote
fastest, the powerful ones slowest: the Veteran threshold is 1.6 × recruit
cost (8 XP for a Shofixti Scout, 45 for an Ur-Quan Dreadnought, 48 for a
Chenjesu Broodhome), Elite is twice that.
(Wesnoth's multiplayer *Experience modifier* setting, 70% by default, scales
these further.) Each promotion adds HP and some mix of stronger or more
frequent attacks, new attacks and new abilities. **Backstab** (double
damage with an ally behind the target) comes with promotion, except the
Syreen dagger and Androsynth acid, which have it from the start (and the
Spathi and Shofixti, which only get it as Elites):

| Ship | Veteran | Elite |
|---|---|---|
| Earthling Cruiser | heavier nukes, stronger point-defense, **heals +4** | nukes ×3, **leadership** |
| Chenjesu Broodhome | stronger crystals, DOGI ×3, **heals +4** | **cures** (heals +8 and cures poison) |
| Mmrnmhrm X-Wing / Y-Wing | X-Wing lasers **backstab**; stronger torpedoes ×3 | lasers ×5 / heavy torpedoes, **self-repair** |
| Yehat Terminator | pulse cannons ×6 | **first strike** |
| Syreen Penetrator | song ×3 | song also **slows**, dagger ×4 |
| Arilou Skiff | new **ranged** laser; close laser **backstab**; **ambush** | ambush, laser ×4 |
| Shofixti Scout | stronger darts, 20-damage Glory | **skirmisher**, darts **backstab**, 24-damage Glory |
| Ur-Quan Dreadnought | heavier fusion blast, fighters ×5 | fighters ×6, **leadership** |
| Mycon Podship | bigger plasmoids, faster regrowth | homing plasmoids **marksman**, new melee **poison** spore burst |
| Spathi Eluder | **skirmisher**, stronger B.U.T.T. | B.U.T.T. ×3, **backstab** |
| Umgah Drone | stronger cone, **heals +4** | cone ×5, **magical** (70% to hit), **heals +8** |
| VUX Intruder | stronger laser, limpets ×3, laser **backstab** | laser **marksman** |
| Androsynth Guardian | hotter Blazer, stronger acid | acid ×4, **heals +4** |
| Ilwrath Avenger | hotter Hellfire, **backstab** | Hellfire ×4 |

**Ambush.** Some ships can hide in certain terrain: invisible to the enemy
unless an enemy ship is next to them, and revealed for the rest of a turn
in which they attack. Nobody hides in open space, ion storms, planets or
starbases.

| Ship | Hides in | From |
|---|---|---|
| Ilwrath Avenger | anywhere (cloaking device) | level 1 |
| Androsynth Guardian | green nebulae, asteroid fields, dust clouds | level 1 |
| Mycon Podship | red nebulae | level 1 |
| Chenjesu Broodhome | red nebulae | level 1 |
| Arilou Skiff | green nebulae, asteroid fields, dust clouds | Veteran |
| Spathi Eluder | asteroid fields | Veteran |
| Mmrnmhrm X-Wing | asteroid fields | Veteran |
| Mmrnmhrm Y-Wing | green nebulae, dust clouds | Veteran |
| VUX Intruder | green nebulae | Elite |
| Shofixti Scout | asteroid fields, green and red nebulae | Elite |

**Leaders** start promoted: Elite (level 3) if the ship costs 16 gold or
less (Earthling Cruiser, Syreen, Arilou, Shofixti, Spathi, Umgah, VUX,
Androsynth, Ilwrath), Veteran (level 2) otherwise. A leader can't use the
Glory Device.

**Precursor artifacts.** About one planet in five (never next to a
starbase) hides a Precursor artifact; on mirrored maps they come in mirror
pairs. The first ship to enter the planet finds it and gains 8 XP plus one
random, permanent bonus, shown as a trait next to the hull size in the side
panel (hover it for details):

| Trait | Bonus |
|---|---|
| +drive | +1 movement |
| +crew | +6 max HP |
| +battery | +1 strike on every attack |
| +recharge | +1 damage on every attack |

**Right-click actions** (click your own ship, then pick the top menu entry):

- *Transform* (Mmrnmhrm): swap between the X-Wing and the fast Y-Wing; uses
  the ship's turn.

Planets are villages (income and repair), starbases are keeps, docking
rings are castles, stars block movement. Terrain, by hull size
(moves to enter / defense):

| Terrain | Large | Medium | Small | Tiny |
|---|---|---|---|---|
| Open space | 1 / 30% | 1 / 40% | 1 / 50% | 1 / 60% |
| Green nebula | 2 / 40% | 2 / 50% | 2 / 60% | 1 / 70% |
| Red nebula (hot plasma) | 2 / 40% | 3 / 50% | 3 / 60% | 2 / 60% |
| Dust cloud | 2 / 20% | 2 / 30% | 2 / 40% | 1 / 50% |
| Ion storm | 3 / 10% | 3 / 20% | 3 / 30% | 2 / 40% |
| Thin ion storm | the better of open space and ion storm |||| 
| Asteroid field | can't enter | 3 / 60% | 2 / 70% | 2 / 70% |
| Dense asteroids | can't enter | 3 / 70% | 3 / 70% | 2 / 70% |

Asteroids over nebula or dust give the better defense and the slower
movement of the two. The fire-born Mycon and Ilwrath (1 / 60%) and the
heat-proof Chenjesu (2 / 50%) are at home in red nebulae.

## Rebuilding (developers)

- `tools/make_art.py --uqm <UQM-MegaMod-Content checkout> --out .`
  regenerates all images and sounds. `art-manifest.txt`
  lists every UQM-derived file (what a published version must replace).
- `tools/make_maps.py .` regenerates the 2p maps.
- `tools/convert_map.py <wesnoth .map> <out .map>` turns any regular
  Wesnoth map into a space map hex for hex: forest → nebula, mushroom
  grove → red nebula, sand → dust cloud, hills → asteroids, mountains →
  dense asteroids, water and swamp → ion storm, ford → thin ion storm,
  villages → planets, impassable → star. Isar's Cross was
  made this way.
- `tools/ai_battles.sh [games] [jobs]` plays headless AI-vs-AI games and
  prints win rates (last run: 40–40 over 80 games).
- All player-visible Star Control names live in `utils/names.cfg`.
  Naming rule: the Hierarchy's masters are "Ur-Quan", never "Kzer-Za".
