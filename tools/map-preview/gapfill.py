# Bakes the gap fill: land on the continent map that no zone map covers, both the narrow
# strips between neighbouring zones (their art's frames) and wider gaps (west of Searing
# Gorge, south of Un'Goro, Mount Hyjal ...). Each zone's own art already reaches as far as
# Blizzard painted it (its sea, the land round it: render.py's territories); past that the
# land is blank, the zone maps' own parchment, which the zones' art fades into at its frame.
#
#   1. the zones alone (no backdrop, full detail; each through its own territory, its land and
#      its sea near its coasts) are rendered over each continent at GAP_PX px per world unit,
#      twice (on black and on white), giving how much of each pixel they cover
#   2. Blizzard's own maps of land Forever's tables don't use (Gilneas, the classic base maps
#      that paint the land round their zone) are drawn there, at their own resolution
#   3. the rest is blank: a clean stretch of Westfall's base art made to tile seamlessly
#      (MapPaper.tga), which the game repeats at the zone maps' scale through a mask of where
#      the land is (MapGapLand), its edge crisp along the coast
#   3b. for the game's minimap in the gaps (Close.lua): a soft mask of the gaps over the
#      whole continent (MapGapMask/<continent>.tga), and the minimap tiles that touch a gap
#      and aren't the black void past the world's edge (Gaps.lua's `minimap`)
#   4. written as GAP_TILE-world-unit tiles, only where there's a gap (the paper reaching a
#      little in under the zones, UNDER_REACH, never to a tile's edge deep under them): the land
#      masks (MapGapLand/<continent>_<col>_<row>.tga), listed in OpenMap/Data/Gaps.lua
#
# Tried and dropped: a colour fade from each neighbour, the neighbours' mountains carried
# in, the minimap as detail, the zones' paintings and edges baked in at the gaps' scale, a
# coastline laid on from the continent map. Each read as terrain that isn't on Blizzard's map,
# or as a blur: Blizzard's art is drawn at its own resolution, or not at all.
# usage: python -P tools/map-preview/gapfill.py <db2 dir> <texture cache> [--rerender]
import math, os, re, sys
import numpy as np
from PIL import Image
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
db2, cache = sys.argv[1:3]
rerender = "--rerender" in sys.argv
work = os.path.join(cache, "_gap")
os.makedirs(work, exist_ok=True)
sys.argv = ["render.py", db2, cache, work]
g = {"__name__": "gapfill", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
TEX, GAP_TILE = g["TEXDIR"], g["GAP_TILE"]
GAP_PX = 4                      # px per world unit while baking (a tile: GAP_TILE * GAP_PX px)
TILE_PX = GAP_TILE * GAP_PX
OUT_PX = 256                    # written at that, as plain 32-bit TGA (its coast edge crisp up close)
UNDER_REACH = (8, 16)           # world units under the zones from a gap where the paper is whole / gone (past
                                #  their edges' fade: a zone is solid there)
SEA_TRUST = (6, 10)             # world units past a zone's painted sea where the continent's land still gives way to sea
PAPER_FROM, PAPER_BOX = "Westfall", (170, 470, 320, 620)   # a clean stretch of its base art (rows, cols)
g.update(ZONES_ONLY=True, FADE_ZOOM=40.0, USE_SEA=False, USE_GAP=False, TERR_OWN=True)   # (each zone's own territory)

def zones_layer(m, cols, rows):
    """the zones' colour C and coverage A over the continent's tile grid (rendered: cached until
    --rerender); its land L (worked out each run: land_layer)"""
    p = os.path.join(work, "%d_layer.npz" % m["id"])
    if os.path.exists(p) and not rerender:
        z = np.load(p)
        C, A = z["C"].astype(np.float32), z["A"].astype(np.float32)
        return C, A, land_layer(m, cols, rows, A)
    l, r, t, b = m["rect"]
    OW, OH = cols * TILE_PX, rows * TILE_PX
    g["OW"], g["OH"] = OW, OH
    zoom = GAP_PX / min(OW / 1002, OH / 668)
    cu, cv = l + cols * GAP_TILE / 2 / 1002, t + rows * GAP_TILE / 2 / 668
    shots = []
    for bg in ((0, 0, 0), (1, 1, 1)):
        g["SEA"] = bg
        q = os.path.join(work, "%d_%d.png" % (m["id"], bg[0]))
        g["render"](cu, cv, zoom, q)
        shots.append(np.asarray(Image.open(q).convert("RGB")).astype(np.float32) / 255)
    dark, light = shots
    A = np.clip(1 - (light - dark).mean(2), 0, 1)
    C = np.clip(dark / np.maximum(A, 1e-3)[..., None], 0, 1)
    np.savez_compressed(p, C=C.astype(np.float16), A=A.astype(np.float16))
    return C, A, land_layer(m, cols, rows, A)

def land_layer(m, cols, rows, A):
    """the continent's land over its tile grid, less the sea the zones' own art paints"""
    l, r, t, b = m["rect"]
    OW, OH = cols * TILE_PX, rows * TILE_PX
    land = g["field_img"](m)[..., 3]                  # MapLand: the land, its frame and torn edges left out
    gw, gh = int(round((r - l) * 1002 * GAP_PX)), int(round((b - t) * 668 * GAP_PX))
    L = np.zeros((OH, OW), np.float32)
    L[:gh, :gw] = np.asarray(Image.fromarray((land * 255).astype(np.uint8)).resize((gw, gh), Image.BILINEAR)).astype(np.float32) / 255
    # where a zone's own art shows sea it's sea, whatever the continent map's coarser outline says
    zsea = np.zeros_like(L)
    for z in g["zones"]:
        zl, zr, zt, zb = z["rect"]
        if zr < l or zl > r or zb < t or zt > b: continue
        # (zone_sea, but only its stretches joined to open sea that reaches the art's frame, render.py's
        # zone_land sea: a small map's inland inlet, Shen'dralas', isn't, and SEA_TRUST spreading
        # from it made the land between Desolace and Feralas sea, so it had no paper)
        sea = g["zone_sea"](z)
        found = g["zone_sea_found"](z) if g["reveal"].get(z["art"]) else None
        lab, n = ndimage.label(sea)
        joined = np.unique(lab[found & (lab > 0)]) if found is not None and n else []
        sea = np.isin(lab, joined[joined > 0]).astype(np.float32) if len(joined) else np.zeros(sea.shape, np.float32)
        x0, y0 = (zl - l) * 1002 * GAP_PX, (zt - t) * 668 * GAP_PX
        w_, h_ = (zr - zl) * 1002 * GAP_PX, (zb - zt) * 668 * GAP_PX
        X0, Y0, X1, Y1 = max(0, int(x0)), max(0, int(y0)), min(OW, int(x0 + w_)), min(OH, int(y0 + h_))
        if X1 <= X0 or Y1 <= Y0: continue
        ys_ = (np.arange(Y0, Y1) + 0.5 - y0) / h_ * 668 - 0.5
        xs_ = (np.arange(X0, X1) + 0.5 - x0) / w_ * 1002 - 0.5
        piece = ndimage.map_coordinates(sea, [ys_[:, None].repeat(X1 - X0, 1), xs_[None, :].repeat(Y1 - Y0, 0)], order=1)
        zsea[Y0:Y1, X0:X1] = np.maximum(zsea[Y0:Y1, X0:X1], piece)
    # ... and just past a zone's painted sea too: there the continent map's coarser coast is
    # the one that's off, so land it claims within SEA_TRUST of a zone's sea is sea
    reach = ndimage.distance_transform_edt(zsea < 0.5) / GAP_PX       # world units from a zone's sea
    zsea = np.maximum(zsea, np.clip(1 - (reach - SEA_TRUST[0]) / (SEA_TRUST[1] - SEA_TRUST[0]), 0, 1) * (A < 0.5))
    return L * (1 - np.clip(zsea * 1.5, 0, 1))

def wrap(a, kx, ky):
    """a zero-mean texture crop made to tile: its last kx columns / ky rows crossfaded into
    its first, keeping its contrast through the crossfade (as sea.py)"""
    h, w = a.shape[:2]
    a = a.copy()
    def mix(x, y, r):
        return (x * (1 - r) + y * r) / np.sqrt((1 - r) ** 2 + r ** 2)
    if kx:
        r = np.linspace(0, 1, kx + 2)[1:-1].reshape((1, kx) + (1,) * (a.ndim - 2))
        a[:, :kx] = mix(a[:, w - kx:], a[:, :kx], r)
        a = a[:, :w - kx]
    if ky:
        r = np.linspace(0, 1, ky + 2)[1:-1].reshape((ky, 1) + (1,) * (a.ndim - 2))
        a[:ky] = mix(a[h - ky:], a[:ky], r)
        a = a[:h - ky]
    return a

def paper_tile():
    """the zone maps' blank parchment, seamless (its own pixels), and its size in world units"""
    m = next(x for x in g["maps"] if x["name"] == PAPER_FROM)
    y0, y1, x0, x1 = PAPER_BOX
    patch = g["base"](m)[y0:y1, x0:x1, :3].astype(np.float32)
    broad = np.dstack([ndimage.gaussian_filter(patch[..., c], 40, mode="reflect") for c in range(3)])
    detail = patch - broad
    sd = detail.mean(2).std()
    # the odd ink mark or fleck evened out (it would repeat with the tile)
    lum = detail.mean(2, keepdims=True)
    detail = detail - lum + np.clip(ndimage.median_filter(lum[..., 0], 5)[..., None], -1.6 * sd, 1.6 * sd)
    tile = np.clip(patch.reshape(-1, 3).mean(0) + wrap(detail, 24, 24), 0, 1)
    zone_px = 1002 / ((m["rect"][1] - m["rect"][0]) * 1002)       # its art px per world unit
    return tile, tile.shape[0] / zone_px

MINI_YARDS = 1600 / 3           # yards per minimap tile
CONT_OF = {1415: 0, 1414: 1}
MASK_PX = 768                   # the gap mask's width
TILE_FADE = 6.0                 # world units inside the drawn minimap tiles where the mask fades in
def minimap_list():
    src_ = open(os.path.join(g["WM"], "Minimap.lua"), encoding="utf-8").read()
    out, cur = {}, None
    for line in src_.split("\n"):
        m_ = re.match(r"\s*\[(\d)\] = \{", line)
        if m_: cur = out.setdefault(int(m_.group(1)), {}); continue
        if cur is not None:
            for k, v in re.findall(r"\[(\d+)\] = (\d+)", line): cur[int(k)] = int(v)
    return out
MINI = minimap_list()

def void_tile(fid):
    """the black void past the world's edge (or a flat, featureless tile)"""
    im = g["fetch"](fid)
    if im is None: return True
    a = np.asarray(im.convert("L").resize((64, 64))).astype(np.float32) / 255
    return (a < 0.06).mean() > 0.35 or a.std() < 0.015

def gap_minimap(m, gap):
    """the gap mask (MapGapMask) and the minimap tiles touching a gap. The mask fades out
    a little inside the tiles that are drawn, so where a tile is left out (the void past the
    world's edge) the minimap ends softly, not at a tile's straight edge"""
    l, r, t, b = m["rect"]
    soft = ndimage.gaussian_filter(gap, GAP_PX * 1.5)
    soft = np.clip((soft - 0.15) / 0.7, 0, 1)
    gw, gh = int(round((r - l) * 1002 * GAP_PX)), int(round((b - t) * 668 * GAP_PX))
    wide = np.asarray(Image.fromarray((g["M_WIDE"] * 255).astype(np.uint8)).resize((gw, gh), Image.BILINEAR)).astype(np.float32) / 255
    mask = soft[:gh, :gw] * wide                    # (faded at the continent art's own edge, as its land is)
    asg = g["assign"][m["id"]][0]
    minX, minY, maxX, maxY = (float(asg["Region_%d" % i]) for i in (0, 1, 3, 4))
    keep, cover = [], np.zeros((gh, gw), bool)
    for key, fid in sorted(MINI.get(CONT_OF[m["id"]], {}).items()):
        tx, ty = key // 64, key % 64
        us = [(maxY - wy) / (maxY - minY) * gw for wy in ((32 - tx) * MINI_YARDS, (31 - tx) * MINI_YARDS)]
        vs = [(maxX - wx) / (maxX - minX) * gh for wx in ((32 - ty) * MINI_YARDS, (31 - ty) * MINI_YARDS)]
        x0, x1 = max(0, int(round(min(us)))), min(gw, int(round(max(us))))
        y0, y1 = max(0, int(round(min(vs)))), min(gh, int(round(max(vs))))
        if x1 <= x0 or y1 <= y0 or mask[y0:y1, x0:x1].max() < 0.05: continue
        if void_tile(fid): continue
        keep.append(key)
        cover[y0:y1, x0:x1] = True
    inside = ndimage.distance_transform_edt(cover) / GAP_PX         # world units in from a missing tile
    mask = mask * np.clip((inside - 0.5) / TILE_FADE, 0, 1)
    mh = int(round(MASK_PX * gh / gw))
    a = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).resize((MASK_PX, mh), Image.LANCZOS)
    os.makedirs(os.path.join(TEX, "MapGapMask"), exist_ok=True)
    Image.merge("RGBA", (Image.new("L", (MASK_PX, mh), 255),) * 3 + (a,)).save(os.path.join(TEX, "MapGapMask", "%d.tga" % m["id"]))
    print("   gap minimap tiles", len(keep), flush=True)
    return keep

