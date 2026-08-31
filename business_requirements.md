# Wimbi (Farmer 360) — Business Requirements (High Level)

**Author:** Augustin Faraja, Business Analyst — One Acre Fund
**Status:** Draft — requirements phase
**Last updated:** 2026-08-31

---

## 1. Background

ANALYTICS (see `docs/documentation.md`) solved the data problem: a deduplicated, cross-country, cross-program client record (`gl_client_id`) with clean facts and REPORTING views on top. It answers *"what is true"* for a farmer across systems.

**"Farmer 360" is the umbrella name for the vision of a unified farmer view at OAF — this project's product is called Wimbi.** It's the interactive, role-based application that lets OAF staff actually *use* that unified view day to day, instead of only consuming it through static dashboards or per-source tables.

Farmer 360 as a name is also used by country-level initiatives (Rwanda's "Farmer 360 view", Kenya's "Customer 360" — see `entities-private/360/`). No conflict: Farmer 360 is the shared global name and direction; other countries are expected to align to it rather than diverge further. Wimbi is the specific product being built.

## 2. Problem Statement

Countries have not adopted ANALYTICS yet. In practice, staff across roles still consume **source-level production tables directly** (e.g. `fineract_repayments`, `odoo_sales`) — the output of data engineering pipelines, not a unified layer. There is no product, anywhere, that lets someone see all of a farmer's activity in one place.

This means the original ANALYTICS problem statement still stands at the point of use: a farmer enrolled in Credit (Fineract), who also buys trees (Kobo/Odoo) and sells produce (buyback), is invisible as *one* person to anyone working from these source systems. Wimbi is what turns the ANALYTICS deduplication work into something people can actually use to answer *"who is this farmer, and what is their full history with OAF?"*

## 3. Objective

Deliver a single, role-based web application, built primarily on `ANALYTICS.REPORTING`, that gives each user type the farmer-level and program-level view they need, with access properly scoped to who they are.

## 4. Users & Needs

| Persona | Size | Context | Primary need | Rollout status |
|---|---|---|---|---|
| **Call center officers** | 100s | HQ, laptops | Look up a farmer's full details fast, repeatedly, to handle inbound queries | First external persona (post-UAT) |
| **Business operations officers** | 100s | HQ, laptops | Farmer payment/loan details for reconciliation and escalations raised by call center/field | Later phase |
| **Field supervisors/leads** | 100s | Regional offices, internet | How their district/region is performing | Later phase |
| **Program executives** | 10s | HQ, internet | Cross-country trends to inform scaling/budget decisions | Later phase (also blocked on multi-country ANALYTICS data) |
| **Field officers** | ~7,000 | Field, tablets, offline-first | Their own client portfolio | Out of scope for now — offline-first delivery is a separate project. FOs themselves are in SuccessFactors; the identity gap is limited to casual/seasonal distribution workers (mainly tree program) hired at distribution time. |

All personas above are who Wimbi is being built *for*. Access for any of them beyond the internal pilot is gated on UAT — see §5.

## 5. MVP Definition

- **Target date:** October 2026
- **Audience for October:** internal — the data team, plus selective test candidates pulled from the user groups above. **Not** a rollout to call center/business ops/etc. as functioning teams yet.
- **Path to wider release:** external rollout (starting with call center) happens once the product has passed UAT, testing, validation, and relevance review — expected sometime next year (2027). No fixed date yet.
- **Geographic scope:** Malawi data for now. Not a hard restriction — other countries become available automatically as they're onboarded into ANALYTICS, with no rework needed on Wimbi's side.
- **Access control:** enforced from day one (see §7), even for the internal pilot — this is farmer PII regardless of audience size.

### MVP shape
A cloud-hosted web app that a select group can log into, navigate, and explore a farmer's 360 view through whatever features are available at the time — starting with:
1. **Farmer search & profile lookup** — find a farmer, see their identity and core details.
2. **Farmer Journey Timeline** — cross-entity history (enrollment → sale → loan → repayment → tree/carbon → buyback), sourced from `V_CLIENT_JOURNEY`.
3. Role-based sign-in via Keycloak SSO, scoped by SuccessFactors-derived role/country/department.

