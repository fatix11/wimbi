# Local vs Cloud

**Snapshot verified 2026-09-12** — every number and fact below was checked directly (`docker compose exec` queries, `pg_proc`/`information_schema` lookups, `EXPLAIN ANALYZE`, a full local test run), not recalled from memory. Re-verify before trusting this doc once real time has passed — it will drift.

**Major update since the 2026-09-10 snapshot:** local `analytics_mirror` is no longer real physical tables — it's now **20 Postgres views over `analytics_mirror_raw`**, the same architecture as AWS. That closes most of what this doc previously flagged as divergence. What's left is genuinely new information, not a restatement of the old gaps.

## Infrastructure & tooling — deliberately different, not a gap

| | Local | Cloud (AWS) |
|---|---|---|
| Provisioning | Docker Compose (`postgres:17`, `redis:7` — dependencies only) + `infra/postgres/init.sql`, run once via `docker-entrypoint-initdb.d` | Terraform (`infra/aws/`) — VPC, RDS, ECS Fargate, ALB, ECR, IAM, Secrets Manager, S3+DynamoDB state backend |
| App process | `manage.py runserver`, run natively via PowerShell — **not containerized** | `granian` under ECS Fargate, built into a Docker image, pushed to ECR |
| Why | A single developer's own machine has no need for infra-as-code, environment promotion, or state locking. Docker Compose + native shell commands are the right tool here. | Multiple planned environments (prod/qa/uat), infrastructure that needs to be reproducible and auditable. Terraform is the right tool there. |

Neither side is behind — they're matched to what each environment actually needs.

## Database schema — now architecturally aligned, data volume differs

**Both local and AWS now use the same shape:** `analytics_mirror_raw` holds landed data (DBeaver copies locally, Airbyte syncs on AWS), `analytics_mirror` holds views translating it to what Django expects. Verified row counts, local, 2026-09-12 — all 20 are views:

| Table | Local rows | Table | Local rows |
|---|---|---|---|
| `bridge_client_source_ids` | 1,734,921 | `loan_portfolio` | 410,783 |
| `dim_client` | 1,305,491 | `program_summary` | 62 |
| `dim_country` | 10 | `repayment_transaction` | 4,321,246 |
| `dim_date` | 10,957 | `sales_line` | 1,809,577 (deliberately bounded sample, MW-00000001 to MW-00199999 — not the full ~12.78M) |
| `dim_exchange_rate` | 5,040 | `sf_employees` | 10,074 |
| `dim_location` | 2,026 | `v_client_journey` | 1,538,237 |
| `dim_mcf` | 7 | `v_client_reach` | 1,305,497 |
| `dim_people` | 1,514 | | |
| `dim_product` | 143 | | |
| `dim_program`/`dim_season`/`dim_system` | 29 / 171 / 218 | | |
| `fo_performance` | 560 | | |

AWS's `analytics_mirror_raw` is mid-backfill and was throttled by an RDS CPU-credit/instance-size issue as of the last cloud session (see `_docs/aws_migration.md`) — cloud row counts are likely still behind local's for the big fact tables. Not re-verified today; this is a local-only session.

**Two real functional gaps from the 2026-09-10 snapshot are now closed:**

1. **`analytics_mirror.to_iso_country()` now exists locally too** (created 2026-09-11, converting `bridge_client_source_ids`/`v_client_reach`/`v_client_journey`/`sales_line`). Identical to AWS's version and to `country_codes.py`'s Python logic — all three still need to be kept in sync by hand, there's just no longer a *missing* copy.
2. **Surrogate ids now work the same way in both places** — `PARTITION BY gl_client_id` was added to all three `ROW_NUMBER()` views (`v_client_journey`, `sales_line`, `repayment_transaction`) locally on 2026-09-12. This closes the "ids behave differently" gap, but see the new divergence below — it also revealed that **AWS's own view definitions likely have the same bug locally just fixed**, unverified until applied there.

## New finding, not in the earlier snapshot: a real performance bug, likely present on AWS too

