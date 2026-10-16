# Paperless DB-Dump (anyumbrelstore-paperless-dbdump)

Täglicher PostgreSQL-Dump der Paperless-ngx-App als saubere Backup-Grundlage
(ohne warm kopierte Postgres-Rohdaten). Kein Web-Interface.

## Voraussetzungen

- Paperless-ngx aus dem offiziellen Umbrel App Store installiert
  (DB-User/DB/Passwort = paperless, Netzwerk paperless_main_network,
  Host paperless_db_1 – exakt wie in der Store-Compose hinterlegt)

## Einrichtung (einmalig)

1. Zielordner anlegen (SSH auf dem Umbrel):

       mkdir -p /home/umbrel/umbrel/app-data/paperless/data/db-export

2. In den App-Einstellungen der Mini-App unter Ordner-Zugriff /
   Folder Access den Eintrag "Dump-Zielordner" mit dem Ordner
   db-export (Pfad aus Schritt 1) verknüpfen.

3. Der Container führt beim Start sofort einen Dump aus und danach
   täglich um 01:30 (Europe/Berlin). 7 Tagesversionen bleiben liegen.

## Prüfen

       docker logs -f anyumbrelstore-paperless-dbdump_dbdump_1
       ls -lh /home/umbrel/umbrel/app-data/paperless/data/db-export

## Restore

       gunzip -c paperless-YYYY-MM-DD.sql.gz | \
         docker exec -i paperless_db_1 psql -U paperless paperless

(vorzugsweise in eine frische, leere Datenbank; danach im
Paperless-Webserver-Container den Suchindex neu aufbauen:
docker exec paperless_webserver_1 document_index reindex)

## Hinweise

- Falls "docker network ls" auf dem Umbrel kein paperless_main_network
  zeigt: Netzwerkname in docker-compose.yml hier im Repo anpassen und
  App im Store neu laden.
- Bei abweichenden DB-Zugangsdaten (andere Paperless-Version) die
  environment-Werte PGUSER/PGPASSWORD/PGDATABASE anpassen und die
  Manifest-Version erhöhen.
