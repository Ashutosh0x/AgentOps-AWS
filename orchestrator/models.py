"""Pydantic models for AgentOps orchestrator."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field, conint, confloat

if TYPE_CHECKING:
    from typing import ForwardRef


class Environment(str, Enum):
    """Deployment environment."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class ApprovalState(str, Enum):
    """Approval state for deployment plans."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PlanStatus(str, Enum):
    """Status of a deployment plan."""
    AWAITING_VALIDATION = "awaiting_validation"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    VALIDATION_FAILED = "validation_failed"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    PAUSED = "paused"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DELETED = "deleted"


class UserIntentRequest(BaseModel):
    """User intent request model."""
    user_id: str = Field(..., description="User identifier")
    intent: str = Field(..., description="Natural language deployment intent")
    env: Environment = Field(..., description="Target deployment environment")
    constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional constraints (e.g., budget_usd_per_hour)"
    )


class SageMakerDeploymentConfig(BaseModel):
    """SageMaker deployment configuration."""
    model_name: str = Field(..., description="SageMaker model name")
    endpoint_name: str = Field(..., description="SageMaker endpoint name")
    instance_type: str = Field(..., description="SageMaker instance type (e.g., ml.m5.large)")
    instance_count: conint(ge=1, le=4) = Field(default=1, description="Number of instances (1-4)")
    max_payload_mb: conint(ge=1, le=1024) = Field(default=6, description="Max payload size in MB")
    autoscaling_min: conint(ge=1, le=4) = Field(default=1, description="Min autoscaling instances")
    autoscaling_max: conint(ge=1, le=8) = Field(default=2, description="Max autoscaling instances")
    rollback_alarms: List[str] = Field(
        default_factory=list,
        description="CloudWatch alarm names for rollback triggers"
    )
    budget_usd_per_hour: confloat(gt=0) = Field(
        default=10.0,
        description="Budget constraint in USD per hour"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "model_name": "llama-3.1-8b-chatbot-x",
                "endpoint_name": "chatbot-x-staging",
                "instance_type": "ml.m5.large",
                "instance_count": 1,
                "max_payload_mb": 6,
                "autoscaling_min": 1,
                "autoscaling_max": 2,
                "rollback_alarms": ["ModelMonitorAlarm"],
                "budget_usd_per_hour": 15.0
            }
        }


class RAGEvidence(BaseModel):
    """RAG retrieval evidence snippet."""
    title: str = Field(..., description="Document title")
    snippet: str = Field(..., description="Relevant text snippet")
    url: Optional[str] = Field(None, description="Document URL if available")
    score: Optional[float] = Field(None, description="Relevance score")


class ReasoningStep(BaseModel):
    """Single reasoning step in Chain-of-Thought."""
    thought: str = Field(..., description="What the agent is thinking")
    reasoning: str = Field(..., description="Explicit reasoning/explanation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0.0-1.0)")
    alternatives: List[str] = Field(default_factory=list, description="Alternative approaches considered")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence or RAG snippets")
    decision: Optional[str] = Field(None, description="Decision made based on this reasoning")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReasoningChain(BaseModel):
    """Chain of reasoning steps showing agent's thought process."""
    agent_name: str = Field(..., description="Name of the agent")
    context: str = Field(..., description="Context/situation being reasoned about")
    steps: List[ReasoningStep] = Field(default_factory=list, description="Reasoning steps")
    conclusion: Optional[str] = Field(None, description="Final conclusion")
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStep(BaseModel):
    """Single step in agent execution plan."""
    step_id: str = Field(..., description="Unique step identifier")
    agent_type: str = Field(..., description="Agent type: 'planner', 'executor', 'monitor', 'retriever'")
    action: str = Field(..., description="Action being performed")
    status: str = Field(..., description="Status: 'thinking', 'executing', 'completed', 'failed', 'retrying'")
    input: Dict[str, Any] = Field(default_factory=dict, description="Step input data")
    output: Dict[str, Any] = Field(default_factory=dict, description="Step output data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Step timestamp")
    error: Optional[str] = Field(None, description="Error message if status is 'failed'")
    retry_count: int = Field(default=0, description="Number of retries for this step")
    reasoning_chain: Optional[ReasoningChain] = Field(None, description="Chain-of-thought reasoning for this step")
    needs_replan: bool = Field(default=False, description="Whether this step failure requires replanning")


class DeploymentPlan(BaseModel):
    """Deployment plan generated by the agent."""
    plan_id: str = Field(..., description="Unique plan identifier")
    status: PlanStatus = Field(default=PlanStatus.AWAITING_VALIDATION)
    user_id: str = Field(..., description="User who requested the deployment")
    intent: str = Field(..., description="Original user intent")
    env: Environment = Field(..., description="Target environment")
    artifact: SageMakerDeploymentConfig = Field(..., description="Generated deployment configuration")
    evidence: List[RAGEvidence] = Field(
        default_factory=list,
        description="Top RAG evidence snippets used in planning"
    )
    reasoning_steps: List[TaskStep] = Field(
        default_factory=list,
        description="Step-by-step reasoning chain from multi-agent execution"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    validation_errors: Optional[List[str]] = Field(
        default_factory=list,
        description="Validation errors if any"
    )


class ApprovalRequest(BaseModel):
    """Approval request model."""
    plan_id: str = Field(..., description="Plan ID requiring approval")
    approver: Optional[str] = Field(None, description="Approver user ID")
    decision: Optional[ApprovalState] = Field(None, description="Approval decision")
    timestamp: Optional[datetime] = Field(None, description="Decision timestamp")
    reason: Optional[str] = Field(None, description="Reason for decision")


class DeploymentResult(BaseModel):
    """Result of deployment execution."""
    plan_id: str = Field(..., description="Associated plan ID")
    success: bool = Field(..., description="Whether deployment succeeded")
    endpoint_name: Optional[str] = Field(None, description="Created endpoint name")
    model_name: Optional[str] = Field(None, description="Created model name")
    endpoint_config_name: Optional[str] = Field(None, description="Created endpoint config name")
    message: str = Field(..., description="Result message")
    dry_run: bool = Field(default=True, description="Whether this was a dry run")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    """Guardrail validation result."""
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class ExecutionPlan(BaseModel):
    """Multi-step execution plan created by Planner Agent."""
    plan_id: str = Field(..., description="Associated deployment plan ID")
    steps: List[TaskStep] = Field(default_factory=list, description="Ordered list of execution steps")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    reasoning_chain: Optional[ReasoningChain] = Field(None, description="Planning reasoning chain")
    replan_count: int = Field(default=0, description="Number of times plan was replanned")
    max_replans: int = Field(default=3, description="Maximum allowed replans")


class ExecutionResult(BaseModel):
    """Result of executing a single step."""
    step_id: str = Field(..., description="Step identifier")
    success: bool = Field(..., description="Whether step execution succeeded")
    output: Dict[str, Any] = Field(default_factory=dict, description="Execution output")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MonitoringResult(BaseModel):
    """Result from Monitoring Agent."""
    plan_id: str = Field(..., description="Deployment plan ID being monitored")
    status: str = Field(..., description="Overall monitoring status")
    checks: List[Dict[str, Any]] = Field(default_factory=list, description="Individual check results")
    requires_action: bool = Field(default=False, description="Whether human action is needed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

