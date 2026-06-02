output "key_id" {
  description = "Key ID of the created KMS key."
  value       = aws_kms_key.this.key_id
}

output "key_arn" {
  description = "ARN of the created KMS key."
  value       = aws_kms_key.this.arn
}

output "alias_name" {
  description = "Full alias name (with the `alias/` prefix)."
  value       = aws_kms_alias.this.name
}

output "alias_arn" {
  description = "ARN of the alias resource."
  value       = aws_kms_alias.this.arn
}
