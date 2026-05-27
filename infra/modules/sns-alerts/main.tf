###############################################################################
# SNS topic for ops alarms with:
#   * KMS-encrypted at rest
#   * one email subscription per address (pending until the recipient
#     clicks the confirmation link in their inbox)
###############################################################################

locals {
  base_tags = merge({ Project = "rxlab", Component = "sns" }, var.tags)
}

resource "aws_sns_topic" "this" {
  name              = var.topic_name
  kms_master_key_id = var.kms_key_arn
  tags              = local.base_tags

  lifecycle {
    postcondition {
      condition     = self.kms_master_key_id != null && self.kms_master_key_id != ""
      error_message = "SNS topic must be created with a customer-managed KMS key."
    }
  }
}

resource "aws_sns_topic_subscription" "email" {
  for_each = toset(var.email_subscribers)

  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = each.value
}
