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

## The ships

| Alliance of Free Stars | | Ur-Quan Hierarchy | |
|---|---|---|---|
| Earthling Cruiser | homing nukes, point-defense | Ur-Quan Dreadnought | close-range fusion blast; fighters at any range (**swarm**: fewer as crew is lost) |
| Chenjesu Broodhome | photon crystal, DOGI (slows) | Mycon Podship | homing plasmoid, regrows crew |
| Mmrnmhrm X-Wing / Y-Wing | recruit either; lasers or torpedoes, transforms | Spathi Eluder | missiles, B.U.T.T. |
| Yehat Terminator | pulse cannons, force shield | Umgah Drone | antimatter cone, skirmisher |
| Syreen Penetrator | dagger, Syreen song (drains) | VUX Intruder | laser, limpets (slow) |
| Arilou Skiff | auto-aim laser, hyperjump | Androsynth Guardian | acid bubbles (poison), Blazer ram |
| Shofixti Scout | dart gun, Glory Device | Ilwrath Avenger | Hellfire, cloaking device |

**Hull size.** Every ship shows its hull class (large, medium, small or
tiny) as a trait in the side panel; hover over it for that hull's moves and
defense on every terrain.

**Promotions.** Every ship can rise from level 1 to **Veteran** (level 2)
and **Elite** (level 3) by gaining experience. Cheap, small ships promote
fastest: the Veteran threshold is 8 + 0.8 × recruit cost (16 XP for a
Shofixti Scout, 34 for an Ur-Quan Dreadnought), Elite is twice that.
(Wesnoth's multiplayer *Experience modifier* setting, 70% by default, scales
these further.) Each promotion adds HP and some mix of stronger or more
frequent attacks, new attacks and new abilities:

| Ship | Veteran | Elite |
|---|---|---|
| Earthling Cruiser | heavier nukes, stronger point-defense | nukes ×3, **leadership** |
| Chenjesu Broodhome | stronger crystals, DOGI ×3 | **heals** nearby ships |
| Mmrnmhrm X-Wing / Y-Wing | stronger lasers / torpedoes ×3 | lasers ×5 / heavy torpedoes, **self-repair** |
| Yehat Terminator | pulse cannons ×6 | **first strike** |
| Syreen Penetrator | song ×3 | song also **slows**, dagger ×4 |
| Arilou Skiff | new **ranged** laser | **nebula ambush** |
| Shofixti Scout | darts **backstab**, 30-damage Glory | **skirmisher**, 36-damage Glory |
| Ur-Quan Dreadnought | heavier fusion blast, fighters ×5 | fighters ×6, **leadership** |
| Mycon Podship | bigger plasmoid, faster regrowth | new melee **poison** spore burst |
| Spathi Eluder | **skirmisher**, stronger B.U.T.T. | B.U.T.T. ×3 |
| Umgah Drone | stronger cone | cone ×5, **magical** (70% to hit) |
| VUX Intruder | stronger laser, limpets ×3 | laser **marksman** |
| Androsynth Guardian | hotter Blazer, stronger acid | acid ×4, **cures** nearby ships |
| Ilwrath Avenger | hotter Hellfire | Hellfire ×4, **backstab** |

**Right-click actions** (click your own ship, then pick the top menu entry):

- *Detonate Glory Device* (Shofixti Scout): the Scout explodes for 24
  damage to every ship next to it, friend or foe.
- *Transform* (Mmrnmhrm): swap between the X-Wing and the fast Y-Wing; uses
  the ship's turn.

Planets are villages (income and repair), starbases are keeps, docking
rings are castles, stars block movement. Terrain, by hull size
(moves to enter / defense):

| Terrain | Large | Medium | Small | Tiny |
|---|---|---|---|---|
| Open space | 1 / 30% | 1 / 40% | 1 / 50% | 1 / 60% |
| Green nebula | 3 / 40% | 2 / 50% | 2 / 60% | 1 / 70% |
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
