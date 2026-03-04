# Releasing FLAtlas (VSCode Workflow)

This is the recommended lightweight workflow after `v0.6.2.1`.

## Branching Model

- Keep `main` stable and releasable.
- Do new work in short-lived branches:
  - `feature/<topic>`
  - `fix/<topic>`
- Merge back into `main` when tested.

Optional:
- Use `release/<version>` if you want a final pre-release branch (for docs/version cleanup only).

## Versioning

- Version source of truth: `fl_atlas.py` -> `APP_VERSION`
- Tag format: `vX.Y.Z.W` (example: `v0.6.2.2`)
- For hotfixes/small updates: increase last number (`0.6.2.1` -> `0.6.2.2`)

## Day-to-Day Development

1. Update local `main`
2. Create branch from `main`
3. Implement + commit
4. Merge into `main`

PowerShell example:

```powershell
git checkout main
git pull
git checkout -b fix/some-bug
```

## Release Checklist (for `0.6.2.2`)

1. Ensure all intended fixes are merged into `main`.
2. Set `APP_VERSION = "0.6.2.2"` in `fl_atlas.py`.
3. Update `README.md` release/version references if needed.
4. Run quick QA smoke tests.
5. Build artifacts (`scripts/build_windows.bat`, optionally Linux build script).
6. Commit release changes:

```powershell
git add .
git commit -m "release: v0.6.2.2"
```

7. Create annotated tag:

```powershell
git tag -a v0.6.2.2 -m "FLAtlas v0.6.2.2"
```

8. Push branch + tag:

```powershell
git push origin main
git push origin v0.6.2.2
```

9. Create GitHub Release from tag `v0.6.2.2` and upload artifacts.

## VSCode: Tagging UI

1. Source Control (`Ctrl+Shift+G`)
2. `...` menu -> `Tags` -> `Create Tag...`
3. Enter `v0.6.2.2`
4. Select commit (`HEAD`)
5. Push:
   - `...` -> `Push`
   - If needed: `...` -> `Push Tags`

## If a Release Needs a Fix

- Do not move/delete published tags.
- Create a new patch version instead:
  - `v0.6.2.2` -> `v0.6.2.3`

## Useful Checks

```powershell
git tag --list
git show v0.6.2.2
git log --oneline --decorate -n 15
```
