# AnyUmbrelStore

Ein [Community App Store](https://github.com/getumbrel/umbrel-community-app-store) für [umbrelOS](https://umbrel.com) mit kuratierten Self-Hosted-Apps, die (noch) nicht im offiziellen Store verfügbar sind.

## Store hinzufügen

1. Öffne auf deinem Umbrel die **App Store** Seite.
2. Wähle unten **External app store hinzufügen** und gib diese URL ein:

   ```
   https://github.com/DemianosHB/AnyUmbrelStore
   ```

3. Die Apps dieses Stores erscheinen anschließend im App Store.

## Verfügbare Apps

| App | ID | Version | Kategorie | Port |
|---|---|---|---|---|
| [Gluetun VPN](https://github.com/passteque/gluetun) | `anyumbrelstore-gluetun` | latest (Dev) | Networking | 30126 |
| [Profilarr](https://github.com/Dictionarry-Hub/profilarr) | `anyumbrelstore-profilearr` | 2.3.1 | Media | 6868 |
| [Paperless Backup](https://github.com/DemianosHB/AnyUmbrelStore/tree/master/anyumbrelstore-paperless-backup) | `anyumbrelstore-paperless-backup` | 2.4.1.0 | Files | 39120 |
| [AIOStreams](https://github.com/Viren070/AIOStreams) | `anyumbrelstore-aiostreams` | 2.37.0 | Media | 30124 |
| [Nuvio Backend](https://github.com/NuvioMedia/self-host) | `anyumbrelstore-nuvio-backend` | 0.1.5 | Media | 30122 |
| [InfiniDysk](https://github.com/infinidysk/infinidysk) | `anyumbrelstore-infinidysk` | 1.6.3 | Media | 30125 |
| [Watchly](https://github.com/TimilsinaBimal/Watchly) | `anyumbrelstore-watchly` | 1.17.2 | Media | 30127 |

### Gluetun VPN

Leichter VPN-Client-Container (WireGuard & OpenVPN, viele Anbieter). Die Weboberfläche (umbrel.local:30126) zeigt Verbindungsstatus, öffentliche IP und Server-Infos und erlaubt Start/Stopp aus dem Browser (API-Key siehe App-Zugangsdaten). Für andere Apps, die durch den Tunnel routen sollen, veröffentlicht er zusätzlich:

- HTTP-Proxy: Port **8009**
- SOCKS5-Proxy: Port **1080**
- Shadowsocks: Port **8388**

Beim Installieren müssen VPN-Anbieter, VPN-Typ und WireGuard-Schlüssel angegeben werden (`VPN_SERVICE_PROVIDER`, `VPN_TYPE`, `WIREGUARD_PRIVATE_KEY`, `SERVER_COUNTRIES`).

Gluetun folgt dem **Entwicklungs-Kanal** (`latest`, digest-gepinnt), da der eingebaute SOCKS5-Proxy bisher nur dort und in keinem Stable-Release enthalten ist. Renovate aktualisiert den Digest automatisch. Die WebUI läuft auf Port 30126 (Packaging-Update: der ursprüngliche Port 8010 kollidiert mit dem Ryot-Paket aus einem anderen Community-Store); HTTP-Proxy (8009), SOCKS5 (1080) und Shadowsocks (8388) bleiben unverändert – AIOStreams und InfiniDysk erreichen Gluetun über den Container-Namen.

### Profilarr

Qualitätsprofile und Custom Formats für Radarr und Sonarr erstellen, testen und synchronisieren – inklusive integriertem Parser zum Testen von Profilen.

### Paperless Backup

Offsite-Backup für die offizielle Paperless-ngx-App – **eine App, zwei Container**:

- **dbdump** (`postgres:18`): erstellt täglich um 01:30 (Europe/Berlin) einen `pg_dump | gzip`-Dump der Paperless-PostgreSQL-Datenbank in die App-Daten (`db-export`, 7 Tagesversionen, atomar geschrieben). Der pg_dump-Client darf neuer sein als der Datenbank-Server, niemals älter – Renovate kann den Tag daher gefahrlos weiter anheben.
- **duplicati** (offizielles `duplicati/duplicati`-Image, digest-gepinnt wie die offizielle Umbrel-App): sichert täglich die Dokumente (`/mnt/source/media`) und die DB-Dumps (`/mnt/source/db-export`) per SFTP (Port 22, Passwort-Authentifizierung – bewusst ohne SSH-Keys), z. B. auf eine Hetzner Storage Box. Backup-Job, Zeitplan (passend nach dem DB-Dump, z. B. 02:30), AES-256-Verschlüsselung und Retention werden in der gewohnten Duplicati-Weboberfläche eingerichtet.

Die offizielle Paperless-App wird weder geforkt noch modifiziert – `media` wird nur lesend in die Backup-App gemountet. Der Duplicati-Container läuft als root (Image-Default), da Docker fehlende Bind-Mount-Ordner und der dbdump-Container die App-Daten root-owned anlegen; die Backup-Quellen bleiben ausschließlich lesend gemountet. Restore: Dokumente über die Duplicati-Web-UI, DB-Dump per `gunzip -c paperless-YYYY-MM-DD.sql.gz | docker exec -i paperless_db_1 psql -U paperless paperless`, danach den Suchindex in Paperless neu aufbauen.

### AIOStreams

Stremio-**Super-Addon**: bündelt mehrere Stremio-Addons und Debrid-/Usenet-Dienste (z. B. Torrentio, Comet, MediaFusion) in einem einzigen, hoch anpassbaren Addon. Ergebnisse aller Quellen werden gefiltert, sortiert, dedupliziert und in einer sauberen Stream-Liste zusammengeführt – inklusive Addon-Marktplatz (80+ Addons), nativer Usenet-Streaming-Engine und Jellyfin-kompatibler Oberfläche zum direkten Ansehen ohne Stremio.

Erste Schritte: Weboberfläche öffnen, im Dashboard einloggen (Benutzer `admin`, Passwort siehe App-Zugangsdaten), Addons und Debrid-Dienste einrichten und das erzeugte Addon über den Install-Button zu Stremio hinzufügen. Debrid- und Usenet-Dienste werden als **Services** eingebunden (Config → Services); seit v2.37 sind die eigenständigen TorBox-Addons entfernt – der TorBox-API-Key (torbox.app → Settings) gehört unter Config → Services → TorBox. `BASE_URL` steht standardmäßig auf der Umbrel-Launch-URL; für Clients ohne mDNS (z. B. manche Android-TV-Apps) in den App-Einstellungen auf die IP-URL umstellen. Das Addon ist bewusst ohne Umbrel-Login im lokalen Netz erreichbar (Stremio- und Jellyfin-Clients senden keine Umbrel-Cookies und erreichen das Addon über dynamische Config-ID-Pfade); das Dashboard selbst ist über den Operator-Login geschützt. Nur im lokalen Netz betreiben. Renovate aktualisiert Manifest-Version und Image gebündelt.

### Nuvio Backend

Selbst gehostetes Nuvio-Backend für eigene Nuvio-Clients – der API-Stack aus [NuvioMedia/self-host](https://github.com/NuvioMedia/self-host) (PostgreSQL, GoTrue-Auth, PostgREST, Storage, Edge Functions, Kong-Gateway) inklusive Account-Dashboard. Nach der Installation im Account-Dashboard (Port **30122**) zuerst einen Account anlegen; Nuvio-Clients verbinden sich mit der Backend-URL (Port **30123**).

Der Upstream wird als Klon an einer gepinnten Commit-Revision in die App-Daten gezogen (`nuvio-fetch`-One-Shot-Service), Secrets werden beim ersten Start automatisch generiert, DB-Migrationen laufen idempotent über `nuvio-migrate`. Die Manifest-Version (0.1.x) ist die eigene Packaging-Version des Stores – Upstream published keine Releases. Die Images des Supabase-Stacks bewegen sich bewusst nur gemeinsam mit dem gepinnten Upstream-Commit (siehe Pflege-Abschnitt).

### InfiniDysk

Usenet-Streaming über ein virtuelles WebDAV-Laufwerk: InfiniDysk (NzbDAV SuperFork) entpackt NZB-Dateien on-the-fly und stellt sie über WebDAV als Dateien bereit – inklusive SABnzbd-kompatibler API, ohne dass Downloads vollständig abgeschlossen werden müssen. Nach dem Erststart (Admin-Account im Web-UI anlegen) werden Newznab-Indexer und NNTP-Server hinterlegt.

Anbindung an AIOStreams auf einem von zwei Wegen: als **NzbDAV-Service** (rein Playback – AIOStreams proxied die Streams, braucht für die Suche aber eigene Newznab-Addons) oder als **Custom Addon** über die Addon-Adapter der InfiniDysk-Search-Profiles (Manifest-URL `/adapters/addon/<token>/manifest.json`, Host-Teil in AIOStreams auf `anyumbrelstore-infinidysk_server_1:3000` ändern) – dann liefert InfiniDysk die Newznab-Suche selbst und AIOStreams übernimmt nur das Playback; beide Wege nicht miteinander kombinieren. Indexer-Anfragen (Newznab-Suche, NZB-Grabs) lassen sich über Settings → Indexers per HTTP(S)- oder SOCKS5-Proxy routen (global oder pro Indexer, z. B. durch den Gluetun-Container); NNTP-Provider-Verbindungen unterstützen keinen Proxy. Die App ist ohne Umbrel-Login im lokalen Netz erreichbar (WebDAV- und SABnzbd-Clients senden keine Umbrel-Cookies), aber über ihr eigenes Login geschützt. Renovate aktualisiert Manifest-Version und Image-Tag gebündelt.

### Watchly

Personalisierte Empfehlungen aus deiner Nuvio-Historie: Watchly liest die Watch-Historie direkt aus dem selbst gehosteten Nuvio-Backend und baut daraus Empfehlungs-Reihen („Top Picks for You", „Because you watched …", Genre- und Keyword-Kataloge), die als Katalog-Addon auf dem Nuvio-Homescreen erscheinen – ohne Umweg über Trakt, Simkl oder die Nuvio-Cloud.

Das Image wird vom Store selbst gebaut (siehe Pflege-Abschnitt) und per Start-Skript auf das eigene Nuvio-Backend gezeigt; der Publishable-Key wird beim Container-Start automatisch über den Discovery-Endpunkt geholt. **Wichtig:** Watchly benötigt einen TMDB-API-Key als `TMDB_API_KEY`-Env-Variable im `server`-Service – mehrere Watchly-Code-Pfade ignorieren den in der Web-UI hinterlegten Key, ohne die Env-Variable schlägt das Manifest mit Fehler 500 fehl (Details: [`docker/watchly/README.md`](docker/watchly/README.md)).

## Struktur

Jede App liegt in einem eigenen Ordner, benannt nach ihrer App-ID (Präfix `anyumbrelstore-`):

```text
<app-id>/
  umbrel-app.yml      # Manifest (Metadata, Port, Version)
  docker-compose.yml  # Docker-Services
  icon.svg            # App-Icon (optional, Community-Stores)
```

Die Store-Definition steht in [`umbrel-app-store.yml`](umbrel-app-store.yml).

## Pflege

- Container-Images werden automatisch von [Renovate](https://renovatebot.com) aktuell gehalten (`renovate.json`).
- **Ausnahme Nuvio Backend:** Die Images des Supabase-Stacks (Kong, GoTrue, PostgREST, Storage-API, Postgres, Edge-Runtime, imgproxy) sind an den gepinnten Upstream-Commit gekoppelt und werden manuell gemeinsam mit dem Pin gebumpt; Renovate aktualisiert sie bewusst nicht (Package-Regel in `renovate.json`). Die One-Shot-Images (`alpine`, `curl`) und das Digest des Account-Dashboards bleiben bei Renovate.
- **Watchly (eigenes Image):** Das Image `ghcr.io/demianoshb/watchly` baut der Workflow [Watchly Docker Image](.github/workflows/watchly-image.yml) selbst (Multi-Arch, amd64+arm64) aus dem gepinnten Upstream-Tag (`WATCHLY_REF`); beim Container-Start patcht das Entry-Skript die hart codierte Nuvio-Cloud-URL auf das eigene Backend (Details: [`docker/watchly/README.md`](docker/watchly/README.md)). Upstream-Bumps laufen bewusst manuell: `WATCHLY_REF` im Workflow erhöhen → Image-Build abwarten → Renovate zieht die App hoch; dabei prüfen, ob die sed/grep-Muster des Entry-Skripts zum neuen Upstream passen. Der TMDB-API-Key muss als `TMDB_API_KEY`-Env-Variable im `server`-Service gesetzt sein (Umbrel rendert die App-Compose bei Updates neu, siehe Watchly-README).
- Jeder Pull-Request wird von der [App-Store-Check](.github/workflows/app-store-check.yml)-Action automatisch geprüft: Manifest-Schema, Versionen (kein bare `latest`), Digest-Pinning beweglicher Tags, Port-Konflikte im eigenen Store und gegen den offiziellen Store, `app_proxy`-Wiring, Icon-Existenz und Security-Gates. Bei Tag- oder Digest-Bumps ermittelt sie zusätzlich die Upstream-Änderungen zwischen altem und neuem Tag (Release-Notes inkl. Breaking-Change-Radar), ergänzt die `releaseNotes` (Changelog) in der `umbrel-app.yml` der betroffenen App und gleicht die Versions-Tabelle oben im README ab – nach bestandenem Check werden diese Änderungen automatisch als Commit zum PR-Branch hinzugefügt, und das Ergebnis erscheint als strukturierter Kommentar am PR. Die zugehörigen Check-Skripte (`scripts/check-apps.py`, `scripts/pr-changelog.py`, `scripts/pr-report.js`) lädt der Workflow immer vom Base-Branch, damit der Check auch auf PR-Branches funktioniert, die älter sind als die Skripte selbst (z. B. ältere Renovate-Branches).
- Wöchentlich (montags, 06:00 UTC) prüft der [Upstream Changelog Watch](.github/workflows/upstream-watch.yml) die Release-Notes der Upstream-Projekte auf neue Versionen und Breaking Changes und veröffentlicht Befunde als Issue – ein bestehendes Watch-Issue wird dabei aktualisiert statt neu angelegt und bei Entwarnung wieder geschlossen.
- Nach jedem Merge auf `master` räumt der [Branch Cleanup](.github/workflows/branch-cleanup.yml) die Branches gemergter Pull-Requests automatisch ab; offene PR-Branches (z. B. von Renovate) und Fork-Branches bleiben unberührt.
- Die Pakete folgen den Verpackungs-Konventionen des offiziellen [umbrel-apps](https://github.com/getumbrel/umbrel-apps)-Repos; Host-Ports sind so gewählt, dass sie sich nicht mit dem offiziellen Store überschneiden.

## Hinweis

Community App Stores werden nicht von umbrelOS vorgeprüft. Prüfe Apps wie immer vor der Installation – die Verantwortung liegt beim Nutzer. Dieser Store steht in keiner Verbindung zu Umbrel oder den jeweiligen Upstream-Projekten.
