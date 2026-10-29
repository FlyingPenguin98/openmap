# The sea chart

Santiago Reyes's sea chart round the world map (Options' **Responsive ocean & border**): the sea, compass roses,
sea creatures, ships, astrolabe, vignette and frame he painted round the game's world map. Used
with his permission; like the rest of `art/drawn/`, it isn't Blizzard's art and isn't covered by
OpenMap's MIT licence: ask him before using it anywhere else. In the game the middle of the chart
is the game's own world map, never his copy of it: his hatching round the continents and the
continents themselves aren't used.

His layers, each flattened on its own over his whole sheet (3840 px square), as he painted them:

| File | What it is | His layer |
| --- | --- | --- |
| `paper.png` | the sheet and the sea painted on it, at half size | Hoja de mapa, Capa 24 |
| `backdrop.png` | a piece of the dark ground the sheet lies on | Fondo |
| `lines.png` | the navigation lines | Líneas Marítimas |
| `ornaments.png` | the compass roses, sea creatures, ships, astrolabe and vignette | Capa 119 |
| `frame.png` | the frame's corners | Marco |
| `sheet.json` | the sheet's size, and where his pictures of the two continent maps sit on it (they place the game's world on the sheet) | |

From his Photoshop file (not committed; 226 MB):

    python -P tools/map-chart/export.py <his .psd>

Then:

    python -P tools/map-chart/build.py <db2 dir> <texture cache>

writes `OpenMap/Media/Textures/MapChart/` and `OpenMap/Data/Chart.lua` (see `tools/map-chart/README.md`).
Restart the game to see new textures.
