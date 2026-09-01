# Wimbi — Feature Catalog & User Stories

**Status:** Draft — brainstorm, not scoped/prioritized
**Last updated:** 2026-08-31
**Companion to:** `business_requirements.md`

This is a wide net, per the BRD's approach: build ambitiously, let time cut scope naturally rather than pre-excluding. Nothing here is committed or rejected — see `business_requirements.md` §5–6 for what's actually targeted for the October internal MVP.

Personas: **CC** = Call center officer · **BO** = Business ops officer · **FS** = Field supervisor/lead · **PE** = Program executive · **FO** = Field officer (parked) · **DT** = Data team (internal, all-access) · **BU** = Business/program user contributing raw data (new, see §18)

---

## Feature × Persona Map

| Feature area                                     | CC  | BO  | FS  | PE  | FO  | DT  | BU  |
| ------------------------------------------------ | --- | --- | --- | --- | --- | --- | --- |
| 1. Farmer Search & Profile                       | ✔   | ✔   | ✔   |     | ✔   | ✔   |     |
| 2. Farmer Journey Timeline                       | ✔   | ✔   |     |     | ✔   | ✔   |     |
| 3. Identity & Match Confidence                   | ✔   |     |     |     |     | ✔   |     |
| 4. Geo Explorer                                  |     |     | ✔   | ✔   | ✔   | ✔   |     |
| 5. Program & Portfolio Dashboards                |     |     | ✔   | ✔   |     | ✔   |     |
| 6. Seasonal Cohort Funnel                        |     |     | ✔   | ✔   |     | ✔   |     |
| 7. Payments & Reconciliation Workspace           |     | ✔   |     |     |     | ✔   |     |
| 8. Case & Escalation Handling                    | ✔   | ✔   | ✔   |     |     | ✔   |     |
| 9. Data Quality & Anomaly Feed                   |     |     |     |     |     | ✔   |     |
| 10. Remediation / Two-Way Edit (future)          |     | ✔   |     |     |     | ✔   |     |
| 11. Conversational AI Assistant (in-app Q&A)     | ✔   | ✔   | ✔   | ✔   |     | ✔   |     |
| 12. Notifications & Alerts                       | ✔   | ✔   | ✔   | ✔   |     |     |     |
| 13. Admin & Access Management                    |     |     |     |     |     | ✔   |     |
| 14. Audit Trail / Activity Log                   |     |     |     |     |     | ✔   |     |
| 15. Export & Reporting                           |     | ✔   | ✔   | ✔   |     | ✔   |     |
| 16. Country/Program Switcher                     |     |     | ✔   | ✔   |     | ✔   |     |
| 17. Field Officer Mode (parked)                  |     |     |     |     | ✔   |     |     |
| 18. Self-Service Bulk Data Mapper                |     |     |     |     |     | ✔   | ✔   |
| 19. AI-Assisted Superset Chart/Dashboard Builder |     | ✔   | ✔   | ✔   |     | ✔   | ✔   |

Features 18–19 are adjacent data-platform capabilities, not farmer-profile consumption features — see Part B below.

---

## Part A: Core Farmer 360 Product Features

## 1. Farmer Search & Profile
Core entry point — find a farmer, see who they are.

- As a **CC officer**, I want to search a farmer by name, phone number, or account ID, so I can pull up their record while on a call.
- As a **CC officer**, I want to see a farmer's core identity (name, location, programs enrolled in, join date), so I can confirm I have the right person before discussing their account.
- As a **BO officer**, I want to open a farmer's profile from a payment record, so I can see who a transaction belongs to without switching systems.
- As a **FS**, I want to search for any farmer in my district, so I can review their status ahead of a visit.
- As a **DT** user, I want to search across all countries/programs regardless of role scoping, so I can debug data issues.

## 2. Farmer Journey Timeline
The signature feature — one farmer's full cross-entity history.

