#!/usr/bin/env lua5.4
-- Sample First Encounter maps from lua/sc1_map.lua, the builder the game
-- runs at the start of every SC1 mission game, to look at outside it:
--
--     lua5.4 tools/sc1_map_preview.lua OUT_DIR SEED [SEED ...]
--
-- writes OUT_DIR/sc1-SEED.map for each SC1 seed (0-65535), with the planets
-- First Encounter's (a colony and a mine in each half, the rest half life,
-- half mineral). Run it from the add-on's directory.

local M = dofile("lua/sc1_map.lua")
local out = arg[1]
for k = 2, #arg do
	local seed = tonumber(arg[k])
	math.randomseed(seed)
	local t = os.clock()
	local data, stars = M.build(seed, 14, 14, math.random)
	-- deal First Encounter's worlds onto each half
	for _, side in ipairs { "B", "A" } do
		local deck = { "l", "m" }
		for _ = 1, 6 do deck[#deck + 1] = "l"; deck[#deck + 1] = "m" end
		local half = {}
		for _, s in ipairs(stars) do
			if s[4] == side then half[#half + 1] = s end
		end
		for i, s in ipairs(half) do
			local j = math.random(i, #deck)
			deck[i], deck[j] = deck[j], deck[i]
			s.type = deck[i] or "d"
		end
	end
	local lines = {}
	for line in data:gmatch("[^\n]+") do lines[#lines + 1] = line end
	for _, s in ipairs(stars) do
		local cells = {}
		for c in (lines[s[2] + 1] .. ","):gmatch("%s*([^,]*),") do cells[#cells + 1] = c end
		cells[s[1] + 1] = "Ys^Vy" .. s.type
		lines[s[2] + 1] = table.concat(cells, ", ")
	end
	local f = assert(io.open(out .. "/sc1-" .. seed .. ".map", "w"))
	f:write(table.concat(lines, "\n"), "\n")
	f:close()
	print(string.format("%s/sc1-%d.map: %d columns x %d rows, %.2f s", out, seed,
		#lines[1]:gsub("[^,]", "") - 1, #lines - 2, os.clock() - t))
end
