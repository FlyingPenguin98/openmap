# Santiago Reyes's sea chart (his Photoshop file, not committed: 226 MB) into the layers OpenMap's chart
# is made from, art/drawn/chart/ (committed, as his other art in art/drawn/ is). Each layer flattened on
# its own over his whole sheet (3840 px square), as he painted it; tools/map-chart/build.py does the rest.
#   paper.png        the sheet and the sea painted on it (his "Hoja de mapa" and "Capa 24"), half size
#   backdrop.png     a piece of the dark ground the sheet lies on ("Fondo")
#   lines.png        the navigation lines ("Lineas Maritimas")
#   ornaments.png    the compass roses, sea creatures, ships, astrolabe and vignette ("Capa 119")
#   frame.png        the frame's corners ("Marco")
#   sheet.json       the sheet's size, and where his two continent pictures sit on it (they're the game's
#                    continent maps whole, so they place the game's world on the sheet)
# His hatching round the continents ("Capa 120") and the continents themselves aren't used: the middle
# of the chart is the game's own map.
#
# usage: python -P tools/map-chart/export.py <his .psd>   (needs psd-tools)
import json, os, sys
from PIL import Image
from psd_tools import PSDImage

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "art", "drawn", "chart")
CONTINENTS = {"1414 Kalimdor": 1414, "1415 Eastern Kingdoms": 1415}


def find(node, path):
    for name in path:
        node = next(l for l in node if l.name == name)
    return node


def flat(layer, size):
    return layer.composite(viewport=(0, 0, size, size), force=True).convert("RGBA")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python -P tools/map-chart/export.py <his .psd>")
    psd = PSDImage.open(sys.argv[1])
    size = psd.size[0]
    assert psd.size == (size, size), psd.size
    os.makedirs(OUT, exist_ok=True)
    paper = flat(find(psd, ["Lienzo", "Hoja de mapa"]), size)
    paper.alpha_composite(flat(find(psd, ["Lienzo", "Agua", "Capa 24"]), size))
    paper.resize((size // 2, size // 2), Image.LANCZOS).save(os.path.join(OUT, "paper.png"), optimize=True)
    ground = find(psd, ["Fondo"])
    gx0, gy0, gx1, gy1 = ground.bbox
    piece = ground.composite(viewport=ground.bbox, force=True).convert("RGBA")
    cx, cy = (gx1 - gx0) // 2, (gy1 - gy0) // 2
    piece.crop((cx - 512, cy - 512, cx + 512, cy + 512)).save(os.path.join(OUT, "backdrop.png"), optimize=True)
    for name, path in (("lines", ["Lienzo", "Agua", "Lineas Maritimas"]), ("ornaments", ["Lienzo", "Agua", "Capa 119"]),
                       ("frame", ["Lienzo", "Marco"])):
        flat(find(psd, path), size).save(os.path.join(OUT, name + ".png"), optimize=True)
        print("wrote", name)
    boxes = {}
    for layer in psd.descendants():
        if layer.name in CONTINENTS:
            boxes[str(CONTINENTS[layer.name])] = list(layer.bbox)
    assert len(boxes) == 2, boxes
    with open(os.path.join(OUT, "sheet.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"size": size, "continents": boxes}, f, indent=1)
        f.write("\n")
    print("wrote art/drawn/chart:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
