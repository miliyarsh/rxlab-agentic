variable "topic_name" {
  description = "SNS topic name."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-[a-z0-9-]{1,50}$", var.topic_name))
    error_message = "topic_name must match `rxlab-<env>-<role>`."
  }
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used for SNS at-rest encryption."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "email_subscribers" {
  description = "List of email addresses subscribed to the topic. Each receives a confirmation email on first apply; must be confirmed before alarms reach the inbox."
  type        = list(string)

  validation {
    condition     = length(var.email_subscribers) > 0
    error_message = "email_subscribers must contain at least one address."
  }

  validation {
    condition = alltrue([
      for e in var.email_subscribers :
      can(regex("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", e))
    ])
    error_message = "Every email_subscribers entry must be a valid email address."
  }
}

variable "tags" {
  description = "Tags applied to all resources in the module."
  type        = map(string)
  default     = {}
}
