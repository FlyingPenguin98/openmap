# The sea chart

Options' **Responsive ocean & border** (off unless chosen): Santiago Reyes's sea chart round the world map
(`art/drawn/chart/`, used with his permission), laid out for the map window's shape. Zoomed right
out, the chart fills the view; the game's own world map stays in its middle, fading into his sea.

- `export.py <his .psd>`: his layers into `art/drawn/chart/` (needs psd-tools).
- `build.py <db2 dir> <texture cache>`: the textures (`OpenMap/Media/Textures/MapChart/`) and `OpenMap/Data/Chart.lua`.
- `layout.py`: the layout, used by both, by `tools/map-preview/render.py` (`OPENMAP_CHART=1`) and by
  `preview.py`. `OpenMap/Map/Chart.lua` does the same in game; `tools/offline-test/chart.py` checks
  the two agree.
- `preview.py <out dir> [aspect ...]`: the chart alone (the middle outlined) for some window shapes.

How it's laid out (`layout.py`, in his sheet's px):

- **The middle.** The game's world map, `SCALE` (build.py) times bigger against his art than he drew
  it, sits in the chart's middle with at least `PAD` of sea round the box where it's at least half
  there; the window's shape gives the other side more. `Middle` is its fade: its continents, islands
  and their coasts whole, and the sea between the continents (the Maelstrom); its sea fading out from
  there, following the coasts. Its open sea is eased toward his (`seaTint`: some colour out, a tint).
- **The paper.** Along each axis his paper is laid in cuts: his torn-edge strip at each end of the
  chart (`EDGE_CUT` long at most), cuts from inside his paper between (`INNER_CUT` at most), each
  fading in over the one before through `SeamX` / `SeamY` (a cross-fade whose edge is bent by smooth
  noise, so a seam is never a straight line). Nothing is stretched; the game's map covers the middle.
- **The lines.** The web of his navigation lines stays with the middle; each compass rose's own
  rays (the lines that meet at its centre) move with that rose. Both fade out before his sheet's
  edge, and at the chart's edge (`MapFeather`).
- **The ornaments** keep their size (the corner ones at most `CORNER` of it). For each window shape
  (`ASPECTS` in `build.py`) each one's place is worked out once: in its own zone (the bands round
  the middle and their corners) at the same share of its room as he painted it; if the game's map
  or another ornament is in the way, the nearest free spot, then the band above or below, then a
  little smaller; never on the game's map. The corner ones stay in their corners (or slide along
  an edge). One with no room at all on a shape is left out there.
- **The frame's corners** sit in the chart's corners, the wooden ones at `FRAME` of his size.

In game (`Chart.lua`, Stitch.lua's `S.SetChart`): the chart is drawn under all of OpenMap's art, in
place of the sea OpenMap draws past the world map (`MapSeaFieldOut`, its mottling, the continents'
sea past the world map's edges); the world map fades into it through `MapChart\Middle`. Zoomed right
out the chart fills the view, and the view pans to its edges and no further (WorldMap.lua:
`LeastZoom`, `Extents`). Its frame is the map's only border: off, the map has none.
