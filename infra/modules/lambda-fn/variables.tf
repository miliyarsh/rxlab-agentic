variable "function_name" {
  description = "Lambda function name. Pattern: `rxlab-<env>-<role>`."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-[a-z0-9-]{1,50}$", var.function_name))
    error_message = "function_name must match `rxlab-<env>-<role>` where env is dev or prod."
  }
}

variable "handler" {
  description = "Python entrypoint (`module.attribute`), e.g. `handler.handler`."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z_][a-zA-Z0-9_]*\\.[a-zA-Z_][a-zA-Z0-9_]*$", var.handler))
    error_message = "handler must look like `module.attribute` (alphanumeric/underscore identifiers)."
  }
}

variable "runtime" {
  description = "Lambda runtime. Only Python 3.11/3.12 are supported in this repo."
  type        = string
  default     = "python3.11"

  validation {
    condition     = contains(["python3.11", "python3.12"], var.runtime)
    error_message = "runtime must be python3.11 or python3.12."
  }
}

variable "source_dir" {
  description = "Absolute or module-relative path to the handler source directory to zip and upload."
  type        = string
}

variable "memory_size" {
  description = "Function memory in MB."
  type        = number
  default     = 256

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 3008
    error_message = "memory_size must be 128..3008 MB."
  }
}

variable "timeout_seconds" {
  description = "Function timeout in seconds."
  type        = number
  default     = 30

  validation {
    condition     = var.timeout_seconds >= 1 && var.timeout_seconds <= 900
    error_message = "timeout_seconds must be 1..900."
  }
}

variable "environment_variables" {
  description = "Plain-text environment variables (config only, no secrets). Encrypted at rest with `kms_key_arn`."
  type        = map(string)
  default     = {}
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used for env-var encryption and DLQ encryption."
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
  description = "Additional IAM statements for the per-Lambda role. Wildcard actions or resources are rejected by precondition."
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "reserved_concurrent_executions" {
  description = "Reserved concurrency. -1 disables reservation."
  type        = number
  default     = -1
}

variable "tags" {
  description = "Tags applied to all resources in the module."
  type        = map(string)
  default     = {}
}
