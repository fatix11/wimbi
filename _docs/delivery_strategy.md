# Wimbi — Product Delivery & Engineering Playbook

**Author:** Augustin Faraja, Business Analyst — One Acre Fund
**Status:** Draft — forward-looking, to be adopted incrementally
**Last updated:** 2026-08-31
**Companion to:** `business_requirements.md`, `features_and_user_stories.md`, `to_do.md` (self-tracker built from this doc)

## Purpose

Today, Wimbi is a small effort building toward an internal October MVP. This doc is written for the version of Wimbi that has traction and a real team — so that if/when that happens, there's a playbook ready rather than a scramble. Treat it as a menu, not a mandate: adopt pieces as the team and stakes grow, starting with whatever's flagged **[Now]** below.

---

## 1. Stakeholders (RACI-style)

| Role | Responsibility | Now (small team) | At scale |
|---|---|---|---|
| **Product Owner** | Owns requirements, prioritization, roadmap | This role, worn by the author | Dedicated PM |
| **Engineering Lead** | Owns architecture, code quality, delivery | Shared/contracted | Dedicated |
| **Frontend/Backend Engineers** | Build the app | Small/contracted | Dedicated squad |
| **Data Engineering (ANALYTICS team)** | Owns SOURCES/MASTER/DIMENSIONS/FACTS/REPORTING that Wimbi consumes | Existing team, informal handoff | Formal API contract owner |
| **QA/Test** | Test strategy, execution, regression | Founder-tested | Dedicated |
| **UX/Design** | Interaction design, usability | Informal | Dedicated |
| **Security & Data Protection** | PII risk, access reviews, incident response | Ad hoc | Formal function, likely shared with OAF IT/ITD |
| **IT/ITD (Keycloak, AWS)** | SSO, infra, hosting | Coordination as needed | Formal SLA |
| **HR/SuccessFactors owner** | Source of truth for role/country/department | Read-only consumer | Data-sharing agreement |
| **Business stakeholders** | Call center lead, BizOps lead, regional ops lead, program executive sponsor — one per persona in `features_and_user_stories.md` | Informal feedback | Formal UAT sign-off per persona |
| **Legal / Data Protection Officer** | Compliance across 10 countries' data protection regimes | Not yet engaged — **flag this early** | Required before any external rollout involving PII at scale |
| **Executive Sponsor** | Budget, org backing, unblocks cross-team dependencies | Implicit | Named, accountable for outcomes |
| **Country/program peers** | Rwanda's BIA team (Innocent), Kenya's BI (Dennis Macharia) — see `entities-private/360/` | Informal awareness | Formal coordination forum, avoid triplicated dedup work |

## 2. Delivery Methodology

- **[Now]** Kanban-style continuous flow — small team, requirements still shifting, no need for sprint ceremony overhead yet.
- **[At scale]** Scrum: 2-week sprints, sprint planning, daily standup, sprint review/demo (invite business stakeholders — this is where UAT feedback loops in), retro.
- **Definition of Ready** (before a ticket enters a sprint): user story written, acceptance criteria defined, design available if UI-facing, dependencies identified.
- **Definition of Done**: code merged, tests passing, reviewed, deployed to staging, acceptance criteria demonstrably met, docs updated.
- **Roadmap cadence**: quarterly planning against the feature catalog in `features_and_user_stories.md`, re-prioritized as UAT feedback comes in.

## 3. Jira / Ticketing Structure

| Ticket type | Use for | Example |
|---|---|---|
| **Epic** | A feature area from the catalog | "Farmer Journey Timeline" |
| **Story** | A single user story | "As a CC officer, I want to search a farmer by phone number..." |
| **Task** | Non-user-facing work | "Set up Keycloak OIDC client" |
| **Bug** | Defect against existing behavior | "Timeline shows duplicate loan entries" |
| **Spike** | Time-boxed investigation, no committed output | "Evaluate NID as a matching variable for Rwanda" |
| **Chore** | Maintenance, upgrades, cleanup | "Bump Next.js version" |
| **Tech Debt** | Known shortcut taken deliberately, to be repaid | "RBAC scoping hardcoded for pilot, needs SF-driven lookup" |

- **Components**: one per Part A/B feature area (Farmer Profile, Journey Timeline, Identity/Match Confidence, Geo, Dashboards, Payments/Reconciliation, Case Handling, Data Quality, Remediation, AI Assistant, Notifications, Admin, Audit, Export, Bulk Data Mapper, Superset AI Builder).
- **Labels**: `mvp`, `phase-2`, `parked`, `security`, `pii`, `uat-blocker`.
- **Every PII-touching ticket gets the `pii` label** — makes security/audit review filterable.

## 4. Environments & Branching

- **Environments**: **Local → QA → UAT → PRD.**
  - **Local** — developer machine, own config/credentials, not shared. Where a change is written and first run before anyone else sees it.
  - **QA** — first shared environment. Active development, internal testing, no real stakeholder eyes yet.
  - **UAT** — promoted once a feature is ready for actual users to test (the pilot candidates from `business_requirements.md` §5). This is where the BRD's UAT gate is exercised.
  - **PRD** — production-ready, only reached once UAT sign-off is documented (per §5 Human Review Layers).
  - UAT should mirror PRD's RBAC/data-scoping behavior exactly — this is where PII leak bugs get caught before they matter.
