"""
Creates any missing analytics_mirror tables from the current Django model
definitions, without touching data — for the case where new mirror models
have been added (e.g. LoanPortfolio, ProgramSummary, RepaymentTransaction,
FOPerformance, added 2026-09-03) and need their empty tables ready for a
real data load (a direct Snowflake-to-Postgres transfer via DBeaver, not
Wimbi's CSV loader — see _docs/architectural_decisions.md). Safe to run
against a dev DB that already has real data loaded into other mirror
tables — ensure_tables_exist() only creates tables that don't exist yet.
"""

from django.core.management.base import BaseCommand

from analytics_mirror.seed_data import ensure_tables_exist


class Command(BaseCommand):
    help = "Create any missing analytics_mirror tables (schema only, no data)."

    def handle(self, *args, **options):
        ensure_tables_exist(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("analytics_mirror tables are up to date."))
