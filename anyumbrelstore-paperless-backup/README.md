# Paperless Backup (anyumbrelstore-paperless-backup)

Eine App, zwei Container: **dbdump** (DB-Dump der Paperless-PostgreSQL)
und **Duplicati** (offizielles Container-Image, identischer Digest wie
in der offiziellen Umbrel-App) fuer das Backup auf die Hetzner
Storage Box. Kein Fork, keine Modifikation der offiziellen
Paperless-App: media wird nur lesend gemountet, die DB wird uebers
gemeinsame Docker-Netzwerk gelesen.

Container:

    anyumbrelstore-paperless-backup_dbdump_1    (DB-Dump, 01:30 Berlin)
    anyumbrelstore-paperless-backup_duplicati_1 (Duplicati Web-UI + Backup)

App-Daten: ~/umbrel/app-data/anyumbrelstore-paperless-backup/data

## Was gesichert wird

    /mnt/source/media     Dokumente (Originale, Archiv, Thumbnails)
    /mnt/source/db-export taegliche SQL-Dumps (dbdump, 7 Tagesversionen)

Beide Mounts sind nur lesend. Nicht gesichert (bewusst): pgdata,
redisdata, Suchindizes - regenerierbar bzw. Laufzeitdaten.

## Voraussetzungen

1. Sub-Account auf der Storage Box, **externe Erreichbarkeit**
   aktivieren, NICHT "Nur lesen". SFTP/SCP auf Port 22 ist bei
Storage Boxes immer aktiv - SSH-Keys werden nicht benoetigt.
2. Offizielle Paperless-App installiert (DB paperless, Host paperless_db_1).

## Backup-Job einrichten (Duplicati Web-UI, ohne SSH)

App in Umbrel oeffnen; das Web-Passwort steht in den App-Zugangsdaten
(deterministicPassword). Dann: Add backup ->

1. **Ziel:** Typ "SSH (SFTP)", Server uXXXXX-sub1.your-storagebox.de,
   Port 22, Benutzername + Passwort des Sub-Accounts, Pfad /.
2. **Verschluesselung:** AES-256 mit eigener Passphrase - Passphrase in
   Vaultwarden sichern, sonst ist das Offsite-Backup im Desasterfall
   unlesbar.
3. **Quelldaten:** /mnt/source/media und /mnt/source/db-export
4. **Zeitplan:** taeglich 02:30 (Europe/Berlin), passend nach dem
   DB-Dump um 01:30.
5. **Retention:** Smart-Retention, z. B. 7 Tage (taeglich), 4 Wochen
   (woechentlich), 6 Monate (monatlich).
6. Erstlauf: Bandbreitenoption "Throttle upload" setzen, falls die
   DSL-Leitung nicht tagelang blockieren soll.

## DB-Dump pruefen

    docker exec -it anyumbrelstore-paperless-backup_dbdump_1 ls -lh /out
    docker logs anyumbrelstore-paperless-backup_dbdump_1

Der dbdump-Container laeuft automatisch (Start + taeglich 01:30,
7 Tagesversionen, atomar via .part-Umbenennung).

## Restore

- **Einzeldateien:** Duplicati-UI -> Restore -> Direct restore,
  Zielpfad z. B. /data/restore (die Quell-Mounts sind bewusst nur
  lesend). Danach vom Host aus von
  ~/umbrel/app-data/anyumbrelstore-paperless-backup/data/restore nach
  ~/umbrel/app-data/paperless/data/media verschieben. Oder Restore
  als ZIP herunterladen.
- **DB-Dump einspielen** (Dump liegt auch lokal in data/db-export):

        gunzip -c data/db-export/paperless-YYYY-MM-DD.sql.gz | sudo docker exec -i paperless_db_1 psql -U paperless paperless

Suchindex danach neu aufbauen (document_index reindex im
webserver-Container).

## Migration von der alten Loesung

- Eigenstaendige App anyumbrelstore-paperless-dbdump: deinstallieren,
  die Dumps entstehen künftig hier (Funktion ist identisch uebernommen).
  Der Ordner db-export in den Paperless-App-Daten ist veraltet und
  kann geloescht werden.
- Falls irgendwo noch die alte Duplicati-App mit Custom-Mount lief:
  Backup-Konfiguration exportieren, App deinstallieren, Job in dieser
  App neu anlegen (Quellen siehe oben).

## Monitoring (optional)

Duplicati-Option "run-script-after" auf ein curl zur Pushover-API
setzen - gleiche Mechanik wie auf dem vServer (Skript-Muster wie
/usr/local/sbin/pushover-notify.sh, dritter Kanal "Paperless-Backup").

## Updates

Duplicati-Image ist tag + digest-gepinnt (2.4.0.1, identisch mit der
offiziellen Umbrel-App); Renovate oeffnet automatisch Update-PRs.
App-Updates entfernen die Konfiguration und Dumps in den App-Daten
nicht.

## Warum nicht die offizielle Duplicati-Store-App?

Die offizielle App sieht die Paperless-App-Daten nicht: der
umbrelOS-Folder-Picker zeigt nur verwaltete Speicherordner, app-data
nicht, und manuelle Custom-Mounts verschwinden bei jedem App-Update.
Diese App loest das mit Mounts in der eigenen Compose-Datei - ohne
Fork des offiziellen Manifests, das offizielle Duplicati-Image bleibt
unveraendert im Einsatz.
