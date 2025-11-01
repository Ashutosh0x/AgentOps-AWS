#!/bin/bash
# Development environment setup script for AgentOps

set -e

echo "🚀 Setting up AgentOps development environment..."

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [[ $(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1) != "$required_version" ]]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please update it with your AWS credentials and endpoint names."
    else
        echo "⚠️  .env.example not found. Creating basic .env file..."
        cat > .env << EOF
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# SageMaker Endpoints
LLM_ENDPOINT=your-llm-endpoint-name
RETRIEVER_EMBED_ENDPOINT=your-embed-endpoint-name
RETRIEVER_RERANK_ENDPOINT=your-rerank-endpoint-name

# DynamoDB
DYNAMODB_TABLE_NAME=agentops-audit-log

# Execution Mode (set to "true" to enable actual deployments)
EXECUTE=false

# SageMaker Execution Role
SAGEMAKER_ROLE_NAME=SageMakerExecutionRole
EOF
        echo "✅ Created basic .env file. Please update it with your configuration."
    fi
fi

# Run upload_docs script to initialize retriever
echo "Uploading sample policy documents..."
python scripts/upload_docs.py

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your AWS credentials and endpoint names"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Start the orchestrator: python -m orchestrator.main"
echo "4. Or use: uvicorn orchestrator.main:app --reload"

