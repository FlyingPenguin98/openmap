# Out-of-game preview of the stitched map for a client whose world and continent art is painted whole
# (retail: its Client.lua says sea = false): MapPaper past the world's art (Territories.lua's
# MapPaperOut), the world's art to its torn edge (MapBackLand/947), each continent's over it, each
# zone's base art with its explored-area pieces through its territory (MapTerritory,
# tools/map-preview/territory.py), the cities over their zones, each fading in by the zoom as Stitch.lua
# fades them (its constants mirrored below).
# WoW Forever's map is render.py's.
#
# usage: python -P tools/map-preview/whole.py <db2 dir> <texture cache> <out dir> name=u,v,zoom ...
#   (OPENMAP_CLIENT: the client, tools/clients.py; u, v: the view's centre on Azeroth's map, 0..1;
#   zoom: 1 = the whole world, as WorldMap.lua's; name=@Zone Name,zoom centres on that map)
#   OPENMAP_SIZE=1400x900: the image's size. Textures missing from the cache are fetched from wago.tools.
import csv, math, os, re, sys, time, urllib.request
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients, uimap

# Stitch.lua's (and Data/<client>/Client.lua's) fades: zoom ranges, in the zoom the layers fade by
CONT_IN = (1.3, 1.7)
CITY_FADE = (0.2, 0.4)
FEATHER_WIDE_EDGE = 0.18        # (make.py's MapFeatherWide)
OW, OH = (int(v) for v in os.environ.get("OPENMAP_SIZE", "1400x900").split("x"))


def smooth(z, rng):
    t = max(0.0, min(1.0, (z - rng[0]) / (rng[1] - rng[0])))
    return t * t * (3 - 2 * t)


def client_tune():
    """Client.lua's zoom and detailFade"""
    src = open(os.path.join(clients.DATA, "Client.lua"), encoding="utf-8").read()
    zoom = re.search(r"\bzoom = ([\d.]+)", src)
    fade = re.search(r"detailFade = \{ ([\d.]+), ([\d.]+) \}", src)
    sea = re.search(r"seaColor = \{ ([\d.]+), ([\d.]+), ([\d.]+) \}", src)
    dens = re.search(r"detailDensity = ([\d.]+)", src)
    global SEA_COLOR, DETAIL_DENSITY, PAPER_OUT, PAPER
    terr = os.path.join(clients.DATA, "Territories.lua")
    out = re.search(r"MapPaperOut = \{ ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+) \}", open(terr, encoding="utf-8").read()) if os.path.exists(terr) else None
    PAPER_OUT = tuple(float(out.group(i)) for i in range(1, 5)) if out else None
    PAPER = np.asarray(Image.open(os.path.join(clients.TEX, "MapPaper.tga")).convert("RGB")).astype(np.float32) / 255 if out else None
    DETAIL_DENSITY = float(dens.group(1)) if dens else None
    SEA_COLOR = tuple(float(sea.group(i)) for i in (1, 2, 3)) if sea else (0.50, 0.49, 0.41)
    return float(zoom.group(1)) if zoom else 1.0, (float(fade.group(1)), float(fade.group(2))) if fade else (3, 4.5)


