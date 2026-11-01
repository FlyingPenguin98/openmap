# OpenMap for retail

OpenMap runs on retail World of Warcraft (Midnight, `## Interface: 120105`) as well as WoW Forever,
from one codebase: retail's toc is `OpenMap/OpenMap_Mainline.toc`, its data `OpenMap/Data/Retail/`,
its textures `OpenMap/Media/Textures/Retail/` (see [development.md](development.md#clients)). Its zip
is a file of its own on CurseForge (`--client=retail`, [releasing.md](releasing.md)).

## How retail's map differs

Retail's maps aren't WoW Forever's, and the map is built from them differently:

- **The world.** Azeroth's map (947) holds twelve continents, not two, and its art is 3840 x 2560
  (Forever's 1002 x 668). A zone is about half as wide on it, so the layers' fades go by twice the zoom
  (`Data/Retail/Client.lua`'s `zoom`), and the deepest zoom goes twice as far.
- **Which maps are stitched** comes from `Data/Retail/World.lua` (`tools/map-data/world.py`, where
  its rules are): the open-world zones on the game's navigation bar, one version of each. Left out:
  Vashj'ir (under the sea), Khaz Algar's underground (right under the Isle of Dorn on Azeroth's map),
  Quel'Thalas before Midnight (game map 530), class halls, scenarios, and the places Azeroth's map
  doesn't place (Outland, Draenor, the Shadowlands, Argus, the Maelstrom, Nazjatar, K'aresh,
  Undermine, the Emerald Dream ...): Blizzard's own map shows those as it always has.
- **The world and continents are painted whole.** Their art paints its own sea and coasts, so there's
  no sea of OpenMap's, and no gap filling, colour matching or hand-cleaned art: the map is Blizzard's art
  as it is, fitted together by masks traced from it (`tools/map-preview/territory.py`): each
  continent's art over the world's (its sea too, but never over another continent's land and
  shallows), each zone's on its own land and what it paints round it over its continent's.
- **The zones are as WoW Forever's**: their base art is blank parchment (the coasts, rivers and
  mountains), painted by their explored-area pieces (`Reveal.lua`), which OpenMap draws whether you've
  explored them or not, unless "Hide unexplored areas" is on (blank parchment till you've been there,
  as Blizzard's own map). "Darken unexplored areas" takes Forever's colour-matched zones' land masks, so
  retail's menu doesn't offer it.
- **The world's edge.** Azeroth's art is a torn parchment with a metal frame at two corners: it's drawn
  out to its torn edge (`MapBackLand/947`, traced from the art: what's dark or cool and joined to the
  art's edge, and what that rings round), and past it the parchment runs on (`MapPaper`, tinted to the
  art's margin: `Territories.lua`'s `MapPaperOut`), so a wide map window shows more parchment, not a fade.
- **The zones come in continent by continent.** Each continent's zones fade in where its own art runs
  out of pixels (`Client.lua`'s `detailDensity`): Pandaria's and the Broken Isles' continent maps are
  coarse (1002 px wide), so their zones come in soon; Quel'Thalas' and the Dragon Isles' are fine, so
  theirs later. A zone that hasn't come in isn't drawn or loaded at all. The fade is slow (`detailFade`)
  and starts with no faint hint from further out (`detailHint`).
- **World positions** (flight masters, entrances, docks, the minimap) go through each game map's
  place on Azeroth's map (`World.lua`'s `yards`), worked out from the tables (`tools/uimap.py`).

## What comes from where

| Data | From | Made by |
| --- | --- | --- |
| `World.lua` | the map tables | `tools/map-data/world.py` |
| `Places.lua` | the map tables; entrances from the encounter journal (`JournalInstanceEntrance`), docks from the map's own points of interest ("Boat to ...") | `tools/map-data/build.py` |
| `Reveal.lua` | the stitched zones' explored-area pieces (`WorldMapOverlay`) | `tools/map-data/build.py` |
| `Minimap.lua` | each game map's own world file | `tools/map-data/minimap.py` |
| `FlightData.lua` | the taxi tables | `tools/map-flights/flights.py` |
| `DungeonMaps.lua` | the dungeon maps and their floors in the map tables | `tools/map-dungeons/tables.py` |
| `Territories.lua`, `Tones.lua` and the masks | the zones' explored-area pieces and art; the world's art (its outline and margin colour) | `tools/map-preview/territory.py` |
| `Caves.lua`, `MapCave/` | the cave maps (micro maps) on the stitched world | `tools/map-caves/build.py` |

Zone levels come from the game itself (`C_Map.GetMapLevels`), as its own map shows them.

## Regenerating

With retail's tables in a folder (`<db2>`: UiMap, UiMapArt, UiMapArtTile, UiMapArtStyleLayer,
UiMapAssignment, UiMapGroupMember, UiMapXMapArt, WorldMapOverlay, WorldMapOverlayTile, Map, AreaTable,
TaxiNodes, TaxiPath, TaxiPathNode, JournalInstance, JournalEncounter, JournalInstanceEntrance, AreaPOI,
from `https://wago.tools/db2/<Table>/csv?build=12.1.5.70448`) and a texture cache (`<tex>`):

```bash
export OPENMAP_CLIENT=retail
python -P tools/map-data/world.py <db2>
python -P tools/map-data/build.py <cache>          # (fetches its tables into <cache>)
python -P tools/map-data/minimap.py <cache>
python -P tools/map-flights/flights.py <db2> OpenMap/Data/Retail/FlightData.lua
python -P tools/map-dungeons/tables.py <db2>
python -P tools/map-preview/territory.py <db2> <tex>
python -P tools/map-caves/build.py <cave cache>
python -P tools/map-textures/make.py
python -P tools/map-art/border.py
python -P tools/map-textures/shared.py
```

The build is `tools/clients.py`'s; a new one needs its tables and a rerun of all of these.

### The zones' highlights (once, in game)

A zone's territory reaches out from its own land (its explored-area pieces) by a fixed distance. Its
whole area, as its continent's map draws it, is better: the glow the map shows on the zone under the
cursor. Where the game draws that glow is only known in game, so it's recorded there once:

1. In retail, with OpenMap on, type `/openmap highlights` (it takes a few seconds), then `/reload`.
2. `python -P tools/map-preview/highlights.py <WoW>/_retail_/WTF/Account/<account>/SavedVariables/OpenMap.lua`
   writes `tools/map-preview/highlights/retail.txt` (commit it: it's the game's own data).
3. Rerun `territory.py`: with the highlights, a zone's painting covers its whole area and reaches only a
   little past it (`REACH_AREA`), so zones meet along the continent map's own borders.

## Checking

As for Forever (lint, `run.py` plain / combat / secret), with `OPENMAP_CLIENT=retail`, and:

- `python -P tools/offline-test/world.py <db2>` builds the stitched world in the stub, with the map
  answering from the tables, sweeps the view over every continent, and prints the textures drawn at
  each zoom (it fails on any Lua error; run it for both clients after a change to the map code).
- `python -P tools/map-preview/whole.py <db2> <tex> <out> name=u,v,zoom ...` renders retail's stitched
  map out of game, as Stitch.lua draws it.

## Not done, or not known yet

- Nothing has been checked in game: the whole retail build needs a first look (and textures need a full
  client restart).
- Townsfolk (vendors, trainers, rares) and dungeon quests come from Questie, which retail doesn't have:
  the menu leaves townsfolk out; dungeon quests work through Dungeon Journal or NeedRoll if a retail
  version of either is installed.
- Four dungeon floors drawn larger than the classic 1002 x 668 (Battle of Dazar'alor, The Nokhud
  Offensive, Vault of the Incarnates' Valdrakken floor, Dawn of the Infinite) are left out of the
  dungeon view; The Nokhud Offensive has no other floor, so its entrance opens nothing.
- Khaz Algar's underground dungeons have no entrance pins (their zones aren't stitched).
- No shrunk minimap for the mid zooms (`MapMiniLOD`: the game's own tiles show from close in), no baked
  zone tiles (`MapZones`) and no lettered names: retail's art letters its own.
- The flight time estimate uses classic's flight speed.
- **Seams between zones.** Retail's zone maps are each toned their own way (Crystalsong Forest's
  yellow beside Dragonblight's snow), and with no colour matching (Forever's `MapBand` / `Grade.lua`)
  they show as patches where a zone's art hands over to the next or to the continent's, most at the
  zoom where the zones come in. A colour match made for retail's art is the next step.
- **Performance.** `tools/offline-test/world.py` counts at most about 1,030 art textures drawn where
  the continents' art comes in (zoom 3; it's 3840 x 2560 a continent) and about 1,200 where the zones
  are in (zoom 13, over a continent of the newer 3840 x 2560 zone maps: about 150 base tiles and 250
  piece tiles each), against about 650 at Forever's worst (with its baked tiles). What's drawn for
  nothing is left out (`Territories.lua`: empty piece tiles and tiles off a zone's territory, and base
  tiles under opaque pieces while the unexplored areas show), which took the zone peak down from about
  1,550. Measure with `/openmap bench` in game; if it's slow there, baked zone tiles (Forever's
  `MapZones`) are the cure, at a cost: retail's world units are four times smaller, so tiles fine
  enough to carry the zooms where the zones are in (6 to 8 px per world unit) would add 100 to 200 MB
  to the download; at 4 px (about 50 MB) the live layers take over again near zoom 10, where the count
  is still high.
- From retail's UI source (the `live` branch of wow-ui-source), to look at in game:
  - its quest log shows its own Quests / Events / Map Legend tabs, which Forever hides: beside
    OpenMap's dungeon tabs there may be two "Quests";
  - the map's "World" button goes to the cosmic map (946), leaving the stitched map;
  - the zone highlight on hover ("Highlight the zone", off by default) only shows over the host
    map's own rectangle;
  - Blizzard's filter and pin buttons sit at the map's top right (the dungeon card is moved below
    them), and its own dungeon entrance pins are hidden while the map is stitched;
  - the gamepad cursor code is Forever's: on retail it does nothing.
- Three caves' masks came out as most of their page (their art is pale): they show as a parchment
  rectangle when they surface.
