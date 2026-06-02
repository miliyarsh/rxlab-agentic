provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "rxlab"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
