# Builds OpenMap/Data/<client>/World.lua: which of the game's maps are stitched into the world, and
# how world positions land on it, from the game's map tables (UiMap, UiMapAssignment, UiMapXMapArt,
# UiMapArt, UiMapArtStyleLayer, UiMapArtTile, WorldMapOverlay, Map) as CSVs from wago.tools.
#
# A client with a world of its own (retail: twelve continents, and zones in several versions) needs
# it; WoW Forever's toc has none, and Stitch.lua takes every continent and zone on Azeroth's map, as
# it always has. Which maps:
#   - continents on Azeroth's map (947) with art, placed on it;
#   - zones under them with art and a place on 947, in the open world (their game map no instance),
#     shown on the game's own navigation bar (UIMapFlag.DoNotShowOnNavbar off);
#   - not a zone that only groups others (Stranglethorn Vale over its two halves), not a second
#     version of one (UiMap.AlternateUiMapGroup: the first is kept; a lower floor of the same place),
#     and not those in EXCLUDE (below, each with why);
#   - a zone without explored-area pieces that lies within another stitched zone (a city, a starting
#     area's own map) is drawn over it as a city (2); the rest are zones (1).
#
# usage: python -P tools/map-data/world.py <db2 dir>      (OPENMAP_CLIENT: the client, tools/clients.py)
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients   # the client the tools build for (OPENMAP_CLIENT)
import uimap

DONT_NAVBAR, CITY_MAP = 0x80000, 0x100000      # UIMapFlag (Blizzard_APIDocumentationGenerated/MapConstants)
# maps the rules above would take that the world map shouldn't (the game has newer maps of the same
# land, or they lie under the land or the sea that another map paints)
EXCLUDE = {
    "retail": {
        94: "Quel'Thalas before Midnight (game map 530): Midnight's own maps of it are stitched",
        95: "(the same)", 110: "(the same)", 122: "(the same)", 467: "(the same)",
        201: "Vashj'ir, under the sea west of the Eastern Kingdoms: its maps would paint the seabed over the sea",
        203: "(the same)", 204: "(the same)", 205: "(the same)",
        2213: "Khaz Algar's underground (game map 2601), right under the Isle of Dorn on Azeroth's map",
        2214: "(the same)", 2215: "(the same)", 2216: "(the same)", 2255: "(the same)", 2256: "(the same)",
        739: "a class's own hall (Trueshot Lodge): only hunters see it",
    },
}
# a zone drawn as the rules wouldn't (2: a city, 1: a zone of its own)
KIND = {
    "retail": {
        554: 1,     # Timeless Isle: an island of its own, which no other zone paints (it lies in the Jade Forest's frame)
    },
}


