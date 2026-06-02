output "state_machine_arn" {
  description = "Created Step Functions state machine ARN."
  value       = aws_sfn_state_machine.this.arn
}

output "state_machine_name" {
  description = "State machine name."
  value       = aws_sfn_state_machine.this.name
}

output "role_arn" {
  description = "ARN of the state machine's execution role."
  value       = aws_iam_role.this.arn
}

output "log_group_name" {
  description = "CloudWatch log group capturing SFN execution logs."
  value       = aws_cloudwatch_log_group.this.name
}
