"""Deployment status aggregation from SageMaker and EKS."""

import os
import logging
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DeploymentStatusService:
    """Service for aggregating deployment status from AWS services."""

    def __init__(self, region: str = None):
        """Initialize deployment status service.
        
        Args:
            region: AWS region
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        try:
            self.sagemaker_client = boto3.client("sagemaker", region_name=self.region)
        except Exception as e:
            logger.warning(f"Failed to initialize SageMaker client: {e}")
            self.sagemaker_client = None
    
    def get_active_deployments(
        self,
        plans_store: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get count and list of active deployments.
        
        Args:
            plans_store: Dictionary of deployment plans (from orchestrator state)
            
        Returns:
            Dictionary with count and deployments list
        """
        active_statuses = ["deployed", "deploying"]
        active_deployments = []
        
        # Filter from plans_store
        if plans_store:
            for plan_id, plan in plans_store.items():
                if hasattr(plan, "status") and plan.status.value in active_statuses:
                    active_deployments.append({
                        "plan_id": plan_id,
                        "endpoint_name": plan.artifact.endpoint_name if hasattr(plan, "artifact") else None,
                        "status": plan.status.value,
                        "environment": plan.env.value if hasattr(plan, "env") else None,
                        "instance_type": plan.artifact.instance_type if hasattr(plan, "artifact") else None
                    })
        
        # Optionally cross-reference with actual SageMaker endpoints
        sage_maker_endpoints = []
        if self.sagemaker_client:
            try:
                response = self.sagemaker_client.list_endpoints(
                    StatusEquals="InService",
                    MaxResults=100
                )
                
                for endpoint in response.get("Endpoints", []):
                    endpoint_name = endpoint["EndpointName"]
                    # Check if endpoint matches any plan
                    matched = False
                    for deployment in active_deployments:
                        if deployment.get("endpoint_name") == endpoint_name:
                            matched = True
                            break
                    
                    if not matched:
                        # Endpoint exists but not in plans (external deployment)
                        sage_maker_endpoints.append({
                            "plan_id": None,
                            "endpoint_name": endpoint_name,
                            "status": "deployed",
                            "environment": "unknown",
                            "instance_type": "unknown"
                        })
                        
            except ClientError as e:
                logger.warning(f"Could not list SageMaker endpoints: {e}")
        
        all_active = active_deployments + sage_maker_endpoints
        
        return {
            "count": len(all_active),
            "deployments": all_active
        }
    
    def get_deployment_status(self, endpoint_name: str) -> Optional[str]:
        """Get status of a specific SageMaker endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
            
        Returns:
            Endpoint status or None if not found
        """
        if not self.sagemaker_client:
            return None
        
        try:
            response = self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
            return response.get("EndpointStatus")
        except ClientError as e:
            logger.warning(f"Could not describe endpoint {endpoint_name}: {e}")
            return None

