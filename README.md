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
| Earthling Cruiser | homing nukes, point-defense | Ur-Quan Dreadnought | fusion blast, launches fighters |
| Chenjesu Broodhome | photon crystal, DOGI (slows) | Mycon Podship | homing plasmoid, regrows crew |
| Mmrnmhrm X-Form / Y-Form | recruit either; lasers or torpedoes, transforms | Spathi Eluder | missiles, B.U.T.T. |
| Yehat Terminator | pulse cannons, force shield | Umgah Drone | antimatter cone, skirmisher |
| Syreen Penetrator | dagger, Syreen song (drains) | VUX Intruder | laser, limpets (slow) |
| Arilou Skiff | auto-aim laser, hyperjump | Androsynth Guardian | acid bubbles (poison), Blazer ram |
| Shofixti Scout | dart gun, Glory Device | Ilwrath Avenger | Hellfire, cloaking device |

**Right-click actions** (click your own ship, then pick the top menu entry):

- *Detonate Glory Device* (Shofixti Scout): the Scout explodes for 24
  damage to every ship next to it, friend or foe.
- *Launch Fighters* (Ur-Quan Dreadnought): instead of attacking, launch up
  to two fighters at 4 HP each. Fighters that end a later turn next to the
  Dreadnought fly back aboard.
- *Transform* (Mmrnmhrm): swap between the X-Form and the fast Y-Form; uses
  the ship's turn.

Planets are villages (income and repair), starbases are keeps, docking
rings are castles, stars block movement. Nebulae and asteroid fields slow
ships but give cover; ion storms slow ships *and* make them easier to hit.

## Rebuilding (developers)

- `tools/make_art.py --uqm <UQM-MegaMod-Content checkout> --out .`
  regenerates all images and sounds. `art-manifest.txt`
  lists every UQM-derived file (what a published version must replace).
- `tools/make_maps.py .` regenerates the 2p maps.
- `tools/convert_map.py <wesnoth .map> <out .map>` turns any regular
  Wesnoth map into a space map hex for hex (forest → nebula, hills →
  asteroids, water → ion storm, villages → planets…). Isar's Cross was
  made this way.
- `tools/ai_battles.sh [games] [jobs]` plays headless AI-vs-AI games and
  prints win rates (last run: 40–40 over 80 games).
- All player-visible Star Control names live in `utils/names.cfg`.
  Naming rule: the Hierarchy's masters are "Ur-Quan", never "Kzer-Za".
