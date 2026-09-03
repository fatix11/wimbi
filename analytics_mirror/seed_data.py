"""
Shared fixture data + seeding logic, used by both the
`seed_mock_analytics_mirror` management command (for local dev) and the
pytest suite (for a hermetic test DB) — one source of truth, not two.

Per ADR-006, these synthetic non-Malawi rows are kept deliberately even
after real (Malawi-only) data is loaded — they're the only way the
cross-country RBAC negative-path tests can prove the country boundary
actually blocks something, until more countries are onboarded for real.
Bridge rows use negative bridge_id values so they can never collide with
real (positive) bridge_id values loaded from CSV.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.db import connection

from .models import (
    BridgeClientSourceId,
    DimCountry,
    DimMCF,
    DimProgram,
    DimSeason,
    DimSystem,
    FarmerReach,
    FOPerformance,
    JourneyEvent,
    LoanPortfolio,
    ProgramSummary,
    RepaymentTransaction,
    SalesLine,
    SFEmployee,
)

FARMERS = [
    dict(gl_client_id="GL-MW-00001", full_name="Grace Banda", country_code="MW",
         primary_site="Lilongwe", primary_program="Core", onboarded_on=date(2022, 9, 12)),
    dict(gl_client_id="GL-MW-00002", full_name="Chikondi Phiri", country_code="MW",
         primary_site="Kasungu", primary_program="Retail", onboarded_on=date(2021, 8, 3)),
    dict(gl_client_id="GL-MW-00003", full_name="Esther Mwale", country_code="MW",
         primary_site="Mzimba", primary_program="Trees", onboarded_on=date(2023, 10, 21)),
    dict(gl_client_id="GL-MW-00004", full_name="Yamikani Zulu", country_code="MW",
         primary_site="Zomba", primary_program="Core", onboarded_on=date(2020, 7, 15)),
    dict(gl_client_id="GL-KE-00001", full_name="Wanjiru Kamau", country_code="KE",
         primary_site="Nakuru", primary_program="Core", onboarded_on=date(2022, 3, 18)),
    dict(gl_client_id="GL-RW-00001", full_name="Uwase Mukamana", country_code="RW",
         primary_site="Musanze", primary_program="Core", onboarded_on=date(2021, 5, 9)),
]

JOURNEY_EVENTS = [
    dict(gl_client_id="GL-MW-00001", event_type="Loan Disbursed", event_date=date(2022, 10, 1),
         program="Core", amount_lcy=Decimal("45000"), currency_code="MWK"),
    dict(gl_client_id="GL-MW-00001", event_type="Sale", event_date=date(2023, 6, 20),
         program="Retail", amount_lcy=Decimal("12000"), currency_code="MWK"),
    dict(gl_client_id="GL-MW-00002", event_type="Loan Disbursed", event_date=date(2021, 9, 5),
         program="Core", amount_lcy=Decimal("38000"), currency_code="MWK"),
    dict(gl_client_id="GL-MW-00002", event_type="Buyback", event_date=date(2022, 7, 18),
         program="Retail", amount_lcy=Decimal("9500"), currency_code="MWK"),
    dict(gl_client_id="GL-MW-00004", event_type="Loan Disbursed", event_date=date(2020, 8, 20),
         program="Core", amount_lcy=Decimal("52000"), currency_code="MWK"),
    dict(gl_client_id="GL-MW-00004", event_type="Sale", event_date=date(2023, 6, 5),
         program="Retail", amount_lcy=Decimal("18500"), currency_code="MWK"),
    dict(gl_client_id="GL-KE-00001", event_type="Loan Disbursed", event_date=date(2022, 4, 2),
         program="Core", amount_lcy=Decimal("15000"), currency_code="KES"),
]

SALES_LINES = [
    dict(gl_client_id="GL-MW-00001", sale_date=date(2023, 6, 20), product_name="Hybrid Maize Seed",
         product_category="Seed", quantity=Decimal("10"), unit_price_lcy=Decimal("1200"),
         total_price_lcy=Decimal("12000"), currency_code="MWK", site="Lilongwe", district="Lilongwe",
         field_officer="Blessings Gondwe", derived_season="LR23"),
    dict(gl_client_id="GL-MW-00004", sale_date=date(2023, 6, 5), product_name="Albizia Lebbeck",
         product_category="Tubes", quantity=Decimal("50"), unit_price_lcy=Decimal("370"),
         total_price_lcy=Decimal("18500"), currency_code="MWK", site="Zomba", district="Zomba",
         field_officer="Blessings Gondwe", derived_season="LR23"),
    # Real Kobo-sourced tree sales can have a null per-line total_price_lcy
    # while the order they belong to still has a real total_order_price_lcy
    # — found live-testing farmer MW-00008737, 2026-09-02 (see
    # _docs/upstream-gaps.md GAP-001). Kept here so the HTML sales table's
    # per-order summary note has a regression case.
    dict(gl_client_id="GL-MW-00003", sale_date=date(2023, 10, 21), product_name="Faidherbia Albida",
         product_category="Tubes", quantity=Decimal("2550"), unit_price_lcy=None,
         total_price_lcy=None, total_order_price_lcy=Decimal("49088"), currency_code="MWK",
         site="Mzimba", district="Mzimba", field_officer="Thembisa Ziwa", source_system="KOBO",
         derived_season="LR23"),
]

# (model, plain unqualified table name) — the plain name is needed
# separately because Meta.db_table is now schema-qualified
# ('analytics_mirror"."v_client_reach'), which Django's own table
# introspection doesn't parse back apart.
MIRROR_MODELS = (
    (FarmerReach, "v_client_reach"),
    (JourneyEvent, "v_client_journey"),
    (BridgeClientSourceId, "bridge_client_source_ids"),
    (SalesLine, "sales_line"),
    (SFEmployee, "sf_employees"),
    # Added 2026-09-03 — empty tables only, no fixture seed data yet.
    # Schemas verified via DESCRIBE VIEW + sample rows (data/raw/snowflake.sql),
    # populated for real via a direct Snowflake-to-Postgres DBeaver transfer
    # rather than the CSV loader this time (see architectural_decisions.md).
    (LoanPortfolio, "loan_portfolio"),
    (ProgramSummary, "program_summary"),
    (RepaymentTransaction, "repayment_transaction"),
    (FOPerformance, "fo_performance"),
    # Added 2026-09-03 — replaces a DBeaver-auto-created uppercase-column
    # version of these same 5 tables (dropped first, see
    # ensure_analytics_tables' docstring update) so Django defines the
    # schema and DBeaver only loads data into it, per the established
    # pattern for every other real table in this mirror.
    (DimCountry, "dim_country"),
    (DimMCF, "dim_mcf"),
    (DimProgram, "dim_program"),
    (DimSeason, "dim_season"),
    (DimSystem, "dim_system"),
)
MIRROR_SCHEMA = "analytics_mirror"


def ensure_tables_exist(stdout=None):
    """Create the mirror tables if they don't already exist. Safe to call
    against a Postgres that real data has already been loaded into — does
    nothing if the tables are already there."""
    with connection.cursor() as cursor:
        # Normally created by infra/postgres/init.sql on first container
        # boot — guarded here too so this works against any fresh Postgres.
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {MIRROR_SCHEMA}")
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            [MIRROR_SCHEMA],
        )
        existing = {row[0] for row in cursor.fetchall()}

    with connection.schema_editor() as editor:
        for model, table_name in MIRROR_MODELS:
            if table_name not in existing:
                editor.create_model(model)
                if stdout:
                    stdout.write(f"Created table {table_name}")


def seed():
    for row in FARMERS:
        FarmerReach.objects.update_or_create(gl_client_id=row["gl_client_id"], defaults=row)

    JourneyEvent.objects.filter(source_ref__startswith="SEED-").delete()
    for i, row in enumerate(JOURNEY_EVENTS):
        JourneyEvent.objects.create(source_ref=f"SEED-{i}", **row)

    SalesLine.objects.filter(source_transaction_id__startswith="SEED-").delete()
    for i, row in enumerate(SALES_LINES):
        SalesLine.objects.create(source_transaction_id=f"SEED-{i}", **row)

    for i, farmer in enumerate(FARMERS):
        BridgeClientSourceId.objects.update_or_create(
            bridge_id=-(i + 1),  # negative — can never collide with real (positive) bridge_ids
            defaults=dict(
                gl_client_id=farmer["gl_client_id"],
                source_system="FINERACT" if farmer["primary_program"] == "Core" else "ODOO",
                source_program=farmer["primary_program"],
                source_client_id=f"SEED-{farmer['gl_client_id']}",
                source_country_code=farmer["country_code"],
                source_fidelity="HIGH",
                is_singleton=True,
                match_confidence=None,
                match_method="SEED",
                linked_at_ts=datetime.now(timezone.utc),
            ),
        )
