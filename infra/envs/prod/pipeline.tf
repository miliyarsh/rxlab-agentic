###############################################################################
# C8 — Step Functions Express pipeline (Intake → Analyzer → FHIR Composer).
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
  }

  lambda_arns = [
    module.agent_intake.function_arn,
    module.agent_analyzer.function_arn,
    module.agent_fhir_composer.function_arn,
  ]

  depends_on = [
    module.agent_intake,
    module.agent_analyzer,
    module.agent_fhir_composer,
  ]
}
