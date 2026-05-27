variable "name_prefix" {
  description = "Prefix used for the dashboard and all alarm names."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)$", var.name_prefix))
    error_message = "name_prefix must be `rxlab-dev` or `rxlab-prod`."
  }
}

variable "region" {
  description = "AWS region (used by the dashboard widgets)."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.region))
    error_message = "region must look like `us-east-1`."
  }
}

variable "alarm_topic_arn" {
  description = "SNS topic ARN that receives alarm notifications."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+$", var.alarm_topic_arn))
    error_message = "alarm_topic_arn must be a fully-qualified SNS topic ARN."
  }
}

variable "lambda_function_names" {
  description = "Lambda function names to chart and alarm on."
  type        = list(string)

  validation {
    condition     = length(var.lambda_function_names) > 0
    error_message = "lambda_function_names must list at least one Lambda."
  }
}

variable "state_machine_arn" {
  description = "Optional Step Functions state machine ARN. Empty string disables SFN widgets/alarms."
  type        = string
  default     = ""
}

variable "api_id" {
  description = "Optional API Gateway HTTP API id. Empty string disables API widgets/alarms."
  type        = string
  default     = ""
}

variable "lambda_error_threshold" {
  description = "Errors per evaluation period that trigger the Lambda errors alarm."
  type        = number
  default     = 1

  validation {
    condition     = var.lambda_error_threshold >= 1
    error_message = "lambda_error_threshold must be >= 1."
  }
}

variable "lambda_error_period_seconds" {
  description = "Evaluation period for Lambda alarms."
  type        = number
  default     = 300

  validation {
    condition     = var.lambda_error_period_seconds >= 60 && var.lambda_error_period_seconds % 60 == 0
    error_message = "lambda_error_period_seconds must be a positive multiple of 60."
  }
}

variable "tags" {
  description = "Tags applied to all created resources."
  type        = map(string)
  default     = {}
}
