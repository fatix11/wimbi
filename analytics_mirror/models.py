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
