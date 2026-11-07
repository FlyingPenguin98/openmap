# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for a security problem. Report it privately through
GitHub: the repository's **Security** tab → **Report a vulnerability**. You'll get a reply
within a week; we'll agree a fix and a disclosure date with you.

## What's in scope

- **The addon** (`OpenMap/`): anything that could run code it shouldn't, taint the game's
  protected UI (blocking actions in combat), corrupt or leak a player's saved data, or let
  another player affect someone's client.
- **The release pipeline** (`.github/workflows`, `tools/package`): anything that could expose
  the release credentials or let someone publish a build.
- **The tools** (`tools/`): anything that could make a developer's machine run code from
  a downloaded file or a report code.

Not in scope: bugs in World of Warcraft itself, in other addons, or in wago.tools.

## How the project keeps it safe

- The addon has no network access (the game doesn't allow it), loads no code at run time
  (no `loadstring` / `RunScript`), sends addon messages only for what the player asks
  (sharing map pins, and their place with their guild and friends when they turn that
  on; what arrives is read as plain numbers and text), and calls no protected functions. It hooks Blizzard's map with `hooksecurefunc` and data providers.
- Report codes (`OM1|...`) are parsed as plain numbers and text by `report.py`; nothing
  in them is executed.
- The tools treat everything they download as data: tables are read as CSV, textures are
  decoded with Pillow, nothing downloaded is executed. Run them with `python -P`, keep the
  caches outside the repo, and ideally in a virtual environment.
- CI runs with read-only permissions; the release workflow, which holds the CurseForge
  key, runs only on version tags pushed by maintainers. Workflows never run untrusted code
  with secrets (no `pull_request_target`).
- Dependabot keeps the workflow actions up to date. Bundled libraries (`OpenMap/Libs`) are
  upstream copies with their licences in `OpenMap/LICENSES`; update them from upstream only.
