# The game's map tables (UiMap, UiMapAssignment, UiMapXMapArt, UiMapArt, UiMapArtStyleLayer, Map) read
# from a folder of their CSVs (wago.tools), and what the tools need of them: where each map lies on
# Azeroth's map (947), as C_Map.GetMapRectOnMap does, and how world positions (yards on a game map)
# land on it.
#
#   w = uimap.World(db2_dir)
#   w.rect(mapID)            -> (l, r, t, b) on 947, normalized, or None
#   w.yards(gameMapID)       -> [ (x0, x1, y0, y1, au, bu, av, bv) ]: in the world box x0..x1, y0..y1,
#                               u = au + bu * y, v = av + bv * x (947, normalized)
#   w.art(mapID)             -> (artID, width, height, tile width, tile height) of its art (phase 0)
import csv, os

WORLD = 947


def _f(r, k):
    return float(r[k])


class World:
    def __init__(self, db2, suffix=""):
        def read(name):
            p = os.path.join(db2, name + suffix + ".csv")     # (suffix: a cache's "-<build>")
            return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []
        self.uimap = {int(r["ID"]): r for r in read("UiMap")}
        self.assign = {}
        for r in read("UiMapAssignment"):
            self.assign.setdefault(int(r["UiMapID"]), []).append(r)
        # (the biggest part of each map's art first: the one GetMapRectOnMap goes by)
        for rows in self.assign.values():
            rows.sort(key=lambda r: (int(r["OrderIndex"]), -(_f(r, "UiMax_0") - _f(r, "UiMin_0")) * (_f(r, "UiMax_1") - _f(r, "UiMin_1"))))
        self.art_of = {}
        for r in read("UiMapXMapArt"):
            if r["PhaseID"] == "0":
                self.art_of.setdefault(int(r["UiMapID"]), int(r["UiMapArtID"]))
        self.style_of = {int(r["ID"]): int(r["UiMapArtStyleID"]) for r in read("UiMapArt")}
        self.layer = {}
        for r in read("UiMapArtStyleLayer"):
            if r["LayerIndex"] == "0":
                self.layer[int(r["UiMapArtStyleID"])] = (int(r["LayerWidth"]), int(r["LayerHeight"]), int(r["TileWidth"]), int(r["TileHeight"]))
        self.gamemap = {int(r["ID"]): r for r in read("Map")}
        self._rects = {}

    def parent(self, m):
        r = self.uimap.get(m)
        return int(r["ParentUiMapID"]) if r else 0

    def under_world(self, m):
        """in Azeroth's tree, as C_Map.GetMapChildrenInfo(947, ..., true)"""
        for _ in range(12):
            if m == WORLD: return True
            if m not in self.uimap: return False
            m = self.parent(m)
        return False

    def art(self, m):
        a = self.art_of.get(m)
        if a is None: return None
        lay = self.layer.get(self.style_of.get(a), (1002, 668, 256, 256))
        return (a,) + lay

    @staticmethod
    def _contains(r, x, y, margin=0.0):
        return _f(r, "Region_0") - margin <= x <= _f(r, "Region_3") + margin and _f(r, "Region_1") - margin <= y <= _f(r, "Region_4") + margin

    @staticmethod
    def _norm(r, x, y):
        """a world point (on r's game map) in r's map, normalized"""
        u = _f(r, "UiMin_0") + (_f(r, "Region_4") - y) / (_f(r, "Region_4") - _f(r, "Region_1")) * (_f(r, "UiMax_0") - _f(r, "UiMin_0"))
        v = _f(r, "UiMin_1") + (_f(r, "Region_3") - x) / (_f(r, "Region_3") - _f(r, "Region_0")) * (_f(r, "UiMax_1") - _f(r, "UiMin_1"))
        return u, v

    def _host_row(self, host, gamemap, x, y):
        """host's assignment on that game map that holds the point (else the one nearest it)"""
        rows = [r for r in self.assign.get(host, []) if int(r["MapID"]) == gamemap]
        if not rows: return None
        for r in rows:
            if self._contains(r, x, y): return r
        cx = lambda r: ((_f(r, "Region_0") + _f(r, "Region_3")) / 2 - x) ** 2 + ((_f(r, "Region_1") + _f(r, "Region_4")) / 2 - y) ** 2
        return min(rows, key=cx)

    def rect(self, m):
        """the map's rectangle on Azeroth's map (normalized): placed through the first of its
        assignments that Azeroth's map (or the nearest map above it that has that game map) places"""
        if m == WORLD: return (0.0, 1.0, 0.0, 1.0)
        if m in self._rects: return self._rects[m]
        out = None
        for a in self.assign.get(m, []):
            gm = int(a["MapID"])
            cx, cy = (_f(a, "Region_0") + _f(a, "Region_3")) / 2, (_f(a, "Region_1") + _f(a, "Region_4")) / 2
            host, hrect = WORLD, (0.0, 1.0, 0.0, 1.0)
            w = self._host_row(WORLD, gm, cx, cy)
            if not w:
                # through the nearest map above it that has this game map
                p = self.parent(m)
                for _ in range(10):
                    if not p or p == WORLD: break
                    w = self._host_row(p, gm, cx, cy)
                    if w:
                        hrect = self.rect(p)
                        break
                    p = self.parent(p)
                if not w or not hrect: continue
            # the corners of a's world box on the host, then a's UiMin..UiMax stretched to its whole art
            u0, v0 = self._norm(w, _f(a, "Region_3"), _f(a, "Region_4"))     # (max X, max Y: top left)
            u1, v1 = self._norm(w, _f(a, "Region_0"), _f(a, "Region_1"))
            l, r_ = min(u0, u1), max(u0, u1)
            t, b = min(v0, v1), max(v0, v1)
            um0, um1, uM0, uM1 = _f(a, "UiMin_0"), _f(a, "UiMin_1"), _f(a, "UiMax_0"), _f(a, "UiMax_1")
            if uM0 <= um0 or uM1 <= um1: continue
            w_, h_ = (r_ - l) / (uM0 - um0), (b - t) / (uM1 - um1)
            l, t = l - um0 * w_, t - um1 * h_
            hl, hr, ht, hb = hrect
            out = (hl + l * (hr - hl), hl + (l + w_) * (hr - hl), ht + t * (hb - ht), ht + (t + h_) * (hb - ht))
            break
        self._rects[m] = out
        return out

    def yards(self, gamemap):
        """how a game map's world positions land on Azeroth's map: one entry per region that a map
        places it by (Azeroth's own rows first, then the maps below it that have rows for it)"""
        out = []
        hosts = [WORLD] + sorted(m for m in self.assign if m != WORLD)
        for host in hosts:
            hrect = self.rect(host)
            if not hrect: continue
            for r in self.assign.get(host, []):
                if int(r["MapID"]) != gamemap: continue
                if any(o[0] <= _f(r, "Region_0") and _f(r, "Region_3") <= o[1] and o[2] <= _f(r, "Region_1") and _f(r, "Region_4") <= o[3] for o in out):
                    continue                     # (inside a region already placed)
                (ua, va), (ub, vb) = self._norm(r, 0.0, 0.0), self._norm(r, 1000.0, 1000.0)
                bu = (ub - ua) / 1000.0          # (u runs along y, v along x)
                bv = (vb - va) / 1000.0
                hl, hr, ht, hb = hrect
                out.append((_f(r, "Region_0"), _f(r, "Region_3"), _f(r, "Region_1"), _f(r, "Region_4"),
                            hl + ua * (hr - hl), bu * (hr - hl), ht + va * (hb - ht), bv * (hb - ht)))
            if host == WORLD and out:
                break                            # (Azeroth's own rows place the whole map)
        return out


