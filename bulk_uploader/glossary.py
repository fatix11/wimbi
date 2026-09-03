"""
The canonical variable glossary uploaded columns get mapped to.

Rewritten 2026-09-03 to use the REAL warehouse column names, read directly
from the pipeline DDL in entities/database/ (dimensions.sql, facts.sql,
master_procedure.sql) — not the earlier synthesis from
new_variable_mapping.csv (a design document, not the built system) or the
Data Collection Template (natural-language names like "served_by" that
turned out to collapse two or three genuinely different real columns into
one, e.g. field_officer/shopkeeper/nursery_manager). Adopting the
warehouse's own names means a mapped upload needs no translation step when
it's eventually promoted into ANALYTICS.SOURCES (v1.2+) — see
_docs/bulk-uploader.md.

Two independent classifications on each Variable, easy to conflate but
serving different purposes:
  * `required` — the strict pass/fail quality gate (required_variables()).
    Deliberately narrow: a client identifier and a per-entity lineage id,
    exactly matching what the real DDL actually enforces (V_SAVINGS has no
    district at all; DIM_LOCATION tolerates partial hierarchy throughout).
    Unaffected by `tier` below — broadening this would start rejecting real
    Kobo Trees data outright, which has no pricing at all (GAP-001).
  * `tier` — "required" / "nice_to_have" / "optional", a business-
    completeness scorecard for the mapping-progress display, restoring the
    Data Collection Template's original tiers (Required-11/Nice-to-have-11/
    Optional-15) onto the real DWH names wherever an equivalent exists. A
    variable can be tier="required" (e.g. Sale's product_name/quantity —
    what a *good* distribution file should have) while required=False (the
    save gate doesn't reject a file missing it, since real data sometimes
    genuinely can't supply it).

Country/Program/Season/Location type stay at the funnel (per-upload) level
rather than per-row, even though DIM_CLIENT/the FACT tables/DIM_LOCATION
carry them per row — the pragmatic simplification that a single upload is
virtually always one country/program/season/place-type, matching how OAF's
own live Google Form already works.

Kept as a plain Python module rather than a DB-backed, admin-editable
model — see the module's original docstring reasoning, unchanged: only
this repo edits it today.
"""

from dataclasses import dataclass, field

TIER_REQUIRED = "required"
TIER_NICE_TO_HAVE = "nice_to_have"
TIER_OPTIONAL = "optional"
TIER_LABELS = {TIER_REQUIRED: "Required", TIER_NICE_TO_HAVE: "Nice-to-have", TIER_OPTIONAL: "Optional"}


@dataclass(frozen=True)
class Variable:
    name: str
    label: str
    description: str
    required: bool = False  # the strict save/quality-gate flag — see module docstring
    tier: str = TIER_OPTIONAL  # the business-completeness scorecard tier — independent of `required`


@dataclass(frozen=True)
class Entity:
    key: str
    name: str
    feeds: str
    variables: list["Variable"] = field(default_factory=list)


# --- Client — from ANALYTICS.MASTER.DIM_CLIENT + BRIDGE_CLIENT_SOURCE_IDS ---
# DIM_CLIENT has THREE separate named identity columns, never a generic
# type+value pair — confirmed straight from the DDL. An upload supplies
# whichever it has; none is universally required, since dims/Programs.csv
# shows the identifier scheme genuinely varies by country (NID/APPSHEET_ID/
# ACCOUNTNUMBER/none).
CLIENT_IDENTITY = [
    Variable("national_id", "National ID", "Government-issued ID number, where the country's ID system is used for matching (e.g. Rwanda, Kenya)", tier=TIER_OPTIONAL),
    Variable("account_number", "Account number", "A general client-facing account/farmer code used within the source program", tier=TIER_NICE_TO_HAVE),
    Variable("fineract_id", "Fineract ID", "The client's id in Fineract (OAF's credit/loan system), if this record already exists there", tier=TIER_OPTIONAL),
]

