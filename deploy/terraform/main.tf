# AgentOps Infrastructure as Code
# Creates DynamoDB table, S3 bucket, CloudTrail, and SageMaker roles

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# DynamoDB table for audit logs
resource "aws_dynamodb_table" "audit_log" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "plan_id"
  range_key      = "timestamp"

  attribute {
    name = "plan_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = {
    Name        = "AgentOps Audit Log"
    Environment = var.environment
    Project     = "AgentOps"
  }
}

# S3 bucket for CloudTrail logs with Object Lock
resource "aws_s3_bucket" "cloudtrail_logs" {
  bucket = "${var.cloudtrail_bucket_name}-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "AgentOps CloudTrail Logs"
    Environment = var.environment
    Project     = "AgentOps"
  }
}

resource "aws_s3_bucket_versioning" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = var.object_lock_retention_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# CloudTrail trail for DynamoDB data events
resource "aws_cloudtrail" "audit_trail" {
  name           = "${var.environment}-agentops-audit-trail"
  s3_bucket_name = aws_s3_bucket.cloudtrail_logs.id

  enable_logging                = true
  include_global_service_events = false
  is_multi_region_trail         = false

  event_selector {
    read_write_type                 = "WriteOnly"
    include_management_events      = false

    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = [aws_dynamodb_table.audit_log.arn]
    }
  }

  depends_on = [
    aws_s3_bucket_public_access_block.cloudtrail_logs,
    aws_s3_bucket_policy.cloudtrail_logs
  ]

  tags = {
    Name        = "AgentOps Audit Trail"
    Environment = var.environment
    Project     = "AgentOps"
  }
}

# S3 bucket policy for CloudTrail
resource "aws_s3_bucket_policy" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail_logs.arn
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudtrail:${var.aws_region}:${data.aws_caller_identity.current.account_id}:trail/${var.environment}-agentops-audit-trail"
          }
        }
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail_logs.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"    = "bucket-owner-full-control"
            "AWS:SourceArn"   = "arn:aws:cloudtrail:${var.aws_region}:${data.aws_caller_identity.current.account_id}:trail/${var.environment}-agentops-audit-trail"
          }
        }
      }
    ]
  })
}

# SageMaker execution role
resource "aws_iam_role" "sagemaker_execution" {
  name = var.sagemaker_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "SageMaker Execution Role"
    Environment = var.environment
    Project     = "AgentOps"
  }
}

resource "aws_iam_role_policy" "sagemaker_execution" {
  name = "SageMakerExecutionPolicy"
  role = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:CreateModel",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:CreateEndpoint",
          "sagemaker:UpdateEndpoint",
          "sagemaker:DeleteEndpoint",
          "sagemaker:DescribeModel",
          "sagemaker:DescribeEndpointConfig",
          "sagemaker:DescribeEndpoint"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::sagemaker-*/*",
          "arn:aws:s3:::sagemaker-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

