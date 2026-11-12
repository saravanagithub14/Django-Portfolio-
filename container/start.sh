#!/bin/sh
# Container entrypoint. The disk is back to the image after every sleep, so with R2 configured the live database
# is restored from there first, and Litestream streams each change back. A failed restore stops the start:
# carrying on with the image's older database would overwrite the real one.
set -eu

: "${SECRET_KEY:?Set it with: npx wrangler secret put SECRET_KEY}"

serve="gunicorn portfolio_hub.wsgi:application --bind 0.0.0.0:8080"

if [ -z "${R2_BUCKET:-}" ]; then
    exec $serve
fi

export SQLITE_PATH=/data/db.sqlite3
litestream restore -config container/litestream.yml -if-replica-exists "$SQLITE_PATH"
[ -f "$SQLITE_PATH" ] || cp db.sqlite3 "$SQLITE_PATH"  # first start: seed from the committed database
python manage.py migrate --noinput
exec litestream replicate -config container/litestream.yml -exec "$serve"
