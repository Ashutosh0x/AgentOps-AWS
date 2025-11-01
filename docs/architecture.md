# AgentOps Architecture

## System Overview

AgentOps is an autonomous MLOps orchestrator that manages the complete lifecycle of ML model deployments on AWS SageMaker. It uses NVIDIA NIMs (NVIDIA Inference Microservices) for LLM reasoning and RAG (Retrieval-Augmented Generation), implementing a three-layer safety framework for production-grade autonomous operations.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   REST API   │  │  Approval UI │  │  Demo/CLI Scripts    │ │
│  │  (FastAPI)   │  │   (HTML)     │  │                       │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────────┘ │
└─────────┼─────────────────┼────────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Core                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Orchestrator (main.py)                           │  │
│  │  - Intent Processing                                      │  │
│  │  - Workflow Orchestration                                 │  │
│  │  - State Management                                       │  │
│  └──────┬───────────────────┬───────────────────┬────────────┘  │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐         │
│  │ LLM Client  │  │  Retriever  │  │  Guardrails   │         │
│  │ (NIM Call)  │  │   Client    │  │  (Validation) │         │
│  └─────────────┘  └─────────────┘  └──────────────┘         │
└──────────────────────────────────────────────────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NVIDIA NIM Services                          │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │ llama-3.1-       │  │  NeMo Retriever NIM               │  │
│  │ nemotron-nano-   │  │  ┌────────────┐  ┌─────────────┐ │  │
│  │ 8B-v1 (LLM)      │  │  │  Embedding  │  │  Reranking  │ │  │
│  │                  │  │  │    NIM      │  │     NIM     │ │  │
│  │ - Coordinator    │  │  └────────────┘  └─────────────┘ │  │
│  │ - Planner        │  │                                    │  │
│  └──────────────────┘  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Layer                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SageMaker Tool (sage_tool.py)                          │  │
│  │  - Model Creation                                        │  │
│  │  - Endpoint Configuration                                │  │
│  │  - Endpoint Deployment                                   │  │
│  │  - AutoRollbackConfiguration                            │  │
│  │  - Model Monitor Setup                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Services                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  SageMaker   │  │  DynamoDB    │  │  CloudTrail + S3     │ │
│  │  Endpoints   │  │  (Audit Log) │  │  (Immutable Log)     │ │
│  └──────────────┘  └──────┬───────┘  └──────────────────────┘ │
└───────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  S3 Object Lock  │
                    │  (Immutability)   │
                    └──────────────────┘
```

## Data Flow

### 1. Intent Submission Flow

```
User Intent (POST /intent)
    │
    ├─▶ Parse UserIntentRequest
    │
    ├─▶ Retriever Client: Query policy documents
    │   │
    │   ├─▶ Embed query (NeMo Retriever Embedding NIM)
    │   ├─▶ Retrieve candidates (vector search)
    │   └─▶ Rerank (NeMo Retriever Reranking NIM)
    │
    ├─▶ LLM Client: Generate deployment plan
    │   │
    │   ├─▶ Format prompt with intent + RAG evidence
    │   ├─▶ Call llama-3.1-nemotron-nano-8B-v1 NIM
    │   └─▶ Parse SageMakerDeploymentConfig JSON
    │
    ├─▶ Guardrail Service: Validate plan
    │   │
    │   ├─▶ Schema validation
    │   ├─▶ Budget validation
    │   ├─▶ Policy validation
    │   └─▶ Cost estimation
    │
    ├─▶ Check if approval required
    │   │
    │   ├─▶ Prod environment → Pending Approval
    │   └─▶ Staging/Dev → Proceed to Execution
    │
    ├─▶ Audit Logger: Log intent
    │
    └─▶ Return plan_id and status
```

### 2. Approval Flow (HITL)

```
Pending Approval Plan
    │
    ├─▶ GET /approvals → List pending requests
    │
    ├─▶ Operator reviews plan (UI or API)
    │
    ├─▶ POST /approve → Approve/Reject
    │   │
    │   ├─▶ Update approval state
    │   ├─▶ If approved → Execute deployment
    │   └─▶ Audit Logger: Log approval
    │
    └─▶ Deployment proceeds
```

### 3. Execution Flow

```
Deployment Execution
    │
    ├─▶ SageMaker Tool: deploy_model()
    │   │
    │   ├─▶ If dry_run: Log actions, return mock result
    │   └─▶ If execute:
    │       ├─▶ create_model()
    │       ├─▶ create_endpoint_config()
    │       │   └─▶ Configure AutoRollbackConfiguration
    │       ├─▶ create_endpoint()
    │       └─▶ configure_model_monitor()
    │
    ├─▶ Update plan status (deployed/failed)
    │
    ├─▶ Audit Logger: Log deployment
    │
    └─▶ Return DeploymentResult
