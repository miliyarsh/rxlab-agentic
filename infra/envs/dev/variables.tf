variable "environment" {
  description = "Deployment environment name. This repo intentionally has ONE environment."
  type        = string
  default     = "dev"

  validation {
    condition     = var.environment == "dev"
    error_message = "Single-environment model: this stack is always 'dev'. See infra/envs/dev/README.md."
  }
}

variable "region" {
  description = "AWS region for all resources in this stack."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.region))
    error_message = "region must look like us-east-1."
  }
}

variable "alert_email" {
  description = "Email address for ops alerts (used when SNS is wired in C9+)."
  type        = string
  default     = ""

  validation {
    condition = (
      var.alert_email == "" ||
      can(regex("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", var.alert_email))
    )
    error_message = "alert_email must be empty or a valid email address."
  }
}

variable "bedrock_model_id" {
  description = "Pinned Bedrock foundation model id (used by bedrock-access in C9+)."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "repo_root" {
  description = "Path to the repository root, relative to this env directory."
  type        = string
  default     = "../../.."
}

variable "log_retention_days" {
  description = "CloudWatch log retention for Lambdas and API access logs."
  type        = number
  default     = 14
}

variable "presigned_url_ttl_seconds" {
  description = "TTL for report presigned URLs returned by GET /jobs/{id}/report."
  type        = number
  default     = 900
}

variable "bedrock_enabled" {
  description = "When false, summarizer/critic use deterministic stubs (SSM mirror)."
  type        = bool
  default     = true
}

variable "monthly_budget_usd" {
  description = "Monthly AWS cost budget alert threshold (USD)."
  type        = number
  default     = 10

  validation {
    condition     = var.monthly_budget_usd >= 1 && var.monthly_budget_usd <= 100
    error_message = "monthly_budget_usd must be 1..100."
  }
}

variable "analyzer_image_tag" {
  description = "Immutable ECR tag for the Analyzer container image (CI passes git SHA)."
  type        = string
  default     = "bootstrap"
}

variable "cors_allow_origins" {
  description = "Browser origins allowed to call the HTTP API (frontend local + Vercel)."
  type        = list(string)
  default     = ["http://localhost:5173"]
}
