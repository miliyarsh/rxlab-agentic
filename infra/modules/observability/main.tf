###############################################################################
# CloudWatch dashboard + per-Lambda / API / SFN alarms.
# Alarm notifications fan out via the caller-provided SNS topic.
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "observability" }, var.tags)

  lambda_error_widgets = [
    for fn in var.lambda_function_names : {
      type = "metric"
      properties = {
        title   = "${fn} errors"
        region  = var.region
        view    = "timeSeries"
        stacked = false
        metrics = [
          ["AWS/Lambda", "Errors", "FunctionName", fn, { stat = "Sum" }],
          [".", "Invocations", ".", ".", { stat = "Sum" }],
          [".", "Throttles", ".", ".", { stat = "Sum" }],
        ]
      }
    }
  ]

  sfn_widgets = var.state_machine_arn == "" ? [] : [{
    type = "metric"
    properties = {
      title   = "Pipeline executions"
      region  = var.region
      view    = "timeSeries"
      stacked = false
      metrics = [
        ["AWS/States", "ExecutionsStarted", "StateMachineArn", var.state_machine_arn, { stat = "Sum" }],
        [".", "ExecutionsFailed", ".", ".", { stat = "Sum" }],
        [".", "ExecutionsTimedOut", ".", ".", { stat = "Sum" }],
      ]
    }
  }]

  api_widgets = var.api_id == "" ? [] : [{
    type = "metric"
    properties = {
      title   = "HTTP API 5xx"
      region  = var.region
      view    = "timeSeries"
      stacked = false
      metrics = [
        ["AWS/ApiGateway", "5XXError", "ApiId", var.api_id, { stat = "Sum" }],
        [".", "4XXError", ".", ".", { stat = "Sum" }],
        [".", "Count", ".", ".", { stat = "Sum" }],
      ]
    }
  }]
}

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.name_prefix}-overview"

  dashboard_body = jsonencode({
    widgets = concat(local.lambda_error_widgets, local.sfn_widgets, local.api_widgets)
  })
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${var.name_prefix}-${each.value}-errors"
  alarm_description   = "Lambda ${each.value} errors >= ${var.lambda_error_threshold} in ${var.lambda_error_period_seconds}s"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = var.lambda_error_period_seconds
  statistic           = "Sum"
  threshold           = var.lambda_error_threshold
  treat_missing_data  = "notBreaching"

  dimensions = { FunctionName = each.value }

  alarm_actions = [var.alarm_topic_arn]
  ok_actions    = [var.alarm_topic_arn]

  tags = local.base_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${var.name_prefix}-${each.value}-throttles"
  alarm_description   = "Lambda ${each.value} throttling detected"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = var.lambda_error_period_seconds
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = { FunctionName = each.value }

  alarm_actions = [var.alarm_topic_arn]
  ok_actions    = [var.alarm_topic_arn]

  tags = local.base_tags
}

resource "aws_cloudwatch_metric_alarm" "sfn_failed" {
  count = var.state_machine_arn == "" ? 0 : 1

  alarm_name          = "${var.name_prefix}-pipeline-failed"
  alarm_description   = "Step Functions pipeline executions failed"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = var.lambda_error_period_seconds
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = { StateMachineArn = var.state_machine_arn }

  alarm_actions = [var.alarm_topic_arn]
  ok_actions    = [var.alarm_topic_arn]

  tags = local.base_tags
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  count = var.api_id == "" ? 0 : 1

  alarm_name          = "${var.name_prefix}-api-5xx"
  alarm_description   = "HTTP API 5xx responses detected"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = var.lambda_error_period_seconds
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = { ApiId = var.api_id }

  alarm_actions = [var.alarm_topic_arn]
  ok_actions    = [var.alarm_topic_arn]

  tags = local.base_tags
}
