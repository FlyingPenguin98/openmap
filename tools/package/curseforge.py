# Uploads a client's release zip to CurseForge: the file build.py wrote (dist/OpenMap-<version>-<client>.zip),
# its notes (dist/OpenMap-<version>-<client>-changelog.md) as the file's changelog, tagged only with that
# client's game version, as a beta / alpha file for a -beta / -alpha version. The release workflow runs it
# only when it's started by hand and approved (.github/workflows/release.yml, docs/releasing.md): a
# tag alone never reaches CurseForge.
#
# usage: CF_API_KEY=... python -P tools/package/curseforge.py <version> --client=forever|retail [--dry-run]
#   --dry-run: find the game version and check the files, upload nothing
# The game version is the one CurseForge names after the client's toc (## Interface: 120105 -> 12.1.5;
# 16001 -> 1.60.1); CF_GAME_VERSIONS=<id>[,<id>] takes CurseForge's ids instead, if it names it otherwise.
import json, os, re, sys, urllib.request, uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import clients

API = "https://wow.curseforge.com/api"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
client = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--client=")), "").lower()
if len(args) != 1 or client not in clients.CLIENTS:
    sys.exit("usage: python -P tools/package/curseforge.py <version> --client=%s [--dry-run]" % "|".join(clients.CLIENTS))
version = args[0]
dry = "--dry-run" in sys.argv
token = os.environ.get("CF_API_KEY", "")
if not token:
    sys.exit("CF_API_KEY isn't set")

toc = open(clients.toc(client), encoding="utf-8").read()
project = re.search(r"^## X-Curse-Project-ID:\s*(\d+)", toc, re.M)
interface = re.search(r"^## Interface:\s*(\d+)", toc, re.M)
if not project or not interface:
    sys.exit("%s has no X-Curse-Project-ID or Interface" % clients.CLIENTS[client]["toc"])
n = int(interface.group(1))
game_version = "%d.%d.%d" % (n // 10000, n // 100 % 100, n % 100)

zip_path = os.path.join(ROOT, "dist", "OpenMap-%s-%s.zip" % (version, client))
notes_path = os.path.join(ROOT, "dist", "OpenMap-%s-%s-changelog.md" % (version, client))
for p in (zip_path, notes_path):
    if not os.path.exists(p):
        sys.exit("%s isn't there: run tools/package/build.py %s --client=%s first" % (os.path.relpath(p, ROOT), version, client))


def request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=dict({"X-Api-Token": token}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8") or "null")


ids = [int(i) for i in os.environ.get("CF_GAME_VERSIONS", "").replace(" ", "").split(",") if i]
if not ids:
    found = [v for v in request(API + "/game/versions") if v.get("name") == game_version]
    if len(found) != 1:
        sys.exit("CurseForge has %d game versions named %s (the toc's Interface %d): set CF_GAME_VERSIONS to its id"
                 % (len(found), game_version, n))
    ids = [found[0]["id"]]

release = "alpha" if "-alpha" in version else "beta" if "-beta" in version else "release"
meta = {
    "changelog": open(notes_path, encoding="utf-8").read(),
    "changelogType": "markdown",
    "displayName": "OpenMap %s (%s)" % (version, "WoW Forever" if client == "forever" else client.capitalize()),
    "gameVersions": ids,
    "releaseType": release,
}
print("%s: project %s, game version %s %s, %s, %s" % (client, project.group(1), game_version, ids, release,
                                                     os.path.relpath(zip_path, ROOT)))
if dry:
    print("dry run: nothing uploaded")
    sys.exit(0)

boundary = uuid.uuid4().hex
body = b"".join([
    b"--%s\r\nContent-Disposition: form-data; name=\"metadata\"\r\n\r\n" % boundary.encode(),
    json.dumps(meta).encode("utf-8"),
    b"\r\n--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\nContent-Type: application/zip\r\n\r\n"
    % (boundary.encode(), os.path.basename(zip_path).encode()),
    open(zip_path, "rb").read(),
    b"\r\n--%s--\r\n" % boundary.encode(),
])
out = request("%s/projects/%s/upload-file" % (API, project.group(1)), body,
              {"Content-Type": "multipart/form-data; boundary=" + boundary})
print("uploaded: file id %s" % (out or {}).get("id"))
