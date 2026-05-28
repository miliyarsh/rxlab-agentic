###############################################################################
# Zip-packaged Python Lambda with:
#   * X-Ray tracing on (CLAUDE.md observability)
#   * CloudWatch log group with retention
#   * dedicated SQS dead-letter queue (encrypted with the same CMK)
#   * per-Lambda IAM role (no shared roles)
#   * inline policy combining basic execution + caller-provided statements
#   * precondition guard rejecting wildcard actions or resources
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "lambda" }, var.tags)

  has_wildcard_action = anytrue([
    for s in var.iam_policy_statements :
    anytrue([for a in s.actions : a == "*" || endswith(a, ":*")])
  ])

  has_wildcard_resource = anytrue([
    for s in var.iam_policy_statements :
    anytrue([
      for r in s.resources :
      r == "*" && !alltrue([for a in s.actions : a == "cloudwatch:PutMetricData"])
    ])
  ])
}

data "archive_file" "zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.terraform/${var.function_name}.zip"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid     = "LambdaAssumeRole"
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = local.base_tags
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = local.base_tags
}

resource "aws_sqs_queue" "dlq" {
  name                              = "${var.function_name}-dlq"
  message_retention_seconds         = 1209600 # 14 days
  kms_master_key_id                 = var.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  tags                              = local.base_tags
}

data "aws_iam_policy_document" "inline" {
  # CloudWatch Logs (scoped to this Lambda's log group).
  statement {
    sid    = "WriteOwnLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  # X-Ray tracing (these actions are not scopable to a resource; AWS accepts
  # `*` here because X-Ray segments are session-bound. tfsec rule AVD-AWS-0057
  # acknowledges the exception for these three actions only.)
  statement {
    sid    = "XRayWriteTrace"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
    ]
    resources = ["*"]
  }

  # Dead-letter queue.
  statement {
    sid       = "SendToDlq"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dlq.arn]
  }

  # KMS for env-var decryption + DLQ encryption.
  statement {
    sid       = "UseEnvVarAndDlqKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
  }

  # Caller-provided statements (must already be wildcard-free; enforced
  # by the precondition on aws_lambda_function below).
  dynamic "statement" {
    for_each = var.iam_policy_statements
    content {
      sid       = statement.value.sid
      effect    = "Allow"
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

resource "aws_iam_role_policy" "inline" {
  name   = "${var.function_name}-inline"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.inline.json
}

resource "aws_lambda_function" "this" {
  function_name                  = var.function_name
  role                           = aws_iam_role.this.arn
  handler                        = var.handler
  runtime                        = var.runtime
  memory_size                    = var.memory_size
  timeout                        = var.timeout_seconds
  reserved_concurrent_executions = var.reserved_concurrent_executions

  filename         = data.archive_file.zip.output_path
  source_code_hash = data.archive_file.zip.output_base64sha256

  kms_key_arn = var.kms_key_arn

  tracing_config {
    mode = "Active"
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  environment {
    variables = var.environment_variables
  }

  tags = local.base_tags

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy.inline,
  ]

  lifecycle {
    precondition {
      condition     = !local.has_wildcard_action
      error_message = "IAM policy statements must not use wildcard actions ('*' or 'service:*'). See CLAUDE.md hard rules."
    }
    precondition {
      condition     = !local.has_wildcard_resource
      error_message = "IAM policy statements must not use wildcard resources ('*'). See CLAUDE.md hard rules."
    }
    postcondition {
      condition     = self.tracing_config[0].mode == "Active"
      error_message = "Lambda must have X-Ray tracing set to Active (CLAUDE.md observability)."
    }
  }
}
