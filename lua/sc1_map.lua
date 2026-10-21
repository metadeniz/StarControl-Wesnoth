-- Star Control TC: a fresh Star Control 1 star cluster, as a Wesnoth map.
-- Used by lua/sc1.lua at the start of every SC1 mission game, and by
-- tools/sc1_map_preview.lua to draw sample maps outside the game.
--
-- The cluster is the one Star Control 1 itself builds from a seed: its
-- generator from STARCON.EXE (0628:216C) with the Microsoft C rand() it
-- calls (214F:0112), as ported by the starcon1-map-prototype project
-- (src/generation/sc1Cluster.ts). Stars are points in a cylinder: x runs
-- along it (the Hierarchy's half 10-94, the Alliance's 96-180, the first
-- star at 95), y and z lie in a disc of radius 118. Stars are placed one at
-- a time, the sides taking turns, and two stars are linked exactly when
-- they are closer than 38; none are closer than 20, no pair is 38-60 apart
-- and no star has more than 4 links. It is laid flat as the prototype's
-- flatLayout.ts does it: links keep SC1's 20-38 lengths, every star stays in
-- its own half and roughly as near the middle as SC1 put it, and the first
-- star sits in the exact middle.
--
-- Then it is put on hexes:
--   - lanes of open space about 4 hexes across along every link, and open
--     space round every planet;
--   - rough terrain outside the lanes: patches of nebula, light badlands,
--     dust and asteroid fields, with open gaps through them, small red
--     nebulae on the edges of the green, a debris disk (3 hexes) in every
--     big asteroid field and a few lone stars, black holes, pulsars and
--     brown dwarfs well away from the lanes;
--   - cover in the lanes: small patches (1-4 hexes) of nebula, dust, light
--     badlands, asteroids or red nebula, clear of planets and starbases;
--   - the Hierarchy's starbase (start 1) just beyond the star of its half
--     farthest from the centre, where SC1 puts it, the Alliance's (start 2)
--     likewise at the south end, each with 3 docking rings, and two forward
--     starbases, one each side of the middle, each with 3;
--   - between the forward starbases, a third of the band made impassable
--     dark nebula, furthest from the lanes first, to narrow the waist;
--   - the map cropped to 2 hexes beyond the outermost planet, starbase or
--     docking ring on every side.
--
-- Every player builds the map for themselves, so it must come out the same
-- everywhere: all the randomness comes from the random function passed in
-- (the synced one in a game), only + - * / and sqrt decide anything (they
-- round the same on every machine; exp, sin and cos need not), and nothing
-- depends on the order pairs() visits a table.

local M = {}

-- ---- Star Control 1's cluster ---------------------------------------------

local MIN_DIST = 20      -- closer than this to any star: position rejected
local LINK_MAX = 38      -- at least MIN_DIST and closer than this: linked
local GAP_MAX = 60       -- at least LINK_MAX and closer than this: rejected
local WINDOW = 40        -- only stars within this on every axis are checked
local MAX_NEW_LINKS = 3  -- a new star links to at most this many...
local MAX_LINKS = 4      -- ...and no star ever has more than this many
local RADIUS = 118
M.CENTRE = 95            -- x of the first star, where the halves meet
M.FRONT = 47             -- stars nearer the centre (in x) are a side's front

-- Microsoft C runtime rand(): a 32-bit LCG returning bits 16-30
local function msc_rand(seed)
	local state = seed & 0xFFFF   -- srand() keeps a 16-bit seed
	return function()
		state = (state * 214013 + 2531011) & 0xFFFFFFFF
		return (state >> 16) & 0x7FFF
	end
end

