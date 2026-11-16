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
