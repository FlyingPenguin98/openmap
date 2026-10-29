# Maps drawn by players

WoW Forever's own dungeons have no map in the game. The maps here were drawn by players who let
OpenMap use them; each is credited on the map in game ("Map by ..."). They are not Blizzard's art
and not covered by OpenMap's MIT licence: ask the artist before using them anywhere else.

Santiago Reyes's Ko-fi: https://ko-fi.com/sr433_20

| File | Dungeon | Drawn by |
| --- | --- | --- |
| `dungeons/city-of-dalaran.png` | City of Dalaran | Santiago Reyes |
| `dungeons/excavation-site-wetlands.png` | Excavation Site: Wetlands | Santiago Reyes |
| `dungeons/ruins-of-lordaeron.png` | Ruins of Lordaeron | Santiago Reyes |
| `dungeons/hall-of-thanes.png` | The Hall of Thanes | Santiago Reyes |

`chart/` holds the sea chart round the world map (Options' Responsive ocean & border: the sea, compass roses, sea
creatures, ships and frame), painted by Santiago Reyes and used with his permission; not covered by the
MIT licence either (see its README).

`gaps/` holds the gaps between zones painted by hand on Blizzard's own art (see its README); like the
dungeon maps, they're used with the artist's permission and aren't covered by the MIT licence.

| File | Where | Painted by |
| --- | --- | --- |
| `gaps/G01_dun-morogh-riverglades.png` | Khaz Modan: round Dun Morogh, Loch Modan, Searing Gorge and the Badlands | Santiago Reyes |
| `gaps/G02_tanaris-silithus.png` | Kalimdor: round Tanaris and Silithus | Santiago Reyes |
| `gaps/G03_eastern-plaguelands-western-plaguelands.png` | Eastern Kingdoms: north of the Plaguelands | Santiago Reyes |
| `gaps/G04_stonetalon-mountains-the-barrens.png` | Kalimdor: west of Stonetalon Mountains and the Barrens | Santiago Reyes |
| `gaps/G05_silverpine-forest-hillsbrad-foothills.png` | Eastern Kingdoms: round Silverpine Forest and Hillsbrad Foothills | Santiago Reyes |
| `gaps/G06_thousand-needles-feralas.png` | Kalimdor: between Thousand Needles and Feralas | Santiago Reyes |
| `gaps/G07_winterspring-darkshore.png` | Kalimdor: between Winterspring and Darkshore | Santiago Reyes |
| `gaps/G08_ashenvale-azshara.png` | Kalimdor: between Ashenvale and Azshara | Santiago Reyes |
| `gaps/G09_stranglethorn-vale-blasted-lands.png` | Eastern Kingdoms: between Stranglethorn Vale and the Blasted Lands | Santiago Reyes |
| `gaps/G10_thousand-needles-dustwallow-marsh.png` | Kalimdor: between Thousand Needles and Dustwallow Marsh | Santiago Reyes |
| `gaps/G11_desolace-feralas.png` | Kalimdor: between Desolace and Feralas | Santiago Reyes |

`python -P tools/map-dungeons/drawn.py` turns them into `OpenMap/Media/Textures/MapDungeonDrawn/`
and `OpenMap/Data/DungeonDrawn.lua`. A new one: add the drawing here (a 3:2 picture, the dungeon
map's 1002 x 668 shape) and a line to the script's `DRAWN`.
