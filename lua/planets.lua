-- Star Control TC: the era's "Planets" option (the sc_planets variable),
-- which deals the planet types out afresh when a game starts.
-- Written against the Wesnoth 1.16 Lua API; loaded after sc.lua.
--
-- The deal follows the map's own symmetry, found the same way as
-- tools/assign_planet_types.py finds it: every mirror and rotation (in
-- steps of 60 degrees) that maps the planets onto each other. Planets that
-- match under them form a set, and every planet in a set gets the same
-- type, so each player (or, on a map where the players aren't all alike,
-- each team) gets the same mix. On a map that is only roughly symmetric it
-- follows the closest symmetry; on a map with three or six players it uses
-- the rotations only. The map keeps as near as it can to the mix of life,
-- mineral and dead worlds it was drawn with, so its income stays the same;
-- only where they are changes. Untyped planets (^Vyp, ^Vys) are left alone.

local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

local TYPES = { "l", "m", "d" }        -- life, mineral, dead
local TOL = 0.5                        -- in hexes: an exact match
local LOOSE = 3.0                      -- a map that is only roughly symmetric

-- Hex centre on a regular grid, 1 = distance between neighbours.
local function centre(x, y)
	return x * math.sqrt(3) / 2, y + (x % 2 == 0 and 0.5 or 0)
end

