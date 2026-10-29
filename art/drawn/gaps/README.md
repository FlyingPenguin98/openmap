# Gaps painted by hand

Land on the continent maps that no zone map covers, painted over by hand: Blizzard's own zone art
cloned, warped and retouched to fill the blank parchment between zones, following the game's own
minimap for what's there. No generated art, and no places or landmarks the game doesn't have.

- `regions.json`: the regions, each with its place on its continent (world units from the
  continent map's top-left), its scale and its size. Kept fixed, so a painting always lines up.
- `G01_<zones>.png` ...: the paintings, named after their region. One may come back at another size
  (a whole-number scale is best). On the game's land only the part inside the region's fill area
  is used; out at sea the painter's own coast is: the land he painted, his shallows and the ink line
  off his shore, fading out into the game's sea past them (his open sea isn't used). A painting may
  leave its sea clear (transparent): its colours there are used as an opaque one's are.
- `fits.json`: how each painting lines up with its region (found once; delete an entry to fit again).

To export the plates an artist paints on (each region's zone art, its fill area, the minimap and
how the map looks there now) into `source/` (not committed):

    python -P tools/map-preview/gapregions.py <db2 dir> <texture cache> [--only G01,G02]

A painting comes back as a Photoshop file (not committed). Its PNG here is the composite saved in it,
as he saw it:

    python -P tools/map-preview/gapexport.py <his .psd> [...]

The plates' zone art sat on top of his paint layers. In G08 (south of Hyjal), where that art faded out
over the gap it was the zones' blank parchment, 75-100% opaque over his finished mountains, so G08 is
flattened without it over its fill area (the script's `UNCOVERED`). The others have the same layer over
parts of their fill areas, mixing that parchment with Blizzard's own drawing he painted round: his to
say, so they're as he saved them. G01's is his full-size file's composite, kept at half size.

Then, with a painting here:

    python -P tools/map-preview/gapfills.py
    python -P tools/map-preview/gapplaces.py <db2 dir> <texture cache>
    python -P tools/map-preview/render.py <db2 dir> <texture cache> <out> --bake-zones

The first writes `OpenMap/Media/Textures/MapGapFill/` and `OpenMap/Data/GapFills.lua`; the second
the places a painting shows that no zone map draws (WoW Forever's own, the Wetlands' Excavation
Site), which the map hides or darkens with unexplored areas until they're found (it lists the
others the paintings show: a new one painted as a place of its own goes in its `PLACES`); the
third bakes the paintings into the zone tiles (`MapZones/`), which draw them at most zooms. Restart
the game to see new textures. Options' Filled gaps turns them off.

| Region | Painted by |
| --- | --- |
| G01 Khaz Modan: round Dun Morogh, Loch Modan, Searing Gorge and the Badlands | Santiago Reyes |
| G02 Kalimdor: round Tanaris and Silithus | Santiago Reyes |
| G03 Eastern Kingdoms: north of the Plaguelands | Santiago Reyes |
| G04 Kalimdor: west of Stonetalon Mountains and the Barrens | Santiago Reyes |
| G05 Eastern Kingdoms: round Silverpine Forest and Hillsbrad Foothills | Santiago Reyes |
| G06 Kalimdor: between Thousand Needles and Feralas | Santiago Reyes |
| G07 Kalimdor: between Winterspring and Darkshore | Santiago Reyes |
| G08 Kalimdor: between Ashenvale and Azshara | Santiago Reyes |
| G09 Eastern Kingdoms: between Stranglethorn Vale and the Blasted Lands | Santiago Reyes |
| G10 Kalimdor: between Thousand Needles and Dustwallow Marsh | Santiago Reyes |
| G11 Kalimdor: between Desolace and Feralas | Santiago Reyes |
