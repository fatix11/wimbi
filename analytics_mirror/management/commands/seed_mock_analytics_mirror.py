"""
Seeds the analytics_mirror schema with fixture data so the app is testable
before Airbyte's real Snowflake sync has run (see _docs/architectural_decisions.md
ADR-003). Safe to run against a fresh Postgres; once Airbyte has landed real
data there's no reason to run this anymore.
"""

from django.core.management.base import BaseCommand

from analytics_mirror.seed_data import FARMERS, JOURNEY_EVENTS, ensure_tables_exist, seed


class Command(BaseCommand):
    help = "Seed the analytics_mirror schema with fixture farmers/journey/lineage data."

    def handle(self, *args, **options):
        ensure_tables_exist(stdout=self.stdout)
        seed()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(FARMERS)} farmers, {len(JOURNEY_EVENTS)} journey events, "
            f"{len(FARMERS)} bridge rows."
        ))