-- The symmetries of a hex grid about a point, other than the identity:
-- 5 rotations and 6 mirrors, each { name, a, b, c, d } (a 2x2 matrix).
local function transforms()
	local out = {}
	for k = 1, 5 do
		local a = k * math.pi / 3
		local c, s = math.cos(a), math.sin(a)
		out[#out + 1] = { rotation = k * 60, c, -s, s, c }
	end
	for k = 0, 5 do
		local a = k * math.pi / 3     -- mirror axis at k * 30 degrees
		local c, s = math.cos(a), math.sin(a)
		out[#out + 1] = { mirror = k * 30, c, s, s, -c }
	end
	return out
end

-- The transforms that map the planets onto themselves, each with where it
-- sends every planet (image[i] = j) and how far off its worst match is.
-- Planets are paired one to one, closest pairs first.
local function symmetries(pts, tol)
	local n = #pts
	local mx, my = 0, 0
	for _, p in ipairs(pts) do mx, my = mx + p[1] / n, my + p[2] / n end
	local found = {}
	for _, t in ipairs(transforms()) do
		local pairs_ = {}
		for i, p in ipairs(pts) do
			local dx, dy = p[1] - mx, p[2] - my
			local qx, qy = mx + t[1] * dx + t[2] * dy, my + t[3] * dx + t[4] * dy
			for j, r in ipairs(pts) do
				local dist = math.sqrt((r[1] - qx) ^ 2 + (r[2] - qy) ^ 2)
				if dist <= tol then pairs_[#pairs_ + 1] = { dist, i, j } end
			end
		end
		table.sort(pairs_, function(u, v)
			if u[1] ~= v[1] then return u[1] < v[1] end
			if u[2] ~= v[2] then return u[2] < v[2] end
			return u[3] < v[3]
		end)
		local image, used, matched, worst = {}, {}, 0, 0
		for _, pr in ipairs(pairs_) do
			local dist, i, j = pr[1], pr[2], pr[3]
			if not image[i] and not used[j] then
				image[i], used[j] = j, true
				matched, worst = matched + 1, math.max(worst, dist)
			end
		end
		if matched == n then
			found[#found + 1] = { t = t, image = image, worst = worst, mx = mx, my = my }
		end
	end
	return found
end

-- How many times the transform must be applied to come back round.
local function order(image)
	local n, k = #image, 1
	local seen = {}
	for i = 1, n do seen[i] = image[i] end
	local function home()
		for i = 1, n do if seen[i] ~= i then return false end end
		return true
	end
	while not home() and k < 12 do
		for i = 1, n do seen[i] = image[seen[i]] end
		k = k + 1
	end
	return k
end

-- Planets that must share a type, as lists of indices into pts.
local function planet_sets(pts, mirrored)
	local n = #pts
	local syms = {}
	if mirrored then
		syms = symmetries(pts, TOL)
		if #syms == 0 then
			-- roughly symmetric: the one symmetry that links the most
			-- planets, then the closest
			syms = symmetries(pts, LOOSE)
			table.sort(syms, function(u, v)
				local ou, ov = order(u.image), order(v.image)
				if ou ~= ov then return ou > ov end
				return u.worst < v.worst
			end)
			syms = { syms[1] }
		else
			local three = false
			for _, s in ipairs(syms) do three = three or s.t.rotation == 120 end
			if three then
				-- three or six players: the rotations alone give every
				-- player the same mix, and keep the sets small
				local rot = {}
				for _, s in ipairs(syms) do
					if s.t.rotation then rot[#rot + 1] = s end
				end
				syms = rot
			end
		end
	end
	local parent = {}
	for i = 1, n do parent[i] = i end
	local function find(i)
		while parent[i] ~= i do i = parent[i] end
		return i
	end
	for _, s in ipairs(syms) do
		for i, j in ipairs(s.image) do parent[find(i)] = find(j) end
	end
	local sets, by_root = {}, {}
	for i = 1, n do
		local r = find(i)
		if not by_root[r] then
			by_root[r] = {}
			sets[#sets + 1] = by_root[r]
		end
		table.insert(by_root[r], i)
	end
	return sets, syms
end

local function nearest(list, x, y)
	local best, bd = nil, nil
	for i, p in ipairs(list) do
		local d = (p[1] - x) ^ 2 + (p[2] - y) ^ 2
		if not bd or d < bd - 1e-6 then best, bd = i, d end
	end
	return best, bd
end

-- Starts the symmetries don't link (on Media Control, a corner and its
-- neighbour) still get the same mix: each planet belongs to the start
-- nearest it, and when every kind of start has the same number of sets of
-- each size, the sets are bundled, one of each kind of start in a bundle,
-- to be dealt the same type. Returns the bundles, or the sets as they were.
local function bundle_by_start(pts, sets, syms, starts)
	if #starts < 2 then return sets end
	local cs = {}
	for i, s in ipairs(starts) do cs[i] = { centre(s[1], s[2]) } end
	local parent = {}
	for i = 1, #cs do parent[i] = i end
	local function find(i)
		while parent[i] ~= i do i = parent[i] end
		return i
	end
	for _, sym in ipairs(syms) do
		local t = sym.t
		for i, p in ipairs(cs) do
			local dx, dy = p[1] - sym.mx, p[2] - sym.my
			local j = nearest(cs, sym.mx + t[1] * dx + t[2] * dy, sym.my + t[3] * dx + t[4] * dy)
			parent[find(i)] = find(j)
		end
	end
	-- each set's kind of start: that of the start nearest its first
	-- planet, unless another kind is as near, to within TOL (then it is
	-- shared, like the planet in the middle)
	local kinds, by_kind, shared = {}, {}, {}
	for _, s in ipairs(sets) do
		local p = pts[s[1]]
		local i, d = nearest(cs, p[1], p[2])
		local kind = find(i)
		for j, c in ipairs(cs) do
			if find(j) ~= kind and math.sqrt((c[1] - p[1]) ^ 2 + (c[2] - p[2]) ^ 2) - math.sqrt(d) < TOL then
				kind = nil
				break
			end
		end
		if kind then
			if not by_kind[kind] then
				by_kind[kind] = {}
				kinds[#kinds + 1] = kind
			end
			table.insert(by_kind[kind], s)
		else
			shared[#shared + 1] = s
		end
	end
	if #kinds < 2 then return sets end
	for _, k in ipairs(kinds) do
		local list = by_kind[k]
		for i = #list, 2, -1 do
			local j = mathx.random(i)
			list[i], list[j] = list[j], list[i]
		end
		-- by size, keeping the shuffled order among sets of one size
		for i = 2, #list do
			local s, j = list[i], i - 1
			while j >= 1 and #list[j] > #s do
				list[j + 1] = list[j]
				j = j - 1
			end
			list[j + 1] = s
		end
	end
	local first = by_kind[kinds[1]]
	for _, k in ipairs(kinds) do
		local list = by_kind[k]
		if #list ~= #first then return sets end
		for i, s in ipairs(list) do
			if #s ~= #first[i] then return sets end
		end
	end
	local out = shared
	for i = 1, #first do
		local b = {}
		for _, k in ipairs(kinds) do
			for _, p in ipairs(by_kind[k][i]) do b[#b + 1] = p end
		end
		out[#out + 1] = b
	end
	return out
end

-- The type counts the sets can make that come closest to the map's own.
local function best_mix(sizes, want, total)
	local reach = { ["0,0"] = { 0, 0 } }
	for _, n in ipairs(sizes) do
		local nxt = {}
		for _, lm in pairs(reach) do
			for _, d in ipairs { { n, 0 }, { 0, n }, { 0, 0 } } do
				local l, m = lm[1] + d[1], lm[2] + d[2]
				nxt[l .. "," .. m] = { l, m }
			end
		end
		reach = nxt
	end
	local best, ties = nil, {}
	local keys = {}
	for k in pairs(reach) do keys[#keys + 1] = k end
	table.sort(keys)                   -- the same on every client
	for _, k in ipairs(keys) do
		local l, m = reach[k][1], reach[k][2]
		local d = total - l - m
		local miss = (l - want.l) ^ 2 + (m - want.m) ^ 2 + (d - want.d) ^ 2
		if not best or miss < best - 1e-9 then
			best, ties = miss, { reach[k] }
		elseif miss - best < 1e-9 then
			ties[#ties + 1] = reach[k]
		end
	end
	local lm = ties[mathx.random(#ties)]
	return { l = lm[1], m = lm[2], d = total - lm[1] - lm[2] }
end

-- A new type for every planet: planets = { { x, y, type }, ... } with type
-- "l", "m" or "d"; mirrored = give matching planets the same type, and
-- the planets nearest each of starts = { { x, y }, ... } the same mix.
-- Returns the new types, in the same order.
function sc.deal_planet_types(planets, mirrored, starts)
	local pts, want = {}, { l = 0, m = 0, d = 0 }
	for i, p in ipairs(planets) do
		pts[i] = { centre(p[1], p[2]) }
		want[p[3]] = want[p[3]] + 1
	end
	local sets, syms = planet_sets(pts, mirrored)
	if mirrored then sets = bundle_by_start(pts, sets, syms, starts or {}) end
	-- deal to the sets in a random order
	for i = #sets, 2, -1 do
		local j = mathx.random(i)
		sets[i], sets[j] = sets[j], sets[i]
	end
	local sizes = {}
	for i, s in ipairs(sets) do sizes[i] = #s end
	local need = best_mix(sizes, want, #planets)

	-- can sets k.. fill exactly nl life and nm mineral (dead the rest)?
	local memo = {}
	local function fits(k, nl, nm)
		if k > #sizes then return nl == 0 and nm == 0 end
		local key = k .. "," .. nl .. "," .. nm
		if memo[key] == nil then
			local n, rest = sizes[k], 0
			for i = k, #sizes do rest = rest + sizes[i] end
			memo[key] = (nl >= n and fits(k + 1, nl - n, nm))
				or (nm >= n and fits(k + 1, nl, nm - n))
				or (rest - n >= nl + nm and fits(k + 1, nl, nm))
		end
		return memo[key]
	end

	local out = {}
	for k, s in ipairs(sets) do
		-- any type that still lets the other sets come out right, the more
		-- of it still to deal the likelier
		local n, options, weight = #s, {}, 0
		for _, t in ipairs(TYPES) do
			if need[t] >= n then
				local l = need.l - (t == "l" and n or 0)
				local m = need.m - (t == "m" and n or 0)
				if fits(k + 1, l, m) then
					options[#options + 1] = t
					weight = weight + need[t]
				end
			end
		end
		local roll, t = mathx.random(weight), options[#options]
		for _, o in ipairs(options) do
			roll = roll - need[o]
			if roll <= 0 then t = o; break end
		end
		need[t] = need[t] - n
		for _, i in ipairs(s) do out[i] = t end
	end
	return out
end

-- Deal the planet types afresh, if the era's "Planets" option says so
-- (prestart, before the planet income is set up).
function sc.randomize_planets()
	local mode = wml.variables["sc_planets"]
	if mode ~= "mirrored" and mode ~= "random" then return end
	local planets, sea = {}, {}
	for _, loc in ipairs(wesnoth.map.find { terrain = "*^Vy*" }) do
		local overlay = wesnoth.current.map[loc]:match("%^(.+)$")
		local s, t = overlay:match("^Vy(s?)([lmd])$")
		if t then
			planets[#planets + 1] = { loc[1], loc[2], t }
			sea[#planets] = s
		end
	end
	if #planets == 0 then return end
	local starts = {}
	for _, side in ipairs(wesnoth.sides) do
		starts[#starts + 1] = side.starting_location   -- nothing if it has none
	end
	local types = sc.deal_planet_types(planets, mode == "mirrored", starts)
	for i, p in ipairs(planets) do
		wesnoth.wml_actions.terrain {
			x = p[1], y = p[2], layer = "overlay",
			terrain = "^Vy" .. sea[i] .. types[i],
		}
	end
end
