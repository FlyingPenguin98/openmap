# The places a painted gap shows that no zone map draws: WoW Forever's own areas in land no zone map
# covers, which the painter put in from the game's minimap (the Wetlands' Excavation Site, a green
# valley with a lake south of Whelgar's). The game marks no one as having explored them (their
# AreaTable row has no exploration bit, AreaBit 0) and Blizzard's maps never draw them, so with
# unexplored areas hidden or darkened Stitch.lua treats each as unexplored land until it's found as a
# city is (Shade.Places: by the zone maps' pieces under its middle).
#   1. the game's terrain under the paintings: each map chunk's area (the ADTs' MCNK), from the game's
#      own files (OPENMAP_WOW: the World of Warcraft folder, tools/casc), else wago.tools into <cache>
#   2. a list of the areas with no exploration bit that the paintings show, for looking at one by one
#      when a painting is new or redone: PLACES takes those painted as a place of their own
#   3. for each of PLACES: the ground its area covers, grown a little (GROW) and faded out (SOFT), where
#      the painting shows (its alpha: the gap, not a zone's own art), as a mask over its box on the world
#      (OpenMap/Media/Textures/MapGapPlace/<area>.tga), with a coarse copy (CELLS) and its middle, in
#      OpenMap/Data/GapPlaces.lua
# Run after gapfills.py (it reads the paintings as the addon draws them).
#
# usage: python -P tools/map-preview/gapplaces.py <db2 dir> <cache>
import csv, os, re, struct, sys, time, urllib.request
import numpy as np
from PIL import Image
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
db2, cache = sys.argv[1:3]
work = os.path.join(cache, "_places")
os.makedirs(work, exist_ok=True)
sys.argv = ["render.py", db2, cache, work]
g = {"__name__": "gapplaces", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
sys.path.insert(0, os.path.join(here, "..", "map-caves"))
from wmo import chunks                              # (it puts tools/casc on the path too)

WM, TEXDIR, BUILD = g["WM"], g["TEXDIR"], g["BUILD"]
W, H = 1002.0, 668.0                                # world units (Azeroth's map art)
O, CHUNK = 32 * 1600 / 3, 1600 / 3 / 16             # yards from a continent's corner to its middle; a map chunk's side
# WoW Forever's own areas that a painting shows as a place of its own, looked at one by one (the list
# below, each run). The others it lists are painted as the land or sea round them: Stormwind Harbor
# (G01: the coast west of Stormwind), The Shaper's Terrace (G02, G06) and Scalding Ridge (G10): mountains;
# Gilneas (no zone's: Blizzard's own map of it is drawn there), Shark-Infested Waters, The Forbidding Sea
PLACES = [17732]                                    # Excavation Site: Wetlands (G01: a green valley with a lake)
ROUND = 0.75                                        # world units its ground's corners are rounded over (a map chunk's side:
                                                    #  the chunks' steps aren't the ground's own shape)
GROW = 0.5                                          # world units past its ground kept whole (the painter's edge of it)
SOFT = 1.0                                          # ... and faded out over past that
MARGIN = 2.0                                        # world units round its ground its box takes in
PX = 8                                              # px a world unit, worked at
SIZE = 128                                          # the mask's px a side, as written
CELLS = 16                                          # the coarse copy's cells a side
PAINTED = 0.5                                       # a painting's alpha counted as painted (the list)
LISTED = 20                                         # chunks painted an area needs to be listed

read = lambda n: list(csv.DictReader(open(os.path.join(db2, n + ".csv"), encoding="utf-8")))
areas = {int(r["ID"]): r for r in read("AreaTable")}
conts = {r["MapID"]: r for r in g["assign"][947] if r["MapID"] in ("0", "1")}
f = lambda r, k: float(r[k])


def to_world(cont, X, Y):
    """yards on continent 0 / 1 -> Azeroth's map (normalized), as render.py's rect()"""
    w = conts[cont]
    u = f(w, "UiMin_0") + (f(w, "Region_4") - Y) / (f(w, "Region_4") - f(w, "Region_1")) * (f(w, "UiMax_0") - f(w, "UiMin_0"))
    v = f(w, "UiMin_1") + (f(w, "Region_3") - X) / (f(w, "Region_3") - f(w, "Region_0")) * (f(w, "UiMax_1") - f(w, "UiMin_1"))
    return u, v


def to_yards(cont, u, v):
    w = conts[cont]
    Y = f(w, "Region_4") - (u - f(w, "UiMin_0")) / (f(w, "UiMax_0") - f(w, "UiMin_0")) * (f(w, "Region_4") - f(w, "Region_1"))
    X = f(w, "Region_3") - (v - f(w, "UiMin_1")) / (f(w, "UiMax_1") - f(w, "UiMin_1")) * (f(w, "Region_3") - f(w, "Region_0"))
    return X, Y


def cont_at(u, v):
    for cont, w in conts.items():
        if f(w, "UiMin_0") <= u <= f(w, "UiMax_0") and f(w, "UiMin_1") <= v <= f(w, "UiMax_1"): return cont


# ---------------------------------------------------------------- the game's terrain
CASC = []
def game_file(fid):
    """a file of the game's by file ID: from the install (OPENMAP_WOW), else wago.tools (kept in <cache>)"""
    if os.environ.get("OPENMAP_WOW"):
        if not CASC:
            from casc import Casc
            CASC.append(Casc(os.environ["OPENMAP_WOW"], "wow_classic_beta"))
        try:
            return CASC[0].read(fid)
        except KeyError:
            pass
    p = os.path.join(work, "%d.bin" % fid)
    if not os.path.exists(p) or os.path.getsize(p) < 100:
        url = "https://wago.tools/api/casc/%d?download&version=%s" % (fid, BUILD)
        open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "openmap-tools/1"}), timeout=120).read())
        time.sleep(0.15)
    data = open(p, "rb").read()
    return data if len(data) > 100 else None          # (a missing file answers with an empty or tiny body)


