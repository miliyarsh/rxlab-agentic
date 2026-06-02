output "dashboard_name" {
  description = "CloudWatch dashboard name."
  value       = aws_cloudwatch_dashboard.this.dashboard_name
}

output "lambda_error_alarm_arns" {
  description = "ARNs of the per-Lambda error alarms."
  value       = { for k, a in aws_cloudwatch_metric_alarm.lambda_errors : k => a.arn }
}

output "lambda_throttle_alarm_arns" {
  description = "ARNs of the per-Lambda throttle alarms."
  value       = { for k, a in aws_cloudwatch_metric_alarm.lambda_throttles : k => a.arn }
}

output "sfn_failed_alarm_arn" {
  description = "ARN of the SFN executions-failed alarm, when configured."
  value       = length(aws_cloudwatch_metric_alarm.sfn_failed) == 0 ? "" : aws_cloudwatch_metric_alarm.sfn_failed[0].arn
}

output "api_5xx_alarm_arn" {
  description = "ARN of the API Gateway 5xx alarm, when configured."
  value       = length(aws_cloudwatch_metric_alarm.api_5xx) == 0 ? "" : aws_cloudwatch_metric_alarm.api_5xx[0].arn
}
