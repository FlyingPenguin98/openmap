# Exports the map art worth hand-cleaning (sea lettering and the like) as full-size PNGs,
# the client's own pixels: the world map, the two continents, and every zone map that
# paints sea. Edit a copy, save it under the same name in art/edits/edited/, and run
# import.py: the tiles you changed replace the client's in the addon.
#
#   art/edits/source/<uiMapID> <name>.png   (regenerate any time; not committed)
#
# Another client (OPENMAP_CLIENT, tools/clients.py) exports the maps named, each map's own base
# art (its explored-area pieces aren't in it: they're drawn over it), to art/edits/<client>/source/:
#
# usage: python -P tools/map-art/export.py <db2 dir> <texture cache> [uiMapID ...]
import os, sys
import numpy as np
from PIL import Image

here = os.path.dirname(os.path.abspath(__file__))
prev = os.path.join(here, "..", "map-preview")
sys.path.insert(0, os.path.join(here, ".."))
import clients   # the client the tools build for (OPENMAP_CLIENT)
db2, cache = sys.argv[1:3]

if clients.NAME != "forever":
    import uimap
    sys.path.insert(0, prev)
    from whole import Art
    ids = [int(a) for a in sys.argv[3:]]
    if not ids: sys.exit("name the maps to export (uiMapIDs): docs/retail.md lists the ones with lettering in the way")
    base = os.path.join(here, "..", "..", "art", "edits", clients.NAME)
    out = os.path.join(base, "source")
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(base, "edited"), exist_ok=True)
    w, art = uimap.World(db2), Art(db2, cache)
    for m in ids:
        a, aw, ah, tw, th = w.art(m)
        img = Image.fromarray((np.clip(art.image(a, aw, ah, tw, th, 1.0)[..., :3], 0, 1) * 255).astype(np.uint8))
        name = "%d %s.png" % (m, w.uimap[m]["Name_lang"].replace("'", ""))
        img.save(os.path.join(out, name))
        print(name, "%d x %d" % (aw, ah))
    print(len(ids), "maps ->", os.path.normpath(out))
    sys.exit()

sys.argv = ["render.py", db2, cache, os.path.join(cache, "_preview")]
g = {"__name__": "export", "__file__": os.path.join(prev, "render.py")}
src = open(os.path.join(prev, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)

out = os.path.join(here, "..", "..", "art", "edits", "source")
os.makedirs(out, exist_ok=True)
os.makedirs(os.path.join(here, "..", "..", "art", "edits", "edited"), exist_ok=True)
picked = [m for m in g["maps"] if m["id"] == 947 or m["kind"] == 2]
for z in g["zones"]:
    if g["reveal"].get(z["art"]) and g["zone_sea"](z).sum() > 3000:
        picked.append(z)
for m in picked:
    img = Image.fromarray((np.clip(g["base"](m)[..., :3], 0, 1) * 255).astype(np.uint8))
    name = "%d %s.png" % (m["id"], m["name"].replace("'", ""))
    img.save(os.path.join(out, name))
    print(name)
print(len(picked), "maps ->", os.path.normpath(out))
