variable "table_name" {
  description = "DynamoDB table name. Alphanumeric, dot, dash, underscore; 3-255 chars."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9._-]{3,255}$", var.table_name))
    error_message = "table_name must be 3-255 chars and contain only letters, digits, '.', '_', or '-'."
  }
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used for SSE-KMS encryption at rest."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "hash_key" {
  description = "Partition key attribute name."
  type        = string

  validation {
    condition     = length(var.hash_key) > 0
    error_message = "hash_key must be non-empty."
  }
}

variable "hash_key_type" {
  description = "Attribute type of the partition key: S (string), N (number), or B (binary)."
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "hash_key_type must be one of S, N, B."
  }
}

variable "range_key" {
  description = "Optional sort key attribute name. Empty string disables the sort key."
  type        = string
  default     = ""
}

variable "range_key_type" {
  description = "Attribute type of the sort key: S, N, or B."
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.range_key_type)
    error_message = "range_key_type must be one of S, N, B."
  }
}

variable "ttl_attribute" {
  description = "Name of the TTL attribute. Empty string disables TTL. Typically `expires_at` for the `audit` table."
  type        = string
  default     = ""
}

variable "point_in_time_recovery" {
  description = "Enable PITR. CLAUDE.md requires this for every DynamoDB table in the repo."
  type        = bool
  default     = true

  validation {
    condition     = var.point_in_time_recovery == true
    error_message = "PITR must be enabled for every DynamoDB table in this repo (CLAUDE.md rule 5 / DDB posture)."
  }
}

variable "deletion_protection_enabled" {
  description = "Whether the table is protected against accidental deletion. Defaults true; flip false only for ephemeral test tables."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to the table. `Project` is always merged in."
  type        = map(string)
  default     = {}
}
