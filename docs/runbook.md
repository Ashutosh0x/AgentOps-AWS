# AgentOps Runbook

## Startup Procedures

### 1. Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd agentops-aws

# Setup development environment
bash scripts/setup_dev.sh

# Configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials and endpoint names
```

### 2. Deploy Infrastructure (First Time)

```bash
cd deploy/terraform
terraform init
terraform plan  # Review changes
terraform apply
```

**Outputs to note:**
- DynamoDB table name
- S3 bucket name (CloudTrail logs)
- SageMaker role ARN

### 3. Deploy NVIDIA NIMs

**Via SageMaker JumpStart:**
1. Open AWS Console → SageMaker → JumpStart
2. Search for "llama-3.1-nemotron-nano-8B-v1"
3. Click "Deploy" → Choose instance type → Create endpoint
4. Note endpoint name
5. Repeat for NeMo Retriever Embedding and Reranking NIMs

**Via AWS Marketplace:**
1. Subscribe to NVIDIA NIM microservices
2. Deploy via SageMaker console
3. Note endpoint names

### 4. Upload Policy Documents

```bash
python scripts/upload_docs.py
```

This populates the retriever with policy documents for RAG.

### 5. Start Orchestrator

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start orchestrator
uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000

# Or using Make
make dev
```

**Verify:**
```bash
curl http://localhost:8000/
# Should return: {"service": "AgentOps Orchestrator", ...}
```

## Daily Operations

### Starting the System

1. **Check AWS Credentials**
   ```bash
   aws sts get-caller-identity
   ```

2. **Verify SageMaker Endpoints**
   ```bash
   aws sagemaker list-endpoints --query 'Endpoints[?contains(EndpointName, `llama`) || contains(EndpointName, `nemo`)].EndpointName'
   ```

3. **Start Orchestrator**
   ```bash
   make dev
   ```

### Stopping the System

1. **Stop Orchestrator**
   - Press `Ctrl+C` in orchestrator terminal
   - Or: `pkill -f "uvicorn orchestrator.main"`

