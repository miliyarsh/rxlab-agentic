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
  foundation_model_arn = "arn:aws:bedrock:${var.region}::foundation-model/${var.model_id}"
}

data "aws_iam_policy_document" "invoke" {
  statement {
    sid    = "InvokePinnedModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
    ]

    resources = [local.foundation_model_arn]
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
  for_each = toset(var.attach_role_arns)

  role       = element(split("/", each.value), length(split("/", each.value)) - 1)
  policy_arn = aws_iam_policy.this.arn
}
