# Local vs Cloud

**Snapshot verified 2026-09-10** — every number and fact below was checked directly (`docker compose exec` queries against local Postgres, `pg_proc`/`information_schema` lookups, a full local test run), not recalled from memory. Re-verify before trusting this doc once real time has passed — it will drift.

## Infrastructure & tooling — deliberately different, not a gap

| | Local | Cloud (AWS) |
|---|---|---|
| Provisioning | Docker Compose (`postgres:17`, `redis:7` — dependencies only) + `infra/postgres/init.sql`, run once via `docker-entrypoint-initdb.d` | Terraform (`infra/aws/`) — VPC, RDS, ECS Fargate, ALB, ECR, IAM, Secrets Manager, S3+DynamoDB state backend |
| App process | `manage.py runserver`, run natively via PowerShell — **not containerized** | `granian` under ECS Fargate, built into a Docker image, pushed to ECR |
| Why | A single developer's own machine has no need for infra-as-code, environment promotion, or state locking. Docker Compose + native shell commands are the right tool here. | Multiple planned environments (prod/qa/uat), infrastructure that needs to be reproducible and auditable. Terraform is the right tool there. |

Neither side is behind — they're matched to what each environment actually needs. Worth stating explicitly so this doesn't get "fixed" into unnecessary symmetry later.

## Database schema — this is where real divergence lives

**`analytics_mirror.*` locally are real physical tables**, populated via `load_csv_snapshot` (real historical CSV extracts) and `seed_mock_analytics_mirror` (small synthetic fixtures, mainly for tests). Verified row counts, 2026-09-10:

| Table | Local rows | Notes |
|---|---|---|
| `bridge_client_source_ids` | 1,734,927 | Real data |
| `repayment_transaction` | 4,321,246 | Real data — exact match to the model's own docstring count |
| `sales_line` | 2,301,490 | Real data |
| `v_client_journey` | 1,538,237 | Real data |
| `v_client_reach` | 1,305,497 | Real data |
| `sf_employees` | 10,074 | Real data |
| `dim_country` / `dim_mcf` / `dim_program` / `dim_season` / `dim_system` / `program_summary` | 10 / 7 / 29 / 171 / 218 / 62 | Small by nature (real dimension-table scale, not a reduced sample) |
| `loan_portfolio` | 0 | Never loaded locally |
| `fo_performance` | 0 | Never loaded locally |

**`analytics_mirror.*` on AWS are views** over `analytics_mirror_raw` (Airbyte's Snowflake landing schema, see `infra/postgres/analytics_mirror_views.sql`) — no physical storage of mirrored data in that schema at all, live pass-through. Real Snowflake-fed data, but mid-backfill and currently throttled (RDS CPU credit exhaustion, this session's live incident) — so as of right now, cloud counts for the big fact tables are partial and, for some tables, actually behind local's. That flips once the backfill finishes.

**Two concrete, real functional consequences of the table-vs-view split — not just structural trivia:**

1. **Country normalization is duplicated, not shared.** `country_codes.py` (Python) is the only normalization path locally. On AWS, `analytics_mirror.to_iso_country()` (a hand-written SQL function) does the same job for the 4 fields that need it (`v_client_reach.country_code`, `v_client_journey.country_code`, `sales_line.country_code`, `bridge_client_source_ids.source_country_code`). **Confirmed absent locally** (`SELECT proname FROM pg_proc WHERE proname = 'to_iso_country'` → 0 rows). If `country_codes.py`'s mapping ever changes without its SQL twin being updated too, these fields would silently disagree between environments. Already flagged in the SQL file's own comment — repeated here because it's exactly the kind of thing that's easy to forget mid-feature-work.
2. **Surrogate ids behave differently.** Locally, `JourneyEvent`/`SalesLine`/`LoanPortfolio`/`ProgramSummary`/`RepaymentTransaction` have real Django-generated auto-increment `id` columns — genuinely stable. On AWS, those same models' `id` comes from a per-query `ROW_NUMBER()` in the view — stable only within one query's execution, not guaranteed across requests. Code or a test that assumes id stability across requests could pass locally and be wrong on AWS.

## App runtime

| | Local | Cloud |
|---|---|---|
| `DJANGO_DEBUG` | `True` | `False` |
| Static files | Served directly by Django's dev server | WhiteNoise, `collectstatic` at container start |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` (default) | ALB DNS name (real domain once OAF provides one) |
| TLS | N/A | Deferred — HTTP only, waiting on `*.oneacrefund.org` |