def read_world(path):
    """a client's World.lua (tools/map-data/world.py) as { zones, continents, yards, minimap }, or None"""
    import re
    if not os.path.exists(path): return None
    src = open(path, encoding="utf-8").read()
    part = lambda a, b: src.split(a, 1)[1].split(b, 1)[0]
    num = r"[-\d.e+]+"
    out = {"continents": [int(v) for v in re.findall(r"\d+", part("continents = {", "}"))],
           "zones": {int(m): int(k) for m, k in re.findall(r"\[(\d+)\] = ([12]),", part("zones = {", "yards = {"))},
           "yards": {}, "minimap": {}}
    for g, body in re.findall(r"\[(\d+)\] = \{ ((?:\{ [^}]+ \},? ?)+)\},", part("yards = {", "minimap = {")):
        out["yards"][int(g)] = [tuple(float(v) for v in re.findall(num, r)) for r in re.findall(r"\{ ([^}]+) \}", body)]
    for c, body in re.findall(r"\[(\d+)\] = \{ ([\d, ]+) \},", part("minimap = {", "\n}")):
        out["minimap"][int(c)] = [int(v) for v in re.findall(r"\d+", body)]
    return out


def on_world(world, c, x, y, margin=0.2):
    """whether a world position is on a client's stitched world (always, without a World.lua): as
    Stitch.lua's S.FromYards, a little past each region's box"""
    if not world: return True
    for r in world["yards"].get(c, []):
        mx, my = (r[1] - r[0]) * margin, (r[3] - r[2]) * margin
        if r[0] - mx <= x <= r[1] + mx and r[2] - my <= y <= r[3] + my: return True
    return False


def from_yards(world, c, x, y):
    """as Stitch.lua's S.FromYards (a client with a World.lua): (u, v) on Azeroth's map, or None"""
    for r in (world or {}).get("yards", {}).get(c, []):
        mx, my = (r[1] - r[0]) * 0.2, (r[3] - r[2]) * 0.2
        if r[0] - mx <= x <= r[1] + mx and r[2] - my <= y <= r[3] + my:
            return r[4] + r[5] * y, r[6] + r[7] * x
    return None
