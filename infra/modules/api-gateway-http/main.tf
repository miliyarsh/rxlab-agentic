###############################################################################
# API Gateway HTTP API (v2) with:
#   * $default auto-deploy stage
#   * route-level Lambda proxy integrations + per-route invoke permission
#   * stage-level throttling + JSON access logs to an encrypted log group
#   * optional CORS
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "apigw-http" }, var.tags)

  # Split "METHOD /path" -> ["METHOD", "/path"] for use in integrations.
  parsed_routes = {
    for k, v in var.routes :
    k => {
      method               = split(" ", k)[0]
      path                 = split(" ", k)[1]
      lambda_arn           = v.lambda_arn
      lambda_invoke_arn    = v.lambda_invoke_arn
      lambda_function_name = v.lambda_function_name
    }
  }
}

resource "aws_apigatewayv2_api" "this" {
  name          = var.api_name
  description   = var.description
  protocol_type = "HTTP"

  dynamic "cors_configuration" {
    for_each = length(var.cors_allow_origins) == 0 ? [] : [1]
    content {
      allow_origins = var.cors_allow_origins
      allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
      allow_headers = ["content-type", "authorization", "x-correlation-id"]
      max_age       = 600
    }
  }

  tags = local.base_tags
}

resource "aws_cloudwatch_log_group" "access_logs" {
  name              = "/aws/apigw/${var.api_name}"
  retention_in_days = var.access_log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = local.base_tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit   = var.throttle_burst_limit
    throttling_rate_limit    = var.throttle_rate_limit
    detailed_metrics_enabled = true
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access_logs.arn
    format = jsonencode({
      requestId         = "$context.requestId"
      ip                = "$context.identity.sourceIp"
      requestTime       = "$context.requestTime"
      httpMethod        = "$context.httpMethod"
      routeKey          = "$context.routeKey"
      status            = "$context.status"
      protocol          = "$context.protocol"
      responseLength    = "$context.responseLength"
      integrationStatus = "$context.integrationStatus"
      integrationError  = "$context.integrationErrorMessage"
    })
  }

  tags = local.base_tags

  lifecycle {
    postcondition {
      condition     = self.default_route_settings[0].throttling_burst_limit > 0
      error_message = "Stage must have a positive throttling_burst_limit."
    }
  }
}

resource "aws_apigatewayv2_integration" "this" {
  for_each = local.parsed_routes

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value.lambda_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "this" {
  for_each = local.parsed_routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.this[each.key].id}"
}

resource "aws_lambda_permission" "invoke" {
  for_each = local.parsed_routes

  statement_id  = "AllowAPIGatewayInvoke-${replace(replace(replace(replace(each.key, " ", "-"), "/", "-"), "{", ""), "}", "")}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
