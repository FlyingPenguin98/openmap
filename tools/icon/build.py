"""OpenMap's icon (drawn by zloyeb), from art/icon/openmap.png, as the game reads it (128x128, 32-bit, uncompressed TGA):
- OpenMap/Media/Textures/OpenMapIcon.tga: the whole picture, its clear background kept (the AddOns list, the map's menu)
- OpenMap/Media/Textures/OpenMapIconRound.tga: cut to the gold ring, round, the rest clear
  (the minimap button, the map window's round portrait)
usage: python -P -E tools/icon/build.py   (Pillow needs -E here, not -I)"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "art" / "icon" / "openmap.png"
OUT = ROOT / "OpenMap" / "Media" / "Textures"
SIZE = 128
# the gold ring's outer edge in the 509 px picture (the scroll's rolled ends reach past it and are cut off)
RING_X, RING_Y, RING_R = 254, 254, 224

src = Image.open(SRC).convert("RGBA")
src.resize((SIZE, SIZE), Image.LANCZOS).save(OUT / "OpenMapIcon.tga", compression=None)

ring = src.crop((RING_X - RING_R, RING_Y - RING_R, RING_X + RING_R, RING_Y + RING_R))
ring = ring.resize((SIZE, SIZE), Image.LANCZOS)
mask = Image.new("L", (SIZE * 4, SIZE * 4), 0)   # drawn large and shrunk, for a smooth edge
ImageDraw.Draw(mask).ellipse((0, 0, SIZE * 4 - 1, SIZE * 4 - 1), fill=255)
ring.putalpha(ImageChops.darker(ring.getchannel("A"), mask.resize((SIZE, SIZE), Image.LANCZOS)))
ring.save(OUT / "OpenMapIconRound.tga", compression=None)
print("wrote OpenMapIcon.tga, OpenMapIconRound.tga")
