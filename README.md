# AnyUmbrelStore

A [community app store](https://github.com/getumbrel/umbrel-community-app-store) for [umbrelOS](https://umbrel.com) with curated self-hosted apps that are (not yet) available in the official store.

[![App Store Check](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/app-store-check.yml/badge.svg)](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/app-store-check.yml)
[![Upstream Changelog Watch](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/upstream-watch.yml/badge.svg)](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/upstream-watch.yml)
[![Watchly Docker Image](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/watchly-image.yml/badge.svg)](https://github.com/DemianosHB/AnyUmbrelStore/actions/workflows/watchly-image.yml)

## Add the store

1. On your Umbrel, open the **App Store** page.
2. At the bottom, choose **Add external app store** and enter this URL:

   ```
   https://github.com/DemianosHB/AnyUmbrelStore
   ```

3. The apps from this store then appear in the App Store.

## Available apps

| App | ID | Version | Category | Port |
|---|---|---|---|---|
| [Gluetun VPN](https://github.com/passteque/gluetun) | `anyumbrelstore-gluetun` | latest (Dev) | Networking | 30126 |
| [Profilarr](https://github.com/Dictionarry-Hub/profilarr) | `anyumbrelstore-profilearr` | 2.3.1 | Media | 6868 |
| [Paperless Backup](https://github.com/DemianosHB/AnyUmbrelStore/tree/master/anyumbrelstore-paperless-backup) | `anyumbrelstore-paperless-backup` | 2.4.1.0 | Files | 39120 |
| [AIOStreams](https://github.com/Viren070/AIOStreams) | `anyumbrelstore-aiostreams` | 2.37.0 | Media | 30124 |
| [Nuvio Backend](https://github.com/NuvioMedia/self-host) | `anyumbrelstore-nuvio-backend` | 0.1.5 | Media | 30122 |
| [InfiniDysk](https://github.com/infinidysk/infinidysk) | `anyumbrelstore-infinidysk` | 1.7.1-lang5 | Media | 30125 |
| [Watchly](https://github.com/TimilsinaBimal/Watchly) | `anyumbrelstore-watchly` | 1.17.2 | Media | 30127 |
| [StremThru](https://github.com/MunifTanjim/stremthru) | `anyumbrelstore-stremthru` | 0.105.4 | Media | 30128 |
| [AIOMetadata](https://github.com/cedya77/aiometadata) | `anyumbrelstore-aiometadata` | 3.8.3 | Media | 30129 |
| [OpenPosterDB](https://github.com/PNRxA/openposterdb) | `anyumbrelstore-openposterdb` | 1.3.0 | Media | 30130 |
| [XRDB](https://github.com/IbbyLabs/XRDB) | `anyumbrelstore-xrdb` | 3.144.0 | Media | 30131 |

### Gluetun VPN

Lightweight VPN client container (WireGuard & OpenVPN, many providers). The web UI (umbrel.local:30126) shows connection status, public IP and server info and allows start/stop from the browser (API key: see app credentials). For other apps that should route through the tunnel, it additionally exposes:

- HTTP proxy: port **8009**
- SOCKS5 proxy: port **1080**
- Shadowsocks: port **8388**

On install, VPN provider, VPN type and WireGuard private key must be provided (`VPN_SERVICE_PROVIDER`, `VPN_TYPE`, `WIREGUARD_PRIVATE_KEY`, `SERVER_COUNTRIES`).

Gluetun follows the **dev channel** (`latest`, digest-pinned) because the built-in SOCKS5 proxy server is so far only included there and in no stable release. Renovate updates the digest automatically. The web UI runs on port 30126 (packaging change: the original port 8010 collides with the Ryot package from another community store); HTTP proxy (8009), SOCKS5 (1080) and Shadowsocks (8388) remain unchanged – AIOStreams and InfiniDysk reach Gluetun via the container name.

### Profilarr

Create, test and sync quality profiles and custom formats for Radarr and Sonarr – including an integrated parser for testing profiles.

### Paperless Backup

Offsite backup for the official Paperless-ngx app – **one app, two containers**:

- **dbdump** (`postgres:18`): creates a `pg_dump | gzip` dump of the Paperless PostgreSQL database daily at 01:30 (Europe/Berlin) into the app data (`db-export`, 7 daily versions, written atomically). The pg_dump client may be newer than the database server, never older – Renovate can therefore safely bump the tag.
- **duplicati** (official `duplicati/duplicati` image, digest-pinned like the official Umbrel app): backs up the documents (`/mnt/source/media`) and the DB dumps (`/mnt/source/db-export`) via SFTP (port 22, password authentication – deliberately no SSH keys), e.g. to a Hetzner Storage Box. Backup job, schedule (right after the DB dump, e.g. 02:30), AES-256 encryption and retention are set up in the usual Duplicati web UI.

The official Paperless app is neither forked nor modified – `media` is only mounted read-only into the backup app. The Duplicati container runs as root (image default) because Docker creates missing bind-mount folders and the dbdump container creates the app data root-owned; the backup sources remain mounted read-only. Restore: documents via the Duplicati web UI, DB dump via `gunzip -c paperless-YYYY-MM-DD.sql.gz | docker exec -i paperless_db_1 psql -U paperless paperless`, then rebuild the search index in Paperless.

### AIOStreams

Stremio **super-addon**: bundles several Stremio addons and debrid/usenet services (e.g. Torrentio, Comet, MediaFusion) into a single, highly customizable addon. Results from all sources are filtered, sorted, deduplicated and merged into a clean stream list – including an addon marketplace (80+ addons), a native usenet streaming engine and a Jellyfin-compatible UI for direct viewing without Stremio.

Getting started: open the web UI, log into the dashboard (user `admin`, password: see app credentials), set up addons and debrid services and add the generated addon to Stremio via the install button. Debrid and usenet services are configured as **Services** (Config → Services); since v2.37 the standalone TorBox addons are removed – the TorBox API key (torbox.app → Settings) belongs under Config → Services → TorBox. `BASE_URL` defaults to the Umbrel launch URL; for clients without mDNS (e.g. some Android TV apps), switch to the IP URL in the app settings. The addon is deliberately reachable in the local network without Umbrel login (Stremio and Jellyfin clients send no Umbrel cookies and reach the addon via dynamic config-ID paths); the dashboard itself is protected by the operator login. Run only in the local network. Renovate updates the manifest version and image together.

### Nuvio Backend

Self-hosted Nuvio backend for your own Nuvio clients – the API stack from [NuvioMedia/self-host](https://github.com/NuvioMedia/self-host) (PostgreSQL, GoTrue auth, PostgREST, storage, edge functions, Kong gateway) including the account dashboard. After installation, first create an account in the account dashboard (port **30122**); Nuvio clients connect to the backend URL (port **30123**).

Upstream is cloned into the app data at a pinned commit revision (`nuvio-fetch` one-shot service), secrets are generated automatically on first start, and DB migrations run idempotently via `nuvio-migrate`. The manifest version (0.1.x) is the store's own packaging version – upstream publishes no releases. The Supabase stack images deliberately move only together with the pinned upstream commit (see Maintenance).

### InfiniDysk

Usenet streaming via a virtual WebDAV drive: InfiniDysk (NzbDAV SuperFork) unpacks NZB files on the fly and serves them as files over WebDAV – including a SABnzbd-compatible API, without downloads having to complete fully. After first start (create an admin account in the web UI), configure Newznab indexers and NNTP servers.

Connect to AIOStreams in one of two ways: as an **NzbDAV service** (playback only – AIOStreams proxies the streams but needs its own Newznab addons for search) or as a **custom addon** via the addon adapters of InfiniDysk's search profiles (manifest URL `/adapters/addon/<token>/manifest.json`, change the host part in AIOStreams to `anyumbrelstore-infinidysk_server_1:3000`) – then InfiniDysk provides the Newznab search itself and AIOStreams only handles playback; do not combine both. Indexer requests (Newznab search, NZB grabs) can be routed through an HTTP(S) or SOCKS5 proxy via Settings → Indexers (global or per indexer, e.g. through the Gluetun container). Since v1.7.1-lang4, all outbound connections including NNTP can be tunneled through a global SOCKS5 proxy via Settings → General → "Outbound proxy" (`general.socks5-proxy`, e.g. `socks5://gluetun:1080`, including a "Test proxy" button) (DNS remote, TLS end-to-end, loopback/Docker names stay direct). Since v1.7.1-lang5, configurable exceptions for this global proxy are available via `general.socks5-proxy-bypass` (host names, domain suffixes like `.lan`/`*.lan`, IPs, CIDR ranges or `*`; also configurable via the `NZBDAV_CONFIG__GENERAL__SOCKS5_PROXY_BYPASS` env variable). Set preferred audio languages per search profile under Settings → Profiles ("Preferred audio languages", ordered list e.g. `de, en`) – they influence result sorting and the watchdog fallback order (bias, not a filter). The app is reachable in the local network without Umbrel login (WebDAV and SABnzbd clients send no Umbrel cookies) but is protected by its own login. Renovate updates the manifest version and image tag together.

### Watchly

Personalized recommendations from your Nuvio history: Watchly reads the watch history directly from the self-hosted Nuvio backend and builds recommendation rows ("Top Picks for You", "Because you watched …", genre and keyword catalogs) that appear as a catalog addon on the Nuvio home screen – without detours via Trakt, Simkl or the Nuvio cloud.

The image is built by the store itself (see Maintenance) and pointed at your own Nuvio backend by a startup script; the publishable key is fetched automatically at container start via the discovery endpoint. **Important:** Watchly requires a TMDB API key as a `TMDB_API_KEY` env variable in the `server` service – several Watchly code paths ignore the key stored in the web UI; without the env variable the manifest fails with error 500 (details: [`docker/watchly/README.md`](docker/watchly/README.md)).

### StremThru

Self-hosted companion for Stremio and Nuvio: StremThru sits in front of debrid services (incl. TorBox) and provides its own Stremio addons – including **Torz** (torrent and debrid search; uncached hits trigger a download at the store and become playable after a short wait), **Store** (catalog of your own debrid account), **Wrap** and **Sidekick** – plus a stream proxy with byte-serving. In the Nuvio stack it closes the gap that Nuvio cannot play uncached Torrentio/Comet hits because Nuvio has no torrent engine: StremThru takes over the download trigger at TorBox.

Dashboard login: `admin` plus app password (app credentials). Store tokens (e.g. the TorBox API key) are stored in the dashboard vault and persisted (vault secret from `APP_SEED`). Connect to AIOStreams via the marketplace addon "StremThru Torz" (StremThru URL `http://umbrel.internal:30128`, credentials `admin` + app password). The TorBox API runs without tunnel directly from the home IP (`STREMTHRU_STORE_TUNNEL=*:false`); optionally routable to the Gluetun container via `STREMTHRU_HTTP_PROXY`.

### AIOMetadata

Poster and metadata service for Stremio and Nuvio: AIOMetadata delivers posters, logos, backgrounds, descriptions, ratings and episode lists from TMDB, TVDB, IMDb, Fanart.tv, TVmaze and more – with language-aware artwork selection (German posters with fallback) and optional ratings directly on the posters (RatingPosterDB). A catalog builder adds own rows (TMDB trending, genres, streaming providers, MDBList), and the collection builder can even export collections to Nuvio. In the Nuvio stack it complements Watchly as the poster/metadata layer next to the per-profile recommendation catalogs.

First steps: set the TMDB API key in the app settings (`BUILT_IN_TMDB_API_KEY`, free at themoviedb.org; the optional TVDB, Fanart.tv, RPDB and MDBList keys belong there as well), then open the web UI behind the Umbrel login and configure everything under `/configure`: pick catalogs, providers and artwork, set the language to German, save – note the UUID and password shown, both are needed to edit the configuration later. The install step generates the manifest URL that goes into Nuvio per profile under Settings → Addons; each Nuvio profile can use its own configuration.

The configuration UI is protected by the Umbrel login; only the addon paths Nuvio needs (`/stremio/*`, the signed artwork proxies `/poster`, `/logo`, `/background`, `/landscape` and `/poster-cache/*`) are reachable without Umbrel cookies – protected by the UUID/config token in the path and the HMAC signature. Cache warming is deliberately disabled in the package (RAM budget), Redis runs with a small memory cap as a cache only. Renovate updates the manifest version and image tag together.

### OpenPosterDB

Self-hosted Rating-Poster-Service als Drop-in-Alternative zu RatingPosterDB: OpenPosterDB generiert Poster, Logos, Backdrops und Episode-Stills mit Rating-Badges direkt auf dem Artwork - Bewertungen aus IMDb, Rotten Tomatoes (Critics und Audience), Metacritic, Trakt, Letterboxd, MyAnimeList, Roger Ebert und dem MDBList-Score, Artwork von TMDB (optional Fanart.tv, Sprachwahl inklusive). Im Nuvio-Stack ersetzt OPDB RPDB als Poster-Rating-Layer: AIOMetadata übernimmt die OPDB-URL-Templates (Artwork-/URL-Pattern), Watchly den Custom-Template für Poster-Ratings.

Erste Schritte: TMDB- und MDBList-Key in den App-Einstellungen hinterlegen (beide kostenlos), dann die Weboberfläche (umbrel.internal:30130) mit admin plus App-Passwort öffnen, einen API-Key anlegen und die Poster-Einstellungen setzen (Ratings, Badge-Stil, Sprache de). Danach in AIOMetadata/Watchly die URL-Templates eintragen - Basis-URL http://umbrel.internal:30130, Pfade siehe Upstream-Doku "Connecting a Media Server".

Die App läuft ohne Umbrel-Login-Gate, weil die Bild-Pfade mit dem zufälligen API-Key als erstem Pfad-Segment beginnen und die Umbrel-Whitelist nur Prefix-Regeln kennt - geschützt wird durch die eigene Auth (Admin-Login mit JWT/Argon2, Poster-Endpoints nur mit gültigem API-Key, dasselbe Schutzmodell wie RPDB). Der Bild-Cache ist vom Backup ausgenommen (regenerierbar), die SQLite-Datenbank (API-Keys, Einstellungen) wird gesichert. Renovate updates the manifest version and image tag together.

### XRDB

Self-hosted Artwork-Engine als Drop-in-Alternative zu RatingPosterDB: XRDB generiert Poster, Backdrops, Thumbnails und Logos mit Rating-Badges direkt auf dem Artwork - Bewertungen aus 13 Quellen (IMDb, TMDB, Rotten Tomatoes, Metacritic, Letterboxd, Trakt, SIMKL, MyAnimeList, AniList, Kitsu u. a.). Gegenüber RPDB/OPDB sind die Artwork-Quellen frei wählbar und in ihrer Reihenfolge konfigurierbar, z. B. Fanart.tv als Primärquelle mit TMDB als Fallback. Profile mit eigenem Alias, Stremio-Addon und eine RPDB-Kompatibilitätsroute sind eingebaut.

Erste Schritte: Weboberfläche hinter dem Umbrel-Login (umbrel.internal:30131) öffnen, Fanart.tv-API-Key (kostenlos) hinterlegen und Profile anlegen (Provider-Reihenfolge, Ratings, Badge-Stil, Sprache de). Der Admin-Key entspricht dem App-Passwort; XRDB_AIOM_ALLOW_PRIVATE=true erlaubt den Ein-Klick-Install der Profile in AIOMetadata. Danach AIOMetadata (Art Providers → URL Patterns) und Watchly (Custom-Template) auf die XRDB-URLs umstellen - Basis-URL http://umbrel.internal:30131. XRDB hat keine eigene Landscape-Fläche: Landschaften laufen über das Backdrop-Pattern; ohne IMDb-ID liefert Watchly kein Custom-Poster.

Die App läuft hinter dem Umbrel-Login-Gate; ohne Umbrel-Cookies freigegeben sind nur die Bild- und Addon-Pfade (/poster, /backdrop, /thumbnail, /logo, /stremio, /healthz, /readyz) - die RPDB-Kompatibilitätsroute mit dem Key als erstem Pfad-Segment ist wie bei OpenPosterDB nicht freigebbar (Whitelist kennt nur Prefix-Regeln). Der Image-Cache (Bind-Mount data/xrdb, cache-Unterordner regenerierbar) ist vom Backup ausgenommen, mem_limit 768m mit internem Memory-Limit (XRDB_MEMORY_LIMIT_MB 512). Das Image ist auf Version und Digest gepinnt (Multi-Arch); Renovate updates the manifest version and image tag together.

## Structure

Each app lives in its own folder, named after its app ID (prefix `anyumbrelstore-`):

```text
<app-id>/
  umbrel-app.yml      # manifest (metadata, port, version)
  docker-compose.yml  # Docker services
  icon.svg            # app icon (optional, community stores)
```

The store definition is in [`umbrel-app-store.yml`](umbrel-app-store.yml).

## Maintenance

- Container images are kept up to date automatically by [Renovate](https://renovatebot.com) (`renovate.json`). Updates are batched at fixed times (Mondays before 5am, Europe/Berlin) and only opened once CI is green; pure digest updates (e.g. Gluetun `:latest`) are auto-merged by Renovate as soon as the App Store Check passes.
- The GitHub Actions in the workflows are pinned to commit SHAs for supply-chain security (`@<sha> # vX.Y.Z`); Renovate updates them bundled in a single "GitHub Actions updates" PR.
- **Exception – Nuvio Backend:** the Supabase stack images (Kong, GoTrue, PostgREST, Storage-API, Postgres, Edge-Runtime, imgproxy) are tied to the pinned upstream commit and are bumped manually together with the pin; Renovate deliberately does not update them (package rule in `renovate.json`). The one-shot images (`alpine`, `curl`) and the account dashboard digest stay with Renovate.
- **Watchly (own image):** the image `ghcr.io/demianoshb/watchly` is built by the [Watchly Docker Image](.github/workflows/watchly-image.yml) workflow itself (multi-arch, amd64+arm64, with provenance + SBOM attestations) from the pinned upstream tag (`WATCHLY_REF`); at container start the entry script patches the hard-coded Nuvio cloud URL to your own backend (details: [`docker/watchly/README.md`](docker/watchly/README.md)). Upstream bumps stay manual: Renovate proposes new Watchly releases automatically as a PR (`WATCHLY_REF` in workflow and Dockerfile bundled, no automerge) → merge the PR → wait for the image build → Renovate pulls the app up; check whether the entry script's sed/grep patterns still match the new upstream. The TMDB API key must be set as a `TMDB_API_KEY` env variable in the `server` service (Umbrel re-renders the app compose on updates, see Watchly README).
- Every pull request is checked automatically by the [App Store Check](.github/workflows/app-store-check.yml) action (additionally weekly on Mondays at 05:00 UTC and after every merge to `master`, so port collisions with the official store are noticed even without an open PR): manifest schema, versions (no bare `latest`), digest pinning of moving tags, port conflicts within this store and against the official store, `app_proxy` wiring, icon existence and security gates. On tag/digest bumps it also determines the upstream changes between the old and new tag (release notes incl. breaking-change radar), updates the `releaseNotes` (changelog) in the affected app's `umbrel-app.yml` and syncs the version table above in this README – after a passing check these changes are automatically committed to the PR branch, and the result appears as a structured comment on the PR. The check scripts (`scripts/check-apps.py`, `scripts/pr-changelog.py`, `scripts/pr-report.js`) are always loaded from the base branch by the workflow, so the check also works on PR branches that are older than the scripts themselves (e.g. older Renovate branches).
- The check detects **breaking changes** on several levels: keywords + conventional-commit markers (`BREAKING CHANGE:`, `feat!:`) in release notes and commit messages, major version jumps, removed env variables/host ports in the compose file, and (for dev-channel digest updates like Gluetun `:latest`) the newest upstream commits. Findings appear as `::warning::` annotations, as a "⚠️ Breaking Changes" section at the top of the PR comment and as the `breaking-change` label on the PR; machine-readable they are available in a JSON summary. Via the repo variable `FAIL_ON_BREAKING=true` the check can additionally fail on breaking changes (label `breaking-ok` on the PR opts out).
- Weekly (Mondays, 06:00 UTC) the [Upstream Changelog Watch](.github/workflows/upstream-watch.yml) checks the release notes of the upstream projects for new versions and breaking changes (incl. early warning on prereleases) and publishes findings as an issue – an existing watch issue is updated instead of duplicated and closed again when all is quiet.
- After every merge to `master`, the [Branch Cleanup](.github/workflows/branch-cleanup.yml) workflow automatically deletes the branches of merged pull requests; open PR branches (e.g. from Renovate) and fork branches are left untouched.
- The packages follow the packaging conventions of the official [umbrel-apps](https://github.com/getumbrel/umbrel-apps) repo; host ports are chosen so they do not overlap with the official store.

## Disclaimer

Community app stores are not reviewed by umbrelOS. As always, check apps before installing – responsibility lies with the user. This store is not affiliated with Umbrel or the respective upstream projects.
