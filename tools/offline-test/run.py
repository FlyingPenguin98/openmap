"""Offline load test: runs OpenMap's toc in a stubbed WoW environment (Lua 5.1).

Usage:  python tools/offline-test/run.py [plain|combat|secret|pad|padmap|padview]
        (OPENMAP_CLIENT=retail for retail's toc; tools/clients.py)
Needs:  pip install lupa

Loads every file of the client's toc, fires ADDON_LOADED / PLAYER_LOGIN / combat events, runs
timers, builds + validates the options table and calls every option getter,
then runs the slash commands. "secret" makes combat values behave like the
client's secret values; "pad" has the game's Gamepad UI on and the controller view
(padView) off, where OpenMap must leave the map alone; "padmap" the same with Options' padMap turned on, which
gives OpenMap the map then; "padview" the same with padView chosen at login, which
leaves Blizzard's map to Blizzard and draws OpenMap's over it (PadView.lua). Exit code 1 on any error. (The stub has no real world
map, so the stitched map itself isn't built here: check that with
tools/map-preview and in game.) Stubs can't catch nil-tests on secrets or layout problems: always
confirm in game.
"""
import os, re, sys
import lupa.lua51 as lupa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "OpenMap"))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients

def toc_files():
    out = []
    for line in open(clients.toc(), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # (a file's inline directives, [AllowLoadTextLocale deDE] ...: every file is loaded here all the
        # same, so each is checked; a translation's own file returns early in another language)
        while re.search(r"\s*\[[^\]]*\]\s*$", line): line = re.sub(r"\s*\[[^\]]*\]\s*$", "", line)
        out.extend(expand(line.replace("\\", os.sep)))
    return out

def expand(rel):
    path = os.path.join(ROOT, rel)
    if rel.endswith(".xml"):
        base = os.path.dirname(rel)
        files = []
        for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', re.sub(r'<!--.*?-->', '', open(path, encoding="utf-8").read(), flags=re.S)):
            files.extend(expand(os.path.join(base, m.group(2).replace("\\", os.sep))))
        return files
    return [rel]

L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute(open(os.path.join(HERE, "stub.lua"), encoding="utf-8").read())
ns = L.eval("{}")
load = L.eval("""function(src, name, ns)
    local fn, err = loadstring(src, "@" .. name)
    if not fn then return false, err end
    local ok, e = xpcall(function() return fn("OpenMap", ns) end, function(m) return tostring(m) .. "\\n" .. debug.traceback() end)
    return ok, e
end""")

failed = False
for rel in toc_files():
    if not os.path.exists(os.path.join(ROOT, rel)):
        print("SKIP (missing)", rel); continue
    src = open(os.path.join(ROOT, rel), encoding="utf-8-sig").read()
    ok, err = load(src, rel, ns)
    if not ok:
        failed = True
        print("LOAD ERROR", rel, "\n", err)

steps = L.eval("""function(ns, scenario)
    -- (the game's Gamepad UI on: OpenMap must leave Blizzard's map alone, WorldMap.lua's OnEnable)
    local pad = scenario == "pad" or scenario == "padmap" or scenario == "padview"
    if pad then InputUtil = { IsGamepadUIEnabled = function() return true end } end
    if scenario == "padview" then OpenMapDB = { worldmap = { padView = true } } end
    -- ("pad", "padmap": the controller view turned off, OpenMap's map left to Blizzard, as before it)
    if scenario == "pad" or scenario == "padmap" then OpenMapDB = { worldmap = { padView = false } } end
    FireEvent("ADDON_LOADED", "OpenMap")
    FireEvent("PLAYER_LOGIN")
    FireEvent("PLAYER_ENTERING_WORLD", true, false)
    RunTimers(3)
    if scenario == "secret" then ENABLE_SECRETS() end
    if scenario == "combat" or scenario == "secret" then
        IN_COMBAT = true
        FireEvent("PLAYER_REGEN_DISABLED")
        RunTimers(3)
        IN_COMBAT = false
        FireEvent("PLAYER_REGEN_ENABLED")
        RunTimers(3)
    end
    local ACR = LibStub("AceConfigRegistry-3.0")
    local ok, err = pcall(function() return ACR:GetOptionsTable("OpenMap", "dialog", "AceGUI-3.0") end)
    if not ok then ERRORS[#ERRORS + 1] = "options: " .. tostring(err) end
    if ok then WalkOptions(err, {}, {}) end
    for _, cmd in ipairs({ "status", "paint", "news" }) do
        local ok2, e2 = pcall(SlashCmdList.OPENMAP, cmd)
        if not ok2 then ERRORS[#ERRORS + 1] = "slash " .. cmd .. ": " .. tostring(e2) end
    end
    RunTimers(2)
    -- your pins hidden and back (the menu's Pins, right-clicked)
    if not pad and ns.modules.worldmap.SetPinsHidden then
        local m = ns.modules.worldmap
        local ok5, e5 = pcall(function() m.SetPinsHidden(true) m.SetPinsHidden(false) end)
        if not ok5 then ERRORS[#ERRORS + 1] = "pins hidden: " .. tostring(e5) end
        if m.db.pinsHidden then ERRORS[#ERRORS + 1] = "pins hidden: they didn't come back" end
    end
    -- friends and guild (Friends.lua): places heard from the guild, a stranger's whisper, a malformed
    -- message, one with a secret text; sharing turned on and off again
    if not pad and ns.modules.worldmap.RefreshFriends then
        local m = ns.modules.worldmap
        local ok6, e6 = pcall(function()
            IsInGuild = function() return true end
            FireEvent("CHAT_MSG_ADDON", "OpenMapLoc", "L1\t1429\t0.5\t0.5\tMAGE\t20", "GUILD", "Guildie-Forever")
            FireEvent("CHAT_MSG_ADDON", "OpenMapLoc", "L1\tnope", "GUILD", "Other-Forever")
            FireEvent("CHAT_MSG_ADDON", "OpenMapLoc", "H1", "WHISPER", "Stranger-Forever")
            FireEvent("CHAT_MSG_ADDON", "OpenMapLoc", Secret("L1\t1429\t0.5\t0.5"), "GUILD", "Hidden-Forever")
            FireEvent("CHAT_MSG_ADDON", "OpenMapLoc", "L0", "GUILD", "Guildie-Forever")
            FireEvent("GUILD_ROSTER_UPDATE")
            FireEvent("FRIENDLIST_UPDATE")
            m.db.friendsShare = true
            m.RefreshFriends()
            RunTimers(15)
            m.db.friendsShare = false
            m.RefreshFriends()
            RunTimers(3)
        end)
        if not ok6 then ERRORS[#ERRORS + 1] = "friends: " .. tostring(e6) end
    end
    if scenario == "pad" then
        -- (Setup never ran: it would have said the stub's map isn't the expected kind)
        local m = ns.modules.worldmap
        local touched = false
        for _, line in ipairs(LOG) do
            if tostring(line):find("isn't the expected kind", 1, true) then touched = true end
        end
        if m.enabled or not m.padWaits or touched then
            ERRORS[#ERRORS + 1] = "pad: OpenMap set itself up on the map with the Gamepad UI on"
        end
        -- swapped to mouse and keyboard: OpenMap sets up then
        InputUtil.IsGamepadUIEnabled = function() return false end
        FireEvent("INPUT_DEVICE_INTERFACE_TRANSITION", 0, 1)
        RunTimers(2)
        if not m.enabled or m.padWaits then ERRORS[#ERRORS + 1] = "pad: OpenMap didn't start when the Gamepad UI went off" end
    end
    if scenario == "padview" then
        -- (OpenMap's usual map waits; the controller view sets up on a stand-in for Blizzard's map,
        -- shows and hides with it, and A and X step in and out, without touching OpenMap's usual map)
        local m = ns.modules.worldmap
        if m.enabled or not m.padWaits then ERRORS[#ERRORS + 1] = "padview: OpenMap took Blizzard's map" end
        local ok7, e7 = pcall(function()
            local wm = CreateFrame("Frame", "WorldMapFrame", UIParent)
            wm.ScrollContainer = CreateFrame("Frame", nil, wm)
            wm.ScrollContainer.Child = CreateFrame("Frame", nil, wm.ScrollContainer)
            wm.GetCanvas = function() return wm.ScrollContainer.Child end
            wm.IsCanvasGamepadFocus = function() return true end
            wm.NavigateToGamepadCursor = function() end
            wm.NavigateToParentMap = function() end
            m.StartPadView()
            wm:Show()
            RunTimers(2)
            wm:NavigateToGamepadCursor()
            wm:NavigateToParentMap()
            SlashCmdList.OPENMAP("padview")
            -- (the menu on it, and a setting changed: the stub can't build the art, so the view says it's on)
            local was = m.PadViewOn
            m.PadViewOn = function() return true end
            MinimalSliderWithSteppersMixin = false  -- (the stub's template has no slider: the menu's own then)
            m:SetupPanel(wm)
            m:SetupPins(wm)
            m:SetupSketch(wm)
            m:BuildSketch()
            m:TogglePins(true)
            m:TogglePins(false)
            m:ToggleSketch(true)
            m.PadSketchPress()
            m:ToggleSketch(false)
            m:SetupReport(wm)
            m:ToggleReport(true)
            m:ToggleReport(false)
            m.PadQuestiePaths(true)
            m.PadQuestiePaths(false)
            m.RefreshGroup()
            m:OpenMenu()
            m:Refresh()
            m:FindMe()
            m.PadViewOn = was
            wm:Hide()
            InputUtil.IsGamepadUIEnabled = function() return false end
            FireEvent("INPUT_DEVICE_INTERFACE_TRANSITION", 0, 1)
            RunTimers(2)
        end)
        if not ok7 then ERRORS[#ERRORS + 1] = "padview: " .. tostring(e7) end
    end
    if scenario == "padmap" then
        -- (Options' padMap turned on while OpenMap waits: its map at once, the Gamepad UI still on)
        local m = ns.modules.worldmap
        if m.enabled or not m.padWaits then ERRORS[#ERRORS + 1] = "padmap: OpenMap didn't wait for the Gamepad UI first" end
        m.db.padMap = true
        local ok3, e3 = pcall(m.SetPadMap, true)
        if not ok3 then ERRORS[#ERRORS + 1] = "padmap: " .. tostring(e3) end
        RunTimers(2)
        if not m.enabled or m.padWaits then ERRORS[#ERRORS + 1] = "padmap: OpenMap didn't take the map with padMap on" end
        if m.PadKeys then
            local ok4, e4 = pcall(m.PadKeys)
            if not ok4 then ERRORS[#ERRORS + 1] = "padmap: the keys: " .. tostring(e4) end
        end
    end
end""")

L.execute(r'''
function WalkOptions(node, path, inherited)
    local inh = {}
    for k, v in pairs(inherited) do inh[k] = v end
    for _, k in ipairs({ "get", "set", "disabled", "hidden", "handler" }) do
        if node[k] ~= nil then inh[k] = node[k] end
    end
    local info = { options = node, option = node, type = node.type, handler = inh.handler, uiType = "dialog", uiName = "AceGUI-3.0", appName = "OpenMap" }
    for i, p in ipairs(path) do info[i] = p end
    local function call(field, ...)
        local v = node[field]
        if type(v) == "function" then
            local ok, err = pcall(v, info, ...)
            if not ok then ERRORS[#ERRORS + 1] = "option " .. table.concat(path, ".") .. " " .. field .. ": " .. tostring(err) end
            return err
        end
        return v
    end
    call("name") call("desc")
    local function callInh(field, ...)
        local v = inh[field]
        if type(v) == "function" then
            local ok, err = pcall(v, info, ...)
            if not ok then ERRORS[#ERRORS + 1] = "option " .. table.concat(path, ".") .. " " .. field .. ": " .. tostring(err) end
        end
    end
    callInh("hidden") callInh("disabled")
    local values = call("values")
    if node.type and node.type ~= "group" and node.type ~= "header" and node.type ~= "description" and node.type ~= "execute" then
        if node.type == "multiselect" and type(values) == "table" then
            for key in pairs(values) do callInh("get", key) end
        else
            callInh("get")
        end
    end
    if node.args then
        for k, child in pairs(node.args) do
            local p = { unpack(path) } p[#p + 1] = k
            WalkOptions(child, p, inh)
        end
    end
end
''')

steps(ns, sys.argv[1] if len(sys.argv) > 1 else "combat")
print("INSPECT", L.eval("""(function()
  local m = OpenMap.modules.worldmap
  local P = OpenMap.MapPlaces or {}
  local reveal = 0 for _ in pairs(OpenMap.MapReveal or {}) do reveal = reveal + 1 end
  return "enabled=" .. tostring(m and m.enabled) .. " revealArts=" .. reveal .. " instances=" .. #(P.instances or {}) .. " docks=" .. #(P.transports or {})
end)()"""))
errs = L.eval("ERRORS")
n = len(errs)
seen = set()
for i in range(1, n + 1):
    e = errs[i]
    key = e.split("\n")[0]
    if key in seen: continue
    seen.add(key)
    print("ERROR:", e[:1500]); print("-" * 60)
logs = L.eval("LOG")
print("log lines:", len(logs), "| errors:", n, "| unique:", len(seen))
for i in range(1, min(len(logs), 40) + 1):
    print("  LOG:", logs[i])
sys.exit(1 if (failed or n) else 0)