- As a **CC officer**, I want to see a chronological timeline of a farmer's enrollments, sales, loans, repayments, and buybacks, so I can answer questions without hopping between systems.
- As a **BO officer**, I want to see a farmer's full loan/repayment history in one timeline, so I can investigate a reconciliation discrepancy quickly.
- As a **FO** (future), I want to see my own client's history before a visit, so I can prepare relevant follow-up.
- As a **DT** user, I want to filter the timeline by entity type (sale, loan, payment, tree, buyback), so I can isolate the activity relevant to an investigation.

## 3. Identity & Match Confidence
Trust and QA layer on top of the dedup pipeline.

- As a **CC officer**, I want to see a confidence indicator on a merged farmer profile, so I know how sure the system is this is one real person before I act on it.
- As a **DT** user, I want to drill into which source records were merged into a `gl_client_id`, so I can audit or correct bad matches.
- As a **DT** user, I want to flag a profile as incorrectly merged/split, so the MASTER pipeline's rules can be improved over time.

## 4. Geo Explorer
Spatial view of reach and risk.

- As a **FS**, I want to see farmers, sites, and nurseries on a map of my district, so I can spot coverage gaps.
- As a **PE**, I want a map shaded by sales density or at-risk loan concentration by region, so I can spot where intervention is needed.
- As a **FO** (future), I want to see my nearest clients on a map, so I can plan an efficient visit route.

## 5. Program & Portfolio Dashboards
Reuses existing REPORTING views (`V_PROGRAM_SUMMARY`, `V_FO_PERFORMANCE`, `V_LOAN_PORTFOLIO`) behind an interactive UI instead of static Superset.

- As a **FS**, I want to see my district/region's program health (enrollment, sales, repayment rate) at a glance, so I know where to focus.
- As a **FS**, I want to see FO performance within my team, so I can coach underperformers.
- As a **PE**, I want to compare program performance across countries, so I can make scaling/budget decisions. *(blocked until multi-country ANALYTICS data lands)*

## 6. Seasonal Cohort Funnel
Track a season's enrollment cohort through its lifecycle.

- As a **FS**, I want to see what % of an enrolled season cohort went on to receive a loan, repay, and sell, so I can spot where farmers are dropping off.
- As a **PE**, I want to compare cohort funnels across seasons/years, so I can evaluate whether program changes are improving outcomes.

## 7. Payments & Reconciliation Workspace
Business ops' core operational need.

- As a **BO officer**, I want to see a farmer's payment and loan ledger reconciled against expected disbursement/repayment schedules, so I can spot discrepancies.
- As a **BO officer**, I want to filter for farmers with unresolved payment issues, so I can prioritize my queue.
- As a **BO officer**, I want to attach a note or resolution status to a payment discrepancy, so the case has a record.

## 8. Case & Escalation Handling
Connects call center → business ops/field, per BO's stated need to handle "anything raised by either call center or field team."

- As a **CC officer**, I want to raise a case against a farmer's profile when I can't resolve their query, so it reaches the right team.
- As a **BO officer**, I want to see all open cases assigned to me, linked to the relevant farmer profile, so I have context without re-asking the farmer.
- As a **FS**, I want to see cases raised about farmers in my district, so I can support resolution in the field.
- As a **CC officer**, I want to see the status of a case I raised, so I can follow up with the farmer if they call back.

## 9. Data Quality & Anomaly Feed
Internal-facing, feeds back into the pipeline rather than being a farmer-facing feature.

