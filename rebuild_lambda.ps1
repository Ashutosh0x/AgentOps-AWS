# Rebuild Lambda deployment package with proper Linux dependencies
# Uses pip with --platform flag to get Linux-compatible wheels

$ErrorActionPreference = "Stop"

Write-Host "Rebuilding Lambda package for Linux..." -ForegroundColor Green

# Clean previous builds
if (Test-Path "lambda-package") {
    Remove-Item "lambda-package" -Recurse -Force
}
if (Test-Path "agentops-lambda.zip") {
    Remove-Item "agentops-lambda.zip" -Force
}

# Create package directory
New-Item -ItemType Directory -Path "lambda-package" | Out-Null

Write-Host "Installing dependencies for Linux (manylinux1_x86_64)..." -ForegroundColor Yellow

# Install dependencies targeting Linux platform
pip install `
    --platform manylinux1_x86_64 `
    --target lambda-package `
    --implementation cp `
    --python-version 3.11 `
    --only-binary=:all: `
    --upgrade `
    fastapi==0.109.0 `
    uvicorn[standard]==0.27.0 `
    pydantic==2.5.3 `
    mangum==0.17.0 `
    boto3==1.34.34 `
    httpx==0.26.0 `
    python-dotenv==1.0.1 `
    --quiet

Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Path "orchestrator" -Destination "lambda-package/orchestrator" -Recurse
Copy-Item -Path "lambda_handler.py" -Destination "lambda-package/"

Write-Host "Creating zip package..." -ForegroundColor Yellow
Compress-Archive -Path lambda-package/* -DestinationPath agentops-lambda.zip -Force

$size = (Get-Item agentops-lambda.zip).Length / 1MB
Write-Host "Package created: agentops-lambda.zip ($([math]::Round($size, 2)) MB)" -ForegroundColor Green

Write-Host ""
Write-Host "Updating Lambda function..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name agentops-orchestrator `
    --zip-file fileb://agentops-lambda.zip `
    --region us-east-1 `
    --output json | ConvertFrom-Json | Select-Object FunctionName, LastUpdateStatus, State

Write-Host ""
Write-Host "Waiting for update to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Done! Testing the function..." -ForegroundColor Green

