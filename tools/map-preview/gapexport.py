# A gap painting from the painter's Photoshop file (not committed: 100-370 MB each) into
# art/drawn/gaps/<region>.png, which gapfills.py brings into the addon: the composite Photoshop saved in
# the file, as he saw it, except in the regions listed in UNCOVERED, over their fill area.
# The plates came to him as a layered file with the zones' art on top of his paint layers ("Zone art -
# Blizzard (do not edit)", for him to paint round). Where that art faded out over the gap it was the zones'
# blank parchment, and his painting showed through it faintly: across most of G08's fill area (south of
# Hyjal) it's 75-100% opaque over his finished mountains, a washed-out band on the map. The map draws his
# painting there and the zones' own art over it, so in those regions his layers are flattened there without
# that one (psd-tools: within 3 levels of Photoshop's own composite of his files). His other changes stay as
# he left them (the context layer's mask he painted, the guides he hid).
#
# usage: python -P tools/map-preview/gapexport.py <his .psd> [...]   (needs psd-tools; run gapregions.py
#        first: it reads source/<region>_fill.png)
import json, os, sys
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
here = os.path.dirname(os.path.abspath(__file__))
GAPS = os.path.join(here, "..", "..", "art", "drawn", "gaps")
SRC = os.path.join(GAPS, "source")
ZONE_ART = "Zone art - Blizzard (do not edit)"   # the plate's layer, as the plates went to him
UNCOVERED = ("G08",)            # regions flattened without it over their fill area. The others have the same layer
                                #  over his paint there, but mixing the zones' blank parchment with Blizzard's own
                                #  drawing he saw and painted round (G07's Darkshore mountains, G09's and G10's), so
                                #  without it some of his paint he never saw would show: theirs stay as he saved them
MARGIN = 3                      # world units past the fill area also left without it: gapfills.py uses his clear
                                #  pixels up to its SHORE_FADE past it, and his coast's colours there
RAMP = 1                        # world units it comes back over past that


def export(path, man):
    stem = os.path.splitext(os.path.basename(path))[0]
    e = man.get(stem)
    if not e:
        sys.exit("%s: not a region of art/drawn/gaps/regions.json" % stem)
    psd = PSDImage.open(path)
    W, H = psd.size
    assert [W, H] == e["size"], (stem, psd.size, e["size"])
    saved = Image.open(path)
    saved.load()                                   # (Pillow reads the file's own composite)
    mode = "RGBA" if saved.mode in ("RGBA", "LA") else "RGB"
    out = np.asarray(saved.convert(mode)).astype(np.float32)
    zone = [l for l in psd.descendants() if l.name == ZONE_ART and l.is_visible()]
    if zone and stem[:3] in UNCOVERED:
        fill = np.asarray(Image.open(os.path.join(SRC, stem + "_fill.png")).convert("L"))
        assert fill.shape == (H, W), (stem, fill.shape)
        dist = ndimage.distance_transform_edt(fill == 0) / e["pxPerUnit"]
        f = np.clip(1 - (dist - MARGIN) / RAMP, 0, 1)[..., None]

        def flat(keep):
            im = psd.composite(force=True, layer_filter=lambda l: l.is_visible() and keep(l)).convert("RGBA")
            if mode == "RGB":                      # as Photoshop flattens a file kept without transparency
                bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
                bg.alpha_composite(im)
                im = bg
            return np.asarray(im.convert(mode)).astype(np.float32)
        # Photoshop's composite, less what the plate's layer adds to it there (the difference psd-tools makes
        # between his file with it and without), so where it covered nothing his pixels are Photoshop's own
        with_it, without = flat(lambda l: True), flat(lambda l: l.name != ZONE_ART)
        lift = f * (without - with_it)
        out = out + lift
        print("%s: %.1f%% of its fill area uncovered by more than 16 levels" % (
            stem, 100 * (np.abs(lift[..., :3]).max(axis=2)[fill > 128] > 16).mean()), flush=True)
    else:
        print("%s: his file's own composite" % stem, flush=True)
    img = Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8), mode)
    dst = os.path.join(GAPS, stem + ".png")
    if os.path.exists(dst):
        old = Image.open(dst)
        if old.size != img.size:                   # a painting may be kept smaller (G01, at half: fits.json lines it up)
            img = img.resize(old.size, Image.LANCZOS)
        if old.mode == img.mode and np.array_equal(np.asarray(old), np.asarray(img)):
            print("   unchanged", flush=True)
            return
    img.save(dst)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python -P tools/map-preview/gapexport.py <his .psd> [...]")
    man = {r["file"][:-4]: r for r in json.load(open(os.path.join(GAPS, "regions.json"), encoding="utf-8"))}
    for p in sys.argv[1:]:
        export(p, man)


main()
