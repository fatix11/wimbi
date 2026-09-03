# Wimbi — Bulk Data Mapper/Uploader

**Status:** Living requirements doc — v1.1 in build, later phases named but not started
**Last updated:** 2026-09-03
**Related:** [architectural_decisions.md](architectural_decisions.md) (ADR-004 origin, ADR-010 frontend approach, ADR-011 the alternating Wimbi↔ANALYTICS cadence this feature exemplifies) · [features_and_user_stories.md](features_and_user_stories.md) (Feature 18, the original story set) · [jira-backlog.md](jira-backlog.md) (Epic 18, live status) · [upstream-gaps.md](upstream-gaps.md) (where gaps this feature surfaces get logged) · [uat.md](uat.md) (acceptance tests, extended per phase)

## Why this exists

OAF's farmer data is spread across ~10 countries, ~30 country+program combinations, and a genuinely long tail of source systems — `dims/Systems.csv` shows single programs fed by 10+ systems (Fieldsmart, Fineract, Odoo, KOBO, Commcare, Dataiku, Sheets, USSD, Appsheet, KissFlow, Zendesk, WMS, MNOs, and more). Today, getting any of that into `ANALYTICS.SOURCES` means a data engineer hand-writing a view per dataset. That doesn't scale, and it leaves whole programs (Trees, Carbon) with no durable home for their data at all — it risks being lost at the end of a season.

Two prior attempts inform this design, and both taught something:

1. **A standardized Excel collection template** (`entities-private/samples/Data Collection Template.xlsx`, also proposed in the Q1 report) — pushed the transformation burden onto business users. They resisted; people were adamant about keeping and shaping their own data their own way. **Lesson: don't demand a shape upfront. Meet data where it already lives, and do the mapping work in the tool.**
2. **A public Google Form** (currently live: *OAF Global Data Analytics*) — asks Country → Program → Operational Year → Season → Data Type → "already in the DWH?" → a link to the dataset (Sheets URL, or a `db.schema.table` address for Snowflake/Dataiku). Lightweight enough that people actually use it. **Lesson: that funnel is the right set of questions — port it forward rather than reinventing it.** Its field set also directly answers ADR-004's open "what metadata does an upload need" question.

## The vision (north star)

A **modern, source-agnostic, quality-checked, steward-centered, AI-assisted bulk data uploader** that makes it effortless for a business user — the steward who signs off on their program's data — to get that data into the warehouse without a data-engineering ticket:

- **Source-agnostic ingestion** — Google Drive/Sheets (read via Sheets API, the way Dataiku does), direct CSV/XLSX upload, and Snowflake/Dataiku tables (`development.<schema>.<table>`, where most Kobo-form pipelines already land).
- **Quality gate at the source** — reject or flag data that fails minimum requirements before it ever propagates. Non-negotiables: a **source id per transaction** and a **client identifier per farmer** (whatever scheme that country actually uses), so every row stays traceable back to its origin.
- **Variable mapping against a canonical glossary** — the uploaded columns get mapped to OAF's real canonical variables, not to a per-dataset bespoke schema.
- **AI-assisted** — sanity checks (row counts, null profiling) and a proposed column mapping inferred from column names plus the top rows, which the human then reviews rather than authors from scratch.
- **Preview before commit** — people see exactly what they're about to submit.
- **Owner/steward/approval centered** — edits, audit, review and approval live in Wimbi, where there's a real user model and permissions.
- **Then a second, automated ETL** promotes approved data from Wimbi into `ANALYTICS.SOURCES` — turning what is today a manual pipeline-authoring step into an unmanned one.

That last point is the strategic payoff: this is the entry point that makes the whole warehouse more self-service, not just a Wimbi feature.

## The glossary (rewritten 2026-09-03 to use the real warehouse's own names)

Two earlier passes at this glossary worked from *design documents*: `entities-private/samples/new_variable_mapping.csv` (an aspirational ERD, ~150 raw variable rows across 8 entities and ~19 normalized views) and the Data Collection Template's natural-language field names (`served_by`, `sale_type`). Both were useful for scoping *which* 8 entities matter, but neither is the built system — and stress-testing the resulting glossary against two real Kobo files (`mw_lr26 registration data.csv`, `mw_seedlings_distribution_data.csv`) kept surfacing the same problem: natural-language names like `served_by` or `sale_type` turned out to each collapse **two or three genuinely different real columns** into one guess.

