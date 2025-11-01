"""Audit logging service for DynamoDB and CloudTrail integration."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from orchestrator.models import (
    UserIntentRequest,
    DeploymentPlan,
    ApprovalRequest,
    DeploymentResult,
    ValidationResult
)

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging audit events to DynamoDB."""

    def __init__(self, table_name: str = None, region: str = None):
        """Initialize audit logger.
        
        Args:
            table_name: DynamoDB table name (defaults to DYNAMODB_TABLE_NAME env var)
            region: AWS region
        """
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "agentops-audit-log")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize DynamoDB client
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
            
            # Test table access
            try:
                self.table.meta.client.describe_table(TableName=self.table_name)
                logger.info(f"Audit logger connected to DynamoDB table: {self.table_name}")
            except ClientError:
                logger.warning(f"DynamoDB table {self.table_name} does not exist or is not accessible. Audit logging will be disabled.")
                self.table = None
        except Exception as e:
            logger.warning(f"Failed to initialize DynamoDB client: {e}. Audit logging will be disabled.")
            self.table = None
    
    async def log_intent(
        self,
        plan_id: str,
        request: Optional[UserIntentRequest],
        plan: Optional[DeploymentPlan],
        validation_result: Optional[ValidationResult]
    ):
        """Log intent submission event."""
        if not self.table:
            logger.debug(f"[AUDIT] Intent logged (mock): plan_id={plan_id}")
            return
        
        try:
            item = {
                "plan_id": plan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "intent_submitted",
                "user_id": request.user_id if request else "system@agentops.ai",
                "intent": request.intent if request else (plan.intent if plan else "unknown"),
                "env": request.env.value if request and request.env else (plan.env.value if plan and plan.env else "unknown"),
                "plan_status": plan.status.value if plan and plan.status else "unknown",
                "validation_passed": validation_result.valid if validation_result else None,
                "validation_errors": validation_result.errors if validation_result else None,
                "requires_approval": plan.status.value == "pending_approval" if plan and plan.status else False
            }
            
            self.table.put_item(Item=item)
            logger.info(f"[AUDIT] Logged intent: {plan_id}")
            
        except ClientError as e:
            logger.error(f"Failed to log intent to DynamoDB: {e}")
    
    async def log_status_change(
        self,
        plan_id: str,
        plan: Optional[DeploymentPlan],
        event_type: str,
        user_id: Optional[str] = None
    ):
        """Log deployment status change event (pause, restart, etc.)."""
        if not self.table:
            logger.debug(f"[AUDIT] Status change logged (mock): plan_id={plan_id}, event={event_type}")
            return
        
        try:
            item = {
                "plan_id": plan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id or "system@agentops.ai",
                "plan_status": plan.status.value if plan and plan.status else "unknown",
                "intent": plan.intent if plan else None,
                "env": plan.env.value if plan and plan.env else None
            }
            
            self.table.put_item(Item=item)
            logger.info(f"[AUDIT] Logged status change: {plan_id}, event={event_type}")
            
        except ClientError as e:
            logger.error(f"Failed to log status change to DynamoDB: {e}")

    async def log_deletion(
        self,
        plan_id: str,
        plan: Optional[DeploymentPlan],
        hard_delete: bool = False,
        user_id: Optional[str] = None
    ):
        """Log deployment deletion event."""
        if not self.table:
            logger.debug(f"[AUDIT] Deletion logged (mock): plan_id={plan_id}, hard_delete={hard_delete}")
            return
        
        try:
            item = {
                "plan_id": plan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "deployment_deleted",
                "user_id": user_id or "system@agentops.ai",
                "plan_status": plan.status.value if plan else "deleted",
                "hard_delete": hard_delete,
                "intent": plan.intent if plan else None,
                "env": plan.env.value if plan and plan.env else None
            }
            
            self.table.put_item(Item=item)
            logger.info(f"[AUDIT] Logged deletion: {plan_id}, hard_delete={hard_delete}")
            
        except ClientError as e:
            logger.error(f"Failed to log deletion to DynamoDB: {e}")

    async def log_approval(self, plan_id: str, approval: ApprovalRequest):
        """Log approval decision event."""
        if not self.table:
            logger.debug(f"[AUDIT] Approval logged (mock): plan_id={plan_id}, decision={approval.decision}")
            return
        
        try:
            item = {
                "plan_id": plan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "approval_decision",
                "approver": approval.approver,
                "decision": approval.decision.value if approval.decision else None,
                "reason": approval.reason
            }
            
            self.table.put_item(Item=item)
            logger.info(f"[AUDIT] Logged approval: {plan_id}, decision={approval.decision}")
            
        except ClientError as e:
            logger.error(f"Failed to log approval to DynamoDB: {e}")
    
    async def log_deployment(self, plan_id: str, result: DeploymentResult):
        """Log deployment execution event."""
        if not self.table:
            logger.debug(f"[AUDIT] Deployment logged (mock): plan_id={plan_id}, success={result.success}")
            return
        
        try:
            item = {
                "plan_id": plan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "deployment_executed",
                "success": result.success,
                "endpoint_name": result.endpoint_name,
                "model_name": result.model_name,
                "dry_run": result.dry_run,
                "message": result.message
            }
            
            self.table.put_item(Item=item)
            logger.info(f"[AUDIT] Logged deployment: {plan_id}, success={result.success}")
            
        except ClientError as e:
            logger.error(f"Failed to log deployment to DynamoDB: {e}")

