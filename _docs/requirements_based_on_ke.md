# Requirements Based on KE (Client 360 / Tupande)

**Source:** `entities-private/360/client360_requirements_breakdown.xlsx` (added 2026-09-02) — a reverse-engineered requirements breakdown of Tupande Operations' Kenya-specific "Client 360" MVP, produced explicitly as a head start for global requirements gathering, not a final global spec. Two sheets: **Requirements** (59 items, observed capabilities) and **Inferred Additional Reqs** (23 items, explicit hypotheses not observed in the KE build — lower confidence, need stakeholder validation).

**Status of this doc: first-pass draft.** Every row below reflects one session's reconciliation against what Wimbi has built/scoped so far — useful as a working reference now, but a proper per-requirement review (confirm/reject/reshape each one with real stakeholder input) is explicitly deferred to a second round after v1 ships, per the user's direction on 2026-09-02.

## The one thing worth internalizing before reading the table

**Most of these requirements aren't things Wimbi can decide to build on its own — they're things ANALYTICS (the `entities` repo's Snowflake pipeline) would need to produce first.** Per ADR-007, Wimbi consumes ANALYTICS' output rather than reinventing it; Wimbi doesn't own `SOURCES`/`MASTER`/`DIMENSIONS`/`FACTS`. So every row below is tagged with a **Layer**:
- **ANALYTICS** — needs a new/changed pipeline stage, source integration, or data model change upstream, before Wimbi can consume it at all.
- **Wimbi** — buildable on top of what ANALYTICS already produces, or as new Wimbi-owned operational data (the ADR-004 pattern — Wimbi's own Postgres tables, not a mirror).
- **New infra** — needs something neither side has today (an LLM integration, SMS/push notifications, ML training pipeline).

## Headline estimate

**Roughly 10% of the combined 82 items (59 + 23) will be covered once the current frontend ships** — concentrated entirely in §1–3 (Identity/Data Model, Search, Client 360 Profile). §4–13 are essentially untouched. This isn't a shortfall — the October MVP was always scoped as a foundational slice (search → profile → timeline), not the full breadth this KE tool demonstrates. Worth having that gap explicit now rather than assumed away.

## Requirements sheet — first-pass status

| ID | Requirement | Status | Layer | Note |
|---|---|---|---|---|
| 1.1 | Canonical client entity | **Built** | ANALYTICS | This is literally what `MASTER`/`gl_client_id` already does; Wimbi just consumes it. |
| 1.2 | Identity resolution / matching engine | **Built**, not exposed | ANALYTICS (done) + Wimbi (UI) | `BridgeClientSourceId.match_confidence`/`match_method` already carry this — deferred to a later frontend pass. |
| 1.3 | Duplicate detection | Partial data, not surfaced | Wimbi | `FarmerReach.source_record_count` already gives the raw count; needs a UI, not new data. |
| 1.4 | Source provenance tagging | Data exists, deferred | Wimbi | Same bridge table; this is ADR-005's "embedded lineage" ambition, deliberately deferred. |
| 1.5 | Activity vs. system timestamps | Partial | Wimbi + ANALYTICS | We have real activity dates; distinguishing them from pipeline (`LOADED_AT`) timestamps in the UI isn't built. |
| 1.6 | Attribute scale (~550 attributes) | Not scoped | ANALYTICS + Wimbi | Our mirror is nowhere near this dense; would need far more fields mirrored plus a dense searchable UI. |
| 2.1 | Global client search | Partial | ANALYTICS + Wimbi | Built minus phone — real `V_CLIENT_REACH` has no phone column (a known gap, see ADR notes). |
| 3.1 | Profile header summary | Partial | Wimbi | Identity + recency (`last_activity_date`) exist; match confidence display deferred. |
| 3.2 | Relationship summary panel | Partial | Wimbi | Raw fields exist on `FarmerReach`; no curated summary panel built. |
| 3.3 | Credit detail section (risk classification, recommended action) | Partial | ANALYTICS + Wimbi | We have loan totals/repayment rate; no PAR-style risk bucket or recommendation logic exists anywhere yet. |
| 3.4 | Cash (input purchase) detail (cross-sell, next action) | Partial | Wimbi | `SalesLine` gives rich line-item detail already; cross-sell/recommendation logic doesn't exist. |
| 3.5 | Soko (market/supply) detail | Not directly applicable | — | Soko is a Kenya-specific value chain; Malawi's nearest analog is Retail/buyback — needs reframing, not a direct port. |
| 3.6 | Trees detail | Partial | Wimbi | `SalesLine`/`JourneyEvent` already carry Trees-program events + season fields. |
| 3.7 | Extension (FieldPro) detail | Not scoped | ANALYTICS | No FieldPro-equivalent source is mirrored for Malawi yet (Fieldsmart is a known source in ANALYTICS' inventory, per the Appendix, but not yet integrated here). |
| 3.8 | Segment explanation panel | Not scoped | ANALYTICS + Wimbi | Depends entirely on §4 existing first. |
| 3.9 | Unified cross-source timeline | **Built** | — | Journey Timeline. |
| 3.10 | All Fields / provenance directory | Data exists, deferred | Wimbi | Same lineage data as 1.4. |
| 4.1–4.3 | Segmentation & Scoring (named tiers, multi-factor scoring, segment→action mapping) | **Not scoped at all** | ANALYTICS (mainly) | The single biggest gap in the whole doc — implies a new scoring pipeline stage, not just a Wimbi feature. Nothing in our current 19-feature catalog covers this. |
| 5.1–5.4 | Cross-Value-Chain Analysis (overlap cards, source-count distribution, rule builder, Explorer hand-off) | Not scoped | **Wimbi-buildable now** | Good news: `BridgeClientSourceId.source_system` already gives us per-client source membership — this doesn't need an ANALYTICS change, just Wimbi engineering. |
| 6.1 | Multi-dimension filtering | Not scoped | Mostly Wimbi | Country/program/site/gender already mirrored; a formal region/area/zone hierarchy isn't. |
| 6.2 | Export | Not scoped | Wimbi | Straightforward, no ANALYTICS dependency. |
| 6.3–6.5 | Saved, dynamic, tracked cohorts | Not scoped | Wimbi (own tables) | New Wimbi-owned Postgres tables, same pattern as ADR-004 — doesn't need ANALYTICS. |
| 7.1–7.6 | Dashboards & Reporting (custom composer) | Not scoped | Wimbi, **if** we build one | Real tension: this is a self-built dashboard composer, which pulls against ADR-007's "consume Superset, don't reinvent" stance. Needs a deliberate decision later, not a default. |
| 8.1–8.4 | AI Data Assistant | Not scoped | New infra + ANALYTICS | Needs an LLM integration plus "prepared aggregate counts" (KE's governed-answer pattern, worth adopting whenever we build this) likely as a new REPORTING-layer view. |
| 9.1 | Server-side scope enforcement | **Built** | — | This is our entire RBAC/ADR-008/009 design. |
| 9.2 | Adjustable super-user scope | Not scoped | Wimbi | Feasible without any ANALYTICS change — a session override for testing/support. |
| 9.3 | Granular role-permission model | Partial | Wimbi | Django Groups give us the persona axis; identifier-reveal and export-permission granularity don't exist yet. |
| 9.4 | Multiple named roles | Partial | Wimbi | We have 8 groups; no direct claim of parity with KE's 6-role model. |
| 10.1–10.7 | Data Quality & Governance (issue dashboard, reviewer workflow, corrections, Data Ops monitoring) | Not scoped | Wimbi (own tables) | The most valuable section in the whole doc for us — finally gives concrete shape to our existing (vague) Features 9 & 10. Mostly buildable as new Wimbi-owned tables; full non-destructive write-back to Fineract/Odoo (10.5) is the bigger, later ambition from the original ADR-004 "circular" conversation. |
| 11.1–11.3 | Audit & Compliance | Not scoped | Wimbi (own tables) | No ANALYTICS dependency — log profile views/exports/etc. in our own Postgres. Maps to existing Feature 14. |
| 12.1 | Multi-format export | Not scoped | Wimbi | Straightforward. |
| 12.2 | Warehouse sync pipeline | **Built** | — | ADR-003. |
| 13.1 | Consistent masking enforcement | Not scoped | Wimbi | No PII fields are even mirrored yet beyond names; matters more once phone/national ID are added. |
| 13.2 | Demonstrated scale | Validated, ongoing | ANALYTICS | Our real Malawi data (1.3M farmers) is the same order of magnitude as KE's 1.54M — validates ADR-003's scaling concern is real, not hypothetical. |

## Inferred Additional Reqs — first-pass status

Lower confidence by the source doc's own framing — treat every row as a hypothesis, not a commitment.

| ID | Requirement | Status | Layer | Note |
|---|---|---|---|---|
| I.1–I.2 | Household / group-lending view | Not scoped | ANALYTICS | Would need household/group linkage fields; likely absent from current Fineract/Odoo/Kobo sources entirely — a real lift, not a UI add. |
| I.3 | Agricultural season framing | Partial | Wimbi | `SalesLine.season`/`derived_season` already exist; not surfaced as a first-class reporting cut. |
| I.4 | Program enrollment history | Partial | Wimbi | `JourneyEvent`/`FarmerReach` give some of this already. |
| I.5 | Multi-currency display & rollup | Partial | ANALYTICS (mostly ready) | `DIM_EXCHANGE_RATE` already exists in ANALYTICS (per the Appendix) — just not mirrored into Wimbi yet. |
| I.6 | Localized UI language | Not scoped | Wimbi | Frontend i18n; no ANALYTICS dependency. |
| I.7 | Cross-country benchmarking | Blocked | ANALYTICS + Wimbi | Malawi-only real data today; waits on more countries being onboarded to ANALYTICS. |
| I.8 | Offline-first field access | **Explicitly parked** | — | Already covered — this is Feature 17 (Field Officer Mode), deliberately out of scope. |
| I.9 | Proactive alerts to field staff | Not scoped | New infra | Maps to existing Feature 12 (Notifications & Alerts); needs SMS/push infra. |
| I.10 | Unified communication log | Not scoped | ANALYTICS | Comm-channel source data (SMS/call/WhatsApp logs) likely doesn't exist as an ANALYTICS source yet. |
| I.11 | Support-flag case management | Not scoped | Wimbi (own tables) | Maps to existing Feature 8. |
| I.12 | Outcome/impact metric linkage | **Not scoped — and not in our 19-feature catalog at all** | ANALYTICS | A real gap worth naming: M&E/impact survey data isn't an ANALYTICS source today, and nothing in our own catalog covers donor/funder-facing impact reporting. |
| I.13 | Multi-season trend view | Partial | Wimbi | Journey Timeline gives the raw material; not framed as a longitudinal trend view. |
| I.14–I.15 | Consent tracking, data residency | Not scoped | Process, not engineering | Ties directly to the DPIA-with-Legal item already on `to_do.md` — becomes concrete once that lands, not before. |
| I.16 | Client-protection vulnerability indicators | Not scoped | ANALYTICS | New risk data, doesn't exist today. |
| I.17 | Real-time payment status | **Tension with ADR-003** | ANALYTICS + decision | Directly contradicts the deliberate batch-sync choice — a conscious tradeoff already made, not an oversight, but worth revisiting explicitly if it ever becomes a real ask. |
| I.18 | National ID / civil registry verification | Not applicable currently | ANALYTICS | Malawi's matching doesn't key on national ID the way Kenya's does; also flagged "Low" confidence in the source doc itself. |
| I.19 | Governed API/webhook layer | Not scoped | Wimbi | Would reuse the existing RBAC/scope model as-is. |
| I.20 | Predictive early-warning scoring | Not scoped | ANALYTICS + New infra | Bigger lift than §4 even — needs an ML pipeline, not just descriptive segmentation. |
| I.21 | Multi-language AI assistant | N/A | — | Moot until §8 exists at all. |
| I.22–I.23 | Configurable value-chain/source registry, versioned scoring | Not scoped | ANALYTICS (architecture) | The biggest structural ask in the doc: today's per-country ANALYTICS builds are hardcoded SQL (Malawi built first, country-specific). A truly configurable global platform is a different architecture, and ties directly to the Rwanda/Kenya/Malawi duplicated-effort concern flagged early in `architectural_decisions.md`. |

## What to do with this doc

- Not a scope change for the current frontend build — that proceeds as already planned (§1–3 is exactly what it covers).
- Treat §4 (Segmentation & Scoring) and §10 (Data Quality & Governance) as the two most valuable candidates for the *next* planning round — one is a real gap, the other already has a home in our catalog and just needed concrete shape.
- I.12 (impact/M&E linkage) is worth raising as a possible addition to `features_and_user_stories.md` on its own merits, independent of this KE doc's confidence rating — it's a mission-fit gap, not just a KE-observed feature.
- Second review round (per-requirement confirm/reject/reshape with real stakeholder input) — deliberately deferred until after v1 ships.