- As a **DT** user, I want to be alerted when an FO's client count changes abnormally, so I can check for a data issue.
- As a **DT** user, I want to see oversized or suspicious dedup clusters flagged automatically, so I can review MASTER pipeline output before it reaches users.
- As a **DT** user, I want a running log of data quality metrics per source table, so I can track improvement over time (mirrors Rwanda's Owner/Steward/Custodian model).

## 10. Remediation / Two-Way Edit (future — architecturally significant)
Beyond MVP; requires direct Fineract/Odoo API integration.

- As a **BO officer**, I want to correct a farmer's phone number or NID directly from Wimbi, so the fix propagates back to the source system instead of living only in ANALYTICS.
- As a **CC officer**, I want to submit a data correction request from a farmer's profile during a call, so BO can review and apply it.
- As a **DT** user, I want every write-back to Fineract/Odoo to be logged and reversible, so remediation doesn't introduce new data integrity risk.

## 11. Conversational AI Assistant
Inspired by Rwanda's Datapedia "WebApp Assistant."

- As a **CC officer**, I want to ask a natural-language question about a farmer ("has this farmer missed any repayments?"), so I don't need to know which view/field holds the answer.
- As a **PE**, I want to ask cross-country questions in natural language ("which country has the highest repayment rate this season?"), so I can explore data without a BI ticket.
- As a **DT** user, I want the assistant's answers traceable to the underlying REPORTING view/query, so I can verify accuracy.

> **Distinct from Feature 19.** This is a bounded, read-only Q&A assistant scoped to `REPORTING` views inside Wimbi — it answers questions, it doesn't create anything. Feature 19 is a separate, more powerful capability (authoring new Superset charts/dashboards, potentially over a broader dataset set) with a correspondingly higher governance bar. They could plausibly share the same underlying MCP infrastructure, but the two need different guardrails — see §19.

## 12. Notifications & Alerts
- As a **BO officer**, I want to be notified when a case is assigned to me, so I don't have to poll a queue.
- As a **FS**, I want a weekly digest of my district's key metrics, so I stay informed without logging in daily.
- As a **PE**, I want to be alerted to significant metric swings (e.g. repayment rate drop), so I can react quickly.

## 13. Admin & Access Management
- As a **DT** user (admin), I want to see which SuccessFactors-derived role/country a user is scoped to, so I can troubleshoot access issues.
- As a **DT** user (admin), I want to manually override a user's scope for the internal pilot, so I can onboard selective test candidates ahead of full SF-driven rollout.
- As a **DT** user (admin), I want to see a list of all users who've logged in and their last activity, so I can track pilot engagement.

## 14. Audit Trail / Activity Log
Important given PII and (eventually) write-back.

- As a **DT** user, I want every profile view logged (who viewed which farmer, when), so we can demonstrate PII access discipline.
- As a **DT** user, I want every remediation edit logged with before/after values and the user who made it, so changes are fully traceable.

## 15. Export & Reporting
- As a **BO officer**, I want to export a reconciliation list to CSV, so I can work offline or share with finance.
- As a **PE**, I want to export a program summary for a board deck, so I don't have to manually rebuild charts.
- As a **FS**, I want to schedule a recurring export of my district's dashboard, so I don't have to remember to pull it.

## 16. Country/Program Switcher
Groundwork for the "extensible beyond Malawi" requirement.

- As a **FS**, I want to switch between countries/programs I have access to, so I don't need multiple logins if I ever cover more than one.
- As a **PE**, I want a single view spanning all countries I'm scoped to, so I don't have to switch back and forth to compare.
- As a **DT** user, I want new countries to appear automatically in the switcher once ANALYTICS onboards them, so no Wimbi-side rework is needed per country.

## 17. Field Officer Mode (parked — offline-first, separate project)
Captured for completeness per the BRD; not scoped now.

- As an **FO**, I want to view my own client list even without connectivity, so I can work in the field.
- As an **FO**, I want changes I make offline to sync once I'm back online, so I don't lose work.
- As an **FO**, I want a simplified, low-bandwidth version of the farmer profile, so it loads on a low-end tablet in poor network conditions.

---

## Part B: Adjacent Data Platform Features
These two don't fit the "view a farmer" pattern of Part A — they're about the data platform Wimbi and ANALYTICS sit on. Both are ambitious enough to be separate projects in their own right; captured here because they're directly connected to Wimbi and to each other.

## 18. Self-Service Bulk Data Mapper
Addresses a recurring real problem: ad-hoc business datasets (Kobo-like exports, one-off program data) arriving with no path into ANALYTICS except a data engineer hand-writing a `SOURCES` view. Instead: a place to upload a dataset and conversationally map its columns to the existing canonical glossary of variables/metrics, so it can flow into ANALYTICS without bespoke engineering per dataset.

- As a **BU**, I want to upload a Kobo-like dataset (CSV/Excel), so I don't have to file a ticket and wait on the data team for a one-off collection.
- As a **BU**, I want to be guided conversationally to map my dataset's columns to the existing glossary of variables and metrics, so my data becomes usable without me needing to understand the underlying schema.
- As a **BU**, I want to see which of my columns didn't match anything in the glossary, so I know what's genuinely new versus what I mislabeled.
- As a **DT** user, I want to review and approve a business user's proposed mapping before it lands in `SOURCES`, so a bad mapping doesn't silently corrupt the global data model.
- As a **DT** user, I want a mapping that's already been approved once (e.g. last season's version of the same Kobo form) to be suggested automatically next time, so the same dataset shape isn't remapped from scratch every cycle.
- As a **DT** user, I want an accepted mapping to generate or update a `SOURCES` view automatically, so onboarding a new dataset doesn't require hand-written SQL.
- As a **DT** user, I want a log of who mapped what, when, and what was approved/rejected, so mapping decisions are auditable (same theme as Feature 14).

