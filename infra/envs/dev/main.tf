###############################################################################
# C5 — Shared data layer: KMS, reports bucket, DynamoDB tables.
###############################################################################

locals {
  name_prefix = "rxlab-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  repo_root   = abspath("${path.module}/${var.repo_root}")
}

module "kms" {
  source = "../../modules/kms-key"

  alias       = "${local.name_prefix}/data"
  description = "RxLab ${var.environment} data encryption key"
  region      = var.region
}

module "reports_bucket" {
  source = "../../modules/s3-bucket-secure"

  bucket_name = "rxlab-reports-${var.environment}-${local.account_id}"
  kms_key_arn = module.kms.key_arn
}

module "jobs_table" {
  source = "../../modules/dynamodb-table"

  table_name  = "${local.name_prefix}-jobs"
  hash_key    = "job_id"
  kms_key_arn = module.kms.key_arn
}

module "agent_runs_table" {
  source = "../../modules/dynamodb-table"

  table_name     = "${local.name_prefix}-agent-runs"
  hash_key       = "job_id"
  range_key      = "agent"
  hash_key_type  = "S"
  range_key_type = "S"
  kms_key_arn    = module.kms.key_arn
}

module "audit_table" {
  source = "../../modules/dynamodb-table"

  table_name     = "${local.name_prefix}-audit"
  hash_key       = "job_id"
  range_key      = "created_at"
  hash_key_type  = "S"
  range_key_type = "S"
  ttl_attribute  = "expires_at"
  kms_key_arn    = module.kms.key_arn
}
