# Paperless DB-Dump (anyumbrelstore-paperless-dbdump)

Taeglicher PostgreSQL-Dump der Paperless-ngx-App als saubere Backup-Grundlage
(ohne warm kopierte Postgres-Rohdaten). Kein Web-Interface.

## Voraussetzungen

- Paperless-ngx aus dem offiziellen Umbrel App Store installiert
  (DB-User/DB/Passwort = paperless, Host paperless_db_1 im gemeinsamen
  umbrel_main_network)

## Funktion

Der Container bindet den Zielordner direkt per Compose:

    ${UMBREL_ROOT}/app-data/paperless/data/db-export -> /out

Das ist derselbe Bereich, den die Duplicati-App als /paperless-data
mountet. Der Ordner wird beim ersten Start automatisch angelegt.
Keine Folder-Access-Konfiguration noetig (der umbrelOS-Picker zeigt
app-data-Ordner ohnehin nicht an).

Der Container dumppt beim Start sofort und danach taeglich um 01:30
(Europe/Berlin). 7 Tagesversionen bleiben liegen.

## Pruefen

    docker logs anyumbrelstore-paperless-dbdump_dbdump_1
    ls -lh /home/umbrel/umbrel/app-data/paperless/data/db-export

## Restore

    gunzip -c paperless-YYYY-MM-DD.sql.gz | \
      docker exec -i paperless_db_1 psql -U paperless paperless

(vorzugsweise in eine frische, leere Datenbank; danach im
Paperless-Webserver-Container den Suchindex neu aufbauen)

## Hinweise

- Bei abweichenden DB-Zugangsdaten (andere Paperless-Version) die
  environment-Werte PGUSER/PGPASSWORD/PGDATABASE anpassen und die
  Manifest-Version erhoehen.
