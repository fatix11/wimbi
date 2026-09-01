# Wimbi — To-Do Tracker

**Purpose:** Self-tracker for progress against `delivery_strategy.md`. This doc changes constantly — check items off as they're actually done, update **Last updated**, and leave `delivery_strategy.md` itself alone (that one's the stable reference).

**Last updated:** 2026-09-02
**Current phase:** Phase 0

---

## Phase 0 — Now (small team, pre-MVP)
- [ ] Provision QA / UAT / PRD environments (AWS)
- [ ] Set up Jira project with epics matching the feature catalog
- [ ] Define branching strategy and CI pipeline skeleton
- [x] Write unit + integration tests as features are built (not after)
- [x] Start the RBAC negative-test suite alongside RBAC implementation, not after
- [ ] Draft an ADR for each decision already made in `business_requirements.md` §9

## Phase 1 — Internal MVP → UAT gate
- [ ] Define UAT sign-off owners per persona
- [ ] Build out E2E tests for the MVP's core flows (search, timeline, login/RBAC)
- [ ] Run a first informal security pass (dependency scan, secrets audit)
- [ ] Start a Data Protection Impact Assessment with Legal — long lead time, start early
- [ ] Usability test with actual pilot candidates, not just the team

## Phase 2 — External rollout (call center first)
- [ ] Formal UAT sign-off completed and documented
- [ ] Access review process running on a schedule
- [ ] Incident response process defined (even lightweight)
- [ ] Feature-flagged rollout plan per persona group
- [ ] First real penetration test

## Phase 3 — Bigger team / handover
- [ ] RACI review with incoming team
- [ ] All informal decisions formalized or retired
- [ ] Full playbook adoption (Scrum ceremonies, CAB, formal SLAs)
- [ ] Country-specific compliance review completed for every live country

---

## Log
Short dated entries when something meaningful gets checked off or a phase changes — not a full changelog, just enough to see momentum at a glance.

- 2026-08-31 — Tracker created, nothing started yet.
- 2026-08-31 — Scaffolded the Next.js app and shipped the first vertical slice: dev-login (Auth.js, stand-in for Keycloak) → farmer search → profile → Journey Timeline, RBAC-scoped by country, running on mock fixture data behind a swappable `DataSource` interface (real Snowflake client built but not wired to live credentials). Unit tests (RBAC negative cases + mock data source) and an E2E flow (Playwright) pass; build and lint clean. `git init` deferred one more step — repo not yet initialized.
- 2026-09-01 — Rebuilt on Django + PostgreSQL per `_docs/architectural_decisions.md` (ADR-001 through ADR-006): Next.js prototype removed, Django backend (accounts/analytics_mirror/farmers apps) built fresh with the same RBAC contract, 16 backend tests passing. Loaded real Malawi data (~1.3M farmers, ~1.5M journey events, ~1.7M bridge/lineage rows, ~10k SF employees) via a chunked Postgres `COPY` loader — row counts match the Q2 2026 Entities Project Report exactly. Verified end-to-end against real data (search → profile → journey → cross-country RBAC block). **Open and blocking real RBAC**: SuccessFactors department names don't map cleanly to Wimbi's role vocabulary (no "Call Center" or "Data Team" department exists) — needs a decision, not a guess. Reflex frontend not started yet.
- 2026-09-01 (later) — ADR-007: consume pre-built REPORTING views for computed metrics, mirror DIMENSIONS directly, raw FACTS only for genuinely new cuts. Folded in `sales_detail.csv` (real `V_SALES_DETAIL`, 5M/12.78M Malawi rows) as a new `SalesLine` model + `GET /api/farmers/<id>/sales/` endpoint, enriching the Journey feature with product/quantity/field-officer/site detail — 18 tests passing, verified against a real farmer. Hit and worked through a real scale incident along the way: the full 5M-row load twice crashed with `MemoryError` (once taking Docker Desktop's WSL2 VM down with it) under this machine's actual memory pressure (host was down to ~0.6GB free with Docker + the existing Superset stack + Postgres all running) — recovered by finishing the load in smaller fresh-process passes against remainder files rather than one continuous run. All 5,000,000 rows loaded and verified. Concrete, lived evidence for ADR-003's incremental-loading concern, not just a theoretical one.
- 2026-09-02 — ADR-008: elastic, admin-editable role-assignment module. New `accounts.RoleAssignmentRule` (department + optional WorkLocation condition → Django Group + country-scope override) and `assign_roles` management command, seeded with the user's initial department mapping via a data migration. Ran against all 10,074 real SF employees — every resulting group count matches the mapping exactly (Field Officer 4,034, Field Supervisor 1,968, Business Ops 241, Program Executive 29, Data Team 114 with `ALL` country scope, Business/Program User 2,013, Gamma 1,675 fallback). "Admin" is structurally unassignable via the rule engine (enforced in `clean()`) and the sync only ever touches groups the rule table owns, so a manually-granted Admin membership always survives a re-run — tested. 30 tests passing. **Still open**: no department maps to Call Center yet (flagged to the user, not guessed); dev personas (`accounts/dev_users.py`) stay in place alongside real SF-backed users for now — wiring the live login/session flow to prefer real users is a deliberate follow-up, not done in this pass.