# Finer maps of land no zone covers, from Blizzard's own maps the client has but Forever's
# map tables don't use. Stitch.lua draws each (its own tiles, at their own resolution) where no
# zone paints, through MapCoastArt/<name>.tga: its land and shallows, inside its frame, less its
# labels.
#   Gilneas   the base map of Gilneas before the Cataclysm (the unexplored layer: parchment,
#             coast and shallows, no towns; uiMap 179, on Silverpine Forest's coordinates),
#             placed as Mists of Pandaria Classic's tables place it (`rect`). The gaps' land
#             takes its outline (`seeds`: points on its land, for finding it)
#   the rest  the classic base maps of Forever's zones (Forever's own are newer art): they
#             paint the land round their zone in Blizzard's lighter style (the ridges round
#             Orgrimmar, the mountains west of Searing Gorge ...), which no zone map of
#             Forever's does. Each is the same drawing as Forever's own map of its zone, so it's
#             placed where Forever's tables place that zone (SAME_ART checks); Mists Classic's
#             own places for them are its Cataclysm-era zones' (The Barrens': Northern Barrens'),
#             and its Hillsbrad Foothills (Alterac's land taken in) and Mulgore are other
#             drawings, left out. The land is Forever's outline. `labels`: boxes round the names
#             of the zones next door that each sets on that land (its art px), left out
# Where two reach the same land, it's shared out by which one's own zone is nearer (SHARE),
# softly, so no stretch shows two paintings of itself.
# (uiMap ids are Mists Classic's: where each file comes from.)
COAST_SOURCES = [{
    "name": "Gilneas", "continent": 1415, "zone": None,          # (uiMap 179)
    "rect": (0.652549, 0.722944, 0.349999, 0.420411),           # l, r, t, b on the world (normalized)
    "files": (308492, 308496, 308497, 308498, 308499, 308500, 308501, 308502, 308503, 308493, 308494, 308495),
    "seeds": ((334, 400), (747, 267), (614, 333), (560, 160), (700, 520), (450, 520), (250, 300), (400, 250)),
}, {
    "name": "Azshara", "continent": 1414, "zone": "Azshara",     # (uiMap 76)
    "files": (270416, 270418, 270422, 270429, 270439, 270440, 270430, 270413, 270407, 270435, 270417, 270428),
}, {
    "name": "Durotar", "continent": 1414, "zone": "Durotar",     # (uiMap 1)
    "files": (271420, 271436, 271430, 271434, 271431, 271432, 271433, 271423, 271425, 271429, 271424, 271441),
}, {
    "name": "Stonetalon Mountains", "continent": 1414, "zone": "Stonetalon Mountains",   # (uiMap 65)
    "files": (272625, 272631, 272639, 272643, 272626, 272627, 272651, 272640, 272622, 272629, 272644, 272645),
    "labels": ((710, 85, 930, 130), (110, 572, 310, 618)),
}, {
    "name": "Silithus", "continent": 1414, "zone": "Silithus",   # (uiMap 81)
    "files": (272549, 272550, 272569, 272578, 272551, 272570, 272571, 272579, 272552, 272568, 272557, 272558),
    "labels": ((770, 345, 970, 432),),
}, {
    "name": "Feralas", "continent": 1414, "zone": "Feralas",     # (uiMap 69)
    "files": (271676, 271689, 271697, 271693, 271703, 271677, 271698, 271690, 271684, 271688, 271701, 271702),
    "labels": ((100, 130, 210, 252), (740, 66, 930, 112), (640, 576, 830, 628)),
}, {
    "name": "Thousand Needles", "continent": 1414, "zone": "Thousand Needles",   # (uiMap 64)
    "files": (272969, 272960, 272974, 272980, 272956, 272970, 272971, 272966, 272967, 272959, 272965, 272979),
    "labels": ((290, 32, 410, 104), (570, 118, 790, 198), (130, 532, 320, 612)),
}, {
    "name": "Ashenvale", "continent": 1414, "zone": "Ashenvale",     # (uiMap 63)
    "files": (270377, 270403, 270374, 270383, 270395, 270404, 270396, 270384, 270385, 270399, 270382, 270406),
    "labels": ((420, 82, 660, 132), (20, 562, 260, 618)),
}, {
    "name": "Felwood", "continent": 1414, "zone": "Felwood",     # (uiMap 77)
    "files": (271651, 271667, 271661, 271668, 271671, 271654, 271662, 271672, 271674, 271670, 271655, 271656),
    "labels": ((730, 82, 960, 122), (650, 352, 780, 396)),
}, {
    "name": "Tanaris", "continent": 1414, "zone": "Tanaris",     # (uiMap 71)
    "files": (272790, 272786, 272802, 272797, 272791, 272779, 272780, 272804, 272803, 272785, 272778, 272796),
    "labels": ((10, 180, 180, 228), (820, 216, 960, 342)),
}, {
    "name": "Dun Morogh", "continent": 1415, "zone": "Dun Morogh",   # (uiMap 27)
    "files": (271407, 271390, 271415, 271402, 271394, 271397, 271403, 271391, 271395, 271413, 271414, 271412),
    "labels": ((680, 32, 890, 78), (490, 516, 750, 578)),
}, {
    "name": "Loch Modan", "continent": 1415, "zone": "Loch Modan",   # (uiMap 48)
    "files": (252868, 252872, 252873, 252874, 252875, 252876, 252877, 252878, 252879, 252869, 252870, 252871),
}, {
    "name": "Arathi Highlands", "continent": 1415, "zone": "Arathi Highlands",   # (uiMap 14)
    "files": (270337, 270355, 270338, 270334, 270345, 270340, 270356, 270335, 270341, 270344, 270339, 270354),
    "labels": ((20, 86, 230, 132),),
}, {
    "name": "Badlands", "continent": 1415, "zone": "Badlands",   # (uiMap 15)
    "files": (270544, 270519, 270523, 270537, 270538, 270539, 270545, 270526, 270516, 270548, 270518, 270549),
    "labels": ((100, 62, 360, 112),),
}, {
    "name": "Un'Goro Crater", "continent": 1414, "zone": "Un'Goro Crater",   # (uiMap 78)
    "files": (253240, 253244, 253245, 253246, 253247, 253248, 253249, 253250, 253251, 253241, 253242, 253243),
}, {
    "name": "Searing Gorge", "continent": 1415, "zone": "Searing Gorge",   # (uiMap 32)
    "files": (254515, 254519, 254520, 254521, 254522, 254523, 254524, 254525, 254526, 254516, 254517, 254518),
}, {
    "name": "The Barrens", "continent": 1414, "zone": "The Barrens",   # (uiMap 10)
    "files": (270575, 270555, 270556, 270557, 270588, 270576, 270582, 270583, 270562, 270566, 270587, 270581),
    "labels": ((100, 50, 310, 110), (630, 128, 770, 172), (160, 292, 350, 342), (220, 572, 380, 656), (860, 512, 975, 612)),
}]
SOURCE_FRAME = (30, 140)        # source art px in from its edge where it takes over (a long fade: where it meets
                                #  blank paper, its edge mustn't read as a line)