```

### 4. Rollback Flow

```
Model Monitor Alarm Triggered
    │
    ├─▶ CloudWatch Alarm: State → ALARM
    │
    ├─▶ AutoRollbackConfiguration detects alarm
    │
    ├─▶ SageMaker automatically:
    │   ├─▶ Terminates new endpoint variant
    │   ├─▶ Routes traffic back to previous variant
    │   └─▶ Emits rollback event
    │
    ├─▶ Update plan status: rolled_back
    │
    └─▶ Audit Logger: Log rollback
```

## Safety Architecture

### Layer 1: Guardrails (Proactive Validation)

**Purpose:** Validate commands before execution.

**Components:**
- Schema validation (Pydantic models)
- Budget validation (cost estimation)
- Policy validation (instance types, counts)
- Constraint validation (user-provided limits)

**Implementation:**
- `orchestrator/guardrail.py`
- Intercepts all deployment plans
- Returns structured validation errors
- Blocks invalid plans before execution

### Layer 2: HITL (Human-in-the-Loop)

**Purpose:** Require human approval for high-risk actions.

**Components:**
- Approval queue
- Simple web UI (`approvals_ui.html`)
- API endpoints (`/approvals`, `/approve`)
- Timeout and escalation (future)

**Triggers:**
- Production deployments (always)
- High-cost deployments (>$20/hour)
- Multiple instances in staging (>=3)

**Implementation:**
- `orchestrator/main.py` (approval endpoints)
- In-memory approval store (DynamoDB optional)
- Background task execution after approval

### Layer 3: Audit (Immutable Logging)

**Purpose:** Provide tamper-proof audit trail.

**Components:**
- DynamoDB table (queryable log)
- CloudTrail Data Events (captures DynamoDB writes)
- S3 bucket with Object Lock (immutable storage)

**Implementation:**
- `orchestrator/audit.py` (DynamoDB logging)
- Terraform: CloudTrail + S3 setup
- All intents, approvals, deployments logged

## RAG Architecture

### Two-Stage Retrieval

1. **Embedding Stage:**
   - Query → NeMo Retriever Embedding NIM
   - Generate query embedding vector
   - Retrieve top-k candidates from vector store

2. **Reranking Stage:**
   - Query + Candidates → NeMo Retriever Reranking NIM
   - Score and rerank candidates
   - Return top-3 most relevant documents

### Knowledge Base

**Documents:**
- Policy documents (`sample_policy.md`)
- Security playbooks
- Cost playbooks
- Technical runbooks

**Storage:**
- MVP: In-memory vector store
- Production: Amazon OpenSearch Serverless (recommended)

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestrator | FastAPI | REST API and workflow orchestration |
| LLM | llama-3.1-nemotron-nano-8B-v1 NIM | Planning and reasoning |
| RAG | NeMo Retriever NIM | Policy grounding |
| Validation | Pydantic | Schema and constraint validation |
| Deployment | boto3 / SageMaker SDK | Model and endpoint creation |
| Storage | DynamoDB | Queryable audit logs |
| Immutability | CloudTrail + S3 Object Lock | Forensic audit trail |
| Infrastructure | Terraform | IaC for AWS resources |

## Deployment Modes

### Dry-Run Mode (Default)

- Validates plans
- Logs boto3 calls
- Does not create actual resources
- Safe for testing and demos

**Enable:** Set `EXECUTE=false` (default)

### Execute Mode

- Creates actual SageMaker resources
- Deploys models and endpoints
- Configures monitoring and rollback
- Requires AWS permissions

**Enable:** Set `EXECUTE=true`

## Scalability Considerations

### Current MVP Limitations

- In-memory state store (plans, approvals)
- Mock RAG vector store
- Single orchestrator instance
- No authentication/authorization

### Production Recommendations

- **State Store:** Redis or DynamoDB for plans/approvals
- **Vector Store:** OpenSearch Serverless for RAG
- **Orchestrator:** Deploy on ECS/Fargate or EKS
- **Auth:** AWS Cognito or API Gateway authorizers
- **Monitoring:** CloudWatch Metrics, X-Ray tracing
- **Alerting:** SNS topics, PagerDuty integration

## Security Considerations

### Current MVP

- IAM roles for SageMaker execution
- S3 encryption at rest
- DynamoDB encryption
- CloudTrail audit logging

### Production Enhancements

- VPC endpoints for SageMaker
- Secrets Manager for credentials
- WAF for API protection
- Network isolation
- Encryption in transit (TLS)

## Cost Optimization

### Instance Selection

- Dev: `ml.m5.large` ($0.115/hour)
- Staging: `ml.m5.large` or `ml.m5.xlarge` ($0.230/hour)
- Prod: `ml.g5.12xlarge` ($16.896/hour) for GPU workloads

### Cost Controls

- Budget validation per environment
- Dry-run mode default
- Automatic endpoint shutdown (future)
- Spot instances for training (future)

---

For operational procedures, see [runbook.md](runbook.md).