class Art:
    """the game's map art, put together from its tiles (fetched into the cache as needed)"""
    def __init__(self, db2, cache):
        self.cache = cache
        self.tiles = {}
        for r in csv.DictReader(open(os.path.join(db2, "UiMapArtTile.csv"), encoding="utf-8")):
            if r["LayerIndex"] == "0":
                self.tiles.setdefault(int(r["UiMapArtID"]), {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
        self.memo = {}
        self.db2 = db2
        self.pieces = None

    def pieces_of(self, art):
        """a zone art's explored-area pieces: [(x, y, {(row, col): file})] (WorldMapOverlay)"""
        if self.pieces is None:
            self.pieces, tiles = {}, {}
            for r in csv.DictReader(open(os.path.join(self.db2, "WorldMapOverlayTile.csv"), encoding="utf-8")):
                if r["LayerIndex"] == "0":
                    tiles.setdefault(r["WorldMapOverlayID"], {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
            for r in csv.DictReader(open(os.path.join(self.db2, "WorldMapOverlay.csv"), encoding="utf-8")):
                if r["ID"] in tiles:
                    self.pieces.setdefault(int(r["UiMapArtID"]), []).append((int(r["OffsetX"]), int(r["OffsetY"]), tiles[r["ID"]]))
        return self.pieces.get(art, [])

    def fetch(self, fid):
        p = os.path.join(self.cache, "%d.blp" % fid)
        if not os.path.exists(p) or os.path.getsize(p) <= 64:
            url = "https://wago.tools/api/casc/%d?download&version=%s" % (fid, clients.BUILD)
            for attempt in range(3):
                try:
                    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "openmap-tools/1"}), timeout=60).read()
                    if len(data) > 64:
                        open(p, "wb").write(data); break
                except Exception:
                    time.sleep(2)
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            return None

    def image(self, art, w, h, tw, th, scale, pieces=False):
        """the art at `scale` of its size (RGBA float array); `pieces`: with its explored-area pieces over it"""
        key = (art, round(scale, 3), pieces)
        if key not in self.memo:
            out = Image.new("RGBA", (max(1, int(w * scale)), max(1, int(h * scale))))
            for (row, col), fid in self.tiles.get(art, {}).items():
                t = self.fetch(fid)
                if t is None: continue
                if scale != 1: t = t.resize((max(1, round(t.width * scale)), max(1, round(t.height * scale))), Image.BILINEAR)
                out.paste(t, (round(col * tw * scale), round(row * th * scale)))
            for x, y, tiles in (self.pieces_of(art) if pieces else []):
                for (row, col), fid in tiles.items():
                    t = self.fetch(fid)
                    if t is None: continue
                    if scale != 1: t = t.resize((max(1, round(t.width * scale)), max(1, round(t.height * scale))), Image.BILINEAR)
                    out.alpha_composite(t, (round((x + col * 256) * scale), round((y + row * 256) * scale)))
            self.memo[key] = np.asarray(out).astype(np.float32) / 255
        return self.memo[key]


def feather_mask(shape, edge, round_=False):
    """MapFeatherWide / MapFeatherRound, roughly: a fade over `edge` of each side"""
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    if round_:
        d = np.hypot((xs + 0.5) / w * 2 - 1, (ys + 0.5) / h * 2 - 1)
        t = np.clip((1 - d) / 0.35, 0, 1)
    else:
        d = np.minimum(np.minimum(xs + 0.5, w - xs - 0.5) / w, np.minimum(ys + 0.5, h - ys - 0.5) / h)
        t = np.clip(d / edge, 0, 1)
    return t * t * (3 - 2 * t)


def main():
    db2, cache, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    w = uimap.World(db2)
    world = uimap.read_world(os.path.join(clients.DATA, "World.lua"))
    art = Art(db2, cache)
    zk, detail_fade = client_tune()
    terr_dir = os.path.join(clients.TEX, "MapTerritory")
    W_, H_ = w.art(uimap.WORLD)[1:3]
    conts = [m for m in world["continents"] if w.rect(m)]
    zones = sorted((m for m, k in world["zones"].items() if k == 1 and w.rect(m)),
                   key=lambda m: -(w.rect(m)[1] - w.rect(m)[0]) * (w.rect(m)[3] - w.rect(m)[2]))
    cities = [m for m, k in world["zones"].items() if k == 2 and w.rect(m)]

    for spec in sys.argv[4:]:
        name, view = spec.split("=", 1)
        parts = view.split(",")
        if parts[0].startswith("@"):
            target = next(m for m in list(world["zones"]) + conts if w.uimap[m]["Name_lang"] == parts[0][1:])
            l, r, t, b = w.rect(target)
            u, v, zoom = (l + r) / 2, (t + b) / 2, float(parts[1])
        else:
            u, v, zoom = (float(x) for x in parts)
        px = min(OW / W_, OH / H_) * zoom              # output px per world unit
        zf = zoom * min(OW / W_, OH / H_) / math.sqrt(OW * OH / (W_ * H_)) / zk   # (WorldMap.lua's DetailK)
        out = np.zeros((OH, OW, 3), np.float32)
        out[:] = SEA_COLOR                              # (Stitch.lua: past the world art, its sea's colour)
        if PAPER_OUT:                                   # (... and MapPaper over it, tinted: ns.MapPaperOut)
            k, tint = PAPER_OUT[0], np.array(PAPER_OUT[1:], np.float32)
            gy = ((np.arange(OH) + 0.5 - OH / 2) / px + v * H_) / k
            gx = ((np.arange(OW) + 0.5 - OW / 2) / px + u * W_) / k
            iy = ((gy % 1) * PAPER.shape[0]).astype(np.int32)
            ix = ((gx % 1) * PAPER.shape[1]).astype(np.int32)
            out[:] = PAPER[iy[:, None], ix[None, :]] * tint

        def place(m, alpha, mask_fn, pieces=False):
            if alpha <= 0.003: return
            l, r, t, b = w.rect(m)
            x0, x1 = (l * W_ - u * W_) * px + OW / 2, (r * W_ - u * W_) * px + OW / 2
            y0, y1 = (t * H_ - v * H_) * px + OH / 2, (b * H_ - v * H_) * px + OH / 2
            vx0, vx1, vy0, vy1 = max(0, int(x0)), min(OW, int(math.ceil(x1))), max(0, int(y0)), min(OH, int(math.ceil(y1)))
            if vx1 - vx0 < 1 or vy1 - vy0 < 1: return
            a_ = w.art(m)
            # the art at about the output's resolution (a power of two below its own size)
            want = (x1 - x0) / a_[1]
            scale = 1.0
            while scale / 2 >= want and scale > 1 / 16: scale /= 2
            img = art.image(a_[0], a_[1], a_[2], a_[3], a_[4], scale, pieces)
            ih, iw = img.shape[:2]
            ys = ((np.arange(vy0, vy1) + 0.5 - y0) / (y1 - y0) * (a_[2] * scale)).astype(np.int32).clip(0, ih - 1)
            xs = ((np.arange(vx0, vx1) + 0.5 - x0) / (x1 - x0) * (a_[1] * scale)).astype(np.int32).clip(0, iw - 1)
            crop = img[ys[:, None], xs[None, :]]
            msk = mask_fn(m, (len(ys), len(xs)), ys / max(1, a_[2] * scale), xs / max(1, a_[1] * scale))
            a = crop[..., 3:4] * msk[..., None] * alpha
            dst = out[vy0:vy1, vx0:vx1]
            dst[:] = dst * (1 - a) + crop[..., :3] * a

        def wide(m, shape, fy, fx):
            d = np.minimum(np.minimum(fx, 1 - fx)[None, :], np.minimum(fy, 1 - fy)[:, None])
            t = np.clip(d / FEATHER_WIDE_EDGE, 0, 1)
            return t * t * (3 - 2 * t)

        def thin(m, shape, fy, fx):
            d = np.minimum(np.minimum(fx, 1 - fx)[None, :], np.minimum(fy, 1 - fy)[:, None])
            t = np.clip((d - 0.01) / 0.05, 0, 1)
            return t * t * (3 - 2 * t)

        def roundf(m, shape, fy, fx):
            d = np.hypot((fx * 2 - 1)[None, :], (fy * 2 - 1)[:, None])
            t = np.clip((1 - d) / 0.35, 0, 1)
            return t * t * (3 - 2 * t)

        terr_cache = {}
        def territory(m, shape, fy, fx):
            if m not in terr_cache:
                p = os.path.join(terr_dir, "%d.tga" % m)
                terr_cache[m] = np.asarray(Image.open(p).getchannel("A")).astype(np.float32) / 255 if os.path.exists(p) else None
            t = terr_cache[m]
            base = thin(m, shape, fy, fx)
            if t is None: return roundf(m, shape, fy, fx)
            ty = (fy * t.shape[0]).astype(np.int32).clip(0, t.shape[0] - 1)
            tx = (fx * t.shape[1]).astype(np.int32).clip(0, t.shape[1] - 1)
            return base * t[ty[:, None], tx[None, :]]

        land_cache = {}
        def back_land(m, shape, fy, fx):           # (Stitch.lua: a continent's art on its land, MapBackLand)
            if m not in land_cache:
                p = os.path.join(clients.TEX, "MapBackLand", "%d.tga" % m)
                land_cache[m] = np.asarray(Image.open(p).getchannel("A")).astype(np.float32) / 255 if os.path.exists(p) else None
            t, f = land_cache[m], wide(m, shape, fy, fx) if m != uimap.WORLD else 1   # (the world's: its outline alone)
            if t is None: return f
            ty = (fy * t.shape[0]).astype(np.int32).clip(0, t.shape[0] - 1)
            tx = (fx * t.shape[1]).astype(np.int32).clip(0, t.shape[1] - 1)
            return f * t[ty[:, None], tx[None, :]]

        world_out = os.path.exists(os.path.join(clients.TEX, "MapBackLand", "%d.tga" % uimap.WORLD))
        place(uimap.WORLD, 1.0, back_land if world_out else wide)
        for m in conts: place(m, smooth(zf, CONT_IN), back_land)
        def continent(m):
            for _ in range(10):
                if m in conts: return m
                m = w.parent(m)
        def zone_fade(m):                              # (Stitch.lua: by its continent's art's resolution, ZoneByContinent)
            c = continent(m)
            if not DETAIL_DENSITY or c is None: return smooth(zf, detail_fade)
            l, r = w.rect(c)[:2]
            k = w.art(c)[1] / ((r - l) * W_) / DETAIL_DENSITY
            return smooth(zf, (detail_fade[0] * k, detail_fade[1] * k))
        for m in zones: place(m, zone_fade(m), territory, True)
        for m in cities:
            l, r, _, _ = w.rect(m)
            f = 1 / (r - l)
            place(m, smooth(zf, (CITY_FADE[0] * f / zk, CITY_FADE[1] * f / zk)), roundf)   # (Stitch.lua: where it fills that much of the view)
        p = os.path.join(outdir, name + ".png")
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(p)
        print("wrote", p, "(zoom %g, layers at %.2f)" % (zoom, zf), flush=True)


if __name__ == "__main__":
    main()
