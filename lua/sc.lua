-- Star Control TC: the right-click ship devices (Glory Device, Mmrnmhrm
-- Transform), and the small amount of help the AI needs to use them.
-- Written against the Wesnoth 1.16 Lua API.

local T = wml.tag
local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc = {}


local function count(name)
	wml.variables["sc_stats." .. name] = (wml.variables["sc_stats." .. name] or 0) + 1
end

-- Every ship comes in levels 1-3: SC_X, SC_X_L2, SC_X_L3. The New Alliance
-- and the Agents of Chaos recruit their own level-1 copies of some older
-- ships, SC_X_NA and SC_X_AC.
local function base_type(t) return (t:gsub("_L[23]$", ""):gsub("_NA$", ""):gsub("_AC$", "")) end
local function is_a(u, base) return u and base_type(u.type) == base end
local function all_levels(base) return base .. "," .. base .. "_NA," .. base .. "_L2," .. base .. "_L3" end
local function by_level(tbl, u) return tbl[math.min(math.max(u.level, 1), #tbl)] end

local function is_ai(side)
	local c = wesnoth.sides[side].controller
	return c == "ai" or c == "network_ai"
end

-- Empty, enterable hexes next to (x, y).
local function free_neighbours(x, y)
	return wesnoth.map.find {
		T.filter_adjacent_location { x = x, y = y },
		T["not"] { terrain = "*^Yx" },
		T["not"] { T.filter {} },
	}
end

------------------------------------------------------------------ Glory Device

-- The Glory Device is a one-strike attack (see Shofixti_Scout.cfg); the
-- scout is destroyed once the attack is over.
function sc.glory_used()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if not u or not is_a(u, "SC_Shofixti_Scout") then return end
	count("glory")
	wesnoth.wml_actions.kill { x = u.x, y = u.y, animate = false, fire_event = true }
end

-- The listed damage is the average: each blast rolls from 2/3 to 4/3 of it
-- (12 -> 8-16). The engine re-reads the weapon after the attack event.
function sc.glory_roll()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if not u or not is_a(u, "SC_Shofixti_Scout") then return end
	for _, a in ipairs(u.attacks) do
		if a.name == "glory_device" then
			a.damage = mathx.random(math.floor(a.damage * 2 / 3 + 0.5), math.floor(a.damage * 4 / 3 + 0.5))
		end
	end
end

-- Fire scout s's Glory Device at enemy e, as a normal attack.
local function fire_glory(s, e)
	for i, a in ipairs(s.attacks) do
		if a.name == "glory_device" then
			wesnoth.wml_actions.do_command { T.attack {
				weapon = i - 1,
				T.source { x = s.x, y = s.y },
				T.destination { x = e.x, y = e.y },
			} }
			return
		end
	end
end

-- Human players pick the Glory Device from the attack dialog like any
-- weapon. An AI side's Scouts get it with attack_weight=0, so the AI never
-- chooses it on its own; ai_glory below decides when to set it off.
function sc.ai_glory_weight()
	for _, u in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout") }) do
		if is_ai(u.side) and not u.variables.sc_ai_glory then
			u.variables.sc_ai_glory = true
			u:add_modification("object", { T.effect { apply_to = "attack", name = "glory_device", attack_weight = 0 } })
		end
	end
end

-- Leaders don't carry a Glory Device: blowing one up would lose the game.
function sc.disarm_leaders()
	for _, u in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout"), canrecruit = true }) do
		u:add_modification("object", { T.effect { apply_to = "remove_attacks", name = "glory_device" } })
	end
end

-- [sc_name_leaders] [captain] faction= type= name= [/captain]: a leader of
-- that ship (any level) on a side of that faction gets that name.
function wesnoth.wml_actions.sc_name_leaders(cfg)
	for _, c in ipairs(wml.child_array(cfg, "captain")) do
		for _, u in ipairs(wesnoth.units.find_on_map { type = all_levels(c.type), canrecruit = true }) do
			if wesnoth.sides[u.side].__cfg.faction == c.faction then
				u.name = c.name
			end
		end
	end
end

--------------------------------------------------------------- Mmrnmhrm X <-> Y

function wesnoth.wml_actions.sc_transform(cfg)
	local u = wesnoth.units.get(cfg.x, cfg.y)
	if not u or u.attacks_left < 1 or u.moves < 1 then return end
	-- Same level, other shape: SC_Mmrnmhrm_XForm_L2 <-> SC_Mmrnmhrm_YWing_L2
	local to
	if u.type:match("^SC_Mmrnmhrm_XForm") then
		to = u.type:gsub("XForm", "YWing")
	elseif u.type:match("^SC_Mmrnmhrm_YWing") then
		to = u.type:gsub("YWing", "XForm")
	else
		return
	end
	count("transform")
	local hp = u.hitpoints
	wesnoth.audio.play("sc/mmrnmhrm-transform.wav")
	u:transform(to)
	-- The two shapes have different hulls, and transforming adds the new
	-- shape's hull trait next to the old one. Rebuild the unit without the
	-- old one.
	local keep
	for _, child in ipairs(wesnoth.unit_types[to].__cfg) do
		if child[1] == "trait" and tostring(child[2].id):match("^sc_hull_") then keep = child[2].id end
	end
	local cfg = u.__cfg
	for _, child in ipairs(cfg) do
		if child[1] == "modifications" then
			local kept = {}
			for _, mod in ipairs(child[2]) do
				local id = mod[1] == "trait" and tostring(mod[2].id) or ""
				if not (id:match("^sc_hull_") and id ~= keep) then kept[#kept + 1] = mod end
			end
			child[2] = kept
		end
	end
	local x, y = u.x, u.y
	u:erase()
	u = wesnoth.units.create(cfg)
	u:to_map(x, y)
	u.hitpoints = hp
	u.moves = 0
	u.attacks_left = 0
end

---------------------------------------------------------------------- AI help

-- End of an AI side's turn: a Shofixti that hasn't attacked uses its Glory
-- Device on a neighbour it would destroy, or on one worth three times its cost.
-- (sc.ai_glory_weight keeps the AI from choosing the weapon by itself.)
local function ai_glory(side)
	for _, s in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout"), side = side, canrecruit = false }) do
		local glory
		for _, a in ipairs(s.attacks) do if a.name == "glory_device" then glory = a end end
		if glory and s.attacks_left > 0 then
			local best, best_worth
			for _, e in ipairs(wesnoth.units.find_on_map {
				T.filter_side { T.enemy_of { side = side } },
				T.filter_adjacent { x = s.x, y = s.y },
				T["not"] { status = "petrified" },
			}) do
				local damage = glory.damage * e:resistance_against("fire") / 100
				local worth = (e.hitpoints <= damage) and e.cost * 2 or e.cost
				if (e.hitpoints <= damage or e.cost >= 3 * s.cost) and (not best or worth > best_worth) then
					best, best_worth = e, worth
				end
			end
			if best then fire_glory(s, best) end
		end
	end
end

-- Wesnoth's spread_poison step runs before normal combat and always fires
-- the poison weapon, never weighing the ship's other guns. That made the
-- Androsynth spit acid instead of ramming with the Blazer, and the L3 Mycon
-- use its weak spore burst. Drop it: normal combat still counts poison when
-- it picks the best weapon.
function sc.ai_no_spread_poison()
	for _, s in ipairs(wesnoth.sides) do
		wesnoth.sides.delete_ai_component(s.side, "stage[main_loop].candidate_action[spread_poison]")
	end
end

function sc.turn_end()
	local side = wesnoth.current.side
	if is_ai(side) then ai_glory(side) end
end

-------------------------------------------------------------------------- music

-- Each player hears their own faction's playlist (the scenario's default is
-- the Alliance one, which spectators and AI-only games keep). Music is not
-- game state, so playing it only on the local client is safe in multiplayer.
-- Track files are prefixed with their faction: 0. shared, 1. Alliance,
-- 2. Hierarchy, 3. New Alliance, 4. Death March.
--
-- The Alliance and the Hierarchy have three music modes: the original
-- tracks, the original tracks with the Precursors' remixes in place of the
-- ones they remix, or both. Each entry is one or more original tracks and,
-- under remix, what replaces them.
local VERSIONS = {
	SC_Alliance = {
		{ "1. commander", remix = { "0. remix-commander" } },
		{ "1. chenjesu-titus" }, { "1. mmrnmhrm-titus" },
		{ "1. yehat", remix = { "1. remix-yehat" } },
		{ "1. syreen", remix = { "0. remix-syreen" } },
		{ "1. arilou", remix = { "0. remix-arilou" } },
		{ "1. shofixti", remix = { "1. remix-shofixti" } },
		{ "1. quasispace", "1. quasispace-3do", remix = { "0. remix-quasispace", "0. remix-mystic-shadows" } },
		{ "1. hyperspace-anamnesis" },   -- a cover; no remix, so in every mode
		{ "0. starbase", remix = { "0. remix-starbase" } },
	},
	SC_Hierarchy = {
		{ "2. urquan", remix = { "2. urquan-now-and-forever", "2. urquan-erol-otus" } },
		{ "2. mycon", remix = { "0. mycon-rebirth" } },
		{ "2. spathi", remix = { "2. remix-spathi", "2. remix-spathi-fwiffo" } },
		{ "2. umgah", remix = { "2. remix-umgah" } },
		{ "2. vux", remix = { "2. remix-vux", "2. remix-vux-acid" } },
		{ "2. ilwrath", remix = { "0. ilwrath-all-evil" } },
		{ "2. thraddash", remix = { "0. thraddash-culture-19" } },
		{ "2. androsynth-duoled", remix = { "2. androsynth-ramen-rider" } },
		{ "2. urquan-idan-schneider" },   -- an orchestral cover; no remix, so in every mode
		{ "0. starbase", remix = { "0. remix-starbase" } },
		{ remix = { "0. remix-hyperspace" } },   -- no original hyperspace track here
	},
}

local MUSIC_MODES = { "original", "remixes", "both" }
local MUSIC_MODE_NAMES = {
	original = _ "original tracks",
	remixes = _ "the Precursors' remixes",
	both = _ "original tracks and the Precursors' remixes",
}

local PLAYLISTS = {   -- faction -> mode -> tracks
	-- the New Alliance hears the Precursors' remixes (and a cover and a
	-- re-imagined Melnorme theme)
	SC_NewAlliance = { "3. remix-chmmr", "3. remix-zoqfotpik", "3. remix-pkunk", "3. remix-supox", "3. remix-utwig",
		"3. remix-utwig-ultron", "0. remix-commander", "0. remix-arilou", "3. remix-melnorme", "3. melnorme-lipavsky", "0. remix-syreen", "3. syreen-ramen-rider",
		"0. remix-mystic-shadows", "0. remix-quasispace", "0. remix-hyperspace",
		"0. remix-starbase" },
	-- the Agents of Chaos hear modern versions: the Precursors' remixes
	SC_DeathMarch = { "4. kohrah-cleansing-required", "4. kohrah-eternal-doctrine", "4. kohrah-battle",
		"4. druuge-crimson-corporation", "0. thraddash-culture-19", "4. slylandro-we-come-in-peace",
		"4. orz-squeezing-the-juice", "0. mycon-rebirth", "0. ilwrath-all-evil", "4. samatra-battle",
		"0. remix-hyperspace", "0. remix-starbase" },
}
for faction, list in pairs(PLAYLISTS) do
	PLAYLISTS[faction] = { original = list }
end
for faction, entries in pairs(VERSIONS) do
	local modes = { original = {}, remixes = {}, both = {} }
	for _, entry in ipairs(entries) do
		for _, track in ipairs(entry) do
			table.insert(modes.original, track)
			table.insert(modes.both, track)
			if not entry.remix then table.insert(modes.remixes, track) end
		end
		for _, track in ipairs(entry.remix or {}) do
			table.insert(modes.remixes, track)
			table.insert(modes.both, track)
		end
	end
	PLAYLISTS[faction] = modes
end

-- Theme played when you win. It is a sound effect, not music, so it follows
-- the sound volume like the victory ditties; the music stops for it (the
-- engine "plays" a silent victory track).
local VICTORY_THEME = {
	SC_Alliance = "sc/alliance-victory.ogg",     -- Star Control 1's Alliance victory theme
	SC_Hierarchy = "sc/hierarchy-victory.ogg",   -- Star Control 1's Hierarchy victory theme
	SC_NewAlliance = "sc/victory-fanfare.ogg",   -- Star Control II's victory fanfare
	SC_DeathMarch = "sc/funeral-march.ogg",      -- Chopin's Funeral March (Sonata No. 2), opening phrase
}

local function local_human_side()
	for _, side in ipairs(wesnoth.sides) do
		if side.is_local and side.controller == "human" then return side end
	end
end

function sc.victory_theme()
	local side = local_human_side()
	local theme = side and VICTORY_THEME[side.__cfg.faction]
	if theme then wesnoth.audio.play(theme) end
end

-- Wesnoth 1.16 and 1.18 never move past a track marked shuffle=no: when it
-- ends, the same track starts again (only 1.19 plays an unshuffled list in
-- order). So the playlist keeps the engine's shuffle, which keeps a track
-- from coming back within two others and from playing a third time before
-- every other track has played. Only the opening track is ours to choose: it
-- comes from a shuffle made with the synced random numbers, so every client
-- shuffles every playlist (in the same order) to stay in sync, then plays
-- only its own.
local function shuffled(list)
	local deck = {}
	for i, track in ipairs(list) do deck[i] = track end
	for i = #deck, 2, -1 do
		local j = mathx.random(i)
		deck[i], deck[j] = deck[j], deck[i]
	end
	return deck
end

local function play(list)
	for i, track in ipairs(list) do
		wesnoth.wml_actions.music {
			name = "sc/" .. track .. ".ogg",
			append = i > 1,
			immediate = i == 1,
			shuffle = true,
		}
	end
end

local function local_playlists()
	local side = local_human_side()
	return side and PLAYLISTS[side.__cfg.faction]
end

local music_mode = nil   -- this client's, see current_music_mode

-- The host picks the music mode everyone starts with (the era's "Music"
-- option, the sc_music variable).
function sc.set_music()
	local start_mode = wml.variables["sc_music"]
	if not MUSIC_MODE_NAMES[start_mode] then start_mode = "original" end
	local factions = {}
	for faction in pairs(PLAYLISTS) do table.insert(factions, faction) end
	table.sort(factions)
	local decks = {}
	for _, faction in ipairs(factions) do
		decks[faction] = {}
		for _, mode in ipairs(MUSIC_MODES) do
			if PLAYLISTS[faction][mode] then decks[faction][mode] = shuffled(PLAYLISTS[faction][mode]) end
		end
	end

	local side = local_human_side()
	local deck = side and decks[side.__cfg.faction]
	if deck then
		music_mode = deck[start_mode] and start_mode or "original"
		play(deck[music_mode])
	end
end

function sc.has_music_modes()
	local playlists = local_playlists()
	return playlists ~= nil and playlists.remixes ~= nil
end

-- The music mode now playing: the one last picked here, or, after a saved
-- game is loaded (which keeps the playlist but not music_mode), read from
-- the playlist itself.
local function current_music_mode(playlists)
	if music_mode then return music_mode end
	local playing = {}
	for i = 1, #wesnoth.audio.music_list do
		playing[wesnoth.audio.music_list[i].name] = true
	end
	local function has_all(list)
		for _, track in ipairs(list) do
			if not playing["sc/" .. track .. ".ogg"] then return false end
		end
		return true
	end
	if has_all(playlists.both) then return "both" end
	if has_all(playlists.remixes) then return "remixes" end
	return "original"
end

-- The "Switch music" menu item: the next music mode, for this player only.
-- It runs unsynced, so the random opening track is this client's own.
function sc.next_music_mode()
	local playlists = local_playlists()
	if not (playlists and playlists.remixes) then return end
	local mode = current_music_mode(playlists)
	for i, m in ipairs(MUSIC_MODES) do
		if m == mode then mode = MUSIC_MODES[i % #MUSIC_MODES + 1] break end
	end
	music_mode = mode
	play(shuffled(playlists[mode]))
	wesnoth.interface.add_chat_message(_ "Music", MUSIC_MODE_NAMES[mode])
end

---------------------------------------------------------------- victory ditties

-- When a ship destroys another, its race's Star Control victory ditty plays
-- over the music, which keeps playing at full volume. Nothing here is game
-- state (sound is local), so it is safe in multiplayer.
local DITTIES = {   -- races with a sounds/sc/ditty-<race>.ogg
	androsynth = true, arilou = true, chenjesu = true, chmmr = true,
	druuge = true, earthling = true, ilwrath = true, kohrah = true,
	mmrnmhrm = true, mycon = true, orz = true, pkunk = true,
	precursor = true, shofixti = true, slylandro = true, spathi = true,
	supox = true, syreen = true, thraddash = true, umgah = true,
	urquan = true, utwig = true, vux = true, yehat = true,
	zoqfotpik = true, melnorme = true,
	samatra = true,     -- the Precursors' remix of the Kohr-Ah ditty
}

function sc.victory_ditty()
	local killer = wesnoth.units.get(wml.variables["x2"], wml.variables["y2"])
	if not killer then return end
	local race = tostring(killer.race):match("^sc_(.+)$")
	if not race or not DITTIES[race] then return end
	wesnoth.audio.play("sc/ditty-" .. race .. ".ogg")
end

------------------------------------------------------------- Pkunk rebirth

-- A destroyed Pkunk Fury may be reborn: the same ship, back at full HP
-- where it died, unable to act until its next turn. The first time the
-- chance is 80%, and it halves with every rebirth (40%, 20%, ...).
-- Replacing the dying unit inside its "die" event tells Wesnoth not to
-- remove it. The SC2 reincarnation "hallelujah" plays instead of the
-- killer's victory ditty, once the explosion has died away: the death
-- animation is 630 ms but sc/ship-dies.wav runs about 1650 ms, so the
-- reborn ship and its hallelujah wait out the rest of the bang.
-- Returns true if the ship was reborn.
local REBIRTH_CHANCE = 80
local REBIRTH_DELAY = 1050   -- ms between the "die" event and the rebirth
function sc.pkunk_rebirth()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if not u or not u:matches { ability = "sc_reincarnation" } then return end
	local rebirths = u.variables.sc_rebirths or 0
	if mathx.random(100) > REBIRTH_CHANCE / 2 ^ rebirths then return end
	count("rebirth")
	u.variables.sc_rebirths = rebirths + 1
	local cfg = u.__cfg
	cfg.hitpoints = u.max_hitpoints
	cfg.moves = 0
	cfg.attacks_left = 0
	local x, y = u.x, u.y
	u:erase()
	wesnoth.interface.delay(REBIRTH_DELAY)
	local reborn = wesnoth.units.create(cfg)
	reborn.status.poisoned = false   -- reborn clean
	reborn.status.slowed = false
	reborn:to_map(x, y)
	wesnoth.audio.play("sc/pkunk-rebirth.wav")
	wesnoth.interface.float_label(x, y, "<span color='#ffe680'>" .. tostring(_ "Reborn!") .. "</span>")
	return true
end

------------------------------------------------------------ Precursor artifacts

-- Hidden on about one planet in five (never next to a starbase). The first
-- ship to enter that planet finds it: a random permanent bonus, shown as a
-- trait, plus some experience. On mirrored maps they come in mirror pairs.
local ARTIFACT_XP = 8   -- also in the floating text, tools/make_artifact_text.py
local ARTIFACTS = {
	{ id = "drive",    name = _ "+drive",
	  description = _ "Precursor artifact: a drive unit. +1 movement, and 10% better defense on every terrain.",
	  effects = { { apply_to = "movement", increase = 1 },
		{ apply_to = "defense", replace = false, T.defense {   -- chance to be hit, so -10 is +10% defense
			space = -10, nebula = -10, rednebula = -10, ionstorm = -10, lightstorm = -10, dust = -10,
			asteroids = -10, dense_asteroids = -10, planet = -10, starbase = -10 } } } },
	{ id = "crew",     name = _ "+crew",
	  description = _ "Precursor artifact: life-support pods, room for more crew. +8 max HP.",
	  effects = { { apply_to = "hitpoints", increase_total = 8, increase = 8 } } },
	{ id = "battery",  name = _ "+battery",
	  description = _ "Precursor artifact: a bigger energy battery. +1 strike on every attack.",
	  effects = { { apply_to = "attack", increase_attacks = 1 } } },
	{ id = "recharge", name = _ "+recharge",
	  description = _ "Precursor artifact: a battery recharger. +2 damage on every attack.",
	  effects = { { apply_to = "attack", increase_damage = 2 } } },
}

local function artifact_key(x, y) return "sc_artifact_" .. x .. "_" .. y end

-- Planet animations: Star Control's scenes from the status panel, played as
-- a halo on the hex below a planet, under its label (above near the bottom
-- edge), to this client alone, so only if its player can see the planet.
-- The last picture is held, then faded out over 4 frames, then nothing until
-- the halo is taken off at the side's next turn (left until then so one
-- played just before ending the turn plays out in full; a halo animation
-- loops, so the blank last frame lasts far longer than anyone waits). Frames
-- are made by tools/make_planet_anims.py.
local function planet_anim_halo(file, frames, ms, hold)
	local function halo(where)
		local f = {}
		for i = 1, frames do
			f[i] = string.format("halo/sc/%s-%s-%03d.png:%d", file, where, i, i == frames - 4 and hold or ms)
		end
		f[#f + 1] = "misc/blank-hex.png:3600000"
		return table.concat(f, ",")
	end
	return { above = halo("above"), below = halo("below") }
end

local function planet_anim_where(y)
	return y >= wesnoth.current.map.playable_height - 1 and "above" or "below"
end

-- The Precursor device's screen filling with glyphs: 103 frames at 15 fps,
-- the finished screen held 1.5 s.
local ARTIFACT_ANIM = "sc_artifact_anim"
local ARTIFACT_ANIM_HALO = planet_anim_halo("artifact", 107, 66, 1500)

-- "Precursor Artifact! / Crew gets +8 XP", rising slowly off the planet over
-- 3 s and fading out (frames made by tools/make_artifact_text.py: 1.16's own
-- floating text is gone within a second, too fast to read).
local ARTIFACT_TEXT = "sc_artifact_text"
local ARTIFACT_TEXT_HALO = (function()
	local f = {}
	for i = 1, 72 do f[i] = string.format("halo/sc/artifact-text-%03d.png:50", i) end
	f[#f + 1] = "misc/blank-hex.png:3600000"
	return table.concat(f, ",")
end)()

-- Whether this client's player can see the hex: the find is announced only
-- to players who could see the planet, not through fog or shroud.
local function locally_visible(x, y)
	local side, full_vision = wesnoth.interface.get_viewing_side()
	if full_vision then return true end
	return not wesnoth.sides.is_fogged(side, x, y) and not wesnoth.sides.is_shrouded(side, x, y)
end

function sc.place_artifacts()
	local map = wesnoth.current.map
	local planets = wesnoth.map.find {
		terrain = "*^Vy*",
		T["not"] { T.filter_adjacent_location { terrain = "Yk,Yc,Yci" } },
		T["not"] { terrain = "Yk,Yc,Yci" },
	}
	local is_planet = {}
	for _, p in ipairs(planets) do is_planet[p[1] .. "," .. p[2]] = true end
	local wanted = math.max(2, math.floor(#planets / 5))
	local placed = 0
	while placed < wanted and #planets > 0 do
		local i = mathx.random(#planets)
		local x, y = planets[i][1], planets[i][2]
		table.remove(planets, i)
		if not wml.variables[artifact_key(x, y)] then
			wml.variables[artifact_key(x, y)] = true
			placed = placed + 1
			-- its mirror image, if the map is mirrored left-right here
			local mx = map.playable_width + 1 - x
			if is_planet[mx .. "," .. y] and not wml.variables[artifact_key(mx, y)] then
				wml.variables[artifact_key(mx, y)] = true
				placed = placed + 1
			end
		end
	end
end

function sc.check_artifact()
	local x, y = wml.variables["x1"], wml.variables["y1"]
	if not wml.variables[artifact_key(x, y)] then return end
	local u = wesnoth.units.get(x, y)
	if not u then return end
	wml.variables[artifact_key(x, y)] = nil
	count("artifacts")

	local a = ARTIFACTS[mathx.random(#ARTIFACTS)]
	local n = (u.variables.sc_artifacts or 0) + 1
	u.variables.sc_artifacts = n
	local trait = {
		id = "sc_artifact_" .. a.id .. "_" .. n,
		male_name = a.name, female_name = a.name,
		description = a.description,
	}
	for _, e in ipairs(a.effects) do trait[#trait + 1] = T.effect(e) end
	u:add_modification("trait", trait)
	-- Sound, animation and floating text are this client's alone (they change
	-- nothing in the game; the animation is a bare hex overlay, not an [item],
	-- so it is never saved), so each client shows them only if its player can
	-- see the planet.
	if locally_visible(x, y) then
		wesnoth.audio.play("sc/artifact.wav")
		wesnoth.interface.add_hex_overlay(x, y, { name = ARTIFACT_ANIM, halo = ARTIFACT_ANIM_HALO[planet_anim_where(y)] })
		wesnoth.interface.add_hex_overlay(x, y, { name = ARTIFACT_TEXT, halo = ARTIFACT_TEXT_HALO })
	end
	-- The floating text fades within a few seconds, so a label naming the
	-- find stays on the planet until the finder's next turn starts (hidden
	-- from players who have the planet under fog).
	wesnoth.map.add_label { x = x, y = y, color = "255,216,74", immutable = true,
		visible_in_fog = false, visible_in_shroud = false,
		text = tostring(_ "Precursor artifact: ") .. tostring(a.name) }
	local labels = wml.array_access.get("sc_artifact_labels")
	labels[#labels + 1] = { x = x, y = y, side = u.side }
	wml.array_access.set("sc_artifact_labels", labels)

	u.experience = u.experience + ARTIFACT_XP
	if u.experience >= u.max_experience then u:advance(true, true) end
end

-- Start of a side's turn: clear the artifact labels (and animations) it put
-- up last turn.
function sc.expire_artifact_labels()
	local keep = {}
	for _, l in ipairs(wml.array_access.get("sc_artifact_labels")) do
		if l.side == wesnoth.current.side then
			wesnoth.map.add_label { x = l.x, y = l.y, text = "" }
			wesnoth.interface.remove_hex_overlay(l.x, l.y, ARTIFACT_ANIM)
			wesnoth.interface.remove_hex_overlay(l.x, l.y, ARTIFACT_TEXT)
		else
			keep[#keep + 1] = l
		end
	end
	wml.array_access.set("sc_artifact_labels", keep)
end

--------------------------------------------------------------- Syreen crew

-- The Syreen Penetrator has room for a huge crew (max HP as high as an
-- Ur-Quan Dreadnought's) but always leaves port with a small one, and fills
-- the rest by luring enemy crew across with its song. Recruits, leaders
-- placed at the start and freshly promoted ships all start at these HP.
local SYREEN_START_HP = { 28, 36, 44 }

local function syreen_low_start(u, floor)
	if not is_a(u, "SC_Syreen_Penetrator") then return end
	local hp = math.max(by_level(SYREEN_START_HP, u), floor or 0)
	u.hitpoints = math.min(hp, u.max_hitpoints)
end

-- recruit: the event's unit.
function sc.syreen_recruited()
	syreen_low_start(wesnoth.units.get(wml.variables["x1"], wml.variables["y1"]))
end

-- prestart: every Syreen already on the map (leaders).
function sc.syreen_prestart()
	for _, u in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Syreen_Penetrator") }) do
		syreen_low_start(u)
	end
end

-- Promotion fully heals a ship; a Syreen instead gains the step between the
-- two levels' starting HP (+8), and is raised to the new level's starting
-- HP if that is still more.
function sc.syreen_before_advance()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if not is_a(u, "SC_Syreen_Penetrator") then return end
	u.variables.sc_pre_advance_hp = u.hitpoints
	u.variables.sc_pre_advance_start = by_level(SYREEN_START_HP, u)
end

function sc.syreen_after_advance()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if not is_a(u, "SC_Syreen_Penetrator") then return end
	local hp = u.variables.sc_pre_advance_hp
	if hp then
		hp = hp + by_level(SYREEN_START_HP, u) - u.variables.sc_pre_advance_start
	end
	syreen_low_start(u, hp)
	u.variables.sc_pre_advance_hp = nil
	u.variables.sc_pre_advance_start = nil
end

-- Healing (planets, healers, resting) only repairs a Syreen up to its
-- level's starting HP; only stolen crew takes it above that. "side turn"
-- fires before a side heals and "turn refresh" after.
function sc.syreen_before_healing()
	for _, u in ipairs(wesnoth.units.find_on_map { side = wesnoth.current.side, race = "sc_syreen" }) do
		u.variables.sc_hp_before_healing = u.hitpoints
	end
end

function sc.syreen_after_healing()
	for _, u in ipairs(wesnoth.units.find_on_map { side = wesnoth.current.side, race = "sc_syreen" }) do
		local before = u.variables.sc_hp_before_healing
		u.variables.sc_hp_before_healing = nil
		if before and u.hitpoints > before then
			local cap = math.max(before, by_level(SYREEN_START_HP, u))
			u.hitpoints = math.min(u.hitpoints, cap)
		end
	end
end

-- The captain watching her ship fill up with the planet's colonists: 103
-- frames at 15 fps.
local SYREEN_CAPTURE_ANIM = "sc_syreen_capture_anim"
local SYREEN_CAPTURE_HALO = planet_anim_halo("syreen-capture", 107, 67, 1000)
-- The colony's domes blown apart and left burning: 104 frames at 15 fps.
local COLONY_DESTROYED_ANIM = "sc_colony_destroyed_anim"
local COLONY_DESTROYED_HALO = planet_anim_halo("colony-destroyed", 108, 67, 1000)
-- The mining vehicle on the planet, the blast, and the screen whiting out:
-- 68 frames at 15 fps, fading out as soon as it is all white.
local MINE_DESTROYED_ANIM = "sc_mine_destroyed_anim"
local MINE_DESTROYED_HALO = planet_anim_halo("mine-destroyed", 72, 67, 67)
-- Each animation's list of { x, y, side } still showing, to take off.
local PLANET_ANIMS = {
	[SYREEN_CAPTURE_ANIM] = "sc_syreen_capture_anims",
	[COLONY_DESTROYED_ANIM] = "sc_colony_destroyed_anims",
	[MINE_DESTROYED_ANIM] = "sc_mine_destroyed_anims",
}

local function play_planet_anim(x, y, side, name, halo)
	if locally_visible(x, y) then
		wesnoth.interface.remove_hex_overlay(x, y, name)
		wesnoth.interface.add_hex_overlay(x, y, { name = name,
			halo = halo[planet_anim_where(y)] })
	end
	local l = wml.array_access.get(PLANET_ANIMS[name])
	l[#l + 1] = { x = x, y = y, side = side }
	wml.array_access.set(PLANET_ANIMS[name], l)
end

local function planet_overlay(x, y)
	return wesnoth.current.map[{ x, y }]:match("%^(.+)$")
end

local function is_life_world(x, y)
	local overlay = planet_overlay(x, y)
	return overlay == "Vyl" or overlay == "Vysl"
end

local function is_mineral_world(x, y)
	local overlay = planet_overlay(x, y)
	return overlay == "Vym" or overlay == "Vysm"
end

-- Whether ship u landing on a planet taken from side owner is a Syreen
-- taking an enemy's colony (life world): its colonists join her crew.
local function syreen_fills_crew(u, owner)
	return is_a(u, "SC_Syreen_Penetrator") and owner > 0
		and wesnoth.sides.is_enemy(u.side, owner) and is_life_world(u.x, u.y)
end

-- Capturing an enemy's life world: its colonists join the Syreen (full HP).
function sc.syreen_captured()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	local owner = wml.variables["owner_side"] or 0
	if syreen_fills_crew(u, owner) then
		u.hitpoints = u.max_hitpoints
		play_planet_anim(u.x, u.y, u.side, SYREEN_CAPTURE_ANIM, SYREEN_CAPTURE_HALO)
		-- and a label on the planet for the rest of the Syreen side's turn
		-- (hidden from players who have it under fog)
		wesnoth.map.add_label { x = u.x, y = u.y, color = "255,128,208", immutable = true,
			visible_in_fog = false, visible_in_shroud = false,
			text = tostring(_ "Syreen gains full crew.") }
		local l = wml.array_access.get("sc_syreen_capture_labels")
		l[#l + 1] = { x = u.x, y = u.y, side = u.side }
		wml.array_access.set("sc_syreen_capture_labels", l)
	end
end

-- End of a side's turn: take down the capture labels it put up this turn.
function sc.expire_syreen_capture_labels()
	local keep = {}
	for _, a in ipairs(wml.array_access.get("sc_syreen_capture_labels")) do
		if a.side == wesnoth.current.side then
			wesnoth.map.add_label { x = a.x, y = a.y, text = "" }
		else
			keep[#keep + 1] = a
		end
	end
	wml.array_access.set("sc_syreen_capture_labels", keep)
end

-- Start of a side's turn: take off the planet animations it played last turn.
function sc.expire_planet_anims()
	for name, list in pairs(PLANET_ANIMS) do
		local keep = {}
		for _, a in ipairs(wml.array_access.get(list)) do
			if a.side == wesnoth.current.side then
				wesnoth.interface.remove_hex_overlay(a.x, a.y, name)
			else
				keep[#keep + 1] = a
			end
		end
		wml.array_access.set(list, keep)
	end
end

-------------------------------------------------------------------- reporting

function sc.note_levelup()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if u then count("level" .. u.level) end
end

function sc.note_recruit()
	local u = wesnoth.units.get(wml.variables["x1"], wml.variables["y1"])
	if u then count("recruit_" .. u.side .. "_" .. u.type:gsub("^SC_", "")) end
end

-- One line on stdout per finished game, for tools/ai_battles.sh.
function sc.report_result()
	local parts = {}
	for _, s in ipairs(wesnoth.sides) do
		if s.hidden then goto continue end   -- e.g. the Caves' derelicts
		local units = wesnoth.units.find_on_map { side = s.side }
		local leader = #wesnoth.units.find_on_map { side = s.side, canrecruit = true } > 0
		local faction = s.__cfg.faction or "?"
		parts[#parts + 1] = string.format("side%d=%s units=%d leader=%s gold=%d",
			s.side, faction, #units, tostring(leader), s.gold)
		::continue::
	end
	local stats = wml.variables["sc_stats"] or {}
	local recruits = {}
	for k, v in pairs(stats) do
		if k:match("^recruit_") then recruits[#recruits + 1] = k:gsub("^recruit_", "") .. "=" .. v end
	end
	table.sort(recruits)
	std_print(string.format("SC_RESULT turn=%d %s glory=%d transform=%d artifacts=%d rebirth=%d to_L2=%d to_L3=%d recruits: %s",
		wesnoth.current.turn, table.concat(parts, " "),
		stats.glory or 0, stats.transform or 0, stats.artifacts or 0, stats.rebirth or 0,
		stats.level2 or 0, stats.level3 or 0,
		table.concat(recruits, " ")))
end

-- Older versions turned the music down during a ditty; a game saved then
-- must not load with the music turned down.
wesnoth.audio.music_list.volume = 100

-- Older versions also turned the engine's shuffle off, which on Wesnoth 1.16
-- and 1.18 repeats the opening track for the whole game (see sc.set_music);
-- a game saved then must load with the shuffle back on.
for i = 1, #wesnoth.audio.music_list do
	pcall(function() wesnoth.audio.music_list[i].shuffle = true end)
end

------------------------------------------------------------------ Ambushes

-- The engine stops a ship that stumbles onto a hidden enemy and takes away
-- the rest of its movement. Where the hidden ship sits in the badlands we
-- give the movement back: the finder still stops where it found the enemy,
-- but can then move on. Ships listed in FULL_AMBUSH_IN_BADLANDS keep the
-- full ambush there too.
--
-- exit_hex fires just before each step, while the hidden ships around the
-- next hex are still hidden (the engine's own ambush test); enter_hex fires
-- after the step, with the ship's moves for that hex already paid; moveto
-- fires after the engine has zeroed them.
local ambush = nil

local BADLANDS = { Yi = true, Yis = true, Yif = true, Yu = true, Yus = true, Yuf = true }
local FULL_AMBUSH_IN_BADLANDS = {
	SC_Arilou_Skiff = true,
	SC_ZoqFotPik_Stinger = true,
	SC_Androsynth_Guardian = true,
	SC_Slylandro_Probe = true,
}

-- Whether the hidden ship e takes away all of its finder's movement.
local function full_ambush(e)
	local base = wesnoth.current.map[{ e.x, e.y }]:match("^[^^]*")
	return not BADLANDS[base] or FULL_AMBUSH_IN_BADLANDS[base_type(e.type)] == true
end

local function hidden_from(side, x, y)
	return wesnoth.units.find_on_map {
		T.filter_side { T.enemy_of { side = side } },
		T.filter_vision { side = side, visible = false },
		T.filter_location { T.filter_adjacent_location { x = x, y = y } },
	}
end

-- Whether e is hiding: the engine's test, before the mover gets next to it.
local function hides(e)
	if e.status.uncovered or not e:ability("hides") then return false end
	return #wesnoth.units.find_on_map {
		T.filter_side { T.enemy_of { side = e.side } },
		T.filter_adjacent { id = e.id },
		T["not"] { status = "petrified" },
	} == 0
end

function sc.ambush_exit_hex()
	local c = wesnoth.current.event_context
	local u = wesnoth.units.get(c.x1, c.y1)
	ambush = nil
	if not u then return end
	local hidden = false
	for _, e in ipairs(hidden_from(u.side, c.x2, c.y2)) do
		-- The filter also counts ships merely lost in the fog, which the
		-- engine does not treat as an ambush.
		if not wesnoth.sides.is_fogged(u.side, e.x, e.y) or hides(e) then
			if full_ambush(e) then return end
			hidden = true
		end
	end
	if not hidden then return end
	-- A ship entering a known enemy's zone of control, or capturing a
	-- planet, would stop with nothing left anyway.
	local zoc = false
	for _, e in ipairs(wesnoth.units.find_on_map {
		T.filter_side { T.enemy_of { side = u.side } },
		T.filter_vision { side = u.side, visible = true },
		T.filter_location { T.filter_adjacent_location { x = c.x2, y = c.y2 } },
	}) do
		if e.zoc then zoc = true end
	end
	local capture = wesnoth.terrain_types[wesnoth.current.map[{ c.x2, c.y2 }]].village
		and wesnoth.map.get_owner(c.x2, c.y2) ~= u.side
	ambush = { id = u.id, x = c.x2, y = c.y2, zoc = zoc, capture = capture }
end

function sc.ambush_enter_hex()
	local c = wesnoth.current.event_context
	if not ambush or ambush.x ~= c.x1 or ambush.y ~= c.y1 then return end
	local u = wesnoth.units.get(c.x1, c.y1)
	if not u or u.id ~= ambush.id then ambush = nil; return end
	ambush.moves = u.moves
	if ambush.zoc and u:ability("skirmisher") then ambush.zoc = false end
end

-- A hidden ship (cloaked or in ambush) that ends up next to an enemy has
-- been found: it stays uncovered until its own side's next turn starts (the
-- engine clears the status then), instead of vanishing again as soon as the
-- enemy moves away.
local function uncover_hidden(u)
	local enemies = wesnoth.units.find_on_map {
		T.filter_side { T.enemy_of { side = u.side } },
		T.filter_adjacent { id = u.id },
	}
	for _, e in ipairs(enemies) do
		if e:ability("hides") then e.status.uncovered = true end
	end
	if #enemies > 0 and u:ability("hides") then u.status.uncovered = true end
end

function sc.ambush_moveto()
	local a = ambush
	ambush = nil
	local c = wesnoth.current.event_context
	local mover = wesnoth.units.get(c.x1, c.y1)
	if mover then uncover_hidden(mover) end
	if not a or not a.moves or a.x ~= c.x1 or a.y ~= c.y1 then return end
	if a.zoc or a.capture then return end
	local u = wesnoth.units.get(c.x1, c.y1)
	if u and u.id == a.id and u.moves == 0 then u.moves = a.moves end
end

------------------------------------------------------------------ Held cones

-- The Umgah antimatter cone stays lit for a whole fight: it is an item halo
-- on the Drone's hex, pointing at its opponent, from the attack event until
-- the fight ends or a ship is destroyed. The images are baked per facing by
-- tools/make_umgah_cone_halos.py.
local CONE_WEAPON = "antimatter_cone"
local held_cones = {}

-- Facing from (x1, y1) to the adjacent hex (x2, y2). Even columns sit half a
-- hex lower than odd ones.
local function facing(x1, y1, x2, y2)
	if x2 == x1 then return y2 < y1 and "n" or "s" end
	local up = y2 < y1 or (y2 == y1 and x1 % 2 == 0)
	if x2 > x1 then return up and "ne" or "se" end
	return up and "nw" or "sw"
end

local function hold(weapon, x1, y1, x2, y2)
	if not weapon or weapon.name ~= CONE_WEAPON then return end
	local halo = "halo/sc/umgah-cone-" .. facing(x1, y1, x2, y2) .. ".png"
	wesnoth.wml_actions.item { x = x1, y = y1, halo = halo }
	table.insert(held_cones, { x = x1, y = y1, halo = halo })
end

function sc.cone_hold()
	local c = wesnoth.current.event_context
	hold(c.weapon, c.x1, c.y1, c.x2, c.y2)
	hold(c.second_weapon, c.x2, c.y2, c.x1, c.y1)
end

function sc.cone_release()
	for _, h in ipairs(held_cones) do
		wesnoth.wml_actions.remove_item { x = h.x, y = h.y, image = h.halo }
	end
	held_cones = {}
end

-- Planet types --------------------------------------------------------------
-- Each planet type pays its own gold and supports its own upkeep:
--   mineral world  2 gold, supports 2 levels of upkeep
--   life world     1 gold, supports 2
--   dead world     0 gold, supports 1
-- An untyped planet (^Vyp, ^Vys) pays what the game settings say.
-- Wesnoth only knows one village gold and support per side, so those are
-- set to 0 and the planets' share is folded into the side's base income,
-- kept up to date whenever planets or ships change hands:
--   base income = the game's base income + planet gold
--                 + the upkeep the planets support (no more than is owed)
-- which leaves the engine's income = base + gold - (upkeep - support, if any).
local PLANET_YIELD = {
	Vym = { 2, 2 }, Vysm = { 2, 2 },
	Vyl = { 1, 2 }, Vysl = { 1, 2 },
	Vyd = { 0, 1 }, Vysd = { 0, 1 },
}

local function planet_yield(terrain, side)
	local overlay = terrain:match("%^(.+)$")
	local y = overlay and PLANET_YIELD[overlay]
	if y then return y[1], y[2] end
	return wml.variables["sc_village_gold_" .. side], wml.variables["sc_village_support_" .. side]
end

function sc.setup_planet_income()
	for _, side in ipairs(wesnoth.sides) do
		local n = side.side
		wml.variables["sc_base_income_" .. n] = side.base_income
		wml.variables["sc_village_gold_" .. n] = side.village_gold
		wml.variables["sc_village_support_" .. n] = side.village_support
		side.village_gold = 0
		side.village_support = 0
	end
	sc.update_planet_income()
end

function sc.update_planet_income()
	local gold, support = {}, {}
	for _, v in ipairs(wesnoth.map.find { terrain = "*^Vy*" }) do
		local owner = wesnoth.map.get_owner(v)
		if owner and owner > 0 then
			local g, s = planet_yield(wesnoth.current.map[v], owner)
			gold[owner] = (gold[owner] or 0) + (g or 0)
			support[owner] = (support[owner] or 0) + (s or 0)
		end
	end
	for _, side in ipairs(wesnoth.sides) do
		local n = side.side
		local base = wml.variables["sc_base_income_" .. n]
		if base then
			side.base_income = base + (gold[n] or 0) + math.min(side.total_upkeep, support[n] or 0)
		end
	end
end

-- Taking planets -------------------------------------------------------------
-- A ship that lands on a planet doesn't take it straight away. An enemy's
-- planet is destroyed (it goes to nobody), and a free planet gets a colony,
-- mine or outpost built on it, which is the ship's side's once its next turn
-- starts, if the ship is still there. Until then the planet is labelled.
local CLAIMS = "sc_planet_claims"
local BUILD = {
	Vyl = _ "Colony next turn", Vysl = _ "Colony next turn",
	Vym = _ "Mine next turn", Vysm = _ "Mine next turn",
}

local function claim_label(x, y, text)
	wesnoth.map.add_label { x = x, y = y, color = "160,224,255", immutable = true,
		visible_in_fog = false, visible_in_shroud = false, text = text }
end

function sc.planet_captured()
	local c = wesnoth.current.event_context
	local u = wesnoth.units.get(c.x1, c.y1)
	local owner = wml.variables["owner_side"] or 0
	wesnoth.map.set_owner(c.x1, c.y1, 0, false)
	if owner > 0 and locally_visible(c.x1, c.y1) then
		wesnoth.interface.float_label(c.x1, c.y1,
			"<span color='#ff8060'>" .. tostring(_ "Planet destroyed") .. "</span>")
	end
	if not u then return end
	-- an enemy's colony blown up, unless a Syreen is taking its colonists,
	-- or an enemy's mine
	if owner > 0 and wesnoth.sides.is_enemy(u.side, owner) then
		if is_life_world(c.x1, c.y1) and not syreen_fills_crew(u, owner) then
			play_planet_anim(c.x1, c.y1, u.side, COLONY_DESTROYED_ANIM, COLONY_DESTROYED_HALO)
		elseif is_mineral_world(c.x1, c.y1) then
			play_planet_anim(c.x1, c.y1, u.side, MINE_DESTROYED_ANIM, MINE_DESTROYED_HALO)
		end
	end
	local claims = wml.array_access.get(CLAIMS)
	claims[#claims + 1] = { x = c.x1, y = c.y1, side = u.side, id = u.id }
	wml.array_access.set(CLAIMS, claims)
	local overlay = planet_overlay(c.x1, c.y1)
	claim_label(c.x1, c.y1, tostring(BUILD[overlay] or _ "Outpost next turn"))
end

-- Drop the claims whose ship has left or been destroyed; at the start of a
-- side's turn (side = that side), its ships still in place take their planets.
-- dying: the hex of a ship being destroyed (still on the map in "die").
function sc.check_planet_claims(side, dying)
	local keep = {}
	for _, a in ipairs(wml.array_access.get(CLAIMS)) do
		local u = wesnoth.units.get(a.x, a.y)
		local here = u and u.id == a.id and u.side == a.side
			and not (dying and dying.x == a.x and dying.y == a.y)
		if here and a.side == side then
			wesnoth.map.set_owner(a.x, a.y, a.side, false)
			claim_label(a.x, a.y, "")
		elseif here then
			keep[#keep + 1] = a
		else
			claim_label(a.x, a.y, "")
		end
	end
	wml.array_access.set(CLAIMS, keep)
	sc.update_planet_income()
end
