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
| [Gluetun VPN](https://github.com/passteque/gluetun) | `anyumbrelstore-gluetun` | latest (Dev) | Networking | 8010 |
| [Profilarr](https://github.com/Dictionarry-Hub/profilarr) | `anyumbrelstore-profilearr` | 2.3.0 | Media | 6868 |
| [Paperless Backup](https://github.com/DemianosHB/AnyUmbrelStore/tree/master/anyumbrelstore-paperless-backup) | `anyumbrelstore-paperless-backup` | 1.1.2 | Files | 39120 |

### Gluetun VPN

Leichter VPN-Client-Container (WireGuard & OpenVPN, viele Anbieter). Die Weboberfläche zeigt Verbindungsstatus und Server-Infos. Für andere Apps, die durch den Tunnel routen sollen, veröffentlicht er zusätzlich:

- HTTP-Proxy: Port **8009**
- SOCKS5-Proxy: Port **1080**
- Shadowsocks: Port **8388**

Beim Installieren müssen VPN-Anbieter, VPN-Typ und WireGuard-Schlüssel angegeben werden (`VPN_SERVICE_PROVIDER`, `VPN_TYPE`, `WIREGUARD_PRIVATE_KEY`, `SERVER_COUNTRIES`).

Gluetun folgt dem **Entwicklungs-Kanal** (`latest`, digest-gepinnt), da der eingebaute SOCKS5-Proxy bisher nur dort und in keinem Stable-Release enthalten ist. Renovate aktualisiert den Digest automatisch.

### Profilarr

Qualitätsprofile und Custom Formats für Radarr und Sonarr erstellen, testen und synchronisieren – inklusive integriertem Parser zum Testen von Profilen.

### Paperless Backup

Offsite-Backup für die offizielle Paperless-ngx-App – **eine App, zwei Container**:

- **dbdump** (`postgres:18`): erstellt täglich um 01:30 (Europe/Berlin) einen `pg_dump | gzip`-Dump der Paperless-PostgreSQL-Datenbank in die App-Daten (`db-export`, 7 Tagesversionen, atomar geschrieben). Der pg_dump-Client darf neuer sein als der Datenbank-Server, niemals älter – Renovate kann den Tag daher gefahrlos weiter anheben.
- **duplicati** (offizielles `duplicati/duplicati`-Image, digest-gepinnt wie die offizielle Umbrel-App): sichert täglich die Dokumente (`/mnt/source/media`) und die DB-Dumps (`/mnt/source/db-export`) per SFTP (Port 22, Passwort-Authentifizierung – bewusst ohne SSH-Keys), z. B. auf eine Hetzner Storage Box. Backup-Job, Zeitplan (passend nach dem DB-Dump, z. B. 02:30), AES-256-Verschlüsselung und Retention werden in der gewohnten Duplicati-Weboberfläche eingerichtet.

Die offizielle Paperless-App wird weder geforkt noch modifiziert – `media` wird nur lesend in die Backup-App gemountet. Der Duplicati-Container läuft als root (Image-Default), da Docker fehlende Bind-Mount-Ordner und der dbdump-Container die App-Daten root-owned anlegen; die Backup-Quellen bleiben ausschließlich lesend gemountet. Restore: Dokumente über die Duplicati-Web-UI, DB-Dump per `gunzip -c paperless-YYYY-MM-DD.sql.gz | docker exec -i paperless_db_1 psql -U paperless paperless`, danach den Suchindex in Paperless neu aufbauen.

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
- Jeder Pull-Request wird von der [App-Store-Check](.github/workflows/app-store-check.yml)-Action automatisch geprüft: Manifest-Schema, Port-Konflikte mit dem offiziellen Store, Digest-Pinning und Sicherheits-Gates. Bei Tag- oder Digest-Bumps ermittelt sie zusätzlich die Upstream-Änderungen zwischen altem und neuem Tag (Release-Notes inkl. Breaking-Change-Radar), ergänzt die `releaseNotes` (Changelog) in der `umbrel-app.yml` der betroffenen App und gleicht die Versions-Tabelle oben im README ab – nach bestandenem Check werden diese Änderungen automatisch als Commit zum PR-Branch hinzugefügt.
- Wöchentlich prüft der [Upstream Changelog Watch](.github/workflows/upstream-watch.yml) die Release-Notes der Upstream-Projekte auf neue Versionen und Breaking Changes und legt bei Befunden automatisch ein Issue an.
- Die Pakete folgen den Verpackungs-Konventionen des offiziellen [umbrel-apps](https://github.com/getumbrel/umbrel-apps)-Repos; Host-Ports sind so gewählt, dass sie sich nicht mit dem offiziellen Store überschneiden.

## Hinweis

Community App Stores werden nicht von umbrelOS vorgeprüft. Prüfe Apps wie immer vor der Installation – die Verantwortung liegt beim Nutzer. Dieser Store steht in keiner Verbindung zu Umbrel oder den jeweiligen Upstream-Projekten.