CLIENT_CORE = [
    Variable("full_name", "Full name", "Required if first/last name aren't captured separately", required=True, tier=TIER_REQUIRED),
    Variable("first_name", "First name", "Ideally as it appears on an identity document", tier=TIER_NICE_TO_HAVE),
    Variable("last_name", "Last name", "Ideally as it appears on an identity document", tier=TIER_NICE_TO_HAVE),
    Variable("gender", "Gender", "M or F", tier=TIER_NICE_TO_HAVE),
    Variable("date_of_birth", "Date of birth", "Full date. If only a birth year is known, use 1 January of that year as a placeholder — real Kobo exports already do this", tier=TIER_NICE_TO_HAVE),
    Variable("phone", "Phone", "With country code if available", tier=TIER_NICE_TO_HAVE),
    Variable("primary_site", "Primary site", "The client's main site/shop/nursery", tier=TIER_OPTIONAL),
    Variable("primary_source_system", "Primary source system", "The system this client is most associated with, e.g. KOBO, ODOO, FINERACT", tier=TIER_OPTIONAL),
    Variable("source_system", "Source system", "Which system THIS record came from — required so it can be traced and matched against other systems", required=True, tier=TIER_REQUIRED),
    Variable("source_client_id", "Source client ID", "This record's own unique identifier in its source system — the anchor MASTER uses to match this record against others", required=True, tier=TIER_REQUIRED),
]

# Real place-types a transaction can happen at — per your own note, this is
# important enough to know that it's now a funnel question (LOCATION_TYPES
# below), not a per-row mapped column, matching how Country/Program already
# work: a single upload is virtually always one place-type throughout.
# "Other" isn't a fixed 6th value here — it's handled the same way as
# Program/Source system (views._resolve_other): a free-text escape hatch
# whose typed value becomes the real stored location_type, not a literal
# "Other" string.
LOCATION_TYPES = ["Nursery", "Site", "Shop", "Warehouse", "Online"]

