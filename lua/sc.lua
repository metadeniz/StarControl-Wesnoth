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
local PLAYLISTS = {
	SC_Alliance = { "commander", "chenjesu-titus", "mmrnmhrm-titus", "yehat", "syreen", "arilou", "shofixti", "quasispace", "quasispace-3do",
		"intro", "victory", "starbase", "outfit" },
	-- the New Alliance hears the Precursors' remixes (and one cover)
	SC_NewAlliance = { "remix-chmmr", "remix-zoqfotpik", "remix-pkunk", "remix-supox", "remix-utwig",
		"remix-utwig-ultron", "remix-commander", "remix-arilou", "remix-melnorme", "remix-syreen", "syreen-ramen-rider",
		"remix-mystic-shadows", "remix-quasispace", "remix-intro", "remix-ending", "remix-starbase",
		"remix-outfit" },
	-- the Agents of Chaos hear modern versions: the Precursors' remixes and a
	-- re-imagined Melnorme theme
	SC_DeathMarch = { "kohrah-cleansing-required", "kohrah-eternal-doctrine", "kohrah-battle",
		"druuge-crimson-corporation", "thraddash-culture-19", "slylandro-we-come-in-peace",
		"orz-squeezing-the-juice", "mycon-rebirth", "ilwrath-all-evil", "samatra-battle", "melnorme-lipavsky",
		"remix-starbase" },
	SC_Hierarchy = { "urquan", "urquan-now-and-forever", "mycon", "spathi", "umgah", "vux", "ilwrath", "thraddash",
		"androsynth-duoled", "starbase" },
}

-- Theme played when you win. It is a sound effect, not music, so it follows
-- the sound volume like the victory ditties; the music stops for it (the
-- engine "plays" a silent victory track).
local VICTORY_THEME = {
	SC_Alliance = "sc/alliance-victory.ogg",     -- Star Control 1's Alliance victory theme
	SC_Hierarchy = "sc/hierarchy-victory.ogg",   -- Star Control 1's Hierarchy victory theme
	SC_NewAlliance = "sc/victory-fanfare.ogg",   -- Star Control II's victory fanfare
	SC_DeathMarch = "sc/kohrah-victory.ogg",     -- for now: the Precursors' Kohr-Ah ditty remix
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

function sc.set_music()
	local side = local_human_side()
	local list = side and PLAYLISTS[side.__cfg.faction]
	if list then
		for i, track in ipairs(list) do
			wesnoth.wml_actions.music {
				name = "sc/" .. track .. ".ogg",
				append = i > 1,
				immediate = i == 1,
				shuffle = true,
			}
		end
	end
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
-- remove it.
local REBIRTH_CHANCE = 80
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
	local reborn = wesnoth.units.create(cfg)
	reborn.status.poisoned = false   -- reborn clean
	reborn.status.slowed = false
	reborn:to_map(x, y)
	wesnoth.audio.play("sc/pkunk-rebirth.wav")
	wesnoth.interface.float_label(x, y, "<span color='#ffe680'>" .. tostring(_ "Reborn!") .. "</span>")
end

------------------------------------------------------------ Precursor artifacts

-- Hidden on about one planet in five (never next to a starbase). The first
-- ship to enter that planet finds it: a random permanent bonus, shown as a
-- trait, plus some experience. On mirrored maps they come in mirror pairs.
local ARTIFACT_XP = 8
local ARTIFACTS = {
	{ id = "drive",    name = _ "+drive",
	  description = _ "Precursor artifact: a drive unit. +1 movement.",
	  effect = { apply_to = "movement", increase = 1 } },
	{ id = "crew",     name = _ "+crew",
	  description = _ "Precursor artifact: life-support pods, room for more crew. +6 max HP.",
	  effect = { apply_to = "hitpoints", increase_total = 6, increase = 6 } },
	{ id = "battery",  name = _ "+battery",
	  description = _ "Precursor artifact: a bigger energy battery. +1 strike on every attack.",
	  effect = { apply_to = "attack", increase_attacks = 1 } },
	{ id = "recharge", name = _ "+recharge",
	  description = _ "Precursor artifact: a battery recharger. +1 damage on every attack.",
	  effect = { apply_to = "attack", increase_damage = 1 } },
}

local function artifact_key(x, y) return "sc_artifact_" .. x .. "_" .. y end

function sc.place_artifacts()
	local map = wesnoth.current.map
	local planets = wesnoth.map.find {
		terrain = "*^Vyp,*^Vys",
		T["not"] { T.filter_adjacent_location { terrain = "Yk,Yc" } },
		T["not"] { terrain = "Yk,Yc" },
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
	u:add_modification("trait", {
		id = "sc_artifact_" .. a.id .. "_" .. n,
		male_name = a.name, female_name = a.name,
		description = a.description,
		T.effect(a.effect),
	})
	wesnoth.audio.play("sc/artifact.wav")
	wesnoth.interface.float_label(x, y, "<span color='#ffd84a'>" .. tostring(_ "Precursor artifact!") .. "</span>\n" .. tostring(a.description))
	-- The floating text fades within a second or two, so a label naming the
	-- find stays on the planet until the finder's next turn starts.
	wesnoth.map.add_label { x = x, y = y, color = "255,216,74", immutable = true,
		text = tostring(_ "Precursor artifact: ") .. tostring(a.name) }
	local labels = wml.array_access.get("sc_artifact_labels")
	labels[#labels + 1] = { x = x, y = y, side = u.side }
	wml.array_access.set("sc_artifact_labels", labels)

	u.experience = u.experience + ARTIFACT_XP
	if u.experience >= u.max_experience then u:advance(true, true) end
end

-- Start of a side's turn: clear the artifact labels it put up last turn.
function sc.expire_artifact_labels()
	local keep = {}
	for _, l in ipairs(wml.array_access.get("sc_artifact_labels")) do
		if l.side == wesnoth.current.side then
			wesnoth.map.add_label { x = l.x, y = l.y, text = "" }
		else
			keep[#keep + 1] = l
		end
	end
	wml.array_access.set("sc_artifact_labels", keep)
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
