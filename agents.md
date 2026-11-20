# Agents Guide

This document is written for AI coding agents (and human contributors) working on this repository.

## What this repository is

AnyUmbrelStore is a community app store for umbrelOS. It contains no application source code – every app is a *package*: an `umbrel-app.yml` manifest plus a `docker-compose.yml` that references an upstream container image. The store is consumed directly from the `master` branch by umbrelOS instances, so every merge to `master` is effectively a release.

## Repository layout

```text
<app-id>/                    # one folder per app, folder name == app id
  umbrel-app.yml             # manifest: metadata, port, version, releaseNotes
  docker-compose.yml         # Docker services (Umbrel compose conventions)
  icon.svg                   # app icon (optional)
  data/                      # committed data files mounted into containers, if any
umbrel-app-store.yml          # store definition (id: anyumbrelstore)
scripts/check-apps.py         # local/CI package validation (see Local checks)
scripts/pr-changelog.py       # changelog + README sync, runs in CI on PRs
scripts/pr-report.js          # structured PR comment from the check results
.github/workflows/           # app-store-check, upstream-watch, branch-cleanup
renovate.json                # all automated update rules (see Renovate rules)
```

App IDs and folders always use the prefix `anyumbrelstore-` (e.g. `anyumbrelstore-gluetun`). The official packaging conventions live in [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps) (`.agents/skills/umbrel-package-app`); `scripts/check-apps.py` enforces them as CI checks.

## Local checks

Before opening a pull request, run the same validation CI runs:

```bash
pip install -r .github/requirements-ci.txt          # just PyYAML
git clone --depth 1 https://github.com/getumbrel/umbrel-apps.git /tmp/umbrel-apps
python scripts/check-apps.py --root . --official /tmp/umbrel-apps --repo DemianosHB/AnyUmbrelStore
```

Exit code 0 = pass (warnings allowed), 1 = errors. The `--official` clone enables port-collision checks against the official store; CI also runs the script weekly on `master` and after every push so conflicts are caught even without an open PR.

## Packaging rules the checker enforces

- **manifest**: required fields present, `id` == folder name, `manifestVersion` numeric (e.g. `1`). Keep manifests consistent with existing apps (see `anyumbrelstore-gluetun/umbrel-app.yml` for a full example).
- **version**: semver (optionally a 4th numeric component for upstream four-part versions, e.g. Duplicati `2.4.1.0`), or a `sha256:` digest. Never a bare `latest`. A packaging-only suffix `-pkgN` is allowed and is the way to ship packaging changes (e.g. port moves) without an image change – Umbrel detects updates by version string inequality.
- **Renovate annotation**: to let Renovate manage the manifest version, place a `# renovate: datasource=... depName=...` comment **directly above** `version:` (only whitespace in between – the regex manager in `renovate.json` requires it). The variant that captures `currentValue` updates version tags; the variant with `currentDigest` updates digests.
- **ports**: host ports must be unique within this store and must not collide with the official Umbrel app store. This store allocates from `30122` upwards (30122–30131 currently in use); pick the next free port for a new app. Headless apps (no `app_proxy`) may use port `0`; web UI apps need a positive port.
- **app_proxy**: `APP_HOST` must follow the container-name pattern and `APP_PORT` must match the container port.
- **data**: `storage.dataRoot` must be exactly `data`. Apps should persist to `$APP_DATA_DIR` (the checker warns if no volume uses it).
- **images**: moving tags (`latest`, `main`) must be digest-pinned.
- **icons**: in-repo icons are referenced via `raw.githubusercontent.com` URLs of this repository and must exist.
- **security warnings** (`privileged`, `docker.sock`, host networking, `cap_add`, device mounts) are allowed only with a justification in the manifest description (e.g. the Gluetun VPN client). They do not fail CI, but they must be deliberate.

## CI behavior agents must know

