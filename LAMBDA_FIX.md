# Lambda Deployment Issue - Pydantic Dependencies

## Problem
The Lambda function fails with: `No module named 'pydantic_core._pydantic_core'`

This happens because Pydantic 2.x has compiled C extensions that need to be built for Linux (Lambda's runtime environment), but we're building on Windows.

## Solutions

### Option 1: Use Docker to Build (Recommended)

Build the deployment package in a Docker container that matches Lambda's Linux environment:

```bash
# Use AWS Lambda Python base image
docker run --rm -v ${PWD}:/var/task \
    public.ecr.aws/lambda/python:3.11 \
    /bin/sh -c "pip install -r requirements.txt -t lambda-package/ && zip -r agentops-lambda.zip lambda-package/"

# Or use a Linux container
docker run --rm -v ${PWD}:/app -w /app \
    python:3.11-slim \
    bash -c "pip install -r requirements.txt -t lambda-package/ && zip -r agentops-lambda.zip lambda-package/"
```

Then update Lambda:
```bash
aws lambda update-function-code \
    --function-name agentops-orchestrator \
    --zip-file fileb://agentops-lambda.zip \
    --region us-east-1
```

### Option 2: Use AWS App Runner (Easier)

AWS App Runner handles container building automatically. This is the recommended approach.

### Option 3: Use Pydantic v1 (Temporary Fix)

Downgrade to Pydantic v1 which has fewer compiled dependencies:

```powershell
# In requirements.txt, change:
# pydantic==2.5.3
# to:
# pydantic==1.10.13

# Then rebuild
pip install -r requirements.txt -t lambda-package/
```

### Option 4: Use Lambda Layers

Create a Lambda Layer with Pydantic and other dependencies, then reference it in the function.

## Quick Test with Mock

For now, the function URL is accessible but has the dependency issue. Once fixed, test with:

```bash
curl https://7ovf2ipaywdvgp7j3r7d6mk5ca0cvfic.lambda-url.us-east-1.on.aws/
```

