# Watchly Docker Image (self-hosted Nuvio backend support)

Builds the unmodified upstream
[Watchly](https://github.com/TimilsinaBimal/Watchly) source (pinned via
`WATCHLY_REF`) and adds an entrypoint that rewrites the hard-coded Nuvio
cloud endpoint at container start, driven entirely by environment variables.
Used by the `anyumbrelstore-watchly` Umbrel app.

## Image

`ghcr.io/demianoshb/watchly:<version>` (multi-arch: linux/amd64, linux/arm64)

## How the Nuvio patch works

Upstream Watchly has no configuration for the Nuvio API endpoint; the URL and
publishable key are constants in:

- `app/services/nuvio.py` (backend: history, token refresh, addon install)
- `app/static/js/modules/nuvio.js` (browser sign-in, addon install)

`entrypoint.sh` rewrites both at container start:

- `NUVIO_BASE_URL`: Nuvio backend URL, e.g. `http://umbrel.internal:30123`.
  Unset = official cloud, no patching.
- `NUVIO_PUBLISHABLE_KEY`: Supabase publishable key of the backend. If unset,
  fetched from `${NUVIO_BASE_URL}/.well-known/nuvio` (discovery endpoint of
  the Nuvio self-host stack).

If the discovery request fails or the sed patterns no longer match after an
upstream update, the container exits with an error instead of silently
talking to the Nuvio cloud.

## TMDB API key (required)

Watchly needs a TMDB API key to build profiles, catalogs and manifests. The
key set in the web UI (Settings → TMDB API Key) is stored per user and used
by some code paths - but **not all**: `app/services/context.py`
(`ProfileService()` without arguments), `app/services/language_service.py`
and `app/services/row_generator.py` construct their TMDB client from the
server-wide `TMDB_API_KEY` environment variable only. Without that env var
the token manifest (`/<token>/manifest.json`) fails with a generic 500
(`{"detail":"Something went wrong. Please try again."}`), even with the UI
key set.

For the Umbrel app set the env var in the rendered app compose
(`~/umbrel/app-data/anyumbrelstore-watchly/docker-compose.yml`), service
`server`, section `environment`:

```yaml
      TMDB_API_KEY: "<TMDB API Key v3>"
```

then apply it with `cd ~/umbrel/app-data/anyumbrelstore-watchly &&
sudo docker-compose up -d`. Get a free key at
https://www.themoviedb.org/settings/api (API Key v3).

Note: Umbrel re-renders the app compose file on every app update and drops
the env var again - re-apply it after updates until Watchly supports a
key file or the per-user key everywhere.

## Bumping Watchly

1. Set the new upstream tag in `.github/workflows/watchly-image.yml`
   (`WATCHLY_REF` default, e.g. `1.17.3`) - or trigger the workflow with
   the `watchly_ref` input.
2. After the image build, Renovate picks up the new tag for the Umbrel app
   (`anyumbrelstore-watchly/`).
3. If upstream changed the constant lines, adjust the grep/sed patterns in
   `entrypoint.sh` together with the bump.

Note: the first GHCR push creates the package as private. Make it public once
(Package settings -> Change visibility) so the Umbrel Home can pull it.
