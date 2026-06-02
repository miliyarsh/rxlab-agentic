variable "name" {
  description = "State machine name."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-[a-z0-9-]{1,50}$", var.name))
    error_message = "name must match `rxlab-<env>-<role>`."
  }
}

variable "type" {
  description = "State machine type. Must be EXPRESS or STANDARD; this repo defaults to EXPRESS for cost/latency."
  type        = string
  default     = "EXPRESS"

  validation {
    condition     = contains(["EXPRESS", "STANDARD"], var.type)
    error_message = "type must be EXPRESS or STANDARD."
  }
}

variable "definition_template_path" {
  description = "Path (relative to the caller) of the ASL JSON template to render with `templatefile()`."
  type        = string
}

variable "definition_substitutions" {
  description = "Template substitutions injected into the ASL JSON (typically Lambda ARNs)."
  type        = map(string)
  default     = {}
}

variable "lambda_arns" {
  description = "Explicit list of Lambda ARNs the state machine is allowed to invoke. The IAM policy is scoped to exactly this list."
  type        = list(string)

  validation {
    condition     = length(var.lambda_arns) > 0
    error_message = "lambda_arns must include at least one ARN."
  }

  validation {
    condition = alltrue([
      for a in var.lambda_arns :
      can(regex("^arn:aws:lambda:[a-z0-9-]+:[0-9]{12}:function:rxlab-(dev|prod)-[a-z0-9-]+$", a))
    ])
    error_message = "Every lambda_arns entry must be a fully-qualified rxlab Lambda function ARN."
  }
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used to encrypt the state machine log group."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "log_retention_days" {
  description = "Retention for the SFN execution log group."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "log_retention_days must be an AWS-allowed retention value."
  }
}

variable "log_level" {
  description = "SFN log level (ALL, ERROR, FATAL, OFF). Default ERROR for production hygiene."
  type        = string
  default     = "ERROR"

  validation {
    condition     = contains(["ALL", "ERROR", "FATAL", "OFF"], var.log_level)
    error_message = "log_level must be one of ALL, ERROR, FATAL, OFF."
  }
}

variable "tags" {
  description = "Tags applied to all resources in the module."
  type        = map(string)
  default     = {}
}
