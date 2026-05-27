###############################################################################
# Express Step Functions state machine with:
#   * caller-provided ASL JSON template (Lambda ARNs injected via substitutions)
#   * IAM role scoped to exactly the listed Lambda ARNs
#   * CloudWatch execution logs (encrypted with the project CMK)
#   * X-Ray tracing enabled
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "stepfunctions" }, var.tags)
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid     = "SfnAssumeRole"
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = local.base_tags
}

data "aws_iam_policy_document" "inline" {
  statement {
    sid       = "InvokePipelineLambdas"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = var.lambda_arns
  }

  # X-Ray actions (segment IDs are session-bound, AWS-allowed wildcard).
  statement {
    sid    = "XRayWriteTrace"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
    ]
    resources = ["*"]
  }

  # CloudWatch Logs delivery (SFN requires these specific actions for its
  # log-delivery resource; resource-scoping is not supported by AWS for them).
  statement {
    sid    = "ManageLogDelivery"
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "inline" {
  name   = "${var.name}-inline"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.inline.json
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/vendedlogs/states/${var.name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = local.base_tags
}

resource "aws_sfn_state_machine" "this" {
  name     = var.name
  role_arn = aws_iam_role.this.arn
  type     = var.type

  definition = templatefile(var.definition_template_path, var.definition_substitutions)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.this.arn}:*"
    include_execution_data = false
    level                  = var.log_level
  }

  tracing_configuration {
    enabled = true
  }

  tags = local.base_tags

  depends_on = [aws_iam_role_policy.inline]

  lifecycle {
    precondition {
      condition     = length(var.lambda_arns) > 0
      error_message = "Pipeline must allow invocation of at least one Lambda."
    }
    postcondition {
      condition     = self.tracing_configuration[0].enabled == true
      error_message = "State machine must have X-Ray tracing enabled."
    }
  }
}
