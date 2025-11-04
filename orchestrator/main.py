"""FastAPI orchestrator for AgentOps autonomous deployment."""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.models import (
    UserIntentRequest,
    DeploymentPlan,
    PlanStatus,
    ApprovalRequest,
    ApprovalState,
    Environment,
    TaskStep,
    ReasoningChain,
    ReasoningStep
)
from orchestrator.llm_client import LLMClient
from orchestrator.retriever_client import RetrieverClient
from orchestrator.guardrail import GuardrailService
from orchestrator.sage_tool import SageMakerTool
from orchestrator.audit import AuditLogger
from orchestrator.cost_service import CostService
from orchestrator.deployment_status import DeploymentStatusService
from orchestrator.plans_storage import PlansStorage
from orchestrator.agent_orchestrator import AgentOrchestrator
from orchestrator.agents.planner_agent import PlannerAgent
from orchestrator.agents.executor_agent import ExecutorAgent
from orchestrator.agents.monitoring_agent import MonitoringAgent
from orchestrator.agent_memory import AgentMemory
from orchestrator.tool_registry import get_tool_registry

# Configure structured logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json as _json
        base = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, 'plan_id'):
            base['plan_id'] = getattr(record, 'plan_id')
        return _json.dumps(base)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgentOps Orchestrator",
    description="Autonomous, safety-first model deployment orchestrator",
    version="1.0.0"
)

# Optional API key protection for /api/* routes
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    api_key = os.getenv("API_KEY")
    # Enforce only on API namespace if API_KEY is set
    if api_key and request.url.path.startswith("/api/"):
        provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if provided != api_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    # Optional HMAC signature validation
    hmac_secret = os.getenv("HMAC_SECRET")
    if hmac_secret and request.url.path.startswith("/api/"):
        import hmac, hashlib
        signature = request.headers.get("x-signature")
        # Compute HMAC over method + path + body
        body = await request.body()
        payload = f"{request.method}\n{request.url.path}\n".encode("utf-8") + body
        expected = hmac.new(hmac_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            return JSONResponse({"detail": "Invalid signature"}, status_code=401)
    return await call_next(request)

# CORS middleware for UI
# Get allowed origins from environment, default to localhost for development
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:8080"
)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory fallback (for compatibility)
plans_store: Dict[str, DeploymentPlan] = {}
approvals_store: Dict[str, ApprovalRequest] = {}
# Simple lifecycle counters (in-memory)
deploy_counters = {
    "started": 0,
    "succeeded": 0,
    "failed": 0,
}

# Initialize services
llm_client: Optional[LLMClient] = None
retriever_client: Optional[RetrieverClient] = None
guardrail_service: Optional[GuardrailService] = None
sage_tool: Optional[SageMakerTool] = None
audit_logger: Optional[AuditLogger] = None
cost_service: Optional[CostService] = None
deployment_status_service: Optional[DeploymentStatusService] = None
plans_storage: Optional[PlansStorage] = None
agent_orchestrator: Optional[AgentOrchestrator] = None
agent_memory: Optional[AgentMemory] = None


def _load_aws_documentation(retriever: RetrieverClient):
    """Load AWS documentation files into retriever with chunking and metadata.
    
    Args:
        retriever: RetrieverClient instance to populate
    """
    try:
        from pathlib import Path
        
        demo_data_dir = Path(__file__).parent / "demo_data"
        
        if not demo_data_dir.exists():
            logger.warning(f"Demo data directory not found: {demo_data_dir}")
            return
        
        doc_files = [
            ("sample_policy.md", {"service": "sagemaker", "doc_type": "policy"}),
            ("aws_security_policies.md", {"service": "sagemaker", "doc_type": "security", "security_level": "high"}),
            ("aws_pricing_catalog.md", {"service": "sagemaker", "doc_type": "pricing"}),
            ("aws_architecture_frameworks.md", {"service": "sagemaker", "doc_type": "architecture"}),
            ("aws_model_deployment_guides.md", {"service": "sagemaker", "doc_type": "deployment"}),
        ]
        
        total_chunks = 0
        
        for doc_file, metadata in doc_files:
            doc_path = demo_data_dir / doc_file
            if not doc_path.exists():
                continue
            
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract title from first line or filename
            lines = content.split("\n")
            doc_title = lines[0].strip("# ").strip() if lines and lines[0].startswith("#") else doc_file.replace(".md", "").replace("_", " ").title()
            
            # Chunk by sections (## headings)
            sections = content.split("\n## ")
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                
                section_lines = section.split("\n")
                section_title = section_lines[0].strip() if section_lines else f"{doc_title} Section {i+1}"
                section_content = "\n".join(section_lines[1:]) if len(section_lines) > 1 else section
                
                # Further chunk if section is too long (>1000 chars)
                if len(section_content) > 1000:
                    # Split into overlapping chunks
                    chunk_size = 1000
                    overlap = 200
                    chunks = []
                    start = 0
                    while start < len(section_content):
                        end = start + chunk_size
                        chunk = section_content[start:end]
                        if start > 0:
                            # Add overlap from previous chunk
                            chunk = section_content[start-overlap:start] + chunk
                        chunks.append(chunk)
                        start = end - overlap
                    
                    for j, chunk in enumerate(chunks):
                        chunk_title = f"{section_title} (Part {j+1})" if len(chunks) > 1 else section_title
                        retriever.add_document(
                            title=chunk_title,
                            content=chunk,
                            url=f"file://{doc_file}#section-{i+1}-part-{j+1}",
                            metadata=metadata
                        )
                        total_chunks += 1
                else:
                    retriever.add_document(
                        title=section_title if len(sections) > 1 else doc_title,
                        content=section_content,
                        url=f"file://{doc_file}#section-{i+1}" if len(sections) > 1 else f"file://{doc_file}",
                        metadata=metadata
                    )
                    total_chunks += 1
        
        logger.info(f"Loaded {total_chunks} document chunks from {len([f for f, _ in doc_files if (demo_data_dir / f).exists()])} files into retriever")
        
    except Exception as e:
        logger.warning(f"Failed to load AWS documentation: {e}")
        import traceback
        logger.debug(traceback.format_exc())


