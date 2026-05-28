###############################################################################
# C8/C9 — Step Functions Express pipeline (5 agents with Critic gate).
###############################################################################

module "pipeline" {
  source = "../../modules/step-functions-pipeline"

  name                     = "${local.name_prefix}-pipeline"
  type                     = "EXPRESS"
  definition_template_path = abspath("${path.module}/../../modules/step-functions-pipeline/pipeline.asl.json.tpl")
  kms_key_arn              = module.kms.key_arn
  log_retention_days       = var.log_retention_days

  definition_substitutions = {
    intake_lambda_arn        = module.agent_intake.function_arn
    analyzer_lambda_arn      = module.agent_analyzer.function_arn
    fhir_composer_lambda_arn = module.agent_fhir_composer.function_arn
    summarizer_lambda_arn    = module.agent_summarizer.function_arn
    critic_lambda_arn        = module.agent_critic.function_arn
  }

  lambda_arns = [
    module.agent_intake.function_arn,
    module.agent_analyzer.function_arn,
    module.agent_fhir_composer.function_arn,
    module.agent_summarizer.function_arn,
    module.agent_critic.function_arn,
  ]

  depends_on = [
    module.agent_intake,
    module.agent_analyzer,
    module.agent_fhir_composer,
    module.agent_summarizer,
    module.agent_critic,
  ]
}
