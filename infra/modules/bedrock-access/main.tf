###############################################################################
# Bedrock access policy scoped to a SINGLE foundation-model ARN.
#
# Resource ARN format (AWS docs):
#   arn:aws:bedrock:<region>::foundation-model/<model-id>
#
# We attach the policy to the caller-provided IAM roles (typically the
# summarizer + critic Lambda roles). Wildcards anywhere are rejected.
###############################################################################

locals {
  base_tags            = merge({ Project = "rxlab", Component = "bedrock-access" }, var.tags)
  is_inference_profile = can(regex("^(us|global|eu)\\.", var.model_id))
  foundation_model_id  = local.is_inference_profile ? join(".", slice(split(".", var.model_id), 1, length(split(".", var.model_id)))) : var.model_id
  foundation_model_arn = "arn:aws:bedrock:${var.region}::foundation-model/${local.foundation_model_id}"
  inference_profile_arn = local.is_inference_profile ? "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.model_id}" : null
  # US system inference profiles route across these regions; IAM must allow each foundation-model ARN.
  us_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
  cross_region_foundation_arns = local.is_inference_profile && startswith(var.model_id, "us.") ? [
    for r in local.us_profile_regions :
    "arn:aws:bedrock:${r}::foundation-model/${local.foundation_model_id}"
  ] : []
  invoke_resources = distinct(concat(
    [local.foundation_model_arn],
    local.is_inference_profile ? [local.inference_profile_arn] : [],
    local.cross_region_foundation_arns,
  ))
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "invoke" {
  statement {
    sid    = "InvokePinnedModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
    ]

    resources = local.invoke_resources
  }
}

resource "aws_iam_policy" "this" {
  name        = var.policy_name
  description = "Bedrock invoke for ${var.model_id}"
  policy      = data.aws_iam_policy_document.invoke.json
  tags        = local.base_tags

  lifecycle {
    postcondition {
      condition     = !strcontains(self.policy, "\"*\"")
      error_message = "Bedrock policy contains a wildcard; refusing to publish."
    }
  }
}

resource "aws_iam_role_policy_attachment" "this" {
  for_each = var.attach_role_arns

  role       = element(split("/", each.value), length(split("/", each.value)) - 1)
  policy_arn = aws_iam_policy.this.arn
}
