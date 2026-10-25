# Star Control TC for Battle for Wesnoth

A total conversion of Battle for Wesnoth into the wars of Star Control: the
Alliance of Free Stars against the Ur-Quan Hierarchy (Star Control 1), and
the New Alliance of Free Stars against the Agents of Death (Star
Control II), fought over space maps with nebulae, asteroid fields, planets
and stars. Any faction can fight any other.

**Status: prototype, development paused.** Personal use only: the ship
sprites, projectiles, explosions and sounds come from The Ur-Quan Masters
(CC BY-NC-SA 2.5), and music tracks from the Precursors' UQM Remix
Packs. The terrain art is original. See [CREDITS.md](CREDITS.md) for
everyone whose work it uses.

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
| 2p — Understanding Power | 1 vs 1 |
| 2p — Understanding Power (Small) | 1 vs 1 |
| 4p — Isar’s Cross (Deep Space) | 2 vs 2 (players 1 & 4 vs 2 & 3) |
| 4p — Manufacturing Consent | 2 vs 2 (west, players 1 & 3, vs east, players 2 & 4) |
| 4p — Media Control | 2 vs 2, one player in each corner (players 1 & 3 vs 2 & 4); the Starts option puts teammates side by side, north vs south or west vs east (default), in opposite corners, in random corners, or each side in its numbered corner clockwise from the northwest |
| 6p — Hegemony or Survival | 2 vs 2 or 3 vs 3 on a hexagon, a player in each corner, numbered clockwise from the north: odd vs even; for 2 vs 2 leave one odd and one even side empty |
| 4p — Hegemony or Survival | 2 vs 2: the 6p hexagon with the northeast and southwest corners cut away behind their bends of light badlands; players clockwise from the north: north (players 1 & 4, north and northwest) vs south (2 & 3, southeast and south) |
| 6p — Year 501 | 2 vs 2 or 3 vs 3, west (players 1, 3 & 5) vs east (2, 4 & 6); for 2 vs 2 leave a mirrored pair empty: 1 & 2 north, 3 & 4 middle, 5 & 6 south |
| 2p — Year 501 | 1 vs 1, west vs east; the 6p map with its north-west and south-west corners (and their mirrors) cut away |
| 2p — The Freelands (Deep Space) | 1 vs 1 |
| 2p — Weldyn Channel (Deep Space) | 1 vs 1 |
| 2p — Fallenstar Lake (Deep Space) | 1 vs 1 |
| 2p — Isar’s Cross (Deep Space) | 1 vs 1, north vs south; the 4p map with the west and east arms cut away |
| 2p — Caves of the Basilisk (Deep Space) | 1 vs 1; black holes stand where the statues were |
| 2p — Silverhead Crossing (Deep Space) | 1 vs 1 |
| 2p — Ruphus Isle (Deep Space) | 1 vs 1 |
| 2p — The Hamlets (Deep Space) | 1 vs 1 |
| 2p — Swamp of Dread (Deep Space) | 1 vs 1 |
| 2p — Hornshark Island (Deep Space) | 1 vs 1 |
| 2p — Thousand Stings Garrison (Deep Space) | 1 vs 1, south vs north; gravity eddies and black holes stand where the scorpion statues were |
| 2p — Howling Ghost Badlands (Deep Space) | 1 vs 1 |
| 2p — Sablestone Delta (Deep Space) | 1 vs 1 |
| 2p — Fred’s Fjord (psydev) | 1 vs 1 |
| 2p — Flashy Chorus (psydev) | 1 vs 1 |
| 2p — Necessary Illusions | 1 vs 1 |

## Music

Each player hears their own faction's playlist, shuffled so that every track plays
once before any repeats:

- **Alliance:** Star Control II's Commander (Earthlings), Yehat, Syreen,
  Arilou and Shofixti themes, Chenjesu and Mmrnmhrm themes by Titus, the
  quasispace theme (original and 3DO versions), Anamnesis's 2014 refresh of the hyperspace theme, and
  Starbase.
- **Hierarchy:** the Ur-Quan, Mycon, Spathi, Umgah, VUX, Ilwrath and
  Thraddash themes, an Androsynth theme by TheMisterCat (DUOLED), Idan
  Schneider's orchestral cover of the Ur-Quan theme, and Starbase.

