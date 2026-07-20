#!/bin/sh
# Runs as root, fixes the volume, then drops to `app` for the actual server.
#
# Railway mounts volumes root-owned at RUNTIME, which covers whatever ownership
# the image baked in. A container that has already dropped to a non-root user
# therefore cannot create its database file — SQLite reports the tersely
# unhelpful "unable to open database file". Chowning has to happen here, after
# the mount exists and while we are still root.
set -e

DB_DIR=$(dirname "${DB_PATH:-/data/pipeline.db}")

mkdir -p "$DB_DIR"

# Only chown when it is actually wrong: after the first boot it always already
# is, and on a large volume the recursive walk is not free.
if [ "$(stat -c '%u' "$DB_DIR")" != "1000" ]; then
    echo "entrypoint: chowning $DB_DIR to app"
    chown -R app:app "$DB_DIR"
fi

SERVER="python -m uvicorn pipeline.app:app --host 0.0.0.0 --port ${PORT:-8000}"

# Drop privileges with whichever tool this base image actually ships. Both come
# from util-linux and should be present, but the fallback means an unexpectedly
# minimal base degrades to running as root rather than refusing to boot — for a
# single-tenant private service that tradeoff is the right way round.
if command -v setpriv >/dev/null 2>&1; then
    exec setpriv --reuid=1000 --regid=1000 --init-groups $SERVER
elif command -v su >/dev/null 2>&1; then
    exec su app -c "$SERVER"
else
    echo "entrypoint: WARNING no setpriv or su; running as root"
    exec $SERVER
fi
