#!/bin/sh
# Entrypoint wrapper for Watchly with self-hosted Nuvio backend support.
#
# Upstream Watchly hard-codes the official Nuvio cloud API (https://api.nuvio.tv)
# and its publishable key in two places, with no configuration hook:
#   - app/services/nuvio.py          (backend: history pulls, token refresh, installs)
#   - app/static/js/modules/nuvio.js (frontend: browser sign-in, addon install)
#
# This script rewrites both files at container start, driven by env vars:
#
#   NUVIO_BASE_URL        Nuvio backend URL, e.g. http://umbrel.internal:30123.
#                         Unset or empty = official cloud, no patching.
#   NUVIO_PUBLISHABLE_KEY Supabase publishable key of that backend. If unset, it
#                         is fetched from ${NUVIO_BASE_URL}/.well-known/nuvio
#                         (discovery endpoint of the Nuvio self-host stack).
#
# If the discovery request fails or the sed patterns no longer match after an
# upstream update, the container exits with an error instead of silently
# talking to the Nuvio cloud.

set -eu

patch_file() {
    # patch_file <file> <expected-grep> <sed-expr> [<sed-expr> ...]
    file="$1"; expected="$2"; shift 2
    sed -i "$@" "$file"
    if ! grep -q "$expected" "$file"; then
        echo "entrypoint: patching ${file} failed (upstream layout changed?) - expected: ${expected}" >&2
        exit 1
    fi
}

if [ -n "${NUVIO_BASE_URL:-}" ]; then
    base_url="${NUVIO_BASE_URL%/}"
    publishable_key="${NUVIO_PUBLISHABLE_KEY:-}"

    if [ -z "$publishable_key" ]; then
        echo "entrypoint: fetching publishable key from ${base_url}/.well-known/nuvio"
        publishable_key="$(curl -fsSL --max-time 15 "${base_url}/.well-known/nuvio" \
            | sed -n 's/.*"publishable_key"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)" || true
        if [ -z "$publishable_key" ]; then
            echo "entrypoint: could not get publishable_key from ${base_url}/.well-known/nuvio - is the backend reachable? Set NUVIO_PUBLISHABLE_KEY manually as fallback" >&2
            exit 1
        fi
    fi

    echo "entrypoint: pointing Watchly at Nuvio backend ${base_url}"

    patch_file app/services/nuvio.py \
        "^BASE_URL = \"${base_url}\"" \
        -e "s|^BASE_URL = .*|BASE_URL = \"${base_url}\"|" \
        -e "s|^PUBLISHABLE_KEY = .*|PUBLISHABLE_KEY = \"${publishable_key}\"|"
    grep -q "^PUBLISHABLE_KEY = \"${publishable_key}\"" app/services/nuvio.py || {
        echo "entrypoint: publishable key patch in app/services/nuvio.py failed" >&2
        exit 1
    }

    patch_file app/static/js/modules/nuvio.js \
        "^const NUVIO_BASE = '${base_url}';" \
        -e "s|^const NUVIO_BASE = .*|const NUVIO_BASE = '${base_url}';|" \
        -e "s|^const NUVIO_KEY = .*|const NUVIO_KEY = '${publishable_key}';|"
    grep -q "^const NUVIO_KEY = '${publishable_key}';" app/static/js/modules/nuvio.js || {
        echo "entrypoint: publishable key patch in app/static/js/modules/nuvio.js failed" >&2
        exit 1
    }
fi

exec uv run main.py