## Deployment — git in sync is not the same as AWS being up to date

Local: a code change is live the moment the dev server reloads — no separate deploy step. Cloud: a code change needs an explicit `docker build` / `ecr push` / `aws ecs update-service --force-new-deployment` sequence. **Pushing to `main` does not update the running ECS task by itself.** Both machines showing the same `git log` says nothing about whether AWS is actually running that code — worth remembering before assuming a bug fix is live in the cloud just because it's committed.

## `bulk_uploader` — real, local-only work

17 `UploadedDataset` rows exist locally; none have been migrated to RDS yet. Still open from the original AWS migration plan — RDS has no simple path from a local machine, and this hasn't been made easy yet the way the analytics-side one-off `ecs run-task` pattern has.

## Test coverage

103 tests passing locally as of this snapshot (`pytest`, ~90s). No equivalent automated suite runs against AWS — cloud verification so far has been manual (row-count checks, Adminer/pgAdmin spot checks, one exact-match proof against `dim_program`/`dim_season`/`dim_system`/`dim_mcf`).

---

## Dev → prod strategy

**Core principle: local is the default, fast loop for almost everything. A cloud pass is reserved for what only cloud can actually tell you** — not used as a general-purpose validation step for everything, which would just import today's AWS slowness into daily development.

**Local alone is sufficient for:**
- Anything in `bulk_uploader`, `accounts`, RBAC, UI/frontend behavior, general business logic — the local test suite + a manual walkthrough is the bar, no cloud round-trip needed to call it done.
- Anything reading the 6 `analytics_mirror` tables that already hold real, large local data (`bridge_client_source_ids`, `repayment_transaction`, `sales_line`, `v_client_journey`, `v_client_reach`, `sf_employees`) — local already offers genuine scale for search/pagination/query-shape testing on these specifically. No need to wait on AWS to validate that class of work.

**A cloud pass is actually needed before calling something done when it touches:**
1. The 4 country-normalized fields — since local and cloud run that logic through two separately-maintained copies, a change to `country_codes.py` needs its SQL twin (`to_iso_country()`) updated too, and only AWS can verify the SQL side.
2. The `ROW_NUMBER()` surrogate ids on the 5 keyless views — local's real auto-increment ids can't catch a bug that only shows up against the view's per-query renumbering.
3. New `analytics_mirror` entities being onboarded (the 7 raw-synced-but-not-modeled tables in `public.wimbi_analytics_mapping`) — real Snowflake-shaped data only exists on AWS right now.
4. Genuine infra/deployment changes — anything under `infra/aws/`, `Dockerfile`, `docker-entrypoint.sh`, or `config/settings.py`'s production-only branches.

**Promotion rhythm:**
- Keep committing to `main` for locally-validated work, same as now — no heavier branching model needed for what's currently close to a one-person team.
- Treat an actual AWS deploy as a deliberate, batched action — group up a stretch of locally-validated commits, then do one build/push/deploy + targeted smoke-check, rather than round-tripping AWS on every commit.
- Update this doc's snapshot whenever a real cloud-validation pass happens, so it stays a live record of what's actually been proven at scale rather than going stale.

**On "cap local data at 10k rows" specifically:** worth narrowing, given what today's queries showed. Several tables already carry real, near-full-scale local data — that's a genuine asset, not something to shrink. The 10k-ish cap makes the most sense as the default for **new** local fixtures via `seed_mock_analytics_mirror` (new models, new entities without existing real local data yet) — fast to generate, fast to test against, with the explicit understanding that it proves *correctness*, not *performance at scale*. Scale/performance questions (pagination cliffs, missing indexes, query-plan degradation) only show up at real volume and need an actual cloud check regardless of how big a local fixture gets — a bigger local dataset doesn't substitute for that, it just makes local dev slower for no real benefit.

## Open items tracked elsewhere

- RDS CPU-credit exhaustion / Free Plan instance-size restriction — unresolved as of this snapshot, see today's session and `_docs/aws_migration.md`.
- Airbyte Overwrite-vs-Incremental sync mode decision — pending, same place.
- `bulk_uploader` data migration to RDS — still open, see `_docs/aws_migration.md` and `infra/aws/README.md` step 5.
