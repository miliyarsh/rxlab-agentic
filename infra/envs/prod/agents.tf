###############################################################################
# C7 — Deterministic pipeline agents (Intake, Analyzer, FHIR Composer).
###############################################################################

module "agent_intake" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-intake"
  handler            = "agents.intake.handler.handler"
  source_dir         = abspath("${path.module}/${var.service_source_dir}")
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = 60
  memory_size        = 512
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT      = var.environment
    AGENT_NAME       = "intake"
    JOBS_TABLE       = module.jobs_table.table_name
    AGENT_RUNS_TABLE = module.agent_runs_table.table_name
    REPORTS_BUCKET   = module.reports_bucket.bucket_id
  }

  iam_policy_statements = [
    {
      sid = "ReadInputVcf"
      actions = [
        "s3:GetObject",
        "s3:GetObjectVersion",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/*"]
    },
    {
      sid = "WriteJobsAndRuns"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [
        module.jobs_table.table_arn,
        module.agent_runs_table.table_arn,
      ]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "agent_analyzer" {
  source = "../../modules/lambda-container"

  function_name       = "${local.name_prefix}-analyzer"
  ecr_repository_name = "${local.name_prefix}-analyzer"
  image_tag           = "latest"
  kms_key_arn         = module.kms.key_arn
  timeout_seconds     = 120
  memory_size         = 1024
  log_retention_days  = var.log_retention_days

  environment_variables = {
    ENVIRONMENT      = var.environment
    AGENT_NAME       = "analyzer"
    JOBS_TABLE       = module.jobs_table.table_name
    AGENT_RUNS_TABLE = module.agent_runs_table.table_name
  }

  iam_policy_statements = [
    {
      sid = "WriteJobsAndRuns"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [
        module.jobs_table.table_arn,
        module.agent_runs_table.table_arn,
      ]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "agent_fhir_composer" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-fhir-composer"
  handler            = "agents.fhir_composer.handler.handler"
  source_dir         = abspath("${path.module}/${var.service_source_dir}")
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = 60
  memory_size        = 512
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT      = var.environment
    AGENT_NAME       = "fhir_composer"
    JOBS_TABLE       = module.jobs_table.table_name
    AGENT_RUNS_TABLE = module.agent_runs_table.table_name
    REPORTS_BUCKET   = module.reports_bucket.bucket_id
  }

  iam_policy_statements = [
    {
      sid = "WriteBundle"
      actions = [
        "s3:PutObject",
        "s3:PutObjectTagging",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/*"]
    },
    {
      sid = "WriteJobsAndRuns"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [
        module.jobs_table.table_arn,
        module.agent_runs_table.table_arn,
      ]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}
