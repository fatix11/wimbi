# Wimbi — Jira Backlog (Working Inventory)

**Status:** Living document — update status inline as work happens, this is a snapshot, not a report
**Last updated:** 2026-09-02
**Companion to:** `features_and_user_stories.md` (source of every epic/story below — read that file for full context per feature, not duplicated here), `delivery_strategy.md` §3 (the ticket-type/labeling conventions this follows), `architectural_decisions.md` (the "why" behind platform epics), `to_do.md` (the day-to-day "what's next" tracker — that one stays the natural, short-term action list; this one is the structured inventory of the whole backlog, current and future)

## Purpose

Everything is currently assigned to one person, so there's no real sprint board yet — but the backlog shape matters regardless of team size: it's the one place that says, for every feature area, what's done, what's in progress, and what hasn't started, so nothing quietly falls off. When a second engineer joins, this imports into real Jira largely as-is (Epics → epics, Stories → stories, following the ticket types in `delivery_strategy.md` §3).

**Status legend:** ✅ Done · 🔶 In Progress / Partial · ⏳ Not Started · 🚧 Blocked · 🅿️ Parked

---

## Platform Epics

Not in `features_and_user_stories.md` (that doc is farmer-facing features only) — these are the infrastructure epics every Part A feature above builds on. Captured here because they represent real, substantial completed work with their own history worth tracking.

### EPIC P1: Application Platform & Architecture
**Status:** ✅ Done for current scope, actively extended · **ADRs:** 001, 010

| Story/Task | Status | Notes |
|---|---|---|
| Django + DRF + PostgreSQL backend | ✅ Done | ADR-001 |
| Evaluate Reflex, supersede with Django + HTMX | ✅ Done | ADR-001 → ADR-010, three rounds of deliberate comparison (Odoo read/write shape, Superset's and DataHub's own React/TS frontends, a forward check against the Bulk Data Mapper) before locking in |
| Login / Dashboard / Search / Farmer Profile HTML pages | ✅ Done | ADR-010, 2026-09-02 |
| `scope_queryset` — DB-level RBAC filter for aggregates | ✅ Done | `accounts/rbac.py` |
| Search result cap + minimum query length (scale hardening) | ✅ Done | A real `q=g` search once returned a 113MB response and crashed the dev server — fixed same day, see ADR-010's 2026-09-02 update |
| `hx-boost` / htmx-partial routing bug (blank Search page) | ✅ Done | Found on first real browser test; fixed same day |
| Bulk Data Mapper frontend (column-to-glossary UI) | ⏳ Not Started | Next up — own plan, not yet written (Epic 18 below) |

### EPIC P2: ANALYTICS Postgres Mirror
**Status:** ✅ Done for Malawi · **ADRs:** 003, 006, 007

| Story/Task | Status | Notes |
|---|---|---|
| Batch-synced Postgres mirror design (not live Snowflake queries) | ✅ Done | ADR-003 |
| Real Malawi data loaded (`FarmerReach`, `JourneyEvent`, `BridgeClientSourceId`, `SalesLine`, `SFEmployee`) | ✅ Done | ~1.3M farmers, ~1.5M journey events, ~1.7M bridge rows, ~5M sales lines, ~10k SF employees — row counts verified against the Q2 2026 Entities Project Report |
| Chunked CSV loader, memory-bounded | ✅ Done | Recovered from a real `MemoryError`/WSL2 crash mid-load — ADR-003 |
| Remaining 4 REPORTING views: models + empty tables (`LoanPortfolio`, `ProgramSummary`, `RepaymentTransaction`, `FOPerformance`) | ✅ Done | 2026-09-03, schemas verified via real `DESCRIBE VIEW` + samples |
| Remaining 4 views: real data loaded | 🔶 In Progress | Tables are ready; user is populating via a direct Snowflake→Postgres transfer in DBeaver rather than the CSV loader this time |
| `V_SALES_DETAIL` fully loaded (currently 5M of 12.78M Malawi rows) | ⏳ Not Started | Scope of the current DBeaver push, to be confirmed |
| Recurring sync job (Airbyte or scheduled, cadence matched to upstream refresh) | ⏳ Not Started | ADR-003 "Open, not yet decided" — data is currently a one-time CSV/DBeaver load, not a live recurring sync |
| Incremental/CDC-style loading for multi-country scale | ⏳ Not Started | Deferred by design until multi-country volume is real (ADR-003) |
| Failure/staleness alert + "data as of [timestamp]" UI indicator | ⏳ Not Started | Flagged as a real gap in ADR-003, not yet built |

### EPIC P3: RBAC & Identity
**Status:** ✅ Done for MVP · **ADRs:** 008, 009

