# Deploy AgentOps to AWS - Step by Step

## Current Status

✅ **DynamoDB Table**: Created and active (`agentops-audit-log`)
✅ **ECR Repository**: Created (`agentops-orchestrator`)
✅ **AWS Credentials**: Configured and working
✅ **Docker**: Available (but Docker Desktop may need to be started)

## Deployment Options

### Option 1: AWS App Runner (Recommended - Simplest)

AWS App Runner can deploy directly from source code or container image.

**Steps:**

1. **Start Docker Desktop** (if using container deployment)

2. **Build and push Docker image:**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 690695877653.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t agentops-orchestrator:latest .

# Tag and push
docker tag agentops-orchestrator:latest 690695877653.dkr.ecr.us-east-1.amazonaws.com/agentops-orchestrator:latest
docker push 690695877653.dkr.ecr.us-east-1.amazonaws.com/agentops-orchestrator:latest
```

3. **Create App Runner service:**
```bash
aws apprunner create-service --cli-input-json file://apprunner-config.json
```

**Or use AWS Console:**
- Go to AWS App Runner → Create service
- Choose "Container image"
- Select ECR image: `690695877653.dkr.ecr.us-east-1.amazonaws.com/agentops-orchestrator:latest`
- Configure: 1 vCPU, 2 GB memory
- Set environment variables:
  - `AWS_REGION=us-east-1`
  - `DYNAMODB_TABLE_NAME=agentops-audit-log`
  - `EXECUTE=false`

### Option 2: AWS Lambda (Alternative)

For Lambda deployment, we need to create a deployment package.

**Steps:**

1. **Create IAM role:**
```bash
aws iam create-role --role-name agentops-lambda-role --assume-role-policy-document file://lambda-role-policy.json
aws iam attach-role-policy --role-name agentops-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name agentops-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name agentops-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

2. **Create deployment package:**
```powershell
# Install dependencies
pip install -r requirements.txt -t ./package

# Copy code
Copy-Item -Path orchestrator -Destination package\orchestrator -Recurse
Copy-Item lambda_handler.py package\

# Create zip
Compress-Archive -Path package\* -DestinationPath agentops-lambda.zip
```

3. **Deploy to Lambda:**
```bash
aws lambda create-function \
    --function-name agentops-orchestrator \
    --runtime python3.11 \
    --role arn:aws:iam::690695877653:role/agentops-lambda-role \
    --handler lambda_handler.handler \
    --zip-file fileb://agentops-lambda.zip \
    --timeout 900 \
    --memory-size 1024 \
    --environment Variables="{AWS_REGION=us-east-1,DYNAMODB_TABLE_NAME=agentops-audit-log,EXECUTE=false}"
```

4. **Create Function URL:**
```bash
aws lambda create-function-url-config \
    --function-name agentops-orchestrator \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}'
```

### Option 3: EC2 Instance (Traditional)

Deploy to EC2 instance for more control.

**Steps:**

1. **Launch EC2 instance:**
```bash
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.medium \
    --key-name your-key-name \
    --security-group-ids sg-xxxxxxxxx \
    --user-data file://ec2-userdata.sh
```

2. **SSH into instance and deploy:**
```bash
git clone <repo-url>
cd agentops-aws
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000
```

## Quick Deploy Commands

### Using AWS CLI (App Runner)

```bash
# 1. Ensure Docker Desktop is running
# 2. Build and push
docker build -t agentops-orchestrator:latest .
docker tag agentops-orchestrator:latest 690695877653.dkr.ecr.us-east-1.amazonaws.com/agentops-orchestrator:latest
docker push 690695877653.dkr.ecr.us-east-1.amazonaws.com/agentops-orchestrator:latest

# 3. Deploy to App Runner
aws apprunner create-service --cli-input-json file://apprunner-config.json
```

### Using AWS Console (Easiest)

1. Go to **AWS App Runner** → Create service
2. Select **Container image** → ECR → Select repository
3. Choose image: `agentops-orchestrator:latest`
4. Service name: `agentops-orchestrator`
5. Instance: 1 vCPU, 2 GB
6. Environment variables:
   - `AWS_REGION=us-east-1`
   - `DYNAMODB_TABLE_NAME=agentops-audit-log`
   - `EXECUTE=false`
7. Create and deploy

## Verify Deployment

After deployment, test the endpoint:

```bash
# App Runner
curl https://<service-url>/

# Lambda Function URL
curl https://<function-url>/
```

## Next Steps After Deployment

1. **Deploy NVIDIA NIMs** via SageMaker JumpStart
2. **Update environment variables** with endpoint names
3. **Test the API** endpoints
4. **Run demo script** pointing to deployed URL

## Troubleshooting

- **Docker not running**: Start Docker Desktop, then retry
- **ECR push fails**: Ensure you're logged in: `aws ecr get-login-password | docker login`
- **Lambda timeout**: Increase timeout (max 15 minutes)
- **Permission errors**: Check IAM roles and policies

