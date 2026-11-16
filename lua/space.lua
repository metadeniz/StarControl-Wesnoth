-- Star Control TC: play any map in space. When a game with the era starts
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
--   impassable, chasm                           -> star                Ys^Yx
--       ...but where impassable hexes touch     -> asteroid wall       Ys^Yw
--   off-map                                     -> unchanged
--   fake map edge (^_fme)                       -> kept, over the converted base
--
-- The new planets are then given types (life, mineral, dead: 40/40/20, no
-- more than 20% dead) following the map's symmetry, as the era's "Planets"
-- option deals them (sc.deal_planet_types in planets.lua), and the
-- scenario's day and night is replaced by the space maps' Deep Space time.

local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

-- One hex's terrain code, in space.
local function convert(code)
	if code:sub(1, 4) == "_off" or code:sub(1, 1) == "Y" then return code end
	if code:sub(-5) == "^_fme" then           -- fake map edge: keep it over the new base
		return convert(code:sub(1, -6)):match("^[^^]*") .. "^_fme"
	end
	local base, overlay = code:match("^([^^]*)%^?(.*)$")
	local b, o = base:sub(1, 1), overlay:sub(1, 1)

	if o == "X" or o == "Q" or b == "X" or b == "Q" then
		return "Ys^Yx"                         -- impassable, chasm
	end
	if o == "B" then return "Ys" end           -- bridges become open lanes
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
-- dealt). Called again at start (again = true) for any terrain the
-- scenario's own prestart events drew after ours, such as Team Survival's
-- masks.
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

	local new, star = {}, {}
	for x = x0, x1 do
		new[x] = {}
		for y = y0, y1 do
			local code = convert(map[{ x, y }])
			new[x][y] = code
			if code == "Ys^Yx" then star[#star + 1] = { x, y } end
		end
	end
	-- impassable hexes that touch another one become an asteroid wall
	local wall = {}
	for _, s in ipairs(star) do
		for _, n in ipairs(neighbours(s[1], s[2])) do
			if new[n[1]] and new[n[1]][n[2]] == "Ys^Yx" then wall[#wall + 1] = s; break end
		end
	end
	for _, s in ipairs(wall) do new[s[1]][s[2]] = "Ys^Yw" end

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
