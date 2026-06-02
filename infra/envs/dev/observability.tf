###############################################################################
# C10 — Observability dashboard, alarms, and scheduled healthz canary.
###############################################################################

module "canary_healthz" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-healthz-canary"
  handler            = "service.canary.healthz_canary.handler"
  package_zip_path   = local.service_zip_path
  source_code_hash   = local.service_source_code_hash
  depends_on         = [terraform_data.service_package]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = 30
  memory_size        = 128
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT = var.environment
    API_URL     = module.api.api_endpoint
  }

  iam_policy_statements = [
    {
      sid       = "PutCanaryMetrics"
      actions   = ["cloudwatch:PutMetricData"]
      resources = ["*"]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt"]
      resources = [module.kms.key_arn]
    },
  ]
}

locals {
  all_lambda_names = [
    module.api_submit_job.function_name,
    module.api_get_job.function_name,
    module.api_get_report.function_name,
    module.api_upload_vcf.function_name,
    module.api_healthz.function_name,
    module.agent_intake.function_name,
    module.agent_analyzer.function_name,
    module.agent_fhir_composer.function_name,
    module.agent_summarizer.function_name,
    module.agent_critic.function_name,
    module.canary_healthz.function_name,
  ]
}

module "observability" {
  count  = var.alert_email == "" ? 0 : 1
  source = "../../modules/observability"

  name_prefix           = local.name_prefix
  region                = var.region
  alarm_topic_arn       = module.alerts[0].topic_arn
  lambda_function_names = local.all_lambda_names
  state_machine_arn     = module.pipeline.state_machine_arn
  api_id                = module.api.api_id
}

resource "aws_cloudwatch_event_rule" "canary" {
  name                = "${local.name_prefix}-healthz-canary"
  description         = "Invoke healthz canary every 5 minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "canary" {
  rule      = aws_cloudwatch_event_rule.canary.name
  target_id = "healthz-canary"
  arn       = module.canary_healthz.function_arn
}

resource "aws_lambda_permission" "canary_eventbridge" {
  statement_id  = "AllowEventBridgeInvokeCanary"
  action        = "lambda:InvokeFunction"
  function_name = module.canary_healthz.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.canary.arn
}
