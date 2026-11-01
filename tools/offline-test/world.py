"""Offline stitch test: builds the stitched world in a stubbed client whose map (C_Map) is the
game's own tables, then sweeps the view across it (Lua 5.1).

Usage:  python -P tools/offline-test/world.py <db2 dir>      (OPENMAP_CLIENT: the client, tools/clients.py)
        <db2 dir>: the client's build's UiMap* CSVs (wago.tools), as tools/map-preview's
Needs:  pip install lupa

run.py's stub has no map, so the stitched world is never built there. Here C_Map answers from the
tables (tools/uimap.py places the maps as GetMapRectOnMap does; the map at a point is the smallest
child map whose rectangle holds it), the stitched world is built (Stitch.lua's S.Build), and the view
is swept from the whole world to the closest zoom over every continent, calling what WorldMap.lua
calls on a pan or zoom (S.SetZoom, S.SetView) and running the file loader. Any Lua error fails it.
It prints how many textures are drawn at each zoom (shown, with every frame above them shown): the
work the client does per frame, to compare between clients and before and after a change. It can't
see the art: tools/map-preview renders that.
"""
import os, sys, time
import lupa.lua51 as lupa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "OpenMap"))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients, uimap


def lua_val(v):
    if v is None: return "nil"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return repr(v)
    if isinstance(v, str): return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)): return "{" + ",".join(lua_val(x) for x in v) + "}"
    if isinstance(v, dict): return "{" + ",".join("[%s]=%s" % (lua_val(k), lua_val(x)) for k, x in v.items()) + "}"
    raise TypeError(v)


