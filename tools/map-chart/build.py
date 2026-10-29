# The sea chart (Options' Responsive ocean & border): Santiago Reyes's sea, ornaments and frame round the game's world map,
# laid out for the window's shape. From his layers (art/drawn/chart/, tools/map-chart/export.py) into:
#   OpenMap/Media/Textures/MapChart/
#     Paper.blp        his sheet and sea (the chart is cut from it: Chart.lua)
#     Backdrop.blp     the dark ground past the sheet's torn edge, made to tile
#     Web.blp          his navigation lines, but each rose's own rays (they move with the rose)
#     Rays<n>.blp      rose n's rays
#     Ornament<n>.blp  each ornament (compass roses, sea creatures, ships, astrolabe, vignette)
#     Frame<n>.blp     the frame's corners
#     SeamX.tga, SeamY.tga   (masks) the cross-fade where two cuts of the paper overlap, its edge wavy
#     Middle.tga       (mask) the game's world map in the chart: its continents, islands and coasts whole, and the
#                      sea between the continents; its sea fading out from there into his (in place of the world
#                      map's own edge fade)
#   OpenMap/Data/Chart.lua   where everything goes (tools/map-chart/layout.py), and each ornament's place
#                            for each window shape
#
# usage: python -P tools/map-chart/build.py <db2 dir> <texture cache>   (as render.py, which fills the cache)
import csv, json, math, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools", "map-textures"))
import blp
import layout as LO

SRC = os.path.join(REPO, "art", "drawn", "chart")
TEX = os.path.join(REPO, "OpenMap", "Media", "Textures")
OUT = os.path.join(TEX, "MapChart")
DATA = os.path.join(REPO, "OpenMap", "Data", "Chart.lua")
WORLD = 947
ROSES = [(740, 748), (3292, 2524)]   # where each compass rose's rays meet (his sheet px: found by voting, below)
RAY_TOL = 7.0                   # sheet px off a ray through a rose's centre that still counts as on it
LINE_FADE = 420                 # his lines fade out over this before his sheet's edge (so moved, none stops short)
MIDDLE_CLOSE = 150             # the world map's art px: the sea between its lands this narrow is kept with them
MIDDLE_KEEP, MIDDLE_FADE = 25, 120   # ... and the sea round all that kept this far out, then fading over this
MIDDLE_RIM = 0.3                # the share of OpenMap's wide edge fade left off (the art's burnt rim shows as a halo)
SCALE = 1.8                     # the game's world this much bigger against his art than he drew it (his sea, ornaments
                                #  and frame read smaller round it, the continents bigger in the window)
SEA_DESAT = 0.35                # the world map's open sea eased toward his sea: this much colour out, then tinted
ORN_LONG = 1024                 # an ornament's or frame piece's texture: its longer side at most this
ASPECTS = (0.35, 4.0, 1.04)     # window shapes a layout is worked out for: least, most, step (a ratio)
PLACE_K = 0.25                  # working px per sheet px for the ornaments' places


def rgba(name):
    return np.asarray(Image.open(os.path.join(SRC, name)).convert("RGBA"), np.float32) / 255


def pow2(n):
    p = 16
    while p < n:
        p *= 2
    return p


def save_blp(name, img):
    """img (h, w, 4) 0..1, straight alpha, on the next power-of-two canvas: its texcoords (u1, v1)."""
    h, w = img.shape[:2]
    H, W = pow2(h), pow2(w)
    canvas = np.zeros((H, W, 4), np.float32)
    canvas[:h, :w] = img
    if w < W:   # (filtering at the edge reads the next texel: carry the edge's colour, clear, over)
        canvas[:h, w:, :3] = img[:, -1:, :3]
    if h < H:
        canvas[h:, :, :3] = canvas[h - 1:h, :, :3]
    blp.write(os.path.join(OUT, name + ".blp"), np.round(np.clip(canvas, 0, 1) * 255).astype(np.uint8))
    return w / W, h / H


def save_mask(name, alpha):
    a = np.clip(alpha, 0, 1)
    img = np.dstack([np.full(a.shape, 255, np.uint8)] * 3 + [np.round(a * 255).astype(np.uint8)])
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, name + ".tga"))


