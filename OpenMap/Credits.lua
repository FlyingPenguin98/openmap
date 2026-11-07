--------------------------------------------------------------------------------
-- Who has made OpenMap: What's new's Credits page (News.lua). Each group is a heading and its
-- people: { name, what they made (through L: it's translated) }. A contribution adds its line here,
-- under the name you go by on GitHub or CurseForge (never a real name you haven't given us), in the
-- same change that brings it.
--------------------------------------------------------------------------------

local _, ns = ...
local L = ns.L

ns.Credits = {
	{ L["Made by"], {
		{ "Ji" },
	} },
	{ L["Maps painted by hand"], {
		{ "Santiago Reyes", L["Hand painted custom art for OpenMap including the sea elements, blank land between zones, and his maps of WoW Forever dungeons."] },
	} },
	{ L["Programming"], {   -- (not "Code": that's the Pins code button's word)
		{ "Ironship", L["the map in combat, RareScanner's icons over the map and other map addons' pins"] },
		{ "C-Clymer", L["how the map reopens, and middle-click to center on you"] },
		{ "RADD95", L["dungeon and cave maps in every language (they showed green on some languages' clients)"] },
	} },
	{ L["Map art"], {
		{ "Blizzard Entertainment", L["the map art is the game's own"] },
	} },
	{ L["Libraries"], {
		{ "Ace3", "AceConfig-3.0, AceGUI-3.0" },
		{ "CallbackHandler-1.0, LibStub" },
	} },
	{ L["Translations"], {
		{ L["If a word reads wrong in your language, say so on CurseForge: it's fixed for the next version."] },
	} },
	{ L["Reports and ideas"], {
		{ L["Everyone who reports problems and ideas on CurseForge."] },
	} },
}
