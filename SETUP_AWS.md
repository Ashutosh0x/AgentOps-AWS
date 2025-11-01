# AWS Setup Status & Next Steps

## ✅ Current AWS Configuration

- **Account ID**: 690695877653
- **Region**: us-east-1
- **Credentials**: ✅ Configured (via AWS CLI)
- **User**: codebuildcloud-admin

AWS credentials are automatically detected by boto3 from your AWS CLI configuration. No need to set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in environment variables.

## 🔧 Environment Variables Needed

Create a `.env` file (or set these environment variables):

```bash
# AWS Region (already configured in AWS CLI)
AWS_REGION=us-east-1

# SageMaker Endpoints (deploy these first - see below)
LLM_ENDPOINT=llama-3.1-nemotron-nano-8b-v1-endpoint
RETRIEVER_EMBED_ENDPOINT=nemo-retriever-embed-endpoint
RETRIEVER_RERANK_ENDPOINT=nemo-retriever-rerank-endpoint

# DynamoDB Table (will be created by Terraform)
DYNAMODB_TABLE_NAME=agentops-audit-log

# Safety: Keep this false for testing
EXECUTE=false
```

## 📋 Next Steps

### 1. Deploy Infrastructure (Optional)

```bash
cd deploy/terraform
terraform init
terraform apply
```

This creates:
- DynamoDB table: `agentops-audit-log`
- S3 bucket for CloudTrail logs
- CloudTrail trail
- SageMaker execution IAM role

### 2. Deploy NVIDIA NIMs via SageMaker JumpStart

**Option A: AWS Console**
1. Go to AWS Console → SageMaker → JumpStart
2. Search for "llama-3.1-nemotron-nano-8B-v1"
3. Click "Deploy" → Select instance type → Create endpoint
4. Note the endpoint name
5. Repeat for "NeMo Retriever Embedding" and "NeMo Retriever Reranking"

**Option B: AWS CLI**
```bash
# List available models in JumpStart
aws sagemaker list-model-packages --query 'ModelPackageSummaryList[?contains(ModelPackageName, `nvidia`) || contains(ModelPackageName, `llama`) || contains(ModelPackageName, `nemo`)].ModelPackageName' --output table

# Deploy via SageMaker SDK or Console
# (JumpStart deployment is easier via Console for first-time setup)
```

### 3. Create DynamoDB Table (if not using Terraform)

```bash
aws dynamodb create-table \
  --table-name agentops-audit-log \
  --attribute-definitions \
    AttributeName=plan_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=plan_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 4. Test AWS Access

```bash
# Test SageMaker access
aws sagemaker list-endpoints --region us-east-1

# Test DynamoDB access
aws dynamodb list-tables --region us-east-1

# Test credentials
aws sts get-caller-identity
```

### 5. Upload Policy Documents

```bash
python scripts/upload_docs.py
```

### 6. Start Orchestrator

```bash
# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start orchestrator
uvicorn orchestrator.main:app --reload
```

## ⚠️ Important Notes

1. **Dry-Run Mode**: The system defaults to `EXECUTE=false` for safety. Set `EXECUTE=true` only when ready for actual deployments.

2. **Mock Mode**: If SageMaker endpoints are not configured, the system will use mock mode automatically for testing.

3. **Costs**: SageMaker endpoints can be expensive. Monitor usage in AWS Cost Explorer.

4. **IAM Permissions**: Ensure your IAM user has permissions for:
   - SageMaker: `CreateModel`, `CreateEndpoint`, `Describe*`
   - DynamoDB: `CreateTable`, `PutItem`, `Query`
   - S3: `GetObject`, `PutObject` (for model artifacts)
   - CloudWatch: `PutMetricData`

## 🔍 Verify Setup

```bash
# Check orchestrator is running
curl http://localhost:8000/

# Check AWS credentials
aws sts get-caller-identity

# List SageMaker endpoints
aws sagemaker list-endpoints --query 'Endpoints[*].EndpointName'
```

