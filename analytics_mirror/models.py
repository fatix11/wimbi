"""
Unmanaged models over tables loaded into the `analytics_mirror` Postgres
schema (see _docs/architectural_decisions.md ADR-003, ADR-006). Django
never migrates these — `managed = False` — and each model schema-qualifies
its own `db_table` (Postgres accepts 'schema"."table' as a db_table value —
Django wraps it in one more pair of quotes, producing a valid qualified
identifier) rather than relying on a connection-wide search_path. That
matters: an earlier version used search_path instead, which put analytics_mirror
ahead of public and caused Django's OWN tables (auth, sessions) to be
created inside analytics_mirror — so resetting this schema's shape (`DROP
SCHEMA analytics_mirror CASCADE`) also silently wiped django_session and
friends. Schema-qualifying db_table directly avoids that trap entirely:
Django's own tables always live in the default `public` schema, completely
decoupled from whatever happens to analytics_mirror.

Column names/shapes here are verified against real CSV exports of
V_CLIENT_REACH, V_CLIENT_JOURNEY, and MASTER.BRIDGE_CLIENT_SOURCE_IDS
(2026-09-01) — not guessed. Notably: the real V_CLIENT_REACH has no phone
number column (search-by-phone isn't backed by real data, see farmers/views.py),
and V_CLIENT_JOURNEY's only real event types are Sale / Loan Disbursed /
Buyback — no enrollment, repayment, or tree events exist at this layer.
COUNTRY/SOURCE_COUNTRY arrive as full names ("Malawi") and are normalized
to ISO-2 on load (see country_codes.py) — stored fields are already ISO.
"""

from django.db import models


class FarmerReach(models.Model):
    gl_client_id = models.CharField(max_length=32, primary_key=True)
    full_name = models.CharField(max_length=255, null=True)  # some Kobo-sourced rows lack a name
    gender = models.CharField(max_length=1, null=True)
    date_of_birth = models.DateField(null=True)
    country_code = models.CharField(max_length=8, null=True)
    primary_program = models.CharField(max_length=64, null=True)
    primary_site = models.CharField(max_length=255, null=True)
    primary_source_system = models.CharField(max_length=32, null=True)
    source_record_count = models.IntegerField(null=True)
    is_singleton = models.BooleanField(null=True)

    has_sale = models.BooleanField(null=True)
    has_loan = models.BooleanField(null=True)
    has_purchase = models.BooleanField(null=True)
    is_multi_program = models.BooleanField(null=True)

    first_sale_date = models.DateField(null=True)
    last_sale_date = models.DateField(null=True)
    total_orders = models.IntegerField(null=True)
    programs_on_sale = models.IntegerField(null=True)
    seasons_with_oaf = models.IntegerField(null=True)
    total_sales_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)

    first_loan_date = models.DateField(null=True)
    last_loan_date = models.DateField(null=True)
    total_loans = models.IntegerField(null=True)
    total_principal_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_repaid_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_outstanding_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    repayment_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    first_purchase_date = models.DateField(null=True)
    last_purchase_date = models.DateField(null=True)
    total_purchases = models.IntegerField(null=True)
    total_purchase_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_program_value_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)

    onboarded_on = models.DateField(null=True)
    last_activity_date = models.DateField(null=True)
    days_sale_to_loan = models.IntegerField(null=True)
    days_since_last_activity = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."v_client_reach'


