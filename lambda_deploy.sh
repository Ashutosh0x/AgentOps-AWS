#!/bin/bash
# Deploy AgentOps Orchestrator to AWS Lambda

set -e

echo "🚀 Deploying AgentOps to AWS Lambda..."
echo ""

REGION="us-east-1"
FUNCTION_NAME="agentops-orchestrator"
ROLE_NAME="agentops-lambda-role"
BUCKET_NAME="agentops-deployments-$(aws sts get-caller-identity --query Account --output text)"

# Step 1: Create IAM role for Lambda
echo "📋 Creating IAM role for Lambda..."
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || \
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --query 'Role.Arn' \
        --output text)

echo "Role ARN: $ROLE_ARN"

# Attach policies
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

# Step 2: Create S3 bucket for deployment package
echo "📦 Creating S3 bucket for deployment..."
aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || echo "Bucket already exists"

# Step 3: Create deployment package
echo "📦 Creating deployment package..."
zip -r agentops-lambda.zip . -x "*.git*" -x "*.pyc" -x "__pycache__/*" -x "venv/*" -x ".venv/*" -x "*.md" -x "tests/*" -x "demo/*" -x "deploy/*" -x ".env"

# Step 4: Upload to S3
echo "📤 Uploading to S3..."
aws s3 cp agentops-lambda.zip s3://$BUCKET_NAME/ --region $REGION

# Step 5: Create or update Lambda function
echo "🔧 Creating/updating Lambda function..."
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_handler.handler \
    --code S3Bucket=$BUCKET_NAME,S3Key=agentops-lambda.zip \
    --timeout 900 \
    --memory-size 1024 \
    --environment Variables="{
        AWS_REGION=$REGION,
        DYNAMODB_TABLE_NAME=agentops-audit-log,
        EXECUTE=false
    }" \
    --region $REGION 2>/dev/null || \
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --s3-bucket $BUCKET_NAME \
        --s3-key agentops-lambda.zip \
        --region $REGION

# Step 6: Create API Gateway
echo "🌐 Setting up API Gateway..."
# This requires additional steps - for now, we'll create a simple HTTP API

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next: Set up API Gateway or use Lambda Function URL"

