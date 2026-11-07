## What and why

<!-- What does this change, and why? Link the issue it fixes ("Fixes #12"). -->

## How it was checked

- [ ] `python -P tools/offline-test/lint.py` and `python tools/offline-test/run.py plain|combat|secret|pad` pass
- [ ] Visual change: before / after renders from `tools/map-preview/render.py` attached (marked out of game)
- [ ] Checked in game (say what; new textures need a full client restart), or say it isn't yet

## Checklist

- [ ] Generated files changed only through their script, committed with it
- [ ] New textures are listed in their client's `OpenMap/Media/Textures/<client>/NOTICE.md`
- [ ] No art or map content made up: art from the game files or a hand edit, facts from the game's tables or a cited source
- [ ] My own work, or from an MIT-compatible source (named here)
- [ ] User-visible changes noted under "Unreleased" in `CHANGELOG.md` (WoW Forever) and/or `CHANGELOG-retail.md`
- [ ] My line in `OpenMap/Credits.lua`, if I'd like to be named in game
