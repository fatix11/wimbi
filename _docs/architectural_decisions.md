# Wimbi — Architectural Decisions

**Author:** Augustin Faraja, Business Analyst — One Acre Fund
**Status:** Living log — append new decisions as ADRs rather than editing old ones; mark superseded entries instead of deleting them
**Companion to:** `business_requirements.md` (§9 Key Decisions Log holds product-level decisions; this doc holds architecture-level ones), `features_and_user_stories.md`, `delivery_strategy.md`

## Purpose

`business_requirements.md` §9 anticipated this: "continue the pattern already started... split into per-decision ADRs once the log gets long." This is that split. Each entry below is a self-contained decision record: context, decision, alternatives considered, consequences. **This doc supersedes the "Build approach" and "Architecture" rows in `business_requirements.md` §9** — those said "Next.js + thin API layer"; ADR-001 below replaces that.

---

## ADR-001: Application stack — Django + DRF + PostgreSQL backend, Reflex frontend

**Status:** Accepted (supersedes the original Next.js/TypeScript prototype)

**Context:** The first vertical slice was built in Next.js/TypeScript to validate the shape of the problem fast (auth → RBAC → data → UI, end to end). That worked, but revealed real constraints: the team's stated preference is Python end-to-end for maintainability and hiring; TypeScript/React is not a language the primary builder is fluent in; and there's an explicit ambition to borrow Odoo's modularity and interactivity without inheriting Odoo's operational weight or its UI's "ERP look."

**Decision:**
- **Backend:** Django + Django REST Framework + PostgreSQL, with Celery + Redis for background/async work (integration syncs, scheduled jobs, retries).
- **Frontend:** Reflex — a Python framework that compiles to a real React app under the hood, giving genuine SPA-quality navigation and polish while every line of code stays Python.

**Alternatives considered:**
| Option | Why it was passed over |
|---|---|
| FastAPI | Async-native and modern, but no built-in admin/auth/migrations — more assembly required for the same outcome as Django |
| NestJS (TypeScript) | Closest structural analog to Odoo's modules, but conflicts directly with the Python requirement |
| Frappe | Genuinely Odoo-like modularity in Python, but MariaDB-first (weak Postgres story) and a narrow, Frappe-specific hiring pool |
| Django + HTMX/Alpine.js (no Reflex) | Safer, more mature, zero JS — but more manual effort to reach the same "app-like," smooth-navigation feel Reflex gives natively. Kept as the fallback if Reflex's smaller ecosystem proves too risky in practice. |
| Keep Next.js/TypeScript | Best UI ceiling available today (and partly already built), but not Python, and not a language the team is fluent in |

**Consequences:**
- The Next.js prototype's *code* is not carried forward, but its *design decisions* are: the `DataSource` interface pattern, the RBAC scoping logic, the fixture data shapes, and the E2E test scenarios all port directly into the Django rebuild — they were validated once and don't need re-deriving.
- Django's "app" convention (self-contained models/views/migrations per feature) becomes Wimbi's module boundary — the Odoo-inspired modularity from earlier discussion, without Odoo itself.
- Reflex is a young framework (~2022). Accepted risk, given how directly it satisfies the Python + visual-polish combination; Django+HTMX remains the documented fallback if it doesn't pan out in practice.

---

## ADR-002: Not building on Odoo

**Status:** Accepted

**Context:** OAF already runs two Odoo deployments (Odoo Sales — POS/inventory; Odoo Procurement — manufacturing/PR-PO/sourcing), each with its own three environments. Odoo has mature RBAC (record rules), a real modular framework, and a chatter/activity-log system (`mail.thread`) that maps well to "validate, remediate, and track who-did-what."

**Decision:** Farmer 360 will not be built as a third Odoo deployment or Odoo module. Specific *patterns* — centralized row-level RBAC, chatter-style audit trails, modular feature boundaries — are borrowed into the Django app instead.

