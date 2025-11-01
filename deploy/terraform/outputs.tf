output "dynamodb_table_name" {
  description = "Name of DynamoDB audit log table"
  value       = aws_dynamodb_table.audit_log.name
}

output "dynamodb_table_arn" {
  description = "ARN of DynamoDB audit log table"
  value       = aws_dynamodb_table.audit_log.arn
}

output "cloudtrail_bucket_name" {
  description = "Name of S3 bucket for CloudTrail logs"
  value       = aws_s3_bucket.cloudtrail_logs.id
}

output "cloudtrail_bucket_arn" {
  description = "ARN of S3 bucket for CloudTrail logs"
  value       = aws_s3_bucket.cloudtrail_logs.arn
}

output "cloudtrail_trail_arn" {
  description = "ARN of CloudTrail trail"
  value       = aws_cloudtrail.audit_trail.arn
}

output "sagemaker_role_arn" {
  description = "ARN of SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.arn
}

output "sagemaker_role_name" {
  description = "Name of SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.name
}

output "frontend_bucket_name" {
  description = "Name of S3 bucket for frontend"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

