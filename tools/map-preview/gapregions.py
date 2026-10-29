# Exports the gap regions for filling (art/drawn/gaps/source/, not committed; see art/drawn/gaps/README.md):
# land on the continent maps that no zone map covers (gapfill.py's gaps, less Blizzard's own
# classic maps of them), each region with PAD world units of the zone maps round it, at the
# resolution of the finest zone map there (at most MAX_PX px a world unit):
#   NN_<zones>.png          the zone maps' art as the game draws it, the rest transparent: fill this
#   NN_<zones>_gap.png      white: the gap the gap fill sees
#   NN_<zones>_fill.png     white: what a fill is taken for (gapfills.py): the continent's land wherever
#                           the zone maps don't fully cover it, and COAST_OUT past its coast, fading
#                           out over COAST_FADE of open sea; less Blizzard's classic maps of the land
#   NN_<zones>_now.png      how the map draws it now
#   NN_<zones>_sea.png      white: open sea (no continent land, no zone art), where a painted coastline is kept
#   NN_<zones>_minimap.png  the game's minimap of the same area, aligned
#   index_<continent>.png   where each region is
# The regions are art/drawn/gaps/regions.json (committed): each region's place on its continent and
# its scale, exported again as they are, so fills made from them still line up. --find looks for the
# regions afresh and keeps the --top N (default 10) with the most gap, named G01, G02 ... by size.
#
# usage: python -P tools/map-preview/gapregions.py <db2 dir> <texture cache> [--find [--top N]] [--only G01,G02]
#   OPENMAP_WOW (the game's folder) reads the textures from the install (tools/casc)
import json, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
GAPS = os.path.join(root, "art", "drawn", "gaps")
OUT = os.path.join(GAPS, "source")
find = "--find" in sys.argv
TOP = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 10
only = None
if "--only" in sys.argv: only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
db2, cache = sys.argv[1:3]
gf = os.path.join(here, "gapfill.py")
src = open(gf, encoding="utf-8").read()
src = src[:src.index("over_dir, land_dir = ")]           # (gapfill.py's set-up: its layers, not its output)
sys.argv = [gf, db2, cache]
G = {"__name__": "gapregions", "__file__": gf}
exec(compile(src, gf, "exec"), G)
g = G["g"]; GAP_PX = G["GAP_PX"]; GAP_TILE = G["GAP_TILE"]; TILE_PX = G["TILE_PX"]
MINI, YARDS, CONT_OF = G["MINI"], G["MINI_YARDS"], G["CONT_OF"]
PAD = 10                        # world units of context round each gap
MERGE = 2                       # world units: gaps closer than this are one region
MIN_AREA = 4                    # square world units: smaller specks are left out
CITY = 0.03                     # zones narrower than this (world widths) are cities: their scale isn't the land's
MAX_PX = 24                     # px a world unit at most
COAST_OUT, COAST_FADE = 3.0, 3.0
os.makedirs(OUT, exist_ok=True)
conts = {m["id"]: m for m in g["maps"] if m["kind"] == 2}
work = os.path.join(cache, "_gap")
tmp = os.path.join(work, "_regions.png")


def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def shoot(cu, cv, px, W, H, path, zones_only, bg=None):
    g["OW"], g["OH"] = W, H
    g.update(ZONES_ONLY=zones_only, USE_SEA=not zones_only, USE_GAP=not zones_only, FADE_ZOOM=40.0)
    g["SEA"] = bg if bg is not None else (0.50, 0.49, 0.41)
    g["render"](cu, cv, px / min(W / 1002, H / 668), path)
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255


def need_of(m):
    """the continent's gaps at GAP_PX a world unit: its land less the zones' cover, less the classic maps"""
    l, r, t, b = m["rect"]
    cols, rows = math.ceil((r - l) * 1002 / GAP_TILE), math.ceil((b - t) * 668 / GAP_TILE)
    C, A, L = G["zones_layer"](m, cols, rows)
    L = L.copy()
    G["apply_sources"](m, L, A, cols * TILE_PX, rows * TILE_PX)
    return L * (1 - A)


