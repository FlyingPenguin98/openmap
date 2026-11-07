# Map colour matching

Generates `OpenMap/Data/Forever/Grade.lua` and the per-zone masks in
`OpenMap/Media/Textures/Forever/` (`MapBand`, `MapTerritory`, `MapCore`) for the stitched world
map's border colour matching and blending.

Needs Python with Pillow, numpy and scipy (`pip install pillow numpy scipy`).
Keep the downloaded textures in a folder outside the repo.

```bash
python -P tools/map-grade/fetch.py OpenMap/Data/Forever/Reveal.lua <tex dir>
python -P tools/map-grade/grade.py OpenMap/Data/Forever/Reveal.lua <tex dir> OpenMap/Data/Forever/Grade.lua OpenMap/Media/Textures/Forever/MapBand <preview dir>
```

Then widen the territories to any land in each zone's rectangle (needs the map
tables; see `tools/map-preview`):

```bash
python -P tools/map-preview/render.py <db2 dir> <tex dir> <out dir> --bake-territory
```

`fetch.py` downloads each overlay texture named in the reveal data by file ID from
wago.tools (cached; reruns skip what's there). `grade.py` rebuilds every zone's
land from its overlays, measures its border band and writes the multipliers, the
band masks and a before/after sheet (`grade_sheet.jpg`) in the preview folder.