def _ensure_services_initialized():
    """Ensure services are initialized (for Lambda compatibility)."""
    global llm_client, retriever_client, guardrail_service, sage_tool, audit_logger
    global cost_service, deployment_status_service, plans_storage, agent_orchestrator, agent_memory
    
    if retriever_client is None:
        try:
            # Initialize LLM client (can fail if endpoint not set - will use mock)
            try:
                llm_client = LLMClient()
            except ValueError:
                logger.warning("LLM_ENDPOINT not set, using mock LLM client")
                llm_client = None
            
            # Initialize retriever client (will use mock if endpoints not set)
            retriever_client = RetrieverClient()
            
            # Load AWS documentation into retriever (with chunking and metadata)
            _load_aws_documentation(retriever_client)
            
            # Initialize guardrail service
            guardrail_service = GuardrailService()
            
            # Initialize SageMaker tool
            sage_tool = SageMakerTool()
            
            # Initialize audit logger
            audit_logger = AuditLogger()
            
            # Initialize metrics services
            cost_service = CostService()
            deployment_status_service = DeploymentStatusService()
            
            # Initialize Agent Memory for learning
            try:
                agent_memory = AgentMemory()
                logger.info("Agent memory system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize agent memory: {e}. Continuing without memory.")
                agent_memory = None
            
            # Initialize DynamoDB storage for plans (with fallback to in-memory)
            try:
                plans_storage = PlansStorage()
                if plans_storage.enabled:
                    logger.info("DynamoDB plans storage enabled")
                    # Load existing plans from DynamoDB into memory cache
                    all_plans = plans_storage.get_all_plans()
                    for plan in all_plans:
                        plans_store[plan.plan_id] = plan
                    logger.info(f"Loaded {len(all_plans)} plans from DynamoDB")
            except Exception as e:
                logger.warning(f"Failed to initialize DynamoDB storage: {e}. Using in-memory only.")
                plans_storage = None
            
            # Initialize multi-agent orchestrator with agentic AI features
            try:
                planner_agent = PlannerAgent(llm_client=llm_client, memory=agent_memory)
                executor_agent = ExecutorAgent(
                    guardrail_service=guardrail_service,
                    sage_tool=sage_tool
                )
                monitoring_agent = MonitoringAgent()
                
                agent_orchestrator = AgentOrchestrator(
                    planner_agent=planner_agent,
                    executor_agent=executor_agent,
                    monitoring_agent=monitoring_agent,
                    retriever_client=retriever_client,
                    agent_memory=agent_memory
                )
                logger.info("Multi-agent orchestrator initialized with agentic AI capabilities")
            except Exception as e:
                logger.warning(f"Failed to initialize agent orchestrator: {e}")
                agent_orchestrator = None
            
            logger.info("AgentOps orchestrator services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

        # Demo seeding removed for realistic operation by default


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Use the consolidated initialization function to avoid duplication
    _ensure_services_initialized()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AgentOps Orchestrator",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/intent", response_model=Dict[str, Any])
async def submit_intent(
    request: UserIntentRequest,
    background_tasks: BackgroundTasks
):
    """Submit deployment intent and generate plan.
    
    Returns plan_id and status. If production, plan will be pending approval.
    """
    plan_id = str(uuid.uuid4())
    
    # Ensure services are initialized (lazy init for Lambda)
    _ensure_services_initialized()
    
    try:
        # Step 1: Retrieve relevant policy documents
        logger.info(f"[{plan_id}] Retrieving policy documents for intent: {request.intent}")
        
        retrieval_query = f"{request.intent} deployment policies for {request.env.value} environment"
        rag_evidence = retriever_client.query(retrieval_query, top_k=3)
        
        logger.info(f"[{plan_id}] Retrieved {len(rag_evidence)} policy documents")
        
        # Step 2: Generate deployment plan using LLM
        logger.info(f"[{plan_id}] Generating deployment plan with LLM")
        
        if llm_client:
            deployment_config = llm_client.generate_plan(
                intent=request.intent,
                env=request.env.value,
                rag_evidence=rag_evidence,
                constraints=request.constraints or {}
            )
        else:
            # Mock LLM response for demo if endpoint not configured
            logger.warning(f"[{plan_id}] Using mock LLM response")
            from orchestrator.models import SageMakerDeploymentConfig
            deployment_config = SageMakerDeploymentConfig(
                model_name=f"llama-3.1-8b-{request.env.value}",
                endpoint_name=f"chatbot-x-{request.env.value}",
                instance_type="ml.m5.large" if request.env != Environment.PROD else "ml.g5.12xlarge",
                instance_count=1 if request.env != Environment.PROD else 2,
                budget_usd_per_hour=request.constraints.get("budget_usd_per_hour", 15.0) if request.env != Environment.PROD else 50.0
            )
        
        # Step 3: Validate plan with guardrails
        logger.info(f"[{plan_id}] Validating plan with guardrails")
        
        validation_result = guardrail_service.validate_plan(
            deployment_config,
            request.env,
            request.constraints or {}
        )
        
        # Create deployment plan
        plan = DeploymentPlan(
            plan_id=plan_id,
            status=PlanStatus.VALIDATION_FAILED if not validation_result.valid else PlanStatus.AWAITING_VALIDATION,
            user_id=request.user_id,
            intent=request.intent,
            env=request.env,
            artifact=deployment_config,
            evidence=rag_evidence,
            validation_errors=validation_result.errors if not validation_result.valid else []
        )
        
        # Check if approval is required
        requires_approval = guardrail_service.requires_approval(deployment_config, request.env)
        
        if not validation_result.valid:
            plan.status = PlanStatus.VALIDATION_FAILED
            plans_store[plan_id] = plan
            
            # Audit log
            await audit_logger.log_intent(plan_id, request, plan, validation_result)
            
            return {
                "plan_id": plan_id,
                "status": plan.status.value,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
        
        # Step 4: Check if approval is needed
        if requires_approval:
            logger.info(f"[{plan_id}] Plan requires approval (env={request.env.value})")
            plan.status = PlanStatus.PENDING_APPROVAL
            
            # Create approval request
            approval_request = ApprovalRequest(
                plan_id=plan_id,
                decision=None
            )
            approvals_store[plan_id] = approval_request
            if plans_storage and plans_storage.enabled:
                plans_storage.save_approval(plan_id, approval_request)
            
        else:
            # Step 5: Execute deployment (staging/low-risk)
            logger.info(f"[{plan_id}] Proceeding with deployment (no approval required)")
            plan.status = PlanStatus.DEPLOYING
            
            # Execute in background
            background_tasks.add_task(execute_deployment, plan_id, deployment_config)
        
        # Store plan (in-memory and DynamoDB)
        plans_store[plan_id] = plan
        if plans_storage and plans_storage.enabled:
            plans_storage.save_plan(plan)
        
        # Audit log
        await audit_logger.log_intent(plan_id, request, plan, validation_result)
        
        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "artifact": deployment_config.dict(),
            "evidence": [ev.dict() for ev in rag_evidence],
            "warnings": validation_result.warnings,
            "requires_approval": requires_approval
        }
        
    except Exception as e:
        logger.error(f"[{plan_id}] Error processing intent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing intent: {str(e)}")


