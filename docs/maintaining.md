# Maintaining OpenMap

How the project is run: settings, triage, reviews, releases. For writing code, see
[development.md](development.md); for releases, [releasing.md](releasing.md).

## GitHub settings (once, by an admin)

- **Branch protection** on `main` (Settings → Branches → Add rule): require a pull
  request, require the `test` check to pass, block force pushes and deletion. Admins can
  still push hotfixes; prefer pull requests.
- **Security** (Settings → Code security): turn on private vulnerability reporting,
  Dependabot alerts and security updates, and secret scanning with push protection.
- **Actions** (Settings → Actions → General): workflow permissions "Read repository
  contents"; "Require approval for first-time contributors" for fork pull requests.
- **Secrets**: only `CF_API_KEY` (CurseForge upload). Rotate it if it may have leaked:
  revoke it on CurseForge, make a new one, replace the secret.
- **Labels**: `bug`, `map` (looks wrong), `from-game` (came from the Report button),
  `enhancement`, `question`, `good first issue`, `help wanted`, `wontfix`, `duplicate`.

## Triage (issues)

1. **Map problems** come with a report code (`OM1|...`). Render it:
   `python -P tools/map-preview/report.py <db2> <tex> report.png "OM1|..."`. If the render
   shows the problem, it's reproducible out of game; if not, it's in-game only (load
   order, another addon, textures not restarted). Ask which other map addons they run.
2. **Lua errors**: ask for the full error text (`/console scriptErrors 1`), the OpenMap
   version, and other addons. Most come from another map addon or an outdated Questie.
3. Label it, link duplicates, and close what can't be reproduced after a week without reply.
4. Security reports come privately (SECURITY.md): don't discuss them in public issues.

## Reviewing a pull request

The template's checklist, plus:

- **Correctness**: does it do what it says, and only that? Read the diff, not just the
  description. CI must pass; for visual changes, look at the before / after renders.
- **Security**: no `loadstring` / `RunScript`, no chat or addon messages, no protected
  calls, no writes to Blizzard's frames' layout tables (taint). In tools: nothing that
  executes downloaded content, no new network endpoints without reason. In workflows: no
  `pull_request_target`, no new secrets, actions from trusted publishers.
- **Content**: true to the original game's art style and intent (the classic vanilla look
  first): art from the game files, or an edit in `art/edits/` that only mends what's blurry
  or broken and adds nothing the game's maps don't have; facts from the game's tables or a
  cited source.
  New textures are listed in `NOTICE.md`.
- **Licensing**: the contributor wrote it, or it comes from an MIT-compatible source.
- **Generated files** changed only with their script, in the same pull request.
- **Performance**: nothing new running every frame without need; new layers hidden when
  faded or off the view. Ask for `/openmap status` numbers if it's a heavy change.
- Merge with "Squash and merge" for a tidy history; the squash message says what and why.

## Releases

See [releasing.md](releasing.md). Before each: the in-game check
([testing.md](testing.md)), the changelog's "Unreleased" moved under the version.
Pre-releases (`-beta`) for anything not checked by several people.

## When the game updates

A new Forever build can change the map tables, art file IDs or Blizzard's map code:

1. Check the build number on wago.tools; rerun `tools/map-data/build.py` with it and
   diff `Data/Reveal.lua` and `Data/Places.lua`.
2. If zone art changed, rerun the regeneration chain (development.md) and render.
3. If Blizzard's map code changed, compare against the `classic_era` branch of
   [wow-ui-source](https://github.com/Gethe/wow-ui-source) for the hooks listed under
   "Things that can break" in ARCHITECTURE.md.
4. Bump `## Interface` in the toc if the client's number changed.
