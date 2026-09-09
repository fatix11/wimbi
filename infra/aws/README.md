# Wimbi on AWS — Terraform (Option B)

Full plan and the decisions behind this shape: `_docs/aws_migration.md` — read that first if you haven't. This directory is the executable half of that plan: VPC (2 public + 2 private subnets), RDS Postgres 17 (Multi-AZ, private, never public), ECS Fargate running the app in the public subnets behind a security group that only trusts the ALB, an ALB, ECR for the container image, IAM roles, and Secrets Manager for the two real secrets (Django's `SECRET_KEY`, the DB password).

**This has not been run.** No `terraform validate`, `plan`, or `apply` has happened against it yet — the environment that wrote it has no AWS credentials or the `terraform` CLI. Run `terraform validate` yourself as the very first step, before trusting any of this against real infrastructure.

## Prerequisites

- Terraform >= 1.7 ([install](https://developer.hashicorp.com/terraform/install))
- AWS CLI, configured with an IAM user (not root) that has permission to create VPC/RDS/ECS/ALB/IAM/Secrets Manager/ECR resources — `aws configure`
- Docker, to build and push the app image

## First-time setup

**0. Bootstrap the state backend, once, ever.** Terraform's state (the record of what's actually been created) lives in S3 now, not as a local file in whatever CloudShell session happens to run `apply` — a genuinely different browser/login is a genuinely different `$HOME`, and local state got trapped in one session's storage once already before this was set up (see `aws_migration.md`, 2026-09-09). This step only needs running once, ever, per AWS account — skip it if the bucket/table already exist:

```bash
aws s3api create-bucket --bucket wimbi-terraform-state-<your-account-id> --region eu-north-1 --create-bucket-configuration LocationConstraint=eu-north-1
aws s3api put-bucket-versioning --bucket wimbi-terraform-state-<your-account-id> --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket wimbi-terraform-state-<your-account-id> --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket wimbi-terraform-state-<your-account-id> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws dynamodb create-table --table-name wimbi-terraform-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region eu-north-1
```

(The bucket name in `versions.tf`'s `backend "s3"` block needs to match whatever you actually created here — it's hardcoded there since backend config blocks can't reference variables.)

**Every other session, from here on:**

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: django_secret_key, db_password at minimum
terraform init
# if state already exists locally from before the backend was set up,
# init will offer to migrate it into S3 - say yes, once
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

OAF's Airbyte is self-hosted and already runs in AWS — the decision was to use this new RDS instance as an Airbyte **destination**, not to run Airbyte as part of this stack at all.

**VPC peering was considered and dropped.** It's the better long-term shape (traffic never touches the public internet), but it needs OAF's VPC ID/CIDR and their side accepting the peering request — too much cross-team coordination for infrastructure that gets rebuilt in OAF's own AWS account in a few weeks anyway. The public-endpoint path below was chosen instead, deliberately, as a bridge. Revisit peering when this moves into OAF's account.

1. **Public endpoint** — set `db_publicly_accessible = true` in `terraform.tfvars` and apply. This gives RDS a public IP and puts its subnet group in the public subnets (both are needed; the flag alone does nothing if the subnets have no internet gateway route). On its own this opens *nothing* — the security group still rejects everything but the app's own tasks.
2. **Find Airbyte's outbound addresses** — you likely can't just ask (they sit with whoever runs Airbyte). `flow_logs.tf` enables REJECT-only VPC Flow Logs precisely so the *blocked* connection attempt identifies itself. Trigger a "Test the destination" in Airbyte, wait a few minutes, then:
   ```bash
   aws logs tail /vpc/wimbi-prod-flow-logs --since 15m --region eu-north-1 | awk '$9 == 5432'
   ```
   Field 9 is the destination port — filtering on 5432 separates real Postgres attempts from the constant background scanner noise any public IP attracts (scanners hit random ports once; Airbyte retries 5432 specifically, several packets at a time).
3. **Security group rule** — put those addresses in `airbyte_source_cidrs` (a list — observed egress used more than one) and re-apply. See the variable's own note on when this can silently go stale.
4. **Airbyte's own destination config** — host = `terraform output rds_address`, port 5432, database `wimbi`, schema `analytics_mirror`, SSL mode `require`, SSH tunnel method **No Tunnel** (there's no bastion in this design — Airbyte connects straight to the endpoint). Username `airbyte`, not the app's own `wimbi` master user: a dedicated role scoped to just the `analytics_mirror` schema, created via a one-off `ecs run-task` (see `_docs/aws_migration.md` for the exact command) rather than `psql`, since RDS isn't reachable from outside the VPC and the image has no psql client.

## Cost note

See `_docs/aws_migration.md`'s cost section for the full breakdown. The one thing this specific Terraform avoids that a more textbook Fargate setup wouldn't: no NAT Gateway (~$32/month) — tasks run in public subnets with a security group that only trusts the ALB, not the more common "private subnets + NAT" pattern. RDS Multi-AZ (`db_multi_az = true` by default, matching the "production-shaped, permanent home" decision) roughly doubles the RDS line versus single-AZ — set it `false` in `terraform.tfvars` if that's not worth it yet.

## Tearing down

```bash
terraform destroy
```

`deletion_protection = true` and `skip_final_snapshot = false` on the RDS instance (`rds.tf`) mean this won't actually delete the database in one step — it'll fail with a clear error until you deliberately turn `deletion_protection` off first. That's intentional, not a bug to route around quickly.