ENTITIES: dict[str, Entity] = {
    "client": Entity(
        key="client",
        name="Client",
        feeds="MASTER.DIM_CLIENT",
        variables=CLIENT_CORE + CLIENT_IDENTITY,
    ),
    "location": Entity(
        key="location",
        name="Location",
        feeds="DIMENSIONS.DIM_LOCATION",
        variables=[
            # Named by channel rather than one generic "Lowest location" —
            # mirrors DIM_PEOPLE's own field_officer/shopkeeper/
            # nursery_manager split (2026-09-03, on request): a single
            # dataset can genuinely carry more than one of these at once
            # (e.g. a file spanning both Site and Shop transactions), so a
            # mapper needs to send each to its own column rather than one
            # shared field only one channel's column could occupy at a time.
            # Which of these IS DIM_LOCATION's lowest_loc for a given row is
            # decided by the funnel's location_type answer, not re-asked
            # here — a promotion-time (v1.2+) concern, not a v1.1 mapping
            # ambiguity. Not tier=required for the same reason the three
            # People roles aren't — only the channel(s) actually present in
            # a given file apply.
            Variable("nursery", "Nursery", "Nursery name/code — for Kobo Trees distributions", tier=TIER_NICE_TO_HAVE),
            Variable("site", "Site", "Site name/code — for Fineract-sourced loans/savings", tier=TIER_NICE_TO_HAVE),
            Variable("shop", "Shop", "Shop name/code — for Odoo Retail sales", tier=TIER_NICE_TO_HAVE),
            Variable("warehouse", "Warehouse", "Warehouse name/code, where applicable", tier=TIER_NICE_TO_HAVE),
            Variable("region", "Region", "Highest level below country", tier=TIER_OPTIONAL),
            Variable("district", "District", "Below region", tier=TIER_OPTIONAL),
            Variable("sector", "Sector", "Below district — this is the level Malawi's Trees program calls \"EPA\" (Extension Planning Area)", tier=TIER_OPTIONAL),
            # village/cell/source_location_id: NOT yet real DIM_LOCATION
            # columns (confirmed 2026-09-03 against the real DDL — it has
            # exactly 11 fields, none of these three). Added ahead of the
            # warehouse on your own call, to be added to DIM_LOCATION for
            # real later — tracked as GAP-004 in _docs/upstream-gaps.md so
            # it isn't forgotten.
            Variable("village", "Village", "Below sector — not a real DIM_LOCATION column yet (see upstream-gaps.md GAP-004)", tier=TIER_OPTIONAL),
            Variable("cell", "Cell", "Below village — not a real DIM_LOCATION column yet (see upstream-gaps.md GAP-004)", tier=TIER_OPTIONAL),
            Variable("source_location_id", "Source location ID", "The lowest location's own id in the source system, e.g. a Kobo NURSERY_ID — not a real DIM_LOCATION column yet (see upstream-gaps.md GAP-004)", tier=TIER_NICE_TO_HAVE),
            Variable("latitude", "Latitude", "Only ever populated for Kobo nursery data today", tier=TIER_OPTIONAL),
            Variable("longitude", "Longitude", "Only ever populated for Kobo nursery data today", tier=TIER_OPTIONAL),
            Variable("geopoint", "Geopoint", "Raw geopoint string, if Kobo captured one", tier=TIER_OPTIONAL),
        ],
    ),
    "product": Entity(
        key="product",
        name="Product",
        feeds="DIMENSIONS.DIM_PRODUCT",
        variables=[
            Variable("product_name", "Product name", "As recorded by the source system", required=True, tier=TIER_REQUIRED),
            Variable("source_product_id", "Source product ID", "The product's id in the source system — Odoo only; Kobo/Sheets products are matched by name instead", tier=TIER_NICE_TO_HAVE),
            Variable("source_system", "Source system", "Which system this product record came from", tier=TIER_OPTIONAL),
        ],
    ),
    "sale": Entity(
        key="sale",
        name="Sale",
        feeds="FACTS.FACT_SALE",
        variables=[
            Variable("source_transaction_id", "Transaction ID", "The smallest unit — one per product per order per client. Required for lineage", required=True, tier=TIER_REQUIRED),
            Variable("source_order_id", "Order ID", "Groups several transaction lines into one order, if the sale had multiple products", tier=TIER_OPTIONAL),
            Variable("source_client_id", "Client ID", "Which client this line belongs to, in the source system", tier=TIER_NICE_TO_HAVE),
            Variable("source_loan_id", "Loan ID", "If this sale was made on credit, the loan it's tied to", tier=TIER_OPTIONAL),
            Variable("product_name", "Product name", "What was sold on this line", tier=TIER_REQUIRED),
            Variable("product_category", "Product category", "A transaction-level attribute in the real warehouse, not a product master attribute — Kobo in particular varies category by transaction", tier=TIER_OPTIONAL),
            Variable("loan_product_name", "Loan product name", "The loan product used, if this sale was financed on credit", tier=TIER_OPTIONAL),
            Variable("order_type", "Order type", "", tier=TIER_OPTIONAL),
            Variable("payment_type", "Payment type", "How payment was collected", tier=TIER_NICE_TO_HAVE),
            Variable("sale_channel", "Sale channel", "How the sale was transacted, e.g. POS, field distribution", tier=TIER_OPTIONAL),
            Variable("fulfillment_status", "Fulfillment status", "Whether the order has been delivered yet", tier=TIER_OPTIONAL),
            Variable("is_credit", "Is credit", "Whether this was sold on credit rather than cash", tier=TIER_OPTIONAL),
            Variable("quantity", "Quantity", "Quantity of the product on this line", tier=TIER_REQUIRED),
            Variable("unit_price_lcy", "Unit price (LCY)", "Price per unit, local currency", tier=TIER_REQUIRED),
            Variable("total_price_lcy", "Total price, this line (LCY)", "quantity × unit price — some sources (Kobo) don't track this per line, only per order", tier=TIER_REQUIRED),
            Variable("total_order_price_lcy", "Total price, whole order (LCY)", "Repeated across every line of the same order — don't sum across lines", tier=TIER_OPTIONAL),
            Variable("currency_code", "Currency", "", tier=TIER_OPTIONAL),
            Variable("created_at", "Created at", "When the order was placed/recorded", tier=TIER_NICE_TO_HAVE),
            Variable("fulfilled_at", "Fulfilled at", "When the product was actually delivered", tier=TIER_OPTIONAL),
            # Who served this sale lives under People now, not here — see
            # DIM_PEOPLE's own real sourcing (field_officer/shopkeeper/
            # nursery_manager are staff roles, not sale attributes).
            Variable(
                "pivoted_product", "Pivoted product quantity",
                "For files with one column per product (e.g. a Kobo distribution sheet with A_LEBBECK_SEEDLINGS, "
                "F_ALBIDA_SEEDLINGS... as separate columns) — map every such column to this. Each one's own column "
                "name is kept as the implied product name, and all of them are preserved together rather than one "
                "overwriting another; the actual unpivot into one row per product happens later, when the real "
                "SOURCES view for this dataset gets built (see _docs/bulk-uploader.md's unpivot decision).",
                tier=TIER_OPTIONAL,
            ),
        ],
    ),
    "purchase": Entity(
        key="purchase",
        name="Purchase (buyback)",
        feeds="FACTS.FACT_PURCHASE",
        variables=[
            Variable("source_purchase_id", "Purchase ID", "Required for lineage", required=True, tier=TIER_REQUIRED),
            Variable("source_client_id", "Client ID", "Which farmer this buyback is from", tier=TIER_NICE_TO_HAVE),
            Variable("farmer_name", "Farmer name", "Kept as free text — buyback sheets don't record a field officer, so there's no third party to resolve this against", tier=TIER_NICE_TO_HAVE),
            Variable("group_name", "Group name", "If the farmer buys/sells as part of a group", tier=TIER_OPTIONAL),
            Variable("payment_reference", "Payment reference", "", tier=TIER_OPTIONAL),
            Variable("quantity_kg", "Quantity (kg)", "Quantity bought back, in kilograms — not a generic unit, the real column is kg-specific", tier=TIER_REQUIRED),
            Variable("unit_price_lcy", "Unit price (LCY)", "", tier=TIER_REQUIRED),
            Variable("total_amount_lcy", "Total amount (LCY)", "loan_settlement_lcy + payout_lcy", tier=TIER_REQUIRED),
            Variable("loan_settlement_lcy", "Loan settlement (LCY)", "Portion of the payout applied to settle an existing loan, rather than paid in cash", tier=TIER_OPTIONAL),
            Variable("payout_lcy", "Payout (LCY)", "Cash portion actually paid to the farmer", tier=TIER_OPTIONAL),
            Variable("payment_date", "Payment date", "When OAF actually paid the farmer", tier=TIER_NICE_TO_HAVE),
            Variable("submitted_at", "Submitted at", "When the farmer submitted/sold the produce — can be well before payment_date", tier=TIER_OPTIONAL),
        ],
    ),
    "loan": Entity(
        key="loan",
        name="Loan",
        feeds="FACTS.FACT_LOAN",
        variables=[
            Variable("ledger_type", "Ledger type", "Loan or Savings — the real table holds both; loan-specific fields are blank for a Savings row and vice versa", tier=TIER_OPTIONAL),
            Variable("source_loan_id", "Loan ID", "Required for lineage", required=True, tier=TIER_REQUIRED),
            Variable("source_client_id", "Client ID", "Who received the loan", tier=TIER_NICE_TO_HAVE),
            Variable("loan_account_number", "Loan account number", "", tier=TIER_OPTIONAL),
            # Renamed from "loan_name" (2026-09-03, glossary review) to line
            # up with Sale's own loan_product_name — confirmed by the user
            # that Fineract's real LOANNAME field is, in practice, the loan
            # product's name, even though the DDL alone doesn't document it
            # that way (FACT_LOAN has no column sourced from
            # FINERACT_PRODUCT_LOAN_NAME the way FACT_SALE does) — see
            # upstream-gaps.md GAP-005.
            Variable("loan_product_name", "Loan product name", "", tier=TIER_OPTIONAL),
            Variable("loan_type", "Loan type", "", tier=TIER_NICE_TO_HAVE),
            Variable("loan_status", "Loan status", "", tier=TIER_OPTIONAL),
            Variable("group_name", "Group name", "If the loan is a group liability loan", tier=TIER_OPTIONAL),
            Variable("principal_lcy", "Principal (LCY)", "Amount disbursed", tier=TIER_REQUIRED),
            Variable("currency_code", "Currency", "", tier=TIER_OPTIONAL),
            Variable("approved_at", "Approved at", "", tier=TIER_OPTIONAL),
            Variable("disbursed_at", "Disbursed at", "", tier=TIER_NICE_TO_HAVE),
            Variable("matured_at", "Matures at", "", tier=TIER_OPTIONAL),
            # Savings branch — savings at OAF are always held against an
            # existing or future loan, never a standalone product, so they
            # share this entity rather than getting their own.
            Variable("source_savings_id", "Savings account ID", "If this row is a Savings account rather than a Loan", tier=TIER_OPTIONAL),
            Variable("savings_account_number", "Savings account number", "", tier=TIER_OPTIONAL),
            Variable("savings_status", "Savings status", "", tier=TIER_OPTIONAL),
            Variable("deposit_type", "Deposit type", "", tier=TIER_OPTIONAL),
            Variable("current_balance_lcy", "Current balance (LCY)", "", tier=TIER_OPTIONAL),
            Variable("total_deposits_lcy", "Total deposits (LCY)", "", tier=TIER_OPTIONAL),
            Variable("total_withdrawals_lcy", "Total withdrawals (LCY)", "", tier=TIER_OPTIONAL),
            Variable("activated_at", "Activated at", "", tier=TIER_OPTIONAL),
            Variable("closed_at", "Closed at", "", tier=TIER_OPTIONAL),
        ],
    ),
    "payment": Entity(
        key="payment",
        name="Payment",
        feeds="FACTS.FACT_PAYMENT",
        variables=[
            Variable("source_transaction_id", "Transaction ID", "Required for lineage", required=True, tier=TIER_REQUIRED),
            Variable("source_client_id", "Client ID", "Who is paying", tier=TIER_NICE_TO_HAVE),
            Variable("source_loan_id", "Loan ID", "Which loan this payment applies to, if any", tier=TIER_OPTIONAL),
            Variable("account_number", "Account number", "", tier=TIER_OPTIONAL),
            Variable("receipt_number", "Receipt number", "", tier=TIER_OPTIONAL),
            Variable("transaction_type", "Transaction type", "e.g. Repayment, Disbursement, Deposit, Withdrawal", tier=TIER_NICE_TO_HAVE),
            Variable("payment_type", "Payment type", "How payment was made — mobile money, cash, bank...", tier=TIER_NICE_TO_HAVE),
            Variable("account_type", "Account type", "Loan or Savings — which ledger this payment applies to", tier=TIER_OPTIONAL),
            Variable("repayment_phone", "Repayment phone", "Phone used to make the payment, if mobile money", tier=TIER_OPTIONAL),
            Variable("amount_lcy", "Amount (LCY)", "Can be negative for reversals/adjustments", tier=TIER_REQUIRED),
            Variable("transaction_date", "Transaction date", "", tier=TIER_NICE_TO_HAVE),
        ],
    ),
    "people": Entity(
        key="people",
        name="People (staff)",
        feeds="DIMENSIONS.DIM_PEOPLE",
        variables=[
            # DIM_PEOPLE's own real sourcing: it unions field_officer/
            # shopkeeper/nursery_manager from V_LOANS/V_SALES into one
            # full_name column, tagging is_fo/is_shopkeeper/
            # is_nursery_manager by which source column the name came from.
            # Mirrored here as three named roles rather than one generic
            # "Full name" — a mapper would have no way to tell which to use
            # for a staff column if both existed side by side.
            Variable("field_officer", "Field officer", "Who served this transaction, for Core/Carbon field sales/loans", tier=TIER_NICE_TO_HAVE),
            Variable("shopkeeper", "Shopkeeper", "Who served this transaction, for Retail shop sales", tier=TIER_NICE_TO_HAVE),
            Variable("nursery_manager", "Nursery manager", "Who served this transaction, for Kobo Trees distributions — exactly one of the three roles should be populated per row, depending on the channel", tier=TIER_NICE_TO_HAVE),
            Variable("division", "Division", "Department — populated once SuccessFactors is wired into this pipeline; currently always blank in the real table", tier=TIER_OPTIONAL),
            Variable("source_system", "Source system", "", tier=TIER_OPTIONAL),
        ],
    ),
}

