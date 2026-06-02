variable "policy_name" {
  description = "IAM customer-managed policy name."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-bedrock-[a-z0-9-]{1,40}$", var.policy_name))
    error_message = "policy_name must match `rxlab-<env>-bedrock-<role>`."
  }
}

variable "model_id" {
  description = "Bedrock model or inference profile identifier (no '*' wildcards). Use a US inference profile for on-demand invoke."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

  validation {
    condition     = !strcontains(var.model_id, "*")
    error_message = "model_id must not contain wildcards; pin to an exact model or inference profile."
  }

  validation {
    condition = (
      can(regex("^(us|global|eu)\\.[a-z0-9.-]+\\.[a-z0-9.:-]+$", var.model_id)) ||
      can(regex("^[a-z0-9.-]+\\.[a-z0-9.:-]+$", var.model_id))
    )
    error_message = "model_id must be a foundation model (anthropic.claude-...) or inference profile (us.anthropic.claude-...)."
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
  description = "Map of logical name -> IAM role ARN for Bedrock invoke policy attachments. Keys must be static (known at plan time)."
  type        = map(string)

  validation {
    condition     = length(var.attach_role_arns) > 0
    error_message = "attach_role_arns must include at least one role."
  }

  validation {
    condition = alltrue([
      for r in values(var.attach_role_arns) :
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", r))
    ])
    error_message = "Every attach_role_arns value must be a fully-qualified IAM role ARN."
  }
}

variable "tags" {
  description = "Tags applied to the policy."
  type        = map(string)
  default     = {}
}
