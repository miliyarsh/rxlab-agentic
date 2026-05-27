variable "policy_name" {
  description = "IAM customer-managed policy name."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-bedrock-[a-z0-9-]{1,40}$", var.policy_name))
    error_message = "policy_name must match `rxlab-<env>-bedrock-<role>`."
  }
}

variable "model_id" {
  description = "Bedrock foundation model identifier. Must be fully qualified (no '*' wildcards). Default is Claude Haiku 4.5."
  type        = string
  default     = "anthropic.claude-haiku-4-5-20251001-v1:0"

  validation {
    condition     = !strcontains(var.model_id, "*")
    error_message = "model_id must not contain wildcards; pin to an exact model version."
  }

  validation {
    condition     = can(regex("^[a-z0-9.-]+\\.[a-z0-9.:-]+$", var.model_id))
    error_message = "model_id must look like `anthropic.claude-haiku-4-5-20251001-v1:0`."
  }
}

variable "region" {
  description = "AWS region hosting the Bedrock model invocation."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.region))
    error_message = "region must look like `us-east-1`."
  }
}

variable "attach_role_arns" {
  description = "IAM role ARNs that receive the Bedrock invoke policy. Each must be a fully-qualified IAM role ARN."
  type        = list(string)

  validation {
    condition     = length(var.attach_role_arns) > 0
    error_message = "attach_role_arns must include at least one role."
  }

  validation {
    condition = alltrue([
      for r in var.attach_role_arns :
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", r))
    ])
    error_message = "Every attach_role_arns entry must be a fully-qualified IAM role ARN."
  }
}

variable "tags" {
  description = "Tags applied to the policy."
  type        = map(string)
  default     = {}
}
