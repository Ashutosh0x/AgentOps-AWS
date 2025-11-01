#!/bin/bash
# AgentOps MVP Demo Script
# Demonstrates end-to-end autonomous deployment flow

set -e

API_BASE="http://localhost:8000"

echo "🚀 AgentOps MVP Demo"
echo "===================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if orchestrator is running
echo -e "${BLUE}Checking if orchestrator is running...${NC}"
if ! curl -s "$API_BASE/" > /dev/null; then
    echo -e "${YELLOW}⚠️  Orchestrator not running. Starting it...${NC}"
    echo "Please start the orchestrator first:"
    echo "  python -m orchestrator.main"
    echo "  or"
    echo "  uvicorn orchestrator.main:app --reload"
    exit 1
fi

echo -e "${GREEN}✅ Orchestrator is running${NC}"
echo ""

# Step 1: Upload policy documents
echo -e "${BLUE}Step 1: Uploading policy documents to retriever...${NC}"
python scripts/upload_docs.py
echo ""

# Step 2: Staging deployment (no approval)
echo -e "${BLUE}Step 2: Submitting staging deployment intent (no approval required)...${NC}"
STAGING_RESPONSE=$(curl -s -X POST "$API_BASE/intent" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "alice@example.com",
        "intent": "deploy llama-3.1 8B for chatbot-x",
        "env": "staging",
        "constraints": {"budget_usd_per_hour": 15.0}
    }')

STAGING_PLAN_ID=$(echo $STAGING_RESPONSE | jq -r '.plan_id')
STAGING_STATUS=$(echo $STAGING_RESPONSE | jq -r '.status')

echo "Response:"
echo $STAGING_RESPONSE | jq '.'
echo ""

if [ "$STAGING_STATUS" == "deploying" ]; then
    echo -e "${GREEN}✅ Staging deployment started (no approval needed)${NC}"
    echo "Plan ID: $STAGING_PLAN_ID"
    echo ""
    
    # Wait a bit and check status
    echo "Waiting 3 seconds and checking deployment status..."
    sleep 3
    curl -s "$API_BASE/plan/$STAGING_PLAN_ID" | jq '.plan | {plan_id, status, artifact: .artifact.model_name}'
    echo ""
else
    echo -e "${YELLOW}⚠️  Unexpected status: $STAGING_STATUS${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Submitting production deployment intent (requires approval)...${NC}"
PROD_RESPONSE=$(curl -s -X POST "$API_BASE/intent" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "alice@example.com",
        "intent": "deploy llama-3.1 8B for chatbot-x",
        "env": "prod",
        "constraints": {"budget_usd_per_hour": 50.0}
    }')

PROD_PLAN_ID=$(echo $PROD_RESPONSE | jq -r '.plan_id')
PROD_STATUS=$(echo $PROD_RESPONSE | jq -r '.status')

echo "Response:"
echo $PROD_RESPONSE | jq '.'
echo ""

if [ "$PROD_STATUS" == "pending_approval" ]; then
    echo -e "${GREEN}✅ Production deployment plan created (pending approval)${NC}"
    echo "Plan ID: $PROD_PLAN_ID"
    echo ""
    
    # Show pending approvals
    echo -e "${BLUE}Checking pending approvals...${NC}"
    curl -s "$API_BASE/approvals" | jq '.pending_approvals[] | {plan_id, created_at}'
    echo ""
    
    # Approve the plan
    echo -e "${BLUE}Step 4: Approving production deployment...${NC}"
    APPROVAL_RESPONSE=$(curl -s -X POST "$API_BASE/approve" \
        -H "Content-Type: application/json" \
        -d "{
            \"plan_id\": \"$PROD_PLAN_ID\",
            \"approver\": \"bob@example.com\",
            \"decision\": \"approved\"
        }")
    
    echo "Approval response:"
    echo $APPROVAL_RESPONSE | jq '.'
    echo ""
    
    if echo $APPROVAL_RESPONSE | jq -e '.status == "approved"' > /dev/null; then
        echo -e "${GREEN}✅ Production deployment approved and started${NC}"
        
        # Wait and check status
        echo "Waiting 3 seconds and checking deployment status..."
        sleep 3
        curl -s "$API_BASE/plan/$PROD_PLAN_ID" | jq '.plan | {plan_id, status, artifact: .artifact.model_name}'
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Unexpected status: $PROD_STATUS${NC}"
fi

echo ""
echo -e "${BLUE}Step 5: Demonstrating rollback simulation...${NC}"
echo "In a real deployment, Model Monitor would detect issues and trigger alarms."
echo "SageMaker AutoRollbackConfiguration would automatically rollback the deployment."
echo ""
echo "For demo purposes, this is simulated. In production:"
echo "  - CloudWatch alarms would trigger based on Model Monitor metrics"
echo "  - AutoRollbackConfiguration would revert to previous endpoint version"
echo "  - Audit log would record the rollback event"
echo ""

echo -e "${GREEN}✅ Demo completed successfully!${NC}"
echo ""
echo "Summary:"
echo "  - Staging deployment: Automatic (no approval)"
echo "  - Production deployment: Required approval and was approved"
echo "  - All actions logged to DynamoDB audit log"
echo ""
echo "Next steps:"
echo "  1. View approval UI: http://localhost:8000/approvals-ui"
echo "  2. Check audit logs in DynamoDB table: agentops-audit-log"
echo "  3. Review deployment plans: GET $API_BASE/plan/{plan_id}"

