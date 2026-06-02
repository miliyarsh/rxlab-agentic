output "environment" {
  description = "Environment name."
  value       = var.environment
}

output "region" {
  description = "AWS region."
  value       = var.region
}

output "kms_key_arn" {
  description = "Customer-managed KMS key ARN for this environment."
  value       = module.kms.key_arn
}

output "reports_bucket_name" {
  description = "S3 bucket storing FHIR bundles and reports."
  value       = module.reports_bucket.bucket_id
}

output "reports_bucket_arn" {
  description = "S3 bucket ARN."
  value       = module.reports_bucket.bucket_arn
}

output "jobs_table_name" {
  description = "DynamoDB jobs table name."
  value       = module.jobs_table.table_name
}

output "agent_runs_table_name" {
  description = "DynamoDB agent_runs table name."
  value       = module.agent_runs_table.table_name
}

output "audit_table_name" {
  description = "DynamoDB audit table name."
  value       = module.audit_table.table_name
}

output "api_url" {
  description = "Base URL for the HTTP API."
  value       = module.api.api_endpoint
}

output "api_endpoint" {
  description = "Alias for api_url (backward compatibility)."
  value       = module.api.api_endpoint
}

output "analyzer_ecr_repository_url" {
  description = "ECR repository URL for the Analyzer container (CI pushes here)."
  value       = module.agent_analyzer.ecr_repository_url
}

output "state_machine_arn" {
  description = "Step Functions pipeline state machine ARN."
  value       = module.pipeline.state_machine_arn
}