@app.get("/approvals")
async def list_approvals():
    """List all pending approval requests."""
    pending = [
        {
            "plan_id": plan_id,
            "plan": plans_store[plan_id].dict(),
            "created_at": approvals_store[plan_id].timestamp or datetime.utcnow()
        }
        for plan_id, approval in approvals_store.items()
        if approval.decision is None and plans_store.get(plan_id) is not None
    ]
    
    return {
        "pending_approvals": pending,
        "count": len(pending)
    }


@app.post("/approve")
async def approve_plan(approval: ApprovalRequest, background_tasks: BackgroundTasks):
    """Approve or reject a deployment plan."""
    plan_id = approval.plan_id
    
    if plan_id not in plans_store:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    plan = plans_store[plan_id]
    
    if plan.status != PlanStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Plan {plan_id} is not pending approval (status: {plan.status.value})"
        )
    
    if approval.decision == ApprovalState.APPROVED:
        logger.info(f"[{plan_id}] Plan approved by {approval.approver}")
        
        # Update approval
        approval_request = approvals_store[plan_id]
        approval_request.decision = ApprovalState.APPROVED
        approval_request.approver = approval.approver
        approval_request.timestamp = datetime.utcnow()
        approval_request.reason = approval.reason
        if plans_storage and plans_storage.enabled:
            plans_storage.save_approval(plan_id, approval_request)
        
        # Update plan status
        plan.status = PlanStatus.DEPLOYING
        plan.updated_at = datetime.utcnow()
        deploy_counters["started"] += 1
        plans_store[plan_id] = plan
        if plans_storage and plans_storage.enabled:
            plans_storage.save_plan(plan)
        
        # Execute deployment in background
        background_tasks.add_task(execute_deployment, plan_id, plan.artifact)
        
        # Audit log
        await audit_logger.log_approval(plan_id, approval)
        
        return {
            "plan_id": plan_id,
            "status": "approved",
            "message": "Deployment started"
        }
    
    elif approval.decision == ApprovalState.REJECTED:
        logger.info(f"[{plan_id}] Plan rejected by {approval.approver}")
        
        # Update approval
        approval_request = approvals_store[plan_id]
        approval_request.decision = ApprovalState.REJECTED
        approval_request.approver = approval.approver
        approval_request.timestamp = datetime.utcnow()
        approval_request.reason = approval.reason
        if plans_storage and plans_storage.enabled:
            plans_storage.save_approval(plan_id, approval_request)
        
        # Update plan status
        plan.status = PlanStatus.REJECTED
        plan.updated_at = datetime.utcnow()
        plans_store[plan_id] = plan
        if plans_storage and plans_storage.enabled:
            plans_storage.save_plan(plan)
        
        # Audit log
        await audit_logger.log_approval(plan_id, approval)
        
        return {
            "plan_id": plan_id,
            "status": "rejected",
            "message": "Deployment rejected"
        }
    
    else:
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")


@app.get("/plan/{plan_id}")
async def get_plan(plan_id: str):
    """Get deployment plan status and details."""
    _ensure_services_initialized()
    
    # Try DynamoDB first, then fallback to in-memory
    plan = None
    if plans_storage and plans_storage.enabled:
        plan = plans_storage.get_plan(plan_id)
        # Update cache for future reads
        if plan:
            plans_store[plan_id] = plan
    
    # Fallback to in-memory store
    if not plan and plan_id in plans_store:
        plan = plans_store[plan_id]
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    # Debug logging for reasoning_steps
    reasoning_steps_count = len(plan.reasoning_steps) if plan.reasoning_steps else 0
    logger.debug(f"[{plan_id}] Plan retrieved with {reasoning_steps_count} reasoning steps")
    if reasoning_steps_count == 0:
        logger.warning(f"[{plan_id}] Plan has no reasoning_steps - frontend will use fallback logs")
    
    # Get approval info
    approval_info = None
    if plans_storage and plans_storage.enabled:
        approval = plans_storage.get_approval(plan_id)
        if approval:
            approval_info = approval.dict()
    elif plan_id in approvals_store:
        approval_info = approvals_store[plan_id].dict()
    
    # Custom serialization to ensure datetime fields and nested objects serialize correctly
    def serialize_plan(plan: DeploymentPlan) -> Dict[str, Any]:
        """Serialize DeploymentPlan with proper datetime and nested object handling."""
        plan_dict = plan.dict(exclude_none=True)
        
        # Ensure created_at and updated_at are ISO strings
        if plan.created_at:
            plan_dict["created_at"] = plan.created_at.isoformat() if isinstance(plan.created_at, datetime) else plan.created_at
        if plan.updated_at:
            plan_dict["updated_at"] = plan.updated_at.isoformat() if isinstance(plan.updated_at, datetime) else plan.updated_at
        
        # Serialize reasoning_steps with nested ReasoningChain and datetime handling
        if plan.reasoning_steps:
            serialized_steps = []
            for step in plan.reasoning_steps:
                step_dict = step.dict(exclude_none=True)
                # Convert timestamp to ISO string
                if step.timestamp:
                    step_dict["timestamp"] = step.timestamp.isoformat() if isinstance(step.timestamp, datetime) else step.timestamp
                # Serialize reasoning_chain if present
                if step.reasoning_chain:
                    chain_dict = step.reasoning_chain.dict(exclude_none=True)
                    # Serialize reasoning steps within the chain
                    if step.reasoning_chain.steps:
                        chain_steps = []
                        for reasoning_step in step.reasoning_chain.steps:
                            rs_dict = reasoning_step.dict(exclude_none=True)
                            # Convert timestamp to ISO string
                            if reasoning_step.timestamp:
                                rs_dict["timestamp"] = reasoning_step.timestamp.isoformat() if isinstance(reasoning_step.timestamp, datetime) else reasoning_step.timestamp
                            chain_steps.append(rs_dict)
                        chain_dict["steps"] = chain_steps
                    # Convert created_at in reasoning chain
                    if step.reasoning_chain.created_at:
                        chain_dict["created_at"] = step.reasoning_chain.created_at.isoformat() if isinstance(step.reasoning_chain.created_at, datetime) else step.reasoning_chain.created_at
                    step_dict["reasoning_chain"] = chain_dict
                serialized_steps.append(step_dict)
            plan_dict["reasoning_steps"] = serialized_steps
        
        # Serialize artifact (deployment config)
        if plan.artifact:
            plan_dict["artifact"] = plan.artifact.dict(exclude_none=True)
        
        # Serialize evidence
        if plan.evidence:
            plan_dict["evidence"] = [ev.dict(exclude_none=True) for ev in plan.evidence]
        
        return plan_dict
    
    return {
        "plan": serialize_plan(plan),
        "approval": approval_info
    }


