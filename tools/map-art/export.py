# Exports the map art worth hand-cleaning (sea lettering and the like) as full-size PNGs,
# the client's own pixels: the world map, the two continents, and every zone map that
# paints sea. Edit a copy, save it under the same name in art/edits/edited/, and run
# import.py: the tiles you changed replace the client's in the addon.
#
#   art/edits/source/<uiMapID> <name>.png   (regenerate any time; not committed)
#
# usage: python -P tools/map-art/export.py <db2 dir> <texture cache>
import os, sys
import numpy as np
from PIL import Image

here = os.path.dirname(os.path.abspath(__file__))
prev = os.path.join(here, "..", "map-preview")
db2, cache = sys.argv[1:3]
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
