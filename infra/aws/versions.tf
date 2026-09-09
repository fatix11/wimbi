terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment once you have an S3 bucket to hold state remotely (recommended
  # once more than one person/machine touches this) — not set up yet, state
  # is local (terraform.tfstate) until then. See infra/aws/README.md.
  # backend "s3" {
  #   bucket = "wimbi-terraform-state"
  #   key    = "wimbi/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}