Found 2026-09-12 via actual frontend testing (not caught by any earlier curl-based check): the three `ROW_NUMBER()` views, without `PARTITION BY`, forced a full table sort before any `WHERE gl_client_id = 'X'` filter could apply — 23.6s for a journey timeline, 39.8s for sales history, on real per-farmer page loads. Fixed locally by adding `PARTITION BY "GL_CLIENT_ID"` plus B-tree indexes on every raw table's `GL_CLIENT_ID` column, and a `pg_trgm` GIN index for the search page's `ILIKE` pattern. All four now run in under 40ms, most well under 1ms.

**`infra/postgres/analytics_mirror_views.sql` (the AWS version) has been updated to match this fix in the repo, but the fix has NOT been applied to the live AWS RDS instance yet.** AWS's raw tables also have no indexes (confirmed conceptually, not re-verified against the live instance today). This is a real, likely-live performance problem on AWS right now, once its backfill finishes and views are actually queried by the app — worth prioritizing early in the next AWS session, not discovering it live in front of a stakeholder.

## App runtime

| | Local | Cloud |
|---|---|---|
| `DJANGO_DEBUG` | `True` | `False` |
| Static files | Served directly by Django's dev server | WhiteNoise, `collectstatic` at container start |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` (default) | ALB DNS name (real domain once OAF provides one) |
| TLS | N/A | Deferred — HTTP only, waiting on `*.oneacrefund.org` |

## Deployment — git in sync is not the same as AWS being up to date

Local: a code change is live the moment the dev server reloads — no separate deploy step. Cloud: a code change needs an explicit `docker build` / `ecr push` / `aws ecs update-service --force-new-deployment` sequence, **and now also a separate SQL apply step** for the view/index fix above, since Terraform doesn't manage database views. Pushing to `main` updates neither the running ECS task nor the RDS schema by itself.

## `bulk_uploader` — still real, local-only work

17 `UploadedDataset` rows exist locally; none have been migrated to RDS yet. Unchanged from the last snapshot — still open.

## Disk space

Local disk was a real, recurring constraint this session (the original trigger for the whole AWS migration). Deleted 6 source CSVs (~4.3GB combined) after verifying their data was safely and fully in Postgres, plus the old, known-incomplete `sales_detail.csv` (2.6GB) once its replacement (the bounded `sales_line` sample) was built and verified. Freed roughly 4.3GB total across the session; disk sits around 10GB free as of the last check.

## Test coverage

103 tests passing locally as of this snapshot (`pytest`, ~65s). No equivalent automated suite runs against AWS. Also added, 2026-09-12: real end-to-end frontend verification via a headless browser (Playwright) — login, dashboard, search, farmer profile, journey timeline, sales history all confirmed rendering real data correctly, not just returning 200s. No project skill exists yet for this; worth generating one via `/run-skill-generator` if this pattern recurs.

---

## Dev → prod strategy

**Core principle, unchanged: local is the default, fast loop for almost everything. A cloud pass is reserved for what only cloud can actually tell you.**

**Local alone is sufficient for:** RBAC, UI/frontend behavior, business logic, and now essentially all `analytics_mirror` work — every table in scope has real local data as of this snapshot (only `sales_line`'s sample is intentionally partial, and that's documented, not hidden).

**A cloud pass is still needed before calling something done when it touches:**
1. Anything relying on `to_iso_country()` staying in sync between the Python and both SQL copies (now three places to update, not two).
2. Genuine infra/deployment changes — anything under `infra/aws/`, `Dockerfile`, `docker-entrypoint.sh`, or `config/settings.py`'s production-only branches.
3. **The performance fix above — needs applying to the live AWS RDS instance**, not just committed to the repo's SQL file.

**Promotion rhythm:** unchanged from the last snapshot — commit locally-validated work to `main` as usual, treat an actual AWS deploy (code + SQL) as a deliberate, batched action, update this doc's snapshot whenever a real cloud-validation pass happens.

## Open items tracked elsewhere

- RDS CPU-credit exhaustion / Free Plan instance-size restriction — unresolved, see `_docs/aws_migration.md`.
- Airbyte Overwrite-vs-Incremental sync mode decision — pending, same place.
- **New: apply the `PARTITION BY` + index performance fix to the live AWS RDS instance** — written into `infra/postgres/analytics_mirror_views.sql` but not yet run there.
- `bulk_uploader` data migration to RDS — still open.
- A proper full (~12.78M row) `sales_line` sync, superseding the current bounded MW-1–200k sample — the sample was a deliberate interim fix, not the final state.