class JourneyEvent(models.Model):
    gl_client_id = models.CharField(max_length=32)
    client_name = models.CharField(max_length=255, null=True)
    gender = models.CharField(max_length=1, null=True)
    country_code = models.CharField(max_length=8, null=True)
    primary_program = models.CharField(max_length=64, null=True)
    event_type = models.CharField(max_length=32)  # "Sale" | "Loan Disbursed" | "Buyback"
    program = models.CharField(max_length=64, null=True)
    event_date = models.DateField()
    line_count = models.IntegerField(null=True)
    amount_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    currency_code = models.CharField(max_length=8, null=True)
    is_credit = models.BooleanField(null=True)
    source_ref = models.CharField(max_length=64, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."v_client_journey'


class BridgeClientSourceId(models.Model):
    MATCH_METHODS = [
        ("SEED", "Seed"),
        ("TIER1_DETERMINISTIC", "Tier 1 — deterministic"),
        ("TIER2_PROBABILISTIC", "Tier 2 — probabilistic"),
    ]

    bridge_id = models.BigIntegerField(primary_key=True)
    gl_client_id = models.CharField(max_length=32)
    source_system = models.CharField(max_length=32)
    source_program = models.CharField(max_length=64, null=True)
    source_client_id = models.CharField(max_length=128)
    source_country_code = models.CharField(max_length=8)
    source_fidelity = models.CharField(max_length=16)
    is_singleton = models.BooleanField()
    match_confidence = models.FloatField(null=True)
    match_method = models.CharField(max_length=32, choices=MATCH_METHODS)
    linked_at_ts = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."bridge_client_source_ids'


class SalesLine(models.Model):
    """
    Mirrors V_SALES_DETAIL (verified against a real 5M-row/12.78M Malawi
    extract, 2026-09-01 — see ADR-007). Line-item grain, not client grain:
    a farmer's single "Sale" journey event (from V_CLIENT_JOURNEY) can
    correspond to several SalesLine rows (one per product on the order),
    so this is deliberately its own model, not a 1:1 join onto JourneyEvent.
    Enriches the Journey Timeline with product/quantity/field-officer/exact
    location detail that V_CLIENT_JOURNEY doesn't carry.
    """

    id = models.BigAutoField(primary_key=True)
    gl_client_id = models.CharField(max_length=32, db_index=True)
    client_name = models.CharField(max_length=255, null=True)
    gender = models.CharField(max_length=1, null=True)
    client_primary_program = models.CharField(max_length=64, null=True)

    sale_date = models.DateField(null=True)
    sale_year = models.IntegerField(null=True)
    sale_quarter = models.CharField(max_length=8, null=True)
    sale_month = models.CharField(max_length=16, null=True)
    year_month = models.CharField(max_length=8, null=True)
    season = models.CharField(max_length=32, null=True)
    derived_season = models.CharField(max_length=32, null=True)

    country_code = models.CharField(max_length=8, null=True)
    region = models.CharField(max_length=128, null=True)
    district = models.CharField(max_length=128, null=True)
    sector = models.CharField(max_length=128, null=True)
    site = models.CharField(max_length=255, null=True)
    loc_type = models.CharField(max_length=32, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    loc_parents = models.CharField(max_length=255, null=True)

    program = models.CharField(max_length=64, null=True)
    source_system = models.CharField(max_length=32, null=True)
    sale_channel = models.CharField(max_length=64, null=True)
    order_type = models.CharField(max_length=64, null=True)
    payment_type = models.CharField(max_length=64, null=True)
    is_credit = models.BooleanField(null=True)
    fulfillment_status = models.CharField(max_length=32, null=True)

    product_name = models.CharField(max_length=255, null=True)
    product_category = models.CharField(max_length=128, null=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    field_officer = models.CharField(max_length=255, null=True)
    shopkeeper = models.CharField(max_length=255, null=True)
    nursery_manager = models.CharField(max_length=255, null=True)

    unit_price_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_price_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_order_price_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    total_price_usd = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    currency_code = models.CharField(max_length=8, null=True)
    usd_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    sap_usd_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    rate_exact_match = models.BooleanField(null=True)
    revenue_lcy = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    revenue_usd = models.DecimalField(max_digits=16, decimal_places=2, null=True)

    location_key = models.CharField(max_length=64, null=True)
    product_key = models.CharField(max_length=64, null=True)
    field_officer_key = models.CharField(max_length=64, null=True)
    shopkeeper_key = models.CharField(max_length=64, null=True)
    nursery_mgr_key = models.CharField(max_length=64, null=True)

    source_transaction_id = models.CharField(max_length=64, null=True)
    source_order_id = models.CharField(max_length=64, null=True)
    source_loan_id = models.CharField(max_length=64, null=True)

    created_at = models.DateTimeField(null=True)
    fulfilled_at = models.DateTimeField(null=True)
    loaded_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."sales_line'


class SFEmployee(models.Model):
    """
    Loaded from a SuccessFactors extract (see ADR-006) — role-to-department
    mapping for RBAC is a deliberately open question, not encoded here.
    CountryCode arrives with some non-standard values (e.g. "RW-TBR",
    "ETH") — stored as-is, normalized at the point RBAC actually uses it.
    """

    email = models.EmailField(primary_key=True)
    full_name = models.CharField(max_length=255)
    department_code = models.CharField(max_length=32, null=True)
    department_name = models.CharField(max_length=128, null=True)
    location_code = models.CharField(max_length=32, null=True)
    location_name = models.CharField(max_length=128, null=True)
    work_location = models.CharField(max_length=128, null=True)
    country_code = models.CharField(max_length=8, null=True)
    country_name = models.CharField(max_length=64, null=True)
    is_active = models.BooleanField(default=True)
    last_updated_date = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."sf_employees'


class LoanPortfolio(models.Model):
    """
    Mirrors V_LOAN_PORTFOLIO (schema verified 2026-09-03 via `DESCRIBE VIEW`
    + sample rows, see data/raw/snowflake.sql — 410,783 rows, Malawi).
    Loan grain, not client grain — one row per loan, so a farmer with
    multiple loans has multiple rows (matches SalesLine's line-grain
    pattern rather than FarmerReach's one-row-per-client pattern).
    COUNTRY arrives as a full name ("Malawi"), same as other mirrored
    views — normalize to ISO-2 at the point RBAC/scoping uses it, not here.
    No natural single-column key looked reliable across the whole view in
    the sample, so this uses an implicit auto `id` PK like JourneyEvent,
    rather than trusting SOURCE_LOAN_ID.
    """

    gl_client_id = models.CharField(max_length=32, db_index=True)
    client_name = models.CharField(max_length=200, null=True)
    gender = models.CharField(max_length=5, null=True)
    primary_program = models.CharField(max_length=64, null=True)

    disbursement_date = models.DateField(null=True)
    disbursement_year = models.IntegerField(null=True)
    disbursement_quarter = models.CharField(max_length=16, null=True)
    disbursement_month = models.CharField(max_length=16, null=True)
    year_month = models.CharField(max_length=16, null=True)

    country = models.CharField(max_length=64, null=True)
    region = models.CharField(max_length=128, null=True)
    district = models.CharField(max_length=128, null=True)
    sector = models.CharField(max_length=128, null=True)
    site = models.CharField(max_length=255, null=True)

    source_loan_id = models.BigIntegerField(null=True)
    loan_account_number = models.CharField(max_length=64, null=True)
    loan_name = models.CharField(max_length=255, null=True)
    loan_type = models.CharField(max_length=255, null=True)
    loan_status = models.CharField(max_length=64, null=True)
    is_disbursed = models.BooleanField(null=True)
    is_closed = models.BooleanField(null=True)
    group_name = models.CharField(max_length=255, null=True)
    source_product_id = models.BigIntegerField(null=True)
    is_at_risk = models.BooleanField(null=True)

    principal_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    principal_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    repaid_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    repaid_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    outstanding_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    outstanding_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_repaid_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    repayment_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    currency_code = models.CharField(max_length=8, null=True)
    usd_exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True)

    approved_at = models.DateField(null=True)
    disbursed_at = models.DateField(null=True)
    matured_at = models.DateField(null=True)
    days_past_maturity = models.IntegerField(null=True)  # negative = not yet due
    loaded_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."loan_portfolio'


class ProgramSummary(models.Model):
    """
    Mirrors V_PROGRAM_SUMMARY (schema verified 2026-09-03, 62 rows —
    one row per (year_month, country, program), already pre-aggregated.
    Feeds Feature 5 (Program & Portfolio Dashboards). Per ADR-007, this
    view is consumed as-is rather than re-derived from raw FACT tables.
    """

    year_month = models.CharField(max_length=16, null=True)
    year = models.IntegerField(null=True)
    month_name = models.CharField(max_length=16, null=True)
    month = models.IntegerField(null=True)
    country = models.CharField(max_length=64, null=True)
    program = models.CharField(max_length=16, null=True)
    program_oaf_eq = models.CharField(max_length=100, null=True)
    program_local_name = models.CharField(max_length=100, null=True)
    maturity_score = models.IntegerField(null=True)
    is_seasonal = models.BooleanField(null=True)
    has_groups = models.BooleanField(null=True)
    # MCF_* flags: program-classification booleans as named upstream —
    # kept opaque here rather than guessed at, ask the data team if the
    # acronym expansion matters for a feature.
    mcf_pa = models.BooleanField(null=True)
    mcf_in = models.BooleanField(null=True)
    mcf_sh = models.BooleanField(null=True)
    mcf_ft = models.BooleanField(null=True)
    mcf_tt = models.BooleanField(null=True)
    mcf_fvc = models.BooleanField(null=True)
    mcf_pes = models.BooleanField(null=True)

    unique_clients = models.IntegerField(null=True)
    total_orders = models.IntegerField(null=True)
    total_sale_lines = models.IntegerField(null=True)
    total_sales_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_sales_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    currency_code = models.CharField(max_length=8, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."program_summary'


class RepaymentTransaction(models.Model):
    """
    Mirrors V_REPAYMENT_ANALYSIS (schema verified 2026-09-03 — 4,321,246
    rows, the largest of the four newly-added views, comparable in scale
    to V_SALES_DETAIL's 12.78M). Transaction grain. Notable: REPAYMENT_PHONE
    is a real column here (e.g. "+265888354435") even though V_CLIENT_REACH
    has no phone column at all — worth revisiting Feature 1's deferred
    "search by phone number" story against this view specifically before
    concluding it's fully blocked (see ADR-006).
    """

    gl_client_id = models.CharField(max_length=32, db_index=True)
    client_name = models.CharField(max_length=200, null=True)
    gender = models.CharField(max_length=5, null=True)
    primary_program = models.CharField(max_length=64, null=True)

    transaction_date = models.DateField(null=True)
    year = models.IntegerField(null=True)
    quarter = models.CharField(max_length=16, null=True)
    month_name = models.CharField(max_length=16, null=True)
    year_month = models.CharField(max_length=16, null=True)

    country = models.CharField(max_length=64, null=True)
    region = models.CharField(max_length=128, null=True)
    district = models.CharField(max_length=128, null=True)
    sector = models.CharField(max_length=128, null=True)
    site = models.CharField(max_length=255, null=True)

    account_type = models.CharField(max_length=16, null=True)
    transaction_type = models.CharField(max_length=255, null=True)
    payment_method = models.CharField(max_length=255, null=True)
    payment_type_raw = models.CharField(max_length=255, null=True)

    amount_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)  # can be negative (adjustments)
    cumulative_amount_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    account_principal_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    payment_direction = models.CharField(max_length=16, null=True)  # e.g. "Inflow" / "Adjustment"

    source_transaction_id = models.BigIntegerField(null=True)
    source_loan_id = models.BigIntegerField(null=True)
    account_number = models.CharField(max_length=64, null=True)
    # 128, not 64 — real receipt numbers run up to 70 chars (Odoo overpayment
    # reversal receipts embed a long structured reference).
    receipt_number = models.CharField(max_length=128, null=True)
    repayment_phone = models.CharField(max_length=32, null=True)
    loaded_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."repayment_transaction'


class FOPerformance(models.Model):
    """
    Mirrors V_FO_PERFORMANCE (schema verified 2026-09-03 — 560 rows, one
    per field officer, already pre-aggregated). Feeds Feature 5's FO
    performance story. FO_KEY (a stable hash-like id) is a genuine
    per-row-unique natural key here, unlike the other three new views, so
    it's used directly as the primary key. Real gap observed in sample
    data: FO_ID is blank even when FO_KEY/FO_NAME are populated — don't
    rely on it. Loan-related aggregates (loan_clients, total_loans, etc.)
    are null rather than 0 for an FO with no loan clients — same for the
    sale-related aggregates when an FO has no sale clients — don't coalesce
    to 0 without checking which side is actually null per row.
    """

    fo_key = models.CharField(max_length=32, primary_key=True)
    fo_name = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=64, null=True)
    fo_id = models.CharField(max_length=64, null=True)

    unique_clients = models.IntegerField(null=True)
    loan_clients = models.IntegerField(null=True)
    total_loans = models.IntegerField(null=True)
    total_principal_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_repaid_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_outstanding_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    portfolio_repayment_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    at_risk_loans = models.IntegerField(null=True)
    at_risk_outstanding_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    sale_clients = models.IntegerField(null=True)
    total_orders = models.IntegerField(null=True)
    total_sales_lcy = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    programs_covered = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."fo_performance'


class DimCountry(models.Model):
    """Mirrors DIM_COUNTRY (schema verified 2026-09-03 via direct Postgres
    introspection after a DBeaver DB-to-DB transfer — real columns are
    richer than the sample dims/Countries.csv, which lacks SAP_COUNTRY_ID
    and REGION). Superseded a DBeaver-auto-created uppercase-column
    version of this table — see ADR-010-adjacent lesson in
    architectural_decisions.md: Django defines the schema, DBeaver only
    loads data into it."""

    country_id = models.IntegerField(primary_key=True)
    country_name = models.CharField(max_length=64, null=True)
    country_code = models.CharField(max_length=8, null=True)
    country_code3 = models.CharField(max_length=8, null=True)
    currency_name = models.CharField(max_length=64, null=True)
    currency_code = models.CharField(max_length=8, null=True)
    odoo_company_id = models.IntegerField(null=True)
    fineract_country_id = models.IntegerField(null=True)
    sap_country_id = models.IntegerField(null=True)
    region = models.CharField(max_length=32, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_country'


class DimMCF(models.Model):
    """Mirrors DIM_MCF — the 7 Market/Client Feature categories (Precision
    Agriculture, Insurance, Soil Health, Fruit Trees, Timber Trees, Fruit
    Value Chain, PES) referenced as boolean flags on DimProgram."""

    mcf_id = models.IntegerField(primary_key=True)
    mcf_abbrev = models.CharField(max_length=16, null=True)
    mcf_name = models.CharField(max_length=128, null=True)
    description = models.CharField(max_length=500, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_mcf'


class DimProgram(models.Model):
    """Mirrors DIM_PROGRAM — every real country+program combination (29
    rows). `cross_program_id_type` is the real column behind the bulk
    uploader's scheme-agnostic client-identity design (see
    _docs/bulk-uploader.md): NID/APPSHEET_ID/ACCOUNTNUMBER/null, varying
    by country — never hard-code one scheme. `phone_quality` is a real,
    already-tracked per-country/program data-quality signal, relevant to
    the deferred phone-search story (ADR-006) and GAP-001 in
    upstream-gaps.md."""

    program_id = models.IntegerField(primary_key=True)
    country_code = models.CharField(max_length=8, null=True)
    country_name = models.CharField(max_length=64, null=True)
    program_local_name = models.CharField(max_length=100, null=True)
    program_oaf_eq = models.CharField(max_length=100, null=True)
    maturity_score = models.IntegerField(null=True)
    is_seasonal = models.BooleanField(null=True)
    has_groups = models.BooleanField(null=True)
    cross_program_id_type = models.CharField(max_length=32, null=True)
    phone_quality = models.CharField(max_length=32, null=True)
    client_definition = models.CharField(max_length=500, null=True)
    mcf_pa = models.BooleanField(null=True)
    mcf_in = models.BooleanField(null=True)
    mcf_sh = models.BooleanField(null=True)
    mcf_ft = models.BooleanField(null=True)
    mcf_tt = models.BooleanField(null=True)
    mcf_fvc = models.BooleanField(null=True)
    mcf_pes = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_program'


class DimSeason(models.Model):
    """Mirrors DIM_SEASON (171 rows) — real per-country season definitions
    with actual date ranges, feeding V_SALES_DETAIL's derived_season and
    any season-scoped reporting."""

    season_id = models.IntegerField(primary_key=True)
    country_code = models.CharField(max_length=8, null=True)
    season_name = models.CharField(max_length=32, null=True)
    local_name = models.CharField(max_length=32, null=True)
    rainfall_type = models.CharField(max_length=16, null=True)
    season_label = models.CharField(max_length=32, null=True)
    season_year = models.IntegerField(null=True)
    season_year_label = models.CharField(max_length=16, null=True)
    start_month = models.IntegerField(null=True)
    end_month = models.IntegerField(null=True)
    crosses_year = models.BooleanField(null=True)
    is_primary = models.BooleanField(null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_season'


class DimSystem(models.Model):
    """Mirrors DIM_SYSTEM (218 rows) — every source system feeding each
    country+program, e.g. a single Malawi Core program is fed by 9+
    systems (Fieldsmart, Fineract, Odoo, USSD, KissFlow, Zendesk, MNOs,
    Commcare, KOBO). Real evidence for why the bulk uploader's
    source-agnostic design is solving a real problem, not over-engineering
    (see _docs/bulk-uploader.md)."""

    system_id = models.IntegerField(primary_key=True)
    country_code = models.CharField(max_length=8, null=True)
    country_name = models.CharField(max_length=64, null=True)
    program_local_name = models.CharField(max_length=100, null=True)
    program_canonical = models.CharField(max_length=100, null=True)
    system_name = models.CharField(max_length=100, null=True)
    client_definition = models.CharField(max_length=500, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_system'


class DimClient(models.Model):
    """Mirrors DIM_CLIENT (1,305,491 rows, verified unique on gl_client_id).
    Notable: has a real PHONE column, unlike V_CLIENT_REACH which has none
    at all (see FarmerReach's docstring) - worth revisiting the deferred
    search-by-phone story (ADR-006) against this table specifically before
    assuming it's still blocked. Also carries COUNTRY and COUNTRY_CODE as
    separate real columns already, so no ISO normalization needed here
    (unlike the fields that derive country_code from a full-name COUNTRY
    only, via analytics_mirror.to_iso_country())."""

    gl_client_id = models.CharField(max_length=32, primary_key=True)
    cluster_seq = models.IntegerField(null=True)
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    full_name = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=32, null=True)
    national_id = models.CharField(max_length=64, null=True)
    account_number = models.CharField(max_length=64, null=True)
    fineract_id = models.CharField(max_length=64, null=True)
    gender = models.CharField(max_length=5, null=True)
    date_of_birth = models.DateField(null=True)
    country = models.CharField(max_length=64, null=True)
    country_code = models.CharField(max_length=8, null=True)
    primary_source_system = models.CharField(max_length=32, null=True)
    primary_program = models.CharField(max_length=64, null=True)
    primary_site = models.CharField(max_length=255, null=True)
    source_record_count = models.IntegerField(null=True)
    is_singleton = models.BooleanField(null=True)
    is_reviewed = models.BooleanField(null=True)
    is_active = models.BooleanField(null=True)
    created_ts = models.DateTimeField(null=True)
    last_updated_ts = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_client'


class DimDate(models.Model):
    """Mirrors DIM_DATE (10,957 rows) - a standard calendar date dimension,
    date_key as the real surrogate PK (verified unique)."""

    date_key = models.IntegerField(primary_key=True)
    date = models.DateField(null=True)
    year = models.IntegerField(null=True)
    quarter = models.IntegerField(null=True)
    quarter_name = models.CharField(max_length=16, null=True)
    month = models.IntegerField(null=True)
    month_short = models.CharField(max_length=8, null=True)
    month_name = models.CharField(max_length=16, null=True)
    year_month_key = models.IntegerField(null=True)
    year_month = models.CharField(max_length=16, null=True)
    week_of_year = models.IntegerField(null=True)
    day_of_year = models.IntegerField(null=True)
    day_of_month = models.IntegerField(null=True)
    day_of_week = models.IntegerField(null=True)
    day_short = models.CharField(max_length=8, null=True)
    day_name = models.CharField(max_length=16, null=True)
    is_weekend = models.BooleanField(null=True)
    is_weekday = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_date'


class DimExchangeRate(models.Model):
    """Mirrors DIM_EXCHANGE_RATE (5,040 rows) - monthly per-country/currency
    exchange rates. No single-column natural key in the real data (country
    + year_month + target_currency together look like the natural
    composite) - id is a ROW_NUMBER() surrogate in the view, same pattern
    as the other keyless mirror tables (see analytics_mirror_views.sql's
    own note on that)."""

    country_id = models.IntegerField(null=True)
    country_code = models.CharField(max_length=8, null=True)
    year_month = models.CharField(max_length=16, null=True)
    target_currency = models.CharField(max_length=8, null=True)
    rate_exact = models.FloatField(null=True)
    usd_rate = models.FloatField(null=True)
    is_exact_match = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_exchange_rate'


class DimLocation(models.Model):
    """Mirrors DIM_LOCATION (2,026 rows, verified unique on location_key)
    - the real target of SalesLine's location_key. Carries real decimal
    LATITUDE/LONGITUDE (verified against sample rows, e.g. -15.434839,
    35.5545106) - unlike V_SALES_DETAIL's own bigint-typed lat/long, which
    sales_line's view flagged as likely truncating real GPS precision.
    This table is probably the better source for real map coordinates -
    worth switching to before trusting sales_line's own lat/long for
    display."""

    location_key = models.CharField(max_length=64, primary_key=True)
    country = models.CharField(max_length=64, null=True)
    region = models.CharField(max_length=128, null=True)
    district = models.CharField(max_length=128, null=True)
    sector = models.CharField(max_length=128, null=True)
    lowest_loc = models.CharField(max_length=255, null=True)
    loc_type = models.CharField(max_length=32, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    geopoint = models.CharField(max_length=255, null=True)
    loc_parents = models.CharField(max_length=255, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_location'


class DimPeople(models.Model):
    """Mirrors DIM_PEOPLE (1,514 rows, verified unique on people_key) - the
    real target of SalesLine's field_officer_key/shopkeeper_key/
    nursery_mgr_key. Distinct from SFEmployee: this is the broader people
    dimension across all source systems (Fineract, Odoo, etc.), not just
    SuccessFactors staff - sf_employee_id/sf_payroll_id link the two where
    applicable."""

    people_key = models.CharField(max_length=64, primary_key=True)
    full_name = models.CharField(max_length=255, null=True)
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    is_fo = models.BooleanField(null=True)
    is_shopkeeper = models.BooleanField(null=True)
    is_nursery_manager = models.BooleanField(null=True)
    division = models.CharField(max_length=128, null=True)
    source_system = models.CharField(max_length=32, null=True)
    country = models.CharField(max_length=64, null=True)
    email = models.EmailField(null=True)
    fo_id = models.CharField(max_length=64, null=True)
    location_id = models.CharField(max_length=64, null=True)
    station_id = models.CharField(max_length=64, null=True)
    sf_employee_id = models.CharField(max_length=64, null=True)
    sf_payroll_id = models.CharField(max_length=64, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_people'


class DimProduct(models.Model):
    """Mirrors DIM_PRODUCT (143 rows, verified unique on product_key) - the
    real target of SalesLine's product_key."""

    product_key = models.CharField(max_length=64, primary_key=True)
    product_name = models.CharField(max_length=255, null=True)
    source_product_id = models.CharField(max_length=64, null=True)
    source_system = models.CharField(max_length=32, null=True)

    class Meta:
        managed = False
        db_table = 'analytics_mirror"."dim_product'