def _seed_demo_plan():
    """Create a deterministic demo plan with rich reasoning steps if none exists."""
    demo_plan_id = os.getenv("DEMO_PLAN_ID", "demo-plan-001")
    if demo_plan_id in plans_store:
        return

    from orchestrator.models import SageMakerDeploymentConfig, RAGEvidence

    config = SageMakerDeploymentConfig(
        model_name=os.getenv("DEMO_MODEL_NAME", "llama-3.1-8b-staging"),
        endpoint_name=os.getenv("DEMO_ENDPOINT_NAME", "chatbot-x-staging"),
        instance_type=os.getenv("DEMO_INSTANCE_TYPE", "ml.m5.large"),
        instance_count=int(os.getenv("DEMO_INSTANCE_COUNT", "1")),
        budget_usd_per_hour=float(os.getenv("DEMO_BUDGET_USD_PER_HOUR", "15.0"))
    )

    evidence = [
        RAGEvidence(title="AWS Security Policies", snippet="Require staging to use non-GPU instances where possible."),
        RAGEvidence(title="AWS Pricing Catalog", snippet="ml.m5.large costs approx $0.115/hr."),
    ]

    now = datetime.utcnow()
    steps = [
        TaskStep(step_id="retriever-1", agent_type="retriever", action="retrieve_policies", status="completed", timestamp=now),
        TaskStep(step_id="planner-1", agent_type="planner", action="generate_config", status="completed", timestamp=now),
        TaskStep(step_id="executor-1", agent_type="executor", action="validate_plan", status="completed", timestamp=now),
        TaskStep(step_id="executor-2", agent_type="executor", action="create_model", status="executing", timestamp=now),
        TaskStep(step_id="executor-3", agent_type="executor", action="create_endpoint_config", status="pending", timestamp=now),
        TaskStep(step_id="executor-4", agent_type="executor", action="create_endpoint", status="pending", timestamp=now),
        TaskStep(step_id="monitor-1", agent_type="monitor", action="configure_monitoring", status="pending", timestamp=now),
    ]

    plan = DeploymentPlan(
        plan_id=demo_plan_id,
        status=PlanStatus.DEPLOYING,
        user_id=os.getenv("DEMO_USER_ID", "demo@agentops.ai"),
        intent=os.getenv("DEMO_INTENT", "deploy llama-3.1 8B for chatbot-x"),
        env=Environment.STAGING,
        artifact=config,
        evidence=evidence,
        reasoning_steps=steps,
        created_at=now
    )

    plans_store[demo_plan_id] = plan
    if plans_storage and plans_storage.enabled:
        plans_storage.save_plan(plan)


