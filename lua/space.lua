-- The Ur-Quan Wars: play any map in space. When a game with the era starts
-- on a map drawn with ordinary Wesnoth terrain (a core map, or a user-made
-- one), every hex is turned into its deep-space counterpart, so the map
-- plays like the original but looks like space. Maps that already use the
-- era's space terrain (anything Y*) are left alone.
-- Written against the Wesnoth 1.16 Lua API; loaded after planets.lua.
--
-- The rules are the ones tools/convert_map.py uses to make the add-on's own
-- converted maps; keep the two in step. Terrain is translated by role:
--
--   open ground (grass, road, cave floor, ice)  -> deep space          Ys
--   sand, desert                                -> dust cloud          Yd
--   forest, trees                               -> nebula              Yn
--   mushroom grove                              -> red nebula          Yr
--   hills, rockbound cave                       -> asteroid field      Ys^Ya
--   dunes (sandy hills)                         -> asteroids in dust   Yd^Ya
--   forested hills                              -> asteroids in nebula Yn^Ya
--   mountains                                   -> dense asteroids     Ys^Yad
--   deep water                                  -> badlands            Yi
--   shallow water, reef, swamp                  -> light badlands      Yis
--   ford, bridge                                -> deep space (a lane) Ys
--   village                                     -> planet              ^Vyp
--   village in water (not swamp)                -> sea planet          ^Vys
--   castle / keep                               -> docking ring / base Yc / Yk
--   castle in water or swamp                    -> docking ring in the badlands Yci
--   cave and stone walls, impassable mountains,
--     the impassable overlay (^Xo)              -> debris disk         Ys^Yw
--   void (Xv)                                   -> dark nebula         Yqd
--   lava, volcano                               -> star                Ys^Yx
--       ...but lava that touches more lava      -> plasma storm        Yqp
--   chasm                                       -> black hole          Ys^Yxb
--       ...but chasm that touches more chasm    -> gravity eddy        Yqe
--   off-map                                     -> unchanged, but holes cut
--                                                  into the play area -> Yqd
--   fake map edge (^_fme)                       -> kept, over the converted base
--   a big block of debris disk or dark nebula
--     that reaches the edge of the map          -> void                Yv
--   a big clump of debris disk, gravity eddy,
--     dark nebula or plasma storm               -> its centrepiece in the middle
--                                                  (see centrepieces below)
--
-- The new planets are then given types (life, mineral, dead: 40/40/20, no
-- more than 20% dead) following the map's symmetry, as the era's "Planets"
-- option deals them (sc.deal_planet_types in planets.lua), and the
-- scenario's day and night is replaced by the space maps' Deep Space time.

local _ = wesnoth.textdomain "wesnoth-The_Ur-Quan_Wars"

-- One hex's terrain code, in space.
local function convert(code)
	if code:sub(1, 4) == "_off" or code:sub(1, 1) == "Y" then return code end
	if code:sub(-5) == "^_fme" then           -- fake map edge: keep it over the new base
		local under = convert(code:sub(1, -6))
		under = ({ ["#lava"] = "Yqp", ["#chasm"] = "Yqe" })[under] or under
		return under:match("^[^^]*") .. "^_fme"
	end
	local base, overlay = code:match("^([^^]*)%^?(.*)$")
	local b, o = base:sub(1, 1), overlay:sub(1, 1)

	if o == "B" then return "Ys" end           -- bridges become open lanes
	-- impassable terrain; lava and chasms are settled by what they touch
	if base == "Xv" then return "Yqd" end      -- void
	if o == "X" or b == "X" then return "Ys^Yw" end
	if base:sub(1, 2) == "Ql" then return "#lava" end
	if b == "Q" or o == "Q" then return "#chasm" end
	if base == "Mv" then return "Ys^Yx" end    -- volcano
	if b == "K" or overlay == "Kov" then return "Yk" end
	if b == "C" or overlay == "Cov" then
		-- sunken (Chw) and swamp (Chs) ruins, aquatic castles (Cm, Cme)
		local wet = base:match("^Ch[ws]$") or base:match("^Cme?$") or (overlay == "Cov" and (b == "W" or b == "S"))
		return wet and "Yci" or "Yc"
	end
	local village = o == "V"
	if base:sub(1, 2) == "Uh" then             -- rockbound cave (rough, like hills)
		return village and "Ys^Vyp" or "Ys^Ya"
	end
	if base:sub(1, 3) == "Wwf" then            -- ford: open space, like a bridge
		return village and "Ys^Vyp" or "Ys"
	end

	local new
	if base:sub(1, 2) == "Wo" then             -- deep water
		new = "Yi"
	elseif b == "W" or b == "S" then           -- shallow water, reef, swamp
		new = "Yis"
	elseif b == "D" or base:sub(1, 2) == "Hd" then -- sand, dunes
		new = "Yd"
	else
		new = "Ys"
	end
	if b == "T" or o == "T" or overlay:sub(1, 2) == "Uf" then
		new = "Yr"                             -- mushroom grove
	elseif o == "F" then                       -- forest
		if new ~= "Yi" and new ~= "Yis" then new = "Yn" end
	end

	if village then return new .. (b == "W" and "^Vys" or "^Vyp") end
	if b == "M" then return new .. "^Yad" end
	if b == "H" then return new .. "^Ya" end
	return new
