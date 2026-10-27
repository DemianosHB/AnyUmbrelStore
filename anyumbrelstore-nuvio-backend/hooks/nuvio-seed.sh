#!/bin/sh
# anyumbrelstore-nuvio-backend - one-shot avatar seeding job (idempotent).
# Replicates ./nuvio seed_avatar_assets: uploads the avatar PNGs from the
# upstream checkout into the Storage bucket via the Kong gateway.
#
# Lives in hooks/ so umbrelOS app updates deliver script fixes (data/ is
# not re-copied on updates).
set -eu

AVATAR_DIR=/app-data/self-host/assets/avatars
# Shared-network alias safety (see nuvio-migrate.sh): use the unique
# compose container name instead of the short "kong" service alias.
STORAGE_URL=http://anyumbrelstore-nuvio-backend_kong_1:8000/storage/v1/object
KEY="${SERVICE_ROLE_KEY:?SERVICE_ROLE_KEY missing}"

[ -d "$AVATAR_DIR" ] || { echo "[nuvio-seed] ERROR: $AVATAR_DIR missing"; exit 1; }

count=0
uploaded=0
for asset in "$AVATAR_DIR"/*.png; do
    [ -f "$asset" ] || continue
    count=$((count + 1))
    name=$(basename "$asset")
    if curl -fsSI -o /dev/null "$STORAGE_URL/public/avatars/$name"; then
        continue
    fi
    curl -fsS -o /dev/null \
        -X POST \
        -H "apikey: $KEY" \
        -H "Authorization: Bearer $KEY" \
        -H "Content-Type: image/png" \
        -H "Cache-Control: public, max-age=31536000, immutable" \
        -H "x-upsert: true" \
        --data-binary "@$asset" \
        "$STORAGE_URL/avatars/$name"
    uploaded=$((uploaded + 1))
done

[ "$count" -gt 0 ] || { echo "[nuvio-seed] ERROR: no PNG assets in $AVATAR_DIR"; exit 1; }
echo "[nuvio-seed] avatar assets: $count present, $uploaded uploaded"
