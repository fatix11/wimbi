terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Shared state, so it's not trapped in one CloudShell session's $HOME -
  # a different browser/login is a genuinely different environment there,
  # which bit us once already (see aws_migration.md, 2026-09-09). Backend
  # config can't itself use variables, so these are hardcoded, not
  # var.aws_region/project - bucket and table created once via plain AWS
  # CLI (infra/aws/README.md), not managed by this Terraform.
  backend "s3" {
    bucket         = "wimbi-terraform-state-520847768893"
    key            = "wimbi/terraform.tfstate"
    region         = "eu-north-1"
    dynamodb_table = "wimbi-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
