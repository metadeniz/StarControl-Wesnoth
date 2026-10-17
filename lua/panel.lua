-- The animation box in the sidebar above End Turn (themes/sc-theme.cfg),
-- with a caption line under it.
--
-- The engine calls the report_clock and report_battery reports every frame
-- and redraws them whenever what they return changes, so picking the frame
-- from the clock animates them. The box shows a scene while one plays
-- (sc.panel_play, e.g. "starbase destroyed"), and otherwise the ship under
-- the mouse (or the selected one) turning through its six facings.
--
-- Display only: nothing here touches the game state, so it can't go out of
-- sync between players.

local FACINGS = { "n", "ne", "se", "s", "sw", "nw" }
local FRAME_MS = 150
-- A transparent canvas the size of the box, to centre each frame on
local BOX = "misc/sc-panel-box.png"
local BOX_W, BOX_H = 168, 76

local function centred(img)
	local w, h = filesystem.image_size(img)
	return string.format("%s~BLIT(%s,%d,%d)", BOX, img,
		math.max(0, (BOX_W - w) // 2), math.max(0, (BOX_H - h) // 2))
end

-- unit type id -> list of facing images, or false when the type has none
local frames_of = {}

local function type_frames(type_id)
	local frames = frames_of[type_id]
	if frames == nil then
		frames = false
		local ut = wesnoth.unit_types[type_id]
		local base = ut and ut.__cfg.image
		base = base and base:match("^(.-)%.png$")
		if base and filesystem.have_asset(filesystem.asset_type.IMAGE, base .. "-n.png") then
			frames = {}
			for i, f in ipairs(FACINGS) do
				frames[i] = centred(base .. "-" .. f .. ".png")
			end
		end
		frames_of[type_id] = frames
	end
	return frames
end

-- The scene playing now: { start = ms, frames = { {image, until_ms}, ... },
-- caption = text }, or nil
local scene

-- Plays a scene in the box, with the caption under it, and waits until it
-- is over. frames: list of { image, ms } shown in turn.
function sc.panel_play(frames, caption)
	local s, t = { frames = {}, caption = caption }, 0
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
	if scene then
		return { { "element", { image = scene_frame() } } }
	end
	local u = wesnoth.interface.get_displayed_unit()
	local frames = u and type_frames(u.type)
	if not frames then return {} end
	local i = (wesnoth.ms_since_init() // FRAME_MS) % #frames + 1
	return { { "element", { image = frames[i] .. "~TC(" .. u.side .. ",magenta)" } } }
end

wesnoth.interface.game_display.report_battery = function()
	if not scene then return {} end
	return { { "element", { text = scene.caption } } }
end