| Story/Task | Status | Notes |
|---|---|---|
| Elastic, admin-editable role-assignment mapping (`RoleAssignmentRule`) | ✅ Done | ADR-008, verified against all 10,074 real SF employees |
| Admin/trust tier structurally unassignable via rules | ✅ Done | `m2m_changed` guardrail, tested |
| Just-in-time login provisioning (`auth.User` blank slate until login) | ✅ Done | ADR-009 |
| Real Django session auth (replacing hand-rolled cookie) | ✅ Done | ADR-009 |
| DRF `AnonymousUser` authentication bug | ✅ Done | Found and fixed during ADR-009 |
| Keycloak SSO (real auth, replacing dev email-only login) | ⏳ Not Started | Named as future work since ADR-001; no blocker, just not started |
| Periodic access review process | ⏳ Not Started | `to_do.md` Phase 2 item |

---

## Part A: Core Farmer 360 Product Features

### EPIC 1: Farmer Search & Profile
**Status:** 🔶 In Progress — core path done, phone search blocked by data

| Story | Status | Notes |
|---|---|---|
| CC: search a farmer by name, phone number, or account ID | 🔶 Partial | Name/ID search: ✅ Done. Phone search: 🚧 Blocked on `V_CLIENT_REACH` (no phone column, ADR-006) — **worth revisiting**: `V_REPAYMENT_ANALYSIS` (added 2026-09-03) has a real `REPAYMENT_PHONE` column; searching that view once populated may unblock this without a data-team conversation |
| CC: see a farmer's core identity (name, location, programs, join date) | ✅ Done | Farmer profile page |
| BO: open a farmer's profile from a payment record | ⏳ Not Started | Depends on Epic 7 (Payments & Reconciliation Workspace) existing first |
| FS: search for any farmer in my district | 🔶 Partial | Country-scoped search works; no explicit district filter control yet |
| DT: search across all countries/programs regardless of role scoping | ✅ Done | Verified via real login (`data.team@` → `ALL` scope) |

### EPIC 2: Farmer Journey Timeline
**Status:** 🔶 In Progress — real data has fewer event types than the story called for

| Story | Status | Notes |
|---|---|---|
| CC: chronological timeline of enrollments/sales/loans/repayments/buybacks | 🔶 Partial | Real `V_CLIENT_JOURNEY` only has Sale / Loan Disbursed / Buyback (ADR-006) — no repayment or tree events at this layer; onboarding date shown as a profile field, not a timeline entry |
| BO: full loan/repayment history for reconciliation | 🚧 Blocked | Same root cause — no repayment events in the data yet |
| FO: own client history before a visit | 🅿️ Parked | Depends on Epic 17 (Field Officer Mode), itself parked |
| DT: filter the timeline by entity type | ⏳ Not Started | Timeline shows everything chronologically; no filter control |
| *(New, built ahead of catalog)* Sales History with product/quantity/field-officer detail | ✅ Done | ADR-007 — `SalesLine`/`V_SALES_DETAIL`, richer than the original story asked for |

### EPIC 3: Identity & Match Confidence
**Status:** ⏳ Not Started — deliberately deferred (ADR-005)

| Story | Status | Notes |
|---|---|---|
| CC: confidence indicator on a merged profile | ⏳ Not Started | `BridgeClientSourceId.match_confidence`/`match_method` already mirrored in Postgres — just not surfaced in UI |
| DT: drill into source records merged into a `gl_client_id` | ⏳ Not Started | Same — data's there, no UI |
| DT: flag a profile as incorrectly merged/split | ⏳ Not Started | No feedback-loop mechanism into MASTER exists yet |

### EPIC 4: Geo Explorer
**Status:** ⏳ Not Started (all stories)

### EPIC 5: Program & Portfolio Dashboards
**Status:** 🔶 In Progress — a lightweight highlights version exists, not the full feature

