# Frontend Deployment Guide

## Overview

The AgentOps dashboard is a React application that needs to be deployed to AWS S3 and served via CloudFront. The frontend communicates with the Lambda backend API.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed (for infrastructure provisioning)
3. Node.js and npm installed
4. Frontend bucket and CloudFront distribution created (via Terraform)

## Step 1: Provision Infrastructure

```bash
cd deploy/terraform
terraform init
terraform plan
terraform apply
```

This will create:
- S3 bucket for frontend static files
- CloudFront distribution
- Origin Access Control (OAC)

After applying, note the outputs:
- `frontend_bucket_name`: S3 bucket name
- `cloudfront_distribution_id`: CloudFront distribution ID
- `cloudfront_url`: CloudFront URL (e.g., `https://d1234567890.cloudfront.net`)

## Step 2: Configure Backend CORS

The Lambda function URL already has CORS configured to allow all origins (`allow_origins=["*"]`). However, for production, you may want to restrict this to your CloudFront domain.

Update `orchestrator/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-cloudfront-domain.cloudfront.net",
        "http://localhost:5173",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then redeploy the Lambda function.

## Step 3: Configure Frontend Environment

1. Create `.env` file in `frontend/` directory:

```bash
cd frontend
cp .env.example .env
```

2. Edit `.env` and set your Lambda Function URL:

```
VITE_API_URL=https://your-lambda-function-url.lambda-url.us-east-1.on.aws
```

## Step 4: Build and Deploy Frontend

### Option A: Using PowerShell (Windows)

```powershell
$env:FRONTEND_BUCKET_NAME="agentops-frontend-xxxxxxxx"
$env:CLOUDFRONT_DIST_ID="E1234567890ABC"
$env:AWS_REGION="us-east-1"

.\deploy\frontend_deploy.ps1
```

### Option B: Using Bash (Linux/Mac)

```bash
export FRONTEND_BUCKET_NAME="agentops-frontend-xxxxxxxx"
export CLOUDFRONT_DIST_ID="E1234567890ABC"
export AWS_REGION="us-east-1"

./deploy/frontend_deploy.sh
```

### Option C: Manual Deployment

```bash
cd frontend
npm install
npm run build
aws s3 sync dist/ s3://your-bucket-name/ --delete
aws cloudfront create-invalidation --distribution-id E1234567890ABC --paths "/*"
```

## Step 5: Access the Dashboard

Once deployed, access the dashboard via the CloudFront URL:

```
https://your-cloudfront-domain.cloudfront.net
```

## Local Development

To run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:5173` (or another port if 5173 is in use).

Make sure your `.env` file points to your Lambda Function URL for API calls.

## Troubleshooting

### CORS Errors

If you see CORS errors:
1. Check that the Lambda Function URL CORS policy allows your CloudFront domain
2. Verify the `VITE_API_URL` in `.env` matches your Lambda Function URL
3. Check browser console for specific error messages

### 404 Errors on Page Refresh

CloudFront is configured with custom error responses to serve `index.html` for 404/403 errors, enabling SPA routing. If you still see 404s:
1. Verify the CloudFront distribution has the custom error pages configured
2. Check that `default_root_object` is set to `index.html` in Terraform

### Cache Issues

If changes aren't appearing:
1. Invalidate CloudFront cache: `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`
2. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)

### API Connection Issues

1. Verify `VITE_API_URL` in `.env` is correct
2. Check that the Lambda Function URL is publicly accessible
3. Verify Lambda function has a Function URL configured with public access
4. Check browser Network tab for actual API requests and responses

## Cost Considerations

- S3 storage: ~$0.023 per GB/month (minimal for static files)
- CloudFront: 
  - Data transfer: $0.085 per GB (first 10 TB/month)
  - Requests: $0.0075 per 10,000 HTTPS requests
- Lambda: Already covered in backend deployment

For a hackathon demo, costs should be minimal (< $1/month for low traffic).

