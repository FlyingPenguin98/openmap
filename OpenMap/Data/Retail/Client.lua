-- Which client this toc is for: its data is in Data\Retail and its textures in Media\Textures\Retail
-- (Core.lua's ns.Media.tex). Each client's toc loads its own Client.lua first.
-- Written by hand (not generated): what about retail's maps the map code can't read from the game.

local _, ns = ...
ns.Client = "Retail"

ns.ClientMaps = {
	-- Retail's Azeroth holds twelve continents, so a zone is about half as wide on it as on WoW Forever's
	-- (Elwynn Forest: 0.033 of the world's width, against 0.078): the layers' fades, set by how much of
	-- the world is in view, go by twice the zoom (WorldMap.lua's DetailK), so each comes in on a zone
	-- the size it does there
	zoom = 2,
	-- the cities under the surface, whose minimap shows the surface (Stitch.lua): Undercity, Ironforge
	underground = { [90] = true, [87] = true },
	cityFadeOf = {},            -- (no city of retail's comes in sooner than the rest: Stitch.lua's CITY_FADE_OF)
	-- Retail's world and continent maps are painted whole: their art paints its own sea and every coast. So
	-- the stitched map is that art as it is (Stitch.lua): no sea of OpenMap's under it (sea = false: the
	-- world and continent art stay as Blizzard painted them, never muted to it), and the world and continent
	-- art drawn only near the view (cullBackdrop: thousands of tiles at 3840 x 2560). Its zone maps are as
	-- WoW Forever's: blank parchment, painted by their explored-area pieces (Reveal.lua)
	sea = false,
	seaColor = { 0.52, 0.39, 0.16 },   -- (under everything: the world art's parchment, near its torn edge)
	-- (past the world art's edges its parchment runs on, and the art shows right up to its burnt edge:
	-- Territories.lua's ns.MapPaperOut and MapBackLand\947, territory.py)
	cullBackdrop = true,
	-- the zones come in where the continents' art runs out of pixels, as on WoW Forever (Stitch.lua's
	-- DETAIL_FADE, in the zoom above), but with no faint hint of them before: retail's continents' art
	-- carries the mid zooms by itself, and the hint would load every zone's art in view from much further out
	detailHint = false,
	-- ... and on each continent where its own art runs out: its continent maps are drawn at very different
	-- resolutions (Pandaria's 1002 px wide over a fifth of the world, the Dragon Isles' 3840 px over as
	-- much), so each continent's zones fade in by DETAIL_FADE times its art's px per world unit over this
	-- (the Eastern Kingdoms', where DETAIL_FADE fits): sooner on Pandaria, later on Quel'Thalas, and a zone
	-- not come in yet isn't drawn (or loaded) at all. Over a wider span than WoW Forever's: retail's zone
	-- maps are drawn in many hands, and a slow crossfade hides where one style gives way to the next
	detailDensity = 2.5,
	detailFade = { 3, 5.5 },
	-- (only the art near the view is drawn: within this much of the view's size round it, less than WoW
	-- Forever's 0.35; retail's newer zones are 150 tiles each)
	cullMargin = 0.2,
	-- townsfolk (vendors, trainers, rares) come from Questie's database, and Questie is classic's: the menu
	-- leaves them out (Panel.lua)
	townsfolk = false,
}