The Alliance and the Hierarchy have three music modes: those original
tracks, the Precursors' remixes in place of the tracks they remix, or both.
The host picks the mode everyone starts with (the era's "Music" option),
and each player can switch their own with "Switch music" in the
right-click menu, which goes through the three in turn. The remixes are:

- **Alliance:** Commander ("Corridor Nine"), Yehat ("Years Late Mix"),
  Syreen ("Close Encounters of the Seventh Kind"), Arilou ("Welcome to
  Falayalaralfali"), Shofixti ("Bonsai!"), quasispace ("Through the Angles
  of Space", "Mystic Shadows", for both quasispace versions) and Starbase ("Under a
  Red Sky"). The Titus themes and the hyperspace refresh
  have no remix and stay.
- **Hierarchy:** Ur-Quan ("Now and Forever", and Erol Otus's Ur-Quan theme
  from Remix Pack 3's extras), Mycon ("Rebirth"), Spathi ("Safe Haven",
  "Fwiffo's Starrunner"), Umgah ("Genetic Modification"), VUX
  ("Ultra-gross", "Acid in the Eye"), Ilwrath ("All Evil"), Thraddash
  ("Culture 19"), Androsynth (Ramen Rider's Androsynth encounter theme),
  Starbase ("Under a Red Sky"), and hyperspace ("Across the Galaxy", which
  has no original track in the list). The orchestral Ur-Quan cover has no remix
  and stays.

The New Alliance and the Agents of Death have one playlist each:

- **New Alliance:** Ramen Rider's cover of the Syreen theme, the Melnorme
  theme re-imagined by DJ Yan Yan Lipavsky, and the
  Precursors' remixes: Chmmr ("Photosynthesis"),
  Zoq-Fot-Pik ("Frungy Party"), Pkunk ("Pkunks Not Dead"), Supox ("Shake
  Yer Rootz"), Utwig ("Mask of Ultimate Embarrassment and Shame", "The
  Ultron"), Commander ("Corridor Nine"), Arilou ("Welcome to
  Falayalaralfali"), Melnorme ("Turning Purple"), Syreen ("Close Encounters of the Seventh Kind"),
  quasispace ("Mystic Shadows", "Through the Angles of Space"), hyperspace ("Across the Galaxy") and Starbase ("Under a Red
  Sky").
- **Agents of Death:** modern versions only, the Precursors' remixes: Kohr-Ah ("Cleansing
  Required", "The Eternal Doctrine", "Kohr-Ah" battle remix), Druuge
  ("Property of the Crimson Corporation"), Thraddash ("Culture 19"),
  Slylandro Probes ("We Come In Peace"), Orz ("Squeezing the Juice"), Mycon
  ("Rebirth"), Ilwrath ("All Evil"), "The Battle of the Sa-Matra", hyperspace ("Across the
  Galaxy") and Starbase ("Under a Red Sky").

When you win, the old Alliance and the Hierarchy hear Star Control 1's
victory theme for their side, the New Alliance Star Control II's victory
fanfare going into a 44-second cut of its ending theme, and the Agents of Death the opening of Chopin's Funeral
March. The game's music stops for it, and each side's victory picture shows in
a message window while its theme plays: Star Control 1's Earth ringed by the
Alliance races, or an Ur-Quan reaching out its tentacles; Star Control II's
free, blue Earth, after its red slave shield falls in a white flash over the
map; and a Kohr-Ah standing over its pit of bones (the HD comm
screen, with the HD Game Over screen's nebula behind it). When a ship destroys
another, its race's victory ditty plays over the music (the Sa-Matra, which has
none in Star Control II, plays the Precursors' remix of the Kohr-Ah ditty), which keeps going at
full volume. A Pkunk that is reborn gets Star Control II's "hallelujah"
instead of its killer's ditty. The victory themes and ditties are sound effects, so they
follow the Sound volume, not the Music volume: turning the music down
leaves them as loud as before.

When the leader of an old Alliance or Hierarchy side is destroyed, Star
Control's "starbase destroyed" scene plays on its hex after the death
explosion, and the game waits for it to finish.

## The ships

| Alliance of Free Stars | | Ur-Quan Hierarchy | |
|---|---|---|---|
| **Alliance Starbase** (leader only) | 4 moves, 110 HP; point-defense laser (**first strike**), missile battery (**marksman**); heals +4, defense grid (+10% resistance for the ships next to it), point-defense, leadership | **Hierarchy Starbase** (leader only) | 4 moves, 120 HP; defense turrets (**first strike**), fighter bays at range; repair dock (heals +8 and cures the ships next to it), slave shield (+20% resistance when attacked), leadership |
| Earthling Cruiser | homing nukes, point-defense (fighters hit it at most 50%) | Ur-Quan Dreadnought | close-range fusion blast; fighters at any range (**swarm**: fewer as crew is lost) |
| Chenjesu Broodhome | photon crystal (ranged; lighter shards close up), DOGI (slows) | Mycon Podship | homing plasmoids at range, heavier plasmoids close up; regrows crew |
| Mmrnmhrm X-Wing / Y-Wing | recruit either; lasers or torpedoes, transforms; X-Wing cures (heals +8 and cures poison), Y-Wing cures +4 | Spathi Eluder | howitzer (**backstab**), B.U.T.T. (**backstab**) |
| Yehat Terminator | Attack with Shields (pulse cannons), Attack Only (rail cannons, pierce); armored hull (resists blade 40%, pierce 30%, impact 20%, arcane 10%); force shield (+40% with Attack with Shields, attacking or defending; +50% against ranged; down with Attack Only; no help against fighters or the Syreen song) | Umgah Drone | antimatter cone, skirmisher |
| Syreen Penetrator | crew capacity as big as the Ur-Quan's (max HP 64 / 80 / 96) but always starts low (28 / 36 / 44 HP); promotion adds +8 HP instead of a full heal, or raises it to the new level's 36 / 44 if still below; planets, healers and resting only repair it up to that starting HP: only stolen crew (the song's drain, or capturing an enemy's life world, which fills it to max) takes it higher; ranged particle dagger (**backstab**: double damage and one extra strike when flanking); close range: one-shot Syreen song (**lures crew**: heals the full damage dealt; **backstab**: one extra strike when flanking); doesn't work on the unmanned Slylandro Probe | VUX Intruder | close-range laser (**first strike**); long-range limpets (slow) |
| Arilou Skiff | auto-aim laser, hyperjump | Androsynth Guardian | acid bubbles (poison, **backstab**), Blazer ram (**charge**, **backstab**) |
| Shofixti Scout | dart gun; **Glory Device**: one unavoidable fire strike of 8–16 / 10–20 / 12–24 by level on one ship, destroying the Scout; a Scout destroyed by a close-range attack has a 50% chance to set it off as it dies, hitting its attacker for half that | Ilwrath Avenger | Hellfire, cloaking device |

| New Alliance of Free Stars | | Agents of Death | |
|---|---|---|---|
| **Precursor Flagship** (leader only) | 4 moves, a Precursor drive (like the Chmmr's) and **hyperjump** between planets; fusion blaster, point-defense, self-repair, heals +4, leadership | **Sa-Matra** (leader only) | 4 moves and a stronger Precursor drive (1 move through nebulae, dust, badlands and asteroids); yellow comets (near and far), slowing green blobs, self-repair +8, cures and heals +8, leadership |
| Earthling Cruiser | as in the Alliance | Kohr-Ah Marauder | 4 moves; spinning blades; F.R.I.E.D. plasma ring (**magical**) |
| Chmmr Avatar | 4 moves, and a drive that handles nebulae, dust, badlands and asteroids better than other large hulls; close-range tractor beam + laser; ranged megawatt laser (**marksman**); point-defense | Druuge Mauler | 4 moves; long-range mass driver (**marksman**); nothing up close |
| Zoq-Fot-Pik Stinger | cheap; acid spit, hard-hitting tongue | Thraddash Torch | fast; afterburner (**charge**, **backstab**), horn blasters (**backstab**) |
| Pkunk Fury | fast triple gun; **reincarnation**: reborn at full HP when destroyed, 80% the first time, halving with each rebirth | Slylandro Probe | 7 moves; seeking lightning (**magical**); repairs 8 HP a turn in asteroid fields |
| Supox Blade | **skirmisher**; globs of goo | Orz Nemesis | hard-hitting space marines (**boarding**: ignore armour and shields); light howitzer |
| Utwig Jugger | six-lance volleys; absorbing shield (+30% resistance when attacked) | Mycon Podship | as in the Hierarchy |
| Melnorme Trader | 4-shot blaster up close; one heavy charged shot and a confusion ray (**slows**) at range; heals +4 (Veteran and Elite cure) | | |

**Hull size.** Every ship shows its hull class (large, medium, small or
tiny) as a trait in the side panel; hover over it for that hull's moves and
defense on every terrain.

**Promotions.** Every ship can rise from level 1 to **Veteran** (level 2)
and **Elite** (level 3) by gaining experience, at roughly mainline pace:
40 XP to Veteran and 100 to Elite. Fast learners need 28 / 70 (Shofixti,
Earthling, Umgah, VUX, Zoq-Fot-Pik, Thraddash, Syreen, Ilwrath, Supox).
The big capital ships and the Arilou Skiff, whose promoted forms are
especially strong, need 50 / 125 (Ur-Quan, Kohr-Ah, Chmmr, Chenjesu,
Arilou). A promotion that brings healing, curing or leadership comes one
step sooner (Melnorme 28 / 70, Chenjesu 40 / 100, Androsynth Elite at 70,
Ur-Quan, Kohr-Ah and Chmmr Elite at 100).
(Wesnoth's multiplayer *Experience modifier* setting, 70% by default, scales
these further.) Each promotion adds HP and some mix of stronger or more
frequent attacks, new attacks and new abilities. **Backstab** (double
damage with an ally behind the target) comes with promotion, except the
Syreen dagger and both Androsynth, Spathi and Thraddash attacks, which have it
from the start (and the Shofixti, which only get it as Elites):

| Ship | Veteran | Elite |
|---|---|---|
| Earthling Cruiser | heavier nukes, stronger point-defense, **heals +4** | nukes ×3, **leadership** |
| Chenjesu Broodhome | stronger crystals, DOGI ×3, **heals +4** | **cures** (heals +8 and cures poison) |
| Mmrnmhrm X-Wing / Y-Wing | X-Wing lasers **backstab**; stronger torpedoes ×3 | lasers ×5 / heavy torpedoes, **self-repair** |
| Yehat Terminator | Attack with Shields ×6, Attack Only ×5 | **first strike** |
| Syreen Penetrator | song gets a 2nd shot | stronger song, dagger ×4 |
| Arilou Skiff | new **ranged** laser; close laser **backstab**; **ambush** | ambush, laser ×4 |
| Shofixti Scout | stronger darts, 10–20 damage Glory | **skirmisher**, darts **backstab**, 12–24 damage Glory |
| Ur-Quan Dreadnought | heavier fusion blast, fighters ×5 | fighters ×6, **leadership** |
| Mycon Podship | bigger plasmoids, faster regrowth | homing plasmoids **marksman**, new melee **poison** spore burst |
| Spathi Eluder | **skirmisher**, stronger B.U.T.T. | B.U.T.T. ×3 |
| Umgah Drone | stronger cone, **heals +4** | cone ×5, **magical** (70% to hit), **heals +8** |
| VUX Intruder | stronger laser, limpets ×3, laser **backstab** | laser **marksman** |
| Androsynth Guardian | hotter Blazer, stronger acid | acid ×4, **heals +4** |
| Ilwrath Avenger | hotter Hellfire, **backstab** | Hellfire ×4 |

**Ambush.** Some ships can hide in certain terrain: invisible to the enemy
unless an enemy ship is next to them, and revealed for the rest of a turn
in which they attack. Nobody hides in open space, badlands, planets or
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
less (Earthling Cruiser, Syreen, Arilou, Shofixti, Umgah, VUX,
Androsynth, Ilwrath), Veteran (level 2) otherwise. A leader can't use the
Glory Device.

**Precursor artifacts.** About one planet in five (never next to a
starbase) hides a Precursor artifact; on mirrored maps they come in mirror
pairs. The first ship to enter the planet finds it and gains 8 XP plus one
random, permanent bonus, shown as a trait next to the hull size in the side
panel (hover it for details):

| Trait | Bonus |
|---|---|
| +drive | +1 movement, and +10% defense on every terrain |
| +crew | +8 max HP |
| +recharge | +2 damage on every attack |

**Right-click actions** (click your own ship, then pick the top menu entry):

- *Transform* (Mmrnmhrm): swap between the X-Wing and the fast Y-Wing; uses
  the ship's turn.

Planets are villages (income and repair), starbases are keeps, docking
rings are castles, stars block movement. Planets come in three kinds,
which replace the game's village gold and support settings:

| Planet | Gold per turn | Upkeep supported | Share of planets |
|---|---|---|---|
| Mineral world | 3 | 1 | 40% |
| Life world | 2 | 2 | 40% |
| Dead world | 1 | 1 | 20% |

The era's "Planets" option can deal the kinds out afresh when the game
starts, keeping the map's count of each kind. *Randomized, mirrored*
follows the map's symmetry, so every player gets the same mix; on maps
where the starts aren't alike to begin with (Isar's Cross, Year 501,
where some starts have more planets near them than others) it is every
team that gets the same mix. *Randomized* deals them with no mirroring.

A ship doesn't take a planet the moment it lands. Landing on an enemy's
planet destroys it (it belongs to nobody); then, as on any free planet,
the ship starts building a colony (life world), mine (mineral world) or
outpost (dead world). Building takes a whole turn: the ship has to stay
on the planet through its side's next turn, and when the turn after that
starts, the planet is that side's and pays that turn.
Every planet repairs a ship on it by 8 HP a turn (and cures poison),
whoever owns it: a free planet, an enemy's, or one the ship is still
building on. A side's own colonies (life worlds) repair its ships by 8
too, and a ship that stays on one through another turn is fully
repaired (a Syreen only up to her starting HP). Moving off, even to come
back, starts that over.
An enemy's colony (life world) blown up this way plays the colony destroyed
scene below the planet, with "Colony destroyed" under the ship until it fades,
unless the ship is a Syreen, which takes the colonists as crew instead; an
enemy's mine (mineral world) plays the mine destroyed scene, with "Mine
destroyed". These scenes, like the Syreen's and the Precursor
artifact's, are cut from Star Control's own and play below the planet, or
above it near the bottom of the map.

Terrain, by hull size (moves to enter / defense):

| Terrain | Large | Medium | Small | Tiny |
|---|---|---|---|---|
| Open space | 1 / 30% | 1 / 40% | 1 / 50% | 1 / 60% |
| Green nebula | 2 / 40% | 2 / 50% | 2 / 60% | 1 / 70% |
| Red nebula (hot plasma) | 2 / 40% | 3 / 50% | 3 / 60% | 2 / 60% |
| Dust cloud | 2 / 20% | 2 / 30% | 2 / 40% | 1 / 50% |
| Badlands | 3 / 10% | 3 / 20% | 3 / 30% | 2 / 40% |
| Light badlands | 2 / 20% | 2 / 30% | 2 / 40% | 1 / 50% |
| Thin badlands | the better of open space and badlands |||| 
| Asteroid field | 4 / 50% | 3 / 60% | 2 / 70% | 2 / 70% |
| Dense asteroids | 4 / 60% | 3 / 70% | 3 / 70% | 2 / 70% |

**Badlands runners** cross the badlands more easily: Arilou, Shofixti and
Zoq-Fot-Pik need 1 move there (50% defense); Umgah, Androsynth, Yehat, Supox,
Slylandro and Thraddash need 2 (with their hull's light-badlands defense), and light
badlands cost all of them 1 move.

Badlands come in two looks that play exactly the same: a flowing blue
current (the usual one) and ripples, pale swell lines over open space.
Map makers pick the look per map; the editor lists the rippled ones as
"(Ripples)".

Asteroids over nebula or dust give the better defense and the slower
movement of the two. The fire-born Mycon and Ilwrath (1 / 60%) and the
heat-proof Chenjesu (1 / 50%) are at home in red nebulae. The Chenjesu
Broodhome and the Sa-Matra also cross nebulae, dust clouds and badlands for 1 move.

## Rebuilding (developers)

- `tools/make_art.py --uqm <UQM-MegaMod-Content checkout> --out . [--remix <unzipped UQM Remix Packs>]`
  regenerates all images and sounds. `art-manifest.txt`
  lists every UQM-derived file (what a published version must replace).
  Green and red nebulae are drawn as gauzy veils; `tools/make_art.py --only gas
  --nebula-style soft --out .` redraws them in the alternate soft-glow look
  (`--nebula-style veils` switches back).
- `tools/make_reach_shade.py` regenerates `reach/images/terrain/darken.png`,
  the solid dark shade over hexes a selected ship cannot reach this turn
  (it replaces core Wesnoth's striped shade, in Star Control games only).
- `tools/make_maps.py .` regenerates the 2p maps.
- `tools/make_understanding_power.py .` regenerates Understanding Power, and
  `maps/default-terrain/2p_Understanding_Power.map`, the same map in default
  Wesnoth terrain.
- `tools/make_understanding_power_small.py .` writes the small version (26×20,
  both terrains) from the full one.
- `tools/make_manufacturing_consent.py .` regenerates Manufacturing Consent
  (4p, west vs east), and `maps/default-terrain/4p_Manufacturing_Consent.map`,
  the same map in default Wesnoth terrain.
- `tools/make_media_control.py .` regenerates Media Control (4p, 2 vs 2, one
  player per corner): it traces the north-west quarter, and
  `tools/make_media_control_4x.py` turns it four ways about the centre of a
  37×37 map, as nearly as hexes allow, with every corner as many moves from
  the centre, its neighbours and its planets as the others (the balance
  comes from `tools/balance_media_control.py`). Also writes
  `maps/default-terrain/4p_Media_Control.map`, the same map in default
  Wesnoth terrain. `tools/make_media_control_6p.py .` then writes the 6p
  Media Control: that map's north-west quarter stretched onto each sixth of
  a hexagon, turned six ways hex for hex (`-v` prints each start's moves), and its 4p cut,
  `maps/4p_Media_Control_Hexagon.map`, with the north and south corners
  shaved off.
- `tools/make_hegemony_or_survival.py .` regenerates Hegemony or Survival, an
  original 6-player map on a hexagon, the same in all six corners (turned
  and mirrored hex for hex), and its 4-player cut without the northeast and
  southwest corners, and `tools/make_year_501.py .` regenerates
  Year 501, an original team map, west vs east, mirrored west to east
  (`tools/make_year_501_2p.py .` regenerates its 1 vs 1 copy);
  `tools/make_necessary_illusions.py .` regenerates Necessary Illusions, a
  small original 1 vs 1 map, mirrored west to east. All of them print each
  start's planet distances as a balance check.
- `tools/assign_planet_types.py <map> ...` makes each untyped planet a life,
  mineral or dead world, following the map's symmetry so every player gets
  the same mix. The map scripts above and `convert_map.py` run it on the maps
  they write. `tools/make_planet_types.py` draws the planet art (six looks
  each for life and mineral worlds, three for dead worlds; an untyped planet
  picks any of the fifteen).
- `tools/grid_overlay.py <map> <render.png> <out.png>` draws a hex grid with
  each hex's in-game coordinates over a `wesnoth --screenshot` render of the
  map, so changes can be asked for by hex.
- `tools/convert_map.py <wesnoth .map> <out .map>` turns any regular
  Wesnoth map into a space map hex for hex: forest → nebula, mushroom
  grove → red nebula, sand → dust cloud, hills → asteroids, mountains →
  dense asteroids, deep water → badlands, shallow water and swamp → light
  badlands, ford → thin badlands, castles → docking rings (sunken and
  swamp ruins → docking rings out in the badlands), villages → planets,
  impassable → star (touching impassable hexes → debris disk). Isar's Cross, The Freelands, Weldyn Channel, Fallenstar
  Lake, Caves of the Basilisk, Silverhead Crossing, Ruphus Isle, The Hamlets, Swamp of Dread, Hornshark Island, Thousand Stings Garrison and Sablestone Delta were made
  this way, and so were psydev's custom maps Fred's Fjord and Flashy Chorus (a fake map edge, `^_fme`, is kept). Extra `X,Y=CODE`
  arguments place terrain afterwards; the Caves' statues became black
  holes: `27,14=Ys^Yxb 40,8=Ys^Yxb 39,8=Ys^Yxb 2,11=Ys^Yxb 8,18=Ys^Yxb
  8,13=Ys^Yxb 22,12=Ys^Yxb 37,17=Ys^Yxb 5,8=Ys^Yxb 25,14=Ys^Yxb
  34,6=Ys^Yxb 34,11=Ys^Yxb 15,11=Ys^Yxb 20,12=Ys^Yxb 17,11=Ys^Yxb`.
  Thousand Stings Garrison's 66 scorpion statues, all along the edges,
  became gravity eddies (`X,Y=Yqe` for each statue's hex) with twelve black
  holes, each with a set look so neighbours differ: `2,7=Yqe^Yxb1
  1,9=Yqe^Yxb2 1,14=Yqe^Yxb4 1,19=Yqe^Yxb3 8,24=Yqe^Yxb1 12,24=Yqe^Yxb2
  28,19=Yqe^Yxb1 29,18=Yqe^Yxb2 29,13=Yqe^Yxb4 29,8=Yqe^Yxb3
  22,2=Yqe^Yxb1 18,2=Yqe^Yxb2`.
- `tools/ai_battles.sh [games] [jobs] [faction] [faction] [first seed]`
  plays headless AI-vs-AI games and prints win rates. Factions:
  `SC_Alliance`, `SC_Hierarchy`, `SC_NewAlliance`, `SC_DeathMarch`.
- All player-visible Star Control names live in `utils/names.cfg`.
  Naming rule: the Hierarchy's masters are "Ur-Quan", never "Kzer-Za".
