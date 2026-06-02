###############################################################################
# DynamoDB table with on-demand billing, PITR, customer-managed KMS, and
# optional TTL. Used for the rxlab `jobs`, `agent_runs`, and `audit` tables.
###############################################################################

resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.hash_key
  range_key    = var.range_key == "" ? null : var.range_key

  deletion_protection_enabled = var.deletion_protection_enabled

  attribute {
    name = var.hash_key
    type = var.hash_key_type
  }

  dynamic "attribute" {
    for_each = var.range_key == "" ? [] : [1]
    content {
      name = var.range_key
      type = var.range_key_type
    }
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  dynamic "ttl" {
    for_each = var.ttl_attribute == "" ? [] : [1]
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  tags = merge({ Project = "rxlab", Component = "dynamodb" }, var.tags)

  lifecycle {
    postcondition {
      condition     = self.point_in_time_recovery[0].enabled == true
      error_message = "Table was created without PITR; refusing to publish."
    }

    postcondition {
      condition     = self.server_side_encryption[0].enabled == true
      error_message = "Table was created without SSE; refusing to publish."
    }
  }
}
