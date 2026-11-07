"""Friends and guild on the map (Friends.lua) in Lua 5.1: python -P tools/offline-test/friends.py.

What's heard (from whom, on which channel) and what's sent (when, to whom), against a stubbed client:
the guild roster, a friends list, the map's pins, the addon-message channel.
"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"

STUB = r"""
NOW, sent, events, frames, pins, badges = 1000, {}, {}, {}, {}, {}
inInstance, inGuild, here, secretText = false, true, { 1429, 0.5, 0.5 }, nil
guild = { { "Guildie-Forever", 30, "Elwynn Forest", true, "MAGE" }, { "Offline-Forever", 20, "Duskwood", false, "ROGUE" } }
friendList = { { name = "Pal", connected = true, level = 40, area = "Westfall", className = "Hunter" },
	{ name = "Gone", connected = false, level = 10, area = "Westfall", className = "Hunter" } }

local function Frame()
	local f = { scripts = {}, shown = true }
	function f:SetScript(k, fn) self.scripts[k] = fn end
	function f:HookScript(k, fn) self.scripts[k] = fn end
	function f:Hide() self.shown = false end
	function f:Show() self.shown = true end
	function f:IsShown() return self.shown end
	function f:CreateFontString() return { SetPoint = function() end, SetText = function(s, t) s.text = t end } end
	frames[#frames + 1] = f
	return f
end
CreateFrame = function() return Frame() end
function Run(seconds)
	-- every frame's OnUpdate, a tenth of a second at a time, and the timers due
	for _ = 1, seconds * 10 do
		NOW = NOW + 0.1
		for _, f in ipairs(frames) do if f.shown and f.scripts.OnUpdate then f.scripts.OnUpdate(f, 0.1) end end
		for _, t in ipairs(timers) do
			if not t.done and NOW >= t.at then
				t.fn()
				if t.every then t.at = NOW + t.every else t.done = true end
			end
		end
	end
end
timers = {}
C_Timer = { After = function(d, fn) timers[#timers + 1] = { at = NOW + d, fn = fn } end,
	NewTicker = function(d, fn) timers[#timers + 1] = { at = NOW + d, fn = fn, every = d } end }
GetTime = function() return NOW end
geterrorhandler = function() return error end
strsplit = function(sep, s, n)
	local out = {}
	for piece in (s .. sep):gmatch("([^" .. sep .. "]*)" .. sep) do out[#out + 1] = piece end
	return unpack(out)
end
tinsert, tremove, wipe = table.insert, table.remove, function(t) for k in pairs(t) do t[k] = nil end return t end
GetNormalizedRealmName = function() return "Forever" end
UnitName = function() return "Me" end
UnitClass = function() return "Warrior", "WARRIOR" end
UnitLevel = function() return 25 end
IsInGroup = function() return false end
IsInInstance = function() return inInstance, inInstance and "party" or "none" end
IsInGuild = function() return inGuild end
GetNumGuildMembers = function() return #guild end
GetGuildRosterInfo = function(i)
	local g = guild[i]
	return g[1], "", 0, g[2], "", g[3], "", "", g[4], 0, g[5]
end
C_FriendList = { GetNumFriends = function() return #friendList end, GetFriendInfoByIndex = function(i) return friendList[i] end }
LOCALIZED_CLASS_NAMES_MALE = { HUNTER = "Hunter", MAGE = "Mage" }
C_ChatInfo = { RegisterAddonMessagePrefix = function() end,
	SendAddonMessage = function(prefix, text, channel, target) sent[#sent + 1] = { prefix = prefix, text = text, channel = channel, target = target } end }
Enum = { UIMapType = { Zone = 3 } }
local zones = { [1429] = "Elwynn Forest", [1436] = "Westfall", [1431] = "Duskwood" }
C_Map = {
	GetBestMapForUnit = function() return here and here[1] end,
	GetPlayerMapPosition = function() if here then return { x = here[2], y = here[3] } end end,
	GetMapInfo = function(id) return { name = zones[id] } end,
	GetMapChildrenInfo = function()
		local t = {}
		for id, name in pairs(zones) do t[#t + 1] = { mapID = id, name = name } end
		return t
	end,
}
GameTooltip_Hide = function() end
issecretvalue = function(v) return v == secretText and v ~= nil end

S = { WORLD = 947 }
function S.Rect(id) if id == 1429 or id == 1436 or id == 1431 then return 0.1, 0.2, 0.1, 0.2 end end
function S.IsBuilt() return true end
function S.PinSet(key) return { key = key } end
function S.ClearPinSet(set) if set.key == "friends" then wipe(pins) else wipe(badges) end end
function S.AddPin(set, u, v, look, data)
	local pin = Frame()
	pin.data = data
	if set.key == "friends" then pins[#pins + 1] = data else badges[#badges + 1] = data end
	return pin
end
mod = { defaults = {}, db = {} }
function mod.IsStitched() return true end
function mod.ToWorld(id, x, y) return x, y end
ns = { MapStitch = S, L = setmetatable({}, { __index = function(_, k) return k end }) }
function ns:GetModule() return mod end
function ns.RegisterEvent(_, event, fn) events[event] = fn end
ns.Safe = {
	IsSecret = function(v) return issecretvalue(v) end,
	Value = function(v) if issecretvalue(v) then return nil end return v end,
	XY = function(p) return p.x, p.y end,
	Call = function(fn, ...) if type(fn) ~= "function" then return nil end local ok, v = pcall(fn, ...) if ok then return v end end,
}
function Fire(event, ...) if events[event] then events[event](nil, event, ...) end end
function Sent(channel, text, target)
	local n = 0
	for _, m in ipairs(sent) do
		if m.channel == channel and (not text or m.text:sub(1, #text) == text) and (not target or m.target == target) then n = n + 1 end
	end
	return n
end
"""


class FriendsTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        src = (ROOT / "Map" / "Friends.lua").read_text(encoding="utf-8")
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", src)
        self.lua.execute("""
            for k, v in pairs(mod.defaults) do mod.db[k] = v end
            worldMap = CreateFrame()
            mod:SetupFriends(worldMap)
        """)

    def run_(self, seconds):
        self.lua.eval("Run")(seconds)

    def test_sharing_is_off_unless_turned_on(self):
        self.run_(30)
        self.assertEqual(self.lua.eval("Sent('GUILD')"), 0)

    def test_sharing_sends_to_the_guild_and_stops_with_a_goodbye(self):
        self.lua.execute("mod.db.friendsShare = true mod.RefreshFriends()")
        self.run_(1)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L1\\t1429\\t0.5000\\t0.5000\\tWARRIOR\\t25')"), 1)
        # standing still: not again for a minute; moving: after ten seconds
        self.run_(20)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L1')"), 1)
        self.lua.execute("here = { 1429, 0.6, 0.5 }")
        self.run_(3)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L1')"), 2)
        self.lua.execute("mod.db.friendsShare = false mod.RefreshFriends()")
        self.run_(1)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L0')"), 1)

    def test_nothing_from_an_instance(self):
        self.lua.execute("mod.db.friendsShare = true mod.RefreshFriends()")
        self.run_(1)
        self.lua.execute("inInstance = true")
        self.run_(5)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L0')"), 1)
        self.lua.execute("here = { 1429, 0.9, 0.9 }")
        self.run_(30)
        self.assertEqual(self.lua.eval("Sent('GUILD', 'L1')"), 1)

    def test_online_friends_get_a_hello_and_known_ones_the_place(self):
        self.run_(8)                                        # (the first scan, five seconds in)
        self.assertEqual(self.lua.eval("Sent('WHISPER', 'H1', 'Pal')"), 1)
        self.assertEqual(self.lua.eval("Sent('WHISPER', 'H1', 'Gone')"), 0)
        self.lua.execute("mod.db.friendsShare = true mod.RefreshFriends()")
        self.run_(2)
        self.assertEqual(self.lua.eval("Sent('WHISPER', 'L1', 'Pal')"), 0)   # (not known to use OpenMap yet)
        self.lua.execute("Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'H2', 'WHISPER', 'Pal')")
        self.lua.execute("here = { 1429, 0.7, 0.5 }")
        self.run_(12)
        self.assertEqual(self.lua.eval("Sent('WHISPER', 'L1', 'Pal')"), 1)

    def test_heard_places_and_badges(self):
        self.run_(8)
        self.lua.execute("""
            Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'L1\\t1429\\t0.3\\t0.4\\tMAGE\\t30', 'GUILD', 'Guildie-Forever')
            Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'L1\\t1436\\t0.3\\t0.4\\tMAGE\\t30', 'WHISPER', 'Stranger')
            Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'L1\\t9999\\t0.3\\t0.4', 'GUILD', 'Nowhere-Forever')
            Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'L1\\t1429\\t3\\t0.4', 'GUILD', 'Far-Forever')
            Fire('CHAT_MSG_ADDON', 'OpenMapLoc', 'L1\\t1429\\t0.3\\t0.4', 'GUILD', 'Me')
            worldMap:Show()
        """)
        self.lua.execute("secretText = 'L1\\t1429\\t0.1\\t0.1' Fire('CHAT_MSG_ADDON', 'OpenMapLoc', secretText, 'GUILD', 'Hidden-Forever')")
        self.run_(2)
        dots = self.lua.eval("(function() local t = {} for _, d in ipairs(pins) do t[#t + 1] = d.full end return table.concat(t, ',') end)()")
        self.assertEqual(dots, "Guildie-Forever")
        # the guildie has a dot: no badge for them; the friend in Westfall has one
        zones = self.lua.eval("(function() local t = {} for _, d in ipairs(badges) do t[#t + 1] = d.map .. ':' .. #d.people end return table.concat(t, ',') end)()")
        self.assertEqual(zones, "1436:1")
        # a dot unheard from goes; the guildie's badge comes back
        self.run_(160)
        self.assertEqual(self.lua.eval("#pins"), 0)
        self.assertIn("1429:1", self.lua.eval("(function() local t = {} for _, d in ipairs(badges) do t[#t + 1] = d.map .. ':' .. #d.people end return table.concat(t, ',') end)()"))

    def test_turned_off_nothing_on_the_map(self):
        self.run_(8)
        self.lua.execute("mod.db.friends = false worldMap:Show() mod.RefreshFriends()")
        self.run_(2)
        self.assertEqual(self.lua.eval("#badges"), 0)


if __name__ == "__main__":
    unittest.main()
