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
| [Gluetun VPN](https://github.com/passteque/gluetun) | `anyumbrelstore-gluetun` | 3.41.3_patch1 | Networking | 8010 |
| [Profilarr](https://github.com/Dictionarry-Hub/profilarr) | `anyumbrelstore-profilearr` | 2.2.0_patch1 | Media | 6868 |

### Gluetun VPN

Leichter VPN-Client-Container (WireGuard & OpenVPN, viele Anbieter). Die Weboberfläche zeigt Verbindungsstatus und Server-Infos. Für andere Apps, die durch den Tunnel routen sollen, veröffentlicht er zusätzlich:

- HTTP-Proxy: Port **8009**
- SOCKS5-Proxy: Port **1080**
- Shadowsocks: Port **8388**

Beim Installieren müssen VPN-Anbieter, VPN-Typ und WireGuard-Schlüssel angegeben werden (`VPN_SERVICE_PROVIDER`, `VPN_TYPE`, `WIREGUARD_PRIVATE_KEY`, `SERVER_COUNTRIES`).

### Profilarr

Qualitätsprofile und Custom Formats für Radarr und Sonarr erstellen, testen und synchronisieren – inklusive integriertem Parser zum Testen von Profilen.

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
- Die Pakete folgen den Verpackungs-Konventionen des offiziellen [umbrel-apps](https://github.com/getumbrel/umbrel-apps)-Repos; Host-Ports sind so gewählt, dass sie sich nicht mit dem offiziellen Store überschneiden.

## Hinweis

Community App Stores werden nicht von umbrelOS vorgeprüft. Prüfe Apps wie immer vor der Installation – die Verantwortung liegt beim Nutzer. Dieser Store steht in keiner Verbindung zu Umbrel oder den jeweiligen Upstream-Projekten.
