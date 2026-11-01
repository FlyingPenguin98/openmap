# The sea chart alone (no map in the middle: its box outlined), laid out for window shapes, from
# OpenMap/Data/Forever/Chart.lua and Media/Textures/Forever/MapChart/ as the game has them: to check a build.
# render.py OPENMAP_CHART=1 shows it with the map.
#
# usage: python -P tools/map-chart/preview.py <out dir> [aspect ...]   (default 0.46 1.6 1.78 2.39)
import os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import layout as LO

TEX = os.path.join(REPO, "OpenMap", "Media", "Textures", "Forever")
_cache = {}


def texture(name):
    if name not in _cache:
        path = os.path.join(TEX, "MapChart", name)
        if name == "MapFeather":
            path = os.path.join(TEX, name)
        for ext in (".blp", ".tga"):
            if os.path.exists(path + ext):
                _cache[name] = np.asarray(Image.open(path + ext).convert("RGBA"), np.float32) / 255
                break
    return _cache[name]


def main():
    out_dir = sys.argv[1]
    aspects = [float(a) for a in sys.argv[2:]] or [0.46, 1.6, 16 / 9, 3440 / 1440]
    os.makedirs(out_dir, exist_ok=True)
    chart = LO.load_chart(os.path.join(REPO, "OpenMap", "Data", "Forever", "Chart.lua"))
    for asp in aspects:
        cw, ch = LO.canvas_for(asp, chart["world"])
        H = 900 if asp >= 1 else 1400
        W = int(round(H * asp))
        k = W / cw
        img = np.zeros((H, W, 3), np.float32)
        o = LO.draw(img, chart, asp, lambda x, y: (x * k, y * k), texture)
        pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        d = ImageDraw.Draw(pil)
        dx, dy = o["shift"]
        w = chart["world"]
        d.rectangle(((w[0] + dx) * k, (w[1] + dy) * k, (w[2] + dx) * k, (w[3] + dy) * k), outline=(255, 210, 90), width=2)
        path = os.path.join(out_dir, "chart_%.2f.jpg" % asp)
        pil.save(path, quality=90)
        print("wrote", path)


if __name__ == "__main__":
    main()