**Open question:** where does "the existing glossary of variables and metrics" actually live today (referenced as mapped in a Q1 report) — is it a document, a spreadsheet, or could it become the DataHub catalog mentioned in §19? Worth resolving, since the mapper's usefulness depends entirely on the glossary being the real source of truth.

## 19. AI-Assisted Superset Chart & Dashboard Builder
Builds on an existing separate effort (Superset MCP, in progress in another repo) plus DataHub MCP (newly learned about, not yet explored) — a frontend letting business users build Superset charts/dashboards conversationally instead of through Superset's native chart builder.

- As a **PE**, I want to describe the chart I want in plain language ("compare repayment rate by country this quarter"), so I get a chart without filing a BI request.
- As a **FS**, I want to ask for a chart scoped to just my district/program, so I don't need to learn Superset's UI.
- As a **BO**, I want to build a quick exploratory chart from a reconciliation dataset during an investigation, so I'm not blocked on a BI ticket.
- As a **BU**, I want to turn a dataset I've onboarded via the Bulk Data Mapper (§18) straight into a chart, so self-service goes from raw data to insight without a handoff to BI.
- As a **DT** user, I want the assistant restricted to governed datasets/metrics (not arbitrary raw tables), so this doesn't become a shadow-BI risk.
- As a **DT** user, I want generated charts/dashboards saved as normal Superset assets, so they inherit Superset's existing permissions and governance rather than living in a parallel system.
- As a **DT** user, I want the assistant to draw on DataHub's catalog (dataset/column definitions, lineage) when interpreting a request, so it's grounded in the same glossary business users rely on in §18 — one shared source of truth for "what does this field mean," not two.

**Connection worth noting:** DataHub (catalog + lineage + business glossary) could plausibly be the shared metadata backbone for *both* new features — the glossary that §18's mapper maps *into*, and the glossary that §19's assistant reasons *from*. Worth evaluating before building either in isolation.

---

## Notes on prioritization (not decided here)
- Features 1–3 are the clearest fit for the October internal MVP — they're what a call center officer or the data team would exercise first, and reuse `V_CLIENT_JOURNEY` directly.
- Features 5–6 reuse existing REPORTING views almost as-is — cheap to add once the app shell exists.
- Features 10 and 17 carry real architectural weight (write-back integration, offline sync) and are natural phase-2+/parked items regardless of how ambitious we want to be elsewhere.
- Feature 8 (case handling) is worth flagging early even if not MVP — it's the connective tissue between call center and business ops that the persona interviews implied but that no other feature covers.
- Features 18–19 are big enough to be their own projects and don't block the October internal MVP (which is Part A only) — but they share a dependency worth resolving early: what "the glossary" actually is.
