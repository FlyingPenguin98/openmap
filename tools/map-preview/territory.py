# The masks of a client whose maps are painted whole (retail: Data/<client>/Client.lua's sea = false),
# from the game's own art and tables. WoW Forever's are render.py's (--bake-territory and the rest),
# made for its blank-parchment zone maps.
#   MapTerritory/<zone>.tga     where a zone's base art shows over its continent's: its own land (its
#                               explored-area pieces, filled), the cities in it, and what its art paints
#                               round them out to REACH world units, never onto another zone's own land;
#                               where two zones paint the same place, the one whose land is nearer has
#                               it (shared over BLEND); never on its frame (its burnt edge, its corners)
#   MapBackLand/<continent>.tga where a continent's art shows over the world's: all of it but another
#                               continent's land and the band of shallows round it (SHALLOWS): its sea,
#                               over the world's (and its names), but never over a neighbour's coast
#   MapBackLand/947.tga         where the world's art shows: all of it but its metal frame and burnt edge
#   MapMiniLand/<continent>.tga where the close-up minimap shows (Close.lua): its zones' own land
#   Data/<client>/Territories.lua  which zones and continents have them (ns.MapTerritories, ns.MapBackLands),
#                               the tint of MapPaper past the world's art (ns.MapPaperOut), and the tiles
#                               drawn for nothing: empty pieces' or off the territory (ns.MapBlank), base off
#                               it (ns.MapOff) or under the pieces (ns.MapUnder)
#   Data/<client>/Tones.lua     each zone's overall colour, for the close-up minimap's tint (as tone.py's)
# Each zone's own land is its explored-area pieces (WorldMapOverlay), as render.py's own_land: zones
# without any (islands, cities) have no territory and are drawn through a round feather (Stitch.lua).
#
# usage: python -P tools/map-preview/territory.py <db2 dir> <texture cache> [preview dir]
#   (OPENMAP_CLIENT: the client, tools/clients.py; the textures are read from the cache, fetched from
#   wago.tools where they're missing; preview dir: each continent's masks, to look at)
import csv, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients, uimap
sys.path.insert(0, HERE)
from whole import Art

CANVAS = (1002, 668)            # a zone's art is worked on at this size, whatever its own (3:2, as all of them)
G = 2.0                         # grid px per world unit, laying a continent's zones out together
REACH = (30.0, 45.0)            # world units off its own land where a zone's painting is full / gone (its sea out
                                #  toward its frame: the continent's art is far coarser close in)
REACH_AREA = (8.0, 16.0)        # ... past its whole area, where its highlight is known (its coasts)
BLEND = 10.0                    # world units: how fast a zone's claim falls off past the nearer one's own land
OTHERS = 3.0                    # world units over which a zone's painting gives way to another zone's own land
SHALLOWS = (28.0, 40.0)         # world units off the land where a continent's art is full / gone (its shallows band)
MINI = (2.0, 4.0)               # ... and the minimap's land
TERR_PX, LAND_PX = 256, 1024    # the masks' sizes
PAPER_OUT = 512                 # world units a tile of MapPaper past the world art (its mottling the size of the art's)


def frame_mask():
    """inside a zone map's frame, on its canvas: off its burnt edge and its decorated corners"""
    w, h = CANVAS
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xs, w - 1 - xs) / w, np.minimum(ys, h - 1 - ys) / h)
    t = np.clip((d - 0.02) / 0.13, 0, 1)        # (a wide fade: where it hands over to a neighbour, no line)
    # the corners' ornaments (Blizzard's gold knots, a dragon's head, Kul Tiras' brass machinery ...): an
    # ellipse round each corner, off inside it and back over a quarter of its size past it
    cx = np.minimum(xs, w - 1 - xs) / (0.17 * w)
    cy = np.minimum(ys, h - 1 - ys) / (0.2 * h)
    c = np.clip((np.hypot(cx, cy) - 1) / 0.25, 0, 1)
    m = t * c
    return m * m * (3 - 2 * m)


