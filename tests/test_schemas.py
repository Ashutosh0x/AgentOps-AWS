"""Unit tests for Pydantic schemas and validation."""

import pytest
from pydantic import ValidationError

from orchestrator.models import (
    SageMakerDeploymentConfig,
    UserIntentRequest,
    Environment,
    PlanStatus,
    ApprovalState
)
from orchestrator.guardrail import GuardrailService


class TestSageMakerDeploymentConfig:
    """Test SageMakerDeploymentConfig schema validation."""
    
    def test_valid_config(self):
        """Test valid configuration."""
        config = SageMakerDeploymentConfig(
            model_name="test-model",
            endpoint_name="test-endpoint",
            instance_type="ml.m5.large",
            instance_count=2,
            budget_usd_per_hour=15.0
        )
        
        assert config.model_name == "test-model"
        assert config.instance_count == 2
    
    def test_instance_count_boundary_min(self):
        """Test minimum instance_count boundary."""
        # Valid: instance_count = 1
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            instance_count=1
        )
        assert config.instance_count == 1
        
        # Invalid: instance_count = 0
        with pytest.raises(ValidationError):
            SageMakerDeploymentConfig(
                model_name="test",
                endpoint_name="test",
                instance_type="ml.m5.large",
                instance_count=0
            )
    
    def test_instance_count_boundary_max(self):
        """Test maximum instance_count boundary."""
        # Valid: instance_count = 4
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            instance_count=4
        )
        assert config.instance_count == 4
        
        # Invalid: instance_count = 5
        with pytest.raises(ValidationError):
            SageMakerDeploymentConfig(
                model_name="test",
                endpoint_name="test",
                instance_type="ml.m5.large",
                instance_count=5
            )
    
    def test_budget_validation(self):
        """Test budget validation."""
        # Valid: positive budget
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            budget_usd_per_hour=10.0
        )
        assert config.budget_usd_per_hour == 10.0
        
        # Invalid: zero budget
        with pytest.raises(ValidationError):
            SageMakerDeploymentConfig(
                model_name="test",
                endpoint_name="test",
                instance_type="ml.m5.large",
                budget_usd_per_hour=0.0
            )
        
        # Invalid: negative budget
        with pytest.raises(ValidationError):
            SageMakerDeploymentConfig(
                model_name="test",
                endpoint_name="test",
                instance_type="ml.m5.large",
                budget_usd_per_hour=-5.0
            )
    
    def test_max_payload_boundary(self):
        """Test max_payload_mb boundary."""
        # Valid: max_payload_mb = 1024
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            max_payload_mb=1024
        )
        assert config.max_payload_mb == 1024
        
        # Invalid: max_payload_mb = 0
        with pytest.raises(ValidationError):
            SageMakerDeploymentConfig(
                model_name="test",
                endpoint_name="test",
                instance_type="ml.m5.large",
                max_payload_mb=0
            )


class TestGuardrailValidation:
    """Test guardrail service validation."""
    
    def test_dev_instance_type_validation(self):
        """Test dev environment instance type requirement."""
        guardrail = GuardrailService()
        
        # Valid: ml.m5.large for dev
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            instance_count=1
        )
        result = guardrail.validate_plan(config, Environment.DEV)
        assert result.valid
        
        # Invalid: wrong instance type for dev
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.g5.12xlarge",
            instance_count=1
        )
        result = guardrail.validate_plan(config, Environment.DEV)
        assert not result.valid
        assert any("required_instance_type" in err.lower() for err in result.errors)
    
    def test_prod_ha_requirement(self):
        """Test production HA requirement (instance_count >= 2)."""
        guardrail = GuardrailService()
        
        # Invalid: instance_count = 1 for prod
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.g5.12xlarge",
            instance_count=1
        )
        result = guardrail.validate_plan(config, Environment.PROD)
        assert not result.valid
        assert any("minimum" in err.lower() and "2" in err for err in result.errors)
        
        # Valid: instance_count = 2 for prod
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.g5.12xlarge",
            instance_count=2
        )
        result = guardrail.validate_plan(config, Environment.PROD)
        assert result.valid
    
    def test_budget_validation(self):
        """Test budget validation."""
        guardrail = GuardrailService()
        
        # Valid: within staging budget
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            instance_count=1,
            budget_usd_per_hour=10.0
        )
        result = guardrail.validate_plan(config, Environment.STAGING)
        assert result.valid
        
        # Invalid: exceeds staging budget
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.g5.12xlarge",
            instance_count=2,
            budget_usd_per_hour=50.0
        )
        result = guardrail.validate_plan(config, Environment.STAGING)
        assert not result.valid
        assert any("budget" in err.lower() for err in result.errors)
    
    def test_user_constraint_budget(self):
        """Test user-provided budget constraint."""
        guardrail = GuardrailService()
        
        config = SageMakerDeploymentConfig(
            model_name="test",
            endpoint_name="test",
            instance_type="ml.m5.large",
            instance_count=1,
            budget_usd_per_hour=20.0
        )
        
        # Valid: within user constraint
        result = guardrail.validate_plan(
            config,
            Environment.STAGING,
            user_constraints={"budget_usd_per_hour": 15.0}
        )
        # Should have warning but be valid (estimated cost ~$0.115 < $15)
        assert result.valid
        
        # Invalid: exceeds user constraint
        result = guardrail.validate_plan(
            config,
            Environment.PROD,
            user_constraints={"budget_usd_per_hour": 5.0}
        )
        assert not result.valid
        assert any("user constraint" in err.lower() for err in result.errors)

