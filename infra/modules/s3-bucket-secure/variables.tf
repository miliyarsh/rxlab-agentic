variable "bucket_name" {
  description = "Globally-unique S3 bucket name. Must be DNS-compliant: lowercase, no underscores, no dots (avoid TLS warnings)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must be 3-63 chars, lowercase alphanumeric or hyphens, must start and end with alphanumeric, and must not contain dots or underscores."
  }
}

variable "kms_key_arn" {
  description = "ARN of the customer-managed KMS key used for SSE-KMS encryption."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "versioning_enabled" {
  description = "Whether object versioning is enabled. Defaults to true; required for state buckets and reports."
  type        = bool
  default     = true
}

variable "access_log_bucket" {
  description = "Bucket name (not ARN) to receive S3 server-access logs. Empty string disables access logging."
  type        = string
  default     = ""
}

variable "access_log_prefix" {
  description = "Key prefix under `access_log_bucket` for this bucket's access logs."
  type        = string
  default     = ""
}

variable "lifecycle_rules" {
  description = "Optional lifecycle rules. Each rule has an id, a prefix filter, and an expiration in days."
  type = list(object({
    id              = string
    prefix          = string
    expiration_days = number
  }))
  default = []

  validation {
    condition = alltrue([
      for r in var.lifecycle_rules : r.expiration_days > 0
    ])
    error_message = "Every lifecycle rule must have expiration_days > 0."
  }
}

variable "force_destroy" {
  description = "Allow the bucket to be deleted with objects still inside. Always false in prod; only true for ephemeral test buckets."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to the bucket. `Project` is always merged in."
  type        = map(string)
  default     = {}
}