**Rationale:**
1. A farmer's unified identity (`gl_client_id`) is the *output* of the ANALYTICS dedup pipeline across Fineract + Odoo + Kobo + buyback data. Odoo's `res.partner` model doesn't natively represent a cross-system merged record — building Wimbi inside Odoo would mean syncing ANALYTICS' output back into a third Odoo instance, which runs backwards from the pipeline's purpose.
2. A third Odoo deployment is a full additional operational stack — its own Postgres, its own major-version upgrade cycle, its own three environments, its own specialized (and harder-to-hire) module-development skill. Heavier, not lighter.
3. Odoo's default UI is hard to fully re-skin to a genuinely custom, "visually appealing" bar without Enterprise tooling or significant custom frontend work.
4. Licensing: several of Odoo's more polished capabilities sit behind Enterprise's per-seat pricing.

**Considered in Odoo's favor (not enough to change the decision):** OAF's ops/business/call-center staff already work inside two Odoo systems daily — a third, similar-feeling screen would carry a real change-management/training advantage. Noted for the record, not dismissed, just outweighed.

**Follow-up (not yet done):** A short, time-boxed spike — stand up Odoo Community locally, configure one custom model with chatter enabled — remains worthwhile purely as a design reference, independent of this decision.

---

## ADR-003: Farmer/journey data via a batch-synced Postgres mirror of ANALYTICS.REPORTING — not live Snowflake queries

**Status:** Accepted

**Context:** The original data-boundary plan had Wimbi querying `ANALYTICS.REPORTING` directly in Snowflake on every request (a `SnowflakeDataSource` implementing live queries per page view). ANALYTICS itself is a batch pipeline — verified against the `entities` repo, the `SOURCES` refresh task runs weekly (`CRON 0 2 * * 1 UTC`, i.e. Monday 02:00 UTC), not nightly as first assumed; the exact cadence for `MASTER`→`REPORTING` downstream of that hasn't been independently confirmed and should be checked with whoever owns the pipeline before the sync job is finalized. Either way, per-request Snowflake queries buy no freshness benefit over a periodic mirror, while incurring real, recurring compute cost that scales with usage (every farmer search, every profile view, every timeline load becomes a billed Snowflake query).

The bigger goal this serves: OAF's farmer data is disparate across many systems of record, each with its own access model — the whole point of ANALYTICS is that it's already organized and unified in one warehouse. Wimbi's job is to *democratize access* to that already-solved unification, not to re-solve it or bolt on a second live query path.

**Decision:** A periodic batch job (cadence matched to the verified upstream refresh schedule, likely weekly to start) replicates the relevant `ANALYTICS.REPORTING` views into Wimbi's own PostgreSQL database. The app reads exclusively from this Postgres mirror at request time; Snowflake is touched only by the sync job, never per user request.

**Rationale (the case as made, preserved on record):**
- Snowflake compute is expensive at query-time scale; a periodic bulk sync is a single, predictable, cheap cost instead of an unbounded per-user-action cost.
- REPORTING is only ever as fresh as its last pipeline run regardless — live querying can never be "more current" than a mirror synced on the same cadence, so no freshness trade-off is actually being made.
- **Consistency guarantee:** because both Superset (querying `ANALYTICS.REPORTING` in Snowflake directly) and Wimbi (querying its Postgres mirror, populated from the same REPORTING views on the same cycle) draw from the same refresh, the two surfaces can never disagree with each other. Same source, same cadence, two frontends.

**Consequences:**
- The `SnowflakeDataSource` design from the Next.js prototype (direct per-request querying) is superseded. Its Django-rebuild equivalent reads from local Postgres tables populated by the sync job — the `DataSource` interface abstraction still holds, only the concrete implementation behind it changes.
- Real-time or near-real-time farmer data is explicitly out of scope by design — acceptable because ANALYTICS itself isn't real-time either.
- The sync becomes infrastructure Wimbi now owns and must operate: it needs a failure/staleness alert (if it doesn't run, Wimbi silently serves stale data with no warning unless we build one), and the UI should surface a "data as of [timestamp]" indicator so users know the freshness contract.

**Known scaling concern, accepted and deferred:** Malawi alone is `FACT_SALE` at 12.8M rows; a full 10-country rollout (repayments especially) could plausibly reach the order of 100M+ rows in some tables. A naive full-refresh sync won't hold up at that scale. This is a real problem, not a hidden one — the working assumption is that incremental/CDC-style loading (only syncing new or changed rows per run, keyed off something like each table's own `loaded_at`/updated-at watermark) is the likely solution, mirroring the same incremental philosophy ANALYTICS' own MASTER pipeline already uses for deduplication (see the Appendix below). Deliberately not designed in detail yet — revisit once multi-country volume is closer to real, not before.

