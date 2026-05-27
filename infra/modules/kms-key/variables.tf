variable "alias" {
  description = "Alias for the KMS key, without the `alias/` prefix. Lowercase letters, digits, hyphens, and slashes only."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-/]{1,250}$", var.alias))
    error_message = "alias must be 2-251 chars, lowercase alphanumeric with hyphens or slashes, and must not start with a hyphen or slash."
  }
}

variable "description" {
  description = "Human-readable description for the key."
  type        = string
  default     = "RxLab Agentic customer-managed KMS key"
}

variable "deletion_window_days" {
  description = "Days the key remains pending deletion after `terraform destroy` (7-30, AWS-enforced)."
  type        = number
  default     = 30

  validation {
    condition     = var.deletion_window_days >= 7 && var.deletion_window_days <= 30
    error_message = "deletion_window_days must be between 7 and 30 (AWS-enforced range)."
  }
}

variable "enable_key_rotation" {
  description = "Whether automatic annual key rotation is enabled. CLAUDE.md hard rule: must be true."
  type        = bool
  default     = true

  validation {
    condition     = var.enable_key_rotation == true
    error_message = "Key rotation must be enabled (CLAUDE.md hard rule #5 / `kms-key` posture)."
  }
}

variable "additional_key_users" {
  description = "Additional IAM principal ARNs that may perform encrypt/decrypt operations with this key. Each must be a fully-qualified IAM ARN (no wildcards)."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for p in var.additional_key_users :
      can(regex("^arn:aws:iam::[0-9]{12}:(role|user|root)(/.+)?$", p))
    ])
    error_message = "Every additional_key_users entry must be a fully-qualified IAM role/user/root ARN (no wildcards)."
  }
}

variable "tags" {
  description = "Tags applied to the key. `Project` is always merged in."
  type        = map(string)
  default     = {}
}