# The funnel's third question used to be a free-text "Data Type" that only
# loosely implied an entity (e.g. "Distributions" -> Sale) — replaced
# 2026-09-03 with an explicit multi-select of which entities a file
# actually involves (a real upload routinely carries columns for several,
# e.g. a Kobo distribution sheet has Client, Location, People, AND Sale
# columns at once). This list decides both which variables the mapping
# dropdown offers and what the save gate requires — no more guessing.
ENTITY_CHOICES = [(key, entity.name) for key, entity in ENTITIES.items()]

# Country/Program/Source system used to be hardcoded lists here (the 10
# countries from entities-private/samples/dims/Countries.csv, and the 6
# canonical OAF_EQ program names). Replaced 2026-09-03: the real
# DimCountry/DimProgram/DimSystem tables are already mirrored into
# analytics_mirror and are the authoritative source — see
# bulk_uploader.views._funnel_dims(), which queries them live rather than
# this module holding a second, driftable copy. Kept the Google Form's
# funnel *shape* (Country → Program → Source system), just sourced for
# real now, with an "Other" free-text escape hatch at each level below
# Country (Country's real 10-country list is exhaustive; Program/Source
# system genuinely vary per country and a new one can show up before the
# warehouse dim catches up).


def variables_for(entity_key: str) -> list[Variable]:
    return list(ENTITIES[entity_key].variables)


