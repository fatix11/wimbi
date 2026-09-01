"""
Loads real CSV snapshots (see _docs/architectural_decisions.md ADR-006)
into the analytics_mirror schema via Postgres COPY. Truncates each target
table first (idempotent reruns) — which means it also wipes the synthetic
Kenya/Rwanda rows `seed_mock_analytics_mirror` creates, since real data is
Malawi-only and shares the same tables. Re-run `seed_mock_analytics_mirror`
*after* this to layer those synthetic rows back on top (it uses
update_or_create / a source_ref prefix, so it won't disturb real rows).

Usage:
    python manage.py load_csv_snapshot                 # loads all four
    python manage.py load_csv_snapshot client_reach     # loads just one
    python manage.py seed_mock_analytics_mirror         # then, re-add KE/RW fixtures
"""

import csv
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from analytics_mirror.country_codes import to_iso
from analytics_mirror.csv_loader import ColumnSpec, load_csv
from analytics_mirror.seed_data import ensure_tables_exist

DATA_RAW = Path(__file__).resolve().parents[3] / "data" / "raw"

# Plain (unqualified) table names — csv_loader.py and the TRUNCATE below
# both prefix the analytics_mirror schema themselves.
DATASETS = {
    "client_reach": dict(
        csv_path=DATA_RAW / "client_reach.csv",
        table="v_client_reach",
        required=["GL_CLIENT_ID"],
        columns=[
            ColumnSpec("GL_CLIENT_ID", "gl_client_id"),
            ColumnSpec("FULL_NAME", "full_name"),
            ColumnSpec("GENDER", "gender"),
            ColumnSpec("DATE_OF_BIRTH", "date_of_birth"),
            ColumnSpec("COUNTRY", "country_code", to_iso),
            ColumnSpec("PRIMARY_PROGRAM", "primary_program"),
            ColumnSpec("PRIMARY_SITE", "primary_site"),
            ColumnSpec("PRIMARY_SOURCE_SYSTEM", "primary_source_system"),
            ColumnSpec("SOURCE_RECORD_COUNT", "source_record_count"),
            ColumnSpec("IS_SINGLETON", "is_singleton"),
            ColumnSpec("HAS_SALE", "has_sale"),
            ColumnSpec("HAS_LOAN", "has_loan"),
            ColumnSpec("HAS_PURCHASE", "has_purchase"),
            ColumnSpec("IS_MULTI_PROGRAM", "is_multi_program"),
            ColumnSpec("FIRST_SALE_DATE", "first_sale_date"),
            ColumnSpec("LAST_SALE_DATE", "last_sale_date"),
            ColumnSpec("TOTAL_ORDERS", "total_orders"),
            ColumnSpec("PROGRAMS_ON_SALE", "programs_on_sale"),
            ColumnSpec("SEASONS_WITH_OAF", "seasons_with_oaf"),
            ColumnSpec("TOTAL_SALES_LCY", "total_sales_lcy"),
            ColumnSpec("FIRST_LOAN_DATE", "first_loan_date"),
            ColumnSpec("LAST_LOAN_DATE", "last_loan_date"),
            ColumnSpec("TOTAL_LOANS", "total_loans"),
            ColumnSpec("TOTAL_PRINCIPAL_LCY", "total_principal_lcy"),
            ColumnSpec("TOTAL_REPAID_LCY", "total_repaid_lcy"),
            ColumnSpec("TOTAL_OUTSTANDING_LCY", "total_outstanding_lcy"),
            ColumnSpec("REPAYMENT_RATE_PCT", "repayment_rate_pct"),
            ColumnSpec("FIRST_PURCHASE_DATE", "first_purchase_date"),
            ColumnSpec("LAST_PURCHASE_DATE", "last_purchase_date"),
            ColumnSpec("TOTAL_PURCHASES", "total_purchases"),
            ColumnSpec("TOTAL_PURCHASE_LCY", "total_purchase_lcy"),
            ColumnSpec("TOTAL_PROGRAM_VALUE_LCY", "total_program_value_lcy"),
            ColumnSpec("ONBOARDED_ON", "onboarded_on"),
            ColumnSpec("LAST_ACTIVITY_DATE", "last_activity_date"),
            ColumnSpec("DAYS_SALE_TO_LOAN", "days_sale_to_loan"),
            ColumnSpec("DAYS_SINCE_LAST_ACTIVITY", "days_since_last_activity"),
        ],
    ),
    "client_journey": dict(
        csv_path=DATA_RAW / "client_journey.csv",
        table="v_client_journey",
        required=["GL_CLIENT_ID"],
        columns=[
            ColumnSpec("GL_CLIENT_ID", "gl_client_id"),
            ColumnSpec("CLIENT_NAME", "client_name"),
            ColumnSpec("GENDER", "gender"),
            ColumnSpec("COUNTRY", "country_code", to_iso),
            ColumnSpec("PRIMARY_PROGRAM", "primary_program"),
            ColumnSpec("EVENT_TYPE", "event_type"),
            ColumnSpec("PROGRAM", "program"),
            ColumnSpec("EVENT_DATE", "event_date"),
            ColumnSpec("LINE_COUNT", "line_count"),
            ColumnSpec("AMOUNT_LCY", "amount_lcy"),
            ColumnSpec("CURRENCY_CODE", "currency_code"),
            ColumnSpec("IS_CREDIT", "is_credit"),
            ColumnSpec("SOURCE_REF", "source_ref"),
        ],
    ),
    "bridge": dict(
        csv_path=DATA_RAW / "bridge_client_source_ids.csv",
        table="bridge_client_source_ids",
        required=["BRIDGE_ID", "GL_CLIENT_ID"],
        columns=[
            ColumnSpec("BRIDGE_ID", "bridge_id"),
            ColumnSpec("GL_CLIENT_ID", "gl_client_id"),
            ColumnSpec("SOURCE_SYSTEM", "source_system"),
            ColumnSpec("SOURCE_PROGRAM", "source_program"),
            ColumnSpec("SOURCE_CLIENT_ID", "source_client_id"),
            ColumnSpec("SOURCE_COUNTRY", "source_country_code", to_iso),
            ColumnSpec("SOURCE_FIDELITY", "source_fidelity"),
            ColumnSpec("IS_SINGLETON", "is_singleton"),
            ColumnSpec("MATCH_CONFIDENCE", "match_confidence"),
            ColumnSpec("MATCH_METHOD", "match_method"),
            ColumnSpec("LINKED_AT_TS", "linked_at_ts"),
        ],
    ),
    "sf_employees": dict(
        csv_path=DATA_RAW / "successfactors_employees.csv",
        table="sf_employees",
        required=["Email"],
        # Real extract has duplicate emails (re-orgs, multiple department
        # records for one person) — dedupe keeps the most recently updated.
        dedupe_key="Email",
        dedupe_order_by="LastUpdatedDate",
        columns=[
            ColumnSpec("Email", "email"),
            ColumnSpec("FullName", "full_name"),
            ColumnSpec("DepartmentCode", "department_code"),
            ColumnSpec("DepartmentName", "department_name"),
            ColumnSpec("LocationCode", "location_code"),
            ColumnSpec("LocationName", "location_name"),
            ColumnSpec("WorkLocation", "work_location"),
            ColumnSpec("CountryCode", "country_code"),
            ColumnSpec("CountryName", "country_name"),
            ColumnSpec("Active", "is_active"),
            ColumnSpec("LastUpdatedDate", "last_updated_date"),
        ],
    ),
}


