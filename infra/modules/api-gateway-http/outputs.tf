output "api_id" {
  description = "HTTP API id."
  value       = aws_apigatewayv2_api.this.id
}

output "api_arn" {
  description = "HTTP API ARN."
  value       = aws_apigatewayv2_api.this.arn
}

output "api_endpoint" {
  description = "Base invoke URL (`https://<api-id>.execute-api.<region>.amazonaws.com`)."
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "execution_arn" {
  description = "Execution ARN used by route-level Lambda invoke permissions."
  value       = aws_apigatewayv2_api.this.execution_arn
}

output "stage_name" {
  description = "Deployed stage name (always `$default`)."
  value       = aws_apigatewayv2_stage.default.name
}

output "access_log_group_name" {
  description = "CloudWatch log group capturing API access logs."
  value       = aws_cloudwatch_log_group.access_logs.name
}