@app.get("/api/events/{plan_id}")
async def stream_plan_events(plan_id: str):
    """Simple SSE stream of plan status and step updates (demo-friendly)."""
    _ensure_services_initialized()

    async def event_generator():
        import asyncio
        sent = 0
        while True:
            plan = None
            if plans_storage and plans_storage.enabled:
                plan = plans_storage.get_plan(plan_id)
                if plan:
                    plans_store[plan_id] = plan
            if not plan and plan_id in plans_store:
                plan = plans_store[plan_id]
            if not plan:
                yield f"event: error\ndata: { {'error': f'plan {plan_id} not found'} }\n\n"
                return

            # Serialize minimal status payload
            step_payload = [
                {
                    "step_id": s.step_id,
                    "agent_type": s.agent_type,
                    "action": s.action,
                    "status": s.status,
                    "message": s.output.get("message") if s.output else None,
                }
                for s in (plan.reasoning_steps or [])
            ]
            payload = {
                "plan_id": plan.plan_id,
                "status": plan.status.value if hasattr(plan.status, 'value') else str(plan.status),
                "steps": step_payload,
            }
            import json as _json
            yield f"data: {_json.dumps(payload)}\n\n"

            sent += 1
            await asyncio.sleep(1.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/approvals-ui", response_class=HTMLResponse)
async def approvals_ui():
    """Simple HTML UI for approval queue."""
    with open("orchestrator/approvals_ui.html", "r") as f:
        return f.read()


# Dashboard API endpoints
@app.get("/api/metrics/deployments/active")
async def get_active_deployments():
    """Get count and list of active deployments."""
    _ensure_services_initialized()
    
    result = deployment_status_service.get_active_deployments(plans_store)
    
    return result


@app.get("/api/metrics/approvals/pending")
async def get_pending_approvals():
    """Get count and list of pending approvals."""
    pending = [
        {
            "plan_id": plan_id,
            "plan": plans_store[plan_id].dict(),
            "created_at": approvals_store[plan_id].timestamp or datetime.utcnow()
        }
        for plan_id, approval in approvals_store.items()
        if approval.decision is None and plans_store.get(plan_id) is not None
    ]
    
    return {
        "count": len(pending),
        "approvals": pending
    }


@app.get("/api/metrics/costs/monthly")
async def get_monthly_costs():
    """Get monthly GPU spend from Cost Explorer."""
    _ensure_services_initialized()
    
    result = cost_service.get_monthly_gpu_spend()
    
    return result

@app.get("/api/metrics/deployments/counters")
async def get_deploy_counters():
    return deploy_counters


@app.get("/api/deployments")
async def get_all_deployments():
    """Get all deployment plans formatted for table display."""
    _ensure_services_initialized()
    
    deployments = []
    
    # Try to get plans from DynamoDB first, then fall back to in-memory
    if plans_storage and plans_storage.enabled:
        try:
            all_plans = plans_storage.get_all_plans()
            for plan in all_plans:
                plan_dict = plan.dict()
                
                # Get approval info from DynamoDB or memory
                approval = plans_storage.get_approval(plan.plan_id)
                if approval:
                    plan_dict["approval"] = {
                        "decision": approval.decision.value if approval.decision else None,
                        "approver": approval.approver,
                        "timestamp": approval.timestamp.isoformat() if approval.timestamp else None
                    }
                elif plan.plan_id in approvals_store:
                    approval = approvals_store[plan.plan_id]
                    plan_dict["approval"] = {
                        "decision": approval.decision.value if approval.decision else None,
                        "approver": approval.approver,
                        "timestamp": approval.timestamp.isoformat() if approval.timestamp else None
                    }
                
                deployments.append(plan_dict)
        except Exception as e:
            logger.error(f"Error loading plans from DynamoDB: {e}, falling back to in-memory")
            # Fall through to in-memory store
    
    # Fallback to in-memory store (or combine if DynamoDB failed)
    for plan_id, plan in plans_store.items():
        # Skip if already added from DynamoDB
        if any(d.get("plan_id") == plan_id for d in deployments):
            continue
        
        # Skip deleted deployments
        if plan.status == PlanStatus.DELETED:
            continue
        
        plan_dict = plan.dict()
        
        # Add approval info if available
        if plan_id in approvals_store:
            approval = approvals_store[plan_id]
            plan_dict["approval"] = {
                "decision": approval.decision.value if approval.decision else None,
                "approver": approval.approver,
                "timestamp": approval.timestamp.isoformat() if approval.timestamp else None
            }
        
        deployments.append(plan_dict)
    
    # Sort by created_at descending (most recent first)
    deployments.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    
    return {
        "deployments": deployments,
        "count": len(deployments)
    }


@app.get("/api/deployments/{plan_id}")
async def get_deployment_details(plan_id: str):
    """Get a single deployment plan with full details (including approval info)."""
    _ensure_services_initialized()

    plan = None
    if plans_storage and plans_storage.enabled:
        plan = plans_storage.get_plan(plan_id)
        if plan:
            plans_store[plan_id] = plan

    if not plan and plan_id in plans_store:
        plan = plans_store[plan_id]

    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    # Build response similar to /plan/{plan_id}
    def serialize_plan(plan: DeploymentPlan) -> Dict[str, Any]:
        plan_dict = plan.dict(exclude_none=True)

        if plan.created_at:
            plan_dict["created_at"] = plan.created_at.isoformat() if isinstance(plan.created_at, datetime) else plan.created_at
        if plan.updated_at:
            plan_dict["updated_at"] = plan.updated_at.isoformat() if isinstance(plan.updated_at, datetime) else plan.updated_at

        if plan.reasoning_steps:
            serialized_steps = []
            for step in plan.reasoning_steps:
                step_dict = step.dict(exclude_none=True)
                if step.timestamp:
                    step_dict["timestamp"] = step.timestamp.isoformat() if isinstance(step.timestamp, datetime) else step.timestamp
                if step.reasoning_chain:
                    chain_dict = step.reasoning_chain.dict(exclude_none=True)
                    if step.reasoning_chain.steps:
                        chain_steps = []
                        for rs in step.reasoning_chain.steps:
                            rs_dict = rs.dict(exclude_none=True)
                            if rs.timestamp:
                                rs_dict["timestamp"] = rs.timestamp.isoformat() if isinstance(rs.timestamp, datetime) else rs.timestamp
                            chain_steps.append(rs_dict)
                        chain_dict["steps"] = chain_steps
                    if step.reasoning_chain.created_at:
                        chain_dict["created_at"] = step.reasoning_chain.created_at.isoformat() if isinstance(step.reasoning_chain.created_at, datetime) else step.reasoning_chain.created_at
                    step_dict["reasoning_chain"] = chain_dict
                serialized_steps.append(step_dict)
            plan_dict["reasoning_steps"] = serialized_steps

        if plan.artifact:
            plan_dict["artifact"] = plan.artifact.dict(exclude_none=True)

        if plan.evidence:
            plan_dict["evidence"] = [ev.dict(exclude_none=True) for ev in plan.evidence]

        return plan_dict

    approval_info = None
    if plans_storage and plans_storage.enabled:
        approval = plans_storage.get_approval(plan_id)
        if approval:
            approval_info = approval.dict()
    elif plan_id in approvals_store:
        approval_info = approvals_store[plan_id].dict()

    return {
        "plan": serialize_plan(plan),
        "approval": approval_info
    }


@app.post("/api/deployments/{plan_id}/pause")
async def pause_deployment(plan_id: str):
    """Pause a deployment."""
    _ensure_services_initialized()
    
    # Get plan from DynamoDB or cache
    plan = None
    if plans_storage and plans_storage.enabled:
        plan = plans_storage.get_plan(plan_id)
    
    if not plan and plan_id in plans_store:
        plan = plans_store[plan_id]
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    # Only allow pausing if deployed or deploying
    if plan.status not in [PlanStatus.DEPLOYED, PlanStatus.DEPLOYING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause deployment with status {plan.status.value}"
        )
    
    plan.status = PlanStatus.PAUSED
    plan.updated_at = datetime.utcnow()
    
    # Save to DynamoDB first (primary storage)
    if plans_storage and plans_storage.enabled:
        plans_storage.save_plan(plan)
    
    # Update cache
    plans_store[plan_id] = plan
    
    await audit_logger.log_status_change(plan_id, plan, "deployment_paused")
    
    return {"success": True, "message": f"Deployment {plan_id} paused successfully"}


@app.post("/api/deployments/{plan_id}/restart")
async def restart_deployment(plan_id: str, background_tasks: BackgroundTasks):
    """Restart a deployment."""
    _ensure_services_initialized()
    
    # Get plan from DynamoDB or cache
    plan = None
    if plans_storage and plans_storage.enabled:
        plan = plans_storage.get_plan(plan_id)
    
    if not plan and plan_id in plans_store:
        plan = plans_store[plan_id]
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    # Only allow restarting if deployed, failed, or paused
    if plan.status not in [PlanStatus.DEPLOYED, PlanStatus.FAILED, PlanStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restart deployment with status {plan.status.value}"
        )
    
    plan.status = PlanStatus.DEPLOYING
    plan.updated_at = datetime.utcnow()
    
    # Save to DynamoDB first (primary storage)
    if plans_storage and plans_storage.enabled:
        plans_storage.save_plan(plan)
    
    # Update cache
    plans_store[plan_id] = plan
    
    # Restart deployment
    if plan.artifact:
        background_tasks.add_task(execute_deployment, plan_id, plan.artifact)
    
    await audit_logger.log_status_change(plan_id, plan, "deployment_restarted")
    
    return {"success": True, "message": f"Deployment {plan_id} restarting"}


@app.delete("/api/deployments/{plan_id}")
async def delete_deployment(plan_id: str, hard_delete: bool = Query(False, description="If True, also delete SageMaker resources and agent memory")):
    """Delete a deployment and clean up associated resources.
    
    Args:
        plan_id: Deployment plan ID
        hard_delete: If True, also delete SageMaker resources and agent memory (default: False for soft delete)
    """
    _ensure_services_initialized()
    
    # Get plan from DynamoDB or cache
    plan = None
    if plans_storage and plans_storage.enabled:
        plan = plans_storage.get_plan(plan_id)
    
    if not plan and plan_id in plans_store:
        plan = plans_store[plan_id]
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    deletion_results = {
        "plan_deleted": False,
        "sagemaker_resources_deleted": False,
        "agent_memory_deleted": False,
        "memory_count": 0,
        "errors": []
    }
    
    try:
        # Step 1: Delete SageMaker resources if hard_delete is True
        if hard_delete and plan.artifact:
            try:
                logger.info(f"[{plan_id}] Deleting SageMaker resources for deployment")
                sagemaker_results = sage_tool.delete_deployment_resources(plan.artifact)
                
                deletion_results["sagemaker_resources_deleted"] = (
                    sagemaker_results.get("endpoint_deleted", False) and
                    sagemaker_results.get("endpoint_config_deleted", False) and
                    sagemaker_results.get("model_deleted", False)
                )
                deletion_results["errors"].extend(sagemaker_results.get("errors", []))
                
                if deletion_results["sagemaker_resources_deleted"]:
                    logger.info(f"[{plan_id}] Successfully deleted SageMaker resources")
                else:
                    logger.warning(f"[{plan_id}] Some SageMaker resources may not have been deleted")
            except Exception as e:
                error_msg = f"Failed to delete SageMaker resources: {str(e)}"
                logger.error(f"[{plan_id}] {error_msg}", exc_info=True)
                deletion_results["errors"].append(error_msg)
        
        # Step 2: Delete agent memories associated with this deployment
        if agent_memory and agent_memory.enabled:
            try:
                logger.info(f"[{plan_id}] Deleting agent memories for deployment")
                memory_count = agent_memory.delete_memories_for_plan(plan_id)
                deletion_results["agent_memory_deleted"] = True
                deletion_results["memory_count"] = memory_count
                logger.info(f"[{plan_id}] Deleted {memory_count} agent memories")
            except Exception as e:
                error_msg = f"Failed to delete agent memories: {str(e)}"
                logger.error(f"[{plan_id}] {error_msg}", exc_info=True)
                deletion_results["errors"].append(error_msg)
        
        # Step 3: Mark plan as deleted (soft delete) or remove from storage (hard delete)
        plan.status = PlanStatus.DELETED
        plan.updated_at = datetime.utcnow()
        
        if hard_delete:
            # Hard delete: Remove from DynamoDB if enabled
            if plans_storage and plans_storage.enabled:
                try:
                    # Actually delete from DynamoDB (not just mark as deleted)
                    plans_storage.table.delete_item(Key={"plan_id": plan_id})
                    logger.info(f"[{plan_id}] Hard deleted plan from DynamoDB")
                except Exception as e:
                    logger.warning(f"[{plan_id}] Failed to hard delete from DynamoDB: {e}, marking as deleted instead")
                    plans_storage.save_plan(plan)  # Fallback to soft delete
            else:
                # Remove from in-memory store
                if plan_id in plans_store:
                    del plans_store[plan_id]
                if plan_id in approvals_store:
                    del approvals_store[plan_id]
            deletion_results["plan_deleted"] = True
        else:
            # Soft delete: Mark as deleted but keep in storage
            if plans_storage and plans_storage.enabled:
                plans_storage.save_plan(plan)
            plans_store[plan_id] = plan
            deletion_results["plan_deleted"] = True
        
        # Audit log deletion
        await audit_logger.log_deletion(plan_id, plan, hard_delete=hard_delete)
        
        # Build response message
        message_parts = [f"Deployment {plan_id} deleted successfully"]
        if hard_delete:
            message_parts.append("(hard delete: resources removed)")
        if deletion_results.get("memory_count", 0) > 0:
            message_parts.append(f"({deletion_results['memory_count']} agent memories deleted)")
        
        response = {
            "success": True,
            "message": " ".join(message_parts),
            "details": deletion_results
        }
        
        if deletion_results["errors"]:
            response["warnings"] = deletion_results["errors"]
        
        return response
        
    except Exception as e:
        logger.error(f"[{plan_id}] Error during deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete deployment: {str(e)}")


@app.post("/api/agent/command")
async def process_agent_command(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Process natural language command through orchestrator.
    
    Expected payload:
    {
        "command": "deploy llama-3.1 8B for chatbot-x",
        "user_id": "alice@example.com",
        "env": "staging"
    }
    """
    _ensure_services_initialized()
    
    # Extract command and convert to UserIntentRequest format
    command = request.get("command", "")
    user_id = request.get("user_id", "system@agentops.ai")
    env_str = request.get("env", "staging").lower()
    
    # Map env string to Environment enum
    env_map = {
        "staging": Environment.STAGING,
        "prod": Environment.PROD,
        "production": Environment.PROD,
        "dev": Environment.STAGING,
        "development": Environment.STAGING
    }
    env = env_map.get(env_str, Environment.STAGING)
    
    # Parse constraints if provided
    constraints = request.get("constraints", {})
    
    # Create UserIntentRequest
    intent_request = UserIntentRequest(
        user_id=user_id,
        intent=command,
        env=env,
        constraints=constraints if constraints else None
    )
    
    # Process through existing intent endpoint logic
    plan_id = str(uuid.uuid4())
    
    try:
        # Step 1: Retrieve relevant policy documents
        logger.info(f"[{plan_id}] Processing command: {command}")
        
        retrieval_query = f"{command} deployment policies for {env.value} environment"
        rag_evidence = retriever_client.query(retrieval_query, top_k=3)
        
        # Step 2: Generate deployment plan
        if llm_client:
            deployment_config = llm_client.generate_plan(
                intent=command,
                env=env.value,
                rag_evidence=rag_evidence,
                constraints=constraints
            )
        else:
            # Mock LLM response
            from orchestrator.models import SageMakerDeploymentConfig
            deployment_config = SageMakerDeploymentConfig(
                model_name=f"llama-3.1-8b-{env.value}",
                endpoint_name=f"chatbot-x-{env.value}",
                instance_type="ml.m5.large" if env != Environment.PROD else "ml.g5.12xlarge",
                instance_count=1 if env != Environment.PROD else 2,
                budget_usd_per_hour=constraints.get("budget_usd_per_hour", 15.0) if env != Environment.PROD else 50.0
            )
        
        # Step 3: Validate plan
        validation_result = guardrail_service.validate_plan(
            deployment_config,
            env,
            constraints
        )
        
        # Step 4: Use Agent Orchestrator to create execution plan with reasoning steps
        reasoning_steps = []
        if agent_orchestrator and validation_result.valid:
            try:
                execution_plan = agent_orchestrator.execute_deployment_plan(
                    plan_id=plan_id,
                    intent=command,
                    env=env.value,
                    deployment_config=deployment_config,
                    rag_evidence=rag_evidence,
                    constraints=constraints
                )
                reasoning_steps = execution_plan.steps
                logger.info(f"[{plan_id}] Generated {len(reasoning_steps)} reasoning steps via agent orchestrator")
            except Exception as e:
                logger.warning(f"[{plan_id}] Agent orchestrator failed: {e}. Generating fallback reasoning steps.")
                reasoning_steps = []
        
        # Ensure reasoning_steps are always populated for log display
        if not reasoning_steps or len(reasoning_steps) == 0:
            logger.info(f"[{plan_id}] Generating fallback reasoning steps for deployment")
            now = datetime.utcnow()
            
            # Create fallback steps representing the deployment process
            reasoning_steps = [
                TaskStep(
                    step_id=f"{plan_id}-step-received",
                    agent_type="system",
                    action="command_received",
                    status="completed",
                    input={"command": command, "env": env.value},
                    output={"message": f"Command received: {command}"},
                    timestamp=now,
                    reasoning_chain=ReasoningChain(
                        agent_name="System",
                        context="Command reception",
                        steps=[
                            ReasoningStep(
                                thought=f"Received deployment command: {command}",
                                reasoning="Command parsed and validated",
                                confidence=1.0,
                                decision="Proceed with deployment planning"
                            )
                        ],
                        conclusion="Command received and queued for processing"
                    )
                ),
                TaskStep(
                    step_id=f"{plan_id}-step-retrieval",
                    agent_type="retriever",
                    action="retrieve_policies",
                    status="completed" if rag_evidence else "thinking",
                    input={"query": f"{command} deployment policies for {env.value}"},
                    output={
                        "message": f"Retrieved {len(rag_evidence)} relevant policy documents",
                        "evidence_count": len(rag_evidence)
                    },
                    timestamp=now,
                    reasoning_chain=ReasoningChain(
                        agent_name="Retriever Agent",
                        context="Policy document retrieval",
                        steps=[
                            ReasoningStep(
                                thought=f"Searching for policies related to: {command}",
                                reasoning=f"Retrieved {len(rag_evidence)} relevant documents",
                                confidence=0.9 if rag_evidence else 0.5,
                                decision="Use retrieved policies for planning"
                            )
                        ],
                        conclusion=f"Retrieval complete with {len(rag_evidence)} documents"
                    )
                ),
                TaskStep(
                    step_id=f"{plan_id}-step-planning",
                    agent_type="planner",
                    action="generate_config",
                    status="completed" if deployment_config else "thinking",
                    input={"intent": command, "env": env.value, "evidence_count": len(rag_evidence)},
                    output={
                        "message": "Deployment configuration generated",
                        "endpoint_name": deployment_config.endpoint_name if deployment_config else None,
                        "instance_type": deployment_config.instance_type if deployment_config else None
                    },
                    timestamp=now,
                    reasoning_chain=ReasoningChain(
                        agent_name="Planner Agent",
                        context="Deployment configuration generation",
                        steps=[
                            ReasoningStep(
                                thought=f"Planning deployment for {command} in {env.value}",
                                reasoning=f"Generated config: {deployment_config.endpoint_name if deployment_config else 'pending'}",
                                confidence=0.85,
                                decision="Configuration ready for validation"
                            )
                        ],
                        conclusion="Deployment plan created"
                    )
                ),
                TaskStep(
                    step_id=f"{plan_id}-step-validation",
                    agent_type="executor",
                    action="validate_plan",
                    status="completed" if validation_result.valid else "failed",
                    input={"config": deployment_config.dict() if deployment_config else {}},
                    output={
                        "message": "Validation complete",
                        "valid": validation_result.valid,
                        "errors": validation_result.errors if validation_result else []
                    },
                    timestamp=now,
                    error=None if validation_result.valid else ("; ".join(validation_result.errors) if validation_result.errors else "Validation failed"),
                    reasoning_chain=ReasoningChain(
                        agent_name="Executor Agent",
                        context="Plan validation",
                        steps=[
                            ReasoningStep(
                                thought="Validating deployment plan against guardrails",
                                reasoning=f"Validation {'passed' if validation_result.valid else 'failed'}",
                                confidence=1.0 if validation_result.valid else 0.3,
                                decision="Plan validated" if validation_result.valid else "Validation errors detected"
                            )
                        ],
                        conclusion="Validation complete"
                    )
                )
            ]
            logger.info(f"[{plan_id}] Generated {len(reasoning_steps)} fallback reasoning steps")
        else:
            logger.debug(f"[{plan_id}] Using {len(reasoning_steps)} reasoning steps from orchestrator")
        
        # Create deployment plan
        plan = DeploymentPlan(
            plan_id=plan_id,
            status=PlanStatus.VALIDATION_FAILED if not validation_result.valid else PlanStatus.AWAITING_VALIDATION,
            user_id=user_id,
            intent=command,
            env=env,
            artifact=deployment_config,
            evidence=rag_evidence,
            reasoning_steps=reasoning_steps,
            validation_errors=validation_result.errors if not validation_result.valid else []
        )
        
        requires_approval = guardrail_service.requires_approval(deployment_config, env)
        
        if not validation_result.valid:
            plan.status = PlanStatus.VALIDATION_FAILED
            plans_store[plan_id] = plan
            await audit_logger.log_intent(plan_id, intent_request, plan, validation_result)
            
            return {
                "command_id": plan_id,
                "status": "validation_failed",
                "result": {
                    "plan_id": plan_id,
                    "errors": validation_result.errors
                }
            }
        
        if requires_approval:
            plan.status = PlanStatus.PENDING_APPROVAL
            approval_request = ApprovalRequest(
                plan_id=plan_id,
                decision=None
            )
            approvals_store[plan_id] = approval_request
            if plans_storage and plans_storage.enabled:
                plans_storage.save_approval(plan_id, approval_request)
        else:
            plan.status = PlanStatus.DEPLOYING
            background_tasks.add_task(execute_deployment, plan_id, deployment_config)
        
        plans_store[plan_id] = plan
        if plans_storage and plans_storage.enabled:
            plans_storage.save_plan(plan)
        await audit_logger.log_intent(plan_id, intent_request, plan, validation_result)
        
        return {
            "command_id": plan_id,
            "status": "success",
            "result": {
                "plan_id": plan_id,
                "status": plan.status.value,
                "artifact": deployment_config.dict(),
                "reasoning_steps": [step.dict() for step in reasoning_steps],
                "requires_approval": requires_approval
            }
        }
        
    except Exception as e:
        logger.error(f"[{plan_id}] Error processing command: {e}", exc_info=True)
        return {
            "command_id": plan_id,
            "status": "error",
            "error": str(e)
        }


async def execute_deployment(plan_id: str, config):
    """Execute deployment in background."""
    try:
        logger.info(f"[{plan_id}] Executing deployment")
        
        plan = plans_store.get(plan_id)
        if not plan:
            logger.error(f"[{plan_id}] Plan not found")
            return
        
        plan.status = PlanStatus.DEPLOYING
        plan.updated_at = datetime.utcnow()
        
        # Helper to update a step's status consistently
        def update_step(action: str, status: str, message: str = None):
            step = None
            for s in (plan.reasoning_steps or []):
                if s.action == action:
                    step = s
                    break
            if not step:
                # Create step if not present
                step = TaskStep(
                    step_id=f"{action}-{uuid.uuid4().hex[:8]}",
                    agent_type="executor",
                    action=action,
                    status=status,
                    output={"message": message} if message else {},
                )
                plan.reasoning_steps.append(step)
            else:
                step.status = status
                if message:
                    step.output = step.output or {}
                    step.output["message"] = message
            plan.updated_at = datetime.utcnow()
            plans_store[plan_id] = plan
            if plans_storage and plans_storage.enabled:
                plans_storage.save_plan(plan)
        
        # Retry/backoff helper
        import time
        def with_retries(op_name: str, func, *args, retries: int = 3, base_delay: float = 2.0, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Map AWS errors if possible
                    friendly = str(e)
                    try:
                        from botocore.exceptions import ClientError
                        if isinstance(e, ClientError):
                            code = e.response.get('Error', {}).get('Code', 'ClientError')
                            msg = e.response.get('Error', {}).get('Message', friendly)
                            friendly = f"{op_name} failed ({code}): {msg}"
                    except Exception:
                        pass
                    attempt += 1
                    if attempt > retries:
                        raise RuntimeError(friendly)
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f"[{plan_id}] {op_name} attempt {attempt} failed, retrying in {delay:.1f}s: {friendly}")
                    time.sleep(delay)

        # 1) Create model
        update_step("create_model", "executing", "Creating model")
        try:
            model_name = with_retries("create_model", sage_tool.create_model, config)
            update_step("create_model", "completed", f"Model {model_name} created")
        except Exception as e:
            update_step("create_model", "failed", f"Create model failed: {str(e)}")
            plan.status = PlanStatus.FAILED
            plans_store[plan_id] = plan
            if plans_storage and plans_storage.enabled:
                plans_storage.save_plan(plan)
            await audit_logger.log_deployment(plan_id, {
                "success": False,
                "message": f"Create model failed: {str(e)}"
            })
            return
        
        # 2) Create endpoint config
        update_step("create_endpoint_config", "executing", "Creating endpoint config")
        try:
            endpoint_config_name = with_retries("create_endpoint_config", sage_tool.create_endpoint_config, config, model_name)
            update_step("create_endpoint_config", "completed", f"Endpoint config {endpoint_config_name} created")
        except Exception as e:
            update_step("create_endpoint_config", "failed", f"Create endpoint config failed: {str(e)}")
            plan.status = PlanStatus.FAILED
            plans_store[plan_id] = plan
            if plans_storage and plans_storage.enabled:
                plans_storage.save_plan(plan)
            await audit_logger.log_deployment(plan_id, {
                "success": False,
                "message": f"Create endpoint config failed: {str(e)}"
            })
            return
        
        # 3) Create endpoint
        update_step("create_endpoint", "executing", "Creating endpoint")
        try:
            endpoint_name = with_retries("create_endpoint", sage_tool.create_endpoint, config, endpoint_config_name)
            update_step("create_endpoint", "executing", f"Endpoint {endpoint_name} creating...")
            # Wait for endpoint to be InService/Failed
            final_status = with_retries("wait_for_endpoint", sage_tool.wait_for_endpoint, endpoint_name, retries=1, base_delay=5.0)
            if final_status == "InService":
                update_step("create_endpoint", "completed", f"Endpoint {endpoint_name} InService")
                plan.status = PlanStatus.DEPLOYED
                logger.info(f"[{plan_id}] Deployment successful: {endpoint_name}")
                deploy_counters["succeeded"] += 1
            else:
                update_step("create_endpoint", "failed", f"Endpoint status: {final_status}")
                plan.status = PlanStatus.FAILED
                logger.error(f"[{plan_id}] Deployment failed with endpoint status: {final_status}")
                deploy_counters["failed"] += 1
        except Exception as e:
            update_step("create_endpoint", "failed", f"Create endpoint failed: {str(e)}")
            plan.status = PlanStatus.FAILED
            deploy_counters["failed"] += 1
        
        
        plan.updated_at = datetime.utcnow()
        
        # Save updated plan to DynamoDB
        plans_store[plan_id] = plan
        if plans_storage and plans_storage.enabled:
            plans_storage.save_plan(plan)
        
        # Audit log
        # Create a minimal deployment result for audit
        await audit_logger.log_deployment(plan_id, {
            "success": plan.status == PlanStatus.DEPLOYED,
            "message": f"Deployment {plan.status.value}",
        })
        
    except Exception as e:
        logger.error(f"[{plan_id}] Error executing deployment: {e}", exc_info=True)
        plan = plans_store.get(plan_id)
        if plan:
            plan.status = PlanStatus.FAILED
            plan.updated_at = datetime.utcnow()
            if plans_storage and plans_storage.enabled:
                plans_storage.save_plan(plan)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

