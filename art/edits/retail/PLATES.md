# Retail plates to clean

What shows on retail's stitched map where it doesn't belong, found by stacking each continent's
zone maps as Stitch.lua draws them (biggest first, each through its territory). Export the plates
with `OPENMAP_CLIENT=retail python -P tools/map-art/export.py <db2> <tex> <uiMapID> ...` (or use
the ones in `source/`), paint a copy into `edited/` (same name, same size), then run `import.py`.

Paint the lettering or inset out into what's round it (sea and its hatching, or parchment), and
keep the coasts exactly where they are. Leave a zone's own place names alone.

## Continents: insets of places that aren't there, in the sea

| Plate | Paint out |
| --- | --- |
| 619 Broken Isles | the Argus inset (top right) |
| 875 Zandalar | the Nazjatar inset (top right) |
| 876 Kul Tiras | the Nazjatar inset (top right); the "KUL TIRAS" title (top left: it shows over the Broken Isles' sea) |
| 1978 Dragon Isles | the Zaralek Cavern inset (bottom right) |
| 2274 Khaz Algar | the K'aresh inset (top left), the Undermine inset (bottom right) |
| 2537 Quel'Thalas | the Voidstorm and Harandar insets (top) |

## Zones: neighbours' names and sea names left in their margins

| Plate | Paint out |
| --- | --- |
| 1 Durotar | THE GREAT SEA |
| 62 Darkshore | THE VEILED SEA; the faint lettering near Bloodcurse Isle (bottom left) |
| 63 Ashenvale | FELWOOD |
| 69 Feralas | THE VEILED SEA |
| 70 Dustwallow Marsh | SOUTHERN BARRENS |
| 76 Azshara | ORGRIMMAR |
| 77 Felwood | TIMBERMAW HOLD (Winterspring letters it too: two labels, offset) |
| 78 Un'Goro Crater | SILITHUS |
| 18 Tirisfal Glades | the compass rose in the sea |
| 21 Silverpine Forest | HILLSBRAD FOOTHILLS |
| 22 Western Plaguelands | TIRISFAL GLADES |
| 23 Eastern Plaguelands | EVERSONG WOODS |
| 32 Searing Gorge | BADLANDS |
| 37 Elwynn Forest | WESTFALL |
| 42 Deadwind Pass | DUSKWOOD |
| 52 Westfall | THE GREAT SEA; the compass rose |
| 210 The Cape of Stranglethorn | NORTHERN STRANGLETHORN; THE SOUTH SEAS |
| 114 Borean Tundra | the walrus-man and dragon-prow figures in the sea |
| 115 Dragonblight | ICECROWN |
| 116 Grizzly Hills | HOWLING FJORD |
| 117 Howling Fjord | the corner figures in the sea |
| 118 Icecrown | the compass rose |
| 119 Sholazar Basin | the compass rose |
| 120 The Storm Peaks | the compass rose (its N and S) |
| 127 Crystalsong Forest | STORM PEAKS; DRAGONBLIGHT |
| 170 Hrothgar's Landing | THE NORTH SEA |
| 390 Vale of Eternal Blossoms | KUN-LAI SUMMIT |
| 422 Dread Wastes | TOWNLONG STEPPES; VALLEY OF THE FOUR WINDS |
| 634 Stormheim | HIGHMOUNTAIN |
| 641 Val'sharah | HIGHMOUNTAIN |
| 646 Broken Shore | DALARAN (unsure: it labels the floating city drawn there) |
| 680 Suramar | STORMHEIM; the stray letter at the top (the end of a neighbour's name) |
| 896 Drustvar | TIRAGARDE SOUND |
| 942 Stormsong Valley | TIRAGARDE SOUND |
| 2023 Ohn'ahran Plains | THE WAKING SHORES |
| 2248 Isle of Dorn | the Siren Isle banner and inset (top left, in the sea) |
| 2395 Eversong Woods | ISLE OF QUEL'DANAS |
| 2437 Zul'Aman | EVERSONG WOODS |

Unsure, look before painting: Zul'Drak's DRAK'THARON KEEP (a real place on its border with the
Grizzly Hills), Tiragarde Sound's WANING GLACIER (may be its own), Darkshore's sketch of Teldrassil's
tree in the sea.

Not for painting (OpenMap's masks, being fixed in code): the frame corners showing on Kul Tiras'
zones, the Eye of Azshara and Mechagon Island; small island maps showing as parchment rectangles
(Isle of Thunder, the Forbidden Reach, Isle of Quel'Danas, Hrothgar's Landing, Tol Barad, Tol Dagor).