2. **Optional: Stop SageMaker Endpoints** (to save costs
   ```bash
   # List endpoints
   aws sagemaker list-endpoints --output table
   
   # Stop endpoint (if needed)
   aws sagemaker delete-endpoint --endpoint-name <endpoint-name>
   ```

## Monitoring

### Health Checks

```bash
# Check orchestrator status
curl http://localhost:8000/

# Check pending approvals
curl http://localhost:8000/approvals | jq

# Check plan status
curl http://localhost:8000/plan/<plan-id> | jq
```

### Logs

**Orchestrator logs:**
- Console output (stdout/stderr)
- Application logs via Python logging

**AWS Service logs:**
- SageMaker: CloudWatch Logs
- DynamoDB: CloudTrail Data Events → S3

### Metrics

**Key Metrics to Monitor:**
- Number of deployment plans generated
- Approval rate (approved vs rejected)
- Deployment success rate
- Average deployment time
- Budget utilization

**CloudWatch Metrics:**
- SageMaker endpoint invocations
- DynamoDB read/write capacity
- S3 storage (CloudTrail logs)

## Cost Management

### Monitoring Costs

1. **AWS Cost Explorer**
   - Filter by service: SageMaker, DynamoDB, S3
   - Set up cost alerts at 80% of budget

2. **Daily Cost Check**
   ```bash
   # Approximate hourly costs
   # LLM NIM: ~$11/hour (ml.g5.12xlarge)
   # Retriever NIMs: ~$X/hour (check pricing)
   # DynamoDB: Pay-per-request (minimal)
   # S3: Storage + requests (minimal)
   ```

### Cost Optimization Tips

1. **Use Dry-Run Mode**
   - Default: `EXECUTE=false`
   - Only set `EXECUTE=true` for actual deployments

2. **Shutdown Endpoints**
   - Stop SageMaker endpoints when not testing
   - Use smaller instance types for development

3. **Monitor DynamoDB**
   - Use on-demand billing (pay-per-request)
   - Clean up old audit logs periodically

4. **S3 Lifecycle Policies**
   - Archive old CloudTrail logs to Glacier
   - Delete logs after retention period

### Budget Alerts

Set up CloudWatch Billing Alerts:
```bash
# AWS Console → Billing → Budgets
# Create budget alert at $80, $90, $100
```

## Troubleshooting

### Orchestrator Won't Start

**Symptom:** `uvicorn` command fails or crashes

**Diagnosis:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip list | grep -E "fastapi|uvicorn|boto3"

# Check environment variables
cat .env
```

**Solutions:**
1. Reinstall dependencies: `pip install -r requirements.txt`
2. Check `.env` file exists and is valid
3. Verify AWS credentials: `aws sts get-caller-identity`

### LLM Endpoint Not Found

**Symptom:** `ValueError: LLM_ENDPOINT environment variable or endpoint_name must be provided`

**Diagnosis:**
```bash
# Check endpoint exists
aws sagemaker describe-endpoint --endpoint-name <your-endpoint-name>

# Check environment variable
echo $LLM_ENDPOINT
```

**Solutions:**
1. Verify endpoint name in `.env` matches actual endpoint name
2. Check endpoint status: `aws sagemaker list-endpoints`
3. System will use mock mode if endpoint not configured (for testing)

### DynamoDB Table Not Found

**Symptom:** `ClientError: ResourceNotFoundException`

**Diagnosis:**
```bash
# Check table exists
aws dynamodb describe-table --table-name agentops-audit-log
```

**Solutions:**
1. Create table manually:
   ```bash
   aws dynamodb create-table \
     --table-name agentops-audit-log \
     --attribute-definitions AttributeName=plan_id,AttributeType=S AttributeName=timestamp,AttributeType=S \
     --key-schema AttributeName=plan_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
     --billing-mode PAY_PER_REQUEST
   ```
2. Or use Terraform: `cd deploy/terraform && terraform apply`

### Approval Not Working

**Symptom:** Production deployment doesn't require approval

**Diagnosis:**
```bash
# Check environment in request
curl -X POST http://localhost:8000/intent -H "Content-Type: application/json" -d '{"user_id":"test","intent":"test","env":"prod"}' | jq
```

**Solutions:**
1. Verify `env` field is `"prod"` (case-sensitive)
2. Check guardrail logic in `orchestrator/guardrail.py`
3. Review logs for approval decision

### Deployment Fails

**Symptom:** Deployment status = "failed"

**Diagnosis:**
```bash
# Check plan status
curl http://localhost:8000/plan/<plan-id> | jq '.plan.status'

# Check logs for errors
# Review orchestrator console output
```

**Solutions:**
1. Verify SageMaker permissions:
   ```bash
   aws iam get-role --role-name SageMakerExecutionRole
   ```
2. Check instance type availability in region
3. Verify model artifacts S3 bucket exists
4. Review CloudWatch Logs for SageMaker errors

### Dry-Run Not Working

**Symptom:** Actual deployments happening when EXECUTE=false

**Diagnosis:**
```bash
# Check environment variable
echo $EXECUTE

# Check .env file
grep EXECUTE .env
```

**Solutions:**
1. Verify `EXECUTE=false` in `.env`
2. Restart orchestrator after changing `.env`
3. Check logs for `[DRY-RUN]` messages

## Maintenance

### Weekly Tasks

1. **Review Audit Logs**
   ```bash
   aws dynamodb scan --table-name agentops-audit-log --limit 10
   ```

2. **Check CloudTrail Logs**
   ```bash
   # CloudTrail logs in S3 bucket
   aws s3 ls s3://agentops-cloudtrail-logs-<suffix>/
   ```

3. **Review Costs**
   - Check AWS Cost Explorer
   - Review SageMaker endpoint usage
   - Verify budget alerts working

### Monthly Tasks

1. **Clean Up Old Logs**
   - Archive DynamoDB items older than 90 days
   - Move CloudTrail logs to Glacier (if configured)

2. **Update Policy Documents**
   - Review and update `orchestrator/demo_data/sample_policy.md`
   - Re-upload: `python scripts/upload_docs.py`

3. **Security Review**
   - Review IAM permissions
   - Check CloudTrail for unauthorized access
   - Verify Object Lock on S3 bucket

## Emergency Procedures

### Critical Deployment Issue

1. **Stop Deployment**
   - Cancel pending approvals via UI or API
   - Manually delete SageMaker endpoints if needed

2. **Rollback**
   - SageMaker AutoRollbackConfiguration should handle automatically
   - If not, manually update endpoint to previous version

3. **Investigate**
   - Review CloudWatch alarms
   - Check Model Monitor metrics
   - Review audit logs for decision chain

### Service Outage

1. **Check Orchestrator Health**
   ```bash
   curl http://localhost:8000/
   ```

2. **Check AWS Service Health**
   - AWS Status Dashboard
   - SageMaker service status

3. **Restart Orchestrator**
   ```bash
   pkill -f "uvicorn orchestrator.main"
   make dev
   ```

### Data Loss Prevention

1. **Backup Audit Logs**
   - DynamoDB: Export to S3 periodically
   - CloudTrail: Already in S3 with Object Lock

2. **Verify Object Lock**
   ```bash
   aws s3api get-object-lock-configuration --bucket <cloudtrail-bucket>
   ```

## Support and Escalation

### Self-Service Resources

- Documentation: `docs/`
- Code repository: GitHub
- AWS Documentation: SageMaker, DynamoDB, CloudTrail

### When to Escalate

- Critical production outage
- Data integrity concerns
- Security incident
- Budget exceeded unexpectedly

---

**Last Updated:** 2024  
**Version:** 1.0.0

