# Wimbi — User Acceptance Testing (v1)

**Status:** Living document — covers what's actually built today (login, dashboard, search, farmer profile, journey timeline, sales history, RBAC, the Bulk Data Mapper, the Glossary page). Re-run relevant sections after any change to these areas; extend with new sections as new features ship.
**Last updated:** 2026-09-03
**Companion to:** `jira-backlog.md` (what's built vs. not), `architectural_decisions.md` (the "why" behind anything that looks like a deliberate limitation, e.g. no phone search)

## How to use this

Each test has a **Pass/Fail** column — fill it in as you go, and a **Notes** column for anything you saw that isn't captured by the expected result. Tests are tagged:

- **[Functional]** — confirms the feature does what it's supposed to. Already covered by the automated test suite (54 pytest tests) at the HTTP/data level — running it here is a second, independent confirmation in a real browser, which is exactly how two real bugs were caught on the first pass (see UAT-4.6 and UAT-4.7 below, both already fixed).
- **[Judgment]** — something that genuinely needs a human: does this look right, does this feel right, does this number match what you know about the real business. I can't self-check these — they're the actual point of this document.

## Setup

1. Dev server: `http://127.0.0.1:8000/login/` (ask for it to be started if it isn't running).
2. Login is a **dev-only stand-in for SSO** — no password, just an email that resolves against the real directory. Use either:
   - A dev persona: `cc.malawi@oneacrefund.org` (Call Center, MW), `bizops.malawi@oneacrefund.org` (Business Ops, MW), `fieldsupervisor.malawi@oneacrefund.org` (Field Supervisor, MW), `data.team@oneacrefund.org` (Data Team, **ALL** countries)
   - Your own real SuccessFactors email, or a colleague's (with their knowledge) — this is the more valuable test since it exercises the real role-mapping (ADR-008), not a hand-picked persona.
3. Recommended: test in at least two browsers or one incognito window, so cookie/session behavior isn't masked by a browser you've been developing against all day.

---

## 1. Login & Session

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 1.1 [Functional] | Visit `/login/` while logged out | Login form renders, single email field | | |
| 1.2 [Functional] | Submit a known email (dev persona or real SF email) | Redirected to `/dashboard/`, sidebar shows your name/department/country | | |
| 1.3 [Functional] | Submit an email not in any directory (e.g. `nobody@example.com`) | Stays on login page, shows "Unknown user" error, email you typed is preserved in the field | | |
| 1.4 [Functional] | While logged out, visit `/dashboard/`, `/search/`, or a farmer URL directly | Redirected to `/login/` | | |
| 1.5 [Judgment] | Log in with **your own real SF email** | Does the department/country shown in the sidebar match what you'd actually expect for yourself? This is the real test of ADR-008's role mapping against live data, not a synthetic one. | | |
| 1.6 [Judgment] | If you know a colleague's role (with their OK to use their email), log in as them | Does their persona/scope look right to someone who knows their actual job? | | |

## 2. Dashboard

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 2.1 [Functional] | Log in as `cc.malawi@oneacrefund.org`, view dashboard | "Farmers in scope" shows a Malawi-only count, not the full dataset | | |
| 2.2 [Functional] | Log in as `data.team@oneacrefund.org`, view dashboard | "Farmers in scope" shows the full count across all countries (higher than 2.1) | | |
| 2.3 [Judgment] | Compare the "Farmers by program" bar chart against what you know of Malawi's real program mix | Do the program names and relative bar heights look directionally sensible, or is anything surprising enough to be a data issue rather than a real pattern? | | |
| 2.4 [Judgment] | Look at "Total sales value" and "Activity, last 30 days" | Do these numbers feel plausible at a glance, or wildly off (e.g. suspiciously zero, or absurdly large)? | | |
| 2.5 [Judgment] | General visual pass on the dashboard | Is the layout clean, is anything crowded/misaligned, do the stat tiles read clearly at a glance? | | |

## 3. Search

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 3.1 [Functional] | From the dashboard, click "Search" in the sidebar | Search page renders fully (input box, sidebar, title) — **not a blank page** | | |
| 3.2 [Functional] | Type a real farmer's name or partial name, pause | Matching results appear without a full page reload, within ~1 second | | |
| 3.3 [Functional] | Type a single character (e.g. "a") | Shows "Keep typing — at least 2 characters," not results and not a crash/hang | | |
| 3.4 [Functional] | Type a common short string likely to match many farmers (e.g. "an", "ma") | At most 50 results shown; if more exist, a "Showing the first 50 matches — refine your search" note appears | | |
| 3.5 [Functional] | Search for a farmer ID instead of a name (e.g. part of a `gl_client_id`) | Matches by ID as well as name | | |
| 3.6 [Functional] | Search for something that matches nothing | Shows "No farmers found for '...'" | | |
| 3.7 [Judgment] | As a country-scoped user (not Data Team), search a common name | Do all results look like they're genuinely from your own country, nothing that looks out of place? | | |

## 4. Farmer Profile

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 4.1 [Functional] | Click a search result | Farmer profile page opens: name, ID, country, primary program, onboarded date, total sales, repayment rate | | |
| 4.2 [Functional] | On the profile page | "Journey timeline" and "Sales history" sections each load in shortly after the page appears (not required to be instant, but should resolve, not spin forever) | | |
| 4.3 [Judgment] | Pick 2-3 real farmers you have some familiarity with, or can cross-check in Superset | Do total sales, repayment rate, and program assignment look directionally correct against what you know or can verify elsewhere? | | |
| 4.4 [Judgment] | Look at a farmer with a missing name (Kobo-sourced rows sometimes lack one, per ADR-006) | Does "(no name on file)" read acceptably, or is this confusing/alarming to someone unfamiliar with the data gap? | | |
| 4.5 [Functional] | As a country-scoped user, manually edit the URL to a farmer ID from a different country (e.g. try a `GL-KE-...` or `GL-RW-...` ID while logged in as `cc.malawi@`) | Blocked (403 Forbidden) — you should not be able to view another country's farmer by guessing/typing a URL | | |
| 4.6 [Functional, already fixed] | Regression: click "Search" in the sidebar from any other page | Renders the full search page correctly (this was blank until 2026-09-02 — see `to_do.md`) | | |
| 4.7 [Functional, already fixed] | Regression: search a single common letter | Shows the "keep typing" message, doesn't hang or crash the page (a `q=g` search once returned a 113MB response and crashed the whole dev server — see `to_do.md` and ADR-010) | | |

## 5. Journey Timeline

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 5.1 [Functional] | View a farmer with activity | Timeline shows events (Sale / Loan Disbursed / Buyback only — real data has no other event types yet, per ADR-006) in reverse-chronological order, each with a date, program, and amount where applicable | | |
| 5.2 [Functional] | View a farmer with no journey events on file | Shows "No journey events on file," not an error or blank section | | |
| 5.3 [Judgment] | Cross-check a real farmer's timeline against what you'd expect from their profile stats (e.g. total sales, total loans) | Does the timeline's event count/amounts roughly reconcile with the summary numbers at the top of the profile? | | |

## 6. Sales History

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 6.1 [Functional] | View a farmer with sales | Table shows date, product, quantity, total, field officer per line item | | |
| 6.2 [Functional] | View a farmer with no sales lines on file | Shows "No sales line items on file" | | |
| 6.3 [Judgment] | Check product names and field officer names against what you'd expect for that program/region | Does anything look like a data-quality issue (garbled product name, obviously wrong field officer) rather than a display bug? | | |

## 7. Logout

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 7.1 [Functional] | Click "Log out" | Redirected to `/login/`; visiting `/dashboard/` afterward redirects back to login (session actually cleared, not just hidden) | | |
| 7.2 [Functional] | Try to reach `/logout/` directly via GET (typing the URL) | Should not log you out via a bare GET (logout requires a POST, to avoid accidental/drive-by logout) | | |

## 8. Overall Impression [Judgment]

| ID | Question | Notes |
|---|---|---|
| 8.1 | Does the interface feel clean and professional, or is anything visually off (spacing, alignment, color)? | |
| 8.2 | Is anything confusing about the flow (login → dashboard → search → profile) that a first-time user (e.g. a call center officer, not you) might stumble on? | |
| 8.3 | Resize the browser window narrower — does anything break badly? (Mobile/tablet wasn't a design target yet, but worth knowing how badly it degrades.) | |
| 8.4 | Anything from `features_and_user_stories.md` you expected to see here and didn't — check `jira-backlog.md` first in case it's already tracked as not-yet-built, then flag anything that looks like a genuine miss. | |

## 9. Bulk Data Mapper / Uploader

The full funnel → map → preview → save path was already exercised live on 2026-09-03 with a real 1,000-row Malawi registration file (`mw_lr26 registration data.csv`) and reached a genuine "Saved — rows committed" state, so the core round trip is confirmed working, not just unit-tested. The table below is for a fresh, deliberate pass — some rows describe things already seen working in that run; others (marked) are pure client-side JS behavior added afterward that hasn't had a live look yet, since this environment has no browser tool of its own.

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 9.1 [Functional] | Start a new upload, pick a Country | Program dropdown updates to that country's real programs (from `DimProgram`); picking a Program updates Source system to that program's real systems (from `DimSystem`) | | |
| 9.2 [Functional] | Pick "Other…" on Program, Source system, or Location type | A text box appears; whatever you type becomes the stored value, not the literal word "Other" | | |
| 9.3 [Functional] | Set a Source system, then reach the mapping page | A locked banner shows the source system, applied to every row; it's not a choosable option in any column's dropdown | | |
| 9.4 [Functional] | Check 2+ entities on the funnel | Only those entities' variables appear in the mapping dropdown; the "Required for..." banner lists the union of their lineage requirements | | |
| 9.5 [Judgment] | Pick a country/program combo you know well | Do the real cascading options (program names, systems) match what you'd actually expect for that country? | | |
| 9.6 [Functional] | On the mapping page, map a column, then open another column's dropdown | The already-mapped variable no longer appears as an option there (except "Pivoted product quantity", which stays available everywhere) — **not yet live-verified, added in the 2026-09-03 polish round** | | |
| 9.7 [Functional] | Check the Stats column for a column you know is a real unique id vs. one you know repeats | % unique is high for the id-like column, low for the repeating one; an all-blank column shows near-0% unique, not a misleadingly high number | | |
| 9.8 [Functional] | For a required field with no clean source column, open "Build from multiple columns" and check 2+ | The field shows satisfied in the checklist; after saving, the preview page tags that column "(synthetic)" | | |
| 9.9 [Functional] | Click "Validate and preview" while a required field is still genuinely missing | First click expands the synthetic-key section and scrolls to it rather than submitting; a second click goes through | | |
| 9.10 [Functional] | Try the column-header drag handles and the sort arrows on the mapping table | Columns resize by dragging; clicking a sortable header (Mapped/Your column/Maps to) reorders rows, clicking again reverses | | |
| 9.11 [Functional] | On the preview page, with at least one row missing a required field | Banner says a row is missing at least one required field (not a list of every field name) — the specific missing field(s) are shown per-row further down | | |
| 9.12 [Judgment] | General visual pass on all 3 uploader screens, in both light and dark mode | Anything crowded, misaligned, or hard to read in either theme? | | |
| 9.13 [Functional] | Visit `/glossary/` as any logged-in user (not just an uploader) | Page loads without a 403; search and the Shared/Single-entity/Save-gate filter chips narrow the table live | | |

## 10. Theme & Layout

| ID | Steps | Expected | Pass/Fail | Notes |
|---|---|---|---|---|
| 10.1 [Functional] | Click the dark-mode toggle in the sidebar | Page switches theme and reloads; the choice persists across a fresh visit/new tab | | |
| 10.2 [Functional] | Click the sidebar collapse toggle | Sidebar shrinks to icons only; labels reappear on expand; the collapsed/expanded state persists across a reload — **not yet live-verified** | | |
| 10.3 [Judgment] | Dashboard chart colors, sales table, and any red/green status text in dark mode | Do the colors still read clearly against the dark background, nothing washed out or illegible? | | |

---

## Known, deliberate gaps (not bugs — don't re-report these)

- **No phone number search** — real `V_CLIENT_REACH` has no phone column (ADR-006). Name/ID only.
- **No repayment or tree events in the timeline** — real `V_CLIENT_JOURNEY` only has Sale / Loan Disbursed / Buyback (ADR-006).
- **No match-confidence badge or lineage drill-down** — deferred by design (ADR-005, Epic 3 in `jira-backlog.md`).
- **Dashboard is intentionally lightweight** — 4 stat tiles + 1 chart, not a Superset replacement (see the dashboard's own subtitle).
- **Single-country data** — only Malawi has real data today; the two other countries visible to Data Team accounts (`GL-KE-...`, `GL-RW-...`) are synthetic test fixtures, not real farmers.
- **Bulk uploader is file-upload only** — no Google Sheets or Snowflake/Dataiku connectors, no AI-assisted mapping suggestions, no Data Team approval workflow, and no promotion ETL into `ANALYTICS.SOURCES` yet — all named v1.2+ in `bulk-uploader.md`.
- **Season/Operational year are optional funnel fields** — Season only offers the 3 closest seasons to today for the chosen country (by design, see `bulk-uploader.md`); it's not meant to cover arbitrary historical backfills.
