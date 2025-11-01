# 🚀 AgentOps - Next Steps & Status

## ✅ What's Working

1. **Lambda Function Deployed**
   - Function: `agentops-orchestrator`
   - URL: `https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/`
   - Status: ✅ Running and responding

2. **API Endpoints Working**
   - ✅ `GET /` - Health check
   - ✅ `POST /intent` - Submit deployment intent
   - ✅ `GET /approvals` - List pending approvals
   - ✅ Production deployments require approval (HITL working)

3. **Infrastructure**
   - ✅ DynamoDB table: `agentops-audit-log` (active)
   - ✅ IAM role: `agentops-lambda-role` (with permissions)
   - ✅ ECR repository: `agentops-orchestrator` (ready)

4. **Features**
   - ✅ Lazy service initialization (Lambda compatible)
   - ✅ Mock LLM/Retriever when endpoints not configured
   - ✅ Guardrail validation working
   - ✅ HITL approval flow working
   - ✅ Dry-run mode (default)

## 📋 Next Steps

### 1. Deploy NVIDIA NIMs (Required for Full Functionality)

**Option A: Via AWS Console (Easiest)**
1. Go to AWS Console → SageMaker → JumpStart
2. Search for "llama-3.1-nemotron-nano-8B-v1"
3. Click "Deploy" → Select instance type (ml.g5.12xlarge recommended)
4. Note the endpoint name
5. Repeat for:
   - NeMo Retriever Embedding NIM
   - NeMo Retriever Reranking NIM

**Option B: Via AWS CLI**
```bash
# List available models
aws sagemaker list-model-packages \
  --query 'ModelPackageSummaryList[?contains(ModelPackageName, `nvidia`) || contains(ModelPackageName, `llama`) || contains(ModelPackageName, `nemo`)].ModelPackageName' \
  --output table

# Deploy via SageMaker SDK or Console
```

**Update Lambda Environment Variables:**
```bash
aws lambda update-function-configuration \
  --function-name agentops-orchestrator \
  --environment "Variables={DYNAMODB_TABLE_NAME=agentops-audit-log,EXECUTE=false,LLM_ENDPOINT=your-llm-endpoint-name,RETRIEVER_EMBED_ENDPOINT=your-embed-endpoint,RETRIEVER_RERANK_ENDPOINT=your-rerank-endpoint}" \
  --region us-east-1
```

### 2. Upload Policy Documents

The retriever needs policy documents for RAG. Currently using mock mode.

**Option A: Via Script (when endpoints ready)**
```bash
python scripts/upload_docs.py
```

**Option B: Manual Upload**
- Policy documents are in `orchestrator/demo_data/sample_policy.md`
- Will be ingested when NeMo Retriever endpoints are configured

### 3. Test End-to-End Flow

**Staging Deployment (Auto):**
```bash
curl -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/intent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice@example.com",
    "intent": "deploy llama-3.1 8B for chatbot-x",
    "env": "staging",
    "constraints": {"budget_usd_per_hour": 15.0}
  }'
```

**Production Deployment (Requires Approval):**
```bash
curl -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/intent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice@example.com",
    "intent": "deploy llama-3.1 8B for chatbot-x",
    "env": "prod",
    "constraints": {"budget_usd_per_hour": 50.0}
  }'
```

**Approve Production Deployment:**
```bash
curl -X POST https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/approve \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "your-plan-id",
    "approver": "bob@example.com",
    "decision": "approved"
  }'
```

### 4. Enable Actual Deployments (When Ready)

Currently in dry-run mode. To enable actual SageMaker deployments:

```bash
aws lambda update-function-configuration \
  --function-name agentops-orchestrator \
  --environment "Variables={DYNAMODB_TABLE_NAME=agentops-audit-log,EXECUTE=true,LLM_ENDPOINT=your-endpoint,RETRIEVER_EMBED_ENDPOINT=your-endpoint,RETRIEVER_RERANK_ENDPOINT=your-endpoint}" \
  --region us-east-1
```

⚠️ **Warning**: Only enable `EXECUTE=true` when ready. This will create actual SageMaker resources.

### 5. Set Up CloudTrail (Optional)

For immutable audit logging:

```bash
# Create S3 bucket for CloudTrail
aws s3 mb s3://agentops-cloudtrail-logs-$(aws sts get-caller-identity --query Account --output text) --region us-east-1

# Enable Object Lock
aws s3api put-object-lock-configuration \
  --bucket agentops-cloudtrail-logs-<account-id> \
  --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"GOVERNANCE","Days":90}}}'

# Create CloudTrail trail
aws cloudtrail create-trail \
  --name agentops-audit-trail \
  --s3-bucket-name agentops-cloudtrail-logs-<account-id> \
  --region us-east-1

# Enable data events for DynamoDB
aws cloudtrail put-event-selectors \
  --trail-name agentops-audit-trail \
  --event-selectors '[{
    "ReadWriteType": "WriteOnly",
    "IncludeManagementEvents": false,
    "DataResources": [{
      "Type": "AWS::DynamoDB::Table",
      "Values": ["arn:aws:dynamodb:us-east-1:690695877653:table/agentops-audit-log"]
    }]
  }]' \
  --region us-east-1
```

### 6. Monitor & Optimize

**View CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/agentops-orchestrator --follow --region us-east-1
```

**Check DynamoDB Audit Logs:**
```bash
aws dynamodb scan --table-name agentops-audit-log --limit 10 --region us-east-1
```

**Monitor Costs:**
- Check AWS Cost Explorer
- Monitor SageMaker endpoint costs
- Set up billing alerts

## 🎯 Demo Script

Update `demo/demo.sh` with the Lambda Function URL:

```bash
# In demo/demo.sh, change:
API_BASE="http://localhost:8000"

# To:
API_BASE="https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws"
```

Then run:
```bash
bash demo/demo.sh
```

## 📊 Current Limitations

1. **State Storage**: Using in-memory stores (doesn't persist across Lambda invocations)
   - Solution: Move to DynamoDB or Redis

2. **Background Tasks**: Lambda doesn't support true background tasks
   - Solution: Use Step Functions or EventBridge for async workflows

3. **Pydantic v1**: Using v1 instead of v2 (for Lambda compatibility)
   - Solution: Build dependencies in Docker for v2 compatibility

## 🔧 Troubleshooting

**Function not responding:**
```bash
aws lambda get-function --function-name agentops-orchestrator --region us-east-1
aws logs tail /aws/lambda/agentops-orchestrator --since 5m --region us-east-1
```

**Update code:**
```bash
# Rebuild package
./deploy_lambda.ps1

# Or manually:
pip install -r requirements.txt -t lambda-package/
cp -r orchestrator lambda-package/
cp lambda_handler.py lambda-package/
zip -r agentops-lambda.zip lambda-package/
aws lambda update-function-code --function-name agentops-orchestrator --zip-file fileb://agentops-lambda.zip
```

## ✅ Checklist for Hackathon Submission

- [x] Lambda function deployed and working
- [x] API endpoints functional
- [x] HITL approval flow working
- [x] Guardrail validation working
- [ ] NVIDIA NIMs deployed (optional - can demo with mocks)
- [ ] Demo video recorded
- [ ] README updated with Lambda URL
- [ ] Repository finalized

---

**Function URL**: `https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/`

**Status**: ✅ Ready for demo (can use mock mode for NIMs)