| Story | Status | Notes |
|---|---|---|
| FS: district/program health at a glance | 🔶 Partial | A "quick highlights" dashboard exists (4 stat tiles + 1 bar chart, ADR-010) — explicitly not a replacement for the full interactive `V_PROGRAM_SUMMARY`-based dashboard this story describes |
| FS: FO performance within my team | ⏳ Not Started | `V_FO_PERFORMANCE` now modeled and its table created (2026-09-03), real data load in progress via DBeaver — not consumed by any UI yet |
| PE: compare program performance across countries | 🚧 Blocked | Real ANALYTICS data is Malawi-only for now (per the catalog's own note) |

### EPIC 6: Seasonal Cohort Funnel
**Status:** ⏳ Not Started (both stories)

### EPIC 7: Payments & Reconciliation Workspace
**Status:** ⏳ Not Started (all 3 stories) — `V_REPAYMENT_ANALYSIS` (4.3M rows) now modeled and its table created (2026-09-03), real data load in progress via DBeaver, so the data prerequisite is closer than the feature itself suggests

### EPIC 8: Case & Escalation Handling
**Status:** ⏳ Not Started (all 4 stories) — flagged in the catalog as worth prioritizing early even though not MVP

### EPIC 9: Data Quality & Anomaly Feed
**Status:** ⏳ Not Started (all 3 stories)

### EPIC 10: Remediation / Two-Way Edit
**Status:** ⏳ Not Started — future, architecturally significant (requires Fineract/Odoo write-back)

### EPIC 11: Conversational AI Assistant
**Status:** ⏳ Not Started (all 3 stories)

### EPIC 12: Notifications & Alerts
**Status:** ⏳ Not Started (all 3 stories)

### EPIC 13: Admin & Access Management
**Status:** 🔶 In Progress — usable via Django admin, no dedicated Wimbi UI yet

| Story | Status | Notes |
|---|---|---|
| DT admin: see which SF-derived role/country a user is scoped to | 🔶 Partial | Visible via Django admin (`WimbiProfile`, group membership) — no Wimbi-native admin screen |
| DT admin: manually override a user's scope for the internal pilot | ✅ Done | Django admin lets an admin grant the `Admin` group or edit `RoleAssignmentRule`; ADR-008's guardrail keeps this safe |
| DT admin: list of all users who've logged in + last activity | ⏳ Not Started | `auth.User.last_login` exists natively but isn't surfaced in any Wimbi view/report |

### EPIC 14: Audit Trail / Activity Log
**Status:** ⏳ Not Started (both stories) — flagged as important given PII, not yet built

### EPIC 15: Export & Reporting
**Status:** ⏳ Not Started (all 3 stories)

### EPIC 16: Country/Program Switcher
**Status:** ⏳ Not Started — also currently moot, only Malawi has real data

| Story | Status | Notes |
|---|---|---|
| FS: switch between countries/programs I have access to | ⏳ Not Started | Country scoping exists server-side (ADR-008/009) but no switcher UI |
| PE: single view spanning all countries I'm scoped to | ⏳ Not Started | An `ALL`-scope user already sees everything unfiltered — but there's no UI concept of "current country" to switch, since there's only one live country |
| DT: new countries appear automatically once ANALYTICS onboards them | 🔶 Partial | Architecturally true already (scoping is data-driven, not hardcoded per country) — just unverified since only Malawi + 2 synthetic test countries exist |

### EPIC 17: Field Officer Mode
**Status:** 🅿️ Parked (per the catalog itself — offline-first, separate project)

---

## Part B: Adjacent Data Platform Features

### EPIC 18: Self-Service Bulk Data Mapper
**Status:** 🔶 In Progress — v1.1 in build (2026-09-03). Full requirements in [bulk-uploader.md](bulk-uploader.md)

| Story | Status | Notes |
|---|---|---|
| BU: upload a Kobo-like dataset (CSV/Excel) | 🔶 In Progress | v1.1 — file upload only; Sheets and Snowflake/Dataiku connectors are v1.2+ |
| BU: be guided to map my columns to the glossary | 🔶 In Progress | v1.1 — funnel-scoped dropdowns + exact-name-match pre-fill. "Conversationally"/AI-assisted is v1.2+ |
| BU: see which of my columns didn't match anything | 🔶 In Progress | v1.1 — unmapped columns are visible in the mapping step; per-row validation shown in preview |
| DT: review/approve a proposed mapping before it lands in SOURCES | ⏳ Not Started | v1.2+ — deliberately deferred; with one power user there's nobody to review for yet |
| DT: an already-approved mapping is suggested next time | ⏳ Not Started | v1.2+ |
| DT: an accepted mapping generates/updates a SOURCES view | ⏳ Not Started | v1.2+ — the promotion ETL, the strategic payoff of this whole feature |
| DT: log of who mapped what, when, approved/rejected | ⏳ Not Started | v1.2+ — v1.1 records uploader + timestamp + the mapping itself, but no approval events to log yet |

### EPIC 19: AI-Assisted Superset Chart & Dashboard Builder
**Status:** ⏳ Not Started (all 7 stories) — adjacent effort, not begun in this repo

---

## Labels (once this is real Jira)

Per `delivery_strategy.md` §3: `mvp`, `phase-2`, `parked`, `security`, `pii`, `uat-blocker`. Every story touching farmer PII (all of Epics 1–3, 7–10, 14) should carry `pii`.