def resized(img, scale):
    h, w = img.shape[:2]
    W, H = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    if (W, H) == (w, h):
        return img
    # (premultiplied, so clear pixels' colour doesn't bleed in)
    pm = img.copy()
    pm[..., :3] *= pm[..., 3:4]
    out = np.dstack([np.asarray(Image.fromarray(pm[..., c]).resize((W, H), Image.LANCZOS)) for c in range(4)])
    a = np.clip(out[..., 3:4], 0, 1)
    out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
    out[..., 3:4] = a
    return np.clip(out, 0, 1)


# ------------------------------------------------------------------------------- the world on his sheet

def world_on_sheet(db2, continents):
    """(A, bx, by): his sheet px = A * world unit + b. His two continent pictures are the game's continent maps
    whole: their boxes on his sheet against their rectangles on Azeroth's map (as GetMapRectOnMap)."""
    rows = list(csv.DictReader(open(os.path.join(db2, "UiMapAssignment.csv"), encoding="utf-8")))
    by = {}
    for r in rows:
        by.setdefault(int(r["UiMapID"]), []).append(r)
    f = lambda r, k: float(r[k])
    fits = []
    for mid, (x0, y0, x1, y1) in continents.items():
        a = by[int(mid)][0]
        w = next(r for r in by[WORLD] if r["MapID"] == a["MapID"])
        U = lambda y: f(w, "UiMin_0") + (f(w, "Region_4") - y) / (f(w, "Region_4") - f(w, "Region_1")) * (f(w, "UiMax_0") - f(w, "UiMin_0"))
        V = lambda x: f(w, "UiMin_1") + (f(w, "Region_3") - x) / (f(w, "Region_3") - f(w, "Region_0")) * (f(w, "UiMax_1") - f(w, "UiMin_1"))
        l, r_ = U(f(a, "Region_4")), U(f(a, "Region_1"))
        t, b = V(f(a, "Region_3")), V(f(a, "Region_0"))
        um0, um1, uM0, uM1 = f(a, "UiMin_0"), f(a, "UiMin_1"), f(a, "UiMax_0"), f(a, "UiMax_1")
        w_, h_ = (r_ - l) / (uM0 - um0), (b - t) / (uM1 - um1)
        L, T = l - um0 * w_, t - um1 * h_
        ax, ay = (x1 - x0) / (w_ * 1002), (y1 - y0) / (h_ * 668)
        fits.append((ax, ay, x0 - L * 1002 * ax, y0 - T * 668 * ay))
    A = sum(a + b for a, b, _, _ in fits) / (2 * len(fits))
    return A, sum(f[2] for f in fits) / len(fits), sum(f[3] for f in fits) / len(fits)


def world_art(db2, cache):
    """The world map's art (1002 x 668, its px), from the client's tiles in the texture cache."""
    art_id = next(int(r["UiMapArtID"]) for r in csv.DictReader(open(os.path.join(db2, "UiMapXMapArt.csv"), encoding="utf-8"))
                  if int(r["UiMapID"]) == WORLD and r["PhaseID"] == "0")
    img = Image.new("RGBA", (1002, 668), (0, 0, 0, 0))
    for r in csv.DictReader(open(os.path.join(db2, "UiMapArtTile.csv"), encoding="utf-8")):
        if int(r["UiMapArtID"]) == art_id and r["LayerIndex"] == "0":
            p = os.path.join(cache, "%s.blp" % r["FileDataID"])
            if not os.path.exists(p):
                sys.exit("the world map's tile %s isn't in the texture cache: run tools/map-preview/render.py first" % r["FileDataID"])
            img.paste(Image.open(p).convert("RGBA"), (int(r["ColIndex"]) * 256, int(r["RowIndex"]) * 256))
    return np.asarray(img, np.float32)[..., :3] / 255


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def world_land(art):
    """Its land: OpenMap's continents with their coastal band (MapBackLand/947), and its islands, found as compact
    saturated gold patches clear of the art's burnt edge (whose sea is as gold)."""
    land = np.asarray(Image.open(os.path.join(TEX, "MapBackLand", "947.tga")).convert("RGBA").getchannel("A")
                      .resize((1002, 668), Image.BILINEAR)) > 127
    mx, mn = art.max(2), art.min(2)
    sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0)
    gold = ndi.binary_opening((sat > 0.62) & (mx > 0.45) & (art[..., 0] >= art[..., 2]), iterations=2)   # (no ink strokes)
    gold = ndi.binary_fill_holes(ndi.binary_closing(gold, iterations=3))
    lab, _ = ndi.label(gold)
    H, W = land.shape
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        piece = lab[sl] == k
        area = piece.sum()
        box = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)
        fill = area / ((box[3] - box[1]) * (box[2] - box[0]))
        if 120 <= area <= 20000 and fill > 0.45 and min(box[0], box[1], W - box[2], H - box[3]) > 30 and not (land[sl] & piece).any():
            land[sl] |= piece
    return land


