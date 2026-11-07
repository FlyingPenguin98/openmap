# Bakes smaller copies of the game's minimap, for showing its detail from further out than its
# own tiles can be drawn (a continent is over a thousand of them; Close.lua draws at most 64):
# the tiles shrunk and laid side by side, at two levels (LEVELS: px a tile, tiles a piece),
# cut into 256-px pieces, each tile tinted as Close.lua tints it (warmed toward the parchment,
# a hint of its zone's colour). Only pieces with a tile in them are written:
# OpenMap/Media/Textures/MapMiniLOD/<continent>_<tiles a piece>_<col>_<row>.tga, listed in
# OpenMap/Data/MinimapLOD.lua. Close.lua crossfades from the coarsest to the game's own tiles.
#
# usage: python -P tools/map-preview/minimaplod.py <db2 dir> <texture cache>
#   OPENMAP_WOW (the game's folder) reads the tiles from the install (tools/casc)
import os, re, sys
import numpy as np
from PIL import Image

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
db2, cache = sys.argv[1:3]
rp = os.path.join(here, "render.py")
src = open(rp, encoding="utf-8").read()
sys.argv = [rp, db2, cache, cache]
g = {"__name__": "minimaplod", "__file__": rp}
exec(compile(src[:src.index("views = sys.argv[4:]")], rp, "exec"), g)   # (its data and texture reading)
OUT = os.path.join(g["TEXDIR"], "MapMiniLOD")
LUA = os.path.join(g["WM"], "MinimapLOD.lua")
PIECE = 256
LEVELS = ((4, 64), (16, 16))    # (tiles a piece, px a tile): a piece is PIECE px either way
YARDS = 1600 / 3                # a tile's side
CONT_MAP = {0: 1415, 1: 1414}
# Close.lua's tint: the parchment warmth, a quarter of the way to the zone's colour at full brightness
PAPER, TONE_SHARE, DEFAULT_TONE = (1, 0.93, 0.80), 0.25, (0.56, 0.45, 0.17)


def minimap_tiles():
    src_ = open(os.path.join(g["WM"], "Minimap.lua"), encoding="utf-8").read()
    out, cur = {}, None
    for line in src_.split("\n"):
        m_ = re.match(r"\s*\[(\d+)\] = \{$", line)          # (a game map's list: retail's are 530, 2444 ...)
        if m_: cur = out.setdefault(int(m_.group(1)), {}); continue
        if cur is not None:
            for k, v in re.findall(r"\[(\d+)\] = (\d+)", line): cur[int(k)] = int(v)
    return out


def tones():
    src_ = open(os.path.join(g["WM"], "Tones.lua"), encoding="utf-8").read()
    return {int(i): (float(r), float(g_), float(b)) for i, r, g_, b in re.findall(r"\[(\d+)\] = \{ ([\d.]+), ([\d.]+), ([\d.]+) \}", src_)}


TONES = tones()


def tint(tone):
    top = max(max(tone), 1e-3)
    return np.array([PAPER[k] + (tone[k] / top - PAPER[k]) * TONE_SHARE for k in range(3)], np.float32)


def tone_at(u, v):
    """the deepest map with a tone whose rectangle holds the world point (as S.ChainAt's last)"""
    best, area = None, 9
    for m in g["maps"]:
        l, r, t, b = m["rect"]
        if l <= u <= r and t <= v <= b and (r - l) * (b - t) < area and m["id"] in TONES:
            best, area = m["id"], (r - l) * (b - t)
    return TONES.get(best, DEFAULT_TONE)


def tile_world(cont, tx, ty):
    """a tile's centre on the world (normalized), through the continent's map rectangle"""
    m = next(x for x in g["maps"] if x["id"] == CONT_MAP[cont])
    l, r, t, b = m["rect"]
    asg = g["assign"][m["id"]][0]
    minX, minY, maxX, maxY = (float(asg["Region_%d" % i]) for i in (0, 1, 3, 4))
    wy, wx = (31.5 - tx) * YARDS, (31.5 - ty) * YARDS            # (game yards: y runs west, x north)
    return l + (maxY - wy) / (maxY - minY) * (r - l), t + (maxX - wx) / (maxX - minX) * (b - t)


os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith(".tga"): os.remove(os.path.join(OUT, f))
listing = {}
for cont, tiles in sorted(minimap_tiles().items()):
    small = {per: {} for per, _ in LEVELS}
    for n, (key, fid) in enumerate(sorted(tiles.items())):
        im = g["fetch"](fid)
        if im is None: continue
        tx, ty = key // 64, key % 64
        rgb = np.asarray(im.convert("RGB")).astype(np.float32) / 255 * tint(tone_at(*tile_world(cont, tx, ty)))
        img = Image.fromarray((np.clip(rgb, 0, 1) * 255).round().astype(np.uint8))
        for per, px in LEVELS: small[per][(tx, ty)] = img.resize((px, px), Image.LANCZOS)
        if n % 200 == 0: print("  continent", cont, n, "of", len(tiles), flush=True)
    listing[cont] = []
    for per, px in LEVELS:
        pieces = sorted({(tx // per, ty // per) for tx, ty in small[per]})
        for col, row in pieces:
            canvas = Image.new("RGBA", (PIECE, PIECE), (0, 0, 0, 0))
            for (tx, ty), im in small[per].items():
                if tx // per == col and ty // per == row:
                    canvas.paste(im, ((tx - col * per) * px, (ty - row * per) * px))
            canvas.save(os.path.join(OUT, "%d_%d_%d_%d.tga" % (cont, per, col, row)))
        listing[cont].append((per, pieces))
        print("continent", cont, "level", per, len(pieces), "pieces", flush=True)
with open(LUA, "w", encoding="utf-8", newline="\n") as f:
    f.write("-- Smaller copies of the game's minimap, for its detail from further out (Close.lua):\n")
    f.write("-- [continent] = { { tiles a piece, { col * 64 + row, ... } }, ... }, finest first; each piece is\n")
    f.write("-- MapMiniLOD/<continent>_<tiles a piece>_<col>_<row>, covering minimap tiles col * n .. and row * n ..\n")
    f.write("-- Generated by tools/map-preview/minimaplod.py; regenerate rather than edit.\n\n")
    f.write("local _, ns = ...\n\nns.MapMinimapLOD = {\n")
    for cont, levels in sorted(listing.items()):
        f.write("\t[%d] = {\n" % cont)
        for per, pieces in levels:
            f.write("\t\t{ %d, { %s } },\n" % (per, ", ".join(str(c * 64 + r) for c, r in pieces)))
        f.write("\t},\n")
    f.write("}\n")
size = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT))
print("ok: %d pieces, %.1f MB" % (len(os.listdir(OUT)), size / 1e6))
