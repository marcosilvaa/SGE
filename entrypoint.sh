#!/usr/bin/env sh
set -eu

: "${DB_WAIT_TIMEOUT:=90}"
: "${DB_WAIT_INTERVAL:=2}"
: "${RUN_MIGRATIONS:=true}"
: "${RUN_COLLECTSTATIC:=true}"

python manage.py wait_for_db --timeout "$DB_WAIT_TIMEOUT" --interval "$DB_WAIT_INTERVAL"

if [ "$RUN_MIGRATIONS" = "true" ] || [ "$RUN_COLLECTSTATIC" = "true" ]; then
  python - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django
from django.core.management import call_command
from django.db import connection, transaction

django.setup()

LOCK_ID = 1936050031
RUN_MIGRATIONS = os.environ.get("RUN_MIGRATIONS", "true") == "true"
RUN_COLLECTSTATIC = os.environ.get("RUN_COLLECTSTATIC", "true") == "true"


def run_startup_tasks():
    if RUN_MIGRATIONS:
        call_command("migrate", interactive=False)
    if RUN_COLLECTSTATIC:
        call_command("collectstatic", interactive=False, verbosity=1)


if connection.vendor == "postgresql":
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [LOCK_ID])
        run_startup_tasks()
else:
    run_startup_tasks()
PY
fi

exec "$@"