def middle_mask(art):
    """The world map's alpha in the chart (1002 x 668, its px): its land whole, and the sea between its lands
    (closed over MIDDLE_CLOSE: the Maelstrom, the islands between the continents); the sea round that kept a
    little way out and fading over MIDDLE_FADE, so the fade follows the coasts; no further than OpenMap's wide
    edge fade less its rim (the art ends there)."""
    land = world_land(art)
    pad = MIDDLE_CLOSE + 4
    big = np.pad(land, pad)
    out = ndi.distance_transform_edt(~big) <= MIDDLE_CLOSE
    kept = (ndi.distance_transform_edt(out) > MIDDLE_CLOSE)[pad:-pad, pad:-pad] | land
    fade = smooth(1 - (ndi.distance_transform_edt(~kept) - MIDDLE_KEEP) / MIDDLE_FADE)
    wide = np.asarray(Image.open(os.path.join(TEX, "MapFeatherWide.tga")).convert("RGBA").getchannel("A")
                      .resize((1002, 668), Image.BILINEAR), np.float32) / 255
    edge = smooth((wide - MIDDLE_RIM) / (1 - MIDDLE_RIM))
    core = smooth(1 - (ndi.distance_transform_edt(~land) - 4) / 8)   # (its land never faded)
    return np.maximum(core, fade * edge), land


def sea_tint(art, land, middle, paper, A, bx, by):
    """How the world map's open sea is eased toward his: SEA_DESAT of its colour out, then a tint (vertex colour,
    at most 1) from the mean of its sea where it fades against the mean of his paper just past it."""
    ring = (middle > 0.2) & (middle < 0.85) & ~ndi.binary_dilation(land, iterations=6)
    world = art[ring].mean(0)
    lum = world @ np.array([0.299, 0.587, 0.114])
    world = world * (1 - SEA_DESAT) + lum * SEA_DESAT
    # his paper (half his sheet's size) just past the middle's edge
    k = paper.shape[0] / LO.SIZE
    m = np.asarray(Image.fromarray(middle).resize((max(1, int(1002 * A * k)), max(1, int(668 * A * k))), Image.BILINEAR))
    sheet = np.zeros(paper.shape[:2], np.float32)
    X, Y = int(round(bx * k)), int(round(by * k))
    y0, x0 = max(0, Y), max(0, X)
    y1, x1 = min(sheet.shape[0], Y + m.shape[0]), min(sheet.shape[1], X + m.shape[1])
    sheet[y0:y1, x0:x1] = m[y0 - Y:y1 - Y, x0 - X:x1 - X]
    d = ndi.distance_transform_edt(sheet < 0.2)
    near = (d > 20 * k) & (d < 300 * k) & (paper[..., 3] > 0.9)
    his = paper[near][:, :3].mean(0)
    t = his / np.maximum(world, 1e-3)
    t = t / max(1.0, t.max())
    print("sea: the world's %s, his %s, tint %s" % (np.round(world, 3), np.round(his, 3), np.round(t, 3)))
    return [round(float(v), 3) for v in t] + [SEA_DESAT]


# ----------------------------------------------------------------------------------------- his lines

