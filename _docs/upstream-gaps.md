# Wimbi — Upstream Data Gaps

**Status:** Living document — tracks real data-quality/completeness issues found in **ANALYTICS** (the Snowflake warehouse Wimbi mirrors) while building and testing Wimbi. These are fixed at the source (the pipeline, or Superset's own reporting logic), not papered over in Wimbi — per `architectural_decisions.md` ADR-007, Wimbi should never locally re-derive a number that could diverge from what Superset shows from the same views. Owned by the user to work through; Wimbi's side of each entry (if any) is noted so it's easy to see what, if anything, needs to change here once the upstream fix lands.
**Last updated:** 2026-09-03 (later still)
**Companion to:** `architectural_decisions.md` (ADR-006/ADR-007 already named several of these gap *categories* before real examples existed; this doc is the concrete, evidence-backed instance log), `uat.md` (where these tend to get found)

## How to use this

Each entry: what's broken, real evidence (not a guess), where it surfaces in Wimbi today, how Wimbi currently handles it, and a status. Add a new entry whenever UAT or normal use turns up something that traces back to the data itself rather than the app.

**Status legend:** 🔴 Open · 🟡 In review · 🟢 Fixed upstream (Wimbi-side note may still apply until data is re-synced)

---

## GAP-001: Kobo-sourced tree sales have no per-line price (`total_price_lcy`/`unit_price_lcy` null)

**Status:** 🔴 Open
**Discovered:** 2026-09-02, live UAT on farmer `MW-00008737` (Joshua Bruwayo, Trees program)
**Surfaces in Wimbi:** Farmer profile → Sales History table

**Evidence:**
```
12 SalesLine rows for MW-00008737, source_system=KOBO, source_order_id=CZTZPS03, all same sale_date (2024-11-18):
  every row: unit_price_lcy=None, total_price_lcy=None, total_price_usd=None
  every row: total_order_price_lcy=49088.00 MWK (identical across all 12 — order-level, not per-line)
  revenue_lcy per row: 10.96, 5.48, 10.96, 1.10, 0.55, 1.10, 0.00, 0.00, 0.00, 12.79, 6.34, 12.79
  revenue_usd per row: 0.01, 0.00, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.01, 0.00, 0.01
  sap_usd_rate: 1735.76 (MWK/USD) on every row, rate_exact_match=True
```

**Root cause (per the user):** Kobo-collected datasets often arrive with no unit prices at all, so `V_SALES_DETAIL` genuinely has nothing to put in `total_price_lcy`/`unit_price_lcy` at the line grain for these rows. `revenue_lcy`/`revenue_usd` exist as a prorated stand-in specifically to get `total_revenue` correct in Superset's own reporting.

**Open question for review:** the `revenue_lcy` values above sum to ~62.07 MWK across all 12 lines — nowhere close to the order's `total_order_price_lcy` of 49,088.00 MWK, so it isn't a simple proportional-proration of the order total in the same currency/scale. Worth the user's own look at what `revenue_lcy`/`revenue_usd` actually represent at line grain (per-unit? a different currency scale? correct but just small for tree seedlings?) before Wimbi considers using either field for anything.

**Current Wimbi-side handling:** Per-line Total column shows "—" (honest, not guessed). Lines missing a per-line total but sharing a populated `total_order_price_lcy` are summarized **once per order** (grouped by `source_order_id`) in a note above the table, rather than repeating the order total on every row (an earlier attempt did exactly that and was flagged as confusing on sight — repeating one number 12 times reads as broken, not informative).

**Suggested fix (upstream):** either backfill a genuine per-line price where derivable (e.g. evenly split the order total by quantity-weighted share, if that's a valid business assumption for these products), or accept line-level price is structurally unavailable for Kobo sources and document that as expected in `V_SALES_DETAIL` itself (a null-with-reason convention, if one exists).

---

## GAP-002: `FarmerReach.total_sales_lcy` (and other rollups) can be null despite `has_sale=True`

**Status:** 🔴 Open
**Discovered:** 2026-09-02, same farmer as GAP-001
**Surfaces in Wimbi:** Farmer profile → "Total sales" stat tile

**Evidence:** `MW-00008737`: `has_sale=True`, `total_orders=1`, but `total_sales_lcy=None`. Likely the same root cause as GAP-001 one layer up — a farmer-level rollup that depends on summing per-line totals that don't exist for Kobo-sourced sales.

**Current Wimbi-side handling:** Shows "—", not a computed guess. Wimbi deliberately does not locally sum `SalesLine.total_price_lcy` (or any other field) to backfill this, since that risks a second, possibly-wrong implementation of a number Superset would compute differently from the same root cause — the fix belongs in `V_CLIENT_REACH`'s own aggregation, not in Wimbi.

**Suggested fix (upstream):** once GAP-001 has a resolution (real or accepted-null per-line prices), `V_CLIENT_REACH`'s `total_sales_lcy` aggregation should reflect the same logic so the two are never inconsistent with each other.

---

## GAP-003: No USD/FCY-equivalent total exists on `V_CLIENT_REACH`

**Status:** 🔴 Open (feature gap, not strictly a data-quality bug)
**Discovered:** 2026-09-02, raised by the user while reviewing GAP-001/002
**Surfaces in Wimbi:** Farmer profile — "Total sales" only ever shows one currency (LCY)

**Evidence:** Direct schema introspection of the real `analytics_mirror.v_client_reach` table — every `total_*` column is LCY-only (`total_sales_lcy`, `total_principal_lcy`, `total_repaid_lcy`, `total_outstanding_lcy`, `total_purchase_lcy`, `total_program_value_lcy`). No USD or other FCY equivalent column exists at all.

**Current Wimbi-side handling:** None — showing both LCY and FCY totals isn't achievable today without a new upstream column, so it isn't attempted client-side (summing `SalesLine.revenue_usd` locally would hit the same divergence-risk problem as GAP-002, on top of GAP-001's open question about what that field even represents at line grain).

**Suggested fix (upstream):** if a USD/FCY total is wanted on the farmer profile, add the equivalent column(s) to `V_CLIENT_REACH` (ideally computed the same way Superset computes any USD figures it already shows, so the two can never disagree) — then it's a one-line addition on Wimbi's side to display it.

---

## GAP-004: `DIM_LOCATION` needs `village`, `cell`, and `source_location_id` — added to the Wimbi glossary ahead of the warehouse

**Status:** 🔴 Open (a needed enhancement, not a bug — the user's own call, tracked here so it isn't forgotten)
**Discovered:** 2026-09-03, while designing the bulk uploader's Location entity
**Surfaces in Wimbi:** Bulk uploader mapping page — `village`/`cell`/`source_location_id` appear as real Location variables, but nothing downstream in ANALYTICS can receive them yet

**Evidence:** Direct DDL read of `entities/database/dimensions.sql` — the real `DIM_LOCATION` has exactly 11 columns (`location_key`, `country`, `region`, `district`, `sector`, `lowest_loc`, `loc_type`, `latitude`, `longitude`, `geopoint`, `loc_parents`), confirmed against the live Postgres mirror too. None of `village`, `cell`, or `source_location_id` exist.

**Why it's wanted:** the real Malawi registration file (`mw_lr26 registration data.csv`) has a `FARMER_VILLAGE` column with no home in the current Location entity — the farmer's own village is a genuinely different place from the nursery/site they're served at (`lowest_loc`/`NURSERY_SITE`), which `DIM_LOCATION`'s current design doesn't distinguish. `cell` is the administrative level below village. `source_location_id` gives the lowest location's own source-system code (e.g. a Kobo `NURSERY_ID`) a proper home, mirroring how `source_product_id` already works for Product.

**Current Wimbi-side handling:** All three added to `bulk_uploader/glossary.py`'s Location entity so real uploads can capture them now, each explicitly documented in its description as "not a real DIM_LOCATION column yet." They map to nothing in `analytics_mirror` today — captured in Wimbi, waiting on the warehouse side.

**Suggested fix (upstream):** add `village`, `cell`, and `source_location_id` as real columns to `DIM_LOCATION` (and whichever `SOURCES`/`FACT` views need to carry them through) — the user's own stated intent, not a request to a data team.

Related, same session: `loc_type` moved from a per-row Location variable to a **funnel-level question** in the bulk uploader (`UploadedDataset.location_type`) — a single upload is virtually always one place-type throughout (all nursery, all shop...), matching how Country/Program already work. No upstream change implied by this one; it's a Wimbi-side UX simplification only.

---

## GAP-005: Loan entity naming — `loan_name` vs `loan_product_name`, and "Loan" vs "Credit" as OAF's own vocabulary

**Status:** 🔴 Open (a naming/design question, not a bug)
**Discovered:** 2026-09-03, reviewing the full bulk-uploader variable glossary end to end
**Surfaces in Wimbi:** the Loan entity's `loan_name` variable, and the "Loan" entity name itself

**Evidence — these are two different real columns, not one field needing a name touch-up:**
```
FACT_LOAN.loan_name          ← Fineract's raw LOANNAME        (V_LOANS, sources_views.sql:134)
FACT_SALE.loan_product_name  ← Fineract's FINERACT_PRODUCT_LOAN_NAME (V_SALES, sources_views.sql:326)
```
`FACT_LOAN` has no column at all sourced from anything like `FINERACT_PRODUCT_LOAN_NAME` — it does carry `source_product_id` (Fineract's `PRODUCT_ID`), but no product-*name* string. `LOANNAME` reads, from the DDL alone, like a per-loan-account label (Fineract lets an account carry its own name), not a documented product-template name.

**The ask, reviewing the glossary:** rename Wimbi's `loan_name` → `loan_product_name` in the Loan entity, so it lines up by name with Sale's own `loan_product_name` (the two sounded like the same concept but weren't backed by the same source field per the DDL alone). **Resolved by the user**: confirmed that Fineract's real `LOANNAME` field is, in practice, the loan product's name — the DDL just doesn't document it that way. Renamed in `glossary.py` (2026-09-03). Still logged here because the *documentation* gap is real regardless of the rename: nothing in `entities/database` states that `LOANNAME` carries the product name, so anyone reading the DDL cold (the next person, or this session in six months) would draw the same "these look like two different fields" conclusion this review did.

**Also flagged, deliberately not acted on:** the user's own observation that "Loan" may be the wrong entity name altogether — OAF's business is fundamentally about Sales, and credit is a financing mechanism for a sale, not a standalone banking product; "Credit" might be the more accurate entity name. Left exactly as-is for now, per explicit request.

**Current Wimbi-side handling:** `glossary.py`'s Loan entity now uses `loan_product_name` (was `loan_name`).

**Suggested fix (upstream):** a one-line comment on `V_LOANS`'/`FACT_LOAN`'s `LOANNAME`→`loan_name` mapping in `sources_views.sql`/`facts.sql` noting that this is, in practice, the loan product name — closing the documentation gap the DDL alone couldn't answer. The "Loan" vs "Credit" entity-naming question is separate and still fully open.
