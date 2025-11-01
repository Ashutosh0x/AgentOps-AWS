# Judge Validation Guide - AgentOps Submission

This guide provides quick validation steps for hackathon judges to verify the AgentOps submission meets all requirements.

## Quick Start (5 minutes)

### 1. Test Live Deployment (No Setup Required)

**Function URL**: `https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/`

```bash
# Health Check
curl https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/

# Expected: {"service":"AgentOps Orchestrator","version":"1.0.0","status":"running"}
```

```bash
# Staging Deployment (Auto)
curl -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/intent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "judge@example.com",
    "intent": "deploy llama-3.1 8B for chatbot-x",
    "env": "staging",
    "constraints": {"budget_usd_per_hour": 15.0}
  }'

# Expected: {"plan_id": "...", "status": "deploying", "artifact": {...}}
```

```bash
# Production Deployment (Requires Approval)
curl -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/intent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "judge@example.com",
    "intent": "deploy llama-3.1 8B for chatbot-x",
    "env": "prod",
    "constraints": {"budget_usd_per_hour": 50.0}
  }'

# Expected: {"plan_id": "...", "status": "pending_approval", "requires_approval": true}
```

### 2. Check Approval Queue

```bash
curl https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/approvals

# Expected: {"pending_approvals": [...], "count": 1}
```

### 3. Review Repository Structure

```bash
git clone <repo-url>
cd agentops-aws
ls -la
```

**Expected folders**:
- ✅ `orchestrator/` - Main code
- ✅ `tests/` - Test suite
- ✅ `demo/` - Demo scripts
- ✅ `deploy/terraform/` - Infrastructure code
- ✅ `docs/` - Documentation

## Requirement Verification

### ✅ Requirement 1: NVIDIA NIMs Usage

**Check**:
1. Open `orchestrator/llm_client.py`
   - Should have `LLMClient` class with SageMaker Runtime integration
   - Uses `LLM_ENDPOINT` environment variable
   
2. Open `orchestrator/retriever_client.py`
   - Should have `RetrieverClient` class
   - Two-stage pipeline: `embed_query()` → `retrieve_docs()` → `rerank()`
   - Uses `RETRIEVER_EMBED_ENDPOINT` and `RETRIEVER_RERANK_ENDPOINT`

3. Check CloudWatch logs (if AWS access available):
   ```bash
   aws logs tail /aws/lambda/agentops-orchestrator --since 1h
   ```
   - Should show: "LLM_ENDPOINT not set, using mock LLM client" (mock mode documented)

**Evidence**: ✅ Code implements NIM integration, mock mode when endpoints not configured

### ✅ Requirement 2: Agentic Behavior (Plan + Execute)

**Check**:
1. POST `/intent` returns structured plan:
   ```json
   {
     "plan_id": "uuid",
     "status": "deploying",
     "artifact": {
       "model_name": "...",
       "endpoint_name": "...",
       "instance_type": "ml.m5.large",
       "instance_count": 1,
       "budget_usd_per_hour": 15.0
     }
   }
   ```

2. Check `orchestrator/sage_tool.py`:
   - Has `deploy_model()` method
   - Creates Model, EndpointConfig, Endpoint
   - Configures AutoRollbackConfiguration

**Evidence**: ✅ Agent generates structured plan and executes (dry-run or real)

### ✅ Requirement 3: Safety-First Design

**Layer 1: Guardrails**
- Check `orchestrator/guardrail.py`
- Run test: Intent with `instance_count: 10` → should fail validation

**Layer 2: HITL**
- Production intent → status: "pending_approval"
- GET `/approvals` → lists pending
- POST `/approve` → approves and proceeds

**Layer 3: Audit**
- Check DynamoDB: `aws dynamodb scan --table-name agentops-audit-log`
- Check Terraform: `deploy/terraform/main.tf` has CloudTrail config

**Evidence**: ✅ Three-layer safety implemented

### ✅ Requirement 4: Reproducibility

**Check README.md**:
- Quickstart section
- Environment variables documented
- Setup script: `scripts/setup_dev.sh`

**Run setup**:
```bash
bash scripts/setup_dev.sh
# Should install dependencies and create .env file
```

**Evidence**: ✅ Clear setup instructions provided

### ✅ Requirement 5: Tests

```bash
pytest tests/test_schemas.py -v
pytest tests/test_orchestrator_flow.py -v
```

**Expected**: All tests pass

## Sample Expected Outputs

### Staging Deployment Response
```json
{
  "plan_id": "a3442a54-cd41-4007-8bee-4b0416f74ff8",
  "status": "deploying",
  "artifact": {
    "model_name": "llama-3.1-8b-staging",
    "endpoint_name": "chatbot-x-staging",
    "instance_type": "ml.m5.large",
    "instance_count": 1,
    "max_payload_mb": 6,
    "autoscaling_min": 1,
    "autoscaling_max": 2,
    "rollback_alarms": [],
    "budget_usd_per_hour": 15.0
  },
  "evidence": [],
  "warnings": [],
  "requires_approval": false
}
```

### Production Approval Flow
```json
// POST /intent with "env": "prod"
{
  "plan_id": "739b32d8-20dd-4cf5-b170-de728ef14af5",
  "status": "pending_approval",
  "requires_approval": true,
  "artifact": {...}
}

// GET /approvals
{
  "pending_approvals": [
    {
      "plan_id": "739b32d8-20dd-4cf5-b170-de728ef14af5",
      "plan": {...}
    }
  ],
  "count": 1
}

// POST /approve
{
  "plan_id": "739b32d8-20dd-4cf5-b170-de728ef14af5",
  "status": "approved",
  "message": "Deployment started"
}
```

### Guardrail Validation Error
```json
{
  "status": "validation_failed",
  "errors": [
    "instance_count must be between 1 and 4, got 10",
    "Estimated cost $25.00/hour exceeds environment max budget $15.00/hour"
  ]
}
```

## Scoring Rubric Quick Reference

| Criteria | Points | How to Verify |
|----------|--------|---------------|
| NIM Usage | 20 | Check `llm_client.py` and `retriever_client.py` |
| Agentic Behavior | 20 | POST `/intent` returns structured plan |
| Safety (Guardrails) | 15 | Test invalid input → validation errors |
| Safety (HITL) | 15 | Prod intent → requires approval |
| Safety (Audit) | 10 | DynamoDB has audit entries |
| Reproducibility | 10 | README has clear setup instructions |
| Tests | 5 | `pytest tests/` passes |
| Polish | 5 | Demo video, documentation quality |

**Total**: 100 points

## Pass/Fail Quick Test

Run this 30-second test:

```bash
# All should return 200 OK or valid JSON
curl -s https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/ | jq .
curl -s https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/approvals | jq .
curl -s -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/intent \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","intent":"test","env":"staging"}' | jq .plan_id
```

**All pass?** → System is operational ✅

---

**Function URL**: `https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/`  
**Status**: ✅ Ready for Evaluation

