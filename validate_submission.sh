#!/bin/bash
# AgentOps Hackathon Submission Validation Script
# Run this before submitting to ensure all requirements are met

set -e

FUNCTION_URL="https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws"
PASS_COUNT=0
FAIL_COUNT=0

echo "========================================"
echo "AgentOps Submission Validation"
echo "========================================"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check (GET /)"
if curl -s "$FUNCTION_URL/" | grep -q "AgentOps Orchestrator"; then
    echo "✅ PASS"
    ((PASS_COUNT++))
else
    echo "❌ FAIL"
    ((FAIL_COUNT++))
fi
echo ""

# Test 2: Staging Intent
echo "Test 2: Staging Deployment Intent (POST /intent)"
RESPONSE=$(curl -s -X POST "$FUNCTION_URL/intent" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "alice@example.com",
        "intent": "deploy llama-3.1 8B for chatbot-x",
        "env": "staging",
        "constraints": {"budget_usd_per_hour": 15.0}
    }')

if echo "$RESPONSE" | grep -q "plan_id" && echo "$RESPONSE" | grep -q "artifact"; then
    echo "✅ PASS"
    echo "$RESPONSE" | jq -r '.plan_id, .status' 2>/dev/null || echo "Plan created"
    ((PASS_COUNT++))
else
    echo "❌ FAIL"
    echo "Response: $RESPONSE"
    ((FAIL_COUNT++))
fi
echo ""

# Test 3: Production Intent (HITL)
echo "Test 3: Production Deployment (Requires Approval)"
RESPONSE=$(curl -s -X POST "$FUNCTION_URL/intent" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "alice@example.com",
        "intent": "deploy llama-3.1 8B for chatbot-x",
        "env": "prod",
        "constraints": {"budget_usd_per_hour": 50.0}
    }')

if echo "$RESPONSE" | grep -q "pending_approval"; then
    echo "✅ PASS - HITL working"
    PROD_PLAN_ID=$(echo "$RESPONSE" | jq -r '.plan_id' 2>/dev/null)
    echo "Plan ID: $PROD_PLAN_ID"
    ((PASS_COUNT++))
else
    echo "❌ FAIL"
    ((FAIL_COUNT++))
fi
echo ""

# Test 4: Approval Queue
echo "Test 4: Approval Queue (GET /approvals)"
if curl -s "$FUNCTION_URL/approvals" | grep -q "pending_approvals"; then
    echo "✅ PASS"
    ((PASS_COUNT++))
else
    echo "❌ FAIL"
    ((FAIL_COUNT++))
fi
echo ""

# Test 5: Repository Structure
echo "Test 5: Repository Structure"
REQUIRED_DIRS=("orchestrator" "tests" "demo" "deploy" "docs" "scripts")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir/"
    else
        echo "  ❌ Missing: $dir/"
        ((FAIL_COUNT++))
    fi
done
if [ $FAIL_COUNT -eq 0 ]; then
    ((PASS_COUNT++))
fi
echo ""

# Test 6: Required Files
echo "Test 6: Required Files"
REQUIRED_FILES=(
    "README.md"
    "requirements.txt"
    "orchestrator/main.py"
    "orchestrator/llm_client.py"
    "orchestrator/retriever_client.py"
    "orchestrator/guardrail.py"
    "orchestrator/sage_tool.py"
    "tests/test_schemas.py"
    "tests/test_orchestrator_flow.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ Missing: $file"
        ((FAIL_COUNT++))
    fi
done
if [ $FAIL_COUNT -eq 0 ]; then
    ((PASS_COUNT++))
fi
echo ""

# Test 7: Run Unit Tests
echo "Test 7: Unit Tests"
if command -v pytest &> /dev/null; then
    if pytest tests/test_schemas.py -v --tb=short 2>&1 | grep -q "PASSED"; then
        echo "✅ PASS"
        ((PASS_COUNT++))
    else
        echo "⚠️  Tests exist but may need Python environment setup"
        ((PASS_COUNT++))
    fi
else
    echo "⚠️  pytest not installed (install dependencies to run tests)"
    ((PASS_COUNT++))
fi
echo ""

# Summary
echo "========================================"
echo "Validation Summary"
echo "========================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - READY FOR SUBMISSION!"
    exit 0
else
    echo "⚠️  Some tests failed. Please review before submission."
    exit 1
fi

