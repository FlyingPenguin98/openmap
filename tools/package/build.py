# Builds a client's release zip, as the release workflow does on a tag (.github/workflows/release.yml):
# one OpenMap/ folder, only the files git tracks under OpenMap/ as committed, the version in the toc
# (@project-version@). Each client gets a zip of its own (tools/clients.py): its toc, its data and
# textures (Data/<folder>, Media/Textures/<folder>) and the shared files, not another client's. Runs
# lint and the offline tests (for that client) first. Writes dist/OpenMap-<version>-<client>.zip and,
# for the upload's changelog, dist/OpenMap-<version>-<client>-changelog.md (that version's section of
# the client's changelog: CHANGELOG.md, CHANGELOG-retail.md). The release workflow runs it for every
# client (.github/workflows/release.yml), and curseforge.py uploads what it writes (docs/releasing.md).
#
# usage: python -P tools/package/build.py <version> [--client=forever|retail] [--dirty] [--no-tests]
#   <version>: as the changelogs head it, e.g. v0.5.0-beta
#   --client: which client's zip (forever if not given)
#   --dirty: allow uncommitted changes under OpenMap/ (the zip still takes the committed files)
import os, re, subprocess, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(ROOT, "dist")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import clients
client = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--client=")), "forever").lower()
if client not in clients.CLIENTS:
    sys.exit("--client: one of " + ", ".join(sorted(clients.CLIENTS)))
CLIENT = clients.CLIENTS[client]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 1:
    sys.exit(__doc__ or "usage: python -P tools/package/build.py <version> [--dirty] [--no-tests]")
version = args[0]
if not re.match(r"^v\d+\.\d+\.\d+(-[a-z0-9.]+)?$", version):
    sys.exit("version should look like v0.5.0 or v0.5.0-beta")


def git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), check=True, capture_output=True).stdout


# the changelog: this version's own section, with its notes
LOG = CLIENT["changelog"]
md = open(os.path.join(ROOT, LOG), encoding="utf-8").read()
m = re.search(r"^## %s\b.*?$(.*?)(?=^## |\Z)" % re.escape(version), md, re.M | re.S)
if not m or not m.group(1).strip():
    sys.exit("%s has no notes under '## %s': move Unreleased under it first (docs/releasing.md)" % (LOG, version))
notes = m.group(1).strip() + "\n"

dirty = git("status", "--porcelain", "--", "OpenMap", LOG).decode().strip()
if dirty and "--dirty" not in sys.argv:
    sys.exit("uncommitted changes (commit them, or --dirty to package what's committed):\n" + dirty)

if "--no-tests" not in sys.argv:
    checks = [["-P", "tools/offline-test/lint.py"]] + [["tools/offline-test/run.py", m_] for m_ in ("plain", "combat", "secret", "pad", "padmap")]
    for c in checks:
        r = subprocess.run([sys.executable] + c, cwd=ROOT, capture_output=True, text=True,
                           env=dict(os.environ, OPENMAP_CLIENT=client))
        if r.returncode != 0:
            sys.exit("failed: %s\n%s%s" % (" ".join(c), r.stdout[-3000:], r.stderr[-3000:]))
        print("ok:", " ".join(c))

# the committed files (as the packager's git checkout has them), not the working tree's
files = git("ls-tree", "-r", "-z", "--name-only", "HEAD", "--", "OpenMap").decode().split("\0")
# not the other clients' tocs, data or textures
others = [c for n, c in clients.CLIENTS.items() if n != client]
skip = ["OpenMap/" + c["toc"] for c in others]
skip_dirs = [d % c["folder"] for c in others for d in ("OpenMap/Data/%s/", "OpenMap/Media/Textures/%s/")]
files = sorted(f for f in files if f and f not in skip and not any(f.startswith(d) for d in skip_dirs))
TOC = "OpenMap/" + CLIENT["toc"]
os.makedirs(DIST, exist_ok=True)
out = os.path.join(DIST, "OpenMap-%s-%s.zip" % (version, client))
toc_seen = False
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in files:
        data = git("show", "HEAD:" + f)
        if f == TOC:
            assert b"@project-version@" in data, "the toc has no @project-version@"
            data = data.replace(b"@project-version@", version.encode())
            toc_seen = True
        info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data)
if not toc_seen:
    sys.exit(TOC + " isn't committed")
NOTES = os.path.join(DIST, "OpenMap-%s-%s-changelog.md" % (version, client))
with open(NOTES, "w", encoding="utf-8", newline="\n") as f:
    f.write(notes)
head = git("rev-parse", "--short", "HEAD").decode().strip()
print("wrote %s (%d files, %.1f MB, from %s)" % (os.path.relpath(out, ROOT), len(files), os.path.getsize(out) / 1e6, head))
print("changelog: %s" % os.path.relpath(NOTES, ROOT))
