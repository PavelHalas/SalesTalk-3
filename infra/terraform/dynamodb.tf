# DynamoDB Tables for SalesTalk Multi-Tenant Architecture
# Version: 1.0
# Author: Data Engineer Agent
# Date: November 2025

# ============================================================================
# Global Tenants Metadata Table
# ============================================================================

resource "aws_dynamodb_table" "tenants_metadata" {
  name           = "tenants-metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tenantId"
  
  attribute {
    name = "tenantId"
    type = "S"
  }

  # Global Secondary Index for querying by owner email
  attribute {
    name = "ownerEmail"
    type = "S"
  }

  global_secondary_index {
    name            = "OwnerEmailIndex"
    hash_key        = "ownerEmail"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by status
  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Service     = "salestalk"
    ManagedBy   = "terraform"
    Purpose     = "tenant-metadata"
  }
}

# ============================================================================
# Per-Tenant Messages Table Module
# ============================================================================

# This is a template/module for creating per-tenant message tables
# Actual tenant tables are created dynamically via Lambda or Terraform modules

resource "aws_dynamodb_table" "tenant_messages_template" {
  count = var.create_sample_tenants ? 2 : 0

  name           = "tenant-${var.sample_tenant_ids[count.index]}-messages"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  # GSI for querying messages by session
  attribute {
    name = "sessionId"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "SessionIndex"
    hash_key        = "sessionId"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI for querying by message type (user, assistant, system)
  attribute {
    name = "sender"
    type = "S"
  }

  global_secondary_index {
    name            = "SenderIndex"
    hash_key        = "sender"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # TTL for automatic message expiration (optional, disabled by default)
  ttl {
    enabled        = var.enable_message_ttl
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Service     = "salestalk"
    ManagedBy   = "terraform"
    TenantId    = var.sample_tenant_ids[count.index]
    Purpose     = "conversation-messages"
  }
}

# ============================================================================
# Per-Tenant Metrics Table Module
# ============================================================================

resource "aws_dynamodb_table" "tenant_metrics_template" {
  count = var.create_sample_tenants ? 2 : 0

  name           = "tenant-${var.sample_tenant_ids[count.index]}-metrics"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  # GSI for time-based queries
  attribute {
    name = "metricType"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "MetricTypeIndex"
    hash_key        = "metricType"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI for dimensional queries (e.g., by region, product)
  attribute {
    name = "dimensionKey"
    type = "S"
  }

  global_secondary_index {
    name            = "DimensionIndex"
    hash_key        = "dimensionKey"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Service     = "salestalk"
    ManagedBy   = "terraform"
    TenantId    = var.sample_tenant_ids[count.index]
    Purpose     = "business-metrics"
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "tenants_metadata_table_name" {
  description = "Name of the global tenants metadata table"
  value       = aws_dynamodb_table.tenants_metadata.name
}

output "tenants_metadata_table_arn" {
  description = "ARN of the global tenants metadata table"
  value       = aws_dynamodb_table.tenants_metadata.arn
}

output "sample_tenant_messages_tables" {
  description = "Names of sample tenant messages tables"
  value       = var.create_sample_tenants ? aws_dynamodb_table.tenant_messages_template[*].name : []
}

output "sample_tenant_metrics_tables" {
  description = "Names of sample tenant metrics tables"
  value       = var.create_sample_tenants ? aws_dynamodb_table.tenant_metrics_template[*].name : []
}