def all_variables_grouped() -> list[tuple[str, list[Variable]]]:
    """Every entity's variables, grouped for a single dropdown — a real
    upload is routinely multi-entity (a Kobo distribution file carries
    Client, Location, People, AND Sale columns in one sheet), so scoping
    the mapping dropdown to just the funnel's chosen "primary" entity
    stranded real columns with nowhere to go (found live-testing
    mw_seedlings_distribution_data.csv, 2026-09-03 — no way to map
    FARMER_NAME). The primary entity still decides what's *required* (see
    required_variables) — only the dropdown's contents are unrestricted.
    Some variable names intentionally repeat across groups (e.g.
    source_client_id appears under Client, Sale, Purchase, Loan, and
    Payment, since each of those FACT tables really does have that
    column) — not deduplicated, so a column shows up under whichever
    entity a mapper is actually looking at."""
    return [(entity.name, entity.variables) for entity in ENTITIES.values()]


def all_variables_deduped() -> list[Variable]:
    """One entry per variable name, first occurrence wins (ENTITIES
    iteration order: client, location, product, sale, purchase, loan,
    payment, people) — for the mapping-progress scorecard, where the same
    field showing up once per entity would inflate/duplicate the count."""
    seen: dict[str, Variable] = {}
    for entity in ENTITIES.values():
        for v in entity.variables:
            seen.setdefault(v.name, v)
    return list(seen.values())


