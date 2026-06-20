import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait until the configured default database is available."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)
        parser.add_argument("--interval", type=float, default=2.0)

    def handle(self, *args, **options):
        timeout = options["timeout"]
        interval = options["interval"]
        deadline = time.monotonic() + timeout
        connection = connections[DEFAULT_DB_ALIAS]

        self.stdout.write("Waiting for database...")
        while True:
            try:
                connection.ensure_connection()
                connection.close()
                self.stdout.write(self.style.SUCCESS("Database is available."))
                return
            except OperationalError as exc:
                if time.monotonic() >= deadline:
                    raise CommandError(f"Database did not become available in {timeout}s") from exc
                self.stdout.write(f"Database unavailable, retrying in {interval}s...")
                time.sleep(interval)
