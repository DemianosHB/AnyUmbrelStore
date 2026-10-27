# SECRET_KEY für AIOStreams: verschlüsselt die gespeicherten Addon-
# Konfigurationen. Muss exakt 64 Hex-Zeichen lang sein und über Updates
# stabil bleiben – derive_entropy liefert deterministisch HMAC-SHA256-Hex
# (64 Zeichen) je Installation und Label.
export APP_ANYUMBRELSTORE_AIOSTREAMS_SECRET_KEY="$(derive_entropy "${app_entropy_identifier}-secret-key")"
