# WoW Forever's cave and dungeon map tiles, copied out of the game into the addon. The game doesn't
# list these tiles (Blizzard's classic dungeon maps and micro maps) for every language: the esMX,
# ruRU and itIT clients (build 1.60.1.70862) can't load them and draw each one as a solid green
# square (--locales shows which languages have them). OpenMap ships them instead and draws them
# from its own folder (Data/Forever/Tiles.lua), for every client.
#   OpenMap/Media/Textures/Forever/MapTile/<file ID>.blp   each tile, as the game has it
# The tiles are the ones Data/Forever/Caves.lua and DungeonMaps.lua name: rerun this after
# tools/map-caves/build.py or tools/map-dungeons/build.py. RADD95's OpenMap TextureFix found the
# cause and fixed it first (credited in Credits.lua).
#
# usage: python -P tools/map-tiles/build.py <World of Warcraft folder> [--locales]
#   --locales: also print which languages the game lists each tile for (the cause, in numbers)
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "casc"))
import clients
from casc import Casc

OUT = os.path.join(clients.tex("forever"), "MapTile")


def tile_ids():
    """every file ID in the Forever cave and dungeon tables' tile lists"""
    ids = set()
    for name in ("Caves.lua", "DungeonMaps.lua"):
        text = open(os.path.join(clients.data("forever"), name), encoding="utf-8").read()
        for group in re.findall(r"\{((?:\s*\d+\s*,){11}\s*\d+\s*)\}", text):
            ids.update(int(x) for x in re.findall(r"\d+", group))
    return sorted(ids)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -P tools/map-tiles/build.py <World of Warcraft folder> [--locales]")
    casc = Casc(sys.argv[1], clients.CLIENTS["forever"]["product"])
    ids = tile_ids()
    os.makedirs(OUT, exist_ok=True)
    keep = {"%d.blp" % f for f in ids}
    for old in os.listdir(OUT):
        if old not in keep:
            os.remove(os.path.join(OUT, old))
    missing, by_locales = [], {}
    for fid in ids:
        try:
            data = casc.read(fid)
        except KeyError:
            missing.append(fid)
            continue
        if data[:4] != b"BLP2":
            raise SystemExit("%d: not a BLP" % fid)
        open(os.path.join(OUT, "%d.blp" % fid), "wb").write(data)
        if "--locales" in sys.argv:
            key = ",".join(casc.locales(fid)) or "none"
            by_locales[key] = by_locales.get(key, 0) + 1
    print("wrote %d tiles to %s" % (len(ids) - len(missing), OUT))
    for key, n in sorted(by_locales.items()):
        print("  listed for %s: %d" % (key, n))
    if missing:
        raise SystemExit("not in this install: %s" % ", ".join(map(str, missing)))


if __name__ == "__main__":
    main()
