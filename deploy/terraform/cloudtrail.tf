# CloudTrail configuration is included in main.tf
# This file is kept for clarity and potential future expansion

# Note: CloudTrail Data Events are configured in main.tf
# Data Events capture DynamoDB item-level operations (PutItem, UpdateItem, etc.)
# and write them to the S3 bucket with Object Lock enabled for immutability

