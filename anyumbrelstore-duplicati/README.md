# Duplicati (anyumbrelstore-duplicati)

Store-Fork von Duplicati mit **persistenten Mounts** fuer das
Paperless-Backup. Im Gegensatz zur Store-Version mit manuell gepatchter
Compose gehen diese Mounts bei Updates nicht verloren, weil die App
aus diesem eigenen Store installiert wird und Versionen nur hier im
Repo erhoeht werden.

## Mounts im Container

- /data            Duplicati-Konfiguration (App-Daten dieser App)
- /umbrel          ${UMBREL_ROOT}/home (umbrelOS-Home)
- /paperless-data  ${UMBREL_ROOT}/app-data/paperless/data
  - /paperless-data/media       Dokumente (Originale, Archive, Thumbnails)
  - /paperless-data/db-export    taegliche SQL-Dumps
    (von anyumbrelstore-paperless-dbdump)
- /extra           optional per Ordner-Zugriff (nur lesend)

## Backup-Quellen fuer Paperless

    /paperless-data/media
    /paperless-data/db-export

NICHT sichern: pgdata (Postgres-Rohdaten), redisdata, data/index,
data/llm_index (regenerierbar bzw. warm-kopiert unzuverlaessig).

## Migration von einer bestehenden Duplicati-Installation

1. Bestehende Backup-Konfigurationen in Duplicati exportieren
   (Settings -> Export), falls vorhanden und gebraucht.
2. Alte Duplicati-App deinstallieren (loescht deren App-Daten).
3. Diese App aus dem AnyUmbrelStore installieren. Das Passwort fuer
   die Weboberflaeche steht in den App-Einstellungen.
4. Backup-Job frisch anlegen (Ziel: Hetzner Storage Box Sub-Account,
   SFTP Port 22; Quellen siehe oben).

## Updates

Das Image ist per Digest gepinnt. Updates von Duplicati werden per
Renovate-PR in diesem Repo vorgeschlagen und durch Versions-Bump im
Manifest + Merge selbst gewaehlt - die Mounts bleiben dabei immer
erhalten.
