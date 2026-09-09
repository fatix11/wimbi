variable "aws_region" {
  description = "AWS region to deploy into. eu-north-1 (Stockholm) — matches the CloudShell session's own region, set when this stack was first stood up."
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Short name used to prefix/tag every resource this stack creates."
  type        = string
  default     = "wimbi"
}

variable "environment" {
  description = "Environment name (tags resources, doesn't change behavior)."
  type        = string
  default     = "prod"
}

# --- Networking -------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the new VPC. Must not overlap OAF's Airbyte VPC if/when peered."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "2 AZs to spread subnets across, for RDS Multi-AZ and ALB's own requirement of 2+ subnets."
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

variable "airbyte_source_cidr" {
  description = <<-EOT
    CIDR range OAF's self-hosted Airbyte connects from, for the RDS security
    group's inbound rule. Leave null to skip that rule for now (e.g. while
    still setting up VPC peering — see infra/aws/README.md "Connecting
    OAF's Airbyte" section; the security group rule alone doesn't create a
    network path, peering/VPN does that separately).
  EOT
  type    = string
  default = null
}

# --- Database -----------------------------------------------------------

variable "db_name" {
  type    = string
  default = "wimbi"
}

variable "db_username" {
  type    = string
  default = "wimbi"
}

variable "db_password" {
  description = "RDS master password. Pass via -var or a .auto.tfvars file that's gitignored — never commit this."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage_gb" {
  description = "Starting storage size — unverified against the real local DB's actual size (it was inaccessible when this was written, see aws_migration.md). RDS storage auto-scaling is enabled up to db_max_allocated_storage_gb so this isn't a hard ceiling."
  type        = number
  default     = 50
}

variable "db_max_allocated_storage_gb" {
  type    = number
  default = 200
}

variable "db_backup_retention_days" {
  description = "Brand-new AWS accounts can land on a restrictive \"Free Plan\" that caps this below the usual default of 7 - if apply fails with a FreeTierRestrictionError on this field, lower it further (1, then 0 if needed) until it matches what your account's plan actually allows, or upgrade the account plan in Billing to remove the cap entirely."
  type        = number
  default     = 1
}

variable "db_multi_az" {
  description = "Option B is production-shaped — Multi-AZ on by default. Set false to cut RDS cost roughly in half if that's not needed yet."
  type        = bool
  default     = true
}

# --- App container --------------------------------------------------------

variable "container_image" {
  description = "Full ECR image URI (repo:tag) to run — built and pushed by infra/aws/README.md's steps. No default: must be set once an image actually exists, or the ECS service has nothing to run."
  type        = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "task_cpu" {
  description = "Fargate task vCPU units (256 = 0.25 vCPU). See AWS's valid cpu/memory combinations."
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "Fargate task memory in MB."
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "How many app instances to run. 1 is enough for a single-user pilot; Option B's ALB/ECS shape still gives you a path to raise this later without redesigning anything."
  type        = number
  default     = 1
}

# --- Django config, passed through to the container as env vars ----------

variable "django_secret_key" {
  description = "Generate fresh — do not reuse the local .env value. e.g. python -c \"import secrets; print(secrets.token_urlsafe(50))\""
  type        = string
  sensitive   = true
}

variable "django_allowed_hosts" {
  description = "Comma-separated. Start with the ALB's DNS name (from terraform output after the first apply); add a real domain here once one is pointed at the ALB."
  type        = string
  default     = ""
}

variable "snowflake_account" {
  description = "Not read by the Django app itself (ADR-003) — kept here only in case a future task/connector in this same stack needs it. Airbyte itself runs outside this stack (OAF's own instance) and configures its own Snowflake source separately."
  type        = string
  default     = ""
}
