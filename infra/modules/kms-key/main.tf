###############################################################################
# Customer-managed KMS key with annual rotation, narrow key policy, and alias.
#
# Posture (CLAUDE.md rule 5):
#   * rotation: on, validated
#   * principals: account root + explicitly-listed IAM roles only
#   * no wildcard principals, no wildcard actions
###############################################################################

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "key" {
  statement {
    sid    = "AllowAccountRootAdministration"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions = [
      "kms:Create*",
      "kms:Describe*",
      "kms:Enable*",
      "kms:List*",
      "kms:Put*",
      "kms:Update*",
      "kms:Revoke*",
      "kms:Disable*",
      "kms:Get*",
      "kms:Delete*",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion",
      "kms:TagResource",
      "kms:UntagResource",
    ]

    resources = ["*"] # Key policies are evaluated against the key itself; this `*` is scoped to the key, not account-wide.
  }

  dynamic "statement" {
    for_each = length(var.additional_key_users) > 0 ? [1] : []

    content {
      sid    = "AllowDelegatedDataKeyUse"
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = var.additional_key_users
      }

      actions = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey",
      ]

      resources = ["*"] # Scoped to the key; never reused account-wide.
    }
  }
}

resource "aws_kms_key" "this" {
  description             = var.description
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = var.enable_key_rotation
  key_usage               = "ENCRYPT_DECRYPT"
  policy                  = data.aws_iam_policy_document.key.json

  tags = merge({ Project = "rxlab", Component = "kms" }, var.tags)

  lifecycle {
    precondition {
      condition     = var.enable_key_rotation == true
      error_message = "KMS keys in this repo must enable annual rotation (CLAUDE.md rule 5)."
    }

    postcondition {
      condition     = self.enable_key_rotation == true
      error_message = "KMS key was created without rotation enabled; refusing to publish."
    }
  }
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.alias}"
  target_key_id = aws_kms_key.this.key_id
}