def split_lines(lines):
    """His navigation lines: each rose's own rays (a pixel whose line points at the rose's centre), and the rest."""
    a = lines[..., 3]
    gy, gx = np.gradient(ndi.gaussian_filter(a, 1.5))
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 5.0) for v in (gx * gx, gy * gy, gx * gy))
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-9)
    H, W = a.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = np.cos(theta), np.sin(theta)
    on = a > 0.01
    owner = np.zeros(a.shape, np.int8)
    best = np.full(a.shape, np.inf, np.float32)
    for k, (cx, cy) in enumerate(ROSES, 1):
        d = np.abs((cx - xx) * dy - (cy - yy) * dx)
        take = on & (d < RAY_TOL) & (d < best) & (coh > 0.5)
        owner[take] = k
        best[take] = d[take]
    for k in range(1, len(ROSES) + 1):   # (crossings and thin gaps: what most of their neighbours are)
        near = ndi.uniform_filter((owner == k).astype(np.float32), 9)
        owner[on & (owner == 0) & (near > 0.35)] = k
    t = np.arange(W, dtype=np.float32)
    d = np.minimum(t - 80, LO.SIZE - 40 - t)
    edge = np.clip(d / LINE_FADE, 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    fade = edge[:, None] * edge[None, :]
    parts = []
    for k in range(len(ROSES) + 1):
        p = lines.copy()
        p[..., 3] = np.where(owner == k, a, 0) * fade
        parts.append(p)
    return parts


def crop(img, pad=4):
    ys, xs = np.nonzero(img[..., 3] > 0.004)
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(img.shape[1], xs.max() + 1 + pad), min(img.shape[0], ys.max() + 1 + pad)
    return img[y0:y1, x0:x1], (int(x0), int(y0), int(x1), int(y1))


def pieces(layer, grow_px, speck=0):
    """Separate pieces of a layer (its parts apart by more than grow_px), each with the specks (pieces smaller
    than `speck` across) nearest it: [(image, box)]."""
    a = layer[..., 3] > 0.04
    lab, n = ndi.label(ndi.binary_dilation(a, iterations=grow_px))
    found = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        ys, xs = np.nonzero((lab[sl] == k) & (layer[sl][..., 3] > 0.01))
        box = (sl[1].start + xs.min(), sl[0].start + ys.min(), sl[1].start + xs.max() + 1, sl[0].start + ys.max() + 1)
        found.append({"k": k, "box": box})
    big = [f for f in found if max(f["box"][2] - f["box"][0], f["box"][3] - f["box"][1]) >= speck]
    for f in found:
        if f in big:
            continue
        cx, cy = (f["box"][0] + f["box"][2]) / 2, (f["box"][1] + f["box"][3]) / 2
        owner = min(big, key=lambda b: max(b["box"][0] - cx, cx - b["box"][2], b["box"][1] - cy, cy - b["box"][3], 0))
        owner.setdefault("specks", []).append(f)
    out = []
    for b in big:
        ks = [b["k"]] + [s["k"] for s in b.get("specks", [])]
        boxes = [b["box"]] + [s["box"] for s in b.get("specks", [])]
        x0, y0 = min(x[0] for x in boxes), min(x[1] for x in boxes)
        x1, y1 = max(x[2] for x in boxes), max(x[3] for x in boxes)
        img = layer[y0:y1, x0:x1].copy()
        img[..., 3] *= np.isin(lab[y0:y1, x0:x1], ks)
        out.append((img, (int(x0), int(y0), int(x1), int(y1))))
    out.sort(key=lambda p: (p[1][1], p[1][0]))   # (top to bottom, then left to right: a stable order)
    return out


def tileable(img, size):
    """A size-px piece of img made to tile: blended with itself shifted half a tile, through a soft cross."""
    t = img[:size, :size].astype(np.float32)
    shifted = np.roll(np.roll(t, size // 2, 0), size // 2, 1)
    u = np.abs(np.arange(size) - size / 2 + 0.5) / (size / 2)
    w = np.clip(np.maximum(u[:, None], u[None, :]) * 1.6 - 0.6, 0, 1)[..., None]   # (1 at the tile's edge)
    return t * (1 - w) + shifted * w


def seam(axis_len, across, seed):
    """A cross-fade mask: 0 at its start to 1 at its end along `axis_len`, its edge bent by smooth noise across."""
    rng = np.random.default_rng(seed)
    u = np.arange(across, dtype=np.float32) / across
    nz = sum(np.sin(u * f * 2 * np.pi + rng.uniform(0, 2 * np.pi)) / f for f in (1.0, 2.3, 5.1, 11.0))
    r = (np.arange(axis_len, dtype=np.float32) + 0.5) / axis_len
    w = np.clip(r[None, :] + 0.9 * nz[:, None] * (r * (1 - r))[None, :], 0, 1)
    return w * w * (3 - 2 * w)


def lua(v, ind=""):
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(lua(x) for x in v) + " }"
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".") if v != int(v) else "%d" % v
    return str(v)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python -P tools/map-chart/build.py <db2 dir> <texture cache>")
    sheet = json.load(open(os.path.join(SRC, "sheet.json"), encoding="utf-8"))
    assert sheet["size"] == LO.SIZE
    A, bx, by = world_on_sheet(sys.argv[1], sheet["continents"])   # (before anything's cleared: it needs the CSVs)
    art = world_art(sys.argv[1], sys.argv[2])
    # the world SCALE times bigger, about the world map's middle (Chart.lua does the same with `scale`)
    cx, cy = bx + A * 501, by + A * 334
    A = A * SCALE
    bx, by = cx - A * 501, cy - A * 334
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    print("world map on his sheet: x %.0f..%.0f, y %.0f..%.0f" % (bx, bx + 1002 * A, by, by + 668 * A))

    middle, land = middle_mask(art)
    save_mask("Middle", np.asarray(Image.fromarray(middle).resize((512, 512), Image.BILINEAR)))
    # its box on his sheet where it's at least half there: the chart's middle, never covered
    ys, xs = np.nonzero(middle > 0.5)
    world = (bx + xs.min() * A, by + ys.min() * A, bx + (xs.max() + 1) * A, by + (ys.max() + 1) * A)
    world = tuple(int(round(v)) for v in world)

    paper = rgba("paper.png")
    pu, pv = save_blp("Paper", paper)
    tint = sea_tint(art, land, middle, paper, A, bx, by)
    back = tileable(rgba("backdrop.png"), 1024)
    save_blp("Backdrop", resized(back, 0.5))
    save_mask("SeamX", seam(256, 64, 1))
    save_mask("SeamY", seam(256, 64, 2).T)

    lines = rgba("lines.png")
    web, *rays = split_lines(lines)
    wu, wv = save_blp("Web", resized(web, 0.5))
    ray_info = []
    for k, r in enumerate(rays, 1):
        img, box = crop(r)
        u1, v1 = save_blp("Rays%d" % k, resized(img, 0.5))
        ray_info.append(list(box) + [u1, v1])
    del lines, web, rays

    orn = rgba("ornaments.png")
    ornaments = pieces(orn, 60, speck=150)
    del orn
    orn_info = []
    for k, (img, box) in enumerate(ornaments, 1):
        sc = min(1.0, ORN_LONG / max(img.shape[:2]))
        u1, v1 = save_blp("Ornament%d" % k, resized(img, sc))
        orn_info.append(list(box) + [u1, v1])
    rose_of = []
    for rx, ry in ROSES:
        rose_of.append([next(k for k, (_, b) in enumerate(ornaments, 1) if b[0] <= rx <= b[2] and b[1] <= ry <= b[3]), rx, ry])
    frame = rgba("frame.png")
    frame_info = []
    for k, (img, box) in enumerate(pieces(frame, 30), 1):
        sc = min(1.0, ORN_LONG / max(img.shape[:2]))
        u1, v1 = save_blp("Frame%d" % k, resized(img, sc))
        # (the wooden corners smaller than he drew them; his paper's curled corner is the paper's own edge: as it is)
        frame_info.append(list(box) + [u1, v1, LO.FRAME if box[2] - box[0] > 1000 else 1])
    del frame

    # the ornaments' places, per window shape
    K = PLACE_K
    mid_sheet = np.zeros((int(LO.SIZE * K), int(LO.SIZE * K)), np.float32)
    m_img = Image.fromarray(middle).resize((max(1, int(1002 * A * K)), max(1, int(668 * A * K))), Image.BILINEAR)
    X, Y = int(round(bx * K)), int(round(by * K))
    mid_sheet[Y:Y + m_img.height, X:X + m_img.width] = np.asarray(m_img)[:mid_sheet.shape[0] - Y, :mid_sheet.shape[1] - X]
    placer = LO.Placer([{"box": box, "alpha": np.asarray(Image.fromarray(img[..., 3]).resize(
        (max(1, int((box[2] - box[0]) * K)), max(1, int((box[3] - box[1]) * K))), Image.BILINEAR))}
        for img, box in ornaments], mid_sheet, world, K)
    lo, hi, step = ASPECTS
    aspects, a = [], lo
    while a < hi * 1.0001:
        aspects.append(a)
        a *= step
    layouts = []
    for asp in aspects:
        where, (cw, ch) = placer.place(asp)
        row = [round(asp, 4)]
        for (sc, nx, ny), (img, box) in zip(where, ornaments):
            w, h = (box[2] - box[0]) * sc, (box[3] - box[1]) * sc
            anc = LO.anchored((nx, ny, nx + w, ny + h), cw, ch, world)
            row.append([anc[0], round(anc[1], 1), anc[2], round(anc[3], 1), round(sc, 3)])
        layouts.append(row)
        print("layout for %.3f: %s" % (asp, " ".join("%d%%" % round(p[4] * 100) for p in row[1:])), flush=True)

    with open(DATA, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- The sea chart (Options' Responsive ocean & border, Map/Chart.lua): Santiago Reyes's sea, ornaments and frame round the\n"
                "-- game's world map, laid out for the window's shape. Boxes are on his sheet (px of its %d square); the\n"
                "-- textures are in Media/Textures/MapChart/ (u, v: the part of each one used).\n"
                "-- Generated by tools/map-chart/build.py from art/drawn/chart/; regenerate rather than edit.\n\n" % LO.SIZE)
        f.write("local _, ns = ...\n\n")
        f.write("ns.MapChart = {\n")
        f.write("\tsize = %d,\n" % LO.SIZE)
        f.write("\tcontinents = { [1414] = %s, [1415] = %s },   -- his pictures of the game's continent maps (they place the world)\n"
                % (lua(sheet["continents"]["1414"]), lua(sheet["continents"]["1415"])))
        f.write("\tscale = %s,   -- the world this much bigger against his art than he drew it (about the world map's middle)\n" % lua(SCALE))
        f.write("\tworld = %s,   -- the game's map in the middle, where it's at least half there: centred, never covered\n" % lua(list(world)))
        f.write("\tseaTint = %s,   -- the world map's open sea eased toward his: vertex colour, and desaturation\n" % lua(tint))
        f.write("\tpad = %d, edge = %d, seam = %d, cut = { %d, %d },   -- (tools/map-chart/layout.py: PAD, EDGE, SEAM, EDGE_CUT, INNER_CUT)\n"
                % (LO.PAD, LO.EDGE, LO.SEAM, LO.EDGE_CUT, LO.INNER_CUT))
        f.write("\tpaper = { %s, %s },   -- Paper: his whole sheet\n" % (lua(pu), lua(pv)))
        f.write("\tweb = { %s, %s },   -- Web: his whole sheet, at half size\n" % (lua(wu), lua(wv)))
        f.write("\trays = {   -- Rays<n>: box, u, v\n")
        for r in ray_info:
            f.write("\t\t%s,\n" % lua(r))
        f.write("\t},\n")
        f.write("\troses = %s,   -- each rose's rays: the ornament they go with, and where they meet\n" % lua(rose_of))
        f.write("\tornaments = {   -- Ornament<n>: box, u, v\n")
        for o in orn_info:
            f.write("\t\t%s,\n" % lua(o))
        f.write("\t},\n")
        f.write("\tframe = {   -- Frame<n>: box, u, v, scale (each pinned to its corner, its scale about it)\n")
        for o in frame_info:
            f.write("\t\t%s,\n" % lua(o))
        f.write("\t},\n")
        f.write("\t-- each window shape (width / height): every ornament's place, per axis the edge it's measured from\n"
                "\t-- (0: the chart's near edge, 1: the middle's, 2: the chart's far edge) and how far; and its scale\n")
        f.write("\tlayouts = {\n")
        for row in layouts:
            f.write("\t\t{ %s,\n" % lua(row[0]))
            for p in row[1:]:
                f.write("\t\t\t%s,\n" % lua(p))
            f.write("\t\t},\n")
        f.write("\t},\n}\n")
    print("wrote", os.path.relpath(DATA, REPO), "and", len(os.listdir(OUT)), "textures")


if __name__ == "__main__":
    main()