maps = {r["ID"]: r for r in read("Map")}
wdts, tiles = {}, {}
def area_of(cont, row, col):
    """the area of the map chunk `row` (along -X) and `col` (along -Y) from the continent's corner"""
    tx, ty = col // 16, row // 16
    if not (0 <= tx < 64 and 0 <= ty < 64): return 0
    if (cont, tx, ty) not in tiles:
        if cont not in wdts: wdts[cont] = dict(chunks(game_file(int(maps[cont]["WdtFileDataID"]))))
        w, n, grid = wdts[cont], ty * 64 + tx, None
        if struct.unpack_from("<I", w["MAIN"], n * 8)[0] & 1:
            data = game_file(struct.unpack_from("<8I", w["MAID"], n * 32)[0])   # (the tile's root file)
            if data:
                grid = np.zeros((16, 16), np.int32)
                for tag, d in chunks(data):
                    if tag != "MCNK": continue
                    ix, iy = struct.unpack_from("<2I", d, 4)
                    grid[iy, ix] = struct.unpack_from("<I", d, 0x34)[0]    # (MCNK's area ID)
        tiles[(cont, tx, ty)] = grid
    grid = tiles[(cont, tx, ty)]
    return 0 if grid is None else int(grid[row - ty * 16, col - tx * 16])


def chunk_world(cont, row, col):
    """a chunk's middle on Azeroth's map (normalized)"""
    return to_world(cont, O - (row + 0.5) * CHUNK, O - (col + 0.5) * CHUNK)


