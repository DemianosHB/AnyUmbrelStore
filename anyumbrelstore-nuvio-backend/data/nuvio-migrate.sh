#!/bin/sh
# anyumbrelstore-nuvio-backend - one-shot DB migration job (idempotent).
# Replicates ./nuvio migrate + ./nuvio configure_instance from
# NuvioMedia/self-host, but over the docker network with a psql client
# (no docker socket, no docker compose exec).
#
# The Nuvio baseline migrations also run via the db image's
# docker-entrypoint-initdb.d on first boot; this job exists to apply
# migrations added by newer upstream revisions on app updates.
set -eu

DB_NAME="${POSTGRES_DB:-postgres}"
PSQL="psql -h db -U supabase_admin -d $DB_NAME"

log() { echo "[nuvio-migrate] $*"; }

for migration in /migrations/*.sql; do
    [ -f "$migration" ] || continue
    name=$(basename "$migration")
    version=${name%%_*}
    table_exists=$($PSQL -Atc "select to_regclass('nuvio_migrations.schema_migrations') is not null" 2>/dev/null || true)
    applied=f
    if [ "$table_exists" = "t" ]; then
        applied=$($PSQL -Atc "select exists(select 1 from nuvio_migrations.schema_migrations where version = '$version')" 2>/dev/null || true)
    fi
    if [ "$applied" = "t" ]; then
        log "$name already applied"
        continue
    fi
    log "applying $name"
    $PSQL -v ON_ERROR_STOP=1 -f "$migration"
done

CATALOG_URL="${DEFAULT_CATALOG_URL:-https://catalog.nuvio.tv/manifest.json}"
$PSQL -v ON_ERROR_STOP=1 -v catalog_url="$CATALOG_URL" <<'SQL'
INSERT INTO nuvio_private.instance_settings (key, value, updated_at)
VALUES ('default_catalog_url', :'catalog_url', now())
ON CONFLICT (key) DO UPDATE
SET value = excluded.value,
    updated_at = excluded.updated_at;
SQL
log "instance configured (catalog: $CATALOG_URL)"