SOURCE_KNOT = 110               # source art px: its corners (the frame's knots) are left out
SOURCE_SHALLOWS = (22, 38)      # source art px off its coast where its own sea (the shallows) is full / gone
SOURCE_MASK = 256               # MapCoastArt's size (a soft mask: more is only file size)
LABEL_SOFT = 10                 # source art px a left-out label's box fades over
# land left as parchment for now: the southern slopes of Mount Hyjal, { u0, v0, u1, v1 } on the
# world (normalized), faded over its last tenth
PARCHMENT = ((0.228, 0.345, 0.288, 0.400),)
SHARE = (6, 4)                  # world units a map's claim halves over (from its own zone's land), and how sharply
                                # (the power) the nearest one leads
SAME_ART = 0.85                 # how closely a source's ink lines must match its zone's own art (correlation)

def ink(art):
    """an art's ink lines: its brightness' gradient"""
    L = ndimage.gaussian_filter(art[..., :3].mean(2), 1.5)
    return np.hypot(ndimage.sobel(L, 0), ndimage.sobel(L, 1))

def place_source(src):
    """a zone's source map goes where Forever's tables place the zone: it's the same drawing as
    Forever's own map of it (their ink lines correlate, inside their frames), or it's left out"""
    if not src["zone"]: return True
    z = next(z for z in g["zones"] if z["name"] == src["zone"])
    src["rect"] = z["rect"]
    a, b = ink(source_land(src)[0])[40:-40, 40:-40], ink(g["base"](z))[40:-40, 40:-40]
    a, b = a - a.mean(), b - b.mean()
    match = float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
    if match < SAME_ART: print("   left out", src["name"], "(not its zone's drawing: %.2f)" % match, flush=True)
    return match >= SAME_ART