-- SC1's cluster: count_a stars on the high-x half (side "A", the
-- Alliance's), count_b on the low-x half ("B", the Hierarchy's). The sides
-- take turns placing (even placements go to A) until one runs out. Returns
-- the stars in placement order, star 1 the central one, each
-- { index, x, y, z, side, links = { stars } }.
function M.cluster(seed, count_a, count_b)
	local rand = msc_rand(seed)
	local total = count_a + count_b
	local list = {}   -- kept sorted by x, as the original scans it
	local stars = {}
	for i = 0, total - 1 do
		local first = i == 0
		local x, y, z, cand, insert_at
		while true do
			if first then
				x, y, z = M.CENTRE, 10, rand() % 20
				first = false
			else
				x = rand() % 85 + 10
				if count_a ~= 0 and (i & 1 == 0 or count_b == 0) then x = x + 86 end
				repeat
					y = rand() % 236 - 118
					z = rand() % 236 - 118
				until not ((y == 0 and z == 0) or y * y + z * z > RADIUS * RADIUS)
			end
			cand, insert_at = {}, nil
			local ok = true
			for k, s in ipairs(list) do
				local dx = s.x - x
				if dx >= -WINDOW then
					if dx == 0 then ok = false; break end   -- no two stars share an x
					if dx > 0 then
						insert_at = insert_at or k
						if dx > WINDOW then break end
					end
					if math.abs(s.y - y) <= WINDOW and math.abs(s.z - z) <= WINDOW then
						local d2 = dx * dx + (s.y - y) ^ 2 + (s.z - z) ^ 2
						if d2 < MIN_DIST * MIN_DIST then ok = false; break end
						if d2 < LINK_MAX * LINK_MAX then
							if #cand == MAX_NEW_LINKS or #s.links == MAX_LINKS then ok = false; break end
							cand[#cand + 1] = s
						elseif d2 < GAP_MAX * GAP_MAX then
							ok = false   -- near miss
							break
						end
					end
				end
			end
			-- every star after the first must link to the cluster, and
			-- stars 3 and 4 to two of it
			if ok and (i == 0 or (#cand > 0 and not (i <= 4 and #cand < (i + 1) >> 1))) then break end
		end
		local side
		if count_b ~= 0 and (i & 1 ~= 0 or count_a == 0) then
			count_b, side = count_b - 1, "B"
		else
			count_a, side = count_a - 1, "A"
		end
		local star = { index = i + 1, x = x, y = y, z = z, side = side, links = {} }
		for _, c in ipairs(cand) do
			star.links[#star.links + 1] = c
			c.links[#c.links + 1] = star
		end
		table.insert(list, insert_at or #list + 1, star)
		stars[i + 1] = star
	end
	return stars
end

-- ---- laid flat (the prototype's flatLayout.ts) ----------------------------

local ANGLES = 36          -- views round the long axis tried as starting points
local TRIES = 4            -- best starting views relaxed in full
local SIDE_GAP = 6         -- stars stay this far from the centre line, on their side
local APART = 32           -- stars that aren't linked stay this far apart
local LINK_CLEARANCE = 14  -- and this far from a link they aren't part of
local LONG_LINK = 42

-- cos and sin of k * pi / 36 for k = 0..35, written out so that every
-- machine uses the same numbers
local COS, SIN = {}, {}
do
	local c = {
		1.0, 0.9961946980917455, 0.984807753012208, 0.9659258262890683,
		0.9396926207859084, 0.9063077870366499, 0.8660254037844387,
		0.8191520442889918, 0.766044443118978, 0.7071067811865476,
		0.6427876096865394, 0.5735764363510462, 0.5000000000000001,
		0.42261826174069944, 0.3420201433256688, 0.25881904510252074,
		0.17364817766693041, 0.08715574274765814, 0.0,
	}
	for k = 0, 18 do
		COS[k], SIN[k] = c[k + 1], c[19 - k]
	end
	for k = 19, 35 do
		COS[k], SIN[k] = -c[37 - k], c[k - 17]
	end
end

local function dist(ax, ay, bx, by)
	return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2)
end

-- the point of segment a-b nearest p
local function nearest_on(px, py, ax, ay, bx, by)
	local dx, dy = bx - ax, by - ay
	local l2 = dx * dx + dy * dy
	if l2 == 0 then l2 = 1 end
	local t = math.max(0, math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
	return ax + t * dx, ay + t * dy
end

local function sign(v) return v > 0 and 1 or v < 0 and -1 or 0 end

local function orient(p, q, r)
	return sign((q[1] - p[1]) * (r[2] - p[2]) - (q[2] - p[2]) * (r[1] - p[1]))
end

local function edges_of(stars)
	local edges = {}
	for _, s in ipairs(stars) do
		for _, t in ipairs(s.links) do
			if t.index > s.index then edges[#edges + 1] = { s.index, t.index } end
		end
	end
	return edges
end

local function linked(a, b)
	for _, t in ipairs(a.links) do
		if t == b then return true end
	end
	return false
end

-- (long links, stars on links, crowded pairs, crossings) of positions pos[i] = { along, across }
local function flaws(stars, edges, pos)
	local crossings = 0
	for i = 1, #edges do
		for j = i + 1, #edges do
			local a, b, c, d = edges[i][1], edges[i][2], edges[j][1], edges[j][2]
			if a ~= c and a ~= d and b ~= c and b ~= d then
				local A, B, C, D = pos[a], pos[b], pos[c], pos[d]
				if orient(A, B, C) * orient(A, B, D) < 0 and orient(C, D, A) * orient(C, D, B) < 0 then
					crossings = crossings + 1
				end
			end
		end
	end
	local crowded = 0
	for i = 1, #stars do
		for j = i + 1, #stars do
			if not linked(stars[i], stars[j]) and dist(pos[i][1], pos[i][2], pos[j][1], pos[j][2]) < 25 then
				crowded = crowded + 1
			end
		end
	end
	local on_link, long_links = 0, 0
	for _, e in ipairs(edges) do
		local A, B = pos[e[1]], pos[e[2]]
		for k = 1, #stars do
			if k ~= e[1] and k ~= e[2] then
				local qx, qy = nearest_on(pos[k][1], pos[k][2], A[1], A[2], B[1], B[2])
				if dist(pos[k][1], pos[k][2], qx, qy) < 10 then on_link = on_link + 1 end
			end
		end
		if dist(A[1], A[2], B[1], B[2]) > LONG_LINK then long_links = long_links + 1 end
	end
	return long_links, on_link, crowded, crossings
end

-- SC1's cluster seen from one angle round its long axis
local function view(stars, step)
	local pos = {}
	for i, t in ipairs(stars) do
		pos[i] = { t.x - M.CENTRE, t.y * COS[step] - t.z * SIN[step] }
	end
	return pos
end

local function relax(stars, edges, start)
	local n = #stars
	local along, across, home, side_a, fixed = {}, {}, {}, {}, {}
	for i, s in ipairs(stars) do
		along[i], across[i] = start[i][1], start[i][2]
		home[i] = s.x - M.CENTRE
		side_a[i] = s.side == "A"
		fixed[i] = i == 1
	end
	local link, target = {}, {}
	for i = 1, n do link[i], target[i] = {}, {} end
	for _, e in ipairs(edges) do
		local i, j = e[1], e[2]
		local a, b = stars[i], stars[j]
		link[i][j], link[j][i] = true, true
		local len = math.sqrt((a.x - b.x) ^ 2 + (a.y - b.y) ^ 2 + (a.z - b.z) ^ 2)
		target[i][j], target[j][i] = len, len
	end
	along[1], across[1] = 0.0, 0.0

	local function keep_to_side(i)
		along[i] = side_a[i] and math.max(along[i], SIDE_GAP) or math.min(along[i], -SIDE_GAP)
	end

	-- 1. springs: links pull toward their SC1 length, other stars push
	--    apart, every star drawn gently back toward its SC1 distance from
	--    the centre
	local ROUNDS = 150
	for round = 0, ROUNDS - 1 do
		local step = 1 - round / ROUNDS + 0.1
		local fa, fc = {}, {}
		for i = 1, n do fa[i], fc[i] = 0.0, 0.0 end
		for i = 1, n do
			for j = i + 1, n do
				local d = dist(along[j], across[j], along[i], across[i])
				if d == 0 then d = 0.01 end
				local k = 0
				if link[i][j] then
					k = (d - target[i][j]) * 0.5
				elseif d < 48 then
					k = -(48 - d) * 0.3
				end
				if k ~= 0 then
					local ua = (along[j] - along[i]) / d * k
					local uc = (across[j] - across[i]) / d * k
					fa[i], fc[i] = fa[i] + ua, fc[i] + uc
					fa[j], fc[j] = fa[j] - ua, fc[j] - uc
				end
			end
		end
		for k = 1, n do
			for _, e in ipairs(edges) do
				local i, j = e[1], e[2]
				if k ~= i and k ~= j then
					local qa, qc = nearest_on(along[k], across[k], along[i], across[i], along[j], across[j])
					local d = dist(along[k], across[k], qa, qc)
					if d == 0 then d = 0.01 end
					if d < 16 then
						local ua = (along[k] - qa) / d * (16 - d) * 0.3
						local uc = (across[k] - qc) / d * (16 - d) * 0.3
						fa[k], fc[k] = fa[k] + ua, fc[k] + uc
						fa[i], fc[i] = fa[i] - ua / 2, fc[i] - uc / 2
						fa[j], fc[j] = fa[j] - ua / 2, fc[j] - uc / 2
					end
				end
			end
		end
		for i = 2, n do
			fa[i] = fa[i] + (home[i] - along[i]) * 0.02
			local size = math.sqrt(fa[i] ^ 2 + fc[i] ^ 2)
			local scale = (size > 6 and 6 / size or 1) * step
			along[i] = along[i] + fa[i] * scale
			across[i] = across[i] + fc[i] * scale
			keep_to_side(i)
		end
	end

	-- 2. hard limits: stars apart and off other links, links within 20-38
	local function move(i, da, dc)
		if fixed[i] then return end
		along[i], across[i] = along[i] + da, across[i] + dc
		keep_to_side(i)
	end
	local function hold(i, j, lo, hi)
		local d = dist(along[j], across[j], along[i], across[i])
		if d == 0 then d = 0.01 end
		local goal = math.min(math.max(d, lo), hi)
		if goal == d then return end
		local share = (d - goal) / d / ((fixed[i] or fixed[j]) and 1 or 2)
		local da, dc = (along[j] - along[i]) * share, (across[j] - across[i]) * share
		move(i, da, dc)
		move(j, -da, -dc)
	end
	for _ = 1, 80 do
		for i = 1, n do
			for j = i + 1, n do
				if not link[i][j] then hold(i, j, APART, math.huge) end
			end
		end
		for k = 1, n do
			for _, e in ipairs(edges) do
				local i, j = e[1], e[2]
				if k ~= i and k ~= j then
					local qa, qc = nearest_on(along[k], across[k], along[i], across[i], along[j], across[j])
					local d = dist(along[k], across[k], qa, qc)
					if d == 0 then d = 0.01 end
					if d < LINK_CLEARANCE then
						local f = (LINK_CLEARANCE - d) / d / 2
						local da, dc = (along[k] - qa) * f, (across[k] - qc) * f
						move(k, da, dc)
						move(i, -da / 2, -dc / 2)
						move(j, -da / 2, -dc / 2)
					end
				end
			end
		end
		for _, e in ipairs(edges) do hold(e[1], e[2], MIN_DIST, LINK_MAX) end
	end
	local pos = {}
	for i = 1, n do pos[i] = { along[i], across[i] } end
	return pos
end

-- Flat positions in SC1 units, pos[i] = { along, across }, star 1 at (0, 0);
-- along is SC1's x (the Alliance's half positive).
function M.flatten(stars)
	local edges = edges_of(stars)
	local starts = {}
	for step = 0, ANGLES - 1 do
		local _, on_link, crowded, crossings = flaws(stars, edges, view(stars, step))
		starts[#starts + 1] = { step = step, key = crossings * 3 + crowded + on_link }
	end
	table.sort(starts, function(a, b)
		if a.key ~= b.key then return a.key < b.key end
		return a.step < b.step
	end)
	local best, best_score
	for t = 1, TRIES do
		local pos = relax(stars, edges, view(stars, starts[t].step))
		local long_links, on_link, crowded, crossings = flaws(stars, edges, pos)
		local score = long_links * 5 + on_link * 4 + crowded * 4 + crossings
		if not best_score or score < best_score then best, best_score = pos, score end
	end
	return best
end

-- ---- hexes -----------------------------------------------------------------
-- Wesnoth's hexes sit 3/4 of a hex apart across and 1 apart down, even
-- columns half a hex lower; distances here are in hexes (row heights).

local function centre(x, y)
	return 0.75 * x, y + (x % 2 == 0 and 0.5 or 0)
end

local function neighbours(x, y)
	local d = x % 2 == 0 and 0 or -1
	return { { x, y - 1 }, { x, y + 1 }, { x - 1, y + d }, { x - 1, y + d + 1 },
		{ x + 1, y + d }, { x + 1, y + d + 1 } }
end

-- the hex whose centre is nearest a point given in hexes
local function snap(px, py)
	local best, bx, by
	local x0 = math.floor(px / 0.75 + 0.5)
	for x = x0 - 1, x0 + 1 do
		for y = math.floor(py) - 1, math.floor(py) + 1 do
			local cx, cy = centre(x, y)
			local d = (cx - px) ^ 2 + (cy - py) ^ 2
			if not best or d < best then best, bx, by = d, x, y end
		end
	end
	return bx, by
end

local function seg_dist(px, py, ax, ay, bx, by)
	local qx, qy = nearest_on(px, py, ax, ay, bx, by)
	return dist(px, py, qx, qy)
end

local function hex_dist(a, b)
	local ax, ay = centre(a[1], a[2])
	local bx, by = centre(b[1], b[2])
	return dist(ax, ay, bx, by)
end

-- shuffle a list in place with random(n) -> 1..n
local function shuffle(list, random)
	for i = #list, 2, -1 do
		local j = random(i)
		list[i], list[j] = list[j], list[i]
	end
	return list
end

-- ---- the map ---------------------------------------------------------------

local S = 6          -- SC1 units per hex (SC1's links are 20-38 long)
local LANE = 1.8     -- lane half-width in hexes (about 4 across)
local POCKET = 2.2   -- open radius round planets
local BASE = 16      -- how far beyond its star (SC1 units) a starbase's keep sits
local FORWARD = 34   -- how far from the centre star (SC1 units) the forward keeps sit
local WAIST = 1 / 3  -- share of the middle band (between the forward keeps) made impassable
local MARGIN = 2     -- hexes kept beyond the outermost planet or starbase
local PAD = 3        -- hexes of rough terrain beyond the outermost open hex

local function has(t, ...)
	for _, k in ipairs { ... } do
		if t:find(k, 1, true) then return true end
	end
	return false
end

-- Builds the map round the cluster SC1 makes from `seed` (0-65535), with
-- `hierarchy` and `alliance` stars a side. random(n) gives a whole number
-- 1..n and random() a number in [0, 1), all from the same synced source.
-- Returns the map data and the stars, each { x, y, sc1x, side }: its hex
-- and its x along SC1's cluster.
function M.build(seed, hierarchy, alliance, random)
	local function uniform(a, b) return a + (b - a) * random() end
	local stars = M.cluster(seed, alliance, hierarchy)
	local flat = M.flatten(stars)
	local n = #stars
	-- x across, y along SC1's axis: the Hierarchy's half (B) on top
	local nodes, links = {}, edges_of(stars)
	for i = 1, n do nodes[i] = { flat[i][2], flat[i][1] } end
	-- the starbases: SC1 puts each on the star of its half farthest from
	-- the centre; here the keep sits just beyond that star, linked to it
	local ends = {}
	for end_, side in ipairs { "B", "A" } do
		local anchor
		for i, s in ipairs(stars) do
			if s.side == side and (not anchor or
				(side == "B" and s.x < stars[anchor].x) or (side == "A" and s.x > stars[anchor].x)) then
				anchor = i
			end
		end
		local ax, ay = nodes[anchor][1], nodes[anchor][2]
		local d = math.sqrt(ax * ax + ay * ay)
		nodes[#nodes + 1] = { ax + ax / d * BASE, ay + ay / d * BASE }
		ends[end_] = #nodes
		links[#links + 1] = { anchor, #nodes }
	end
	local minx, miny, maxx, maxy = math.huge, math.huge, -math.huge, -math.huge
	for _, p in ipairs(nodes) do
		minx, maxx = math.min(minx, p[1] / S), math.max(maxx, p[1] / S)
		miny, maxy = math.min(miny, p[2] / S), math.max(maxy, p[2] / S)
	end
	local ox, oy = -minx + 0.75 * (PAD + 2), -miny + PAD + 2
	local hexes = {}
	for i, p in ipairs(nodes) do hexes[i] = { snap(p[1] / S + ox, p[2] / S + oy) } end
	local W = math.floor((maxx + ox + 0.75 * (PAD + 2)) / 0.75) + 1
	local H = math.floor(maxy + oy + PAD + 2) + 1
	local function in_map(x, y) return x >= 1 and x <= W and y >= 1 and y <= H end
	-- the centre star's hex: where the forward keeps are measured from
	ox, oy = centre(hexes[1][1], hexes[1][2])
	local cen = {}
	for i, h in ipairs(hexes) do cen[i] = { centre(h[1], h[2]) } end

	local grid, open = {}, {}
	for y = 0, H + 1 do
		grid[y], open[y] = {}, {}
		for x = 0, W + 1 do grid[y][x] = "Ys" end
	end
	local function is_open(x, y) return open[y] and open[y][x] end
	local open_list = {}
	for x = 1, W do
		for y = 1, H do
			local px, py = centre(x, y)
			local o = false
			for _, c in ipairs(cen) do
				if dist(px, py, c[1], c[2]) <= POCKET then o = true; break end
			end
			if not o then
				for _, l in ipairs(links) do
					local a, b = cen[l[1]], cen[l[2]]
					if seg_dist(px, py, a[1], a[2], b[1], b[2]) <= LANE then o = true; break end
				end
			end
			if o then
				open[y][x] = true
				open_list[#open_list + 1] = { x, y }
			end
		end
	end

	-- rough terrain outside the lanes: smooth random fields, the largest wins
	local kinds = { "Yn", "Yis", "Yd", "Ys^Ya", "Ys" }
	local weights = { 1.0, 0.8, 0.45, 0.4, 0.6 }   -- "Ys": open gaps through the rough
	local blobs = {}
	for k = 1, #kinds do
		for _ = 1, math.floor(W * H / 60) do
			blobs[#blobs + 1] = { k, uniform(0, 0.75 * W), uniform(0, H), uniform(1.5, 3.5) }
		end
	end
	local rough = {}
	for x = 0, W + 1 do
		for y = 0, H + 1 do
			if not is_open(x, y) then
				local px, py = centre(x, y)
				local score = { 0, 0, 0, 0, 0 }
				for _, b in ipairs(blobs) do
					local d2 = ((px - b[2]) ^ 2 + (py - b[3]) ^ 2) / (b[4] * b[4])
					-- a smooth bump, 1 at the blob's middle, 0 at twice its radius
					if d2 < 4 then score[b[1]] = score[b[1]] + (1 - d2 / 4) ^ 3 end
				end
				local best = 1
				for k = 1, #kinds do
					score[k] = score[k] * weights[k]
					if score[k] > score[best] then best = k end
				end
				grid[y][x] = kinds[best]
				if in_map(x, y) then rough[#rough + 1] = { x, y } end
			end
		end
	end

	-- red nebula: small patches on the edges of green nebula
	local edges = {}
	for _, h in ipairs(rough) do
		if grid[h[2]][h[1]] == "Yn" then
			for _, nb in ipairs(neighbours(h[1], h[2])) do
				if in_map(nb[1], nb[2]) and not is_open(nb[1], nb[2]) and grid[nb[2]][nb[1]] ~= "Yn" then
					edges[#edges + 1] = h
					break
				end
			end
		end
	end
	shuffle(edges, random)
	for e = 1, math.min(#edges, math.max(3, W * H // 300)) do
		local size, patch, q, inpatch = random(4) + 2, 0, { edges[e] }, {}
		while #q > 0 and patch < size do
			local a = table.remove(q, random(#q))
			local x, y = a[1], a[2]
			if not (inpatch[y * 1024 + x] or not in_map(x, y) or is_open(x, y) or grid[y][x] == "Yr") then
				inpatch[y * 1024 + x] = true
				patch = patch + 1
				grid[y][x] = "Yr"
				for _, nb in ipairs(neighbours(x, y)) do q[#q + 1] = nb end
			end
		end
	end

	-- a debris disk (a star behind rocks, 3 hexes) in every big asteroid field
	local ast, seen = {}, {}
	local ast_list = {}
	for _, h in ipairs(rough) do
		if grid[h[2]][h[1]] == "Ys^Ya" then
			ast[h[2] * 1024 + h[1]] = true
			ast_list[#ast_list + 1] = h
		end
	end
	table.sort(ast_list, function(a, b) return a[1] < b[1] or (a[1] == b[1] and a[2] < b[2]) end)
	for _, h0 in ipairs(ast_list) do
		if not seen[h0[2] * 1024 + h0[1]] then
			local comp, q = {}, { h0 }
			seen[h0[2] * 1024 + h0[1]] = true
			while #q > 0 do
				local a = table.remove(q)
				comp[#comp + 1] = a
				for _, nb in ipairs(neighbours(a[1], a[2])) do
					local key = nb[2] * 1024 + nb[1]
					if ast[key] and not seen[key] then
						seen[key] = true
						q[#q + 1] = nb
					end
				end
			end
			if #comp >= 15 then
				local cs, mx, my = {}, 0, 0
				for _, c in ipairs(comp) do
					cs[c[2] * 1024 + c[1]] = true
					local cx, cy = centre(c[1], c[2])
					mx, my = mx + cx / #comp, my + cy / #comp
				end
				local best, tri
				for _, c in ipairs(comp) do
					local x, y = c[1], c[2]
					if x % 2 == 0 and cs[y * 1024 + x + 1] and cs[(y + 1) * 1024 + x + 1] then
						local t = { { x, y }, { x + 1, y }, { x + 1, y + 1 } }
						local clear = true
						for _, p in ipairs(t) do
							for _, nb in ipairs(neighbours(p[1], p[2])) do
								if is_open(nb[1], nb[2]) then clear = false end
							end
						end
						if clear then
							local cx, cy = centre(x + 1, y + 0.5)
							local d = dist(cx, cy, mx, my)
							if not best or d < best then best, tri = d, t end
						end
					end
				end
				if tri then
					local look = random(6)
					for _, p in ipairs(tri) do grid[p[2]][p[1]] = "Ys^Ytd" .. look end
				end
			end
		end
	end

	-- a few lone obstacles, well away from lanes: hexes 3 or more steps
	-- from any open hex
	local steps = {}
	local q = {}
	for _, h in ipairs(open_list) do
		steps[h[2] * 1024 + h[1]] = 0
		q[#q + 1] = h
	end
	local head = 1
	while head <= #q do
		local a = q[head]
		head = head + 1
		for _, nb in ipairs(neighbours(a[1], a[2])) do
			local key = nb[2] * 1024 + nb[1]
			if in_map(nb[1], nb[2]) and not steps[key] then
				steps[key] = steps[a[2] * 1024 + a[1]] + 1
				q[#q + 1] = nb
			end
		end
	end
	local far = {}
	for _, h in ipairs(rough) do
		if (steps[h[2] * 1024 + h[1]] or 99) >= 3 then far[#far + 1] = h end
	end
	shuffle(far, random)
	local obstacles = { "^Yx", "^Yxb", "^Yxp", "^Ybd" }
	local placed = {}
	for _, h in ipairs(far) do
		if #placed >= math.max(3, W * H // 400) then break end
		local t = grid[h[2]][h[1]]
		local clear = not t:find("^Yt", 1, true)
		for _, p in ipairs(placed) do
			if hex_dist(h, p) <= 8 then clear = false end
		end
		if clear then
			placed[#placed + 1] = h
			grid[h[2]][h[1]] = t:match("^[^%^]*") .. obstacles[(#placed - 1) % #obstacles + 1]
		end
	end

	-- planets (lua/sc1.lua deals their types), then the starbases
	for i = 1, n do grid[hexes[i][2]][hexes[i][1]] = "Ys^Vyd" end
	local mx, my = 0.75 * (W + 1) / 2, (H + 1) / 2
	for side = 1, 2 do
		local x, y = hexes[ends[side]][1], hexes[ends[side]][2]
		grid[y][x] = side .. " Yk"
		local nb = neighbours(x, y)
		table.sort(nb, function(a, b)
			local ax, ay = centre(a[1], a[2])
			local bx, by = centre(b[1], b[2])
			local da, db = dist(ax, ay, mx, my), dist(bx, by, mx, my)
			if da ~= db then return da < db end
			return a[1] < b[1] or (a[1] == b[1] and a[2] < b[2])
		end)
		for k = 1, 3 do grid[nb[k][2]][nb[k][1]] = "Yc" end
	end

	-- forward keeps: one each side of the middle, each with 3 docking rings
	local near_planet = {}
	for i = 1, n do
		local h = hexes[i]
		near_planet[h[2] * 1024 + h[1]] = true
		for _, nb in ipairs(neighbours(h[1], h[2])) do near_planet[nb[2] * 1024 + nb[1]] = true end
	end
	local used = {}
	local forward_y = {}
	for _, sy in ipairs { -1, 1 } do
		local tx, ty = ox, oy + sy * FORWARD / S
		local best, keep, ring
		for _, h in ipairs(open_list) do
			local key = h[2] * 1024 + h[1]
			if not near_planet[key] and not used[key] then
				local r = {}
				for _, nb in ipairs(neighbours(h[1], h[2])) do
					local k2 = nb[2] * 1024 + nb[1]
					if is_open(nb[1], nb[2]) and not near_planet[k2] and not used[k2] then r[#r + 1] = nb end
				end
				if #r >= 3 then
					local cx, cy = centre(h[1], h[2])
					local d = dist(cx, cy, tx, ty)
					if not best or d < best then best, keep, ring = d, h, r end
				end
			end
		end
		grid[keep[2]][keep[1]] = "Yk"
		table.sort(ring, function(a, b)
			local ax, ay = centre(a[1], a[2])
			local bx, by = centre(b[1], b[2])
			local da, db = dist(ax, ay, tx, ty), dist(bx, by, tx, ty)
			if da ~= db then return da < db end
			return a[1] < b[1] or (a[1] == b[1] and a[2] < b[2])
		end)
		used[keep[2] * 1024 + keep[1]] = true
		for k = 1, 3 do
			grid[ring[k][2]][ring[k][1]] = "Yc"
			used[ring[k][2] * 1024 + ring[k][1]] = true
		end
		for _, nb in ipairs(neighbours(keep[1], keep[2])) do used[nb[2] * 1024 + nb[1]] = true end
		forward_y[#forward_y + 1] = keep[2]
	end

	-- cover in the lanes: small patches (1-4 hexes) to hide in or fight
	-- from, clear of planets, starbases and docking rings
	local function busy(x, y)
		return has(grid[y][x], "Vy", "Yk", "Yc")
	end
	local cand, is_cand = {}, {}
	for _, h in ipairs(open_list) do
		if grid[h[2]][h[1]] == "Ys" then
			local ok = true
			for _, nb in ipairs(neighbours(h[1], h[2])) do
				if in_map(nb[1], nb[2]) and busy(nb[1], nb[2]) then ok = false end
			end
			if ok then
				cand[#cand + 1] = h
				is_cand[h[2] * 1024 + h[1]] = true
			end
		end
	end
	shuffle(cand, random)
	local seeds = {}
	for _, h in ipairs(cand) do
		if #seeds >= #links * 2 // 3 then break end
		local ok = true
		for _, s in ipairs(seeds) do
			if hex_dist(h, s) <= 4.5 then ok = false end
		end
		if ok then seeds[#seeds + 1] = h end
	end
	local cover = { { "Yn", 0.3 }, { "Yd", 0.2 }, { "Yis", 0.2 }, { "Ys^Ya", 0.2 }, { "Yr", 0.1 } }
	for _, h in ipairs(seeds) do
		local r, kind = random(), "Yr"
		for _, c in ipairs(cover) do
			if r < c[2] then kind = c[1]; break end
			r = r - c[2]
		end
		local size, patch, q2, inpatch = random(4), 0, { h }, {}
		while #q2 > 0 and patch < size do
			local a = table.remove(q2, random(#q2))
			local key = a[2] * 1024 + a[1]
			if not inpatch[key] and is_cand[key] then
				inpatch[key] = true
				patch = patch + 1
				grid[a[2]][a[1]] = kind
				for _, nb in ipairs(neighbours(a[1], a[2])) do q2[#q2 + 1] = nb end
			end
		end
	end

	-- the hourglass's waist: between the forward keeps, the third of the
	-- hexes furthest from any lane becomes impassable dark nebula
	local top, bottom = math.min(forward_y[1], forward_y[2]), math.max(forward_y[1], forward_y[2])
	local walls, band = {}, 0
	for x = 1, W do
		for y = top, bottom do
			band = band + 1
			local t = grid[y][x]
			if not is_open(x, y) and not t:find("^Y", 1, true) and not has(t, "Vy", "Yk", "Yc") then
				local cx = centre(x, y)
				walls[#walls + 1] = { x, y, steps[y * 1024 + x] or 99, math.abs(cx - mx) }
			end
		end
	end
	table.sort(walls, function(a, b)
		if a[3] ~= b[3] then return a[3] > b[3] end
		if a[4] ~= b[4] then return a[4] > b[4] end
		return a[1] < b[1] or (a[1] == b[1] and a[2] < b[2])
	end)
	for k = 1, math.min(#walls, math.floor(band * WAIST + 0.5)) do
		grid[walls[k][2]][walls[k][1]] = "Yqd"
	end

	-- crop to MARGIN hexes beyond the outermost planet, starbase or docking
	-- ring on every side; columns go in even numbers on the left so the
	-- hexes keep their places (even columns sit half a hex lower)
	local t, b, l, r = math.huge, -math.huge, math.huge, -math.huge
	for y = 1, H do
		for x = 1, W do
			if has(grid[y][x], "Vy", "Yk", "Yc") then
				t, b = math.min(t, y), math.max(b, y)
				l, r = math.min(l, x), math.max(r, x)
			end
		end
	end
	t, b = math.max(1, t - MARGIN), math.min(H, b + MARGIN)
	l, r = math.max(1, l - MARGIN), math.min(W, r + MARGIN)
	l = l - (l - 1) % 2
	local rows = {}
	for _, y in ipairs { 0 } do rows[#rows + 1] = y end
	for y = t, b do rows[#rows + 1] = y end
	rows[#rows + 1] = H + 1
	local lines = {}
	for _, y in ipairs(rows) do
		local cells = { grid[y][0] }
		for x = l, r do cells[#cells + 1] = grid[y][x] end
		cells[#cells + 1] = grid[y][W + 1]
		lines[#lines + 1] = table.concat(cells, ", ")
	end
	local out = {}
	for i, s in ipairs(stars) do
		out[i] = { hexes[i][1] - l + 1, hexes[i][2] - t + 1, s.x, s.side }
	end
	return table.concat(lines, "\n") .. "\n", out
end

return M
