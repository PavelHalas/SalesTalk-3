# Terraform Variables for SalesTalk DynamoDB Infrastructure
# Version: 1.0

variable "environment" {
  description = "Deployment environment (local, staging, production)"
  type        = string
  default     = "local"
  
  validation {
    condition     = contains(["local", "staging", "production"], var.environment)
    error_message = "Environment must be one of: local, staging, production."
  }
}

variable "create_sample_tenants" {
  description = "Whether to create sample tenant tables for development/testing"
  type        = bool
  default     = true
}

variable "sample_tenant_ids" {
  description = "Sample tenant IDs for development/testing"
  type        = list(string)
  default     = ["acme-corp-001", "techstart-inc-002"]
}

variable "enable_message_ttl" {
  description = "Enable TTL for automatic message expiration (days)"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}
