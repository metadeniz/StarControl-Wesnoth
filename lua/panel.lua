-- The animation box in the sidebar above End Turn (themes/sc-theme.cfg),
-- with a caption line under it.
--
-- The engine calls the report_clock and report_battery reports every frame
-- and redraws them whenever what they return changes, so picking the frame
-- from the clock animates them. The box shows a scene while one plays
-- (sc.panel_play, e.g. "starbase destroyed"), and is empty otherwise.
--
-- Display only: nothing here touches the game state, so it can't go out of
-- sync between players.

-- A transparent canvas the size of the box, to centre each frame on
local BOX = "misc/sc-panel-box.png"
local BOX_W, BOX_H = 168, 76

local function centred(img)
	local w, h = filesystem.image_size(img)
	return string.format("%s~BLIT(%s,%d,%d)", BOX, img,
		math.max(0, (BOX_W - w) // 2), math.max(0, (BOX_H - h) // 2))
end

-- The sidebar only draws left-aligned text, so each caption line is centred
-- by putting a transparent spacer of the right width in front of it. Line
-- widths come from the advance widths of the sidebar font (Lato Regular at
-- the caption's size, 13), characters 32-126, measured with PIL and checked
-- against a 1.16 screenshot; other characters count as 7 pixels.
local CAPTION_W = BOX_W
local CHAR_W = {
	3.2, 3.4, 4.7, 7.3, 7.3, 10.1, 9.0, 2.6, 3.4, 3.4, 5.4, 7.3, 2.9, 4.7, 3.0, 5.7,
	7.3, 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, 7.3, 3.2, 3.3, 7.3, 7.3, 7.3, 5.6,
	10.5, 8.5, 8.1, 8.4, 9.6, 7.3, 7.1, 9.2, 9.6, 3.5, 5.3, 8.3, 6.5, 11.7, 9.6, 10.1,
	7.6, 10.1, 7.9, 6.8, 7.4, 9.3, 8.5, 13.0, 8.2, 7.9, 7.6, 3.9, 5.7, 3.9, 7.3, 5.8,
	5.0, 6.3, 7.0, 6.0, 7.0, 6.7, 4.4, 6.5, 7.0, 3.0, 3.0, 6.4, 3.0, 10.4, 7.0, 7.1,
	7.1, 7.0, 4.6, 5.5, 4.5, 7.0, 6.5, 9.9, 6.3, 6.5, 5.7, 3.8, 3.2, 3.8, 7.3,
}

local function line_width(line)
	local w = 0
	for _, c in utf8.codes(line) do
		w = w + (CHAR_W[c - 31] or 7)
	end
	return w
end

local function caption_elements(caption)
	local elements, lines = {}, {}
	for line in (tostring(caption) .. "\n"):gmatch("(.-)\n") do
		lines[#lines + 1] = line
	end
	for i, line in ipairs(lines) do
		local pad = math.floor((CAPTION_W - line_width(line)) / 2)
		if pad > 0 then
			elements[#elements + 1] = { "element", { image = string.format("%s~CROP(0,0,%d,1)", BOX, pad) } }
		end
		elements[#elements + 1] = { "element", { text = i < #lines and line .. "\n" or line } }
	end
	return elements
end

-- The scene playing now: { start = ms, frames = { {image, until_ms}, ... },
-- caption_elements = report elements }, or nil
local scene

-- Plays a scene in the box, with the caption under it, and waits until it
-- is over. frames: list of { image, ms } shown in turn.
function sc.panel_play(frames, caption)
	local s, t = { frames = {}, caption_elements = caption_elements(caption) }, 0
	for i, f in ipairs(frames) do
		t = t + f[2]
		s.frames[i] = { centred(f[1]), t }
	end
	s.start = wesnoth.ms_since_init()
	scene = s
	wesnoth.interface.delay(t)
	scene = nil
end

local function scene_frame()
	local elapsed = wesnoth.ms_since_init() - scene.start
	for _, f in ipairs(scene.frames) do
		if elapsed < f[2] then return f[1] end
	end
	return scene.frames[#scene.frames][1]
end

wesnoth.interface.game_display.report_clock = function()
	if not scene then return {} end
	return { { "element", { image = scene_frame() } } }
end

wesnoth.interface.game_display.report_battery = function()
	if not scene then return {} end
	return scene.caption_elements
end
