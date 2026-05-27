variable "api_name" {
  description = "API Gateway HTTP API name."
  type        = string

  validation {
    condition     = can(regex("^rxlab-(dev|prod)-[a-z0-9-]{1,50}$", var.api_name))
    error_message = "api_name must match `rxlab-<env>-<role>`."
  }
}

variable "description" {
  description = "Free-text API description."
  type        = string
  default     = "RxLab Agentic HTTP API"
}

variable "routes" {
  description = "Map of `METHOD /path` -> {lambda_arn, lambda_invoke_arn, lambda_function_name}."
  type = map(object({
    lambda_arn           = string
    lambda_invoke_arn    = string
    lambda_function_name = string
  }))

  validation {
    condition = alltrue([
      for k in keys(var.routes) :
      can(regex("^(GET|POST|PUT|PATCH|DELETE) /[a-zA-Z0-9/{}_-]*$", k))
    ])
    error_message = "Each routes key must look like `METHOD /path`, e.g. `POST /jobs` or `GET /jobs/{id}`."
  }
}

variable "throttle_burst_limit" {
  description = "Per-stage burst limit applied across all routes."
  type        = number
  default     = 100

  validation {
    condition     = var.throttle_burst_limit >= 1
    error_message = "throttle_burst_limit must be >= 1."
  }
}

variable "throttle_rate_limit" {
  description = "Per-stage steady-state request rate per second."
  type        = number
  default     = 50

  validation {
    condition     = var.throttle_rate_limit >= 1
    error_message = "throttle_rate_limit must be >= 1."
  }
}

variable "cors_allow_origins" {
  description = "List of CORS-allowed origins. Empty list disables CORS (server-to-server callers)."
  type        = list(string)
  default     = []
}

variable "access_log_retention_days" {
  description = "Retention for the API Gateway access log group."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.access_log_retention_days)
    error_message = "access_log_retention_days must be an AWS-allowed retention value."
  }
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used to encrypt the access log group."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/[a-f0-9-]{36}$", var.kms_key_arn))
    error_message = "kms_key_arn must be a fully-qualified KMS key ARN."
  }
}

variable "tags" {
  description = "Tags applied to all resources in the module."
  type        = map(string)
  default     = {}
}