def required_variables(entity_key: str) -> list[str]:
    return [v.name for v in ENTITIES[entity_key].variables if v.required]


def required_variables_for_entities(entity_keys: list[str]) -> list[str]:
    """Union of required_variables across every selected entity — the save
    gate for a multi-entity upload is the union of each entity's own
    lineage requirement, not just one entity's."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for key in entity_keys:
        for name in required_variables(key):
            if name not in seen_set:
                seen_set.add(name)
                seen.append(name)
    return seen


def entities_grouped(entity_keys: list[str]) -> list[tuple[str, str, list[Variable]]]:
    """(key, name, variables) for just the given entities, in ENTITIES'
    own order — scopes the mapping dropdown and progress tracker to what
    an upload actually involves, once the uploader has said so via the
    entities checklist."""
    return [(key, ENTITIES[key].name, ENTITIES[key].variables) for key in ENTITIES if key in entity_keys]


def variables_deduped_for(entity_keys: list[str]) -> list[Variable]:
    """Like all_variables_deduped, but scoped to just the given entities —
    one entry per variable name, first occurrence wins in ENTITIES order."""
    seen: dict[str, Variable] = {}
    for key in ENTITIES:
        if key not in entity_keys:
            continue
        for v in ENTITIES[key].variables:
            seen.setdefault(v.name, v)
    return list(seen.values())


def suggest_mapping(columns: list[str], variables: list[Variable]) -> dict[str, str]:
    """Pre-fill the mapping where a source column already matches a variable
    by name, case- and separator-insensitively. Cheap, no AI — a real
    suggestion engine (column names + top rows fed to a model) is v1.2+."""
    def normalize(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    by_normalized = {normalize(v.name): v.name for v in variables}
    for variable in variables:
        by_normalized.setdefault(normalize(variable.label), variable.name)

    mapping = {}
    for column in columns:
        match = by_normalized.get(normalize(column))
        if match:
            mapping[column] = match
    return mapping
