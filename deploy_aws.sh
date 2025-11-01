#!/bin/bash
# Deploy AgentOps Orchestrator to AWS

set -e

echo "🚀 Deploying AgentOps to AWS..."
echo ""

# Get AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
ECR_REPO="agentops-orchestrator"

echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Create ECR repository
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO --region $REGION --output json

# Get ECR login
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Step 2: Build Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPO:latest .

# Step 3: Tag and push to ECR
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:latest"
echo "📤 Tagging and pushing to ECR..."
docker tag $ECR_REPO:latest $ECR_URI
docker push $ECR_URI

echo ""
echo "✅ Docker image pushed to ECR: $ECR_URI"
echo ""
echo "Next steps:"
echo "1. Deploy to AWS App Runner or ECS"
echo "2. Or use: aws apprunner create-service --cli-input-json file://apprunner-config.json"

