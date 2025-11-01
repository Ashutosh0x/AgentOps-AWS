# AgentOps - Autonomous Model Deployment System

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [User Flows](#user-flows)
5. [Technical Implementation](#technical-implementation)
6. [API Reference](#api-reference)
7. [Deployment](#deployment)

---

## 🎯 Overview

**AgentOps** is an autonomous, safety-first model deployment system that enables users to deploy AI/ML models to Amazon SageMaker using natural language commands. The system intelligently orchestrates the entire deployment lifecycle, from intent understanding to execution, with built-in guardrails, human-in-the-loop approvals, and comprehensive audit logging.

### Key Capabilities

- **Natural Language Deployment**: Deploy models using simple commands like "deploy llama-3.1 8B for chatbot-x"
- **Autonomous Orchestration**: AI agent automatically generates deployment configurations
- **Safety-First Design**: Multi-layer guardrails with budget checks, validation, and approval workflows
- **Real-Time Dashboard**: Live monitoring of deployments, costs, and approvals
- **Enterprise-Grade**: Audit logging, immutable trails, and production-ready infrastructure

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (UI)                      │
│  - Dashboard with KPI Cards                                 │
│  - Deployment Table with Actions Menu                       │
│  - Command Bar with Auto-complete Suggestions               │
│  - Dark/Light Mode Toggle                                   │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API (Lambda Function URL)
┌────────────────────▼────────────────────────────────────────┐
│              FastAPI Orchestrator (AWS Lambda)              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Orchestration Layer                                  │   │
│  │  - Intent Processing                                  │   │
│  │  - Plan Generation                                    │   │
│  │  - Approval Management                                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Service Layer                                        │   │
│  │  - LLM Client (llama-3.1-nemotron-nano-8B-v1)      │   │
│  │  - Retriever Client (NeMo Retriever NIM)            │   │
│  │  - Guardrail Service                                  │   │
│  │  - SageMaker Tool                                     │   │
│  │  - Audit Logger                                       │   │
│  │  - Cost Service (AWS Cost Explorer)                  │   │
│  │  - Deployment Status Service                         │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼────┐ ┌─────▼─────┐ ┌───▼────────┐
│ DynamoDB   │ │ SageMaker  │ │ AWS Cost   │
│ - Plans    │ │ - Models   │ │ Explorer   │
│ - Approvals│ │ - Endpoints│ │ - GPU Spend│
│ - Audit    │ │            │ │            │
└────────────┘ └────────────┘ └────────────┘
```

### Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite (build tool)
- Tailwind CSS + shadcn/ui (styling)
- React Query (data fetching & caching)
- Lucide React (icons)
- Axios (HTTP client)

**Backend:**
- FastAPI (Python web framework)
- AWS Lambda (serverless hosting)
- Pydantic (data validation)
- boto3 (AWS SDK)
- DynamoDB (persistent storage)
- AWS Cost Explorer API (cost metrics)

**Infrastructure:**
- AWS Lambda Function URL (API endpoint)
- AWS S3 + CloudFront (frontend hosting)
- DynamoDB (data persistence)
- CloudTrail (audit trail)

---

## ✨ Features

### 1. **Natural Language Command Interface**

Users can deploy models using conversational commands:

```
"deploy llama-3.1 8B for chatbot-x"
"deploy nemotron nano 8B for customer support bot"
"deploy llama model with budget $20 per hour"
```

**Features:**
- **Auto-complete Suggestions**: 30+ pre-defined command templates
- **Recent Commands**: Remembers last 5 commands in localStorage
- **Smart Filtering**: Filters suggestions as you type
- **Keyboard Navigation**: Arrow keys, Enter, Escape support
- **Environment Selection**: STAGING or PROD toggle

### 2. **Intelligent Orchestration Flow**

When a user submits a command, the system executes:

```
User Command
    ↓
1. Intent Parsing (Natural Language → Structured Request)
    ↓
2. RAG Retrieval (NeMo Retriever NIM)
   - Queries knowledge base for relevant policies/docs
   - Returns top-k evidence snippets
    ↓
3. Plan Generation (LLM - llama-3.1-nemotron-nano-8B-v1)
   - Generates SageMakerDeploymentConfig JSON
   - Includes model_name, endpoint_name, instance_type, etc.
   - Cites evidence from RAG retrieval
    ↓
4. Guardrail Validation (Layer 1)
   - Schema validation (Pydantic)
   - Budget checks
   - Instance count limits (1-4)
   - Cost validation
    ↓
5. Approval Check (HITL - Layer 2)
   - Production deployments → Requires approval
   - Staging deployments → Auto-proceed
    ↓
6. Execution (SageMaker Tool)
   - Creates Model, EndpointConfig, Endpoint
   - Configures AutoRollbackConfiguration
   - Supports dry-run mode (default)
    ↓
7. Audit Logging (Layer 3)
   - Logs to DynamoDB
   - CloudTrail integration (optional)
```

### 3. **Real-Time Dashboard**

#### KPI Cards
- **Active Deployments**: Count and list of currently running deployments
- **Pending Approvals**: Production deployments awaiting human approval
- **Monthly GPU Spend**: Real-time cost tracking from AWS Cost Explorer
- **Trend Indicators**: Percentage change from last month

#### Deployment Table
- **Comprehensive View**: All deployments with full details
- **Status Tracking**: Real-time status updates (deploying → deployed → paused, etc.)
- **Smart Polling**: 5-second intervals for in-progress, 60-second for stable
- **Actions Menu**: Three-dot menu with 4 options per deployment

### 4. **Actions Menu (Per Deployment)**

Each deployment row has an actions menu (⋮) with:

1. **View Details** (Document icon)
   - Opens deployment overview (placeholder for modal)
   - Shows full deployment configuration

2. **Pause** (Pause icon)
   - Temporarily stops deployment
   - Only available for DEPLOYED or DEPLOYING status
   - Updates status to PAUSED

3. **Restart** (Refresh icon)
   - Restarts a paused, failed, or deployed endpoint
   - Triggers redeployment via SageMaker
   - Sets status to DEPLOYING

4. **Delete** (X icon)
   - Soft deletes deployment (marks as DELETED)
   - Filtered from list view
   - Confirmation dialog with custom UI (matches dashboard theme)

### 5. **Command Suggestions System**

**Auto-complete Features:**
- **30+ Pre-defined Commands**: Categorized by use case
- **Recent Commands**: Last 5 commands saved locally
- **Smart Filtering**: Real-time filtering as you type
- **Floating Dropdown**: Appears above input (no clipping)
- **Keyboard Shortcuts**: Full keyboard navigation support

**Command Categories:**
- Basic deployments (6 variations)
- Nemotron deployments (4 variations)
- Budget-constrained (4 variations)
- Use case specific (6 variations)
- Environment-specific (4 variations)
- Instance scaling (3 variations)
- Alternative phrasings (4 variations)

### 6. **Dark Mode Support**

- **Theme Toggle**: Sun/Moon icon in header
- **Persistent**: Saves preference to localStorage
- **System Preference**: Auto-detects OS theme on first visit
- **Consistent Styling**: All components support dark mode
- **No FOUC**: Theme applied immediately on page load

### 7. **Error Handling & User Feedback**

- **Network Errors**: Descriptive messages for CORS/connection issues
- **Validation Errors**: Yellow warning box with detailed error list
- **Success Messages**: Green notification with endpoint name and status
- **Loading States**: Spinners and disabled buttons during processing
- **Error Recovery**: Dialog stays open on error for retry

### 8. **Data Persistence**

- **DynamoDB Storage**: All plans and approvals persisted
- **In-Memory Fallback**: Gracefully degrades if DynamoDB unavailable
- **Auto-Reload**: Loads existing plans from DynamoDB on startup
- **Soft Delete**: Deleted deployments marked but preserved for audit

---

## 🔄 User Flows

### Flow 1: Staging Deployment (No Approval)

```
1. User opens dashboard
   → Dashboard loads, shows KPIs and existing deployments
   
2. User types in command bar: "deploy llama-3.1 8B for chatbot-x"
   → Auto-complete suggestions appear above input
   → User selects suggestion or types manually
   → Environment: STAGING (default)
   
3. User clicks "Send"
   → Command sent to /api/agent/command
   → Button shows "Processing..." with spinner
   → Input disabled during processing
   
4. Backend Processing:
   a. Retriever queries knowledge base → Gets policy docs
   b. LLM generates deployment plan → SageMakerDeploymentConfig
   c. Guardrails validate → Schema + budget checks pass
   d. No approval needed (staging) → Proceeds directly
   e. SageMaker Tool creates endpoint (dry-run by default)
   f. Plan saved to DynamoDB + in-memory store
   
5. Frontend Updates:
   → Success message appears below command bar
   → Shows endpoint name and status: "DEPLOYING"
   → New row appears in deployment table immediately (optimistic update)
   → Status badge: Blue "DEPLOYING"
   
6. Background Execution:
   → Deployment runs asynchronously
   → Status updates: DEPLOYING → DEPLOYED
   → Table auto-refreshes every 5 seconds until complete
   
7. Final State:
   → Status badge changes to green "DEPLOYED"
   → Endpoint name visible in table
   → Can now use Actions menu (Pause, Restart, Delete)
```

### Flow 2: Production Deployment (Requires Approval)

```
1. User changes environment to "PROD"
2. User types: "deploy llama-3.1 8B for chatbot-x"
3. User clicks "Send"

4. Backend Processing:
   a. Same RAG + LLM + Guardrail flow
   b. Approval check: Production → REQUIRES_APPROVAL
   c. Status set to: PENDING_APPROVAL
   d. Approval request created in DynamoDB
   
5. Frontend Updates:
   → Success message: "DEPLOYING • Requires approval"
   → Pending Approvals KPI increases: 0 → 1
   → Table shows status: Yellow "PENDING_APPROVAL"
   
6. Approval Process:
   → Admin reviews via /approvals endpoint (or UI)
   → POST /approve with decision: APPROVED or REJECTED
   
7. If Approved:
   → Status changes to: DEPLOYING
   → Background deployment starts
   → Table updates: DEPLOYING → DEPLOYED
   
8. If Rejected:
   → Status changes to: REJECTED
   → Deployment cancelled
   → Red status badge shown
```

### Flow 3: View Details Action

```
1. User clicks three-dot menu (⋮) on a deployment row
   → Dropdown menu appears (fixed positioning, no clipping)
   → Row highlights to show active state
   
2. User clicks "View Details"
   → Menu closes
   → [Future: Modal opens with full deployment info]
   → Currently logs to console (placeholder)
```

### Flow 4: Pause Deployment

```
1. User clicks Actions menu → "Pause"
   → Menu closes immediately
   
2. Frontend:
   → POST /api/deployments/{plan_id}/pause
   → Button shows loading state
   
3. Backend:
   → Validates status (must be DEPLOYED or DEPLOYING)
   → Updates status to PAUSED
   → Saves to DynamoDB
   
4. Frontend:
   → Table refreshes automatically
   → Status badge changes to gray "PAUSED"
   → Pause button disabled (already paused)
```

### Flow 5: Restart Deployment

```
1. User clicks Actions menu → "Restart"
   → Menu closes
   
2. Backend:
   → Validates status (DEPLOYED, FAILED, or PAUSED allowed)
   → Status → DEPLOYING
   → Triggers execute_deployment() in background
   → Redeploys via SageMaker
   
3. Frontend:
   → Table shows status: "DEPLOYING"
   → Smart polling: Refreshes every 5 seconds
   → On completion: "DEPLOYED"
```

### Flow 6: Delete Deployment

```
1. User clicks Actions menu → "Delete" (red option)
   → Menu closes
   → Custom confirmation dialog appears
   
2. Dialog Features:
   - Dark mode styled
   - AlertTriangle icon (red)
   - Message: "Are you sure you want to delete deployment 'chatbot-x-staging'?"
   - Cancel button (gray)
   - Delete button (red, with loading state)
   
3. User clicks "Delete"
   → DELETE /api/deployments/{plan_id}
   → Button shows spinner: "Processing..."
   → Dialog buttons disabled during request
   
4. Backend:
   → Marks status as DELETED
   → Saves to DynamoDB
   → Plan filtered from /api/deployments response
   
5. Frontend:
   → Dialog closes on success
   → Table refreshes
   → Deployment removed from list
   → Active Deployments count decreases
   
6. On Error:
   → Dialog stays open
   → Error message shown (alert)
   → User can retry or cancel
```

### Flow 7: Command Suggestions

```
1. User clicks command input field
   → Dropdown appears above input (floating)
   → Shows: Recent Commands (if any) + Suggestions
   
2. User starts typing: "deploy"
   → Filtered suggestions appear
   → Only matching commands shown (up to 12)
   
3. User uses arrow keys
   → Highlights different suggestions
   → Enter key selects highlighted option
   
4. User clicks a suggestion
   → Input field auto-fills
   → Dropdown closes
   → Focus returns to input
   
5. User submits command
   → Command saved to recent commands
   → Appears in "Recent Commands" section next time
```

---

## 🔧 Technical Implementation

### Frontend Architecture

#### Component Structure

```
App.tsx
├── ThemeProvider (Context)
├── Header
│   ├── Branding
│   ├── System Status Badge
│   └── Theme Toggle (Sun/Moon)
├── Main Content
│   ├── KPICards
│   │   ├── ActiveDeploymentsCard
│   │   ├── PendingApprovalsCard
│   │   └── MonthlyCostsCard
│   └── DeploymentTable
│       ├── DeploymentTableRow (per deployment)
│       └── DeploymentActionsMenu
│           └── ConfirmDialog (for delete)
└── CommandBar (Footer)
    ├── Environment Selector
    ├── Command Input (with suggestions)
    └── Send Button
```

#### State Management

- **React Query**: Server state (deployments, metrics, costs)
- **React Context**: Theme state (light/dark)
- **Local Storage**: Recent commands, theme preference
- **Optimistic Updates**: Immediate UI updates before server response

#### API Integration

**Base URL Handling:**
- Development: Uses Vite proxy (`/api/*` → Lambda URL)
- Production: Direct Lambda Function URL
- CORS configured for browser access

**Error Handling:**
- Network errors: Descriptive messages
- Validation errors: Structured error display
- Timeout: 30-second timeout with retry capability

### Backend Architecture

#### Service Initialization

All services use **lazy initialization** for Lambda compatibility:

```python
def _ensure_services_initialized():
    """Called at start of each endpoint"""
    global llm_client, retriever_client, guardrail_service, ...
    if retriever_client is None:
        # Initialize all services
```

#### Storage Layer

**DynamoDB Plans Storage:**
- Table: `agentops-deployment-plans`
- Primary Key: `plan_id`
- Stores: DeploymentPlan objects (JSON serialized)
- Auto-loads on startup (syncs to in-memory cache)

**In-Memory Fallback:**
- Used if DynamoDB unavailable
- Data persists during Lambda warm invocations
- Lost on cold starts (expected behavior)

#### Orchestration Flow Details

**Step 1: Intent Processing**
```python
# Parse natural language
intent_request = UserIntentRequest(
    user_id="dashboard-user@agentops.ai",
    intent="deploy llama-3.1 8B for chatbot-x",
    env=Environment.STAGING
)
```

**Step 2: RAG Retrieval**
```python
# Query NeMo Retriever NIM
rag_evidence = retriever_client.retrieve_and_rerank(
    query=intent,
    top_k=3
)
# Returns: [{title, snippet, url, score}, ...]
```

**Step 3: Plan Generation**
```python
# Call LLM with context
deployment_config = llm_client.generate_plan(
    intent=intent,
    evidence=rag_evidence,
    env=env
)
# Returns: SageMakerDeploymentConfig
```

**Step 4: Guardrail Validation**
```python
validation_result = guardrail_service.validate_plan(
    config=deployment_config,
    budget_constraint=constraints.get("budget_usd_per_hour")
)
# Returns: ValidationResult(valid, errors, warnings)
```

**Step 5: Approval Check**
```python
requires_approval = guardrail_service.requires_approval(
    config=deployment_config,
    env=env
)
# Production → True, Staging → False
```

**Step 6: Execution**
```python
# SageMaker deployment (dry-run by default)
result = sage_tool.deploy_model(
    config=deployment_config,
    dry_run=True  # Set EXECUTE=true to actually deploy
)
# Returns: DeploymentResult(success, endpoint_name, ...)
```

**Step 7: Audit Logging**
```python
await audit_logger.log_intent(
    plan_id=plan_id,
    request=intent_request,
    plan=plan,
    validation_result=validation_result
)
# Writes to DynamoDB audit table
```

---

## 📡 API Reference

### Metrics Endpoints

#### `GET /api/metrics/deployments/active`
Returns active (non-deleted) deployments.

**Response:**
```json
{
  "count": 1,
  "deployments": [
    {
      "plan_id": "plan-123",
      "endpoint_name": "chatbot-x-staging",
      "status": "deployed",
      "environment": "staging",
      "instance_type": "ml.m5.large"
    }
  ]
}
```

#### `GET /api/metrics/approvals/pending`
Returns pending approval requests.

**Response:**
```json
{
  "count": 1,
  "approvals": [
    {
      "plan_id": "plan-456",
      "plan": {...},
      "created_at": "2025-11-01T09:33:00Z"
    }
  ]
}
```

#### `GET /api/metrics/costs/monthly`
Returns monthly GPU spend from AWS Cost Explorer.

**Response:**
```json
{
  "amount": 1234.56,
  "currency": "USD",
  "trend": "up",
  "percent_change": 15.5,
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-31"
  }
}
```

### Deployment Endpoints

#### `GET /api/deployments`
Returns all deployment plans (excluding deleted).

**Response:**
```json
{
  "deployments": [
    {
      "plan_id": "plan-123",
      "status": "deployed",
      "user_id": "user@example.com",
      "intent": "deploy llama-3.1 8B for chatbot-x",
      "env": "staging",
      "artifact": {
        "model_name": "llama-3.1-nemotron-nano-8B-v1",
        "endpoint_name": "chatbot-x-staging",
        "instance_type": "ml.m5.large",
        "instance_count": 1,
        "budget_usd_per_hour": 15.0
      },
      "evidence": [...],
      "created_at": "2025-11-01T09:33:00Z",
      "updated_at": "2025-11-01T09:35:00Z"
    }
  ],
  "count": 1
}
```

#### `POST /api/deployments/{plan_id}/pause`
Pauses a deployment.

**Request:** None

**Response:**
```json
{
  "success": true,
  "message": "Deployment plan-123 paused successfully"
}
```

**Status Requirements:** DEPLOYED or DEPLOYING

#### `POST /api/deployments/{plan_id}/restart`
Restarts a deployment.

**Request:** None

**Response:**
```json
{
  "success": true,
  "message": "Deployment plan-123 restarting"
}
```

**Status Requirements:** DEPLOYED, FAILED, or PAUSED

#### `DELETE /api/deployments/{plan_id}`
Deletes a deployment (soft delete).

**Request:** None

**Response:**
```json
{
  "success": true,
  "message": "Deployment plan-123 deleted successfully"
}
```

**Effect:** Status set to DELETED, filtered from list

### Command Endpoints

#### `POST /api/agent/command`
Processes natural language command.

**Request:**
```json
{
  "command": "deploy llama-3.1 8B for chatbot-x",
  "user_id": "dashboard-user@agentops.ai",
  "env": "staging",
  "constraints": {
    "budget_usd_per_hour": 20.0
  }
}
```

**Response (Success):**
```json
{
  "command_id": "plan-789",
  "status": "success",
  "result": {
    "plan_id": "plan-789",
    "status": "deploying",
    "artifact": {
      "endpoint_name": "chatbot-x-staging",
      "instance_type": "ml.m5.large",
      ...
    },
    "requires_approval": false
  }
}
```

**Response (Validation Failed):**
```json
{
  "command_id": "plan-789",
  "status": "validation_failed",
  "result": {
    "plan_id": "plan-789",
    "errors": [
      "instance_count exceeds max allowed (4)",
      "budget_usd_per_hour exceeds limit"
    ]
  }
}
```

### Approval Endpoints

#### `GET /approvals`
Returns pending approval requests.

**Response:**
```json
{
  "approvals": [
    {
      "plan_id": "plan-456",
      "status": "pending_approval",
      "created_at": "2025-11-01T09:33:00Z",
      "plan": {...}
    }
  ]
}
```

#### `POST /approve`
Approves or rejects a deployment plan.

**Request:**
```json
{
  "plan_id": "plan-456",
  "decision": "approved",
  "approver": "admin@example.com",
  "reason": "Meets all requirements"
}
```

**Response:**
```json
{
  "plan_id": "plan-456",
  "status": "approved",
  "message": "Deployment started"
}
```

---

## 🚀 Deployment

### Frontend Deployment

**Build:**
```bash
cd frontend
npm install
npm run build
```

**Deploy to S3/CloudFront:**
```bash
# Windows PowerShell
.\deploy\frontend_deploy.ps1

# Linux/Mac
./deploy/frontend_deploy.sh
```

**Environment Variables:**
- `VITE_API_URL`: Lambda Function URL (for production)

### Backend Deployment

**Package Lambda:**
```bash
cd orchestrator
pip install -r requirements.txt -t .
zip -r lambda_function.zip .
```

**Deploy via AWS CLI:**
```bash
aws lambda update-function-code \
  --function-name agentops-orchestrator \
  --zip-file fileb://lambda_function.zip
```

**Environment Variables:**
- `LLM_ENDPOINT`: SageMaker endpoint for llama-3.1-nemotron-nano-8B-v1
- `RETRIEVER_EMBED_ENDPOINT`: NeMo Retriever embedding endpoint
- `RETRIEVER_RERANK_ENDPOINT`: NeMo Retriever reranking endpoint
- `DYNAMODB_TABLE_NAME`: Audit log table (default: agentops-audit-log)
- `DYNAMODB_PLANS_TABLE_NAME`: Plans storage table (default: agentops-deployment-plans)
- `AWS_REGION`: AWS region (default: us-east-1)
- `EXECUTE`: Set to "true" to enable real deployments (default: dry-run)

### Infrastructure Setup

**DynamoDB Tables:**

1. **Plans Table:**
```bash
aws dynamodb create-table \
  --table-name agentops-deployment-plans \
  --attribute-definitions AttributeName=plan_id,AttributeType=S \
  --key-schema AttributeName=plan_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

2. **Audit Table:**
```bash
aws dynamodb create-table \
  --table-name agentops-audit-log \
  --attribute-definitions AttributeName=plan_id,AttributeType=S AttributeName=timestamp,AttributeType=S \
  --key-schema AttributeName=plan_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

**Lambda Permissions:**
- DynamoDB: Read/Write to tables
- SageMaker: Create models, endpoints, configurations
- Cost Explorer: Read cost data
- CloudWatch Logs: Write logs

---

## 📊 Data Models

### DeploymentPlan (Pydantic)

```python
{
  "plan_id": "uuid-string",
  "status": "deployed" | "deploying" | "pending_approval" | "failed" | "paused" | "deleted",
  "user_id": "user@example.com",
  "intent": "deploy llama-3.1 8B for chatbot-x",
  "env": "staging" | "prod" | "dev",
  "artifact": SageMakerDeploymentConfig,
  "evidence": [RAGEvidence],
  "created_at": "2025-11-01T09:33:00Z",
  "updated_at": "2025-11-01T09:35:00Z",
  "validation_errors": []
}
```

### SageMakerDeploymentConfig

```python
{
  "model_name": "llama-3.1-nemotron-nano-8B-v1",
  "endpoint_name": "chatbot-x-staging",
  "instance_type": "ml.m5.large",
  "instance_count": 1,  # 1-4 allowed
  "rollback_alarms": [],
  "budget_usd_per_hour": 15.0
}
```

---

## 🎨 UI Features in Detail

### Dashboard Components

#### Header
- **Branding**: "AgentOps" logo/title
- **System Status**: "All Systems Operational" badge (green)
- **Theme Toggle**: Sun (light) / Moon (dark) icon button

#### KPI Cards
- **Layout**: 3 cards in row (responsive grid)
- **Styling**: Gradient backgrounds, dark mode support
- **Icons**: Deployment, Clock, Dollar icons
- **Auto-refresh**: 60 seconds (active), 5 minutes (costs)

#### Deployment Table
- **Columns**: Intent, Endpoint, Environment, Instance, Status, Created, Actions
- **Row Highlighting**: Hover effect, active state when menu open
- **Status Badges**: Color-coded (green=deployed, blue=deploying, yellow=pending, red=failed)
- **Smart Polling**: 5s if deploying, 60s if stable

#### Command Bar (Footer)
- **Fixed Position**: Stays at bottom of viewport
- **Input Features**: 
  - Environment dropdown (STAGING/PROD)
  - Auto-complete suggestions (floating above)
  - Clear button (X icon)
  - Loading/success/error indicators
- **Success Message**: Green box with endpoint details
- **Error Display**: Yellow box with validation errors list

### Dark Mode Implementation

- **Theme Provider**: React Context API
- **Persistence**: localStorage key: "theme"
- **System Detection**: Checks `prefers-color-scheme` on first visit
- **Immediate Apply**: Inline script in index.html prevents FOUC
- **Tailwind Classes**: All components use `dark:` variants

---

## 🔒 Security & Safety Features

### Guardrails (Layer 1)

1. **Schema Validation**: Pydantic models enforce structure
2. **Budget Checks**: Validates `budget_usd_per_hour` against limits
3. **Instance Limits**: Enforces 1-4 instance count range
4. **Cost Validation**: Estimates and validates deployment costs

### Human-in-the-Loop (Layer 2)

1. **Approval Queue**: Production deployments require approval
2. **Approval Endpoints**: GET /approvals, POST /approve
3. **Decision Tracking**: Stores approver, timestamp, reason
4. **Rejection Handling**: Updates status to REJECTED

### Audit Trail (Layer 3)

1. **DynamoDB Logging**: All intents, approvals, deployments logged
2. **CloudTrail Integration**: Infrastructure-level audit (optional)
3. **Immutable Records**: Timestamps and full context preserved
4. **Audit Query**: Can retrieve full history per plan_id

---

## 🧪 Testing & Validation

### Test Commands

**Staging (Auto-deploy):**
```bash
curl -X POST https://<lambda-url>/api/agent/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "deploy llama-3.1 8B for chatbot-x",
    "env": "staging",
    "user_id": "test@example.com"
  }'
```

**Production (Requires Approval):**
```bash
curl -X POST https://<lambda-url>/api/agent/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "deploy llama-3.1 8B for chatbot-x production",
    "env": "prod",
    "user_id": "test@example.com"
  }'
```

**Get Deployments:**
```bash
curl https://<lambda-url>/api/deployments
```

### Expected Behaviors

1. **Dry-Run Mode (Default)**: Logs actions but doesn't create real endpoints
2. **Real Deployment**: Set `EXECUTE=true` environment variable
3. **Error Handling**: Graceful degradation if services unavailable
4. **Fallback Behavior**: In-memory storage if DynamoDB unavailable

---

## 📝 Future Enhancements

### Planned Features

1. **View Details Modal**: Full deployment overview with configuration
2. **WebSocket Updates**: Real-time status streaming
3. **Toast Notifications**: Replace alerts with toast system
4. **Deployment History**: Timeline view of status changes
5. **Cost Breakdown**: Per-deployment cost analysis
6. **Multi-User Support**: User authentication and authorization
7. **Webhook Integration**: Slack/Teams notifications for approvals
8. **Rollback Automation**: Automatic rollback on alarms
9. **EKS Support**: Kubernetes deployment option
10. **Multi-Region**: Deploy across AWS regions

---

## 🐛 Known Limitations

1. **Cold Start Latency**: Lambda cold starts may delay first request
2. **In-Memory Data**: Lost on Lambda cold start (mitigated with DynamoDB)
3. **Dry-Run Default**: Must set EXECUTE=true for real deployments
4. **View Details**: Currently placeholder (logs to console)
5. **Error Alerts**: Uses browser `alert()` (to be replaced with toasts)

---

## 📚 Additional Resources

- **README.md**: Quick start guide
- **COMMAND_EXAMPLES.md**: Example commands with explanations
- **NEXT_STEPS_PRIORITIZED.md**: Development roadmap
- **CODEBASE_REVIEW_AND_IMPROVEMENTS.md**: Code review and suggestions

---

## 🎯 Summary

AgentOps is a production-ready, autonomous model deployment system that:

- ✅ Accepts natural language commands
- ✅ Generates deployment plans using AI (LLM + RAG)
- ✅ Validates with multi-layer guardrails
- ✅ Requires approvals for production
- ✅ Executes deployments to SageMaker
- ✅ Provides real-time dashboard monitoring
- ✅ Enables deployment management (pause, restart, delete)
- ✅ Logs all actions for audit
- ✅ Tracks costs in real-time
- ✅ Supports dark/light themes
- ✅ Offers excellent UX with auto-complete and suggestions

The system is designed for hackathon demos but built with production-grade practices: safety-first design, comprehensive logging, error handling, and scalable architecture.