def main():
    db2 = sys.argv[1]
    w = uimap.World(db2)
    read = lambda n: list(csv.DictReader(open(os.path.join(db2, n + ".csv"), encoding="utf-8")))
    tiles = set(int(r["UiMapArtID"]) for r in read("UiMapArtTile") if r["LayerIndex"] == "0")
    pieces = {}
    for r in read("WorldMapOverlay"):
        pieces[int(r["UiMapArtID"])] = pieces.get(int(r["UiMapArtID"]), 0) + 1
    exclude = EXCLUDE.get(clients.NAME, {})

    def has_art(m):
        a = w.art(m)
        return a is not None and a[0] in tiles

    # (its first game map open world: a zone's own map can also be a scenario's, the Valley of the Four
    # Winds' Halfhill)
    def open_world(m):
        rows = sorted(w.assign.get(m, []), key=lambda r: int(r["OrderIndex"]))
        g = rows and int(rows[0]["MapID"])
        return bool(rows) and g in w.gamemap and w.gamemap[g]["InstanceType"] == "0"

    # (all of them in its tree, as C_Map.GetMapChildrenInfo(947, Continent, true): Quel'Thalas is under
    # the Eastern Kingdoms)
    continents = [m for m, r in sorted(w.uimap.items()) if r["Type"] == "2" and w.under_world(m)
                  and has_art(m) and w.rect(m)]
    cand = {}
    for m, r in sorted(w.uimap.items()):
        if r["Type"] != "3" or not w.under_world(m) or m in exclude: continue
        if not has_art(m) or not w.rect(m) or not open_world(m): continue
        if int(r["Flags"]) & DONT_NAVBAR: continue
        cand[m] = r
    # a second version of one: the first of its group
    groups = {}
    for m, r in cand.items():
        g = int(r["AlternateUiMapGroup"])
        if g: groups.setdefault(g, []).append(m)
    alias = {}                      # a version left out -> the one stitched (a player phased into it: its map is ours)
    for g, ms in groups.items():
        for m in sorted(ms)[1:]:
            cand.pop(m, None)
            alias[m] = sorted(ms)[0]
    n_pieces = lambda m: pieces.get(w.art(m)[0], 0)
    # a zone that only groups others: no pieces of its own, two or more zones under it that have
    for m in list(cand):
        kids = [k for k in cand if w.parent(k) == m and n_pieces(k) > 0]
        if n_pieces(m) == 0 and len(kids) >= 2: cand.pop(m)

    def inside(m, other):
        a, b = w.rect(m), w.rect(other)
        cx, cy = (a[0] + a[1]) / 2, (a[2] + a[3]) / 2
        return b[0] < cx < b[1] and b[2] < cy < b[3] and (a[1] - a[0]) < (b[1] - b[0])
    kinds = {}
    for m, r in cand.items():
        city = n_pieces(m) == 0 and (int(r["Flags"]) & CITY_MAP or any(o != m and n_pieces(o) > 0 and inside(m, o) for o in cand))
        kinds[m] = KIND.get(clients.NAME, {}).get(m, 2 if city else 1)

    # world positions: per game map with a stitched zone, the regions that place it
    gamemaps = sorted({int(a["MapID"]) for m in cand for a in w.assign.get(m, [])})
    yards = {}
    for g in gamemaps:
        regions = w.yards(g)
        # (only the regions some stitched zone lies in: Outland shares game map 530 with the draenei isles)
        keep = []
        for reg in regions:
            for m in cand:
                for a in w.assign.get(m, []):
                    if int(a["MapID"]) == g and reg[0] <= float(a["Region_0"]) + 1 and float(a["Region_3"]) - 1 <= reg[1] \
                            and reg[2] <= float(a["Region_1"]) + 1 and float(a["Region_4"]) - 1 <= reg[3]:
                        break
                else: continue
                keep.append(reg); break
        if keep: yards[g] = keep
    # the game maps whose minimap shows on each continent: those of its stitched zones
    minimap = {}
    for m in cand:
        c = m
        while c and w.uimap.get(c, {}).get("Type") != "2": c = w.parent(c)
        if c in continents:
            for a in w.assign.get(m, []):
                g = int(a["MapID"])
                if g in yards and g not in minimap.setdefault(c, []): minimap[c].append(g)

    out = os.path.join(clients.DATA, "World.lua")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- The maps stitched into the world, and how world positions (yards) land on it.\n")
        fh.write("-- Generated by tools/map-data/world.py from the game's map tables (build %s); regenerate rather than edit.\n" % clients.BUILD)
        fh.write("--   continents: stitched (their art and land); zones: [uiMapID] = 1 a zone, 2 a city (over its zone)\n")
        fh.write("--   yards: [game map] = { { x0, x1, y0, y1, au, bu, av, bv } }: in that world box, u = au + bu * y, v = av + bv * x\n")
        fh.write("--   minimap: [continent] = the game maps whose minimap tiles show on it\n")
        fh.write("--   alias: [uiMapID] = the stitched map it's another version of (a player phased into it sees ours)\n\n")
        fh.write("local _, ns = ...\n\nns.MapWorld = {\n")
        fh.write("\tcontinents = { %s },\n" % ", ".join(str(c) for c in continents))
        fh.write("\tzones = {\n")
        for m in sorted(kinds):
            fh.write("\t\t[%d] = %d,   -- %s\n" % (m, kinds[m], w.uimap[m]["Name_lang"]))
        fh.write("\t},\n\tyards = {\n")
        for g in sorted(yards):
            fh.write("\t\t[%d] = { %s },\n" % (g, ", ".join("{ %s }" % ", ".join("%.10g" % v for v in reg) for reg in yards[g])))
        fh.write("\t},\n\tminimap = {\n")
        for c in sorted(minimap):
            fh.write("\t\t[%d] = { %s },\n" % (c, ", ".join(str(g) for g in sorted(minimap[c]))))
        fh.write("\t},\n\talias = {\n")
        for m in sorted(alias):
            if alias[m] in kinds: fh.write("\t\t[%d] = %d,   -- %s\n" % (m, alias[m], w.uimap[m]["Name_lang"]))
        fh.write("\t},\n}\n")
    print("wrote %s: %d continents, %d zones (%d cities), %d game maps" % (os.path.relpath(out, clients.REPO), len(continents),
          sum(1 for k in kinds.values() if k == 1), sum(1 for k in kinds.values() if k == 2), len(yards)))


if __name__ == "__main__":
    main()
