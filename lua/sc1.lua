-- Star Control TC: Star Control 1's built-in missions (scenarios/scenarios_sc1.cfg).
-- Written against the Wesnoth 1.16 Lua API; loaded after sc.lua.
--
-- Star Control 1 drew a fresh star cluster for every game. Here each
-- mission has a few maps, each drawn by tools/make_sc1_maps.py round the
-- cluster SC1's own generator builds from one seed, with a .lua file beside
-- it giving each star's hex and its x along SC1's cluster. At prestart,
-- before the era's planet income and Precursor artifacts are set up,
-- sc1.setup() picks one of the maps and sets the game up the way SC1's
-- scenario setup does (STARCON.EXE 014C:01FE, as the starcon1-map-prototype
-- project read it): each side's worlds dealt at random onto its half, the
-- starbases at the far ends and the ships placed by start zone. It uses the
-- synced random numbers, so every player sees the same game. On every map
-- the Hierarchy (side 1) starts at the north end and the Alliance (side 2)
-- at the south.

local T = wml.tag
local _ = wesnoth.textdomain "wesnoth-Star_Control_TC"

sc1 = {}

-- Each mission: its maps (in maps/), and each side's setup from Star
-- Control 1's SCENARIO files:
--   ships   { unit type, start zone }, each placed at a random star of its
--           zone, as in SC1: 0 its half's back (the stars farther from the
--           centre), 1 its half's front, 2 the enemy's nearest unclaimed
--           stars, 3 anywhere
--   worlds  { dead, mineral, life, colony, fortified colony, mine,
--           fortified mine }: the worlds dealt onto its half, one per star
--           (colonies and mines start owned)
sc1.missions = {
	first_encounter = {
		maps = {
			"2p_SC1_First_Encounter_1", "2p_SC1_First_Encounter_2",
			"2p_SC1_First_Encounter_3", "2p_SC1_First_Encounter_4",
		},
		{   -- side 1, the Hierarchy
			ships = { { "SC_Spathi_Eluder", 0 }, { "SC_Androsynth_Guardian", 0 }, { "SC_Ilwrath_Avenger", 0 } },
			worlds = { 0, 6, 6, 1, 0, 1, 0 },
		},
		{   -- side 2, the Alliance
			ships = { { "SC_Mmrnmhrm_XForm", 0 }, { "SC_Arilou_Skiff", 0 }, { "SC_Earthling_Cruiser", 0 } },
			worlds = { 0, 6, 6, 1, 0, 1, 0 },
		},
	},
}

-- SC1's world deck, in the order it counts through the cards when drawing
-- one: { index in worlds, planet type, owned }
local deck = {
	{ 1, "d" }, { 3, "l" }, { 2, "m" }, { 4, "l", true }, { 6, "m", true },
	{ 5, "l", true }, { 7, "m", true },
}

local CENTRE, FRONT = 95, 47   -- SC1: the centre star's x; a side's front