So the glossary was rebuilt a third time, this time read directly from the pipeline's own DDL (`entities/database/dimensions.sql`, `facts.sql`, `master_procedure.sql`) — the actual `CREATE TABLE`/`CREATE VIEW` statements that build `DIM_CLIENT`, `DIM_LOCATION`, `DIM_PRODUCT`, `DIM_PEOPLE`, `FACT_SALE`, `FACT_LOAN`, `FACT_PAYMENT`, `FACT_PURCHASE`. Adopting these names directly means a mapped upload needs no translation step when it's eventually promoted into `ANALYTICS.SOURCES` (v1.2+) — full field-by-field list with descriptions lives in code, `bulk_uploader/glossary.py`.

**What reading the real DDL settled, definitively (not guessed) — this is what the two stretch tests against real files were exposing:**

- **`field_officer` / `shopkeeper` / `nursery_manager` are three separate real `DIM_PEOPLE` roles**, not one generic "served by" field — confirmed by `DIM_PEOPLE`'s own sourcing SQL (`V_LOANS.field_officer`, `V_SALES.field_officer`/`shopkeeper`/`nursery_manager`). Exactly one is populated per row, depending on the sale channel.
- **`EPA` → `sector` and `NURSERY_SITE` → `lowest_loc` are exact, confirmed mappings**, not judgment calls — `DIM_LOCATION`'s Kobo branch does precisely this, with the comment *"EPA is the administrative unit above the nursery → sector level."*
- **`DIM_CLIENT` has three separate named identity columns**: `national_id`, `account_number`, `fineract_id` — never a generic type+value pair. This is the second, final nail in the earlier `id_type`/`id_value` EAV design (already flagged as wrong-shape once, from real files; now also confirmed wrong-*requirement* — a client's own identifier and `source_client_id`, the universal lineage id used for MASTER matching, are two different things entirely).
- **`FACT_PURCHASE` is real** — Purchase is no longer unverified. It has a genuine buyback-specific split not anticipated by either design document: `loan_settlement_lcy` (portion of a payout applied against an existing loan) + `payout_lcy` (cash to the farmer), summing to `total_amount_lcy`.
- **Location is not universally required.** The Data Collection Template claimed `LOWEST_LOC` was always mandatory; the actual DDL never enforces it — `V_SAVINGS` has no district at all, and `DIM_LOCATION` tolerates partial hierarchy throughout. Required is now scoped to exactly what was asked for: a client identifier, and a per-entity lineage/transaction id (`source_transaction_id`, `source_purchase_id`, `source_loan_id` — each entity's *own* real id column, not one invented generic field).
- Household/group survey fields (`family_size`, `has_youth`, group membership) were **dropped** — they were only ever in the aspirational `new_variable_mapping.csv`, with no backing in any real `DIM_*`/`FACT_*` table. Re-add if/when a real table backs them.

### The client identifier is not one scheme

`dims/Programs.csv`'s `CROSS_ID` column (and `DIM_PROGRAM.cross_program_id_type`, the same thing mirrored for real) shows what actually identifies a farmer varies by country: **NID** (Rwanda, Kenya), **APPSHEET_ID** (DRC), **ACCOUNTNUMBER** (Uganda), and **nothing formal at all** (Malawi, Tanzania, Nigeria, Burundi — where MASTER falls back to probabilistic name/phone matching). `DIM_CLIENT`'s three separate identity columns already reflect this — none is required.

Related signal worth using: `DIM_PROGRAM.phone_quality` rates phone data per country/program from "Excellent" (Kenya, Rwanda, Uganda) down to "Very Bad" (Malawi Trees) — useful for setting per-context expectations rather than one blanket rule.

### The unpivot problem (found via stretch test, decided 2026-09-03)

`mw_seedlings_distribution_data.csv` (a real Kobo Trees distribution file) is **wide**, not long — one column per tree species (`A_LEBBECK_SEEDLINGS`, `F_ALBIDA_SEEDLINGS`, `S_SPECTABILIS_SEEDLINGS`, `POLYCANTHA_SEEDLINGS`), each holding a quantity, with a `TOTAL_SEEDLINGS` checksum column. `FACT_SALE` is long-grain — one row per product per transaction. No column mapping fixes this; it needs an unpivot (each farmer row → up to 4 `Sale` rows).

**Decision: don't unpivot at Wimbi's capture stage.** Pull the file as uploaded; the unpivot happens when the real `SOURCES` view for this dataset gets built — a manual pipeline step, the same way the rest of `entities/database` already works, not something Wimbi's capture layer should own. **Not yet built**: the mapping UI currently only has two states per column, "map to a variable" or "drop" — a dropped column's data is gone. Needs a third **"keep as raw column"** option so a wide file's product-quantity columns survive capture under their own original names, ready for whoever writes the eventual `UNPIVOT` SQL, without forcing Wimbi to solve the reshape itself.

### The glossary today, and its own review pass (2026-09-03)

The synthesized-down "~45 variables" above was the *starting* estimate — real stretch-testing (People's three roles, `pivoted_product`, Location's channel split, synthetic keys, GAP-004's added-ahead-of-the-warehouse fields) grew it to **~99 mapped fields, 84 unique names, across the same 8 entities**. Rather than let that list only live as scattered comments in `glossary.py`, it now has two real surfaces: a **Glossary page** in Wimbi itself (`/glossary/`, open to any logged-in user — general Farmer 360 context, not just for uploaders) and, before that, a one-off review artifact the user scanned end to end. That review caught one real placement issue — `loan_name` and Sale's `loan_product_name` looked like the same concept but were sourced from two different real Fineract columns per the DDL (`LOANNAME` vs. `FINERACT_PRODUCT_LOAN_NAME`) — confirmed by the user as, in practice, the same thing, and renamed; logged as `upstream-gaps.md` GAP-005 since the DDL itself still doesn't document that. Also raised in that same pass, deliberately left alone: whether "Loan" is even the right entity name given OAF is fundamentally sales-led, not a bank — "Credit" might fit better. Worth a real look whenever the glossary gets its next structural pass.

## The funnel

**Country → Program → Source system → Which entities does this file involve? → Location type.** Updated twice on 2026-09-03: the entities checklist replaced the Google Form's single "Data Type" question (see below), then Country/Program/Source system were switched from hardcoded/free-text to live, cascading dropdowns sourced from the real mirrored dims (`DimCountry`/`DimProgram`/`DimSystem`), and Source system was added as a new funnel question in its own right.

**Real dims, not a second hardcoded copy.** `bulk_uploader.views._funnel_dims()` queries `analytics_mirror` at request time; the cascade key from Program → Source system is `program_local_name`, not `program_oaf_eq` — real data shows the OAF-equivalent code alone can collapse genuinely distinct programs in one country (Kenya has two separate "Retail" rows, "Asili - Cash (Walk-in)" and "(App)", sharing one `oaf_eq`), while `program_local_name` is also exactly what `DimSystem`'s own rows key against. Every level below Country has an "Other…" escape hatch: the dropdown's sentinel value is never stored, whatever the uploader types into the paired free-text field becomes the real value — Country's real 10-country list is treated as exhaustive and gets no "Other".

**Source system is broadcast, not just captured.** Once set, it appears on the mapping page as a locked, uneditable banner rather than a normal column mapping, and gets written into every row's `mapped_data` automatically — like `SELECT 'KOBO' AS source_system` applied to the whole file, mirroring how a real upload almost never carries its own per-row source_system column. An explicit per-row mapped value (the rare genuinely mixed-system file) still wins if one is present; leaving Source system blank at the funnel keeps `source_system` an ordinary mappable variable for that case.

The entities checklist replaced Data Type because the original single-select (Registration/Enrollment/Distributions/Household surveys/Geomapping surveys/Impact surveys/Other) only ever *implied* one entity, and real files routinely aren't one entity — a Kobo distribution sheet carries Client, Location, People, AND Sale columns in the same upload. The checklist says directly, not by inference, which entities apply — one or many — and:
1. **Scopes the mapping UI** to just those entities' variables, not every entity's fields at once, and not just one guessed entity either.
2. **Directly decides the save gate.** The strict required-field check (`required_variables_for_entities`) is the union of every checked entity's own lineage requirement — check Sale and Client, and the gate requires both `source_transaction_id` and `source_client_id`/`full_name`/`source_system` (the last of which the Source system funnel answer now satisfies automatically, if set).

**Season and Operational year are also dropdowns now** (built as a direct follow-on, once the user confirmed it): Operational year is a plain 2015–current-year range (descending), and Season cascades off Country via `DimSeason`, showing only the **3 seasons closest to today** for that country — 0 distance for whichever season today falls inside (the current one), otherwise the gap to the nearer edge (`views._closest_seasons`). In practice this surfaces the current season plus its immediate neighbors (the one just ended, the one coming up), not an arbitrary recency cutoff. Both fields are optional. Editing an old draft whose stored season has since aged out of the "closest 3" window still shows it (appended as an extra option) rather than silently dropping a real answer.

## Synthetic composite keys

For an upload with no single clean source id — real files this session hit directly — the mapping page lets an uploader combine 2+ of their own columns into a composite key instead, per required lineage field. `parsers.build_synthetic_key()` normalizes (trim, uppercase) and MD5-hashes the chosen columns' values together, mirroring `DIM_LOCATION`/`DIM_PEOPLE`'s own real MD5-keying and the same probabilistic-matching spirit `BRIDGE_CLIENT_SOURCE_IDS` falls back to when no direct id exists. Tagged as **synthetic** — shown as such on the preview page — the same tagging concept as a funnel-broadcast value (`source_system`), per the user's own framing: both are dataset-level facts about *how* a field's value was resolved, not a real per-row mapped column.

Rules, mirroring the `source_system` broadcast precedent: an explicit real column mapped to the same variable always wins over the synthetic combination (synthetic is a fallback for what's missing, not an override); a row where every chosen column is blank gets `""`, not a manufactured hash, so it still fails the required-field gate honestly; and choosing only 1 column doesn't count as a combination — 2+ are required. Scoped to just the dataset's actual required fields (`required_variables_for_entities`), matching the concrete problem this solves, not opened up to every glossary variable.

## Phasing

### v1.1 — in build now
Upload → funnel → map → validate → preview → store durably in Wimbi's own Postgres.

- **File upload only** (CSV/XLSX).
- **Mapping**: dropdown per source column against the funnel-scoped variable list, pre-filled by exact case-insensitive name match where the header already matches a variable name — a cheap, real first pass at "smart" without AI yet.
- **Quality gate, visibly**: validate the whole file up front; show a per-row pass/fail summary in the preview. Invalid rows are *visibly excluded*, never silently dropped, and never cause a blanket rejection of the whole file — the user decides whether to proceed with valid rows or go fix the source.
- **No `gl_client_id` matching** — uploads stay unlinked from the resolved farmer identity for now.
- **Not yet built**: a "keep as raw column" third mapping option, needed for wide/pivoted files (see the unpivot problem above) so their data survives capture rather than being silently dropped.
- **Power-user UX.** The first real user is the person building it, onboarding additional countries by hand before anyone else touches the tool. Dense and fast beats hand-holding at this stage; the "effortless for a first-time business user" pass comes when real multi-user rollout does.
- **Access**: uploader + Admin/Data Team. No new RBAC dimension — with effectively one user, program-scoped visibility would be speculative design.

### v1.2+ — named, deferred, not forgotten
- Google Sheets connector (Sheets API)
- Snowflake / Dataiku connector (`development.<schema>.<table>`)
- AI-assisted mapping suggestions + automated sanity checks (counts, null profiling) — possibly via MCP, undecided
- Steward review/approval workflow before a mapping is final
- Auto-suggested mappings from a previously-approved mapping of the same recurring dataset
- **The second ETL: promotion of approved Wimbi uploads into `ANALYTICS.SOURCES`**
- `gl_client_id` matching, feeding the dedup/identity loop (Feature 3)
- Program/department-scoped upload visibility

## Open questions

- Where exactly does an approved upload land in `ANALYTICS.SOURCES` — one table per uploaded dataset, or an appended common table per entity? (Decide before building the v1.2+ promotion ETL, not now.)
- Does the AI mapping step need MCP, or is a direct model call with column names + top-10 rows enough? Leaning toward the latter — smaller surface, no new infrastructure.
- Whether `PHONE_QUALITY` / `CROSS_ID` from `dims/` should be mirrored into Wimbi as real reference data (they're currently read-once design inputs, not live tables).
