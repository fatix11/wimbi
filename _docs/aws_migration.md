# Wimbi — AWS Migration Plan

**Status:** Living document — the Terraform stack and container image are written; **no AWS resources have actually been created yet** (no credentials/CLI available in the environment that wrote this — see `infra/aws/README.md`'s prerequisites). Local dev is unaffected either way — everything below is additive (new files, new env vars with safe defaults), nothing about the existing docker-compose setup changed.
**Last updated:** 2026-09-09
**Companion to:** `infra/aws/README.md` (the executable half of this plan — Terraform apply steps, image build/push, Airbyte connection steps), `architectural_decisions.md` (ADR-001/003 — the original Docker Compose/local-Postgres decisions this plan changes the *hosting* of, not the app architecture itself), `to_do.md` (Phase 1 already names a Data Protection Impact Assessment with Legal as a real, not-yet-started item — directly relevant here, see below), `.env.example` (the exact config surface, now including the AWS-specific vars this added: `DJANGO_ALLOWED_HOSTS`, `DJANGO_HTTPS`)

## What's actually built so far (2026-09-09)

- **`Dockerfile`** + **`docker-entrypoint.sh`** — runs the app under `granian` (already a dependency, previously unconfigured). `collectstatic` runs at container start, not build time, since it needs real settings (`SECRET_KEY`, DB env vars) that only exist once ECS actually injects them.
- **`config/settings.py`** — three additive changes, all with defaults that preserve local dev exactly: `ALLOWED_HOSTS` now reads `DJANGO_ALLOWED_HOSTS` (comma-separated) instead of being hardcoded to `localhost`; `STATIC_ROOT`/`STORAGES` added for WhiteNoise (in-process static serving — no S3/CloudFront needed at this scale); a `DJANGO_HTTPS` toggle gates `SECURE_SSL_REDIRECT`/`SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/`SECURE_HSTS_SECONDS` together, off by default since the ALB has no TLS listener yet (turning these on before a cert exists would redirect-loop every request).
- **`requirements.txt`** — added `whitenoise`.
- **`infra/aws/`** — the full Terraform stack: VPC (2 public + 2 private subnets across 2 AZs), RDS Postgres 17 (Multi-AZ, fully private, `deletion_protection = true`), ECS Fargate running the app in public subnets behind a security group that trusts only the ALB (deliberately not the "private subnets + NAT Gateway" pattern — saves ~$32/month a single-instance app doesn't need), an ALB (HTTP only for now), ECR, IAM roles scoped tightly (execution role can only read the 2 secrets it needs; task role starts empty), and Secrets Manager for `DJANGO_SECRET_KEY`/the DB password. **Not yet run against real AWS** — `infra/aws/README.md` has the full apply sequence, including the still-open Airbyte VPC-peering step (needs OAF's VPC ID/CIDR, which isn't available here).
- 103 tests still passing locally after all of the above — nothing about local dev changed behavior.

## Why

2026-09-09: the local dev environment's WSL2/Docker virtual disk hit a real fault — the host C: drive was at 96% full (5.9GB free), and Postgres started throwing `FATAL: could not open file "base/16384/2601": Read-only file system` on basic reads. A container restart didn't clear it; `psql` itself failed inside the container with an `Input/output error` on exec, meaning the fault was in the WSL2 virtual disk layer, not just Postgres. Same underlying class of problem as the `MemoryError`/WSL2 crash from `to_do.md`'s 2026-09-01 entry — disk pressure this time, not RAM. Moving off a single local machine's disk removes this whole failure class.

## What's actually moving

Wimbi has **no separate frontend to move** — ADR-010 deliberately dropped the idea of one. The whole app is a single Django service that server-renders HTML, with HTMX/Tailwind/Chart.js loaded from CDN inside the templates (no Node.js, no build step, no separate frontend host or process). "Move the backend and frontend" in practice means: move this one Django app, and move its Postgres database.

**Current local shape** (`docker-compose.yml`):
- `wimbi_db` — Postgres 17, `wimbi`/`wimbi`/`wimbi`, real data: ~1.3M farmers, ~1.5M journey events, ~1.7M bridge rows, sales lines (5M target, partial load), ~10k SF employees, plus the `analytics_mirror` DimCountry/DimProgram/DimSystem/DimSeason tables and bulk_uploader's own operational tables.
- `wimbi_redis` — Redis 7, provisioned per ADR-001 for future Celery use — **nothing uses it today** (`REDIS_URL` is read but no task exists), so it doesn't need to move at all for now.
- Django app itself runs via `manage.py runserver` locally — there's no production WSGI/ASGI process defined yet. `granian` (a Rust-based server) is already in `requirements.txt` but has no configured entrypoint, systemd unit, or `Procfile` — that's a real gap to close as part of this move, not something already solved.

**This is real farmer PII** — names, ids, and (in some mirrored views) phone numbers for real Malawian farmers. That's the one point in this plan that isn't just a technical decision — see the open question below before anything gets provisioned.

## Proposed architecture

### Option A — minimal, single-instance (recommended to start)
- **1x EC2 instance** (`t3.micro` or `t3.small`) running the Django app directly (granian, behind a systemd unit so it survives a reboot) — no separate app server needed for one user.
- **1x RDS Postgres 17** (`db.t3.micro` or `db.t4g.micro`), replacing the docker-compose Postgres — security group open only to the EC2 instance, never public.
- **No Redis/ElastiCache** — skip it entirely for now; nothing depends on it.
- **Static files via WhiteNoise** (in-process, no S3/CloudFront needed at this traffic level) — one new dependency, `whitenoise`, and a small `MIDDLEWARE`/`STATICFILES_STORAGE` change.
- **No load balancer, no Multi-AZ, no auto-scaling** — single points of failure, accepted deliberately for a one-user dev/pilot environment. Access via SSH key pair + a security group locked to your own IP; the app itself stays behind Django's existing login, not exposed further.

### Option B — closer to "real" production (ECS Fargate + RDS + ALB)
Containerize (the existing `docker-compose.yml` shape maps fairly directly to ECS task definitions), put an Application Load Balancer in front, RDS Multi-AZ, credentials in Secrets Manager instead of a `.env` file on disk. Meaningfully more setup and cost — worth it if this becomes the permanent home rather than a stopgap for the local disk issue, not before.

**Recommendation:** start with Option A. It solves the actual problem (a broken local disk) with the least new surface area, and nothing about it blocks moving to Option B later — RDS in particular doesn't change shape between the two.

## Cost — honest answer: not free in general, and Airbyte is the number that actually matters here

For the app itself (EC2 + RDS, Option A):
- **A new-ish AWS account, within its first 12 months:** genuinely close to $0/month. The free tier covers 750 hrs/month of `t3.micro`/`t2.micro` EC2, 750 hrs/month of `db.t3.micro`/`db.t4g.micro` RDS with 20GB storage, and enough S3/data-transfer allowance that this scale of app wouldn't come close to the limit.
- **An account past its first 12 months:** roughly **$20–35/month** — EC2 ~$7–15/month, RDS ~$15–20/month, no load balancer or NAT Gateway (Option A deliberately avoids both — a NAT Gateway alone runs ~$32/month and isn't needed for a single public-subnet EC2 instance with a locked-down security group).
- **Option B** adds an ALB (~$16/month + usage) and Multi-AZ RDS (roughly doubles the RDS line) — meaningfully more, not recommended to start.
- Storage sizing is currently a guess — I can't check the real database's on-disk size until DB access is restored (that's the outage this move is partly in response to), so "does 20GB actually fit the real data" is unverified, not assumed-yes.

**Airbyte is the line item that can dominate the whole bill, regardless of free tier:**
- Self-hosted: realistically **$60+/month** just for the compute Airbyte itself needs (well past what free-tier EC2 sizes can run), on top of everything above.
- Airbyte Cloud: no compute cost, but usage-based pricing on rows synced — with multi-million-row fact tables refreshed periodically, this is a real, recurring, usage-driven cost that doesn't get smaller once the free trial ends.
- Either way, **Airbyte is very unlikely to be free**, even on a brand-new AWS account — this is the honest answer to "I don't know if it's free": the app hosting plausibly is (for 12 months), Airbyte plausibly isn't, from month one.

## The non-technical question: where should real farmer PII live?

**Partly answered already** — this is your own personal AWS account, a deliberate choice, not a default fallen into. What's still open is narrower but still real: if Airbyte Cloud is chosen over self-hosted, real farmer data (names, ids, phone numbers in some views) transits a third party's infrastructure on every sync, even briefly, rather than staying entirely inside AWS infrastructure you control end to end. `to_do.md`'s own Phase 1 checklist already names a Data Protection Impact Assessment with Legal as real, tracked, not-yet-started work — worth keeping in mind here, not as a blocker, just as context for the Airbyte hosting choice above.

## Decisions made (2026-09-09)

- **Account:** the user's own personal AWS account, not an OAF-managed one.
- **Permanence:** this is the permanent home for Wimbi going forward, not a stopgap — worth a bit more deliberateness even within a minimal starting shape.
- **Data path, split in two:**
  - **Wimbi's own operational tables** (`accounts`, `bulk_uploader` — the `public` schema, per ADR-006's schema isolation) migrate "as they are." In practice this is smaller than it sounds: `RoleAssignmentRule` is seeded by a Django **data migration** (ADR-008), and `auth.User`/sessions are re-provisioned just-in-time on login (ADR-009) — both recreate themselves automatically the moment `python manage.py migrate` runs on the new RDS instance, no manual export needed. The one thing that's genuinely irreplaceable real work is `bulk_uploader.UploadedDataset`/`UploadedRow` — the actual uploaded-and-mapped datasets (e.g. the 1,000-row Malawi registration file already saved). That's a small, targeted `pg_dump -t` (or a Django `dumpdata`/`loaddata` pair, which travels better across a Postgres version/schema difference) of just those two tables, once the local DB is readable again.
  - **`analytics_mirror`** does **not** get copied from local at all — it gets rebuilt properly via **Airbyte**, syncing directly from Snowflake into the new RDS instance. This is real, meaningful new scope: Airbyte was already named as future work in `jira-backlog.md` (EPIC P2: "Recurring sync job (Airbyte or scheduled...) — Not Started") and ADR-003 ("Open, not yet decided"); this migration is where it actually gets built, replacing the manual DBeaver CSV/direct-transfer approach used so far. See the Airbyte section below — it has its own real hosting/cost decision.

## Airbyte — hosting choice (this is a real decision, not a detail)

Two ways to run Airbyte, with meaningfully different cost and data-governance shapes:

| | Self-hosted (OSS) | Airbyte Cloud |
|---|---|---|
| **Where farmer data flows** | Stays entirely inside your own AWS account — Snowflake → your EC2/ECS → your RDS | Passes through Airbyte's own managed infrastructure in transit (their cloud, not yours) before landing in your RDS |
| **Compute** | Needs a real instance — Airbyte's own docs recommend ~4 vCPU/8GB RAM minimum, well past free-tier (`t3.micro` is 1 vCPU/1GB) — realistically a `t3.large` or bigger | None to run yourself — Airbyte's problem, not AWS's |
| **Cost shape** | AWS compute cost only, but not small: a `t3.large` runs roughly **$60/month** on-demand, before RDS/EC2-for-the-app on top | Free trial, then usage-based pricing on rows synced/month — with 1.3M+ farmers and multi-million-row fact tables refreshed periodically, this can add up fast, and it's billed separately from AWS |
| **Ops** | You own upgrades, connector maintenance, uptime | Managed for you |

**The real question underneath this table:** self-hosted keeps real farmer PII inside infrastructure you fully control end to end; Airbyte Cloud means that data transits a third party's systems, even briefly, on every sync. Given `to_do.md` already flags a Data Protection Impact Assessment as real, tracked, not-yet-started work, this is worth a deliberate answer, not a default — see the open question below.

## Migration steps (sequenced, blocked on the open questions below)

1. **Account + access** — an IAM user (not root) in the personal AWS account, least-privilege access to EC2/RDS/VPC (and Airbyte's own compute, once its hosting choice is made), MFA on, access keys never committed to the repo.
2. **Network** — a VPC (the AWS default VPC is fine to start), a security group for RDS (inbound Postgres from the app's and Airbyte's security groups only, never public), a security group for the app EC2 instance (inbound SSH from your IP only, HTTP/HTTPS as needed once there's a domain).
3. **RDS** — provision Postgres 17, note the endpoint, create the `wimbi` database/user matching `.env.example`'s shape, run `python manage.py migrate` against it (this alone recreates the schema and the role-assignment seed data — see above).
4. **`bulk_uploader` data** — once the local DB is readable again: `dumpdata`/`loaddata` (or a targeted `pg_dump -t`) of just `UploadedDataset`/`UploadedRow` onto the new RDS instance.
5. **Airbyte** — stand up per whichever hosting choice gets made below; configure the Snowflake source connector (credentials already exist in `.env.example`'s `SNOWFLAKE_*` block, just unused by the app itself — Airbyte is what actually reads them) and a Postgres destination pointed at the new RDS instance's `analytics_mirror` schema; set a sync cadence.
6. **App EC2** — provision the instance, install Python 3.12 + system deps, clone the repo (needs a deploy key or GitHub auth — the repo is presumably private), install `requirements.txt`.
7. **Django config for production** — real `DJANGO_SECRET_KEY` (generated fresh, not reused from local `.env`), `DJANGO_DEBUG=False`, `ALLOWED_HOSTS` set to the EC2 public DNS (or a real domain if one gets pointed at it), `collectstatic`.
8. **Run process** — a systemd unit running `granian` (already a dependency, currently unconfigured) so the app survives a reboot unattended; a domain + TLS is a later, separate decision, not required to get working.
9. **Verify** — run the `uat.md` acceptance pass against the AWS-hosted instance; confirm real row counts on RDS (both the `bulk_uploader` restore and the first Airbyte sync) match expectations before calling the move done.

## Decisions made (2026-09-09, continued)

- **Airbyte:** not provisioned by this project at all — **OAF already runs its own self-hosted Airbyte instance**, and the new RDS instance becomes a *destination* it syncs into, same as it presumably already syncs into other real infrastructure today. This removes the entire self-hosted-vs-Cloud compute/cost tradeoff above — no Airbyte compute to provision, own, or pay for here. What it does add: **RDS needs to be reachable from wherever OAF's Airbyte instance actually runs**, which is a real network question — see below.
- **App shape:** Option B — ECS Fargate + RDS (Multi-AZ) + ALB, production-shaped from the start rather than starting minimal.
- **Timing:** start provisioning now; the small `bulk_uploader` table migration (`UploadedDataset`/`UploadedRow`) happens as a follow-up once the local Postgres is readable again, not a blocker to starting.

## Open question: how does OAF's Airbyte actually reach the new RDS instance?

This is now the one real unresolved design point before RDS's network setup can be finalized. Options, depending on where OAF's Airbyte runs:
- **If OAF's Airbyte already runs in AWS** (even a different account) — VPC peering or a private connection is possible, keeping the connection off the public internet entirely. Needs OAF's AWS account/VPC details.
- **If it runs elsewhere** (on-prem, a different cloud, OAF's own servers) — RDS needs a public endpoint, locked down via security group to Airbyte's specific outbound IP(s) (not open to the internet generally), with SSL enforced (`sslmode=require` at minimum, ideally `verify-full`) and a strong dedicated Airbyte-only database credential (not the app's own Django DB user).

## Practical blocker before anything gets created

I don't have AWS credentials or the `aws` CLI available in this environment — nothing here can call the AWS API on your behalf right now. For work involving real billable resources in your own personal account, that's the right default anyway, not just a missing tool. Three ways to actually execute from here, in order of how much control you keep:

1. **I write Terraform** for the full Option B stack (VPC, RDS Multi-AZ, ECS Fargate, ALB, security groups) — you review it, run `terraform apply` yourself with your own credentials. Repeatable, reviewable, diffable for changes later. Recommended given the scope (production-shaped, permanent, real PII).
2. **I write exact AWS Console click-through steps** — no IaC, slower to redo/change later, but zero tooling needed on either side.
3. **You configure AWS CLI credentials in this environment** (`aws configure`, scoped to an IAM user with least-privilege access, not root) and I run commands directly — fastest, but means real AWS credentials sit in this dev environment.
