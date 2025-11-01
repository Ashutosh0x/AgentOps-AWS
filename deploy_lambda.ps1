# Deploy AgentOps to AWS Lambda - PowerShell Script
# This script creates a Lambda deployment package and deploys

$ErrorActionPreference = "Stop"

$REGION = "us-east-1"
$FUNCTION_NAME = "agentops-orchestrator"
$ROLE_NAME = "agentops-lambda-role"
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

Write-Host "Deploying AgentOps to AWS Lambda..." -ForegroundColor Green
Write-Host "Account: $ACCOUNT_ID" -ForegroundColor Cyan
Write-Host "Region: $REGION" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create IAM role if it doesn't exist
Write-Host "Setting up IAM role..." -ForegroundColor Yellow
try {
    $null = aws iam get-role --role-name $ROLE_NAME 2>&1 | Out-Null
    $roleExists = $true
} catch {
    $roleExists = $false
}

if (-not $roleExists -or $LASTEXITCODE -ne 0) {
    Write-Host "Creating IAM role: $ROLE_NAME" -ForegroundColor Yellow
    
    $roleArn = aws iam create-role `
        --role-name $ROLE_NAME `
        --assume-role-policy-document file://lambda-role-policy.json `
        --query 'Role.Arn' `
        --output text
    
    Write-Host "Role created: $roleArn" -ForegroundColor Green
    
    # Attach policies
    Write-Host "Attaching policies..." -ForegroundColor Yellow
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole | Out-Null
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess | Out-Null
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess | Out-Null
    
    Write-Host "Waiting for role to propagate..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
} else {
    $roleArn = aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text
    Write-Host "Role exists: $roleArn" -ForegroundColor Green
}

# Step 2: Create deployment package
Write-Host ""
Write-Host "Creating deployment package..." -ForegroundColor Yellow

# Clean previous builds
if (Test-Path "agentops-lambda.zip") {
    Remove-Item "agentops-lambda.zip" -Force
}
if (Test-Path "lambda-package") {
    Remove-Item "lambda-package" -Recurse -Force
}

# Create package directory
New-Item -ItemType Directory -Path "lambda-package" | Out-Null

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -t lambda-package/ --quiet

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Path "orchestrator" -Destination "lambda-package/orchestrator" -Recurse
Copy-Item -Path "lambda_handler.py" -Destination "lambda-package/"

# Create zip file
Write-Host "Creating zip package..." -ForegroundColor Yellow
Compress-Archive -Path lambda-package/* -DestinationPath agentops-lambda.zip -Force

$zipSize = (Get-Item agentops-lambda.zip).Length / 1MB
Write-Host "Package created: agentops-lambda.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green

# Step 3: Deploy to Lambda
Write-Host ""
Write-Host "Deploying to Lambda..." -ForegroundColor Yellow

$envVars = @{
    AWS_REGION = $REGION
    DYNAMODB_TABLE_NAME = "agentops-audit-log"
    EXECUTE = "false"
} | ConvertTo-Json -Compress

$functionExists = aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    # Create function
    Write-Host "Creating Lambda function..." -ForegroundColor Yellow
    aws lambda create-function `
        --function-name $FUNCTION_NAME `
        --runtime python3.11 `
        --role $roleArn `
        --handler lambda_handler.handler `
        --zip-file fileb://agentops-lambda.zip `
        --timeout 900 `
        --memory-size 1024 `
        --environment Variables=$envVars `
        --region $REGION `
        --output json | ConvertFrom-Json | Select-Object FunctionName, FunctionArn, Runtime
    
    Write-Host "Lambda function created!" -ForegroundColor Green
} else {
    # Update function code
    Write-Host "Updating Lambda function code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name $FUNCTION_NAME `
        --zip-file fileb://agentops-lambda.zip `
        --region $REGION | Out-Null
    
    aws lambda update-function-configuration `
        --function-name $FUNCTION_NAME `
        --environment Variables=$envVars `
        --region $REGION | Out-Null
    
    Write-Host "Lambda function updated!" -ForegroundColor Green
}

# Step 4: Create Function URL
Write-Host ""
Write-Host "Creating Function URL..." -ForegroundColor Yellow

$urlExists = aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $REGION 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    $urlConfig = aws lambda create-function-url-config `
        --function-name $FUNCTION_NAME `
        --auth-type NONE `
        --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' `
        --region $REGION `
        --output json | ConvertFrom-Json
    
    $functionUrl = $urlConfig.FunctionUrl
    Write-Host "Function URL created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Deployment complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Function URL: $functionUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Test it:" -ForegroundColor Yellow
    Write-Host "  curl $functionUrl" -ForegroundColor White
} else {
    $functionUrl = aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $REGION --query FunctionUrl --output text
    Write-Host "Function URL already exists!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Function URL: $functionUrl" -ForegroundColor Cyan
}

# Cleanup
Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item "lambda-package" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Done!" -ForegroundColor Green