def main():
    db2, cache = sys.argv[1], sys.argv[2]
    preview = sys.argv[3] if len(sys.argv) > 3 else None
    # (trying it out: OPENMAP_TERRITORY_OUT writes everything to that folder instead of the addon's, and
    # OPENMAP_TERRITORY_ONLY=12,13 does only those continents)
    only = [int(c) for c in os.environ.get("OPENMAP_TERRITORY_ONLY", "").split(",") if c]
    w = uimap.World(db2)
    world = uimap.read_world(os.path.join(clients.DATA, "World.lua"))
    if not world: sys.exit("no World.lua for %s: run tools/map-data/world.py first" % clients.NAME)
    if os.environ.get("OPENMAP_TERRITORY_OUT"):
        clients.TEX = clients.DATA = os.environ["OPENMAP_TERRITORY_OUT"]
    art = Art(db2, cache)
    read = lambda n: list(csv.DictReader(open(os.path.join(db2, n + ".csv"), encoding="utf-8")))
    pieces = {}
    for r in read("WorldMapOverlay"):
        pieces.setdefault(int(r["UiMapArtID"]), []).append(r)
    ptiles = {}
    for r in read("WorldMapOverlayTile"):
        if r["LayerIndex"] == "0":
            ptiles.setdefault(r["WorldMapOverlayID"], {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
    W, H = w.art(uimap.WORLD)[1:3]
    FRAME = frame_mask()

    def own_land(m):
        """the zone's own land on its canvas: its pieces' alpha, closed and filled (None: it has none)"""
        a, aw, ah, tw, th = w.art(m)
        if not pieces.get(a): return None
        alpha = np.zeros((ah, aw), np.uint8)
        for o in pieces[a]:
            x, y = int(o["OffsetX"]), int(o["OffsetY"])
            for (row, col), fid in ptiles.get(o["ID"], {}).items():
                t = art.fetch(fid)
                if t is None: continue
                ta = np.asarray(t.getchannel("A"))
                X0, Y0 = x + col * 256, y + row * 256
                X1, Y1 = min(aw, X0 + ta.shape[1]), min(ah, Y0 + ta.shape[0])
                if X1 > X0 and Y1 > Y0:
                    alpha[Y0:Y1, X0:X1] = np.maximum(alpha[Y0:Y1, X0:X1], ta[:Y1 - Y0, :X1 - X0])
        o = np.asarray(Image.fromarray(alpha).resize(CANVAS, Image.BILINEAR)).astype(np.float32) / 255
        # (not cut at the frame: its territory fades out there by the frame's own wide fade, not at a line)
        land = ndimage.binary_fill_holes(ndimage.binary_closing(o > 0.5, np.ones((3, 3)), iterations=6))
        return land if land.any() else None

    def continent_of(m):
        for _ in range(10):
            if m in world["continents"]: return m
            m = w.parent(m)
        return None

    zones = [m for m, k in world["zones"].items() if k == 1]
    cities = [m for m, k in world["zones"].items() if k == 2]

    # each zone's whole area as its continent's map draws it, where the zones' highlights have been recorded in
    # game (/openmap highlights, highlights.py): its highlight, placed as the game places it (the part of the
    # texture TexPercent of it, over its rectangle on the continent). With it a zone's painting reaches only
    # REACH_AREA past its area; without, REACH past its own land
    hl_path = os.path.join(HERE, "highlights", clients.NAME + ".txt")
    hl_of = {}
    if os.path.exists(hl_path):
        fid_zone = {}
        art_hl = {int(r["ID"]): int(r["HighlightFileDataID"]) for r in read("UiMapArt")}
        for z in zones:
            f = art_hl.get(w.art(z)[0])
            if f: fid_zone[f] = z
        for line in open(hl_path, encoding="utf-8"):
            if line.startswith("#") or not line.strip(): continue
            c, z, fid, atlas, px, py, tx, ty, sx, sy = line.split()
            z = fid_zone.get(int(fid), int(z))
            if z in zones and int(fid) and float(tx) > 0 and float(ty) > 0:
                hl_of.setdefault(z, []).append((int(c), int(fid), float(px), float(py), float(tx), float(ty), float(sx), float(sy)))
        print("highlights for %d zones" % len(hl_of), flush=True)

    def area_of(m):
        """the zone's highlight on its canvas (0..1), or None"""
        if m not in hl_of: return None
        l, r, t, b = w.rect(m)
        xs = l + (np.arange(CANVAS[0]) + 0.5) / CANVAS[0] * (r - l)
        ys = t + (np.arange(CANVAS[1]) + 0.5) / CANVAS[1] * (b - t)
        out = np.zeros((CANVAS[1], CANVAS[0]), np.float32)
        for c, fid, px, py, tx, ty, sx, sy in hl_of[m]:
            img = art.fetch(fid)
            cr_ = w.rect(c)
            if img is None or not cr_: continue
            a = np.asarray(img.convert("RGB")).astype(np.float32).max(2)
            a /= max(1.0, a.max())
            s = ((xs - cr_[0]) / (cr_[1] - cr_[0]) - sx) / tx * px        # (texture coordinates, 0..px, 0..py)
            u = ((ys - cr_[2]) / (cr_[3] - cr_[2]) - sy) / ty * py
            S, U = np.meshgrid(s, u)
            inside = (S >= 0) & (S <= px) & (U >= 0) & (U <= py)
            v = ndimage.map_coordinates(a, [U * a.shape[0] - 0.5, S * a.shape[1] - 0.5], order=1, mode="nearest") * inside
            out = np.maximum(out, v)
        return out

    memo = {}
    def land_of(m):
        """a zone's own land with the cities in it (theirs, or whose middle is on its land: its art paints
        them till theirs comes in), on its canvas; None without pieces"""
        if m in memo: return memo[m]
        land = own_land(m)
        if land is not None:
            l, r, t, b = w.rect(m)
            for city in cities:
                ql, qr, qt, qb = w.rect(city)
                cx, cy = int(((ql + qr) / 2 - l) / (r - l) * CANVAS[0]), int(((qt + qb) / 2 - t) / (b - t) * CANVAS[1])
                if w.parent(city) != m and not (0 <= cx < CANVAS[0] and 0 <= cy < CANVAS[1] and land[cy, cx]): continue
                x0, x1 = int((ql - l) / (r - l) * CANVAS[0]), int((qr - l) / (r - l) * CANVAS[0])
                y0, y1 = int((qt - t) / (b - t) * CANVAS[1]), int((qb - t) / (b - t) * CANVAS[1])
                yy, xx = np.ogrid[0:CANVAS[1], 0:CANVAS[0]]
                land = land | (((xx - (x0 + x1) / 2) / max(1, (x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / max(1, (y1 - y0) / 2)) ** 2 <= 0.6)
        memo[m] = land
        return land
    terr_dir, land_dir, mini_dir = (os.path.join(clients.TEX, d) for d in ("MapTerritory", "MapBackLand", "MapMiniLand"))
    for d in (terr_dir, land_dir, mini_dir): os.makedirs(d, exist_ok=True)
    done_terr, done_land = [], []
    shallows = {}                   # continent -> its land and shallows over its rectangle (LAND_PX square)
    for c in [c for c in world["continents"] if not only or c in only]:
        cl, cr, ct, cb = w.rect(c)
        gw, gh = int((cr - cl) * W * G), int((cb - ct) * H * G)
        mine = [m for m in zones if continent_of(m) == c]
        def box(m):
            l, r, t, b = w.rect(m)
            return (int(round((l - cl) * W * G)), int(round((t - ct) * H * G)), int(round((r - cl) * W * G)), int(round((b - ct) * H * G)))
        def to_grid(img, m):
            x0, y0, x1, y1 = box(m)
            dst = np.zeros((gh, gw), np.float32)
            if x1 - x0 < 2 or y1 - y0 < 2: return dst
            a = np.asarray(Image.fromarray(np.clip(img, 0, 1).astype(np.float32), "F").resize((x1 - x0, y1 - y0), Image.BILINEAR))
            X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
            if X1 > X0 and Y1 > Y0: dst[Y0:Y1, X0:X1] = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
            return dst
        def to_art(img, m):
            x0, y0, x1, y1 = box(m)
            pad = np.zeros((y1 - y0, x1 - x0), np.float32)
            X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
            if X1 > X0 and Y1 > Y0: pad[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = img[Y0:Y1, X0:X1]
            return np.asarray(Image.fromarray(pad, "F").resize(CANVAS, Image.BILINEAR))
        own, frame = {}, {}
        for m in mine:
            land = land_of(m)
            if land is None: continue
            own[m] = to_grid(land.astype(np.float32), m)
            frame[m] = to_grid(FRAME, m)
        if own:
            dist = {m: ndimage.distance_transform_edt(own[m] < 0.5) / G for m in own}
            near = {m: ndimage.gaussian_filter((dist[m] <= 0).astype(np.float32), OTHERS * G / 2) for m in own}
            avail, logw = {}, {}
            cover = np.zeros((gh, gw), np.float32)
            for m in own:
                others = np.zeros((gh, gw), np.float32)
                for n in own:
                    if n != m: others = np.maximum(others, near[n] * frame[n])
                area = area_of(m)
                if area is None:
                    u = np.clip(1 - (dist[m] - REACH[0]) / (REACH[1] - REACH[0]), 0, 1)
                    reach = u * u * (3 - 2 * u)
                else:                                # (its whole area, as its continent draws it, and a little past)
                    u = np.clip(1 - (dist[m] - REACH_AREA[0]) / (REACH_AREA[1] - REACH_AREA[0]), 0, 1)
                    reach = np.maximum(u * u * (3 - 2 * u), np.clip(to_grid(area, m) * 2, 0, 1))
                avail[m] = frame[m] * np.clip(1 - others, 0, 1) * reach
                logw[m] = np.log(np.maximum(avail[m], 1e-9)) - dist[m] / BLEND
                cover = np.maximum(cover, avail[m])
            # shared out by nearness (each one's weight: what it can show there, falling off with the distance
            # from its own land; its share, its weight's part of them all, in logs), as much as any of them can
            # show there: where one fades out at its frame the next takes over, with no gap and no line
            top = np.maximum.reduce(list(logw.values()))
            total = sum(np.exp(l - top) for l in logw.values())
            for m in own:
                soft = np.clip(1 - dist[m], 0, 1)                    # (its own land, a little past it)
                terr = np.maximum(soft * frame[m], np.exp(logw[m] - top) / total * cover)
                a = Image.fromarray((np.clip(to_art(terr, m), 0, 1) * 255).astype(np.uint8)).resize((TERR_PX, TERR_PX), Image.LANCZOS)
                Image.merge("RGBA", (Image.new("L", (TERR_PX, TERR_PX), 255),) * 3 + (a,)).save(os.path.join(terr_dir, "%d.tga" % m))
                done_terr.append(m)
        # the continent's land: its zones' own land (and the islands drawn round, no zone's: a round
        # feather of theirs), its shallows past it. The minimap's: every zone's whose middle is on the
        # continent's map, another continent's too (Quel'Thalas' zones, on the Eastern Kingdoms' game map,
        # whose minimap is drawn through the Eastern Kingdoms' land: Close.lua's CONT_MAP)
        def land_of_zones(ms):
            land = np.zeros((gh, gw), bool)
            for m in ms:
                ln = land_of(m) if m in zones else None
                if ln is not None:
                    land |= to_grid(ln.astype(np.float32), m) > 0.5
                    continue
                x0, y0, x1, y1 = box(m)
                yy, xx = np.ogrid[0:gh, 0:gw]
                land |= ((xx - (x0 + x1) / 2) / max(1, (x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / max(1, (y1 - y0) / 2)) ** 2 <= 0.35
            return land
        def middle_on(m):
            l, r, t, b = w.rect(m)
            return cl <= (l + r) / 2 <= cr and ct <= (t + b) / 2 <= cb
        land = land_of_zones(mine + [x for x in cities if continent_of(x) == c])
        mini = land_of_zones([m for m in zones + cities if middle_on(m)])
        if land.any():
            for out_dir, (a0, a1), ln in ((land_dir, SHALLOWS, land), (mini_dir, MINI, mini)):
                d = ndimage.distance_transform_edt(~ln) / G
                t = np.clip(1 - (d - a0) / (a1 - a0), 0, 1)
                a = Image.fromarray((t * t * (3 - 2 * t) * 255).astype(np.uint8)).resize((LAND_PX, LAND_PX), Image.LANCZOS)
                if out_dir == land_dir:              # (each continent's land and shallows: below, once all are known)
                    shallows[c] = np.asarray(a).astype(np.float32) / 255
                    continue
                Image.merge("RGBA", (Image.new("L", (LAND_PX, LAND_PX), 255),) * 3 + (a,)).save(os.path.join(out_dir, "%d.tga" % c))
            done_land.append(c)
            if preview:
                os.makedirs(preview, exist_ok=True)
                sheet = np.zeros((gh, gw, 3), np.float32)
                d = ndimage.distance_transform_edt(~land) / G
                t = np.clip(1 - (d - SHALLOWS[0]) / (SHALLOWS[1] - SHALLOWS[0]), 0, 1)
                sheet[..., 2] = t * 0.6
                for i, m in enumerate(own):
                    sheet[..., i % 2] = np.maximum(sheet[..., i % 2], own[m] * (0.5 + 0.5 * (i % 3) / 2))
                Image.fromarray((sheet * 255).astype(np.uint8)).save(os.path.join(preview, "land-%d.png" % c))
        print("  %s: %d zones, %d territories" % (w.uimap[c]["Name_lang"], len(mine), len(own)), flush=True)

    # each continent's art: its land and shallows, and the sea round them shared with the other continents
    # whose maps reach it by nearness (as the zones share theirs): the sea goes to the continent whose land
    # is nearest, each one's claim fading at its map's edge (MapFeatherWide's), so no continent's page
    # (its insets, frame, lettering) paints over a neighbour's coast, and no map's edge shows as a line
    N = LAND_PX
    GW = 0.5                                     # world grid px per world unit
    ww, wh = int(W * GW), int(H * GW)
    def on_world(c, img):
        cl, cr, ct, cb = w.rect(c)
        x0, x1 = int(round(cl * ww)), int(round(cr * ww))
        y0, y1 = int(round(ct * wh)), int(round(cb * wh))
        dst = np.zeros((wh, ww), np.float32)
        a = np.asarray(Image.fromarray(img.astype(np.float32), "F").resize((max(1, x1 - x0), max(1, y1 - y0)), Image.BILINEAR))
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(ww, x1), min(wh, y1)
        if X1 > X0 and Y1 > Y0: dst[Y0:Y1, X0:X1] = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        return dst
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    edge = np.minimum(np.minimum(xs + 0.5, N - xs - 0.5), np.minimum(ys + 0.5, N - ys - 0.5)) / N
    fw = np.clip(edge / 0.18, 0, 1)
    fw = fw * fw * (3 - 2 * fw)
    # (weights: how far in its map a spot is, times a falloff with the distance from its land; each
    # continent's share is its weight's part of them all, in logs, so far from every land none underflows)
    logw, cover = {}, np.zeros((wh, ww), np.float32)
    for c, a in shallows.items():
        inside = on_world(c, fw)
        near = ndimage.distance_transform_edt(on_world(c, a) < 0.5) / GW
        logw[c] = np.log(np.maximum(inside, 1e-9)) - near / 15.0
        cover = np.maximum(cover, inside)
    top = np.maximum.reduce(list(logw.values()))
    total = sum(np.exp(l - top) for l in logw.values())
    for c in shallows:
        cl, cr, ct, cb = w.rect(c)
        share = np.exp(logw[c] - top) / total * cover
        u = (cl + (np.arange(N) + 0.5) / N * (cr - cl)) * ww - 0.5
        v = (ct + (np.arange(N) + 0.5) / N * (cb - ct)) * wh - 0.5
        Y, X = np.meshgrid(v, u, indexing="ij")
        mask = ndimage.map_coordinates(share, [Y, X], order=1, mode="constant", cval=0)
        # (its own land and shallows always, where two overlap each keeping its own; but not on its page's frame,
        # which its land can run right up to: Quel'Thalas')
        inner = np.clip((edge - 0.04) / 0.06, 0, 1)
        mask = np.maximum(mask, shallows[c] * inner * inner * (3 - 2 * inner))
        a = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
        Image.merge("RGBA", (Image.new("L", (N, N), 255),) * 3 + (a,)).save(os.path.join(land_dir, "%d.tga" % c))

    # the world's art: all of it but its frame (the metal corners and bars, their jewels) and its burnt edge,
    # traced from the art (what's dark or cool, joined to the art's edge, and what that rings round), so its
    # parchment shows right up to where it's torn; and the colour of its margin there, which MapPaper is
    # tinted to past it (ns.MapPaperOut)
    a, aw, ah, tw, th = w.art(uimap.WORLD)
    img = np.asarray(Image.fromarray((art.image(a, aw, ah, tw, th, 0.5) * 255).astype(np.uint8)).resize((1920, 1280), Image.BILINEAR)).astype(np.float32)[..., :3] / 255
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    cut = (lum < 0.28) | (b > np.maximum(r, g) + 0.03) | ((b > r + 0.01) & (g < r + 0.02) & (lum < 0.7)) | ((r - g > 0.08) & (b > 0.9 * g))
    lab, _ = ndimage.label(cut)
    edge_lab = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    off = ndimage.binary_closing(np.isin(lab, list(edge_lab)), iterations=4)
    off[:3] = off[-3:] = True
    off[:, :3] = off[:, -3:] = True
    keep, _ = ndimage.label(ndimage.binary_erosion(~off, iterations=24))   # (the page itself: what's left once
    big = np.argmax(np.bincount(keep.ravel())[1:]) + 1                        #  thin bridges to the frame are cut)
    off = ndimage.binary_dilation(~(ndimage.binary_dilation(keep == big, iterations=24) & ~off), iterations=5)
    page = np.clip((1 - ndimage.gaussian_filter(off.astype(np.float32), 5) - 0.5) * 2, 0, 1)
    mask = Image.fromarray((page * 255).astype(np.uint8)).resize((LAND_PX, LAND_PX), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (LAND_PX, LAND_PX), 255),) * 3 + (mask,)).save(os.path.join(land_dir, "%d.tga" % uimap.WORLD))
    done_land.append(uimap.WORLD)
    inside = ndimage.distance_transform_edt(page > 0.5)
    margin = np.median(img[(inside > 8) & (inside < 60)], axis=0)
    paper = np.asarray(Image.open(os.path.join(clients.TEX, "MapPaper.tga")).convert("RGB")).astype(np.float32) / 255
    tint = np.clip(margin / paper.reshape(-1, 3).mean(0), 0, 1)

    # each zone's overall painted colour (as tone.py's for Forever: the median of its art on its own
    # land), which Close.lua tints the close-up minimap toward
    tones = []
    for m in sorted(zones):
        if only and continent_of(m) not in only: continue
        land = land_of(m)
        if land is None or land.sum() < 1000: continue
        a, aw, ah, tw, th = w.art(m)
        scale = 1.0
        while aw * scale / 2 >= CANVAS[0]: scale /= 2
        img = art.image(a, aw, ah, tw, th, scale)
        rgb = np.asarray(Image.fromarray((img * 255).astype(np.uint8)).resize(CANVAS, Image.BILINEAR)).astype(np.float32)[..., :3] / 255
        tones.append((m, np.median(rgb[land], axis=0)))
    with open(os.path.join(clients.DATA, "Tones.lua"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- Each zone's overall painted colour: [uiMapID] = { r, g, b }, the median of its base art on its own land.\n")
        fh.write("-- Generated by tools/map-preview/territory.py (build %s); regenerate rather than edit.\n\n" % clients.BUILD)
        fh.write("local _, ns = ...\n\nns.MapTones = {\n")
        for m, c in tones:
            fh.write("\t[%d] = { %.3f, %.3f, %.3f },  -- %s\n" % (m, c[0], c[1], c[2], w.uimap[m]["Name_lang"]))
        fh.write("}\n")

    # what's drawn for nothing (Stitch.lua leaves it out): the explored-area pieces' tiles with nothing in
    # them (MapBlank, by file), and the zones' base tiles that lie wholly under their pieces' opaque
    # painting, inside their territory (MapUnder: hidden while the unexplored pieces show; Hide
    # unexplored areas shows them again)
    # (and, drawn through its territory, a zone's tiles wholly outside it: MapBlank for a piece's, MapOff for
    # its base art's, always left out)
    blank, under, off = set(), {}, {}
    terr_px = lambda m: np.asarray(Image.open(os.path.join(terr_dir, "%d.tga" % m)).getchannel("A"))
    for m in sorted(done_terr):
        a, aw, ah, tw, th = w.art(m)
        own = np.asarray(Image.fromarray(terr_px(m)).resize((aw, ah), Image.BILINEAR))
        cover = np.zeros((ah, aw), np.uint8)
        for o in pieces.get(a, []):
            x, y = int(o["OffsetX"]), int(o["OffsetY"])
            for (row, col), fid in ptiles.get(o["ID"], {}).items():
                t = art.fetch(fid)
                if t is None: continue
                ta = np.asarray(t.getchannel("A"))
                X0, Y0 = x + col * 256, y + row * 256
                X1, Y1 = min(aw, X0 + ta.shape[1]), min(ah, Y0 + ta.shape[0])
                if ta.max() < 8 or X1 <= X0 or Y1 <= Y0 or own[Y0:Y1, X0:X1].max() < 3:
                    blank.add(fid); continue
                cover[Y0:Y1, X0:X1] = np.maximum(cover[Y0:Y1, X0:X1], ta[:Y1 - Y0, :X1 - X0])
        cols = -(-aw // tw)
        for (row, col) in art.tiles.get(a, {}):
            c, t = cover[row * th:(row + 1) * th, col * tw:(col + 1) * tw], own[row * th:(row + 1) * th, col * tw:(col + 1) * tw]
            if not t.size or t.max() < 3:
                off.setdefault(m, []).append(row * cols + col + 1)
            elif c.min() >= 250 and t.min() >= 250:
                under.setdefault(m, []).append(row * cols + col + 1)
    print("%d piece tiles empty or off their territory, %d base tiles off it, %d under the pieces" % (
        len(blank), sum(len(v) for v in off.values()), sum(len(v) for v in under.values())), flush=True)

    path = os.path.join(clients.DATA, "Territories.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- Which zones have a territory (Media/Textures/<client>/MapTerritory) and which continents a land mask\n")
        fh.write("-- (MapBackLand, MapMiniLand): Stitch.lua draws each through it.\n")
        fh.write("-- Generated by tools/map-preview/territory.py from the game's art (build %s); regenerate rather than edit.\n\n" % clients.BUILD)
        fh.write("local _, ns = ...\n\n")
        fh.write("ns.MapTerritories = {\n%s}\n\n" % "".join("\t[%d] = true,   -- %s\n" % (m, w.uimap[m]["Name_lang"]) for m in sorted(done_terr)))
        fh.write("ns.MapBackLands = {\n%s}\n\n" % "".join("\t[%d] = true,   -- %s\n" % (m, w.uimap[m]["Name_lang"]) for m in sorted(done_land)))
        fh.write("-- past the world art's edges: MapPaper, a tile this many world units, tinted to the world art's margin\n")
        fh.write("ns.MapPaperOut = { %d, %.3f, %.3f, %.3f }\n\n" % (PAPER_OUT, tint[0], tint[1], tint[2]))
        fh.write("-- explored-area pieces' tiles with nothing in them, or wholly off their zone's territory (file IDs), left out\n")
        fh.write("ns.MapBlank = {%s}\n\n" % ", ".join("[%d] = true" % f for f in sorted(blank)))
        fh.write("-- each zone's base tiles (row-major, from 1) wholly off its territory, left out\n")
        fh.write("ns.MapOff = {\n%s}\n\n" % "".join("\t[%d] = { %s },   -- %s\n" % (m, ", ".join("[%d] = true" % i for i in sorted(v)), w.uimap[m]["Name_lang"]) for m, v in sorted(off.items())))
        fh.write("-- each zone's base tiles (row-major, from 1) wholly under its pieces' opaque painting, left out while\n")
        fh.write("-- they show\n")
        fh.write("ns.MapUnder = {\n%s}\n" % "".join("\t[%d] = { %s },   -- %s\n" % (m, ", ".join("[%d] = true" % i for i in sorted(v)), w.uimap[m]["Name_lang"]) for m, v in sorted(under.items())))
    print("wrote %s: %d territories, %d continents' land" % (os.path.relpath(path, clients.REPO), len(done_terr), len(done_land)))


if __name__ == "__main__":
    main()
