-- The animation box in the sidebar above End Turn (themes/sc-theme.cfg).
-- The engine calls this report every frame and redraws the box whenever the
-- returned image changes, so picking the frame from the clock animates it.
-- Prototype: the ship under the mouse (or the selected one) turns through
-- its six facings.

local FACINGS = { "n", "ne", "se", "s", "sw", "nw" }
local FRAME_MS = 150
-- A transparent canvas the size of the box, to centre each frame on
local BOX = "misc/sc-panel-box.png"
local BOX_W, BOX_H = 168, 120

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
				local img = base .. "-" .. f .. ".png"
				local w, h = filesystem.image_size(img)
				frames[i] = string.format("%s~BLIT(%s,%d,%d)", BOX, img,
					math.max(0, (BOX_W - w) // 2), math.max(0, (BOX_H - h) // 2))
			end
		end
		frames_of[type_id] = frames
	end
	return frames
end

wesnoth.interface.game_display.report_clock = function()
	local u = wesnoth.interface.get_displayed_unit()
	local frames = u and type_frames(u.type)
	if not frames then return {} end
	local i = (wesnoth.ms_since_init() // FRAME_MS) % #frames + 1
	return { { "element", { image = frames[i] .. "~TC(" .. u.side .. ",magenta)" } } }
end
