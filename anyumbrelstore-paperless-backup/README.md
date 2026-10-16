# Paperless Borg Backup (anyumbrelstore-paperless-backup)

Headless-App: sichert die Paperless-Daten per Borgmatic in ein
Borg-Repo auf einer Hetzner Storage Box. Kein Fork, keine Modifikation
der offiziellen Paperless-App: der Paperless-App-Datenordner wird nur
lesend gemountet, die App laesst Paperless sonst voellig unberuehrt.

Container: anyumbrelstore-paperless-backup_backup_1
App-Daten: ~/umbrel/app-data/anyumbrelstore-paperless-backup/data

## Was gesichert wird

    /mnt/source/media       Dokumente (Originale, Archiv, Thumbnails)
    /mnt/source/db-export   taegliche SQL-Dumps (von anyumbrelstore-paperless-dbdump)

Nicht gesichert (bewusst): pgdata, redisdata, Suchindizes -
regenerierbar bzw. Laufzeitdaten. Zeitplan: taeglich 02:30 (Europe/
Berlin), passend nach dem dbdump um 01:30. Retention: 7 daily,
4 weekly, 6 monthly.

## Voraussetzungen

1. Sub-Account auf der Storage Box mit aktivierter SSH-Unterstuetzung
   UND externer Erreichbarkeit (Hetzner Console). NICHT "Nur lesen".
   Borg laeuft auf Port 23, Sub-Account-Host z.B. uXXXXX-sub1.your-storagebox.de.
2. anyumbrelstore-paperless-dbdump installiert (fuer db-export).

## Einrichtung (einmalig, per SSH auf dem Umbrel)

Im Folgenden: APP=anyumbrelstore-paperless-backup_backup_1 und
DATA=~/umbrel/app-data/anyumbrelstore-paperless-backup/data

1. SSH-Key erzeugen und beim Sub-Account hinterlegen:

        docker exec -it $APP ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ""
        docker exec -it $APP cat /root/.ssh/id_ed25519.pub

   Den angezeigten Key in der Hetzner Console als SSH-Key des
   Sub-Accounts speichern.

2. Host-Key der Storage Box uebernehmen:

        docker exec -it $APP sh -c "ssh-keyscan -p 23 uXXXXX-sub1.your-storagebox.de >> /root/.ssh/known_hosts"

3. Borg-Passphrase erzeugen (dateibasiert, nie im Repo):

        openssl rand -base64 32 > $DATA/borg-passphrase
        chmod 600 $DATA/borg-passphrase

   Und sicher verwahren (Password-Manager): ohne sie ist das Repo unlesbar.

4. borgmatic-Konfiguration anlegen: $DATA/borgmatic.d/config.yaml

        source_directories:
          - /mnt/source/media
          - /mnt/source/db-export

        repositories:
          - path: ssh://uXXXXX-sub1@uXXXXX-sub1.your-storagebox.de:23/./borg/paperless
            label: storagebox

        storage:
          remote_path: borg-1.4
          ssh_command: ssh -i /root/.ssh/id_ed25519

        retention:
          keep_daily: 7
          keep_weekly: 4
          keep_monthly: 6

        archive_name_format: paperless-{now}

   remote_path: borg-1.4 gemaess Hetzner-Doku; falls Hetzner den Pfad
   aendert, hier anpassen (siehe Hetzner-Docs "SSH/rsync/BorgBackup").

5. Borg-Repo initialisieren:

        docker exec -it $APP sh -c "export BORG_PASSPHRASE=$(cat /config/borg-passphrase) && borg init --encryption=repokey --remote-path=borg-1.4 ssh://uXXXXX-sub1@uXXXXX-sub1.your-storagebox.de:23/./borg/paperless"

6. Erster Testlauf + Kontrolle:

        docker exec -it $APP sh -c "export BORG_PASSPHRASE=$(cat /config/borg-passphrase) && borgmatic --stats -v 1"
        docker logs $APP

Danach laeuft der Cron des Containers automatisch (02:30 Berlin).

## Restore

Archive anzeigen:

        docker exec -it $APP sh -c "export BORG_PASSPHRASE=$(cat /config/borg-passphrase) && borgmatic list"

Dateien aus einem Archiv extrahieren: /mnt/source ist nur-lesend,
extrahieren geht deshalb nach /config/restore:

        mkdir -p $DATA/restore && cd $DATA/restore
        docker exec -it --workdir /config/restore $APP sh -c "export BORG_PASSPHRASE=$(cat /config/borg-passphrase) && borgmatic extract --archive ARCHIVNAME --path media"

Danach die Dateien vom Host aus nach ~/umbrel/app-data/paperless/data/
kopieren. DB-Dump einspielen:

        gunzip -c db-export/paperless-YYYY-MM-DD.sql.gz | sudo docker exec -i paperless_db_1 psql -U paperless paperless

Suchindex danach neu aufbauen (document_index reindex im
webserver-Container).

## Monitoring (optional)

Das Image enthaelt Apprise. Fuer Pushover-Meldungen bei Fehlern einen
Hook in config.yaml ergaenzen (URL-Schema siehe Apprise-Doku zu
Pushover/pover://):

        commands:
          - after: everything
            states: [fail]
            run:
              - apprise -t "Paperless-Backup FEHLER" -b "borgmatic fehlgeschlagen" "pover://.../"

## Updates

Image ist Semver-Tag + Digest-gepinnt (2.1.10); Renovate oeffnet
automatisch Update-PRs. App-Updates entfernen die Konfiguration und
Secrets in den App-Daten nicht.

## Warum keine offizielle Duplicati-App / kein Fork?

- Custom-Mounts in offiziellen Store-Apps verschwinden bei jedem App-Update.
- Der umbrelOS-Folder-Picker zeigt app-data nicht an.
- Ein Store-Fork von Duplicati waere ein Fork (verworfen).
- Diese App ist ein origineller Sidecar: Paperless bleibt unangetastet,
  die Compose-Datei steht in diesem Repo und ueberlebt Updates.
