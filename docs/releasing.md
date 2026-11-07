# Releasing

One version tag releases every game client: `.github/workflows/release.yml` builds a zip per client
(`tools/package/build.py`: WoW Forever's and retail's, each with only its own toc, data and
textures, the version in its toc), runs each client's lint and offline tests on the way, and makes
the GitHub release with both zips and both clients' notes.

**CurseForge is a separate, approved step.** A tag never uploads anything to CurseForge by itself.
The upload runs only when the release workflow is started by hand with the tag, and only after the
maintainer approves it in the `curseforge` environment. Each zip becomes its own CurseForge file,
tagged only with its own client's game version, with its own client's notes.

## Once

1. **API token**: CurseForge → My API Tokens → generate one, then on GitHub: the repo's
   Settings → Secrets and variables → Actions → New secret `CF_API_KEY`.
2. **The approval**: the repo's Settings → Environments → New environment `curseforge` →
   Required reviewers: the maintainer. (Do this before the first upload: without it, GitHub makes
   the environment the first time the job runs, with no approval step.)
3. **Game versions**: `tools/package/curseforge.py` tags each file with the CurseForge game version
   named after its toc's `## Interface` (120105 → 12.1.5, 16001 → 1.60.1). If CurseForge names one
   differently, its dry run fails saying so. Then add a repository variable and pass it as
   `CF_GAME_VERSIONS` (CurseForge's ids, comma-separated) for that client's step in `release.yml`.

## Each release

1. Run the in-game check for each client: [testing.md](testing.md).
2. Move the "Unreleased" notes in each client's changelog under the new version: `CHANGELOG.md`
   (WoW Forever) and `CHANGELOG-retail.md` (retail), both headed with the same version (a client
   with nothing new says so in a line). Write them as what the release does (not each step of
   getting there), grouped under `### New`, `### Improved` and `### Fixed`, the most important first
   (a change's lead-in in `**bold**`). Then run `python -P tools/changelog/build.py`: each client's
   in-game "What's new" (`Data/<client>/Changelog.lua`) is made from its changelog, and lint fails
   while they disagree.
3. Tag and push: `git tag v0.8.0-beta` then `git push origin v0.8.0-beta`. The GitHub release
   appears with `OpenMap-v0.8.0-beta-forever.zip` and `OpenMap-v0.8.0-beta-retail.zip`.
4. **To CurseForge, once approved**: Actions → release → Run workflow, with the tag. Its
   `curseforge` job waits for the maintainer's approval, does a dry run for both clients (the game
   versions found, the files there), then uploads both.

Tags with `-beta` or `-alpha` in them are uploaded to CurseForge as beta / alpha files.

## By hand

    python -P tools/package/build.py v0.8.0-beta --client=forever
    python -P tools/package/build.py v0.8.0-beta --client=retail

Each runs lint and the offline tests with that client's toc, then writes
`dist/OpenMap-v0.8.0-beta-<client>.zip` (the `OpenMap/` folder as committed, with only that
client's toc, data and textures) and `dist/OpenMap-v0.8.0-beta-<client>-changelog.md` (that
version's notes from the client's changelog).
`CF_API_KEY=... python -P tools/package/curseforge.py v0.8.0-beta --client=forever --dry-run` checks
what an upload would do; without `--dry-run` it uploads. Only with the maintainer's go-ahead.