def _dedupe_csv(csv_path: Path, key_field: str, order_by: str) -> Path:
    """Keeps one row per `key_field` value — the one with the highest
    `order_by` (a zero-padded 'YYYY-MM-DD HH:MM:SS...' string sorts
    correctly as plain text, no datetime parsing needed). Writes the result
    to a temp file and returns its path."""
    best: dict[str, dict] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            key = row.get(key_field)
            if not key:
                continue
            existing = best.get(key)
            if existing is None or row.get(order_by, "") > existing.get(order_by, ""):
                best[key] = row

    tmp = tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", suffix=".csv", delete=False
    )
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(best.values())
    tmp.close()
    return Path(tmp.name)


class Command(BaseCommand):
    help = "Load real CSV snapshots into the analytics_mirror schema (see ADR-006)."

    def add_arguments(self, parser):
        parser.add_argument(
            "dataset", nargs="?", choices=list(DATASETS), default=None,
            help="Load just this dataset; omit to load all four.",
        )

    def handle(self, *args, **options):
        ensure_tables_exist(stdout=self.stdout)

        targets = [options["dataset"]] if options["dataset"] else list(DATASETS)
        for name in targets:
            spec = DATASETS[name]
            if not spec["csv_path"].exists():
                raise CommandError(f"{spec['csv_path']} not found")

            self.stdout.write(f"Loading {name} from {spec['csv_path'].name}...")
            # Truncate first so re-running is idempotent: PK-bearing tables
            # (client_reach, bridge) would otherwise fail on conflict, and
            # JourneyEvent (no natural key, plain serial id) would silently
            # duplicate every row instead.
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE analytics_mirror.{spec['table']}")

            source_path = spec["csv_path"]
            temp_path = None
            if "dedupe_key" in spec:
                temp_path = _dedupe_csv(source_path, spec["dedupe_key"], spec["dedupe_order_by"])
                source_path = temp_path

            try:
                count, skipped = load_csv(
                    source_path, spec["table"], spec["columns"],
                    required=spec.get("required"), stdout=self.stdout,
                )
            finally:
                if temp_path:
                    temp_path.unlink(missing_ok=True)

            msg = f"Loaded {count:,} rows into {spec['table']}"
            if skipped:
                msg += f" ({skipped:,} skipped — missing a required field)"
            self.stdout.write(self.style.SUCCESS(msg))