- **Branching**: trunk-based with short-lived feature branches; PRs required into main. Promotion QA→UAT→PRD is a deliberate, gated step, not automatic on merge.
- **PR requirements [at scale]**: minimum 1 reviewer (2 for anything touching RBAC, auth, or write-back), CI green, no unresolved review comments.

## 5. Testing Strategy

This is where "internal tool" and "farmer PII, 10 countries, eventual write-back to Fineract/Odoo" both demand real rigor — worth over-investing here relative to team size.

### Functional
- **Unit tests** — business logic, RBAC scoping functions, data transformation.
- **Integration tests** — API layer ↔ `ANALYTICS.REPORTING`; verify queries return expected shape and respect row-level scoping.
- **Contract tests** — API request/response schemas, especially if multiple frontends (Wimbi web app, future mobile FO mode) consume the same API.
- **End-to-end (E2E) tests** — critical user flows per persona (e.g. CC officer logs in → searches farmer → views timeline).
- **Regression suite** — run before every release; grows with every bug fixed (bug fix without a regression test isn't done).

### Access & security
- **RBAC negative testing** — for every role, explicitly verify what they *cannot* see, not just what they can. This is the single most important test category given the PII stakes.
- **Access review testing** — periodic audit that live user scopes match SuccessFactors reality (catches stale/orphaned access).
- **Security testing** — dependency vulnerability scanning (SAST), dynamic scanning (DAST), and a periodic penetration test once external rollout is live.
- **Secrets/config audit** — no credentials in code or client-side bundles.

### Data quality
- **Source-to-REPORTING validation** — spot-check that Wimbi's numbers reconcile with known ANALYTICS REPORTING outputs (row counts, key aggregates).
- **Identity/match confidence sanity checks** — sample farmer profiles, manually verify merges are correct, especially per country now that matching strategy is country-specific.
- **Write-back validation tests** (once Feature 10 exists) — every remediation write to Fineract/Odoo must be tested for correctness and reversibility before going live.

### Non-functional
- **Performance/load testing** — Snowflake query latency under concurrent users; matters more once beyond the internal pilot.
- **Accessibility (a11y)** — WCAG-level check once this becomes a real product for a broader non-technical audience.
- **Usability testing** — run with actual pilot users (the "selective test candidates" from the BRD), not just the team.
- **Localization readiness** — 10 countries; even if English-only now, confirm date/number/currency formatting doesn't break per-country.
- **Disaster recovery** — backup/restore drill, especially once write-back exists.

### Human review layers
- **Code review** — every PR.
- **Design review** — before building a new feature area, not after.
- **Architecture review** — for anything touching the data boundary (e.g. the Fineract/Odoo write-back integration) or introducing a new external dependency (Superset MCP, DataHub MCP).
- **UAT** — the formal gate the BRD already names before any external rollout. Needs a defined sign-off owner per persona (see §1).
- **Security review** — before any release that changes auth, RBAC, or write-back behavior.

## 6. Release Management

- **Versioning**: semantic versioning once there's an external audience relying on stability.
- **Feature flags**: use them for phased rollout — matches the BRD's "select group → wider rollout after UAT" model directly. A flag per persona group is a natural fit.
- **Release notes**: even informal ones, so pilot users know what changed.
- **Rollback plan**: defined before release, not improvised during an incident.
- **[At scale]** Change Advisory Board (CAB) review for releases touching write-back or RBAC.

## 7. Observability & Operations

- **Logging**: every profile view and every write-back logged (already scoped as Feature 14, Audit Trail).
- **Monitoring/alerting**: uptime, error rates, query latency against `ANALYTICS.REPORTING`.
- **Incident management [at scale]**: severity levels (SEV1–3), on-call rotation, postmortem template — especially relevant given PII exposure is a plausible SEV1 class.
- **SLAs/SLOs**: define once external users depend on it daily; not needed for the internal pilot.

## 8. Security & Compliance

- **Data Protection Impact Assessment (DPIA)** — should happen *before* external rollout, given farmer PII across multiple countries with different data protection regimes. Not yet done — flag to Legal early, this can be a long lead-time item.
- **Periodic access reviews** — confirm RBAC scoping still matches SuccessFactors reality.
- **Data governance model** — worth adopting Rwanda's Owner/Steward/Custodian pattern (see `project_farmer360_prior_art` notes) per data domain, rather than inventing a new one.
- **Country-specific compliance** — 10 countries may have different legal requirements for farmer data; this needs Legal input, not just engineering judgment.

## 9. Documentation & Knowledge Management

- **Architecture Decision Records (ADRs)** — continue the pattern already started in `business_requirements.md` §9 (Key Decisions Log); split into per-decision ADRs once the log gets long.
- **Runbooks** — for common operational tasks (rotating a credential, handling a stuck RBAC sync, restoring from backup).
- **API docs** — once there's more than one consumer of the API layer.
- **Onboarding doc** — for the first engineer who isn't the founder; write it *before* it's needed, not during their first week.

## 10. Handover & Scale Readiness

Written specifically for the "bigger team takes this over" scenario:
- Ownership transition should hand over this playbook plus `business_requirements.md`, `features_and_user_stories.md`, and the ADR/decision log — not just the codebase.
- Everything in this doc should be revisited and re-owned explicitly (not assumed inherited) as new roles fill in — a RACI review is a good first meeting for an incoming team.
- Existing informal decisions (RBAC overrides for pilot users, manual mapping approvals, etc.) should be formalized or explicitly retired at handover, not carried forward silently.

Progress against this playbook is tracked separately in `to_do.md` — keep that one current, this doc stable.
