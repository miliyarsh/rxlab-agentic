output "function_name" {
  description = "Created Lambda function name."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "Created Lambda function ARN."
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "Invoke ARN used by API Gateway / Step Functions integrations."
  value       = aws_lambda_function.this.invoke_arn
}

output "role_arn" {
  description = "ARN of the per-Lambda IAM role."
  value       = aws_iam_role.this.arn
}

output "ecr_repository_url" {
  description = "Repository URL used by CI to push new image tags."
  value       = aws_ecr_repository.this.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN."
  value       = aws_ecr_repository.this.arn
}

output "log_group_name" {
  description = "CloudWatch log group name for this Lambda."
  value       = aws_cloudwatch_log_group.this.name
}

output "dlq_arn" {
  description = "ARN of the dead-letter SQS queue."
  value       = aws_sqs_queue.dlq.arn
}
