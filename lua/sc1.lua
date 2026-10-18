-- Star Control TC: Star Control 1's built-in missions (scenarios/sc1.cfg).
-- Written against the Wesnoth 1.16 Lua API; loaded after sc.lua.
--
-- Star Control 1 drew a fresh star cluster for every game. So does this: at
-- prestart, before the era's planet income and Precursor artifacts are set
-- up, sc1.setup() picks one of the clusters in lua/sc1_clusters.lua
-- (made by tools/make_sc1_clusters.py), mirrored left to right or not, and
-- lays it over the map: planets joined by lanes of open space through
-- impassable dark nebula, the Hierarchy's starbase at the north end (side
-- 1) and the Alliance's at the south (side 2). Then it deals the mission's
-- holdings and planet types and puts the starting ships next to their
-- starbases, all with the synced random numbers, so every player sees the
-- same cluster.

local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc1 = {}

-- Each side's start, from Star Control 1's SCENARIO files (see the decode
-- in the project's sc1-scenarios notes): ships, starting colonies and
-- mines, and the free worlds in its half of the cluster.
--   ships     unit types, placed on the docking rings and round the starbase
--   colonies  life worlds it owns; mines: mineral worlds it owns (both the
--             planets nearest its starbase, in random order)
--   worlds    { dead, mineral, life }: the types dealt out to the other
--             planets in its half
sc1.missions = {
	first_encounter = {
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

local FILL = "Yqd"         -- dark nebula: impassable
local OPEN = "Ys"
local ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

local function decode(s, mirror_w)
	local out = {}
	for i = 1, #s, 2 do
		local x = ALPHABET:find(s:sub(i, i), 1, true) - 1
		local y = ALPHABET:find(s:sub(i + 1, i + 1), 1, true) - 1
		if mirror_w then x = mirror_w + 1 - x end
		out[#out + 1] = { x, y }
	end
	return out
end

local function key(p) return p[1] .. "," .. p[2] end

-- The six hexes round x,y (even columns sit half a hex lower).
local function adjacent(x, y)
	local d = x % 2 == 0 and 0 or -1
	return { { x, y - 1 }, { x, y + 1 }, { x - 1, y + d }, { x - 1, y + d + 1 },
		{ x + 1, y + d }, { x + 1, y + d + 1 } }
end

local function shuffle(list)
	for i = #list, 2, -1 do
		local j = mathx.random(i)
		list[i], list[j] = list[j], list[i]
	end
	return list
end

-- The open hexes nearest a starbase, docking rings first, then outward
-- along the open hexes, skipping planets and the starbase itself.
local function berths(keep, rings, open, planet)
	local out, seen = {}, { [key(keep)] = true }
	local queue = {}
	for _, r in ipairs(rings) do
		seen[key(r)] = true
		out[#out + 1] = r
		queue[#queue + 1] = r
	end
	queue[#queue + 1] = keep
	local i = 1
	while i <= #queue do
		local x, y = queue[i][1], queue[i][2]
		i = i + 1
		for _, n in ipairs(adjacent(x, y)) do
			local k = key(n)
			if open[k] and not seen[k] then
				seen[k] = true
				queue[#queue + 1] = n
				if not planet[k] then out[#out + 1] = n end
			end
		end
	end
	return out
end

function sc1.setup(mission_id)
	local mission = sc1.missions[mission_id]
	local data = wesnoth.dofile("~add-ons/Star_Control_TC/lua/sc1_clusters.lua")
	local w, h = data.width, data.height
	local c = data.clusters[mathx.random(#data.clusters)]
	local mw = mathx.random(2) == 2 and w or nil   -- mirrored left to right

	local grid = {}
	for y = 0, h + 1 do
		grid[y] = {}
		for x = 0, w + 1 do grid[y][x] = FILL end
	end
	local open = {}
	for _, p in ipairs(decode(c.open, mw)) do
		grid[p[2]][p[1]] = OPEN
		open[key(p)] = true
	end

	local planet, top = {}, {}
	local planets = decode(c.planets, mw)
	for _, p in ipairs(planets) do planet[key(p)] = true end
	for _, p in ipairs(decode(c.top, mw)) do top[key(p)] = true end

	-- holdings, nearest each starbase first; then the other planets of
	-- each half get that side's mix of free worlds
	local owned, ends = {}, {}
	for side, e in ipairs { "h", "a" } do
		local m = mission[side]
		local holdings = {}
		for _ = 1, m.colonies or 0 do holdings[#holdings + 1] = "l" end
		for _ = 1, m.mines or 0 do holdings[#holdings + 1] = "m" end
		shuffle(holdings)
		local n = 0
		for _, p in ipairs(decode(c["home_" .. e], mw)) do
			if n >= #holdings then break end
			if not owned[key(p)] then
				n = n + 1
				owned[key(p)] = { side = side, type = holdings[n], loc = p }
			end
		end
		ends[side] = {
			keep = decode(c["keep_" .. e], mw)[1],
			rings = decode(c["rings_" .. e], mw),
		}
	end
	for side = 1, 2 do
		local free = {}
		for _, p in ipairs(planets) do
			if (top[key(p)] == true) == (side == 1) and not owned[key(p)] then free[#free + 1] = p end
		end
		local counts, types = mission[side].worlds, {}
		for t, n in ipairs(counts) do
			for _ = 1, n do types[#types + 1] = ({ "d", "m", "l" })[t] end
		end
		-- more planets than the mission names: deal the mix again
		local base = #types
		while #types < #free and base > 0 do types[#types + 1] = types[#types - base + 1] end
		shuffle(types)
		for i, p in ipairs(free) do
			grid[p[2]][p[1]] = OPEN .. "^Vy" .. (types[i] or "d")
		end
	end
	for _, o in pairs(owned) do
		grid[o.loc[2]][o.loc[1]] = OPEN .. "^Vy" .. o.type
	end
	for side = 1, 2 do
		local k = ends[side].keep
		grid[k[2]][k[1]] = side .. " Yk"
		for _, r in ipairs(ends[side].rings) do grid[r[2]][r[1]] = "Yc" end
	end

	local rows = {}
	for y = 0, h + 1 do rows[#rows + 1] = table.concat(grid[y], ", ", 0, w + 1) end
	wesnoth.wml_actions.replace_map { map = table.concat(rows, "\n"), expand = true, shrink = true }

	for _, o in pairs(owned) do
		wesnoth.map.set_owner(o.loc[1], o.loc[2], o.side, false)
	end
	for side = 1, 2 do
		local e = ends[side]
		local facing = side == 1 and "s" or "n"
		for _, u in ipairs(wesnoth.units.find_on_map { side = side, canrecruit = true }) do
			u:to_map(e.keep[1], e.keep[2])
			u.facing = facing
		end
		local spots = berths(e.keep, e.rings, open, planet)
		for i, t in ipairs(mission[side].ships) do
			local p = spots[i]
			if p then
				wesnoth.wml_actions.unit {
					type = t, side = side, x = p[1], y = p[2],
					facing = facing, animate = false,
				}
			end
		end
	end
end
