###############################################################################
# C6 — API Lambda functions + HTTP API Gateway routes.
###############################################################################

locals {
  api_lambdas = {
    submit_job = {
      handler = "service.api.submit_job.handler.handler"
      timeout = 30
    }
    get_job = {
      handler = "service.api.get_job.handler.handler"
      timeout = 15
    }
    get_report = {
      handler = "service.api.get_report.handler.handler"
      timeout = 15
    }
    upload_vcf = {
      handler = "service.api.upload_vcf.handler.handler"
      timeout = 30
    }
    healthz = {
      handler = "service.api.healthz.handler.handler"
      timeout = 10
    }
  }
}

module "api_submit_job" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-submit-job"
  handler            = local.api_lambdas.submit_job.handler
  package_zip_path   = local.service_zip_path
  source_code_hash   = local.service_source_code_hash
  depends_on         = [terraform_data.service_package, module.pipeline]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = local.api_lambdas.submit_job.timeout
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT       = var.environment
    JOBS_TABLE        = module.jobs_table.table_name
    REPORTS_BUCKET    = module.reports_bucket.bucket_id
    STATE_MACHINE_ARN = module.pipeline.state_machine_arn
    AGENT_RUNS_TABLE  = module.agent_runs_table.table_name
    PRESIGNED_URL_TTL = tostring(var.presigned_url_ttl_seconds)
  }

  iam_policy_statements = [
    {
      sid = "ReadWriteJobs"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
      ]
      resources = [module.jobs_table.table_arn]
    },
    {
      sid       = "StartPipeline"
      actions   = ["states:StartExecution"]
      resources = [module.pipeline.state_machine_arn]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]

}

module "api_get_job" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-get-job"
  handler            = local.api_lambdas.get_job.handler
  package_zip_path = local.service_zip_path
  source_code_hash = local.service_source_code_hash
  depends_on       = [terraform_data.service_package]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = local.api_lambdas.get_job.timeout
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT = var.environment
    JOBS_TABLE  = module.jobs_table.table_name
  }

  iam_policy_statements = [
    {
      sid       = "ReadJobs"
      actions   = ["dynamodb:GetItem"]
      resources = [module.jobs_table.table_arn]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "api_get_report" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-get-report"
  handler            = local.api_lambdas.get_report.handler
  package_zip_path = local.service_zip_path
  source_code_hash = local.service_source_code_hash
  depends_on       = [terraform_data.service_package]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = local.api_lambdas.get_report.timeout
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT       = var.environment
    JOBS_TABLE        = module.jobs_table.table_name
    REPORTS_BUCKET    = module.reports_bucket.bucket_id
    PRESIGNED_URL_TTL = tostring(var.presigned_url_ttl_seconds)
  }

  iam_policy_statements = [
    {
      sid       = "ReadJobs"
      actions   = ["dynamodb:GetItem"]
      resources = [module.jobs_table.table_arn]
    },
    {
      sid = "PresignReportObject"
      actions = [
        "s3:GetObject",
        "s3:GetObjectVersion",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/*"]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "api_upload_vcf" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-upload-vcf"
  handler            = local.api_lambdas.upload_vcf.handler
  package_zip_path   = local.service_zip_path
  source_code_hash   = local.service_source_code_hash
  depends_on         = [terraform_data.service_package]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = local.api_lambdas.upload_vcf.timeout
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT    = var.environment
    REPORTS_BUCKET = module.reports_bucket.bucket_id
  }

  iam_policy_statements = [
    {
      sid = "WriteUploadedVcf"
      actions = [
        "s3:PutObject",
      ]
      resources = ["${module.reports_bucket.bucket_arn}/uploads/*"]
    },
    {
      sid       = "UseDataKey"
      actions   = ["kms:Encrypt", "kms:GenerateDataKey"]
      resources = [module.kms.key_arn]
    },
  ]
}

module "api_healthz" {
  source = "../../modules/lambda-fn"

  function_name      = "${local.name_prefix}-healthz"
  handler            = local.api_lambdas.healthz.handler
  package_zip_path = local.service_zip_path
  source_code_hash = local.service_source_code_hash
  depends_on       = [terraform_data.service_package]
  kms_key_arn        = module.kms.key_arn
  timeout_seconds    = local.api_lambdas.healthz.timeout
  log_retention_days = var.log_retention_days

  environment_variables = {
    ENVIRONMENT = var.environment
    VERSION     = "0.1.0"
  }
}

module "api" {
  source = "../../modules/api-gateway-http"

  api_name    = "${local.name_prefix}-api"
  kms_key_arn = module.kms.key_arn

  cors_allow_origins = var.cors_allow_origins

  routes = {
    "POST /jobs" = {
      lambda_arn           = module.api_submit_job.function_arn
      lambda_invoke_arn    = module.api_submit_job.invoke_arn
      lambda_function_name = module.api_submit_job.function_name
    }
    "GET /jobs/{id}" = {
      lambda_arn           = module.api_get_job.function_arn
      lambda_invoke_arn    = module.api_get_job.invoke_arn
      lambda_function_name = module.api_get_job.function_name
    }
    "GET /jobs/{id}/report" = {
      lambda_arn           = module.api_get_report.function_arn
      lambda_invoke_arn    = module.api_get_report.invoke_arn
      lambda_function_name = module.api_get_report.function_name
    }
    "POST /uploads/vcf" = {
      lambda_arn           = module.api_upload_vcf.function_arn
      lambda_invoke_arn    = module.api_upload_vcf.invoke_arn
      lambda_function_name = module.api_upload_vcf.function_name
    }
    "GET /healthz" = {
      lambda_arn           = module.api_healthz.function_arn
      lambda_invoke_arn    = module.api_healthz.invoke_arn
      lambda_function_name = module.api_healthz.function_name
    }
  }

  depends_on = [
    module.api_submit_job,
    module.api_get_job,
    module.api_get_report,
    module.api_upload_vcf,
    module.api_healthz,
  ]
}
