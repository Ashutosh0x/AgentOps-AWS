variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "dynamodb_table_name" {
  description = "Name of DynamoDB table for audit logs"
  type        = string
  default     = "agentops-audit-log"
}

variable "cloudtrail_bucket_name" {
  description = "Base name for CloudTrail logs S3 bucket"
  type        = string
  default     = "agentops-cloudtrail-logs"
}

variable "object_lock_retention_days" {
  description = "Number of days to retain CloudTrail logs with Object Lock"
  type        = number
  default     = 90
}

variable "sagemaker_role_name" {
  description = "Name of SageMaker execution IAM role"
  type        = string
  default     = "SageMakerExecutionRole"
}

variable "frontend_bucket_name" {
  description = "Base name for frontend S3 bucket"
  type        = string
  default     = "agentops-frontend"
}

