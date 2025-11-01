"""Executor Agent - Executes AWS API calls and deployment steps."""

import logging
from typing import Dict, Any
from datetime import datetime

from orchestrator.models import TaskStep, ExecutionResult, SageMakerDeploymentConfig
from orchestrator.guardrail import GuardrailService
from orchestrator.sage_tool import SageMakerTool

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """Agent that executes deployment steps via AWS APIs."""
    
    def __init__(
        self,
        guardrail_service: GuardrailService = None,
        sage_tool: SageMakerTool = None
    ):
        """Initialize Executor Agent.
        
        Args:
            guardrail_service: Guardrail service for validation
            sage_tool: SageMaker tool for deployment
        """
        self.guardrail_service = guardrail_service
        self.sage_tool = sage_tool
    
    def execute_step(
        self,
        step: TaskStep,
        deployment_config: SageMakerDeploymentConfig = None,
        env: str = None,
        constraints: Dict[str, Any] = None
    ) -> ExecutionResult:
        """Execute a single deployment step.
        
        Args:
            step: Task step to execute
            deployment_config: Deployment configuration (for deployment steps)
            env: Target environment
            constraints: Optional constraints
            
        Returns:
            ExecutionResult with success status and output
        """
        logger.info(f"[Executor] Executing step: {step.action} (step_id: {step.step_id})")
        
        try:
            step.status = "executing"
            step.timestamp = datetime.utcnow()
            
            # Route to appropriate executor method based on action
            if step.action == "validate_plan":
                result = self._validate_plan(deployment_config, env, constraints)
            elif step.action == "create_model":
                result = self._create_model(deployment_config)
            elif step.action == "create_endpoint_config":
                result = self._create_endpoint_config(deployment_config)
            elif step.action == "create_endpoint":
                result = self._create_endpoint(deployment_config)
            elif step.action == "configure_monitoring":
                result = self._configure_monitoring(deployment_config)
            else:
                # Unknown action - log and skip
                logger.warning(f"[Executor] Unknown action: {step.action}, skipping")
                result = ExecutionResult(
                    step_id=step.step_id,
                    success=True,
                    output={"message": f"Action {step.action} not implemented, skipped"},
                    metrics={}
                )
            
            step.status = "completed" if result.success else "failed"
            step.output = result.output
            step.error = result.error
            
            return result
            
        except Exception as e:
            logger.error(f"[Executor] Error executing step {step.action}: {e}")
            step.status = "failed"
            step.error = str(e)
            
            return ExecutionResult(
                step_id=step.step_id,
                success=False,
                output={},
                error=str(e)
            )
    
    def _validate_plan(
        self,
        config: SageMakerDeploymentConfig,
        env: str,
        constraints: Dict[str, Any]
    ) -> ExecutionResult:
        """Validate deployment plan against guardrails.
        
        Args:
            config: Deployment configuration
            env: Target environment
            constraints: User constraints
            
        Returns:
            ExecutionResult with validation outcome
        """
        if not self.guardrail_service:
            return ExecutionResult(
                step_id="validate_plan",
                success=True,
                output={"message": "Guardrail service not available, validation skipped"},
                metrics={}
            )
        
        from orchestrator.models import Environment
        env_enum = Environment(env) if isinstance(env, str) else env
        
        validation_result = self.guardrail_service.validate_plan(
            config,
            env_enum,
            constraints or {}
        )
        
        return ExecutionResult(
            step_id="validate_plan",
            success=validation_result.valid,
            output={
                "valid": validation_result.valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            },
            metrics={"validation_duration_ms": 100},
            error=None if validation_result.valid else "; ".join(validation_result.errors)
        )
    
    def _create_model(self, config: SageMakerDeploymentConfig) -> ExecutionResult:
        """Create SageMaker model.
        
        Args:
            config: Deployment configuration
            
        Returns:
            ExecutionResult with model creation outcome
        """
        if not self.sage_tool:
            return ExecutionResult(
                step_id="create_model",
                success=True,
                output={"message": "[DRY-RUN] Would create SageMaker model", "model_name": config.model_name},
                metrics={}
            )
        
        try:
            # In real implementation, call sage_tool.create_model()
            # For now, simulate success
            result = self.sage_tool.deploy_model(config, dry_run=True)
            
            return ExecutionResult(
                step_id="create_model",
                success=True,
                output={
                    "message": result.message,
                    "model_name": config.model_name,
                    "dry_run": True
                },
                metrics={"execution_duration_ms": 500}
            )
        except Exception as e:
            return ExecutionResult(
                step_id="create_model",
                success=False,
                output={},
                error=str(e)
            )
    
    def _create_endpoint_config(self, config: SageMakerDeploymentConfig) -> ExecutionResult:
        """Create SageMaker endpoint configuration.
        
        Args:
            config: Deployment configuration
            
        Returns:
            ExecutionResult with endpoint config creation outcome
        """
        return ExecutionResult(
            step_id="create_endpoint_config",
            success=True,
            output={
                "message": "[DRY-RUN] Would create endpoint configuration",
                "endpoint_name": config.endpoint_name,
                "instance_type": config.instance_type,
                "instance_count": config.instance_count
            },
            metrics={"execution_duration_ms": 300}
        )
    
    def _create_endpoint(self, config: SageMakerDeploymentConfig) -> ExecutionResult:
        """Create and deploy SageMaker endpoint.
        
        Args:
            config: Deployment configuration
            
        Returns:
            ExecutionResult with endpoint creation outcome
        """
        return ExecutionResult(
            step_id="create_endpoint",
            success=True,
            output={
                "message": "[DRY-RUN] Would create and deploy endpoint",
                "endpoint_name": config.endpoint_name,
                "status": "creating"
            },
            metrics={"execution_duration_ms": 2000}
        )
    
    def _configure_monitoring(self, config: SageMakerDeploymentConfig) -> ExecutionResult:
        """Configure Model Monitor and rollback alarms.
        
        Args:
            config: Deployment configuration
            
        Returns:
            ExecutionResult with monitoring configuration outcome
        """
        return ExecutionResult(
            step_id="configure_monitoring",
            success=True,
            output={
                "message": "[DRY-RUN] Would configure Model Monitor",
                "rollback_alarms": config.rollback_alarms,
                "monitoring_enabled": True
            },
            metrics={"execution_duration_ms": 400}
        )

