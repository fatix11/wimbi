# Wimbi on AWS — Terraform (Option B)

Full plan and the decisions behind this shape: `_docs/aws_migration.md` — read that first if you haven't. This directory is the executable half of that plan: VPC (2 public + 2 private subnets), RDS Postgres 17 (Multi-AZ, private, never public), ECS Fargate running the app in the public subnets behind a security group that only trusts the ALB, an ALB, ECR for the container image, IAM roles, and Secrets Manager for the two real secrets (Django's `SECRET_KEY`, the DB password).

**This has not been run.** No `terraform validate`, `plan`, or `apply` has happened against it yet — the environment that wrote it has no AWS credentials or the `terraform` CLI. Run `terraform validate` yourself as the very first step, before trusting any of this against real infrastructure.

## Prerequisites

- Terraform >= 1.7 ([install](https://developer.hashicorp.com/terraform/install))
- AWS CLI, configured with an IAM user (not root) that has permission to create VPC/RDS/ECS/ALB/IAM/Secrets Manager/ECR resources — `aws configure`
- Docker, to build and push the app image

## First-time setup

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: django_secret_key, db_password at minimum
terraform init
terraform validate   # do this before plan/apply — see note above
```

## 1. Build and push the app image

The ECS service needs a real image before its first successful deploy — `container_image` in `terraform.tfvars` is a placeholder until this step runs once.

```bash
# From the repo root, not infra/aws/
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-north-1.amazonaws.com

docker build -t wimbi-prod .
docker tag wimbi-prod:latest <account-id>.dkr.ecr.eu-north-1.amazonaws.com/wimbi-prod:latest
```

The ECR repository itself is created by Terraform (`ecr.tf`), so do a first `terraform apply` (steps 2 onward) with any placeholder `container_image` value to get the repository to exist, *then* push the real image, then re-apply so the ECS service picks it up — chicken-and-egg only on the very first run.

## 2. Provision everything

```bash
terraform plan    # read this before apply — confirm it's creating what you expect
terraform apply
```

Takes a while — RDS Multi-AZ in particular can take 10-15 minutes.

## 3. Point Django's ALLOWED_HOSTS at the real ALB

```bash
terraform output alb_dns_name
```

Set that value as `django_allowed_hosts` in `terraform.tfvars`, then `terraform apply` again (this updates the running task's environment — ECS will roll a new task).

## 4. First-time database setup

The schema doesn't exist on a fresh RDS instance until migrations run. From your own machine (RDS isn't public, so this needs to happen from something that can reach it — either a bastion/VPN, or temporarily via `aws ecs execute-command` into the running task):

```bash
# Simplest: exec into the running ECS task and run it from there
aws ecs execute-command --cluster wimbi-prod --task <task-id> --container app --interactive --command "python manage.py migrate"
```

(Needs `enableExecuteCommand` on the service — not currently set in `ecs.tf`; add `enable_execute_command = true` to the `aws_ecs_service` resource before you need this, or use a one-off Fargate task instead.)

This alone recreates the role-assignment seed data (`RoleAssignmentRule`, a Django data migration — ADR-008) — nothing manual needed for that part.

## 5. Migrate the real `bulk_uploader` data

Once the local Postgres is readable again (see `_docs/aws_migration.md` — this was blocked on a local disk issue when this plan was written):

```bash
# Locally, against the (fixed) local DB:
python manage.py dumpdata bulk_uploader.UploadedDataset bulk_uploader.UploadedRow > bulk_uploader_data.json

# Against RDS (via the same execute-command path, or a temporary local
# connection if you open one — RDS stays non-public otherwise):
python manage.py loaddata bulk_uploader_data.json
```

## 6. Connecting OAF's Airbyte

OAF's Airbyte is self-hosted and already runs in AWS — the decision was to use this new RDS instance as an Airbyte **destination**, not to run Airbyte as part of this stack at all. Two things still need to happen, neither of them in this Terraform yet because they need details only OAF's side has:

1. **VPC peering** — `aws_vpc_peering_connection` from this VPC (`terraform output vpc_id`) to OAF's Airbyte VPC, requiring their VPC ID and CIDR (and their side accepting the peering request if it's a different AWS account). Once accepted, add a route in `aws_route_table.private` (`terraform output private_route_table_id`) pointing OAF's VPC CIDR at the peering connection — that's the actual network path; add it as a new `aws_route` resource once you have those details, not something to guess at here.
2. **Security group rule** — set `airbyte_source_cidr` in `terraform.tfvars` to OAF's Airbyte VPC CIDR and re-apply; this alone doesn't create connectivity (step 1 does), it just allows the traffic once the network path exists.
3. **Airbyte's own destination config** — Postgres host = `terraform output rds_address`, port 5432, database `analytics_mirror`-schema-aware (see `analytics_mirror/seed_data.py`'s `MIRROR_SCHEMA`), a dedicated Airbyte-only DB user (not the app's own `wimbi` user) — create that user manually via `psql` once connectivity exists, scoped to just the `analytics_mirror` schema.

## Cost note

See `_docs/aws_migration.md`'s cost section for the full breakdown. The one thing this specific Terraform avoids that a more textbook Fargate setup wouldn't: no NAT Gateway (~$32/month) — tasks run in public subnets with a security group that only trusts the ALB, not the more common "private subnets + NAT" pattern. RDS Multi-AZ (`db_multi_az = true` by default, matching the "production-shaped, permanent home" decision) roughly doubles the RDS line versus single-AZ — set it `false` in `terraform.tfvars` if that's not worth it yet.

## Tearing down

```bash
terraform destroy
```

`deletion_protection = true` and `skip_final_snapshot = false` on the RDS instance (`rds.tf`) mean this won't actually delete the database in one step — it'll fail with a clear error until you deliberately turn `deletion_protection` off first. That's intentional, not a bug to route around quickly.
