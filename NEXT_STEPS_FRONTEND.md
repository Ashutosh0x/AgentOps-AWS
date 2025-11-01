# Next Steps: Frontend Deployment & Backend Update

## ✅ Completed

1. **Frontend Built Successfully**
   - ✅ Dependencies installed
   - ✅ Production build completed (dist/ folder created)
   - ✅ All TypeScript compilation passed

2. **Backend Code Ready**
   - ✅ New services created: `cost_service.py`, `deployment_status.py`
   - ✅ New API endpoints added to `orchestrator/main.py`
   - ✅ Code is ready but **NOT yet deployed to Lambda**

## 🔄 Next Steps Required

### 1. Redeploy Lambda Function (Required)

The new backend services need to be deployed to AWS Lambda. Run:

```powershell
.\deploy_lambda.ps1
```

This will:
- Rebuild the Lambda package with new services
- Update the Lambda function code
- Keep existing Function URL and configuration

**Note**: The new endpoints (`/api/metrics/*`, `/api/deployments`, `/api/agent/command`) will only work after redeployment.

### 2. Configure Frontend Environment

Create `.env` file in `frontend/` directory:

```powershell
cd frontend
Copy-Item .env.example .env
# Edit .env and set VITE_API_URL to your Lambda Function URL
```

Get your Lambda Function URL:
```powershell
aws lambda get-function-url-config --function-name agentops-orchestrator --query FunctionUrl --output text
```

### 3. Test Frontend Locally (Optional)

```powershell
cd frontend
npm run dev
```

Then open `http://localhost:5173` in browser to test locally.

### 4. Deploy Frontend Infrastructure (First Time Only)

If you haven't already, provision the S3 + CloudFront infrastructure:

```powershell
cd deploy\terraform
terraform init
terraform plan
terraform apply
```

Save the outputs:
- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_url`

### 5. Deploy Frontend to S3 + CloudFront

```powershell
$env:FRONTEND_BUCKET_NAME="agentops-frontend-xxxxx"  # From terraform output
$env:CLOUDFRONT_DIST_ID="E1234567890"                # From terraform output
.\deploy\frontend_deploy.ps1
```

### 6. Access Dashboard

Open the CloudFront URL in browser:
```
https://your-cloudfront-domain.cloudfront.net
```

Or get it from Terraform:
```powershell
terraform output cloudfront_url
```

## Quick Start (Minimal)

If you just want to test quickly:

1. **Redeploy Lambda** (to include new endpoints):
   ```powershell
   .\deploy_lambda.ps1
   ```

2. **Test Frontend Locally**:
   ```powershell
   cd frontend
   # Create .env with your Lambda Function URL
   npm run dev
   ```

3. **Open** `http://localhost:5173` and verify:
   - KPI cards show data
   - Deployment table is visible
   - Command bar works

## Verification Checklist

After deployment, verify:

- [ ] Lambda function updated (check logs for new endpoints)
- [ ] `/api/metrics/deployments/active` endpoint returns data
- [ ] `/api/metrics/approvals/pending` endpoint returns data
- [ ] `/api/metrics/costs/monthly` endpoint returns data (may be mock if Cost Explorer not configured)
- [ ] `/api/deployments` endpoint returns deployment list
- [ ] `/api/agent/command` endpoint processes commands
- [ ] Frontend loads without errors
- [ ] KPI cards display values
- [ ] Deployment table shows data
- [ ] Command bar can submit commands

## Troubleshooting

### Frontend shows "No deployments"
- Check that you've submitted some intents via `/intent` endpoint
- Verify `/api/deployments` endpoint returns data

### API calls fail with CORS errors
- Lambda Function URL CORS is already configured (`allow_origins=["*"]`)
- Verify the `VITE_API_URL` in `.env` is correct

### Cost metrics show mock data
- This is expected if AWS Cost Explorer permissions aren't configured
- The service will return realistic mock data for demo purposes
- To enable real data, grant `ce:GetCostAndUsage` permission to Lambda role

### Build errors
- Make sure `npm install` completed successfully
- Check that Node.js version is 18+ (run `node --version`)

## Files Modified for Backend

These files need to be in the Lambda package:
- ✅ `orchestrator/main.py` (updated with new endpoints)
- ✅ `orchestrator/cost_service.py` (new)
- ✅ `orchestrator/deployment_status.py` (new)

The `deploy_lambda.ps1` script will automatically include these when rebuilding.

---

**Status**: Frontend ready, backend code ready, needs Lambda redeployment to activate new endpoints.

