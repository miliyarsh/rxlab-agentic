variable "function_name" {
  description = "Lambda function name. Pattern: `rxlab-<env>-<role>`."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-[a-z0-9-]{1,50}$", var.function_name))
    error_message = "function_name must match `rxlab-<env>-<role>` where env is dev or prod."
  }
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository created and used by this Lambda. Lowercase alphanumeric with `-`, `_`, `.`, `/`."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._/-]{1,255}$", var.ecr_repository_name))
    error_message = "ecr_repository_name must be 2-256 chars, lowercase, and start with an alphanumeric."
  }
}

variable "image_tag" {
  description = "ECR image tag used by the Lambda. CI/CD pushes a new tag and updates the Lambda by retagging."
  type        = string
  default     = "latest"

  validation {
    condition     = length(var.image_tag) > 0 && length(var.image_tag) <= 128
    error_message = "image_tag must be 1-128 characters."
  }
}

variable "memory_size" {
  description = "Function memory in MB. Defaults higher than zip Lambdas because container images need more headroom."
  type        = number
  default     = 1024

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "memory_size must be 128..10240 MB."
  }
}

variable "timeout_seconds" {
  description = "Function timeout in seconds."
  type        = number
  default     = 60

  validation {
    condition     = var.timeout_seconds >= 1 && var.timeout_seconds <= 900
    error_message = "timeout_seconds must be 1..900."
  }
}

variable "environment_variables" {
  description = "Plain-text environment variables. Encrypted at rest with `kms_key_arn`."
  type        = map(string)
  default     = {}
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used for env-var, DLQ, and ECR repository encryption."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention. Must be one of the AWS-allowed values."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "log_retention_days must be an AWS-allowed retention value."
  }
}

variable "iam_policy_statements" {
  description = "Additional IAM statements for the per-Lambda role. Wildcards rejected by precondition."
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "tags" {
  description = "Tags applied to all resources in the module."
  type        = map(string)
  default     = {}
}
