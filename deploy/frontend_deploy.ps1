# PowerShell script to deploy frontend to S3 + CloudFront

param(
    [string]$BucketName = $env:FRONTEND_BUCKET_NAME,
    [string]$DistributionId = $env:CLOUDFRONT_DIST_ID,
    [string]$Region = $env:AWS_REGION
)

if (-not $BucketName) {
    Write-Host "Error: FRONTEND_BUCKET_NAME environment variable not set" -ForegroundColor Red
    exit 1
}

if (-not $Region) {
    $Region = "us-east-1"
}

Write-Host "Building frontend..." -ForegroundColor Blue
Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Blue
    npm install
}

Write-Host "Building production bundle..." -ForegroundColor Blue
npm run build

if (-not (Test-Path "dist")) {
    Write-Host "Error: dist directory not found after build" -ForegroundColor Red
    exit 1
}

Write-Host "Syncing to S3 bucket: $BucketName..." -ForegroundColor Blue
aws s3 sync dist/ "s3://$BucketName/" --delete --region $Region

if ($DistributionId) {
    Write-Host "Invalidating CloudFront cache..." -ForegroundColor Blue
    aws cloudfront create-invalidation `
        --distribution-id $DistributionId `
        --paths "/*" `
        --region $Region
    
    Write-Host "✓ Frontend deployed and cache invalidated" -ForegroundColor Green
} else {
    Write-Host "✓ Frontend deployed to S3" -ForegroundColor Green
    Write-Host "Note: Set CLOUDFRONT_DIST_ID environment variable to invalidate CloudFront cache" -ForegroundColor Yellow
}

Write-Host "Deployment complete!" -ForegroundColor Green
Set-Location ..

