# Measures how far each zone's painted art sits from the ground it shows, so roads meet
# across zone borders. Blizzard's zone paintings were drawn by hand: a few are shifted a
# little against their placement, so their roads miss the neighbour's (Elwynn into
# Redridge). The game's own minimap is the ground truth: each zone's art is compared with
# the minimap under it (the edges in both: roads, rivers, coasts, cliffs) over a range of
# small shifts, and the best one is reported ("NUDGE" where it's clear and big enough to
# matter). Report only, for now: the first full run (October 2026) found every zone within
# about a pixel of the ground, so the addon applies no nudges. The --sheet picture shows
# each zone with the minimap's edges in red over it, as placed and as nudged.
#
# usage: python -P tools/map-tuning/align.py <db2 dir> <texture cache> [zone name ...] [--sheet out.png]
import math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
prev = os.path.join(here, "..", "map-preview")
db2, cache = sys.argv[1:3]
args = sys.argv[3:]
sheet_path = None
if "--sheet" in args:
    i = args.index("--sheet"); sheet_path = args[i + 1]; del args[i:i + 2]
only = set(args)
sys.argv = ["render.py", db2, cache, os.path.join(cache, "_preview")]
g = {"__name__": "align", "__file__": os.path.join(prev, "render.py")}
src = open(os.path.join(prev, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)

YARDS = 1600 / 3                # per minimap tile
SEARCH = 14                     # art px each way
MIN_SHIFT, MIN_GAIN = 1.5, 0.08 # nudge only if it moves this far (art px) and beats no shift by this much

def minimap_tiles():
    src_ = open(os.path.join(g["WM"], "Minimap.lua"), encoding="utf-8").read()
    out, cur = {}, None
    for line in src_.split("\n"):
        m_ = re.match(r"\s*\[(\d)\] = \{", line)
        if m_: cur = out.setdefault(int(m_.group(1)), {}); continue
        if cur is not None:
            for k, v in re.findall(r"\[(\d+)\] = (\d+)", line): cur[int(k)] = int(v)
    return out
MINI = minimap_tiles()
CONT = {1415: 0, 1414: 1}

def continent_of(m):
    l, r, t, b = m["rect"]
    return next(c for c in g["maps"] if c["kind"] == 2 and c["rect"][0] <= (l + r) / 2 <= c["rect"][1] and c["rect"][2] <= (t + b) / 2 <= c["rect"][3])

_tile = {}
def tile_lum(fid):
    if fid not in _tile:
        im = g["fetch"](fid)
        _tile[fid] = None if im is None else np.asarray(im.convert("L")).astype(np.float32) / 255
    return _tile[fid]

def minimap_under(m, H=668, W=1002):
    """the minimap's brightness on the zone art's pixel grid (NaN where there's no tile)"""
    c = continent_of(m)
    a = g["assign"][c["id"]][0]
    minX, minY, maxX, maxY = (float(a["Region_%d" % i]) for i in (0, 1, 3, 4))
    l, r, t, b = m["rect"]; cl, cr, ct, cb = c["rect"]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    u = l + (xs + 0.5) / W * (r - l); v = t + (ys + 0.5) / H * (b - t)
    wy = maxY - (u - cl) / (cr - cl) * (maxY - minY)
    wx = maxX - (v - ct) / (cb - ct) * (maxX - minX)
    fx, fy = 32 - wy / YARDS, 32 - wx / YARDS
    tx, ty = np.floor(fx).astype(int), np.floor(fy).astype(int)
    out = np.full((H, W), np.nan, np.float32)
    keys = tx * 64 + ty
    for key in np.unique(keys):
        fid = MINI.get(CONT[c["id"]], {}).get(int(key))
        lum = tile_lum(fid) if fid else None
        if lum is None: continue
        n = lum.shape[0]; sel = keys == key
        out[sel] = ndimage.map_coordinates(lum, [np.clip((fy[sel] % 1) * n - 0.5, 0, n - 1), np.clip((fx[sel] % 1) * n - 0.5, 0, n - 1)], order=1)
    return out

def edges(img, mask):
    """edge strength at road / river scale, normalized within the mask"""
    gx, gy = ndimage.sobel(ndimage.gaussian_filter(img, 1.2), 1), ndimage.sobel(ndimage.gaussian_filter(img, 1.2), 0)
    e = np.hypot(gx, gy) * mask
    s = e[mask > 0].std() if (mask > 0).any() else 1
    return (e - e[mask > 0].mean()) / max(s, 1e-6) * mask

def measure(m):
    art = g["over"](m)
    if art is None or not art[..., 3].any(): return None
    mini = minimap_under(m)
    have = ~np.isnan(mini)
    inside = ndimage.binary_erosion((art[..., 3] > 0.9) & have, iterations=SEARCH + 4)
    if inside.sum() < 20000: return None
    lum = art[..., :3].mean(2)
    ea = edges(lum, inside.astype(np.float32))
    em = edges(np.nan_to_num(mini), have.astype(np.float32))
    best, scores = None, {}
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            # the art moved by (dx, dy) lines up with the minimap where...
            sh = np.roll(np.roll(em, -dy, 0), -dx, 1)
            sc = float((ea * sh).sum() / inside.sum())
            scores[(dx, dy)] = sc
    (dx, dy), top = max(scores.items(), key=lambda kv: kv[1])
    # sub-pixel: parabola through the neighbours
    def para(a, b, c): d = a - 2 * b + c; return 0 if d == 0 else 0.5 * (a - c) / d
    if abs(dx) < SEARCH and abs(dy) < SEARCH:
        fx = dx + para(scores[(dx - 1, dy)], top, scores[(dx + 1, dy)])
        fy = dy + para(scores[(dx, dy - 1)], top, scores[(dx, dy + 1)])
    else:
        fx, fy = dx, dy
    zero = scores[(0, 0)]
    others = sorted(v for k, v in scores.items() if max(abs(k[0] - dx), abs(k[1] - dy)) > 4)
    return {"dx": -fx, "dy": -fy, "score": top, "zero": zero, "runner": others[-1] if others else 0, "art": art, "mini": mini}

results = {}
zones = [m for m in g["zones"] if (not only or m["name"] in only)]
for m in zones:
    r = measure(m)
    if r is None: print("%-24s (no minimap / too small)" % m["name"], flush=True); continue
    shift = math.hypot(r["dx"], r["dy"])
    gain = (r["score"] - r["zero"]) / max(abs(r["zero"]), 1e-6)
    sharp = (r["score"] - r["runner"]) / max(abs(r["score"]), 1e-6)
    ok = shift >= MIN_SHIFT and gain >= MIN_GAIN and sharp > 0.05 and max(abs(r["dx"]), abs(r["dy"])) < SEARCH - 0.5
    print("%-24s shift %+5.1f %+5.1f px  score %.3f (no shift %.3f, gain %+.0f%%, sharp %.0f%%) %s" % (
        m["name"], r["dx"], r["dy"], r["score"], r["zero"], gain * 100, sharp * 100, "NUDGE" if ok else ""), flush=True)
    r["ok"] = ok
    results[m["id"]] = (m, r)

if sheet_path:
    rows = [(m, r) for m, r in results.values()]
    sheet = Image.new("RGB", (2 * 420, max(1, len(rows)) * 290), (20, 20, 20))
    for k, (m, r) in enumerate(rows):
        mini = np.nan_to_num(r["mini"])
        for j, (dx, dy) in enumerate(((0, 0), (r["dx"], r["dy"]))):
            art = ndimage.shift(r["art"][..., :3], (dy, dx, 0), order=1)
            # the minimap's edges in red over the art: lined up, red sits on the roads
            e = np.clip(edges(mini, np.ones_like(mini)) / 4, 0, 1)[..., None]
            im = art * (1 - e * 0.8) + np.array([1, 0.1, 0.1]) * e * 0.8
            tile = Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).resize((420, 280))
            ImageDraw.Draw(tile).text((6, 4), "%s %s" % (m["name"], "as placed" if j == 0 else "nudged %+.1f,%+.1f" % (dx, dy)), fill=(255, 255, 0))
            sheet.paste(tile, (j * 420, k * 290))
    sheet.save(sheet_path)
