# Textures another client takes from WoW Forever's, as they are, for what isn't its map: written into
# OpenMap/Media/Textures/<client>/ (OPENMAP_CLIENT, tools/clients.py) from Forever's folder.
#   MapPaper   the blank parchment of the classic Westfall map (tools/map-preview/gapfill.py cuts it):
#              the dungeon map's page (Map/Dungeons.lua) and What's new's (Map/News.lua)
# (tools/map-textures/make.py and tools/map-art/border.py make their own for each client.)
#
# usage: python -P tools/map-textures/shared.py
import os, shutil, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import clients

SHARED = ["MapPaper.tga"]

if clients.NAME == "forever":
    sys.exit("these are WoW Forever's own: set OPENMAP_CLIENT to the client to copy them to")
os.makedirs(clients.TEX, exist_ok=True)
for name in SHARED:
    shutil.copyfile(os.path.join(clients.tex("forever"), name), os.path.join(clients.TEX, name))
    print("copied", name, "to", os.path.relpath(clients.TEX, clients.REPO))
