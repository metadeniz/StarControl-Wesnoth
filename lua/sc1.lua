-- Star Control TC: Star Control 1's built-in missions (scenarios/scenarios_sc1.cfg).
-- Written against the Wesnoth 1.16 Lua API; loaded after sc.lua.
--
-- Star Control 1 drew a fresh star cluster for every game. Here each
-- mission has a few maps (made by tools/make_sc1_maps.py, and fine to edit
-- by hand), and at prestart, before the era's planet income and Precursor
-- artifacts are set up, sc1.setup() picks one of them, then deals the
-- mission's holdings and planet types and puts the starting ships by their
-- starbases, all with the synced random numbers, so every player sees the
-- same game. On every map the Hierarchy (side 1) starts at the starbase
-- furthest north and the Alliance (side 2) at the one furthest south.

local T = wml.tag
local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc1 = {}

-- Each mission: its maps (in maps/), and each side's start from Star
-- Control 1's SCENARIO files:
--   ships     unit types, placed on the docking rings round its starbase
--   colonies  life worlds it owns; mines: mineral worlds it owns (the
--             planets nearest its starbase, in random order)
--   worlds    { dead, mineral, life }: the types dealt out to the other
--             planets in its half of the map (the half nearer its starbase)
sc1.missions = {
	first_encounter = {
		maps = {
			"2p_SC1_First_Encounter_1", "2p_SC1_First_Encounter_2",
			"2p_SC1_First_Encounter_3", "2p_SC1_First_Encounter_4",
		},
		{   -- side 1, the Hierarchy
			ships = { "SC_Spathi_Eluder", "SC_Androsynth_Guardian", "SC_Ilwrath_Avenger" },
			colonies = 1, mines = 1,
			worlds = { 0, 6, 6 },
		},
		{   -- side 2, the Alliance
			ships = { "SC_Mmrnmhrm_XForm", "SC_Arilou_Skiff", "SC_Earthling_Cruiser" },
			colonies = 1, mines = 1,
			worlds = { 0, 6, 6 },
		},
	},
}

-- Hexes apart (even columns sit half a hex lower).
local function distance(a, b)
	local function cube(p)
		local q = p[1] - 1
		local r = p[2] - (q - q % 2) / 2
		return q, r, -q - r
	end
	local ax, az, ay = cube(a)
	local bx, bz, by = cube(b)
	return math.max(math.abs(ax - bx), math.abs(ay - by), math.abs(az - bz))
end

local function shuffle(list)
	for i = #list, 2, -1 do
		local j = mathx.random(i)
		list[i], list[j] = list[j], list[i]
	end
	return list
end

local function by_distance(list, from)
	table.sort(list, function(a, b)
		local da, db = distance(a, from), distance(b, from)
		if da ~= db then return da < db end
		if a[2] ~= b[2] then return a[2] < b[2] end
		return a[1] < b[1]
	end)
	return list
end

function sc1.setup(mission_id)
	local mission = sc1.missions[mission_id]
	local name = mission.maps[mathx.random(#mission.maps)]
	local data = filesystem.read_file("~add-ons/Star_Control_TC/maps/" .. name .. ".map")
	wesnoth.wml_actions.replace_map { map = data, expand = true, shrink = true }

	-- the starbases: north for the Hierarchy, south for the Alliance
	local keeps = wesnoth.map.find { terrain = "Yk" }
	table.sort(keeps, function(a, b) return a[2] < b[2] end)
	local home = { keeps[1], keeps[#keeps] }

	-- each side's half: the half of the planets nearer its starbase than
	-- the enemy's (by how much nearer, so the halves come out even)
	local planets = wesnoth.map.find { terrain = "*^Vy*" }
	local function lean(p) return distance(p, home[1]) - distance(p, home[2]) end
	table.sort(planets, function(a, b)
		local la, lb = lean(a), lean(b)
		if la ~= lb then return la < lb end
		if a[2] ~= b[2] then return a[2] < b[2] end
		return a[1] < b[1]
	end)
	local halves = { {}, {} }
	for i, p in ipairs(planets) do
		table.insert(halves[i <= #planets / 2 and 1 or 2], { p[1], p[2] })
	end

	local deal = {}
	for side = 1, 2 do
		local m = mission[side]
		local planets = by_distance(halves[side], home[side])
		local holdings = {}
		for _ = 1, m.colonies or 0 do holdings[#holdings + 1] = "l" end
		for _ = 1, m.mines or 0 do holdings[#holdings + 1] = "m" end
		shuffle(holdings)
		local types = {}
		for t, n in ipairs(m.worlds) do
			for _ = 1, n do types[#types + 1] = ({ "d", "m", "l" })[t] end
		end
		-- more planets than the mission names: deal the mix again
		local count = #types
		while #types < #planets - #holdings and count > 0 do
			types[#types + 1] = types[#types - count + 1]
		end
		shuffle(types)
		for i, p in ipairs(planets) do
			local owned = i <= #holdings
			deal[#deal + 1] = {
				loc = p, side = owned and side or nil,
				type = owned and holdings[i] or types[i - #holdings] or "d",
			}
		end
	end
	for _, d in ipairs(deal) do
		wesnoth.wml_actions.terrain {
			x = d.loc[1], y = d.loc[2], layer = "overlay", terrain = "^Vy" .. d.type,
		}
		wesnoth.map.set_owner(d.loc[1], d.loc[2], d.side or 0, false)
	end

	for side = 1, 2 do
		local k = home[side]
		local facing = side == 1 and "s" or "n"
		for _, u in ipairs(wesnoth.units.find_on_map { side = side, canrecruit = true }) do
			u:to_map(k[1], k[2])
			u.facing = facing
		end
		-- the docking rings round the starbase, nearest the middle first;
		-- ships beyond those go to the nearest free hex
		local rings = wesnoth.map.find { terrain = "Yc", T.filter_adjacent_location { x = k[1], y = k[2] } }
		by_distance(rings, home[3 - side])
		for i, t in ipairs(mission[side].ships) do
			local p = rings[i] or k
			wesnoth.wml_actions.unit {
				type = t, side = side, x = p[1], y = p[2],
				facing = facing, animate = false,
			}
		end
	end
end