# ---------------------------------------------------------------- the paintings, as the addon draws them
fills = []                                          # (name, u0, v0, u1, v1, alpha at their own px)
for num, rect, w_, h_, cols, tl in re.findall(r'\{ "(\w+)", \{ ([-\d., ]+) \}, (\d+), (\d+), (\d+), \{ ([\d, ]*) \} \}',
                                             open(os.path.join(WM, "GapFills.lua"), encoding="utf-8").read()):
    w_, h_, cols = int(w_), int(h_), int(cols)
    img = Image.new("RGBA", (cols * 256, -(-h_ // 256) * 256))
    for t in (int(s) for s in tl.split(",") if s.strip()):
        img.paste(Image.open(os.path.join(TEXDIR, "MapGapFill", "%s_%d.tga" % (num, t))).convert("RGBA"), (((t - 1) % cols) * 256, ((t - 1) // cols) * 256))
    u0, v0, u1, v1 = (float(s) for s in rect.split(","))
    fills.append((num, u0, v0, u1, v1, np.asarray(img.crop((0, 0, w_, h_)).getchannel("A")).astype(np.float32) / 255))


def painted(us, vs):
    """the paintings' alpha at world points (normalized arrays): the most of any"""
    out = np.zeros(np.shape(us), np.float32)
    for _, u0, v0, u1, v1, a in fills:
        inside = (us >= u0) & (us < u1) & (vs >= v0) & (vs < v1)
        if inside.any():
            x, y = (us - u0) / (u1 - u0) * a.shape[1] - 0.5, (vs - v0) / (v1 - v0) * a.shape[0] - 0.5
            out = np.maximum(out, np.where(inside, ndimage.map_coordinates(a, [y, x], order=1, mode="nearest"), 0))
    return out


# ---------------------------------------------------------------- the list: areas with no exploration bit painted
print("areas with no exploration bit the paintings show (map chunks painted):", flush=True)
ground = {}                                         # area -> {(cont, row, col)} under a painting's box
for num, u0, v0, u1, v1, a in fills:
    cont = cont_at((u0 + u1) / 2, (v0 + v1) / 2)
    Xa, Ya = to_yards(cont, u0, v0)
    Xb, Yb = to_yards(cont, u1, v1)
    for row in range(int((O - Xa) // CHUNK), int((O - Xb) // CHUNK) + 1):
        for col in range(int((O - Ya) // CHUNK), int((O - Yb) // CHUNK) + 1):
            r = areas.get(area_of(cont, row, col))
            if r and r["AreaBit"] == "0": ground.setdefault(int(r["ID"]), set()).add((cont, row, col))
for area, cells in sorted(ground.items(), key=lambda kv: -len(kv[1])):
    us, vs = np.array([chunk_world(c, r, k) for c, r, k in cells]).T
    n = int((painted(us, vs) > PAINTED).sum())
    if n >= LISTED:
        parent = areas.get(int(areas[area]["ParentAreaID"]), {}).get("AreaName_lang", "-")
        print("  %5d %-28s (in %s) %4d%s" % (area, areas[area]["AreaName_lang"], parent, n, "   a place: PLACES" if area in PLACES else ""), flush=True)


# ---------------------------------------------------------------- the places
overlay = {(int(r["UiMapArtID"]), "%s:%s:%s:%s" % (r["TextureWidth"], r["TextureHeight"], r["OffsetX"], r["OffsetY"])):
           areas.get(int(r["AreaID_0"]), {}).get("AreaName_lang", "?") for r in read("WorldMapOverlay")}
def under(u, v):
    """the zone maps' pieces whose rectangle holds the world point (u, v), by name (Stitch.lua's Shade.Under)"""
    out = []
    for m in g["zones"]:
        l, r_, t, b = m["rect"]
        x, y = (u - l) / (r_ - l) * 1002, (v - t) / (b - t) * 668
        whose = m["name"] + ("'" if m["name"].endswith("s") else "'s")
        for key, _ in g["reveal"].get(m["art"], []):
            w_, h_, px, py = map(int, key.split(":"))
            if px <= x <= px + w_ and py <= y <= py + h_: out.append("%s %s" % (whose, overlay.get((m["art"], key), key)))
    return out


out_dir = os.path.join(TEXDIR, "MapGapPlace")
os.makedirs(out_dir, exist_ok=True)
for fn in os.listdir(out_dir):
    if fn.endswith(".tga"): os.remove(os.path.join(out_dir, fn))
rows_out = []
for area in PLACES:
    own = ground.get(area)
    if not own:
        print("  %d isn't under a painting: left out" % area, flush=True)
        continue
    cont = next(iter(own))[0]
    rows, cols_ = [r for _, r, _ in own], [k for _, _, k in own]
    u0, v0 = to_world(cont, O - min(rows) * CHUNK, O - min(cols_) * CHUNK)            # (its chunks' outer corners)
    u1, v1 = to_world(cont, O - (max(rows) + 1) * CHUNK, O - (max(cols_) + 1) * CHUNK)
    box = [min(u0, u1) - MARGIN / W, min(v0, v1) - MARGIN / H, max(u0, u1) + MARGIN / W, max(v0, v1) + MARGIN / H]
    gw, gh = int(round((box[2] - box[0]) * W * PX)), int(round((box[3] - box[1]) * H * PX))
    U, V = np.meshgrid(box[0] + (np.arange(gw) + 0.5) / gw * (box[2] - box[0]), box[1] + (np.arange(gh) + 0.5) / gh * (box[3] - box[1]))
    X, Y = to_yards(cont, U, V)
    R, K = ((O - X) // CHUNK).astype(int), ((O - Y) // CHUNK).astype(int)
    on = np.vectorize(lambda r, k: (cont, r, k) in own)(R, K)                         # (each px: the chunk it's in)
    on = ndimage.gaussian_filter(on.astype(np.float32), ROUND * PX) > 0.5
    dout = ndimage.distance_transform_edt(~on) / PX                                    # world units out from its ground
    t = np.clip(1 - (dout - GROW) / SOFT, 0, 1)
    m = t * t * (3 - 2 * t) * painted(U, V)
    a8 = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
    Image.merge("RGBA", (Image.new("L", (SIZE, SIZE), 255),) * 3 + (a8.resize((SIZE, SIZE), Image.LANCZOS),)).save(
        os.path.join(out_dir, "%d.tga" % area))
    coarse = np.asarray(a8.resize((CELLS, CELLS), Image.BOX)).astype(np.float32) / 255
    cells = "".join("%x" % min(15, int(c * 16)) for c in coarse.flatten())
    mid = (float((U * m).sum() / m.sum()), float((V * m).sum() / m.sum()))
    by = under(*mid)
    rows_out.append((area, areas[area]["AreaName_lang"], box, mid, cells, by))
    print("  %d %s: box %s, middle %.4f, %.4f, under %s" % (area, areas[area]["AreaName_lang"], ", ".join("%.4f" % b for b in box),
          mid[0], mid[1], ", ".join(by) or "no zone's pieces (always found)"), flush=True)

with open(os.path.join(WM, "GapPlaces.lua"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("-- Places a painted gap (art/drawn/gaps) shows that no zone map draws: WoW Forever's own, which the game\n"
             "-- marks no one as having explored (AreaTable's AreaBit 0). With unexplored areas hidden or darkened,\n"
             "-- each is unexplored land until it's found as a city is, by the zone maps' pieces under its middle\n"
             "-- (Stitch.lua's Shade.Places). Each: its area (AreaTable), its name, its box on the world (normalized:\n"
             "-- left, top, right, bottom), its middle (u, v), and how much of each of 16 x 16 cells over its box it\n"
             "-- covers (a hex digit each, rows from the top). Its mask, MapGapPlace/<area> over its box: the ground\n"
             "-- its area covers (the game's terrain) where the painting shows.\n"
             "-- Generated by tools/map-preview/gapplaces.py (build %s); regenerate rather than edit.\n\n" % BUILD)
    fo.write("local _, ns = ...\n\n")
    fo.write("ns.MapGapPlaces = {\n")
    for area, name, box, mid, cells, by in rows_out:
        fo.write('\t{ %d, "%s", { %s }, { %.6f, %.6f },   -- under %s\n' % (area, name, ", ".join("%.6f" % b for b in box),
                 mid[0], mid[1], ", ".join(by) or "no zone's pieces"))
        fo.write('\t\t"%s" },\n' % cells)
    fo.write("}\n")
print("wrote", len(rows_out), "place(s)", flush=True)