end

-- Wesnoth hex neighbours (columns with an odd x sit half a hex higher).
local function neighbours(x, y)
	if x % 2 == 1 then
		return { { x, y - 1 }, { x, y + 1 }, { x - 1, y - 1 }, { x + 1, y - 1 }, { x - 1, y }, { x + 1, y } }
	end
	return { { x, y - 1 }, { x, y + 1 }, { x - 1, y }, { x + 1, y }, { x - 1, y + 1 }, { x + 1, y + 1 } }
end

-- Big impassable blocks round the edge of the map (a cave map's rock, a
-- void border) are nothing at all, not a wall of debris disks: every block
-- of debris disk or dark nebula that reaches the edge and has at least
-- VOID_MIN hexes in the play area becomes void.
local VOID_MIN = 6
local VOIDABLE = { ["Ys^Yw"] = true, ["Yqd"] = true, ["Yv"] = true }
local function edge_void(new, x0, x1, y0, y1, w, h)
	local seen = {}
	local function key(x, y) return x * 10000 + y end
	for sx = x0, x1 do
		for sy = y0, y1 do
			if VOIDABLE[new[sx][sy]] and not seen[key(sx, sy)] then
				local block, edge, inside, i = { { sx, sy } }, false, 0, 1
				seen[key(sx, sy)] = true
				while i <= #block do
					local x, y = block[i][1], block[i][2]
					i = i + 1
					if x <= 1 or y <= 1 or x >= w or y >= h then edge = true end
					if x >= 1 and y >= 1 and x <= w and y <= h then inside = inside + 1 end
					for _, n in ipairs(neighbours(x, y)) do
						local nx, ny = n[1], n[2]
						if new[nx] and new[nx][ny] and VOIDABLE[new[nx][ny]] and not seen[key(nx, ny)] then
							seen[key(nx, ny)] = true
							block[#block + 1] = { nx, ny }
						end
					end
				end
				if edge and inside >= VOID_MIN then
					for _, b in ipairs(block) do new[b[1]][b[2]] = "Yv" end
				end
			end
		end
	end
end

-- Centrepieces. Every big clump of impassable cloud gets its matching
-- object in the middle, as on the hand-made maps: a supergiant behind a
-- debris disk, a supermassive black hole in a gravity eddy, a dark star in
-- a dark nebula, a big storm sun in a plasma storm. The object fills a
-- diamond of 4 hexes where one fits well inside the clump, else a triangle
-- of 3, else it is a one-hex star or black hole. It only takes hexes of the
-- clump, which are impassable either way, so the map plays the same. A
-- clump of 2 * PER_PIECE hexes or more gets one more piece for each
-- PER_PIECE, at least SPACING hexes apart. Void (Yv) is left alone, and so
-- is a clump that already has a piece. The pieces follow the map's
-- symmetry: where a mirror or a rotation maps the impassable hexes onto
-- each other (to within a hex), the clumps that match each other get the
-- same piece in the same look (each in its own kind of cloud), each at the
-- matching place. The same as tools/convert_map.py, step for step, so a
-- map comes out the same either way.
local CLOUDS = { ["Ys^Yw"] = "w", ["Yqe"] = "e", ["Yqd"] = "d", ["Yqp"] = "p" }
local PIECES = {                         -- kind -> {hexes: looks}
	w = { [4] = { "^Ysg", "^Ysg2", "^Ysg3", "^Ysg4" },
		[3] = { "^Ytd1", "^Ytd2", "^Ytd3", "^Ytd4", "^Ytd5", "^Ytd6" },
		[1] = { "^Yxd1", "^Yxd2", "^Yxd3", "^Yxd4", "^Yxd5" } },
	e = { [4] = { "^Ybh1", "^Ybh2", "^Ybh3", "^Ybh4", "^Ybh5", "^Ybh6" },
		[3] = { "^Ytbh" }, [1] = { "^Yxb1", "^Yxb2", "^Yxb3", "^Yxb4" } },
	d = { [4] = { "^Yds1", "^Yds2", "^Yds3", "^Yds4" }, [3] = { "^Ytds" }, [1] = { "^Yx" } },
	p = { [4] = { "^Ygg" }, [1] = { "^Yxs1", "^Yxs2", "^Yxs3", "^Yxs4", "^Yxs5", "^Yxs6" } },
}
local SIZES = { 4, 3, 1 }
local MIN_CLUMP = { [4] = 8, [3] = 6, [1] = 5 } -- clump hexes needed for each size of piece
local PER_PIECE, SPACING = 25, 4
local SYM_MIN = 0.7                      -- share of impassable hexes a symmetry must match
local S3 = math.sqrt(3)
-- cos and sin of k * 60 degrees, exact (so this rounds as convert_map.py does)
local COS = { [0] = 1, 0.5, -0.5, -1, -0.5, 0.5 }
local SIN = { [0] = 0, S3 / 2, S3 / 2, 0, -S3 / 2, -S3 / 2 }

local function cloud_kind(code)
	if CLOUDS[code] then return CLOUDS[code] end
	local base, overlay = code:match("^([^^]*)%^(.*)$")
	if not base then return nil end
	local o3 = overlay:sub(1, 3)
	if base == "Ys" and (o3 == "Ysg" or o3 == "Ytd" or o3 == "Yxd") then return "w" end
	if (base == "Yqe" or base == "Yqd" or base == "Yqp") and overlay ~= "" then return CLOUDS[base] end
	return nil
end

local function hex_distance(a, b)
	-- odd columns sit higher
	local az = a[2] - (a[1] - a[1] % 2) // 2
	local bz = b[2] - (b[1] - b[1] % 2) // 2
	return math.max(math.abs(a[1] - b[1]), math.abs(az - bz), math.abs(a[1] + az - b[1] - bz))
end

local function centre(p)
	return p[1] * S3 / 2, p[2] + (p[1] + 1) % 2 / 2
end

local function nearest_hex(px, py)
	local x = math.floor(px / (S3 / 2) + 0.5)
	return x, math.floor(py - (x + 1) % 2 / 2 + 0.5)
end

local function key(x, y) return x * 10000 + y end
-- hexes in reading order, as a string that sorts that way
local function order_key(s)
	local t = {}
	for i, p in ipairs(s) do t[i] = string.format("%05d%05d", p[2] + 100, p[1] + 100) end
	return table.concat(t)
end
local function sort_reading(s)
	table.sort(s, function(a, b) return a[2] < b[2] or (a[2] == b[2] and a[1] < b[1]) end)
	return s
end
local function gcd(a, b)
	while b ~= 0 do a, b = b, a % b end
	return a
end

-- The powers (but the identity) of the mirror or rotation of the play area
-- that best maps the impassable hexes onto or next to impassable hexes,
-- as functions on points; {} if none matches SYM_MIN of them.
local function symmetry(w, h, imp_list, near)
	local mx, my, n = 0, 0, 0
	for y = 1, h do
		for x = 1, w do
			local cx = centre { x, y }
			mx = mx + cx
			n = n + 1
		end
	end
	for y = 1, h do
		for x = 1, w do
			local _, cy = centre { x, y }
			my = my + cy
		end
	end
	mx, my = mx / n, my / n
	local function make(a, b, c, d)
		return function(px, py)
			return mx + a * (px - mx) + b * (py - my), my + c * (px - mx) + d * (py - my)
		end
	end
	local groups = {}
	for k = 1, 5 do                      -- rotations by k * 60 degrees
		local g = {}
		for j = 1, 6 // gcd(k, 6) - 1 do
			local t = j * k % 6
			g[#g + 1] = make(COS[t], -SIN[t], SIN[t], COS[t])
		end
		groups[#groups + 1] = g
	end
	for k = 0, 5 do                      -- mirrors, the axis at k * 30 degrees
		groups[#groups + 1] = { make(COS[k], SIN[k], SIN[k], -COS[k]) }
	end
	local best, best_score = {}, SYM_MIN * #imp_list
	for _, g in ipairs(groups) do
		local score = 0
		for _, p in ipairs(imp_list) do
			local qx, qy = nearest_hex(g[1](centre(p)))
			if near[key(qx, qy)] then score = score + 1 end
		end
		if score > best_score then best, best_score = g, score end
	end
	return best
end

-- Every diamond (4), triangle (3) or single hex (1) inside a set of hexes
-- (in reading order), each a list of hexes in reading order.
local function shapes(list, inset, size)
	local out, seen = {}, {}
	local function add(s)
		sort_reading(s)
		local k = order_key(s)
		if not seen[k] then seen[k] = true; out[#out + 1] = { k = k, s = s } end
	end
	for _, p in ipairs(list) do
		if size == 1 then
			add { p }
		else
			local ns = {}
			for _, q in ipairs(neighbours(p[1], p[2])) do
				if inset[key(q[1], q[2])] then ns[#ns + 1] = q end
			end
			local nset = {}
			for _, q in ipairs(ns) do nset[key(q[1], q[2])] = q end
			for _, q in ipairs(ns) do
				local common = {}
				for _, r in ipairs(neighbours(q[1], q[2])) do
					if nset[key(r[1], r[2])] then common[#common + 1] = nset[key(r[1], r[2])] end
				end
				if size == 3 then
					for _, r in ipairs(common) do add { p, q, r } end
				elseif #common == 2 then
					add { p, q, common[1], common[2] }
				end
			end
		end
	end
	table.sort(out, function(a, b) return a.k < b.k end)
	local r = {}
	for i, o in ipairs(out) do r[i] = o.s end
	return r
end

local function centrepieces(new, x0, x1, y0, y1, w, h)
	local function playable(p) return p[1] >= 1 and p[2] >= 1 and p[1] <= w and p[2] <= h end
	local kind = {}
	for y = y0, y1 do
		for x = x0, x1 do
			kind[key(x, y)] = cloud_kind(new[x][y])
		end
	end
	local clump_of, clumps = {}, {}
	for y = y0, y1 do
		for x = x0, x1 do
			local k = kind[key(x, y)]
			if k and not clump_of[key(x, y)] then
				local id = #clumps + 1
				local block, i = { { x, y } }, 1
				clump_of[key(x, y)] = id
				while i <= #block do
					local p = block[i]
					i = i + 1
					for _, q in ipairs(neighbours(p[1], p[2])) do
						local qk = key(q[1], q[2])
						if not clump_of[qk] and kind[qk] == k then
							clump_of[qk] = id
							block[#block + 1] = q
						end
					end
				end
				clumps[id] = block
			end
		end
	end
	local imp_list, near = {}, {}
	for y = 1, h do
		for x = 1, w do
			if kind[key(x, y)] then
				imp_list[#imp_list + 1] = { x, y }
				near[key(x, y)] = true
				for _, q in ipairs(neighbours(x, y)) do near[key(q[1], q[2])] = true end
			end
		end
	end
	local maps = symmetry(w, h, imp_list, near)
	local placed, looks = {}, {}

	local function too_close(s)
		for _, p in ipairs(s) do
			for _, q in ipairs(placed) do
				if hex_distance(p, q) < SPACING then return true end
			end
		end
		return false
	end
	-- where a piece of this size can go in clump i, best first: well inside
	-- the clump, near its middle, away from the other pieces
	local function candidates(i, size)
		local clump = clumps[i]
		local n = #clump
		local k = kind[key(clump[1][1], clump[1][2])]
		if n < MIN_CLUMP[size] or not PIECES[k][size] then return {} end
		local sx, sy = 0, 0
		local list, inset = {}, {}
		for _, p in ipairs(clump) do
			sx = sx + p[1]
			sy = sy + 2 * p[2] + (p[1] + 1) % 2
			if playable(p) then
				list[#list + 1] = p
				inset[key(p[1], p[2])] = true
			end
		end
		sort_reading(list)
		local out = {}
		for idx, s in ipairs(shapes(list, inset, size)) do
			if not too_close(s) then
				local mine, ring, cover, nring = {}, {}, 0, 0
				for _, p in ipairs(s) do mine[key(p[1], p[2])] = true end
				for _, p in ipairs(s) do
					for _, q in ipairs(neighbours(p[1], p[2])) do
						local qk = key(q[1], q[2])
						if not mine[qk] and not ring[qk] then
							ring[qk] = true
							nring = nring + 1
							if clump_of[qk] == i then cover = cover + 1 end
						end
					end
				end
				local ok
				if size > 1 then ok = 2 * cover >= nring else ok = cover >= 2 end
				if ok then
					local ax, ay = 0, 0
					for _, p in ipairs(s) do
						ax = ax + p[1]
						ay = ay + 2 * p[2] + (p[1] + 1) % 2
					end
					local dx, dy = n * ax - size * sx, n * ay - size * sy
					local mid = 3 * dx * dx + dy * dy
					out[#out + 1] = { cover = cover, mid = mid, idx = idx, s = s }
				end
			end
		end
		table.sort(out, function(a, b)
			if a.cover ~= b.cover then return a.cover > b.cover end
			if a.mid ~= b.mid then return a.mid < b.mid end
			return a.idx < b.idx
		end)
		local r = {}
		for j, o in ipairs(out) do r[j] = o.s end
		return r
	end
	local function middle(s)
		local cx, cy = 0, 0
		for _, p in ipairs(s) do
			local px, py = centre(p)
			cx = cx + px
			cy = cy + py
		end
		return cx / #s, cy / #s
	end

	-- the clumps that match each other under the symmetry, biggest first
	local done, by_size = {}, {}
	for i, c in ipairs(clumps) do
		by_size[i] = i
		for _, p in ipairs(c) do
			if not CLOUDS[new[p[1]][p[2]]] then done[i] = true; break end
		end
	end
	table.sort(by_size, function(a, b)
		local ca, cb = clumps[a], clumps[b]
		if #ca ~= #cb then return #ca > #cb end
		if ca[1][2] ~= cb[1][2] then return ca[1][2] < cb[1][2] end
		return ca[1][1] < cb[1][1]
	end)
	for _, i in ipairs(by_size) do
		if not done[i] then
			local mates = {}
			for _, m in ipairs(maps) do
				local hits, best, best_hits = {}, nil, 0
				for _, p in ipairs(clumps[i]) do
					if playable(p) then
						local j = clump_of[key(nearest_hex(m(centre(p))))]
						if j then hits[j] = (hits[j] or 0) + 1 end
					end
				end
				for j, c in pairs(hits) do
					if c > best_hits or (c == best_hits and j < best) then best, best_hits = j, c end
				end
				if best and not done[best] then mates[#mates + 1] = { best, m } end
			end
			done[i] = true
			for _, mate in ipairs(mates) do done[mate[1]] = true end
			for _ = 1, math.max(1, #clumps[i] // PER_PIECE) do
				local put = false
				for _, size in ipairs(SIZES) do
					local cands = candidates(i, size)
					if #cands > 0 then
						local s = cands[1]
						local mine = {}
						for _, p in ipairs(s) do mine[key(p[1], p[2])] = true end
						local pieces = { { kind[key(s[1][1], s[1][2])], s } }
						for _, mate in ipairs(mates) do
							local j, m = mate[1], mate[2]
							-- the mate's spot nearest the image of this piece's middle
							local tx, ty = m(middle(s))
							local pick, miss
							for _, c in ipairs(candidates(j, size)) do
								local shared = false
								for _, p in ipairs(c) do
									if mine[key(p[1], p[2])] then shared = true end
								end
								if not shared then
									local cx, cy = middle(c)
									local d = (cx - tx) * (cx - tx) + (cy - ty) * (cy - ty)
									if not miss or d < miss then pick, miss = c, d end
								end
							end
							if not pick then pieces = nil; break end
							pieces[#pieces + 1] = { kind[key(pick[1][1], pick[1][2])], pick }
						end
						if pieces then
							local n = looks[size] or 0
							for _, piece in ipairs(pieces) do
								-- a self-symmetric clump: one piece
								if not too_close(piece[2]) then
									local options = PIECES[piece[1]][size]
									local look = options[n % #options + 1]
									for _, p in ipairs(piece[2]) do
										new[p[1]][p[2]] = new[p[1]][p[2]]:match("^[^^]*") .. look
										placed[#placed + 1] = p
									end
								end
							end
							looks[size] = n + 1
							put = true
							break
						end
					end
				end
				if not put then break end
			end
		end
	end
end

-- Does the map already use space terrain?
local function is_space(map, x0, x1, y0, y1)
	for x = x0, x1 do
		for y = y0, y1 do
			local code = map[{ x, y }]
			if code:sub(1, 1) == "Y" or code:find("%^Y") or code:find("%^Vy") then return true end
		end
	end
	return false
end

-- Types for the new, untyped planets (^Vyp, ^Vys).
local function type_planets()
	local planets, sea = {}, {}
	for _, loc in ipairs(wesnoth.map.find { terrain = "*^Vyp,*^Vys" }) do
		planets[#planets + 1] = { loc[1], loc[2] }
		sea[#planets] = wesnoth.current.map[loc]:match("%^Vy(s?)p?$")
	end
	local n = #planets
	if n == 0 then return end
	-- the mix to aim for: 40% life, 40% mineral, 20% dead (rounded down)
	local d = math.floor(n * 0.2)
	local l = math.ceil((n - d) / 2)
	for i, p in ipairs(planets) do
		p[3] = i <= l and "l" or i <= n - d and "m" or "d"
	end
	local starts = {}
	for _, side in ipairs(wesnoth.sides) do
		starts[#starts + 1] = side.starting_location
	end
	local types = sc.deal_planet_types(planets, true, starts)
	for i, p in ipairs(planets) do
		wesnoth.current.map[{ p[1], p[2] }] = "^Vy" .. sea[i] .. types[i]
	end
end

-- Turn the map into space, unless the era's "Play any map in space" option
-- is off or the map is space already (prestart, before the planets are
-- dealt). Called again (again = true) at start and at every turn refresh
-- for any terrain the scenario drew after ours or changed since: Team
-- Survival's masks, Aethermaw's halves joining on turns 4-6.
function sc.convert_to_space(again)
	if wml.variables["sc_space"] == false then return end
	local map = wesnoth.current.map
	local border = map.border_size
	local x0, x1 = 1 - border, map.playable_width + border
	local y0, y1 = 1 - border, map.playable_height + border
	if again then
		if not wml.variables["sc_space_converted"] then return end
	elseif is_space(map, x0, x1, y0, y1) then
		return
	end
	wml.variables["sc_space_converted"] = true

	local new, marked = {}, {}
	for x = x0, x1 do
		new[x] = {}
		for y = y0, y1 do
			local code = convert(map[{ x, y }])
			-- off-map holes cut into the play area become dark nebula
			if code:sub(1, 4) == "_off" and x >= 1 and y >= 1
				and x <= map.playable_width and y <= map.playable_height then
				code = "Yqd"
			end
			new[x][y] = code
			if code:sub(1, 1) == "#" then marked[#marked + 1] = { x, y, code } end
		end
	end
	-- a lone lava hex is a star, a lone chasm a black hole; where they
	-- touch more of the same they are a plasma storm or a gravity eddy,
	-- so a lava field doesn't become a row of suns
	local LONE = { ["#lava"] = "Ys^Yx", ["#chasm"] = "Ys^Yxb" }
	local FIELD = { ["#lava"] = "Yqp", ["#chasm"] = "Yqe" }
	for _, m in ipairs(marked) do
		local x, y, kind = m[1], m[2], m[3]
		local field = false
		for _, n in ipairs(neighbours(x, y)) do
			local c = new[n[1]] and new[n[1]][n[2]]
			if c == kind or c == FIELD[kind] then field = true; break end
		end
		new[x][y] = field and FIELD[kind] or LONE[kind]
	end
	edge_void(new, x0, x1, y0, y1, map.playable_width, map.playable_height)
	centrepieces(new, x0, x1, y0, y1, map.playable_width, map.playable_height)

	for x = x0, x1 do
		for y = y0, y1 do
			if map[{ x, y }] ~= new[x][y] then map[{ x, y }] = new[x][y] end
		end
	end
	type_planets()
	if again then return end

	-- space has no day and night
	wesnoth.wml_actions.replace_schedule {
		wml.tag.time {
			id = "sc_deep_space",
			name = _ "Deep Space",
			image = "misc/time-schedules/schedule-underground.png",
			lawful_bonus = 0,
		},
	}
end
