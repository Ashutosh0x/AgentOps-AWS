#!/bin/bash
# Deploy frontend to S3 + CloudFront

set -e

# Configuration
BUCKET_NAME="${FRONTEND_BUCKET_NAME:-agentops-frontend}"
DISTRIBUTION_ID="${CLOUDFRONT_DIST_ID:-}"
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building frontend...${NC}"
cd frontend
npm install
npm run build

if [ ! -d "dist" ]; then
    echo "Error: dist directory not found after build"
    exit 1
fi

echo -e "${BLUE}Syncing to S3 bucket: ${BUCKET_NAME}...${NC}"
aws s3 sync dist/ s3://${BUCKET_NAME}/ --delete --region ${REGION}

if [ -n "$DISTRIBUTION_ID" ]; then
    echo -e "${BLUE}Invalidating CloudFront cache...${NC}"
    aws cloudfront create-invalidation \
        --distribution-id ${DISTRIBUTION_ID} \
        --paths "/*" \
        --region ${REGION}
    
    echo -e "${GREEN}✓ Frontend deployed and cache invalidated${NC}"
else
    echo -e "${GREEN}✓ Frontend deployed to S3${NC}"
    echo "Note: Set CLOUDFRONT_DIST_ID environment variable to invalidate CloudFront cache"
fi

echo -e "${GREEN}Deployment complete!${NC}"

