"""OpenMap's icon, from art-icon/openmap.jpg, as the game reads it (128x128, 32-bit, uncompressed TGA):
- OpenMap/Media/Textures/OpenMapIcon.tga: the whole square picture (the AddOns list, the map's menu)
- OpenMap/Media/Textures/OpenMapIconRound.tga: cut to the compass's ring, round, the rest clear
  (the minimap button, the map window's round portrait)
usage: python -P -E tools/icon/build.py   (Pillow needs -E here, not -I)"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "art-icon" / "openmap.jpg"
OUT = ROOT / "OpenMap" / "Media" / "Textures"
SIZE = 128
# the ring's outer edge in the 1024 px picture: centred on the needle's hub, 355 px out (openmap.world crops its round icon the same)
RING_X, RING_Y, RING_R = 512, 514, 355

src = Image.open(SRC).convert("RGB")
src.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA").save(OUT / "OpenMapIcon.tga", compression=None)

ring = src.crop((RING_X - RING_R, RING_Y - RING_R, RING_X + RING_R, RING_Y + RING_R))
ring = ring.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
mask = Image.new("L", (SIZE * 4, SIZE * 4), 0)   # drawn large and shrunk, for a smooth edge
ImageDraw.Draw(mask).ellipse((0, 0, SIZE * 4 - 1, SIZE * 4 - 1), fill=255)
ring.putalpha(mask.resize((SIZE, SIZE), Image.LANCZOS))
ring.save(OUT / "OpenMapIconRound.tga", compression=None)
print("wrote OpenMapIcon.tga, OpenMapIconRound.tga")