### On scope generally
Feature scope is intentionally not locked down further than this. What's "in" vs "later" may shift as we build — the approach is to build ambitiously and let time be the natural constraint, not a pre-set exclusion list. §6 is a running set of candidates, not a committed backlog or a rejected list.

## 6. Candidate Features (fluid — not committed, not excluded)

- **Match confidence badge** — surface identity-resolution confidence on a farmer profile; doubles as a QA feedback loop into the MASTER dedup pipeline.
- **Geo view** — map farmers/sites/nurseries, shaded by reach/sales/at-risk concentration.
- **Seasonal cohort funnel** — track a `DIM_SEASON` cohort through enrolled → disbursed → repaid → harvest sale.
- **Anomaly feed** — surface data-quality issues (e.g. FO client-count spikes, oversized dedup clusters) back to the DE team.
- **Conversational/AI assistant** — natural-language self-service querying, inspired by Rwanda's Datapedia "WebApp Assistant."
- **Two-way remediation workflows** (future, see §7) — review/edit flows against Fineract/Odoo directly from Wimbi, e.g. correcting a farmer record at the source.

## 7. Non-Functional Requirements

- **Authentication:** Keycloak SSO (Google-authenticated emails).
- **Authorization:** derived from SuccessFactors (email → country → department), enforcing role-based scoping — e.g. a country lead sees only their country, an FO (future) sees only their own portfolio.
- **PII handling:** this is farmer beneficiary data — access control is a requirement, not an enhancement, from day one, regardless of whether the audience is internal or external.
- **Hosting:** AWS, cloud-hosted, accessible to select login groups.
- **Data boundary — MVP:** reads primarily from `ANALYTICS.REPORTING`, preserving the same layer discipline as the rest of ANALYTICS.
- **Data boundary — future:** scope is expected to extend beyond read-only REPORTING consumption. Planned direction: custom integration with Fineract and Odoo via APIs, enabling **two-way communication** — not just viewing data, but reviewing and editing it (remediation workflows) directly from Wimbi.
- **Architecture:** custom web app (Next.js + thin API layer), not a BI tool (Superset/Streamlit) or a modified operational system (Odoo) — see decision log in §9.

## 8. Success Criteria (draft — needs stakeholder sign-off)

- Internal pilot users (data team + selected test candidates) can log in, navigate, and explore a farmer's 360 view without support.
- RBAC correctly scopes every pilot user with zero incidents of over-exposed data.
- Product passes UAT, testing, validation, and relevance review as the gate for any wider rollout.

## 9. Key Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Build approach | Custom web app on AWS | Only option giving real RBAC, real interactivity, and no re-coupling to a single source system (unlike modifying Odoo) |
| Product name | Wimbi | Distinct product name under the shared "Farmer 360" direction; avoids ambiguity with country-level "Farmer 360"/"Customer 360" initiatives while staying aligned to the same vision |
| October scope | Internal tool only | External rollout (call center first) is gated on UAT/testing/validation passing, not a fixed date |
| Geographic MVP scope | Malawi data, extensible | Only country fully validated in ANALYTICS today; other countries flow in automatically as ANALYTICS onboards them |
| RBAC timing | Day one | Farmer PII; retrofitting access control after rollout is high-risk and hard to unwind, regardless of audience size |
| Auth/authorization source | Keycloak + SuccessFactors | Already exists; avoids building an identity system from scratch |
| Identity/dedup matching strategy | Country-specific, not uniform | Strongest available identity variables differ by country (e.g. NID in Rwanda vs name/location fuzzy matching elsewhere) — the MASTER pipeline's matching approach adapts per country rather than using one fixed method globally |

## 10. Open Questions

- What does UAT / "passed testing, validation, and relevance" concretely require before external rollout begins?
- Should Kenya (Dennis Macharia) and Rwanda (Innocent, BIA team) be looped in on the shared "Farmer 360" direction, given their existing country-level work?
- What's the concrete design for two-way Fineract/Odoo integration (auth model, write-back validation, conflict handling) — deferred until after MVP, but worth flagging early given its architectural weight.