def map_data(db2):
    """the maps on Azeroth's map: { id: { name, type, parent, rect, art, files, asg } }"""
    import csv
    w = uimap.World(db2)
    tiles = {}
    for r in csv.DictReader(open(os.path.join(db2, "UiMapArtTile.csv"), encoding="utf-8")):
        if r["LayerIndex"] == "0":
            tiles.setdefault(int(r["UiMapArtID"]), {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
    out = {}
    for m, r in w.uimap.items():
        if int(r["Type"]) not in (1, 2, 3, 4, 5, 6) or not w.under_world(m) and m != uimap.WORLD: continue
        a = w.art(m)
        e = {"name": r["Name_lang"], "type": int(r["Type"]), "parent": w.parent(m), "rect": w.rect(m)}
        if a and a[0] in tiles:
            t = tiles[a[0]]
            rows, cols = max(k[0] for k in t) + 1, max(k[1] for k in t) + 1
            e["art"] = list(a[1:]) + [a[0]]
            e["files"] = [t.get((j, i), 0) for j in range(rows) for i in range(cols)]
        rows = w.assign.get(m)
        if rows:
            b = rows[0]
            e["asg"] = [int(b["MapID"])] + [float(b[k]) for k in ("UiMin_0", "UiMin_1", "UiMax_0", "UiMax_1", "Region_0", "Region_1", "Region_3", "Region_4")]
        out[m] = e
    return out


C_MAP = r'''
Enum.UIMapType = { Cosmic = 0, World = 1, Continent = 2, Zone = 3, Dungeon = 4, Micro = 5, Orphan = 6 }
CreateVector2D = function(x, y) return { x = x, y = y, GetXY = function(self) return self.x, self.y end } end
local function info(id) local m = MAPS[id] if m then return { mapID = id, name = m.name, mapType = m.type, parentMapID = m.parent } end end
local function rel(id, host)
	local a, h = MAPS[id] and MAPS[id].rect, MAPS[host] and MAPS[host].rect
	if not a or not h then return end
	local hw, hh = h[2] - h[1], h[4] - h[3]
	return (a[1] - h[1]) / hw, (a[2] - h[1]) / hw, (a[3] - h[3]) / hh, (a[4] - h[3]) / hh
end
local kids = {}
for id, m in pairs(MAPS) do kids[m.parent] = kids[m.parent] or {} table.insert(kids[m.parent], id) end
local function under(id, top) for _ = 1, 12 do if id == top then return true end local m = MAPS[id] if not m then return false end id = m.parent end return false end
C_Map = {
	GetMapInfo = info,
	GetMapArtID = function(id) return MAPS[id] and MAPS[id].art and MAPS[id].art[5] end,
	GetMapArtLayers = function(id)
		local a = MAPS[id] and MAPS[id].art
		if a then return { { layerWidth = a[1], layerHeight = a[2], tileWidth = a[3], tileHeight = a[4], minScale = 1, maxScale = 1, additionalZoomSteps = 0 } } end
	end,
	GetMapArtLayerTextures = function(id) local m = MAPS[id] return m and m.files and { unpack(m.files) } end,
	GetMapRectOnMap = function(id, host)
		if id == host then return 0, 1, 0, 1 end
		return rel(id, host)
	end,
	GetMapChildrenInfo = function(id, kind, all)
		local out = {}
		for cid, m in pairs(MAPS) do
			if cid ~= id and (kind == nil or m.type == kind) and (all and under(cid, id) or m.parent == id) then out[#out + 1] = info(cid) end
		end
		table.sort(out, function(a, b) return a.mapID < b.mapID end)
		return out
	end,
	GetMapInfoAtPosition = function(id, x, y)
		local best, area
		for _, cid in ipairs(kids[id] or {}) do
			local m = MAPS[cid]
			if m.type == 2 or m.type == 3 then
				local l, r, t, b = rel(cid, id)
				if l and x >= l and x <= r and y >= t and y <= b and (not area or (r - l) * (b - t) < area) then best, area = cid, (r - l) * (b - t) end
			end
		end
		return best and info(best)
	end,
	GetWorldPosFromMapPos = function(id, pos)
		local a = MAPS[id] and MAPS[id].asg
		if not a then return end
		local u, v = pos.x, pos.y
		local X = a[8] - (v - a[3]) / (a[5] - a[3]) * (a[8] - a[6])
		local Y = a[9] - (u - a[2]) / (a[4] - a[2]) * (a[9] - a[7])
		return a[1], CreateVector2D(X, Y)
	end,
	GetBestMapForUnit = function() return nil end,
	GetPlayerMapPosition = function() return nil end,
	GetMapLevels = function() return 10, 30 end,
	-- (a stand-in: one highlight per zone under the point, for /openmap highlights' sake)
	GetMapHighlightInfoAtPosition = function(id, x, y)
		local z = C_Map.GetMapInfoAtPosition(id, x, y)
		if z then return 100000 + z.mapID, nil, 0.8, 0.7, 0.2, 0.1, 0.3, 0.4 end
	end,
	GetMapGroupID = function() return nil end,
}
setmetatable(C_Map, { __index = function() return function() return nil end end })   -- (the rest: nothing)
C_MapExplorationInfo = { GetExploredMapTextures = function() return {} end }
GetQuestDifficultyColor = function() return { r = 1, g = 0.82, b = 0 } end
QuestDifficultyColors = { difficult = { r = 1, g = 0.5, b = 0.25 } }
GetPhysicalScreenSize = function() return 1920, 1080 end
'''

SWEEP = r'''
function SWEEP(ns, zooms)
	local S = ns.MapStitch
	local out = {}
	local view = CreateFrame("Frame", nil, UIParent)
	local canvas = CreateFrame("Frame", nil, view)
	local t0 = os.clock()
	if not S.Build(canvas, 100, 80, 2000) then return { built = false } end
	out.build = os.clock() - t0
	-- every game map's yards there and back (S.FromYards, S.ToYards: the minimap and the caves go by them)
	local yards = ns.MapWorld and ns.MapWorld.yards or { [0] = { { -1e4, 1e4, -1e4, 1e4 } }, [1] = { { -1e4, 1e4, -1e4, 1e4 } } }
	for cont, regions in pairs(yards) do
		local r = regions[1]
		local x, y = (r[1] + r[2]) / 2, (r[3] + r[4]) / 2
		local u, v = S.FromYards(cont, x, y)
		local x2, y2
		if u then x2, y2 = S.ToYards(cont, u, v) end
		if not x2 or math.abs(x2 - x) > 1 or math.abs(y2 - y) > 1 then
			ERRORS[#ERRORS + 1] = ("yards on game map %d don't come back: %s, %s -> %s, %s -> %s, %s"):format(cont, x, y, tostring(u), tostring(v), tostring(x2), tostring(y2))
		end
	end
	S.Layout(S.WORLD)
	S.ApplyGrade(1, 0.1, "show")
	local function shown(r)
		while r do
			if not r.__shown then return false end
			r = r.__parent
		end
		return true
	end
	local parts = S.Parts()[1][2]                  -- (root: the art; pinRoot: the icons)
	local function under(r, top)
		while r do if r == top then return true end r = r.__parent end
		return false
	end
	local function count()
		local art, icons = 0, 0
		for _, f in ipairs(FRAMES) do
			if f.__kind == "Texture" and shown(f) then
				if under(f, parts[2]) then icons = icons + 1 elseif under(f, parts[1]) then art = art + 1 end
			end
		end
		return art, icons
	end
	-- views: the whole world, then over every stitched continent's middle, zooming in
	local centres = { { 0.5, 0.5 } }
	for _, id in ipairs((ns.MapWorld and ns.MapWorld.continents) or { 1414, 1415 }) do
		local l, r, t, b = S.Rect(id)
		if l then centres[#centres + 1] = { (l + r) / 2, (t + b) / 2 } end
	end
	local k = ns.ClientMaps and ns.ClientMaps.zoom or 1
	out.rows = {}
	for _, z in ipairs(zooms) do
		local worstArt, worstIcons = 0, 0
		for _, c in ipairs(centres) do
			local hu, hv = 0.5 / z, 0.5 / z
			S.SetZoom(z / k, z)
			S.SetView(c[1], c[2], hu, hv, z / k, z / k)
			for _ = 1, 30 do RunOnUpdate(0.016) end      -- (the loader sets files a few dozen a frame)
			local a, i = count()
			if a > worstArt then
				-- (that view's art by layer: the world's, the continents', the zones', the cities')
				local by = {}
				for _, part in ipairs(S.Parts()) do
					local n = 0
					for _, f in ipairs(FRAMES) do
						if f.__kind == "Texture" and shown(f) then
							for _, top in ipairs(part[2]) do if under(f, top) then n = n + 1 break end end
						end
					end
					by[#by + 1] = part[1]:sub(1, 12) .. "=" .. n
				end
				out.split = out.split or {}
				out.split[z] = table.concat(by, " ", 2, 10)
			end
			worstArt, worstIcons = math.max(worstArt, a), math.max(worstIcons, i)
		end
		out.rows[#out.rows + 1] = { z, worstArt, worstIcons, out.split and out.split[z] or "" }
	end
	return out
end
'''


def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    db2 = sys.argv[1]
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(open(os.path.join(HERE, "stub.lua"), encoding="utf-8").read())
    maps = map_data(db2)
    L.execute("MAPS = " + lua_val(maps))
    L.execute(C_MAP)
    L.execute(SWEEP)
    ns = L.eval("{}")
    load = L.eval("""function(src, name, ns)
        local fn, err = loadstring(src, "@" .. name)
        if not fn then return false, err end
        local ok, e = xpcall(function() return fn("OpenMap", ns) end, function(m) return tostring(m) .. "\\n" .. debug.traceback() end)
        return ok, e
    end""")
    import re
    def expand(rel):                    # (as run.py: a library's XML, its scripts)
        if not rel.endswith(".xml"): return [rel]
        base = os.path.dirname(rel)
        src = re.sub(r"<!--.*?-->", "", open(os.path.join(ROOT, rel), encoding="utf-8").read(), flags=re.S)
        return [f for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', src)
                for f in expand(os.path.join(base, m.group(2).replace("\\", os.sep)))]
    files = []
    for line in open(clients.toc(), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"): files += expand(line.replace("\\", os.sep))
    failed = False
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("MISSING", rel); failed = True; continue
        ok, err = load(open(path, encoding="utf-8-sig").read(), rel, ns)
        if not ok:
            failed = True
            print("LOAD ERROR", rel, "\n", err)
    L.execute('FireEvent("ADDON_LOADED", "OpenMap") FireEvent("PLAYER_LOGIN") RunTimers(2)')
    # /openmap highlights (a client with a world of its own): it runs to the end and keeps what it found
    L.execute('SlashCmdList.OPENMAP("highlights") for _ = 1, 600 do RunTimers(0.02) end')
    got = L.eval('(OpenMap.modules.worldmap.db.highlights and #OpenMap.modules.worldmap.db.highlights) or -1')
    print("/openmap highlights:", got, "recorded")
    t = time.time()
    res = L.eval("SWEEP")(ns, L.table(1, 1.5, 2, 3, 4, 6, 9, 13, 20, 30, 48, 80))
    if not res["built"] is None and res["built"] is False:
        print("NOT BUILT (no world art?)"); failed = True
    else:
        print("built in %.2fs (Lua)" % res["build"])
        print("zoom   textures drawn, the most over the views: art, icons")
        for i in range(1, len(res["rows"]) + 1):
            row = res["rows"][i]
            print("%5g  %5d %5d   %s" % (row[1], row[2], row[3], row[4]))
    errs = L.eval("ERRORS")
    seen = set()
    for i in range(1, len(errs) + 1):
        key = errs[i].split("\n")[0]
        if key in seen: continue
        seen.add(key)
        print("ERROR:", errs[i][:1500]); print("-" * 60)
    print("%s: %d errors (%d unique), %.1fs" % (clients.NAME, len(errs), len(seen), time.time() - t))
    sys.exit(1 if failed or len(errs) else 0)


if __name__ == "__main__":
    main()