**Lived, not just projected (2026-09-01):** loading the 5M-row `sales_detail.csv` (ADR-007) crashed with `MemoryError` twice — once severely enough to take down Docker Desktop's WSL2 VM (and with it, briefly, Django's own `public`-schema tables, recovered without data loss). Root cause was this dev machine's actual memory pressure (Docker + the pre-existing Superset stack + Postgres all competing for RAM, host down to ~0.6GB free at the worst point), not a flaw in the chunked-COPY approach itself — chunking to smaller sizes and running the tail of the load as fresh, short-lived processes against remainder files got all 5M rows in cleanly. Real confirmation that "deal with scale later" needs to mean incremental *and* memory-bounded per run, once this stops being a single-machine dev exercise.

**Open, not yet decided:**
- Sync tooling — Airbyte (Snowflake source → Postgres destination connectors both exist out of the box) is the natural first candidate given the team already operates Airbyte for similar pipelines; a custom scheduled job is the fallback.
- Full-refresh vs. incremental sync per view/table (see scaling concern above).
- Schema convention in Wimbi's Postgres to clearly separate the analytics mirror (read-only, sync-owned) from Wimbi's own operational tables (cases, audit log, bulk-uploaded program data — owned and written by the app itself). These should not live in the same schema or be easy to confuse.

---

## ADR-004: Non-core program data gets a home via the Bulk Data Mapper/Uploader, not a bespoke system of record

**Status:** Accepted (extends Feature 18 in `features_and_user_stories.md`)

**Context:** Fineract and Odoo serve Core/Credit farmers adequately, but programs like Trees and Carbon have no proper operational system of record today. Their data currently risks losing value or being lost outright at the end of a season or distribution cycle, because there's nowhere durable for it to live once the immediate collection exercise ends.

**Decision:** Rather than standing up a dedicated new system of record per underserved program, extend the already-planned **Bulk Data Mapper** (Feature 18) so it does double duty:
1. Its original purpose stands — guide a business user through mapping a new dataset's columns to the canonical glossary so it can flow into `ANALYTICS.SOURCES` without bespoke data-engineering work per dataset.
2. **New:** the uploaded dataset is also durably persisted as first-class records inside Wimbi's own PostgreSQL database (the operational side from ADR-003, not the analytics mirror) — giving the program team a permanent place that data belongs to them, independent of whatever happens to it downstream in ANALYTICS.

**Rationale:** This directly answers "their data has a place to call their own" without building N bespoke systems for N underserved programs — one general-purpose capability (upload + map + own) scales across Trees, Carbon, and whatever program shows up next with the same gap.

**Consequences / open design questions (not yet resolved):**
- Data model for "program dataset upload" as a durable, versioned entity (which season, which distribution, which program, uploaded by whom, mapped how).
- Relationship to `gl_client_id`: a row should link to a resolved farmer identity where a match exists, and remain program-scoped/unlinked where it doesn't yet — this is itself a feedback loop into the MASTER dedup pipeline, related to Feature 3 (Identity & Match Confidence).
- Access control for a program team's own uploaded data — likely program-scoped RBAC, a new dimension alongside the existing country scoping.

---

## ADR-005: Data lineage as an embedded, cross-cutting feature — not a separate page

**Status:** Accepted

**Context:** `MASTER.BRIDGE_CLIENT_SOURCE_IDS` (verified against the `entities` repo — not `bridge_to_source_ids` as first assumed) already records which source-system records — a Fineract client ID, an Odoo partner ID, a Kobo submission ID — were merged into a given `gl_client_id` golden record, one row per source record with columns including `oaf_client_id`, `source_system`, `source_program`, `source_client_id`, `source_country_code`, `source_fidelity`, `is_singleton`, `match_confidence`, `match_method` (`SEED` / `TIER1_DETERMINISTIC` / `TIER2_PROBABILISTIC`), and `linked_at_ts`. This lineage already exists inside the ANALYTICS pipeline but isn't surfaced anywhere in the product today.

**Decision:** Treat "show where this came from" as a first-class capability embedded into every screen that shows farmer or journey data, not a bolted-on "lineage explorer" built later. Every meaningful data point — a profile field, a timeline event — should be able to reveal its originating source system and source record ID on demand.

