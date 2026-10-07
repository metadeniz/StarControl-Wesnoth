-- Star Control TC: the right-click ship devices, fighter docking, and the
-- small amount of help the AI needs to use those devices.
-- Written against the Wesnoth 1.16 Lua API.

local T = wml.tag
local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc = {}

local GLORY_DAMAGE = { 24, 30, 36 }      -- by the Scout's level
local FIGHTER_CREW = 4                   -- HP a Dreadnought spends per fighter
local FIGHTERS_PER_LAUNCH = { 2, 3, 3 }  -- by the Dreadnought's level
local AI_MAX_FIGHTERS = 4      -- the AI stops launching at this many per side

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

function wesnoth.wml_actions.sc_glory_device(cfg)
	local u = wesnoth.units.get(cfg.x, cfg.y)
	if not is_a(u, "SC_Shofixti_Scout") then return end
	local damage = by_level(GLORY_DAMAGE, u)
	local x, y = u.x, u.y
	count("glory")

	wesnoth.wml_actions.animate_unit { flag = "glory", T.filter { x = x, y = y } }
	wesnoth.wml_actions.kill { x = x, y = y, animate = false, fire_event = true }
	wesnoth.wml_actions.harm_unit {
		T.filter { T.filter_location { x = x, y = y, radius = 1 } },
		amount = damage,
		damage_type = "fire",
		animate = true,
		fire_event = true,
	}
end

---------------------------------------------------------------- Ur-Quan fighters

function wesnoth.wml_actions.sc_launch_fighters(cfg)
	local u = wesnoth.units.get(cfg.x, cfg.y)
	if not is_a(u, "SC_UrQuan_Dreadnought") or u.attacks_left < 1 then return end

	local spots = free_neighbours(u.x, u.y)
	local n = math.min(by_level(FIGHTERS_PER_LAUNCH, u), #spots, math.floor((u.hitpoints - 1) / FIGHTER_CREW))
	if n < 1 then
		wesnoth.interface.add_chat_message(_ "No room to launch fighters.")
		return
	end
	count("launch")

	wesnoth.audio.play("sc/urquan-launch.wav")
	for i = 1, n do
		local f = wesnoth.units.create {
			type = "SC_UrQuan_Fighter",
			side = u.side,
			name = "",
			random_traits = false,
			T.variables { launched_turn = wesnoth.current.turn },
		}
		f:to_map(spots[i][1], spots[i][2])
	end
	u.hitpoints = u.hitpoints - n * FIGHTER_CREW
	u.attacks_left = 0
end

-- Fighters that end a later turn next to a friendly Dreadnought fly home.
local function dock_fighters(side)
	local turn = wesnoth.current.turn
	for _, f in ipairs(wesnoth.units.find_on_map { type = "SC_UrQuan_Fighter", side = side }) do
		if (f.variables.launched_turn or 0) < turn then
			local carrier = wesnoth.units.find_on_map {
				type = all_levels("SC_UrQuan_Dreadnought"), side = side,
				T.filter_adjacent { x = f.x, y = f.y },
			}[1]
			if carrier then
				carrier.hitpoints = math.min(carrier.max_hitpoints, carrier.hitpoints + FIGHTER_CREW)
				wesnoth.audio.play("sc/urquan-fighter-dock.wav")
				f:erase()
				count("dock")
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
	u.hitpoints = hp
	u.moves = 0
	u.attacks_left = 0
end

---------------------------------------------------------------------- AI help

-- Start of an AI side's turn (units already refreshed): launch fighters
-- when there is something to fight.
function sc.ai_turn_start()
	local side = wesnoth.current.side
	if not is_ai(side) then return end
	local fighters = #wesnoth.units.find_on_map { type = "SC_UrQuan_Fighter", side = side }
	for _, d in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_UrQuan_Dreadnought"), side = side }) do
		if fighters >= AI_MAX_FIGHTERS then break end
		if d.attacks_left > 0 and d.hitpoints >= 30 then
			local enemies = wesnoth.units.find_on_map {
				T.filter_side { T.enemy_of { side = side } },
				T.filter_location { x = d.x, y = d.y, radius = 5 },
			}
			if #enemies > 0 then
				wesnoth.wml_actions.sc_launch_fighters { x = d.x, y = d.y }
				fighters = #wesnoth.units.find_on_map { type = "SC_UrQuan_Fighter", side = side }
			end
		end
	end
end

-- End of an AI side's turn: a Shofixti next to two enemies, or next to one
-- big one, triggers its Glory Device.
local function ai_glory(side)
	for _, s in ipairs(wesnoth.units.find_on_map { type = all_levels("SC_Shofixti_Scout"), side = side }) do
		local enemies = wesnoth.units.find_on_map {
			T.filter_side { T.enemy_of { side = side } },
			T.filter_adjacent { x = s.x, y = s.y },
		}
		local friends = wesnoth.units.find_on_map {
			side = side,
			T.filter_adjacent { x = s.x, y = s.y },
		}
		local worth = 0
		for _, e in ipairs(enemies) do worth = worth + e.cost end
		for _, f in ipairs(friends) do worth = worth - f.cost end
		if #enemies >= 2 or worth >= 20 then
			wesnoth.wml_actions.sc_glory_device { x = s.x, y = s.y }
		end
	end
end

function sc.turn_end()
	local side = wesnoth.current.side
	dock_fighters(side)
	if is_ai(side) then ai_glory(side) end
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
	std_print(string.format("SC_RESULT turn=%d %s glory=%d launch=%d dock=%d transform=%d to_L2=%d to_L3=%d recruits: %s",
		wesnoth.current.turn, table.concat(parts, " "),
		stats.glory or 0, stats.launch or 0, stats.dock or 0, stats.transform or 0,
		stats.level2 or 0, stats.level3 or 0,
		table.concat(recruits, " ")))
end