def find_regions(m, need, n0):
    l, r, t, b = m["rect"]
    gap = need > 0.25
    lab, k_ = ndimage.label(ndimage.binary_dilation(gap, iterations=MERGE * GAP_PX))
    found = []
    for k in range(1, k_ + 1):
        sel = (lab == k) & gap
        if sel.sum() / GAP_PX ** 2 < MIN_AREA: continue
        ys, xs = np.nonzero(sel)
        found.append((ys.min() / GAP_PX - PAD, xs.min() / GAP_PX - PAD, (ys.max() + 1) / GAP_PX + PAD, (xs.max() + 1) / GAP_PX + PAD))
    out = []
    for n, (y0, x0, y1, x1) in enumerate(sorted(found), n0):
        gy0, gx0 = max(0, int(y0 * GAP_PX)), max(0, int(x0 * GAP_PX))
        bu0, bu1, bv0, bv1 = l + x0 / 1002, l + x1 / 1002, t + y0 / 668, t + y1 / 668
        near = []
        for z in g["zones"]:
            zl, zr, zt, zb = z["rect"]
            ov = max(0, min(zr, bu1) - max(zl, bu0)) * max(0, min(zb, bv1) - max(zt, bv0))
            if ov > 0: near.append((ov, z["name"], 1 / (zr - zl), zr - zl < CITY))
        near.sort(reverse=True)
        land = [x for x in near if not x[3]]
        px = round(min(MAX_PX, max([x[2] for x in land] or [8])))
        area = round(float((need[gy0:int(y1 * GAP_PX), gx0:int(x1 * GAP_PX)] > 0.25).sum()) / GAP_PX ** 2)
        out.append({"file": "%02d_%s.png" % (n, slug(" ".join(x[1] for x in land[:2]) or "gap")), "continent": m["id"], "gapArea": area,
                    "continentName": m["name"], "box": [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
                    "pxPerUnit": px, "size": [int(round((x1 - x0) * px)), int(round((y1 - y0) * px))],
                    "zones": [x[1] for x in near[:5]]})
    return out


def minimap(m, e):
    l, r, t, b = m["rect"]
    asg = g["assign"][m["id"]][0]
    minX, minY, maxX, maxY = (float(asg["Region_%d" % i]) for i in (0, 1, 3, 4))
    x0, y0 = e["box"][:2]; px = e["pxPerUnit"]; W, H = e["size"]
    xs = (np.arange(W) + 0.5) / px + x0
    ys = (np.arange(H) + 0.5) / px + y0
    wy = maxY - xs / ((r - l) * 1002) * (maxY - minY)          # (game yards: y runs west, x north)
    wx = maxX - ys / ((b - t) * 668) * (maxX - minX)
    tx = np.floor(32 - wy / YARDS).astype(int); fx = (32 - wy / YARDS) - tx
    ty = np.floor(32 - wx / YARDS).astype(int); fy = (32 - wx / YARDS) - ty
    o = np.zeros((H, W, 3), np.float32)
    tiles = MINI.get(CONT_OF[m["id"]], {})
    for TX in np.unique(tx):
        cols = np.nonzero(tx == TX)[0]
        for TY in np.unique(ty):
            rows = np.nonzero(ty == TY)[0]
            fid = tiles.get(int(TX) * 64 + int(TY))
            im = g["fetch"](fid) if fid else None
            if im is None: continue
            a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
            n = a.shape[0]
            cy, cx = fy[rows] * n - 0.5, fx[cols] * n - 0.5
            for c in range(3):
                o[rows[:, None], cols[None, :], c] = ndimage.map_coordinates(a[..., c], [cy[:, None].repeat(len(cols), 1), cx[None, :].repeat(len(rows), 0)], order=1, mode="nearest")
    return o


def export(e, need):
    m = conts[e["continent"]]
    l, r, t, b = m["rect"]
    stem = e["file"][:-4]
    x0, y0, x1, y1 = e["box"]; px = e["pxPerUnit"]; W, H = e["size"]
    e["world"] = [round(l + x0 / 1002, 6), round(t + y0 / 668, 6), round(l + x1 / 1002, 6), round(t + y1 / 668, 6)]
    cu, cv = (e["world"][0] + e["world"][2]) / 2, (e["world"][1] + e["world"][3]) / 2
    # (a region can leave the cities' own maps out: a fill goes under them, where they're drawn over it)
    cities = [z for z in g["zones"] if not g["reveal"].get(z["art"])] if e.get("noCities") else []
    for z in cities: g["zones"].remove(z)
    blk = shoot(cu, cv, px, W, H, tmp, True, (0, 0, 0))
    wht = shoot(cu, cv, px, W, H, tmp, True, (1, 1, 1))
    a = np.clip(1 - (wht - blk).mean(axis=2), 0, 1)
    c = np.clip(blk / np.maximum(a[..., None], 1e-3), 0, 1)
    Image.fromarray((np.dstack([c, a]) * 255).round().astype(np.uint8), "RGBA").save(os.path.join(OUT, stem + ".png"))
    shoot(cu, cv, px, W, H, os.path.join(OUT, stem + "_now.png"), False)
    g["zones"].extend(cities)
    # the gap, from the GAP_PX bake, at this size
    ys = (np.arange(H) + 0.5) / px + y0
    xs = (np.arange(W) + 0.5) / px + x0
    gm = ndimage.map_coordinates(need, [ys[:, None].repeat(W, 1) * GAP_PX - 0.5, xs[None, :].repeat(H, 0) * GAP_PX - 0.5], order=1, mode="constant")
    gap = np.clip((gm - 0.25) / 0.5 + 0.5, 0, 1)
    Image.fromarray((gap * 255).astype(np.uint8)).save(os.path.join(OUT, stem + "_gap.png"))
    # the fill area: the continent's own land (not trimmed by the zones' painted seas) less the zones'
    # cover, and a little sea past its coast; less where Blizzard's classic maps are drawn (they stay)
    land = g["field_img"](m)[..., 3] if "land" not in conts[m["id"]] else conts[m["id"]]["land"]
    conts[m["id"]]["land"] = land
    L = ndimage.map_coordinates(land, [(ys / ((b - t) * 668) * land.shape[0] - 0.5)[:, None].repeat(W, 1),
                                       (xs / ((r - l) * 1002) * land.shape[1] - 0.5)[None, :].repeat(H, 0)], order=1, mode="constant")
    # the sea there (no continent land, no zone art): where a painter's coastline past the fill area is kept (gapfills.py)
    Image.fromarray((((L < 0.5) & (a < 0.05)) * 255).astype(np.uint8)).save(os.path.join(OUT, stem + "_sea.png"))
    seed = (L > 0.5) & (a < 0.5)
    out_ = ndimage.distance_transform_edt(~seed) / px if seed.any() else np.full((H, W), 1e9, np.float32)
    coast = np.clip(1 - (out_ - COAST_OUT) / COAST_FADE, 0, 1)
    fill = np.maximum(gap, np.clip(2 * np.maximum(L, coast) * (1 - a), 0, 1))
    u, v = l + xs / 1002, t + ys / 668
    blizz = np.zeros((H, W), np.float32)
    for x in g["gap_art"]():
        al, ar, at, ab = x["rect"]
        a_ = x["img"][..., 3] * (x["mask"] if x["mask"] is not None else 1)
        piece = ndimage.map_coordinates(a_, [((v - at) / (ab - at) * 668 - 0.5)[:, None].repeat(W, 1), ((u - al) / (ar - al) * 1002 - 0.5)[None, :].repeat(H, 0)], order=1, mode="constant")
        blizz = np.maximum(blizz, piece)
    fill = fill * (1 - np.clip(blizz * 1.25, 0, 1))
    Image.fromarray((fill * 255).round().astype(np.uint8)).save(os.path.join(OUT, stem + "_fill.png"))
    Image.fromarray((minimap(m, e) * 255).round().astype(np.uint8)).save(os.path.join(OUT, stem + "_minimap.png"))
    print(stem, "%dx%d at %d px/u" % (W, H, px), flush=True)


mp = os.path.join(GAPS, "regions.json")
manifest = json.load(open(mp)) if os.path.exists(mp) and not find else None
needs = {}
if manifest is None:
    manifest, n = [], 1
    for m in conts.values():
        needs[m["id"]] = need_of(m)
        regions = find_regions(m, needs[m["id"]], n)
        manifest += regions; n += len(regions)
    # (the biggest gaps first, named by their rank)
    manifest = sorted(manifest, key=lambda e: -e["gapArea"])[:TOP]
    for k, e in enumerate(manifest, 1):
        e["rank"], e["file"] = k, "G%02d_%s" % (k, e["file"][3:])
for e in manifest:
    if only and e["file"][:3] not in only: continue
    if e["continent"] not in needs: needs[e["continent"]] = need_of(conts[e["continent"]])
    export(e, needs[e["continent"]])
json.dump(manifest, open(mp, "w", encoding="utf-8", newline="\n"), indent=1)
# where each one is, on its continent
try: font = ImageFont.truetype("arial.ttf", 28)
except Exception: font = ImageFont.load_default()
for cid, need in needs.items():
    m = conts[cid]
    base = np.asarray(Image.open(os.path.join(work, "%d_0.png" % cid)).convert("RGB")).astype(np.float32)
    red = (need[..., None] > 0.25)
    base = base * 0.6 + np.array([255, 40, 40]) * red * 0.4 + base * 0.4 * ~red
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for e in manifest:
        if e["continent"] != cid: continue
        x0, y0, x1, y1 = e["box"]
        d.rectangle([x0 * GAP_PX, y0 * GAP_PX, x1 * GAP_PX, y1 * GAP_PX], outline=(255, 230, 80), width=3)
        d.text((x0 * GAP_PX + 6, y0 * GAP_PX + 4), e["file"][:3], fill=(255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(os.path.join(OUT, "index_%d_%s.png" % (cid, slug(m["name"]))))
print("ok:", len(manifest), "regions")
