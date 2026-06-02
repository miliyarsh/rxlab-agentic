output "policy_arn" {
  description = "ARN of the Bedrock invoke IAM policy."
  value       = aws_iam_policy.this.arn
}

output "policy_name" {
  description = "Name of the Bedrock invoke IAM policy."
  value       = aws_iam_policy.this.name
}

output "foundation_model_arn" {
  description = "Pinned foundation-model ARN granted by this policy."
  value       = "arn:aws:bedrock:${var.region}::foundation-model/${var.model_id}"
}
