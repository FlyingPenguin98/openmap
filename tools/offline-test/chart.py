"""The sea chart's layout in Lua 5.1 (Map/Chart.lua's S.Chart.Ops, from Data/Chart.lua) against its Python
original (tools/map-chart/layout.py, which render.py draws with): the same pieces in the same places for every
window shape, and every ornament on the chart, clear of the game's map in its middle:
python -P tools/offline-test/chart.py."""
from pathlib import Path
import math
import sys
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "map-chart"))
import layout as LO   # noqa: E402

ASPECTS = [0.3, 0.35, 0.46, 0.6, 0.8, 1.0, 1.2, 1.224, 1.25, 4 / 3, 1.5, 1.6, 16 / 9, 2.0, 2.39, 3.0, 32 / 9, 4.0, 5.0]


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = LO.load_chart(ROOT / "OpenMap" / "Data" / "Forever" / "Chart.lua")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("ns = { MapStitch = {}, Media = { path = 'OpenMap\\\\Media\\\\', tex = 'OpenMap\\\\Media\\\\Textures\\\\Forever\\\\' } }")
        load = lua.eval("function(src, name) local f = assert(loadstring(src, name)) f('OpenMap', ns) end")
        load((ROOT / "OpenMap" / "Data" / "Forever" / "Chart.lua").read_text(encoding="utf-8"), "Chart data")
        load((ROOT / "OpenMap" / "Map" / "Chart.lua").read_text(encoding="utf-8"), "Chart.lua")
        cls.lua = lua

    def lua_ops(self, aspect):
        o = self.lua.eval("ns.MapStitch.Chart.Ops")(aspect)

        def py(v):
            if hasattr(v, "keys"):
                keys = list(v.keys())
                if keys and all(isinstance(k, int) for k in keys):
                    return [py(v[k]) for k in sorted(keys)]
                return {k: py(v[k]) for k in keys}
            return v
        return py(o)

    def close(self, a, b, what):
        if isinstance(a, (list, tuple)):
            self.assertEqual(len(a), len(b), what)
            for i, (x, y) in enumerate(zip(a, b)):
                self.close(x, y, "%s[%d]" % (what, i))
        elif isinstance(a, str):
            self.assertEqual(a, b, what)
        else:
            self.assertAlmostEqual(float(a), float(b), places=4, msg=what)

    def test_lua_lays_out_as_python(self):
        for asp in ASPECTS:
            p, q = LO.ops(self.chart, asp), self.lua_ops(asp)
            self.close(p["canvas"], q["canvas"], "canvas at %.3f" % asp)
            self.close(p["shift"], q["shift"], "shift at %.3f" % asp)
            self.close([list(x[0]) + list(x[1]) + [x[2], x[3], x[4]] for x in p["paper"]],
                       [x[0] + x[1] + [x[2], x[3], x[4]] for x in q["paper"]], "paper at %.3f" % asp)
            for key in ("ornaments", "rays", "frame"):
                self.close([[x[0]] + list(x[1]) + [x[2], x[3]] for x in p[key]],
                           [[x[0]] + x[1] + [x[2], x[3]] for x in q[key]], "%s at %.3f" % (key, asp))
            self.close([p["web"][0][0]] + list(p["web"][0][1]) + list(p["web"][0][2:]),
                       [q["web"][0]] + q["web"][1] + [q["web"][2], q["web"][3]], "web at %.3f" % asp)

    def test_paper_covers_the_chart(self):
        # the cuts along each axis meet or overlap, from the chart's one edge to the other
        for asp in ASPECTS:
            o = LO.ops(self.chart, asp)
            cw, ch = o["canvas"]
            for n in (cw, ch):
                pieces = LO.axis(n)
                self.assertAlmostEqual(pieces[0][2], 0, places=4)
                self.assertAlmostEqual(pieces[-1][3], n, places=4)
                for a, b in zip(pieces, pieces[1:]):
                    self.assertLessEqual(b[2], a[3] + 1e-6, "a gap between cuts at %.3f" % asp)
                    self.assertAlmostEqual(a[3] - b[2], b[4], places=4, msg="a cut's fade isn't its overlap at %.3f" % asp)
                for s0, s1, d0, d1, f in pieces:
                    self.assertGreaterEqual(s0, -1e-6)
                    self.assertLessEqual(s1, LO.SIZE + 1e-6)
                    self.assertAlmostEqual(s1 - s0, d1 - d0, places=4, msg="a cut stretched at %.3f" % asp)
            # (Chart.lua draws them in two draw layers' sublevels: 31 in order)
            self.assertLessEqual(max(x[4] for x in o["paper"]), 30, "more cuts than draw sublevels at %.3f" % asp)

    def test_ornaments_on_the_chart_clear_of_the_map(self):
        world = self.chart["world"]
        for row in self.chart["layouts"]:
            asp = row[0]
            o = LO.ops(self.chart, asp)
            cw, ch = o["canvas"]
            dx, dy = o["shift"]
            mid = (world[0] + dx, world[1] + dy, world[2] + dx, world[3] + dy)
            for name, box, u1, v1 in o["ornaments"]:
                self.assertGreaterEqual(box[0], -1, "%s off the chart at %.3f" % (name, asp))
                self.assertGreaterEqual(box[1], -1, "%s off the chart at %.3f" % (name, asp))
                self.assertLessEqual(box[2], cw + 1, "%s off the chart at %.3f" % (name, asp))
                self.assertLessEqual(box[3], ch + 1, "%s off the chart at %.3f" % (name, asp))
                inside = box[0] > mid[0] and box[2] < mid[2] and box[1] > mid[1] and box[3] < mid[3]
                self.assertFalse(inside, "%s on the game's map at %.3f" % (name, asp))

    def test_lays_out_on_frames(self):
        # Chart.lua's own drawing, on stand-in frames and textures (any method does nothing, a few answer):
        # it runs without an error for every shape, puts every region it shows somewhere, and fits the view
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("""
            ns = { MapStitch = {}, Media = { path = 'OpenMap\\\\Media\\\\', tex = 'OpenMap\\\\Media\\\\Textures\\\\Forever\\\\' } }
            local function Region()
                local r = { shown = true }
                return setmetatable(r, { __index = function(t, k)
                    if k == "Show" then return function(self) self.shown = true end end
                    if k == "Hide" then return function(self) self.shown = false end end
                    if k == "SetShown" then return function(self, on) self.shown = on and true or false end end
                    if k == "CreateTexture" or k == "CreateMaskTexture" then
                        return function(self) local x = Region() x.mask = k == "CreateMaskTexture" made[#made + 1] = x return x end
                    end
                    return function() end
                end })
            end
            made, placed = {}, {}
            function CreateFrame() return Region() end
            local S = ns.MapStitch
            S.chartHost = { Region(), 5 }
            function S.Size() return 1002, 668 end
            rects = {}
            function S.Rect(id) local r = rects[id] if r then return r[1], r[2], r[3], r[4] end end
            function S.PlaceWorld(region, u0, v0, u1, v1) placed[region] = { u0, v0, u1, v1 } end
            function S.UnplaceWorld(region) placed[region] = nil end
            function S.IsShownNow() return true end
            function S.SetChart(on) S.chartWas = on end
        """)
        load = lua.eval("function(src, name) local f = assert(loadstring(src, name)) f('OpenMap', ns) end")
        load((ROOT / "OpenMap" / "Data" / "Forever" / "Chart.lua").read_text(encoding="utf-8"), "Chart data")
        load((ROOT / "OpenMap" / "Map" / "Chart.lua").read_text(encoding="utf-8"), "Chart.lua")
        # the two continent maps' rectangles on the world, as the game has them (his pictures of them at the
        # scale and place build.py measured: 1.5164 sheet px a world unit, the world map's corner at 1198, 1416)
        A, BX, BY = 1.5164, 1198.35, 1415.6
        for mid, box in self.chart["continents"].items():
            lua.eval("function(id, l, r, t, b) rects[id] = { l, r, t, b } end")(
                int(mid), (box[0] - BX) / A / 1002, (box[2] - BX) / A / 1002, (box[1] - BY) / A / 668, (box[3] - BY) / A / 668)
        lua.execute("ns.MapStitch.Chart.SetShown(true)")
        self.assertTrue(lua.eval("ns.MapStitch.Chart.on and ns.MapStitch.chartWas"))
        for w, h in ((1600, 900), (3440, 1440), (800, 1700), (1000, 1000), (1600, 900)):
            lua.eval("ns.MapStitch.Chart.Layout")(w, h)
            unplaced = lua.eval("""function()
                local n = 0
                for _, r in ipairs(made) do if r.shown and not r.mask and not placed[r] then n = n + 1 end end
                return n end""")()
            self.assertEqual(unplaced, 0, "regions shown but not placed at %dx%d" % (w, h))
            fit = min(w / 1002, h / 668)
            least = lua.eval("ns.MapStitch.Chart.LeastZoom")(w, h, fit)
            self.assertLess(least, 1, "the chart's least zoom isn't further out than the world at %dx%d" % (w, h))
            l, t, r, b = lua.eval("ns.MapStitch.Chart.Rect")(w, h)
            self.assertTrue(l < 0 and t < 0 and r > 1 and b > 1, "the chart doesn't reach round the world at %dx%d" % (w, h))
            # the chart, at its least zoom, is the view's size
            self.assertAlmostEqual((r - l) * 1002 * fit * least, w, delta=w * 0.002)
            self.assertAlmostEqual((b - t) * 668 * fit * least, h, delta=h * 0.002)
        lua.execute("ns.MapStitch.Chart.SetShown(false)")
        self.assertFalse(lua.eval("ns.MapStitch.Chart.on"))
        self.assertEqual(lua.eval("ns.MapStitch.Chart.LeastZoom")(1600, 900, 1.3), 1)

    def test_every_shape_has_a_layout_near_it(self):
        aspects = [row[0] for row in self.chart["layouts"]]
        for a, b in zip(aspects, aspects[1:]):
            self.assertLess(math.log(b / a), 0.05, "layouts too far apart: %.3f, %.3f" % (a, b))


if __name__ == "__main__":
    unittest.main()
