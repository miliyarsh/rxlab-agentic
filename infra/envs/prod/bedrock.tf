###############################################################################
# C9 — Bedrock agents, SSM parameters, SNS alerts, and cost budget.
###############################################################################

resource "aws_ssm_parameter" "bedrock_model_id" {
  name  = "/rxlab/${var.environment}/bedrock/model_id"
  type  = "String"
  value = var.bedrock_model_id

  tags = { Project = "rxlab", Environment = var.environment, Component = "ssm" }
}

resource "aws_ssm_parameter" "bedrock_enabled" {
  name  = "/rxlab/${var.environment}/feature_flags/bedrock_enabled"
  type  = "String"
  value = tostring(var.bedrock_enabled)

  tags = { Project = "rxlab", Environment = var.environment, Component = "ssm" }
}

locals {
  bedrock_agent_env = {
    ENVIRONMENT      = var.environment
    JOBS_TABLE       = module.jobs_table.table_name
    AGENT_RUNS_TABLE = module.agent_runs_table.table_name
    AUDIT_TABLE      = module.audit_table.table_name
    REPORTS_BUCKET   = module.reports_bucket.bucket_id
    BEDROCK_MODEL_ID = var.bedrock_model_id
    BEDROCK_ENABLED  = tostring(var.bedrock_enabled)
  }
}

module "agent_summarizer" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-summarizer"
  handler            = "agents.summarizer.handler.handler"
  source_dir         = abspath("${path.module}/${var.service_source_dir}")
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = 90
  memory_size        = 512
  log_retention_days = var.log_retention_days

  environment_variables = merge(local.bedrock_agent_env, { AGENT_NAME = "summarizer" })

  iam_policy_statements = [
    {
      sid = "ReadBundleAndJobs"
      actions = [
        "s3:GetObject",
        "s3:GetObjectVersion",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/*"]
    },
    {
      sid = "ReadWriteJobsRunsAudit"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [
        module.jobs_table.table_arn,
        module.agent_runs_table.table_arn,
        module.audit_table.table_arn,
      ]
    },
    {
      sid = "ReadBedrockConfig"
      actions = [
        "ssm:GetParameter",
        "ssm:GetParameters",
      ]
      resources = [
        aws_ssm_parameter.bedrock_model_id.arn,
        aws_ssm_parameter.bedrock_enabled.arn,
      ]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "agent_critic" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-critic"
  handler            = "agents.critic.handler.handler"
  source_dir         = abspath("${path.module}/${var.service_source_dir}")
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = 90
  memory_size        = 512
  log_retention_days = var.log_retention_days

  environment_variables = merge(local.bedrock_agent_env, { AGENT_NAME = "critic" })

  iam_policy_statements = [
    {
      sid = "ReadWriteBundleAndJobs"
      actions = [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:PutObject",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/*"]
    },
    {
      sid = "ReadWriteJobsRunsAudit"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [
        module.jobs_table.table_arn,
        module.agent_runs_table.table_arn,
        module.audit_table.table_arn,
      ]
    },
    {
      sid = "ReadBedrockConfig"
      actions = [
        "ssm:GetParameter",
        "ssm:GetParameters",
      ]
      resources = [
        aws_ssm_parameter.bedrock_model_id.arn,
        aws_ssm_parameter.bedrock_enabled.arn,
      ]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "bedrock_access" {
  source = "../../modules/bedrock-access"

  policy_name = "${local.name_prefix}-bedrock-agents"
  model_id    = var.bedrock_model_id
  region      = var.region

  attach_role_arns = [
    module.agent_summarizer.role_arn,
    module.agent_critic.role_arn,
  ]
}

module "alerts" {
  count  = var.alert_email == "" ? 0 : 1
  source = "../../modules/sns-alerts"

  topic_name  = "${local.name_prefix}-alerts"
  kms_key_arn = module.kms.key_arn
  email_subscribers = [var.alert_email]
}

resource "aws_budgets_budget" "monthly" {
  count = var.alert_email == "" ? 0 : 1

  name         = "${local.name_prefix}-monthly-cost"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 10
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
