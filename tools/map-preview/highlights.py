# Copies the zones' highlights recorded in game (/openmap highlights: Map/Debug.lua) out of the game's
# saved settings into tools/map-preview/highlights/<client>.txt, where territory.py reads them: one line
# a highlight, "continent zone fileID atlas texPercentX texPercentY width height left top" (the last four
# normalized on the continent's map), as C_Map.GetMapHighlightInfoAtPosition gives them.
#
# usage: python -P tools/map-preview/highlights.py <WTF/Account/<account>/SavedVariables/OpenMap.lua>
#   (OPENMAP_CLIENT: the client, tools/clients.py; log out or /reload after recording, so it's written)
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients

src = open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r'\["highlights"\]\s*=\s*\{(.*?)\n\s*\}', src, re.S)
if not m: sys.exit("no highlights in %s: record them in game first (/openmap highlights), then /reload" % sys.argv[1])
lines = re.findall(r'"([-\d. e]+(?: [-\w.]+)+)"', m.group(1))
lines = [l for l in lines if len(l.split()) == 10]
if not lines: sys.exit("the highlights recorded are empty")
out = os.path.join(HERE, "highlights", clients.NAME + ".txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# The zones' highlights on their continents' maps, recorded in game (/openmap highlights) by\n")
    fh.write("# tools/map-preview/highlights.py: continent zone fileID atlas texPercentX texPercentY width height left top\n")
    for l in sorted(set(lines)): fh.write(l + "\n")
print("wrote %s: %d highlights" % (os.path.relpath(out, clients.REPO), len(set(lines))))