- **App Store Check** (`.github/workflows/app-store-check.yml`) runs on every PR, every push to `master`, weekly, and via `workflow_dispatch`.
- On PRs, CI additionally runs the **changelog sync**: it compares the affected app's `docker-compose.yml` between base SHA and HEAD, fetches upstream release notes between old and new tag, and rewrites `releaseNotes` in `umbrel-app.yml` **and** the version table in `README.md`. After a passing check, CI commits these changes back to the PR branch. **Consequence:** when you bump a tag/digest, you normally do **not** need to hand-write `releaseNotes` or update the README version table – CI does it. Review the generated release notes and especially any breaking-change findings, but don't fight the automation.
- The check detects breaking changes (keywords, `BREAKING CHANGE:`/`feat!:` markers, major jumps, removed env vars/host ports, upstream commits for dev-channel digest updates). Findings appear as PR-comment sections, `::warning::` annotations and the `breaking-change` label. If a breaking change is accepted deliberately, set the label `breaking-ok`. `FAIL_ON_BREAKING=true` (repo variable) makes the check fail on them.
- The check scripts are always loaded from the **base branch** by the workflow, so changes to `scripts/*.py` in a PR are not what validates that same PR.
- Branch Cleanup deletes branches of merged PRs automatically; Renovate branches with open PRs are left alone.
- Pull requests must use the checklist in `.github/PULL_REQUEST_TEMPLATE.md` (check state, release notes, breaking changes, security warnings, README).
- GitHub Actions are pinned to commit SHAs (`@<sha> # vX.Y.Z`); Renovate bundles their updates in one "GitHub Actions updates" PR. Keep new workflow steps SHA-pinned too.

## Renovate rules (do not work against them)

- `umbrel-app.yml` and `docker-compose.yml` of the same app are updated in **one bundled PR** (`{{parentDir}} app updates`).
- **Digest pinning is deliberate per app**: Gluetun (`latest`), gluetun-webui (`main`) and Duplicati are digest-pinned; everything else is deliberately **not**. In `umbrel-app.yml` the Duplicati rule intentionally has no `pinDigests` (the regex manager can't pin there). Don't "fix" these rules – they encode packaging decisions documented in `renovate.json` and the README.
- **Nuvio Backend exception**: the Supabase stack images (Kong, GoTrue, PostgREST, Storage-API, Postgres, Edge-Runtime, imgproxy) are version-locked to the pinned upstream commit of `NuvioMedia/self-host`. They are bumped **manually, together with the commit pin** in the `nuvio-fetch` service – Renovate is disabled for them. Only the one-shot images (`alpine`, `curl`) and the account-dashboard digest stay with Renovate.
- Pure digest updates (e.g. Gluetun `:latest`) are auto-merged once the App Store Check is green.
- Update schedule: Mondays before 5am, Europe/Berlin.

## Workflow for common tasks

### Bump an app version/tag

1. Update the image tag in `docker-compose.yml` and, if the packaging version tracks it, the `version:` in `umbrel-app.yml` (Renovate usually does this for you – manual bumps are for cases Renovate can't handle).
2. Run the local checks above.
3. Open a PR; let CI sync `releaseNotes` and the README, then review them.

### Packaging-only change (e.g. port move, no image change)

Bump the `-pkgN` suffix on the manifest version (see `anyumbrelstore-gluetun/umbrel-app.yml` for the pattern) and document the reason in `releaseNotes`.

### Add a new app

1. Create `anyumbrelstore-<name>/` with `umbrel-app.yml`, `docker-compose.yml`, and ideally an in-repo `icon.svg`.
2. Pick the next free host port (next after 30131); check against the official store clone.
3. Add a Renovate annotation above `version:` so the app stays updated.
4. Add the app to the version table and add a description section in `README.md` (CI syncs the table on tag bumps, but the initial row/description is manual).
5. Run the local checks with `--official`, then open a PR.

## General rules

- Keep changes minimal and focused on one app per PR.
- Follow the existing bilingual style: manifests and config comments in this repo are largely English with some German explanations – keep the surrounding file's language and tone.
- Do not modify files CI owns on PR branches after the check ran (the changelog-sync commit may conflict); rebase instead of amending CI-pushed commits.
- Never add secrets or credentials to manifests or compose files.
- `master` is the published store – only merge with a green App Store Check.