**Rationale:** This is a trust feature for a product whose entire premise is cross-system deduplication and matching — showing your work is how users learn to trust a merged record instead of silently distrusting it. It also overlaps directly with, and strengthens, the already-planned Feature 3 (Identity & Match Confidence): a user spotting a wrong source attribution while looking at lineage is exactly the QA feedback loop Feature 3 wants into the MASTER pipeline. `match_confidence` and `match_method` are already sitting right there in the bridge table, ready to drive Feature 3's confidence badge directly.

**Consequences:**
- The sync job (ADR-003) must replicate `MASTER.BRIDGE_CLIENT_SOURCE_IDS` into Wimbi's Postgres mirror alongside the REPORTING views themselves — lineage needs to be joinable locally, not fetched via an extra live Snowflake call per view.
- UI components need one shared "source" affordance (e.g., an expandable badge) designed once and reused everywhere farmer/journey data appears, rather than each feature inventing its own way of showing provenance.
- This decision effectively merges lineage display and Feature 3's match-confidence UI into one connected design problem, worth designing together rather than sequentially.

---

## ADR-006: Real data over mock, ahead of the frontend — RBAC to move to real SuccessFactors identity

**Status:** Accepted (in progress)

**Context:** The Django backend (accounts/analytics_mirror/farmers apps, RBAC, DRF endpoints) was built and fully tested against fixture data seeded by `seed_mock_analytics_mirror` (see ADR-003's "mock first" pattern). Before building the Reflex frontend, the user chose to plug in real data first rather than build the UI against fixtures — both for `analytics_mirror` (real Airbyte-synced Snowflake data) and for identity/RBAC (real SuccessFactors data instead of the 4 hardcoded dev personas in `accounts/dev_users.py`).

**Decisions:**
1. **RBAC moves from dev personas to real SuccessFactors data**, matching the direction already stated in `business_requirements.md` §7 ("Authorization: derived from SuccessFactors"). The mapping from SF's raw fields (email, country, department, job title) to Wimbi's role vocabulary (`call_center`, `business_ops`, `field_supervisor`, `data_team`) doesn't exist yet — it will be designed collaboratively once a real SF employee extract (matching the shape of the `V_SF_EMPLOYEES`-style sample already seen in `entities-private/samples`) is available to inspect, rather than guessed at now.
2. **Synthetic non-Malawi farmer rows stay in `analytics_mirror` alongside real synced data.** Real ANALYTICS data is Malawi-only today (per the Q2 report), so the cross-country RBAC negative-path tests (`tests/test_farmers_api.py`) would otherwise lose their only way to prove the country boundary actually blocks something, until more countries are onboarded for real. A couple of fixture Kenya/Rwanda rows are kept deliberately, clearly separable from real data (e.g., by `source_fidelity`/seed-specific IDs).
3. **Initial real-data sync targets a representative slice, not the full Malawi dataset** (~1.3M farmers, 12.8M+ `FACT_SALE` rows). Full-scale loading is deferred until the app itself is further along — matches the "deal with scale later" posture already accepted in ADR-003.

**Consequences:**
- `accounts/dev_users.py`'s hardcoded `DEV_USERS` list is temporary scaffolding, not a permanent design — expect it to be replaced by a real identity source (likely its own `analytics_mirror`-style synced table, e.g. `sf_employees`) plus a small role-mapping table/config Wimbi owns.
- Reflex frontend work is paused until this real data is in place, so the UI is built against something closer to production shape from the start rather than needing a rework pass later.

**Update (2026-09-01) — what actually happened:**
- The user provided full CSV exports rather than a filtered slice — `client_reach.csv` (1,305,491 rows), `client_journey.csv` (1,538,230 rows), `bridge_client_source_ids.csv` (1,734,921 rows), `successfactors_employees.csv` (10,815 rows). Row counts for the first and third match the Q2 2026 Entities Project Report exactly. Point 3 above (representative slice) didn't happen as planned — loading the full dataset via Postgres `COPY` in chunks (`analytics_mirror/csv_loader.py`) turned out to be fast enough (~6 minutes for ~4.6M rows combined) that slicing wasn't worth the extra complexity. Superseded, not a problem.
- **Filenames as handed over didn't match their actual content** — `client_reach.csv` actually contained journey/event data and vice versa with `export.csv`; caught by checking real headers before writing any loader code, not by trusting names.
- **Real schemas differ from what was assumed when the unmanaged models were first drafted**, all now corrected in `analytics_mirror/models.py`:
  - `V_CLIENT_REACH` has **no phone number column** — Feature 1's "search by name, phone number, or account ID" (`business_requirements.md`) isn't backed by real data for the phone case. Search is name/ID only until a phone-bearing source gets joined in — worth a product conversation, not silently patched over.
  - `V_CLIENT_JOURNEY`'s only real event types are **Sale / Loan Disbursed / Buyback** — no enrollment, repayment, or tree events exist at this layer (`onboarded_on` on the reach table covers enrollment instead).
  - `BRIDGE_CLIENT_SOURCE_IDS` has a real `BRIDGE_ID` primary key — better than the `source_client_id`-as-pk guess used before real data was seen.
  - Real data has genuine gaps that the loader tolerates rather than fails on: some Kobo-sourced farmers have no `full_name`; some SF employee records have no email (skipped, since email is the RBAC lookup key) or duplicate emails across re-orgs (deduped, keeping the most recently updated).
- **Found and fixed a real schema-isolation bug while wiring this up**: the Postgres connection originally set `search_path=analytics_mirror,public` so the unmanaged mirror models would resolve without schema-qualifying every `db_table`. This backfired — Django's *own* migrations (auth, sessions, admin) also landed inside `analytics_mirror` (unqualified `CREATE TABLE` always targets the first schema on the search path), so a later `DROP SCHEMA analytics_mirror CASCADE` (done to fix the model shape) silently wiped `django_session` and friends along with it. Fixed by schema-qualifying each mirror model's `db_table` directly (`'analytics_mirror"."v_client_reach'` — Postgres accepts this as a valid qualified identifier) and removing the custom `search_path` entirely, so Django's own tables live in the normal default `public` schema, fully decoupled from whatever happens to `analytics_mirror`.
- **Role-mapping remains genuinely unresolved, on purpose.** The real SF extract has no department literally called "Call Center" or "Data Team" — the closest matches are "Business Operations" (243 people) and "Field Operations" (6,186 people, almost certainly far broader than just supervisors). Rather than guess a mapping for a decision that gates PII access, this is flagged back to the user rather than encoded into `accounts/`.

---

## ADR-007: Consume pre-built REPORTING views for computed metrics; mirror DIMENSIONS directly; only build from raw FACTS for genuinely new cuts

**Status:** Accepted

**Context:** ANALYTICS' `DIMENSIONS`/`FACTS` schemas (`DIM_CLIENT`, `DIM_DATE`, `DIM_PRODUCT`, `DIM_LOCATION`, `DIM_PEOPLE`, `DIM_COUNTRY`, `DIM_SEASON`, `DIM_EXCHANGE_RATE`; `FACT_SALE`/`FACT_LOAN`/`FACT_PAYMENT`/`FACT_PURCHASE`) form a proper star schema — normalized, and a genuinely nice shape to build arbitrary new aggregations against. This raised a real question: for features needing aggregated numbers (program dashboards, FO performance, seasonal cohorts), should Wimbi pull raw dimensions/facts and compute its own joins/`GROUP BY`s in Postgres at query time, rather than mirroring Snowflake's already-built `REPORTING` views?

**Decision:** The deciding question isn't which shape is more elegant (the star schema wins that outright) — it's **whether re-deriving a number independently creates a second, divergence-prone implementation of a metric someone can already see in Superset**. Split accordingly:
1. **Point-lookup features** (farmer search, profile, journey) — unchanged from ADR-003: mirror the per-entity `REPORTING` views (`V_CLIENT_REACH`, `V_CLIENT_JOURNEY`). Nothing here is a computed aggregate, so there's nothing to diverge on.
2. **Aggregated/computed features** (Program & Portfolio Dashboards, Seasonal Cohort Funnel, FO Performance, repayment analysis) — consume the matching pre-built `REPORTING` view (`V_PROGRAM_SUMMARY`, `V_FO_PERFORMANCE`, `V_REPAYMENT_ANALYSIS`) rather than recomputing the same aggregation from raw `FACT_*` tables locally.
3. **DIMENSIONS tables** — mirror these fully and directly regardless of the above. They're small, static reference data (`DIM_DATE` ~11k rows, `DIM_LOCATION` ~2k, `DIM_PEOPLE` ~1.5k, `DIM_COUNTRY` 10, `DIM_SEASON` 171), not computed metrics, so there's no risk of disagreeing with Superset by holding a local copy.
4. **Raw FACT tables** — pull directly only when building a genuinely new cut that has no existing canonical view or Superset chart to potentially diverge from (e.g., a novel geo/product cross-cut nobody's computed before). If a feature needs a cut close to an existing view but not quite there (like the missing phone number on `V_CLIENT_REACH`), the default should be raising it with the data team as a view change, not silently reimplementing the logic inside Wimbi.

**Rationale:** This directly extends ADR-003's "Wimbi and Superset must never disagree" principle from the freshness layer (nightly/batch sync vs. live query) down to the aggregation layer (whose join/`GROUP BY` logic computes the number). The data team already solved real complexity to get these views right (recursive-SQL performance failures, the Odoo client-filter gap, season-label edge cases, SAP exchange-rate gap-filling) — re-deriving that independently isn't cleaner, it's a second place for the same class of bug to live, this time invisibly out of sync with the original.

**Consequences:**
- Dashboard-shaped features should default to sourcing from the matching `REPORTING` view, not `FACT_SALE`/`FACT_LOAN`/etc. directly.
- Geo Explorer (Feature 4) is expected to combine locally-mirrored `DIMENSIONS` (`DIM_LOCATION`'s lat/lon) with transaction-level detail from whichever view/fact already carries it (e.g. `V_SALES_DETAIL`-shaped data) — this is additive/new, not a re-derivation of an existing Superset number, so it doesn't trigger the divergence concern above.
- `sales_detail.csv` (added 2026-09-01, `V_SALES_DETAIL`-shaped, 5M of 12.78M Malawi `FACT_SALE` rows, 2.6GB) — also a concrete proof point for ADR-003's scaling note (see Appendix). **Update (2026-09-01):** loaded into a new `SalesLine` model/`sales_line` table (line-item grain, deliberately separate from `JourneyEvent` since one journey "Sale" event can correspond to several sales lines) via the same `load_csv_snapshot` command. A new `GET /api/farmers/<gl_client_id>/sales/` endpoint exposes it, RBAC-scoped the same way as journey/profile. This is the "richer Journey Timeline entries" enrichment named as the top candidate use when the file first arrived — product name, quantity, unit price, field officer, and exact site per sale line, none of which `V_CLIENT_JOURNEY` carries.

---

## Appendix: ANALYTICS reference

Verified against the `entities` repo and the Q2 2026 Entities Project Report (2026-06-21, status Final) — not re-derived from memory. Kept here so the next person (including future-us) doesn't have to re-read the pipeline SQL from scratch.

**Layers:** `ANALYTICS` database, five schemas, built and validated in strict order: `SOURCES → MASTER → DIMENSIONS → FACTS → REPORTING`.

- **SOURCES** — full-replace daily... *([sic] the refresh procedure's own header comment says "daily," but the Snowflake Task attached to it is actually scheduled `CRON 0 2 * * 1 UTC` — weekly, Monday 02:00 UTC. Trust the Task, not the comment, until confirmed otherwise.)* Tables: `FINERACT_CLIENTS`, `FINERACT_LOANS`, `FINERACT_LOAN_TRANSACTIONS`, `FINERACT_SAVINGS`, `FINERACT_COMBINED_TRANSACTIONS`, `ODOO_CLIENTS`, `ODOO_SALES`, `KOBO_SALES_MW_TREES_2024`, `SHEETS_PURCHASES_MW_MARKET_2025`. Every table carries `LOADED_AT`.
- **MASTER** — identity resolution. Normalizes all sources into `STG_CLIENTS_ALL`/`STG_MATCH_BASE` → Tier 1 deterministic matches (hard cross-system keys, e.g. a Fineract ID recorded in Odoo) → Tier 2 probabilistic matches (phone + name/site fuzzy matching, `JAROWINKLER_SIMILARITY`, ≥0.60 threshold) → graph connected-components clustering (production uses **Python/NetworkX**, not recursive SQL — recursive SQL was tested and found too slow at Malawi's scale) → `DIM_CLIENT` (golden record, highest-fidelity source donates attributes) → `BRIDGE_CLIENT_SOURCE_IDS` (lineage, see ADR-005). Source fidelity ranking: Fineract = HIGH, Odoo = MEDIUM, Kobo/Sheets = LOW. Golden ID format: `{ISO_CODE}-{SEQUENCE}`, e.g. `MW-00000001` (an older archived SQL script used a different `OAF-CLT-{COUNTRY}-{seq}` format — superseded).
- **DIMENSIONS** — `DIM_DATE`, `DIM_PRODUCT`, `DIM_LOCATION` (incl. lat/lon for nurseries), `DIM_PEOPLE` (FOs/shopkeepers), `DIM_COUNTRY`, `DIM_EXCHANGE_RATE` (sourced from **SAP**, gap-filled), `DIM_SEASON`.
- **FACTS** — `FACT_SALE` (12.78M rows, Malawi — Core/Carbon/Retail via Odoo *and* Trees via Kobo), `FACT_LOAN` (601k, Fineract incl. savings), `FACT_PAYMENT` (4.32M, Fineract ledger only), `FACT_PURCHASE` (1,599, buyback via Sheets). Every fact carries `gl_client_id` + `date_key`.
- **REPORTING** — 7 views: `V_SALES_DETAIL`, `V_LOAN_PORTFOLIO`, `V_PROGRAM_SUMMARY`, `V_CLIENT_REACH` (the 1.3M-farmer spine), `V_CLIENT_JOURNEY` (what Wimbi builds on), `V_REPAYMENT_ANALYSIS`, `V_FO_PERFORMANCE`.

**Scale (Malawi only, Q2 2026):** 2,818,673 raw records → 1,734,921 after within-source dedup → **1,305,491 unique farmers**. A full 10-country rollout is expected to push some fact tables well past 100M rows (see ADR-003's scaling note). Concrete proof point (2026-09-01): a 5,000,000-row (of 12,776,927 total Malawi) extract of `V_SALES_DETAIL` alone is 2.6GB as CSV — the full Malawi table would be ~6.7GB, one country, one fact table.

**Known upstream gaps that will surface in Wimbi's UI:**
- 67,965 Odoo clients (0.5% of `FACT_SALE`) have no `gl_client_id` yet — a filtered `ODOO_CLIENTS` source table excludes some `res_partner` records; fix identified, deferred to Q3.
- Kobo tree sales don't join to `DIM_LOCATION` (site-level mismatch between the Kobo source view and the dimension's lowest grain).
- 125 people in `DIM_PEOPLE` are name-collisions between two different FOs/shopkeepers — pending SuccessFactors wiring to resolve via employee ID/email.
- `Fieldsmart` (the tablet app) is already a known source system in ANALYTICS' own system inventory, alongside Fineract and Odoo, for the Core program — not a greenfield integration target.

**Related, not yet acted on:** the Q2 report's own Q3 roadmap names a "Governance layer... based on Tasman work (DB restructure, roles, RBAC)... apply RLS in Superset" — worth reading `entities-private/samples/Tasman vs OAF — Deduplication Approach Comparison.md` and the Tasman feedback notes before designing Wimbi's RBAC in detail, in case there's already a governance direction set that Wimbi should align to rather than duplicate.

---

## Open follow-ups tracked elsewhere

- Update `business_requirements.md` §7/§9 to point at this doc instead of the now-superseded Next.js/live-Snowflake description (not yet done — flagged, pending confirmation).
- Update `features_and_user_stories.md` Feature 18 write-up to reflect its dual purpose from ADR-004.
- SAP and FieldSmart integration are real, stated scope (per the factors that shaped ADR-001) but appear nowhere yet in `business_requirements.md` — needs a proper requirements pass, not just an architectural mention.
- The Odoo research spike from ADR-002 hasn't been run yet.
- Confirm the actual `MASTER`→`REPORTING` refresh cadence with the ANALYTICS pipeline owner (only `SOURCES`' weekly schedule is verified so far) before finalizing the sync job in ADR-003.
- Read the Tasman governance/RBAC material referenced in the Appendix before finalizing Wimbi's RBAC model in detail.
