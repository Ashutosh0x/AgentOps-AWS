# Simple PowerShell deployment script for AgentOps
# Deploys to AWS Lambda with Function URL

$REGION = "us-east-1"
$FUNCTION_NAME = "agentops-orchestrator"
$ROLE_NAME = "agentops-lambda-role"

Write-Host "🚀 Deploying AgentOps to AWS Lambda..." -ForegroundColor Green
Write-Host ""

# Check if Lambda function exists
Write-Host "📋 Checking Lambda function..." -ForegroundColor Cyan
$functionExists = aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating IAM role..." -ForegroundColor Yellow
    
    # Create IAM role
    $roleArn = aws iam create-role `
        --role-name $ROLE_NAME `
        --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' `
        --query 'Role.Arn' `
        --output text
    
    Write-Host "Role ARN: $roleArn" -ForegroundColor Green
    
    # Attach policies
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
    
    Write-Host "Waiting for role to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

Write-Host ""
Write-Host "✅ Ready! Next steps:" -ForegroundColor Green
Write-Host "1. Create deployment package (zip file with code)"
Write-Host "2. Deploy to Lambda using AWS CLI or Console"
Write-Host ""
Write-Host "For a simpler approach, let's deploy using AWS App Runner with source code." -ForegroundColor Yellow