function sc1.setup(mission_id)
	local mission = sc1.missions[mission_id]
	local name = mission.maps[mathx.random(#mission.maps)]
	local path = "~add-ons/Star_Control_TC/maps/" .. name
	local data = filesystem.read_file(path .. ".map")
	local stars = wesnoth.dofile(path .. ".lua")
	-- park the starbases in the corner first: a smaller map would drop
	-- units that end up off it
	for i, u in ipairs(wesnoth.units.find_on_map {}) do u:to_map(i, 1) end
	wesnoth.wml_actions.replace_map { map = data, expand = true, shrink = true }

	-- every star, counted from each side's far end toward the enemy's;
	-- the Hierarchy's half is SC1's low x
	local walk = { {}, {} }
	for i, s in ipairs(stars) do
		local star = { x = s[1], y = s[2], sc1x = s[3], index = i }
		walk[1][i], walk[2][i] = star, star
	end
	table.sort(walk[1], function(a, b) return a.sc1x < b.sc1x end)
	table.sort(walk[2], function(a, b) return a.sc1x > b.sc1x end)

	-- deal the worlds: one card per star, drawn at random from the side's deck
	local count, back, front, unowned = {}, { 0, 0 }, { 0, 0 }, {}
	local owner = {}   -- star -> side, for worlds owned or claimed
	for side = 1, 2 do
		local left = 0
		local cards = {}
		for i, n in ipairs(mission[side].worlds) do
			cards[i] = n
			left = left + n
		end
		count[side], unowned[side] = left, left
		for k = 1, count[side] do
			local star = walk[side][k]
			if math.abs(star.sc1x - CENTRE) < FRONT then
				front[side] = front[side] + 1
			else
				back[side] = back[side] + 1
			end
			local r = mathx.random(left) - 1
			left = left - 1
			for _, card in ipairs(deck) do
				r = r - cards[card[1]]
				if r < 0 then
					cards[card[1]] = cards[card[1]] - 1
					star.type, star.improved = card[2], card[3]
					if card[3] then
						owner[star] = side
						unowned[side] = unowned[side] - 1
					end
					break
				end
			end
		end
	end
	for _, star in ipairs(walk[1]) do
		wesnoth.wml_actions.terrain {
			x = star.x, y = star.y, layer = "overlay", terrain = "^Vy" .. (star.type or "d"),
		}
		wesnoth.map.set_owner(star.x, star.y, star.improved and owner[star] or 0, false)
	end

	-- the starbases: north for the Hierarchy, south for the Alliance
	local keeps = wesnoth.map.find { terrain = "Yk" }
	table.sort(keeps, function(a, b) return a[2] < b[2] end)
	local home = { keeps[1], keeps[#keeps] }
	local facing = { "s", "n" }

	-- a random star of walk[side][base + 1 .. base + range] the enemy
	-- doesn't own (SC1 rerolls those), which the side then claims unless a
	-- world there is improved or an enemy ship is there
	local ships_at = {}
	for _, star in ipairs(walk[1]) do ships_at[star] = {} end
	local function place(side, base, range)
		local options = {}
		for k = base + 1, base + math.max(range, 1) do
			local star = walk[side][k]
			if star and owner[star] ~= 3 - side then options[#options + 1] = star end
		end
		local star = #options > 0 and options[mathx.random(#options)] or walk[side][1]
		local was_own = owner[star] == side
		if not star.improved and not ships_at[star][3 - side] then owner[star] = side end
		return star, was_own
	end
	local function ship(side, type, star)
		ships_at[star][side] = true
		local u = wesnoth.units.create { type = type, side = side, facing = facing[side] }
		-- one ship to a hex: more at one star wait beside it
		local x, y = wesnoth.paths.find_vacant_hex(star.x, star.y, u)
		u:to_map(x, y)
	end

	for side = 1, 2 do
		local k = home[side]
		for _, u in ipairs(wesnoth.units.find_on_map { side = side, canrecruit = true }) do
			u:to_map(k[1], k[2])
			u.facing = facing[side]
		end
		-- SC1 always puts the starbase on the star farthest from the
		-- centre; its keep is beside that star
		local _, was_own = place(side, 0, 1)
		if not was_own then unowned[side] = unowned[side] - 1 end
		for _, s in ipairs(mission[side].ships) do
			if s[2] <= 1 then
				local base, range = 0, back[side]
				if s[2] == 1 then base, range = back[side], front[side] end
				if range == 0 then base, range = 0, back[side] > 0 and back[side] or front[side] end
				local star, own = place(side, base, range)
				if not own then unowned[side] = unowned[side] - 1 end
				ship(side, s[1], star)
			end
		end
	end
	for side = 1, 2 do
		for _, s in ipairs(mission[side].ships) do
			if s[2] >= 2 then
				local base, range = 0, #stars
				if s[2] == 2 then
					-- the enemy stars nearest the middle, as many as the
					-- enemy has unclaimed
					base, range = count[side], unowned[3 - side]
					if range == 0 then
						range = front[side] > 0 and front[side] or back[side]
						base = count[side] - range
					end
				end
				ship(side, s[1], (place(side, base, range)))
			end
		end
	end
end
