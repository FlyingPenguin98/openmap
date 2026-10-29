# Where these textures come from (retail)

OpenMap draws no art of its own. Every texture here is either cut from World of
Warcraft's own map art (Blizzard Entertainment's, not covered by OpenMap's MIT
licence) or generated from noise. Each is made by a script in `tools/`, so it can
be rebuilt from the game's files. Retail's map itself is the game's art as it is
(its world, continent and zone maps, drawn from the client); these are the masks
that fit them together.

**OpenMap's own icon**: `OpenMapIcon` and `OpenMapIconRound` (cut to the compass's ring) (shared by both clients, in `Media/Textures/`: the AddOns list,
the minimap button, the map's menu and portrait) is OpenMap's own picture, not Blizzard's: a compass
over a parchment map, shrunk from `art-icon/openmap.jpg` by `tools/icon/build.py`.

**From Blizzard's art** (shapes traced from the game's map art and tables):

| Texture | What it is | Made by |
| --- | --- | --- |
| `MapTerritory/` | where each zone map's art shows over its continent's: its own land (its explored-area pieces, filled) and cities, and what it paints round them, shared with its neighbours | `tools/map-preview/territory.py` |
| `MapBackLand/` | where each continent map's art shows over the world map's: all of it but the other continents' land and the band of shallows round it; and the world map's own (`947`): all of it but its metal frame and burnt edge | `tools/map-preview/territory.py` |
| `MapMiniLand/` | where the close-up minimap shows: the zones' own land on each continent's map | `tools/map-preview/territory.py` |
| `MapCave/` | masks traced from the cave maps (Blizzard's micro maps): the cave without its parchment, frame, title or corners | `tools/map-caves/build.py` |
| `MapPaper` | blank map parchment, from the classic Westfall zone map (WoW Forever's, as it is): the dungeon map's and What's new's page, and the parchment past the world map's edges | `tools/map-textures/shared.py` (cut by `tools/map-preview/gapfill.py`) |
| `MapBorder/` | the map art's parchment frame (cut out by hand from the classic continent map), in nine pieces | `tools/map-art/border.py` |

**Generated** (no game art in them): `MapGrain`, `MapTooth` (paper grain, from noise)
and the `MapFeather*` edge masks (`tools/map-textures/make.py`).
