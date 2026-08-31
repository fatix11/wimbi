# Wimbi — To-Do Tracker

**Purpose:** Self-tracker for progress against `delivery_strategy.md`. This doc changes constantly — check items off as they're actually done, update **Last updated**, and leave `delivery_strategy.md` itself alone (that one's the stable reference).

**Last updated:** 2026-08-31
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