def source_land(src):
    """the source map's art and its land: a watershed between its coast's ink line (the ridge),
    the sea (its pale shallows and the art's edge) and points on the land (`seeds`)"""
    from PIL import ImageFilter
    art = Image.new("RGB", (1024, 768))
    for i, fid in enumerate(src["files"]):
        tile = g["fetch"](fid)
        if tile: art.paste(tile.convert("RGB"), ((i % 4) * 256, (i // 4) * 256))
    art = np.asarray(art.crop((0, 0, 1002, 668))).astype(np.float32) / 255
    if not src.get("seeds"): return art, None
    hsv = np.asarray(Image.fromarray((art * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)).convert("HSV")).astype(np.float32) / 255
    elev = (np.clip((0.62 - hsv[..., 2]) / 0.35, 0, 1) * 254).astype(np.uint8)
    markers = np.zeros(elev.shape, np.int16)
    markers[ndimage.binary_erosion(ndimage.gaussian_filter(hsv[..., 1], 3) < 0.40, iterations=3)] = 1
    markers[:8] = markers[-8:] = 1
    markers[:, :8] = markers[:, -8:] = 1
    for x, y in src["seeds"]: markers[y - 3:y + 3, x - 3:x + 3] = 2
    land = ndimage.watershed_ift(elev, markers) == 2
    land = ndimage.binary_fill_holes(ndimage.binary_closing(land, iterations=5))   # (its city's streets: land)
    return art, ndimage.binary_opening(land, iterations=2).astype(np.float32)

def frame_fade(sx, sy):
    """a source map's own frame and corner knots faded out (its art px)"""
    inside = np.minimum(np.minimum(sx, 1002 - sx), np.minimum(sy, 668 - sy))
    wf = np.clip((inside - SOURCE_FRAME[0]) / (SOURCE_FRAME[1] - SOURCE_FRAME[0]), 0, 1)
    knot = (np.minimum(sx, 1002 - sx) < SOURCE_KNOT) & (np.minimum(sy, 668 - sy) < SOURCE_KNOT)
    return (wf * ~knot).astype(np.float32)

def label_holes(src):
    """1, but 0 over the source's labels (its art grid), softened"""
    keep = np.ones((668, 1002), np.float32)
    for x0, y0, x1, y1 in src.get("labels", ()):
        keep[max(0, y0):y1, max(0, x0):x1] = 0
    return np.clip(ndimage.gaussian_filter(keep, LABEL_SOFT / 2), 0, 1) if src.get("labels") else keep

source_art = []                 # (name, continent, rect, files): for Gaps.lua's `art`
def apply_sources(m, L, A, OW, OH):
    """L (land) on the continent's grid, from each source map over it; and each one's mask
    (MapCoastArt): its land and shallows, inside its frame, less its labels, where no zone (A)
    paints, and its share where more than one reaches"""
    l, r, t, b = m["rect"]
    srcs = [s for s in COAST_SOURCES if s["continent"] == m["id"] and place_source(s)]
    if not srcs: return
    zones_by = {z["name"]: z for z in g["zones"]}
    # the shares, on a coarse grid (a world unit a cell): each map's claim, by its reach (its
    # frame) and how near its own zone's land is
    SW, SH = int(math.ceil((r - l) * 1002)), int(math.ceil((b - t) * 668))
    cu = l + (np.arange(SW) + 0.5) / 1002
    cv = t + (np.arange(SH) + 0.5) / 668
    claims = []
    for src in srcs:
        sl, sr, st, sb = src["rect"]
        sx = ((cu - sl) / (sr - sl) * 1002)[None, :].repeat(SH, 0)
        sy = ((cv - st) / (sb - st) * 668)[:, None].repeat(SW, 1)
        reach = frame_fade(sx, sy)
        z = zones_by.get(src["zone"]) if src["zone"] else None
        if z:
            zl, zr, zt, zb = z["rect"]
            own = g["own_land"](z).astype(np.float32)
            zx = ((cu - zl) / (zr - zl) * 1002)[None, :].repeat(SH, 0)
            zy = ((cv - zt) / (zb - zt) * 668)[:, None].repeat(SW, 1)
            on = ndimage.map_coordinates(own, [zy - 0.5, zx - 0.5], order=1, mode="constant") > 0.5
            d = ndimage.distance_transform_edt(~on) if on.any() else np.full((SH, SW), 1e3)
            claim = reach / (1 + d / SHARE[0]) ** SHARE[1]
        else:
            claim = reach.copy()        # (a map of its own land, not a zone's surroundings: it leads there)
        claims.append(claim.astype(np.float32))
    total = np.maximum(sum(claims), 1e-6)
    for src, claim in zip(srcs, claims):
        art, land = source_land(src)
        sl, sr, st, sb = src["rect"]
        ax, ay = np.meshgrid(np.arange(1002) + 0.5, np.arange(668) + 0.5)
        wu, wv = sl + ax / 1002 * (sr - sl), st + ay / 668 * (sb - st)       # its pixels on the world
        gx, gy = (wu - l) * 1002 * GAP_PX - 0.5, (wv - t) * 668 * GAP_PX - 0.5
        if land is not None:            # its own outline for the gaps' land
            u = l + (np.arange(OW) + 0.5) / (1002 * GAP_PX)
            v = t + (np.arange(OH) + 0.5) / (668 * GAP_PX)
            sx = ((u - sl) / (sr - sl) * 1002)[None, :].repeat(OH, 0)
            sy = ((v - st) / (sb - st) * 668)[:, None].repeat(OW, 1)
            wf = frame_fade(sx, sy)
            on = ndimage.map_coordinates(land, [sy - 0.5, sx - 0.5], order=1, mode="constant")
            L[:] = L * (1 - wf) + on * wf
        else:                           # Forever's outline, on its grid
            land = ndimage.map_coordinates(L, [gy, gx], order=1, mode="constant")
        # the mask, on the source art's own grid
        off = ndimage.distance_transform_edt(land < 0.5)
        keep = np.clip(1 - (off - SOURCE_SHALLOWS[0]) / (SOURCE_SHALLOWS[1] - SOURCE_SHALLOWS[0]), 0, 1)
        zone = ndimage.map_coordinates(ndimage.gaussian_filter(A, 2), [gy, gx], order=1, mode="nearest")
        share = ndimage.map_coordinates(claim / total, [(wv - t) * 668 - 0.5, (wu - l) * 1002 - 0.5], order=1, mode="nearest")
        mask = keep * frame_fade(ax, ay) * np.clip(1 - zone * 1.4, 0, 1) * share * label_holes(src)
        for u0, v0, u1, v1 in PARCHMENT:
            fu, fv = (u1 - u0) * 0.1, (v1 - v0) * 0.1
            inside = np.clip(np.minimum((wu - u0) / fu, (u1 - wu) / fu), 0, 1) * np.clip(np.minimum((wv - v0) / fv, (v1 - wv) / fv), 0, 1)
            mask = mask * (1 - inside)
        if mask.max() < 0.05: continue
        os.makedirs(os.path.join(TEX, "MapCoastArt"), exist_ok=True)
        a = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).resize((SOURCE_MASK, SOURCE_MASK), Image.LANCZOS)
        key = re.sub(r"[^A-Za-z]", "", src["name"])    # (its file's name: letters only)
        Image.merge("RGBA", (Image.new("L", (SOURCE_MASK, SOURCE_MASK), 255),) * 3 + (a,)).save(os.path.join(TEX, "MapCoastArt", "%s.tga" % key))
        # its tiles that show anything (the rest aren't drawn: 0)
        files = [f if np.clip(mask, 0, 1)[(i // 4) * 256:(i // 4 + 1) * 256, (i % 4) * 256:(i % 4 + 1) * 256].max() > 0.02 else 0
                 for i, f in enumerate(src["files"])]
        source_art.append((key, src["continent"], src["rect"], files))
        print("   coast from", src["name"], flush=True)

over_dir, land_dir = os.path.join(TEX, "MapGap"), os.path.join(TEX, "MapGapLand")
# (MapGap: what was laid over the paper, none now; MapCoastArt: so a source left out leaves no mask behind)
for d_ in (over_dir, land_dir, os.path.join(TEX, "MapCoastArt")):
    os.makedirs(d_, exist_ok=True)
    for f in os.listdir(d_):
        if f.endswith(".tga"): os.remove(os.path.join(d_, f))
listing, gap_tiles = {}, {}
for m in g["maps"]:
    if m["kind"] != 2: continue
    l, r, t, b = m["rect"]
    cols, rows = math.ceil((r - l) * 1002 / GAP_TILE), math.ceil((b - t) * 668 / GAP_TILE)
    OW, OH = cols * TILE_PX, rows * TILE_PX
    C, A, L = zones_layer(m, cols, rows)
    print(m["name"], flush=True)
    L = L.copy()
    apply_sources(m, L, A, OW, OH)
    # a crisp land edge
    crisp = np.clip((ndimage.gaussian_filter(L, 1.0) - 0.5) / 0.12 + 0.5, 0, 1)
    need = L * (1 - A)
    # the paper reaches UNDER_REACH in under the zones from the gaps and no
    # further: deeper in it's never seen, and ending it there rather than at a tile's edge
    # leaves no straight line where a tile with a gap meets one without (zoomed out, where the
    # zones are only partly drawn in, the paper shows through them)
    from_gap = ndimage.distance_transform_edt(need < 0.25) / GAP_PX     # world units from a gap
    reach = np.clip(1 - (from_gap - UNDER_REACH[0]) / (UNDER_REACH[1] - UNDER_REACH[0]), 0, 1)
    paper_a = crisp * reach
    got = []
    for j in range(rows):
        for i in range(cols):
            ys, xs = slice(j * TILE_PX, (j + 1) * TILE_PX), slice(i * TILE_PX, (i + 1) * TILE_PX)
            if need[ys, xs].max() < 0.25 and paper_a[ys, xs].max() < 0.01: continue
            name = "%d_%d_%d.tga" % (m["id"], i, j)
            # where the land is (the game draws the paper through it)
            Image.merge("RGBA", (Image.new("L", (OUT_PX, OUT_PX), 255),) * 3 + (
                Image.fromarray((paper_a[ys, xs] * 255).astype(np.uint8)).resize((OUT_PX, OUT_PX), Image.LANCZOS),)).save(os.path.join(land_dir, name))
            got.append((i, j, 0))
    listing[m["id"]] = got
    gap_tiles[m["id"]] = gap_minimap(m, ((L > 0.5) & (A < 0.5)).astype(np.float32))
    print("  %d x %d tiles, %d with gaps" % (cols, rows, len(got)), flush=True)

tile, paper_world = paper_tile()
Image.fromarray((tile * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS).save(os.path.join(TEX, "MapPaper.tga"))
with open(os.path.join(g["WM"], "Gaps.lua"), "w", encoding="utf-8", newline="\n") as f:
    f.write("-- The gaps: land no zone map covers. Per continent, tiles { col, row, over, ... }, each `tile`\n")
    f.write("-- world units square from the continent map's top-left corner. MapGapLand/<continent>_<col>_<row>\n")
    f.write("-- is where the land is, and the blank map paper (MapPaper, `paper` world units a tile) is drawn\n")
    f.write("-- through it (`over` is 0: nothing is laid over the paper).\n")
    f.write("-- Generated by tools/map-preview/gapfill.py; regenerate rather than edit.\n\n")
    f.write("local _, ns = ...\n\nns.MapGaps = {\n\ttile = %d,\n\tpaper = %.2f,\n" % (GAP_TILE, paper_world))
    for cid, got in sorted(listing.items()):
        f.write("\t[%d] = { %s },\n" % (cid, ", ".join("%d, %d, %d" % t for t in got)))
    f.write("\t-- the minimap tiles (x * 64 + y) touching a gap, for Close.lua (MapGapMask/<continent> is where)\n\tminimap = {\n")
    for cid, keys in sorted(gap_tiles.items()):
        f.write("\t\t[%d] = { %s },\n" % (cid, ", ".join(str(k) for k in keys)))
    f.write("\t},\n")
    f.write("\t-- finer maps the client has of land no zone covers, drawn by Stitch.lua through MapCoastArt/<name>:\n")
    f.write("\t-- { name, continent, { l, r, t, b } (on the world, normalized), { its 12 tiles, file IDs: 0 where the\n\t-- mask leaves nothing of it } }\n\tart = {\n")
    for name, cont, rect, files in source_art:
        f.write('\t\t{ "%s", %d, { %s }, { %s } },\n' % (name, cont, ", ".join("%.6f" % x for x in rect), ", ".join(str(x) for x in files)))
    f.write("\t},\n}\n")
print("ok")
