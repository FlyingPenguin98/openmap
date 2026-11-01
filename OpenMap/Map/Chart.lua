--------------------------------------------------------------------------------
-- The sea chart (Options' Responsive ocean & border; off unless chosen): Santiago Reyes's sea, ornaments and frame
-- round the game's world map, used with his permission (ns.MapChart, tools/map-chart). The game's map
-- stays in the middle, never covered; the chart is laid out for the window's shape: its paper cut and
-- cross-faded to fill it, the ornaments each in its place for that shape (worked out once per shape:
-- tools/map-chart/layout.py, which this mirrors; tools/offline-test/chart.py checks they agree), the
-- frame's corners in the chart's corners. Zoomed right out the chart fills the view, and you can pan to
-- its edges and no further (WorldMap.lua: S.Chart.LeastZoom, S.Chart.Rect).
-- Stitch.lua draws it under its own art: the world map fades into it through MapChart\Middle instead of
-- its own wide edge fade, and the sea OpenMap draws past the world map (MapSeaFieldOut) is put away.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch

local C = { on = false }
S.Chart = C

local TEX = ns.Media.tex .. "MapChart\\"
local FEATHER = ns.Media.tex .. "MapFeather"

--------------------------------------------------------------------------------
-- Layout (sheet px: Santiago's sheet, D.size square; the chart's top-left at 0, 0)
--------------------------------------------------------------------------------

-- the chart's size for a window `aspect` (width / height)
function C.Canvas(aspect)
	local D = ns.MapChart
	local w0, w1 = D.world, D.pad
	local ww, wh = w0[3] - w0[1], w0[4] - w0[2]
	local w, h = ww + 2 * w1, wh + 2 * w1
	if w / h < aspect then w = h * aspect else h = w / aspect end
	return w, h
end

-- one axis of the chart, n px long: cuts { s0, s1, d0, d1, fade } (his sheet, the chart). His torn-edge strip at
-- each end, cuts from inside his paper between; each after the first fades in over `fade` at its start, over
-- the one before. A short axis: the two edge strips alone (layout.py's axis)
local function Axis(n)
	local D = ns.MapChart
	local size, edge, X = D.size, D.edge, math.min(D.seam, n / 3)
	local pe, pi = D.cut[1], D.cut[2]
	if n <= 2 * pe - X then
		local P = (n + X) / 2
		return { { 0, P, 0, P, 0 }, { size - P, size, n - P, n, X } }
	end
	local k = 1
	while 2 * pe + k * pi - (k + 1) * X < n do k = k + 1 end
	local P = (n - 2 * pe + (k + 1) * X) / k
	local out = { { 0, pe, 0, pe, 0 } }
	local at = pe - X
	for i = 1, k do
		local s0 = edge + (size - 2 * edge - P) * ((i * 0.618) % 1)
		out[#out + 1] = { s0, s0 + P, at, at + P, X }
		at = at + P - X
	end
	out[#out + 1] = { size - pe, size, at, at + pe, X }
	return out
end

-- the worked-out layout nearest `aspect` (by ratio)
local function Pick(aspect)
	local best, bestD
	for _, row in ipairs(ns.MapChart.layouts) do
		local d = math.abs(math.log(row[1] / aspect))
		if not bestD or d < bestD then best, bestD = row, d end
	end
	return best
end

-- an ornament's left and top: per axis, measured from the chart's near edge (0), the middle's (1) or
-- the chart's far edge (2)
local function Unanchor(a, cw, ch)
	local w = ns.MapChart.world
	local wx0, wy0 = (cw - (w[3] - w[1])) / 2, (ch - (w[4] - w[2])) / 2
	local x = a[1] == 0 and a[2] or (a[1] == 1 and wx0 + a[2] or cw - a[2])
	local y = a[3] == 0 and a[4] or (a[3] == 1 and wy0 + a[4] or ch - a[4])
	return x, y
end

-- everything the chart draws for a window `aspect` (layout.py's ops): boxes on the chart
function C.Ops(aspect)
	local D = ns.MapChart
	local w = D.world
	local cw, ch = C.Canvas(aspect)
	local wx0, wy0 = (cw - (w[3] - w[1])) / 2, (ch - (w[4] - w[2])) / 2
	local dx, dy = wx0 - w[1], wy0 - w[2]
	local xs, ys = Axis(cw), Axis(ch)
	local o = { canvas = { cw, ch }, shift = { dx, dy }, paper = {}, ornaments = {}, rays = {}, frame = {} }
	local majorX = #xs >= #ys
	for i, x in ipairs(xs) do
		for j, y in ipairs(ys) do
			local level = majorX and (i - 1) * #ys + (j - 1) or (j - 1) * #xs + (i - 1)
			o.paper[#o.paper + 1] = { { x[1], y[1], x[2], y[2] }, { x[3], y[3], x[4], y[4] }, x[5], y[5], level }
		end
	end
	o.web = { "Web", { dx, dy, dx + D.size, dy + D.size }, D.web[1], D.web[2] }
	local places, moved = Pick(aspect), {}
	for k, orn in ipairs(D.ornaments) do
		local p = places[k + 1]
		if p[5] > 0 then
			local x, y = Unanchor(p, cw, ch)
			local sc = p[5]
			o.ornaments[#o.ornaments + 1] = { "Ornament" .. k, { x, y, x + (orn[3] - orn[1]) * sc, y + (orn[4] - orn[2]) * sc }, orn[5], orn[6] }
			moved[k] = { x, y, sc, orn[1], orn[2] }
		end
	end
	for k, r in ipairs(D.rays) do
		local rose = D.roses[k]
		local m = moved[rose[1]]
		if m then   -- (the rose's centre, where its rays meet, carried with it; the rays keep their size)
			local mx, my = m[1] + (rose[2] - m[4]) * m[3] - rose[2], m[2] + (rose[3] - m[5]) * m[3] - rose[3]
			o.rays[#o.rays + 1] = { "Rays" .. k, { r[1] + mx, r[2] + my, r[3] + mx, r[4] + my }, r[5], r[6] }
		end
	end
	for k, f in ipairs(D.frame) do   -- each in its own corner of the chart, at its scale about the corner
		local right, bottom = (f[1] + f[3]) / 2 > D.size / 2, (f[2] + f[4]) / 2 > D.size / 2
		local cx, cy = right and D.size or 0, bottom and D.size or 0
		local fx, fy = right and cw - D.size or 0, bottom and ch - D.size or 0
		local sc = f[7]
		o.frame[#o.frame + 1] = { "Frame" .. k, { cx + (f[1] - cx) * sc + fx, cy + (f[2] - cy) * sc + fy,
			cx + (f[3] - cx) * sc + fx, cy + (f[4] - cy) * sc + fy }, f[5], f[6] }
	end
	return o
end

--------------------------------------------------------------------------------
-- On the world (world units: Azeroth's map's art px)
--------------------------------------------------------------------------------

-- his sheet on the world: sheet px = A * world unit + b. His two continent pictures are the game's
-- continent maps whole, so their boxes against the maps' own rectangles place it
local place
local function Place()
	if place then return place end
	local D, W, H = ns.MapChart, S.Size()
	if not (D and W) then return end
	local a, bx, by, n = 0, 0, 0, 0
	for id, box in pairs(D.continents) do
		local l, r, t, b = S.Rect(id)
		if not l then return end
		local ax, ay = (box[3] - box[1]) / ((r - l) * W), (box[4] - box[2]) / ((b - t) * H)
		a = a + ax + ay
		bx, by = bx + box[1] - l * W * ax, by + box[2] - t * H * ay
		n = n + 1
	end
	if n == 0 then return end
	a, bx, by = a / (2 * n), bx / n, by / n
	-- the world D.scale times bigger against his art than he drew it, about the world map's middle
	local s = D.scale or 1
	local cx, cy = bx + a * W / 2, by + a * H / 2
	place = { a * s, cx - a * s * W / 2, cy - a * s * H / 2 }
	return place
end

local frame, now                -- the chart's frame (under the art: Stitch.lua's S.chartHost); the layout drawn
local regions = {}              -- name -> texture; paper cuts and their masks by number
local cuts, seams = {}, {}

-- a point on the chart (sheet px) as world units
local function World(x, y)
	local p, sh = Place(), now.shift
	return (x - sh[1] - p[2]) / p[1], (y - sh[2] - p[3]) / p[1]
end

-- places `region` over the chart box (sheet px)
local function Put(region, box)
	local W, H = S.Size()
	local x0, y0 = World(box[1], box[2])
	local x1, y1 = World(box[3], box[4])
	S.PlaceWorld(region, x0 / W, y0 / H, x1 / W, y1 / H)
end

local function Texture(name, layer, sub, wrap)
	local tex = regions[name]
	if not tex then
		tex = frame:CreateTexture(nil, layer, nil, sub)
		tex:SetTexture(TEX .. name, wrap, wrap, "TRILINEAR")
		regions[name] = tex
	end
	return tex
end

local function Mask(file, wrap)
	local m = frame:CreateMaskTexture()
	m:SetTexture(file, wrap, wrap)
	return m
end

local edgeMask                  -- the lines soft at the chart's edge

-- the chart for a view w x h (px), if its shape changed
function C.Layout(w, h)
	if not (C.on and frame and w and h and w > 0 and h > 0 and Place()) then return end
	local aspect = w / h
	if now and math.abs(math.log(now.aspect / aspect)) < 1e-4 then return end
	now = C.Ops(aspect)
	now.aspect = aspect
	local cw, ch = now.canvas[1], now.canvas[2]
	local D = ns.MapChart
	-- the dark ground past the paper's torn edge, tiled
	local bd = Texture("Backdrop", "BACKGROUND", -8, "REPEAT")
	bd:SetTexCoord(0, cw / 1024, 0, ch / 1024)
	Put(bd, { 0, 0, cw, ch })
	-- the paper: each cut of his, fading in over the one before (SeamX / SeamY over its fade, the mask's
	-- edge carried on past it: CLAMP)
	local pu, pv = D.paper[1], D.paper[2]
	for i, p in ipairs(now.paper) do
		local tex = cuts[i]
		if not tex then
			tex = frame:CreateTexture(nil, "BACKGROUND")
			tex:SetTexture(TEX .. "Paper", nil, nil, "TRILINEAR")
			cuts[i] = tex
			seams[i] = { Mask(TEX .. "SeamX", "CLAMP"), Mask(TEX .. "SeamY", "CLAMP") }
		end
		local s, d = p[1], p[2]
		-- (each cut over those before it: two draw layers' sublevels, over the ground's)
		if p[5] < 15 then tex:SetDrawLayer("BACKGROUND", -7 + p[5]) else tex:SetDrawLayer("BORDER", math.min(7, p[5] - 23)) end
		tex:SetTexCoord(s[1] / D.size * pu, s[3] / D.size * pu, s[2] / D.size * pv, s[4] / D.size * pv)
		Put(tex, d)
		local on = seams[i].on or {}
		seams[i].on = on
		for axis = 1, 2 do
			local m, fade = seams[i][axis], p[2 + axis]
			if fade > 0 then
				Put(m, axis == 1 and { d[1], d[2], d[1] + fade, d[4] } or { d[1], d[2], d[3], d[2] + fade })
				if not on[axis] then tex:AddMaskTexture(m) on[axis] = true end
			elseif on[axis] then
				tex:RemoveMaskTexture(m)
				on[axis] = false
			end
		end
		tex:Show()
	end
	for i = #now.paper + 1, #cuts do cuts[i]:Hide() S.UnplaceWorld(cuts[i]) end
	-- the lines, soft at the chart's edge; the ornaments; the frame
	edgeMask = edgeMask or Mask(FEATHER, "CLAMPTOBLACKADDITIVE")
	Put(edgeMask, { 0, 0, cw, ch })
	local shown = {}
	local function Draw(list, layer, sub, masked)
		for _, e in ipairs(list) do
			local tex = Texture(e[1], layer, sub)
			tex:SetTexCoord(0, e[3], 0, e[4])
			Put(tex, e[2])
			if masked and not tex.omEdge then tex:AddMaskTexture(edgeMask) tex.omEdge = true end
			tex:Show()
			shown[e[1]] = true
		end
	end
	Draw({ now.web }, "ARTWORK", 0, true)
	Draw(now.rays, "ARTWORK", 1, true)
	Draw(now.ornaments, "ARTWORK", 2)
	Draw(now.frame, "OVERLAY", 0)
	shown.Backdrop = true
	for name, tex in pairs(regions) do
		if not shown[name] then tex:Hide() end
	end
end

-- the chart on or off (Options' Responsive ocean & border)
function C.SetShown(on)
	on = on and ns.MapChart and S.chartHost and Place() and true or false
	if on and not frame then
		local host = S.chartHost
		frame = CreateFrame("Frame", nil, host[1])
		frame:SetAllPoints(host[1])
		frame:SetFrameLevel(host[2])
		frame:SetScale(S.chartScale or 1)
	end
	C.on = on
	if frame then frame:SetShown(on and S.IsShownNow and S.IsShownNow() or false) end
	if S.SetChart then S.SetChart(on) end
	now = nil
end

function C.Frame() return frame end

-- the least zoom (WorldMap.lua's zoom 1 = the whole world fits): the chart fits the view. fitPx: view
-- px per world unit when the world fits
function C.LeastZoom(w, h, fitPx)
	if not (C.on and Place() and w and h and w > 0 and h > 0 and fitPx and fitPx > 0) then return 1 end
	local cw, ch = C.Canvas(w / h)
	local p = Place()
	return math.min(w / (cw / p[1]), h / (ch / p[1])) / fitPx
end

-- the chart's rectangle on the world (normalized: left, top, right, bottom), for a view w x h
function C.Rect(w, h)
	local p = Place()
	if not (C.on and p and w and h and w > 0 and h > 0) then return end
	local D, W, H = ns.MapChart, S.Size()
	local cw, ch = C.Canvas(w / h)
	local wo = D.world
	local dx, dy = (cw - (wo[3] - wo[1])) / 2 - wo[1], (ch - (wo[4] - wo[2])) / 2 - wo[2]
	local l, t = (0 - dx - p[2]) / p[1], (0 - dy - p[3]) / p[1]
	local r, b = (cw - dx - p[2]) / p[1], (ch - dy - p[3]) / p[1]
	return l / W, t / H, r / W, b / H
end
