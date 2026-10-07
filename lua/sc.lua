-- Star Control TC: the right-click ship devices (Glory Device, Mmrnmhrm
-- Transform), and the small amount of help the AI needs to use them.
-- Written against the Wesnoth 1.16 Lua API.

local T = wml.tag
local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc = {}


local function count(name)
	wml.variables["sc_stats." .. name] = (wml.variables["sc_stats." .. name] or 0) + 1
end

-- Every ship comes in levels 1-3: SC_X, SC_X_L2, SC_X_L3.
local function base_type(t) return (t:gsub("_L[23]$", "")) end
local function is_a(u, base) return u and base_type(u.type) == base end
local function all_levels(base) return base .. "," .. base .. "_L2," .. base .. "_L3" end
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

-- Leaders don't carry a Glory Device: blowing one up would lose the game.
function sc.disarm_leaders()
	for _, u in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout"), canrecruit = true }) do
		u:add_modification("object", { T.effect { apply_to = "remove_attacks", name = "glory_device" } })
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
-- Device on a neighbour it would destroy, or on one worth twice its cost.
-- (The weapon has attack_weight=0, so the AI never picks it by itself.)
local function ai_glory(side)
	for _, s in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout"), side = side, canrecruit = false }) do
		local weapon
		for i, a in ipairs(s.attacks) do if a.name == "glory_device" then weapon = i - 1 end end
		if weapon and s.attacks_left > 0 then
			local best, best_worth
			for _, e in ipairs(wesnoth.units.find_on_map {
				T.filter_side { T.enemy_of { side = side } },
				T.filter_adjacent { x = s.x, y = s.y },
			}) do
				local damage = s.attacks[weapon + 1].damage * e:resistance_against("fire") / 100
				local worth = (e.hitpoints <= damage) and e.cost * 2 or e.cost
				if (e.hitpoints <= damage or e.cost >= 2 * s.cost) and (not best or worth > best_worth) then
					best, best_worth = e, worth
				end
			end
			if best then
				wesnoth.wml_actions.do_command { T.attack {
					weapon = weapon,
					T.source { x = s.x, y = s.y },
					T.destination { x = best.x, y = best.y },
				} }
			end
		end
	end
end

function sc.turn_end()
	local side = wesnoth.current.side
	if is_ai(side) then ai_glory(side) end
end

---------------------------------------------------------------- victory ditties

-- When a ship destroys another, its race's Star Control victory ditty plays.
function sc.victory_ditty()
	local killer = wesnoth.units.get(wml.variables["x2"], wml.variables["y2"])
	if not killer then return end
	local race = tostring(killer.race):match("^sc_(.+)$")
	if race then wesnoth.audio.play("sc/ditty-" .. race .. ".ogg") end
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
		terrain = "*^Vyp",
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
	wesnoth.interface.add_chat_message(tostring(_ "Precursor artifact"),
		tostring(u.name) .. ": " .. tostring(a.description))

	u.experience = u.experience + ARTIFACT_XP
	if u.experience >= u.max_experience then u:advance(true, true) end
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
		local units = wesnoth.units.find_on_map { side = s.side }
		local leader = #wesnoth.units.find_on_map { side = s.side, canrecruit = true } > 0
		local faction = s.__cfg.faction or "?"
		parts[#parts + 1] = string.format("side%d=%s units=%d leader=%s gold=%d",
			s.side, faction, #units, tostring(leader), s.gold)
	end
	local stats = wml.variables["sc_stats"] or {}
	local recruits = {}
	for k, v in pairs(stats) do
		if k:match("^recruit_") then recruits[#recruits + 1] = k:gsub("^recruit_", "") .. "=" .. v end
	end
	table.sort(recruits)
	std_print(string.format("SC_RESULT turn=%d %s glory=%d transform=%d artifacts=%d to_L2=%d to_L3=%d recruits: %s",
		wesnoth.current.turn, table.concat(parts, " "),
		stats.glory or 0, stats.transform or 0, stats.artifacts or 0,
		stats.level2 or 0, stats.level3 or 0,
		table.concat(recruits, " ")))
end
