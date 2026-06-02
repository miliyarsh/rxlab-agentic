###############################################################################
# Container-image Lambda backed by a private ECR repository with:
#   * IMMUTABLE tag policy (no `latest` overwrites in prod)
#   * scan-on-push enabled
#   * KMS encryption at rest
#   * lifecycle: retain only the 10 most recent tagged images
#
# The Lambda itself mirrors lambda-fn (X-Ray on, DLQ, per-Lambda role,
# no-wildcard IAM precondition).
#
# BOOTSTRAP NOTE: AWS rejects Lambda creation if the image tag does not
# exist. On a brand-new environment:
#   1. terraform apply -target=module.<name>.aws_ecr_repository.this
#   2. push the first image to <repo>:<image_tag>
#   3. terraform apply
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "lambda-container" }, var.tags)

  has_wildcard_action = anytrue([
    for s in var.iam_policy_statements :
    anytrue([for a in s.actions : a == "*" || endswith(a, ":*")])
  ])

  has_wildcard_resource = anytrue([
    for s in var.iam_policy_statements :
    anytrue([for r in s.resources : r == "*"])
  ])

  image_uri = "${aws_ecr_repository.this.repository_url}:${var.image_tag}"
}

resource "aws_ecr_repository" "this" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key_arn
  }

  tags = local.base_tags

  lifecycle {
    postcondition {
      condition     = self.image_tag_mutability == "IMMUTABLE"
      error_message = "ECR repository must have IMMUTABLE tag mutability (CLAUDE.md container posture)."
    }
    postcondition {
      condition     = self.image_scanning_configuration[0].scan_on_push == true
      error_message = "ECR repository must have scan-on-push enabled."
    }
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the 10 most recent tagged images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
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
  message_retention_seconds         = 1209600
  kms_master_key_id                 = var.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  tags                              = local.base_tags
}

data "aws_iam_policy_document" "inline" {
  statement {
    sid    = "WriteOwnLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

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

  statement {
    sid       = "SendToDlq"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dlq.arn]
  }

  statement {
    sid       = "UseEnvVarAndDlqKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
  }

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
  function_name = var.function_name
  role          = aws_iam_role.this.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  memory_size   = var.memory_size
  timeout       = var.timeout_seconds
  kms_key_arn   = var.kms_key_arn

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
