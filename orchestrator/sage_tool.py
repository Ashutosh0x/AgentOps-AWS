"""SageMaker deployment tool for executing validated deployment plans."""

import os
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from orchestrator.models import SageMakerDeploymentConfig, DeploymentResult

logger = logging.getLogger(__name__)


class SageMakerTool:
    """Tool for deploying models to SageMaker."""

    def __init__(self, region: str = None, dry_run: bool = None):
        """Initialize SageMaker tool.
        
        Args:
            region: AWS region
            dry_run: Whether to run in dry-run mode (defaults to EXECUTE env var)
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # Default to dry_run unless EXECUTE=true is set
        execute_flag = os.getenv("EXECUTE", "false").lower() == "true"
        self.dry_run = dry_run if dry_run is not None else not execute_flag
        
        self.sagemaker_client = boto3.client("sagemaker", region_name=self.region)
        self.cloudwatch_client = boto3.client("cloudwatch", region_name=self.region)
        
        if self.dry_run:
            logger.warning("SageMakerTool running in DRY-RUN mode. No actual deployments will be made.")
    
    def delete_deployment_resources(
        self,
        config: SageMakerDeploymentConfig,
        force: bool = False
    ) -> Dict[str, Any]:
        """Delete SageMaker resources for a deployment.
        
        Args:
            config: Deployment configuration with endpoint/model names
            force: If True, delete even if endpoint is in use
            
        Returns:
            Dict with deletion results for each resource
        """
        results = {
            "endpoint_deleted": False,
            "endpoint_config_deleted": False,
            "model_deleted": False,
            "errors": []
        }
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would delete endpoint: {config.endpoint_name}")
            logger.info(f"[DRY-RUN] Would delete endpoint config: {config.endpoint_name}")
            logger.info(f"[DRY-RUN] Would delete model: {config.model_name}")
            results["endpoint_deleted"] = True
            results["endpoint_config_deleted"] = True
            results["model_deleted"] = True
            return results
        
        try:
            # Step 1: Delete Endpoint
            try:
                logger.info(f"Deleting SageMaker endpoint: {config.endpoint_name}")
                self.sagemaker_client.delete_endpoint(EndpointName=config.endpoint_name)
                # Wait for endpoint to be deleted
                try:
                    waiter = self.sagemaker_client.get_waiter('endpoint_deleted')
                    waiter.wait(EndpointName=config.endpoint_name, WaiterConfig={'Delay': 10, 'MaxAttempts': 60})
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFound':
                        raise
                logger.info(f"Successfully deleted endpoint: {config.endpoint_name}")
                results["endpoint_deleted"] = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFound':
                    logger.warning(f"Endpoint {config.endpoint_name} not found, may already be deleted")
                    results["endpoint_deleted"] = True
                else:
                    error_msg = f"Failed to delete endpoint {config.endpoint_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Step 2: Delete Endpoint Config
            try:
                logger.info(f"Deleting SageMaker endpoint config: {config.endpoint_name}")
                self.sagemaker_client.delete_endpoint_config(EndpointConfigName=config.endpoint_name)
                logger.info(f"Successfully deleted endpoint config: {config.endpoint_name}")
                results["endpoint_config_deleted"] = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFound':
                    logger.warning(f"Endpoint config {config.endpoint_name} not found, may already be deleted")
                    results["endpoint_config_deleted"] = True
                else:
                    error_msg = f"Failed to delete endpoint config {config.endpoint_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Step 3: Delete Model
            try:
                logger.info(f"Deleting SageMaker model: {config.model_name}")
                self.sagemaker_client.delete_model(ModelName=config.model_name)
                logger.info(f"Successfully deleted model: {config.model_name}")
                results["model_deleted"] = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFound':
                    logger.warning(f"Model {config.model_name} not found, may already be deleted")
                    results["model_deleted"] = True
                else:
                    error_msg = f"Failed to delete model {config.model_name}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during resource deletion: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)
        
        return results
    
    def deploy_model(
        self,
        config: SageMakerDeploymentConfig,
        model_data_url: str = None,
        container_image: str = None
    ) -> DeploymentResult:
        """Deploy model to SageMaker endpoint.
        
        Args:
            config: Validated deployment configuration
            model_data_url: S3 URI for model artifacts (required if not dry_run)
            container_image: Container image URI (defaults to minimal hello-world image)
            
        Returns:
            DeploymentResult with deployment status
        """
        if self.dry_run:
            return self._deploy_dry_run(config)
        
        if not model_data_url and not container_image:
            # Use a minimal hello-world container for demo
            container_image = "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.13.1-cpu-py39"
            logger.info(f"Using default container image: {container_image}")
        
        try:
            # Step 1: Create Model
            model_name = self._create_model(config, model_data_url, container_image)
            
            # Step 2: Create Endpoint Config with AutoRollbackConfiguration
            endpoint_config_name = self._create_endpoint_config(config, model_name)
            
            # Step 3: Create Endpoint
            endpoint_name = self._create_endpoint(config, endpoint_config_name)
            
            # Step 4: Configure Model Monitor (mock for demo)
            self._configure_model_monitor(config)
            
            return DeploymentResult(
                plan_id="",  # Will be set by orchestrator
                success=True,
                endpoint_name=endpoint_name,
                model_name=model_name,
                endpoint_config_name=endpoint_config_name,
                message=f"Successfully deployed {endpoint_name}",
                dry_run=False,
                timestamp=datetime.utcnow()
            )
            
        except ClientError as e:
            logger.error(f"SageMaker deployment error: {e}")
            return DeploymentResult(
                plan_id="",
                success=False,
                message=f"Deployment failed: {str(e)}",
                dry_run=False,
                timestamp=datetime.utcnow()
            )
    
    def _deploy_dry_run(self, config: SageMakerDeploymentConfig) -> DeploymentResult:
        """Simulate deployment in dry-run mode."""
        logger.info(f"[DRY-RUN] Would create model: {config.model_name}")
        logger.info(f"[DRY-RUN] Would create endpoint config with:")
        logger.info(f"  - Instance type: {config.instance_type}")
        logger.info(f"  - Instance count: {config.instance_count}")
        logger.info(f"  - AutoRollbackConfiguration: {config.rollback_alarms}")
        logger.info(f"[DRY-RUN] Would create endpoint: {config.endpoint_name}")
        logger.info(f"[DRY-RUN] Estimated cost: ${self._estimate_cost(config):.2f}/hour")
        
        return DeploymentResult(
            plan_id="",
            success=True,
            endpoint_name=config.endpoint_name,
            model_name=config.model_name,
            endpoint_config_name=f"{config.endpoint_name}-config",
            message="Dry-run completed successfully (no actual deployment)",
            dry_run=True,
            timestamp=datetime.utcnow()
        )
    
    def _create_model(
        self,
        config: SageMakerDeploymentConfig,
        model_data_url: Optional[str],
        container_image: Optional[str]
    ) -> str:
        """Create SageMaker model."""
        model_name = config.model_name
        
        model_params = {
            "ModelName": model_name,
            "PrimaryContainer": {
                "Image": container_image or "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.13.1-cpu-py39",
                "ModelDataUrl": model_data_url or "s3://sagemaker-sample-data/inference/model.tar.gz"
            },
            "ExecutionRoleArn": self._get_execution_role_arn()
        }
        
        logger.info(f"Creating model: {model_name}")
        self.sagemaker_client.create_model(**model_params)
        
        return model_name
    
    def _create_endpoint_config(
        self,
        config: SageMakerDeploymentConfig,
        model_name: str
    ) -> str:
        """Create SageMaker endpoint configuration with AutoRollbackConfiguration."""
        endpoint_config_name = f"{config.endpoint_name}-config"
        
        production_variants = [{
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InitialInstanceCount": config.instance_count,
            "InstanceType": config.instance_type,
            "InitialVariantWeight": 1.0
        }]
        
        # AutoRollbackConfiguration for safety
        auto_rollback_config = None
        if config.rollback_alarms:
            auto_rollback_config = {
                "Alarms": [
                    {
                        "AlarmName": alarm_name
                    }
                    for alarm_name in config.rollback_alarms
                ]
            }
        
        endpoint_config_params = {
            "EndpointConfigName": endpoint_config_name,
            "ProductionVariants": production_variants,
        }
        
        if auto_rollback_config:
            endpoint_config_params["AutoRollbackConfiguration"] = auto_rollback_config
            logger.info(f"Configured AutoRollbackConfiguration with alarms: {config.rollback_alarms}")
        
        logger.info(f"Creating endpoint config: {endpoint_config_name}")
        self.sagemaker_client.create_endpoint_config(**endpoint_config_params)
        
        return endpoint_config_name
    
    def _create_endpoint(
        self,
        config: SageMakerDeploymentConfig,
        endpoint_config_name: str
    ) -> str:
        """Create SageMaker endpoint."""
        endpoint_name = config.endpoint_name
        
        endpoint_params = {
            "EndpointName": endpoint_name,
            "EndpointConfigName": endpoint_config_name
        }
        
        logger.info(f"Creating endpoint: {endpoint_name}")
        self.sagemaker_client.create_endpoint(**endpoint_params)
        
        logger.info(f"Endpoint {endpoint_name} is being created (this may take several minutes)")
        
        return endpoint_name
    
    def _configure_model_monitor(self, config: SageMakerDeploymentConfig):
        """Configure Model Monitor (mock for demo)."""
        # In production, this would set up Model Monitor
        # For MVP, we'll just log it
        logger.info(f"[MOCK] Configuring Model Monitor for {config.endpoint_name}")
        logger.info(f"[MOCK] Model Monitor alarms: {config.rollback_alarms}")
    
    def _get_execution_role_arn(self) -> str:
        """Get SageMaker execution role ARN."""
        role_name = os.getenv("SAGEMAKER_ROLE_NAME", "SageMakerExecutionRole")
        
        # Try to get from env var first
        role_arn = os.getenv("SAGEMAKER_ROLE_ARN")
        if role_arn:
            return role_arn
        
        # Otherwise construct from role name
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    
    def _estimate_cost(self, config: SageMakerDeploymentConfig) -> float:
        """Estimate hourly cost (matching guardrail pricing)."""
        from orchestrator.guardrail import INSTANCE_PRICING
        base_price = INSTANCE_PRICING.get(config.instance_type, 1.0)
        return base_price * config.instance_count

