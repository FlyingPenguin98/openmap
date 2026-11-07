-- Zones' fishing: [uiMapID] = the zone's base fishing level. The client's tables don't carry it (the
-- server rolls each catch), so this is entered by hand from the original game's values as the
-- cMaNGOS project keeps them: classic-db's skill_fishing_base_level table (by zone,
-- github.com/cmangos/classic-db). A cast lands with (your skill - base + 5)% chance, so every cast
-- lands from base + 95: the "skill for the zone" fishing guides give (Elwynn 25, Hillsbrad 150,
-- Stranglethorn 225 ...). Its sub-zones with their own level (Jaguero Isle) and the dungeons aren't
-- here, nor WoW Forever's own zones. Corrections: cite a source.

local _, ns = ...

ns.MapFishing = {
	-- Eastern Kingdoms
	[1416] = 130,   -- Alterac Mountains
	[1417] = 130,   -- Arathi Highlands
	[1420] = -70,   -- Tirisfal Glades
	[1421] = -20,   -- Silverpine Forest
	[1422] = 205,   -- Western Plaguelands
	[1423] = 330,   -- Eastern Plaguelands
	[1424] = 55,    -- Hillsbrad Foothills
	[1425] = 205,   -- The Hinterlands
	[1426] = -70,   -- Dun Morogh
	[1428] = 330,   -- Burning Steppes
	[1429] = -70,   -- Elwynn Forest
	[1430] = 330,   -- Deadwind Pass
	[1431] = 55,    -- Duskwood
	[1432] = -20,   -- Loch Modan
	[1433] = 55,    -- Redridge Mountains
	[1434] = 130,   -- Stranglethorn Vale
	[1435] = 130,   -- Swamp of Sorrows
	[1436] = -20,   -- Westfall
	[1437] = 55,    -- Wetlands
	-- Kalimdor
	[1411] = -70,   -- Durotar
	[1412] = -70,   -- Mulgore
	[1413] = -20,   -- The Barrens
	[1438] = -70,   -- Teldrassil
	[1439] = -20,   -- Darkshore
	[1440] = 55,    -- Ashenvale
	[1441] = 130,   -- Thousand Needles
	[1442] = 55,    -- Stonetalon Mountains
	[1443] = 130,   -- Desolace
	[1444] = 205,   -- Feralas
	[1445] = 130,   -- Dustwallow Marsh
	[1446] = 205,   -- Tanaris
	[1447] = 205,   -- Azshara
	[1448] = 205,   -- Felwood
	[1449] = 205,   -- Un'Goro Crater
	[1450] = 205,   -- Moonglade
	[1451] = 330,   -- Silithus
	[1452] = 330,   -- Winterspring
	-- cities
	[1453] = -20,   -- Stormwind City
	[1454] = -20,   -- Orgrimmar
	[1455] = -20,   -- Ironforge
	[1456] = -20,   -- Thunder Bluff
	[1457] = -20,   -- Darnassus
	[1458] = -20,   -- Undercity
}
