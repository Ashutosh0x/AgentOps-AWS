"""Integration tests for orchestrator flow."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from orchestrator.models import (
    UserIntentRequest,
    Environment,
    PlanStatus,
    ApprovalState
)


@pytest.mark.asyncio
async def test_staging_deployment_flow():
    """Test end-to-end staging deployment flow (no approval)."""
    from orchestrator.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Mock services
    with patch("orchestrator.main.llm_client") as mock_llm, \
         patch("orchestrator.main.retriever_client") as mock_retriever, \
         patch("orchestrator.main.guardrail_service") as mock_guardrail, \
         patch("orchestrator.main.sage_tool") as mock_sage, \
         patch("orchestrator.main.audit_logger") as mock_audit:
        
        from orchestrator.models import SageMakerDeploymentConfig, ValidationResult, RAGEvidence
        
        # Setup mocks
        mock_retriever.query.return_value = [
            RAGEvidence(title="Policy", snippet="Dev uses ml.m5.large", score=0.9)
        ]
        
        mock_llm.generate_plan.return_value = SageMakerDeploymentConfig(
            model_name="test-model",
            endpoint_name="test-endpoint-staging",
            instance_type="ml.m5.large",
            instance_count=1,
            budget_usd_per_hour=10.0
        )
        
        mock_guardrail.validate_plan.return_value = ValidationResult(
            valid=True,
            errors=[],
            warnings=[]
        )
        
        mock_guardrail.requires_approval.return_value = False
        
        mock_sage.deploy_model.return_value = MagicMock(
            success=True,
            endpoint_name="test-endpoint-staging",
            dry_run=True
        )
        
        mock_audit.log_intent = AsyncMock()
        
        # Submit intent
        request = {
            "user_id": "test@example.com",
            "intent": "deploy llama-3.1 8B for chatbot-x",
            "env": "staging",
            "constraints": {"budget_usd_per_hour": 15.0}
        }
        
        response = client.post("/intent", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "plan_id" in data
        assert data["status"] == "deploying"  # No approval needed
        assert "artifact" in data


@pytest.mark.asyncio
async def test_prod_deployment_approval_flow():
    """Test production deployment flow with approval."""
    from orchestrator.main import app, plans_store, approvals_store
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Mock services
    with patch("orchestrator.main.llm_client") as mock_llm, \
         patch("orchestrator.main.retriever_client") as mock_retriever, \
         patch("orchestrator.main.guardrail_service") as mock_guardrail, \
         patch("orchestrator.main.audit_logger") as mock_audit:
        
        from orchestrator.models import SageMakerDeploymentConfig, ValidationResult, RAGEvidence
        
        # Setup mocks
        mock_retriever.query.return_value = [
            RAGEvidence(title="Policy", snippet="Prod needs HA", score=0.9)
        ]
        
        mock_llm.generate_plan.return_value = SageMakerDeploymentConfig(
            model_name="test-model",
            endpoint_name="test-endpoint-prod",
            instance_type="ml.g5.12xlarge",
            instance_count=2,
            budget_usd_per_hour=50.0
        )
        
        mock_guardrail.validate_plan.return_value = ValidationResult(
            valid=True,
            errors=[],
            warnings=[]
        )
        
        mock_guardrail.requires_approval.return_value = True  # Prod requires approval
        
        mock_audit.log_intent = AsyncMock()
        mock_audit.log_approval = AsyncMock()
        
        # Submit prod intent
        request = {
            "user_id": "test@example.com",
            "intent": "deploy llama-3.1 8B for chatbot-x",
            "env": "prod",
            "constraints": {"budget_usd_per_hour": 50.0}
        }
        
        response = client.post("/intent", json=request)
        
        assert response.status_code == 200
        data = response.json()
        plan_id = data["plan_id"]
        assert data["status"] == "pending_approval"
        assert data["requires_approval"] is True
        
        # Check approval request exists
        assert plan_id in approvals_store
        
        # Approve the plan
        approval_request = {
            "plan_id": plan_id,
            "approver": "admin@example.com",
            "decision": "approved"
        }
        
        response = client.post("/approve", json=approval_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        
        # Check plan status updated
        assert plans_store[plan_id].status == PlanStatus.DEPLOYING


@pytest.mark.asyncio
async def test_validation_failure_flow():
    """Test flow when guardrail validation fails."""
    from orchestrator.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    with patch("orchestrator.main.retriever_client") as mock_retriever, \
         patch("orchestrator.main.llm_client") as mock_llm, \
         patch("orchestrator.main.guardrail_service") as mock_guardrail, \
         patch("orchestrator.main.audit_logger") as mock_audit:
        
        from orchestrator.models import SageMakerDeploymentConfig, ValidationResult, RAGEvidence
        
        mock_retriever.query.return_value = [RAGEvidence(title="Policy", snippet="Test", score=0.9)]
        
        mock_llm.generate_plan.return_value = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.g5.12xlarge",
            instance_count=1,
            budget_usd_per_hour=100.0
        )
        
        # Validation fails
        mock_guardrail.validate_plan.return_value = ValidationResult(
            valid=False,
            errors=["Budget exceeds limit", "Instance type not allowed"],
            warnings=[]
        )
        
        mock_audit.log_intent = AsyncMock()
        
        request = {
            "user_id": "test@example.com",
            "intent": "deploy model",
            "env": "dev",
            "constraints": {}
        }
        
        response = client.post("/intent", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validation_failed"
        assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_get_plan_endpoint():
    """Test GET /plan/{plan_id} endpoint."""
    from orchestrator.main import app, plans_store
    from fastapi.testclient import TestClient
    from orchestrator.models import DeploymentPlan, SageMakerDeploymentConfig, PlanStatus
    
    client = TestClient(app)
    
    # Create a test plan
    test_plan = DeploymentPlan(
        plan_id="test-plan-123",
        status=PlanStatus.PENDING_APPROVAL,
        user_id="test@example.com",
        intent="test intent",
        env=Environment.STAGING,
        artifact=SageMakerDeploymentConfig(
            model_name="test-model",
            endpoint_name="test-endpoint",
            instance_type="ml.m5.large",
            instance_count=1
        )
    )
    
    plans_store["test-plan-123"] = test_plan
    
    response = client.get("/plan/test-plan-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["plan_id"] == "test-plan-123"
    assert data["plan"]["status"] == "pending_approval"
    
    # Test non-existent plan
    response = client.get("/plan/non-existent")
    assert response.status_code == 404

