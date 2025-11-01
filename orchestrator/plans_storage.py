"""DynamoDB storage service for deployment plans and approvals."""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from orchestrator.models import (
    DeploymentPlan,
    PlanStatus,
    ApprovalRequest,
    ApprovalState,
    Environment
)

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ClientError, Exception) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed {func.__name__} after {max_retries} retries: {e}")
            raise last_exception
        return wrapper
    return decorator


class PlansStorage:
    """Service for storing and retrieving deployment plans from DynamoDB.
    
    Uses DynamoDB as primary storage with in-memory cache for performance.
    """

    def __init__(self, table_name: str = None, region: str = None):
        """Initialize plans storage.
        
        Args:
            table_name: DynamoDB table name (defaults to DYNAMODB_PLANS_TABLE_NAME env var)
            region: AWS region
        """
        self.table_name = table_name or os.getenv("DYNAMODB_PLANS_TABLE_NAME", "agentops-deployment-plans")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # In-memory cache for performance (plan_id -> DeploymentPlan)
        self._cache: Dict[str, DeploymentPlan] = {}
        self._cache_ttl: Dict[str, float] = {}  # Timestamp when cache entry expires
        self._cache_timeout = 300  # 5 minutes cache TTL
        
        # Configure DynamoDB client with retry settings
        config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'  # Adaptive retry mode for better reliability
            }
        )
        
        # Initialize DynamoDB client
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region, config=config)
            self.table = self.dynamodb.Table(self.table_name)
            
            # Test table access
            try:
                self.table.meta.client.describe_table(TableName=self.table_name)
                logger.info(f"Plans storage connected to DynamoDB table: {self.table_name}")
                self.enabled = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"DynamoDB table {self.table_name} does not exist. Attempting to create...")
                    # Try to create table (optional - could be created via Terraform)
                    try:
                        self._create_table_if_not_exists()
                    except Exception as create_error:
                        logger.warning(f"Could not create table: {create_error}. Using in-memory fallback.")
                        self.enabled = False
                        self.table = None
                else:
                    logger.warning(f"DynamoDB table {self.table_name} access error: {e}. Using in-memory fallback.")
                    self.enabled = False
                    self.table = None
        except Exception as e:
            logger.warning(f"Failed to initialize DynamoDB client: {e}. Using in-memory fallback.")
            self.enabled = False
            self.table = None
    
    def _create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist."""
        try:
            self.table.meta.client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'plan_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'plan_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            logger.info(f"Created DynamoDB table: {self.table_name}")
            # Wait for table to be active
            self.table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            self.enabled = True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {self.table_name} already exists")
                self.enabled = True
            else:
                raise
    
    def _get_from_cache(self, plan_id: str) -> Optional[DeploymentPlan]:
        """Get plan from cache if valid."""
        if plan_id in self._cache:
            if plan_id in self._cache_ttl and time.time() < self._cache_ttl[plan_id]:
                return self._cache[plan_id]
            else:
                # Cache expired
                del self._cache[plan_id]
                if plan_id in self._cache_ttl:
                    del self._cache_ttl[plan_id]
        return None
    
    def _set_cache(self, plan_id: str, plan: DeploymentPlan):
        """Cache a plan with TTL."""
        self._cache[plan_id] = plan
        self._cache_ttl[plan_id] = time.time() + self._cache_timeout
    
    def _invalidate_cache(self, plan_id: str):
        """Remove plan from cache."""
        if plan_id in self._cache:
            del self._cache[plan_id]
        if plan_id in self._cache_ttl:
            del self._cache_ttl[plan_id]
    
    @retry_on_error(max_retries=3, delay=1.0)
    def save_plan(self, plan: DeploymentPlan) -> bool:
        """Save or update a deployment plan.
        
        Saves to DynamoDB (primary) and updates cache.
        """
        # Always update cache for immediate reads
        self._set_cache(plan.plan_id, plan)
        
        if not self.enabled or not self.table:
            logger.warning("DynamoDB not enabled, plan saved to cache only")
            return False
        
        try:
            plan_dict = plan.dict()
            
            # Convert Pydantic models to JSON-serializable format
            item = {
                "plan_id": plan.plan_id,
                "status": plan.status.value,
                "user_id": plan.user_id,
                "intent": plan.intent,
                "env": plan.env.value if hasattr(plan.env, 'value') else str(plan.env),
                "created_at": plan.created_at.isoformat() if isinstance(plan.created_at, datetime) else str(plan.created_at),
                "updated_at": plan.updated_at.isoformat() if plan.updated_at and isinstance(plan.updated_at, datetime) else (str(plan.updated_at) if plan.updated_at else None),
                "artifact": json.dumps(plan.artifact.dict()) if plan.artifact else None,
                "evidence": json.dumps([ev.dict() for ev in plan.evidence]) if hasattr(plan, 'evidence') and plan.evidence else None,
                "reasoning_steps": json.dumps([step.dict() for step in plan.reasoning_steps]) if hasattr(plan, 'reasoning_steps') and plan.reasoning_steps else None,
                "validation_errors": json.dumps(plan.validation_errors) if hasattr(plan, 'validation_errors') and plan.validation_errors else None,
            }
            
            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}
            
            self.table.put_item(Item=item)
            logger.debug(f"[STORAGE] Saved plan: {plan.plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save plan to DynamoDB: {e}")
            return False
    
    @retry_on_error(max_retries=3, delay=1.0)
    def get_plan(self, plan_id: str) -> Optional[DeploymentPlan]:
        """Get a deployment plan by ID.
        
        Checks cache first, then DynamoDB. Updates cache on DynamoDB read.
        """
        # Try cache first
        cached_plan = self._get_from_cache(plan_id)
        if cached_plan:
            return cached_plan
        
        # If not in cache and DynamoDB not enabled, return None
        if not self.enabled or not self.table:
            return None
        
        try:
            response = self.table.get_item(
                Key={"plan_id": plan_id}
            )
            
            if "Item" not in response:
                return None
            
            item = response["Item"]
            plan = self._item_to_plan(item)
            
            # Update cache for future reads
            if plan:
                self._set_cache(plan_id, plan)
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to get plan from DynamoDB: {e}")
            return None
    
    @retry_on_error(max_retries=3, delay=1.0)
    def get_all_plans(self) -> List[DeploymentPlan]:
        """Get all deployment plans.
        
        Fetches from DynamoDB and updates cache.
        """
        if not self.enabled or not self.table:
            # Return cached plans if DynamoDB not available
            return list(self._cache.values())
        
        try:
            response = self.table.scan()
            plans = []
            
            for item in response.get("Items", []):
                try:
                    plan = self._item_to_plan(item)
                    if plan:
                        plans.append(plan)
                except Exception as e:
                    logger.warning(f"Failed to parse plan item: {e}")
                    continue
            
            # Continue scanning if paginated
            while "LastEvaluatedKey" in response:
                response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                for item in response.get("Items", []):
                    try:
                        plan = self._item_to_plan(item)
                        if plan:
                            plans.append(plan)
                            # Update cache
                            self._set_cache(plan.plan_id, plan)
                    except Exception as e:
                        logger.warning(f"Failed to parse plan item: {e}")
                        continue
            
            return plans
            
        except Exception as e:
            logger.error(f"Failed to get all plans from DynamoDB: {e}")
            return []
    
    def _item_to_plan(self, item: Dict[str, Any]) -> Optional[DeploymentPlan]:
        """Convert DynamoDB item to DeploymentPlan."""
        try:
            from orchestrator.models import SageMakerDeploymentConfig, RAGEvidence, TaskStep
            
            # Parse artifact (deployment config)
            artifact = None
            if item.get("artifact"):
                config_dict = json.loads(item["artifact"])
                artifact = SageMakerDeploymentConfig(**config_dict)
            
            # Parse evidence (RAG evidence)
            evidence = []
            if item.get("evidence"):
                evidence_list = json.loads(item["evidence"])
                evidence = [RAGEvidence(**ev) for ev in evidence_list]
            
            # Parse reasoning_steps with nested ReasoningChain support
            reasoning_steps = []
            if item.get("reasoning_steps"):
                try:
                    steps_list = json.loads(item["reasoning_steps"])
                    from orchestrator.models import ReasoningChain, ReasoningStep
                    
                    for step_dict in steps_list:
                        # Parse timestamp if present
                        if "timestamp" in step_dict and isinstance(step_dict["timestamp"], str):
                            step_dict["timestamp"] = datetime.fromisoformat(step_dict["timestamp"])
                        
                        # Parse reasoning_chain if present
                        if "reasoning_chain" in step_dict and step_dict["reasoning_chain"]:
                            chain_dict = step_dict["reasoning_chain"]
                            if isinstance(chain_dict, str):
                                chain_dict = json.loads(chain_dict)
                            
                            # Parse reasoning steps within the chain
                            chain_steps = []
                            if "steps" in chain_dict and chain_dict["steps"]:
                                for rs_dict in chain_dict["steps"]:
                                    # Parse timestamp in reasoning step
                                    if "timestamp" in rs_dict and isinstance(rs_dict["timestamp"], str):
                                        rs_dict["timestamp"] = datetime.fromisoformat(rs_dict["timestamp"])
                                    chain_steps.append(ReasoningStep(**rs_dict))
                            chain_dict["steps"] = chain_steps
                            
                            # Parse created_at in reasoning chain
                            if "created_at" in chain_dict and isinstance(chain_dict["created_at"], str):
                                chain_dict["created_at"] = datetime.fromisoformat(chain_dict["created_at"])
                            
                            step_dict["reasoning_chain"] = ReasoningChain(**chain_dict)
                        
                        reasoning_steps.append(TaskStep(**step_dict))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to parse reasoning_steps: {e}. Using empty list.")
                    reasoning_steps = []
                    # Log for debugging
                    logger.debug(f"reasoning_steps raw value: {item.get('reasoning_steps')}")
            
            # Parse validation_errors
            validation_errors = None
            if item.get("validation_errors"):
                validation_errors = json.loads(item["validation_errors"])
            
            # Parse dates
            created_at = datetime.fromisoformat(item["created_at"]) if isinstance(item.get("created_at"), str) else datetime.utcnow()
            updated_at = None
            if item.get("updated_at"):
                updated_at = datetime.fromisoformat(item["updated_at"]) if isinstance(item["updated_at"], str) else None
            
            plan = DeploymentPlan(
                plan_id=item["plan_id"],
                status=PlanStatus(item["status"]),
                user_id=item["user_id"],
                intent=item["intent"],
                env=Environment(item["env"]),
                created_at=created_at,
                updated_at=updated_at,
                artifact=artifact,
                evidence=evidence,
                reasoning_steps=reasoning_steps,
                validation_errors=validation_errors
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to convert item to plan: {e}")
            return None
    
    @retry_on_error(max_retries=3, delay=1.0)
    def save_approval(self, plan_id: str, approval: ApprovalRequest) -> bool:
        """Save or update an approval request.
        
        Saves to DynamoDB and invalidates cache for the plan.
        """
        if not self.enabled or not self.table:
            return False
        
        # Invalidate cache so next read fetches updated approval
        self._invalidate_cache(plan_id)
        
        try:
            item = {
                "plan_id": plan_id,
                "approval_decision": approval.decision.value if approval.decision else None,
                "approver": approval.approver,
                "approval_timestamp": approval.timestamp.isoformat() if approval.timestamp else None,
                "approval_reason": approval.reason,
            }
            
            # Update the plan item with approval info (using update_item)
            update_expression = "SET approval_decision = :decision, approver = :approver"
            expression_values = {
                ":decision": item["approval_decision"],
                ":approver": item["approver"],
            }
            
            if item["approval_timestamp"]:
                update_expression += ", approval_timestamp = :timestamp"
                expression_values[":timestamp"] = item["approval_timestamp"]
            
            if item["approval_reason"]:
                update_expression += ", approval_reason = :reason"
                expression_values[":reason"] = item["approval_reason"]
            
            self.table.update_item(
                Key={"plan_id": plan_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.debug(f"[STORAGE] Saved approval for plan: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save approval to DynamoDB: {e}")
            return False
    
    def get_approval(self, plan_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by plan_id."""
        if not self.enabled or not self.table:
            return None
        
        try:
            response = self.table.get_item(Key={"plan_id": plan_id})
            
            if "Item" not in response:
                return None
            
            item = response["Item"]
            
            if "approval_decision" not in item:
                return None
            
            decision = ApprovalState(item["approval_decision"]) if item.get("approval_decision") else None
            timestamp = datetime.fromisoformat(item["approval_timestamp"]) if item.get("approval_timestamp") else None
            
            approval = ApprovalRequest(
                plan_id=plan_id,
                decision=decision,
                approver=item.get("approver"),
                timestamp=timestamp,
                reason=item.get("approval_reason")
            )
            
            return approval
            
        except Exception as e:
            logger.error(f"Failed to get approval from DynamoDB: {e}")
            return None

