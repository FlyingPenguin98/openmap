--------------------------------------------------------------------------------
-- The controller view (padView, a test; off unless chosen): with the game's Gamepad UI on, OpenMap's
-- stitched map drawn over Blizzard's world map on a frame of its own, Blizzard's map left as it is.
--
-- Why a frame of its own: on OpenMap's usual map (WorldMap.lua) the view is Blizzard's scroll
-- container, driven by OpenMap: its zoom and scroll written by OpenMap's code, its ResetZoom and
-- scroll extents OpenMap's. The Gamepad UI reads that same state each time the map changes, and the
-- controller's bindings it then makes (the map footer's, the binding stack's) carry OpenMap's taint:
-- closing the map then has the game block SetPreferredGamepadInteractTarget, and the taint stays in
-- the binding stack until a reload. Here nothing of Blizzard's map is written or replaced: its canvas
-- is only made see-through while this view covers it, and its gamepad functions only hooked
-- (hooksecurefunc), so the Gamepad UI's own code (the cursor, B, the D-pad, the focus) stays secure.
--
-- The controller, read rather than bound: the cursor is Blizzard's (SoftCursor, its left stick), the
-- right stick is read from the controller (mod.PadStickTilt) and zooms about the cursor, the cursor at
-- the view's edge pans as Blizzard's map does (its gamepadScrollSpeed, read), A zooms into the zone
-- under the cursor and X out a level (after Blizzard's own, on its map underneath, unseen).
-- For now the art, the place names and your arrow; not yet the map's icons (dungeons, flight paths,
-- Questie's, pins), OpenMap's menu or the quest log's areas.
--------------------------------------------------------------------------------

local _, ns = ...
local S = ns.MapStitch
local mod = ns:GetModule("worldmap")
local WORLD = S.WORLD

local ART_RANGE = 80            -- frame levels the stitched art takes (as WorldMap.lua's)
local GLIDE_TIME = 0.4          -- A and X's zoom, as a click's on the usual map
local PAD_ZOOM_RATE = 1.8       -- the right stick at full tilt, per second in log zoom (as WorldMap.lua's)
local CITY_ZOOM = 1.5           -- deeper over a city (as WorldMap.lua's)
local PLAYER_EVERY = 0.1        -- seconds between moves of your arrow

local map, sc, view, canvas
local built, failed = false, false
local u, v, zoom                -- the view: world centre (normalized) and zoom (1: the whole world fits)
local glide                     -- A or X's zoom under way
local lastX, lastY              -- the pad's cursor on the last frame (screen px): Blizzard re-centres it
                                --  as A or X changes its map, before the hooks below run
local dirty = false
local playerWait = 0

local function Clamp(x, lo, hi) return math.max(lo, math.min(hi, x)) end

local function On()
	return mod.db and mod.db.padView and not mod.enabled and mod.PadUI and mod.PadUI() or false
end

--------------------------------------------------------------------------------
-- Geometry (WorldMap.lua's, on this view)
--------------------------------------------------------------------------------

local function FitPx()
	local W, H = S.Size()
	return math.min(view:GetWidth() / W, view:GetHeight() / H)
end

local function DetailK()
	local W, H = S.Size()
	local w, h = view:GetWidth(), view:GetHeight()
	local k = ns.ClientMaps and ns.ClientMaps.zoom or 1
	if not W or w <= 0 or h <= 0 then return 1 / k end
	return math.min(w / W, h / H) / math.sqrt(w * h / (W * H)) / k
end

local function Stitchable(mapID)
	if not mapID or mapID == WORLD then return mapID == WORLD end
	local info = C_Map.GetMapInfo(mapID)
	if not info or (info.mapType ~= Enum.UIMapType.Continent and info.mapType ~= Enum.UIMapType.Zone) then return false end
	return S.Rect(mapID) ~= nil and S.ArtSize(mapID) ~= nil and S.Stitched(mapID, true)
end

local function FitZoom(mapID)
	local W, H = S.Size()
	local l, r, t, b = S.Rect(mapID)
	return math.min(view:GetWidth() / ((r - l) * W), view:GetHeight() / ((b - t) * H)) / FitPx()
end

local function MostAt(cu, cv)
	return (mod.db.maxZoom or 64) * ((cu and S.InCity and S.InCity(cu, cv)) and CITY_ZOOM or 1)
end

-- a screen point (px, as GetCursorPosition) -> its offset from the view's centre (view px, y down)
local function Offset(x, y)
	local l, b, w, h = view:GetRect()
	if not l then return 0, 0 end
	local es = view:GetEffectiveScale()
	return x / es - (l + w / 2), (b + h / 2) - y / es
end

-- the world point at a view offset
local function WorldAt(sx, sy)
	local W, H = S.Size()
	local px = FitPx() * zoom
	return u + sx / (W * px), v + sy / (H * px)
end

-- the pad's cursor (screen px), while the map has the pad
local function Cursor()
	local soft = _G.SoftCursor
	if not (soft and soft:IsShown()) then return end
	if map.IsCanvasGamepadFocus and not map:IsCanvasGamepadFocus() then return end
	local l, b, w, h = soft:GetRect()
	if not l then return end
	local es = soft:GetEffectiveScale()
	return (l + w / 2) * es, (b + h / 2) * es
end

--------------------------------------------------------------------------------
-- The view
--------------------------------------------------------------------------------

local function Apply()
	dirty = false
	local W, H = S.Size()
	local px = FitPx() * zoom
	if not W or px <= 0 then return end
	zoom = Clamp(zoom, 1, math.max(1, MostAt(u, v), zoom))
	u, v = Clamp(u, 0, 1), Clamp(v, 0, 1)
	canvas:SetScale(px)
	canvas:ClearAllPoints()
	canvas:SetPoint("TOPLEFT", view, "CENTER", -u * W, v * H)     -- (offsets in the canvas's own units)
	local dk = DetailK()
	S.SetZoom(zoom * dk, px)
	local hu, hv = view:GetWidth() / 2 / (W * px), view:GetHeight() / 2 / (H * px)
	S.SetView(u, v, hu, hv, zoom * dk, zoom / (ns.ClientMaps and ns.ClientMaps.zoom or 1))
	S.PlacePlayer()
end

-- to zoom `to`, the world point under the view offset (sx, sy) kept there
local function ZoomAbout(sx, sy, to)
	local W, H = S.Size()
	local cu, cv = WorldAt(sx, sy)
	local most = MostAt(cu, cv)
	if to > zoom then most = math.max(most, zoom) end
	to = Clamp(to, 1, most)
	local px = FitPx() * to
	u, v, zoom = cu - sx / (W * px), cv - sy / (H * px), to
	dirty = true
end

local function GlideTo(tu, tv, tz)
	glide = { u0 = u, v0 = v, z0 = zoom, u1 = tu, v1 = tv, z1 = Clamp(tz, 1, MostAt(tu, tv)), t = 0 }
end

local function Glide(elapsed)
	local a = glide
	a.t = math.min(1, a.t + elapsed / GLIDE_TIME)
	local e = a.t * a.t * (3 - 2 * a.t)
	zoom = math.exp(math.log(a.z0) + (math.log(a.z1) - math.log(a.z0)) * e)
	-- (the centre moves with 1/zoom: one zoom about a fixed point, as WorldMap.lua's)
	local w = math.abs(a.z1 - a.z0) < 1e-6 and e or (1 / a.z0 - 1 / zoom) / (1 / a.z0 - 1 / a.z1)
	u, v = a.u0 + (a.u1 - a.u0) * w, a.v0 + (a.v1 - a.v0) * w
	if a.t >= 1 then glide = nil end
	dirty = true
end

-- A: into the zone (or continent) under the cursor; X: out a level (as a click and right-click)
local function Step(inward)
	local cu, cv
	if lastX then cu, cv = WorldAt(Offset(lastX, lastY)) else cu, cv = u, v end
	local chain = S.ChainAt(cu, cv)
	if inward then
		for _, id in ipairs(chain) do
			if id ~= WORLD and Stitchable(id) and FitZoom(id) > zoom * 1.05 then
				local l, r, t, b = S.Rect(id)
				GlideTo((l + r) / 2, (t + b) / 2, FitZoom(id))
				return
			end
		end
	else
		local target = WORLD
		for _, id in ipairs(chain) do
			if id ~= WORLD and Stitchable(id) and FitZoom(id) < zoom * 0.95 then target = id end
		end
		local l, r, t, b = S.Rect(target)
		GlideTo((l + r) / 2, (t + b) / 2, FitZoom(target))
	end
end

local function UpdatePlayer()
	local best = C_Map.GetBestMapForUnit("player")
	local pos = best and S.Rect(best) and C_Map.GetPlayerMapPosition(best, "player")
	local x, y
	if pos then x, y = ns.Safe.XY(pos) end
	if ns.Safe.IsSecret(x) or ns.Safe.IsSecret(y) or not (x and y) then S.SetPlayer(nil) return end
	local l, r, t, b = S.Rect(best)
	S.SetPlayer(l + x * (r - l), t + y * (b - t), ns.Safe.Call(GetPlayerFacing))
end

local function OnUpdate(_, elapsed)
	local x, y = Cursor()
	local tilt = x and mod.PadStickTilt and mod.PadStickTilt() or 0
	if tilt ~= 0 then
		glide = nil
		local sx, sy = Offset(x, y)
		ZoomAbout(sx, sy, zoom * math.exp(tilt * PAD_ZOOM_RATE * elapsed))
	end
	-- the cursor at the view's edge: Blizzard's pan speed for its map (view px a second), ours too
	local speed = x and sc.gamepadScrollSpeed
	local sxs, sys = speed and tonumber(speed.X) or 0, speed and tonumber(speed.Y) or 0
	if sxs ~= 0 or sys ~= 0 then
		glide = nil
		local W, H = S.Size()
		local px = FitPx() * zoom
		u, v = u + sxs * elapsed / (W * px), v - sys * elapsed / (H * px)
		dirty = true
	end
	if glide then Glide(elapsed) end
	if x then lastX, lastY = x, y end
	playerWait = playerWait - elapsed
	if playerWait <= 0 then
		playerWait = PLAYER_EVERY
		UpdatePlayer()
	end
	if dirty then Apply() end
end

--------------------------------------------------------------------------------
-- Building it, showing it
--------------------------------------------------------------------------------

-- OpenMap's look, as its Options have it (WorldMap.lua's Refresh, the parts that are the art's)
local function Look()
	local db = mod.db
	S.SetPlayerHidden(db.playerArrow == false)
	S.SetPlacesFrom(db.iconsFrom)
	S.SetFoundOnly(db.foundOnly)
	S.SetIconScale(db.iconScale or 1)
	S.SetGapFillsShown(db.gapFills ~= false)
	if S.SetDarkening then S.SetDarkening(db.darkening or 1, db.darkenColor or nil) end
	S.ApplyGrade(db.colorMatch, db.desaturate, mod.Unexplored())
end

local function Build()
	if built or failed then return built end
	if S.IsBuilt() then failed = true return false end   -- (built on Blizzard's map already: OpenMap's usual map)
	local base = sc.Child:GetFrameLevel() + 2
	view:SetFrameLevel(base)
	canvas:SetFrameLevel(base)
	S.Build(canvas, base + 1, ART_RANGE, base + ART_RANGE + 4)
	local W, H = S.Size()
	if not (S.IsBuilt() and W and S.Layout(WORLD)) then failed = true return false end
	canvas:SetSize(W, H)
	S.RaiseArrow(base + ART_RANGE + 40)
	S.SetShown(true)
	Look()
	built = true
	return true
end

-- the view to open on: where it was, else around you, your zone filling it
local function FirstView()
	UpdatePlayer()
	local best = C_Map.GetBestMapForUnit("player")
	local l, r, t, b
	if best then l, r, t, b = S.Rect(best) end
	local pos = best and C_Map.GetPlayerMapPosition(best, "player")
	local x, y
	if pos then x, y = ns.Safe.XY(pos) end
	if l and x and y and not ns.Safe.IsSecret(x) and not ns.Safe.IsSecret(y) then
		u, v = l + x * (r - l), t + y * (b - t)
		local zone = best
		while zone and not Stitchable(zone) do
			local info = C_Map.GetMapInfo(zone)
			zone = info and info.parentMapID and info.parentMapID > 0 and info.parentMapID or nil
		end
		zoom = zone and FitZoom(zone) or 4
	else
		u, v, zoom = 0.5, 0.5, 1
	end
end

local function Show()
	if not On() or not Build() then
		view:Hide()
		if built then sc.Child:SetAlpha(1) end
		return
	end
	if not u then FirstView() end
	glide = nil
	sc.Child:SetAlpha(0)      -- (Blizzard's map underneath: there, unseen; nothing of it written)
	view:Show()
	dirty = true
end

local function Hide()
	view:Hide()
	glide, lastX, lastY = nil, nil, nil
	if sc and sc.Child then sc.Child:SetAlpha(1) end
end

-- for WorldMap.lua: built here, OpenMap's usual map can't be (its art is on this view): a reload then
function mod.PadViewBuilt() return built end

local function Setup()
	map = _G.WorldMapFrame
	sc = map and map.ScrollContainer
	if not (sc and sc.Child and map.GetCanvas) or view then return end
	view = CreateFrame("Frame", nil, map)
	view:SetAllPoints(sc)
	view:SetClipsChildren(true)
	view:Hide()
	canvas = CreateFrame("Frame", nil, view)
	canvas:SetSize(1, 1)
	view:SetScript("OnUpdate", OnUpdate)
	view:SetScript("OnSizeChanged", function() dirty = true end)
	map:HookScript("OnShow", Show)
	map:HookScript("OnHide", Hide)
	-- A and X: after Blizzard's own (GamepadMapClick, GamepadMapUp) on its map underneath
	if map.NavigateToGamepadCursor then
		hooksecurefunc(map, "NavigateToGamepadCursor", function() if view:IsShown() then Step(true) end end)
	end
	if map.NavigateToParentMap then
		hooksecurefunc(map, "NavigateToParentMap", function() if view:IsShown() then Step(false) end end)
	end
	local owner = {}
	ns.RegisterEvent(owner, "INPUT_DEVICE_INTERFACE_TRANSITION", function()
		if map:IsShown() then if On() then Show() else Hide() end end
	end)
	if map:IsShown() then Show() end
end

-- WorldMap.lua's OnEnable, with the Gamepad UI on and padView chosen (OpenMap's usual map waiting)
function mod.StartPadView()
	if _G.WorldMapFrame then
		Setup()
	elseif EventUtil and EventUtil.ContinueOnAddOnLoaded then
		EventUtil.ContinueOnAddOnLoaded("Blizzard_WorldMap", Setup)
	end
end
