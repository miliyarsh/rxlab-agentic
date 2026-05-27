output "table_name" {
  description = "Created DynamoDB table name."
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "Created DynamoDB table ARN."
  value       = aws_dynamodb_table.this.arn
}

output "table_id" {
  description = "DynamoDB table id (same as name)."
  value       = aws_dynamodb_table.this.id
}
