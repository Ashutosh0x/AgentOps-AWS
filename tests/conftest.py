"""Pytest configuration and fixtures."""

import os
import pytest
from unittest.mock import Mock, MagicMock

# Set environment variables for testing
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "test-audit-log")
os.environ.setdefault("EXECUTE", "false")


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    from orchestrator.models import SageMakerDeploymentConfig
    
    mock = MagicMock()
    mock.generate_plan.return_value = SageMakerDeploymentConfig(
        model_name="test-model",
        endpoint_name="test-endpoint",
        instance_type="ml.m5.large",
        instance_count=1,
        budget_usd_per_hour=10.0
    )
    return mock


@pytest.fixture
def mock_retriever_client():
    """Mock retriever client."""
    from orchestrator.models import RAGEvidence
    
    mock = MagicMock()
    mock.query.return_value = [
        RAGEvidence(
            title="Test Policy",
            snippet="Development models must use ml.m5.large",
            url="test://policy",
            score=0.9
        )
    ]
    return mock


@pytest.fixture
def mock_sage_tool():
    """Mock SageMaker tool."""
    from orchestrator.models import DeploymentResult
    from datetime import datetime
    
    mock = MagicMock()
    mock.deploy_model.return_value = DeploymentResult(
        plan_id="test-plan",
        success=True,
        endpoint_name="test-endpoint",
        model_name="test-model",
        message="Deployment successful",
        dry_run=True,
        timestamp=datetime.utcnow()
    )
    return mock


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger."""
    mock = MagicMock()
    mock.log_intent = MagicMock(return_value=None)
    mock.log_approval = MagicMock(return_value=None)
    mock.log_deployment = MagicMock(return_value=None)
    return mock

