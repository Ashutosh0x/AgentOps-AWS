# AgentOps MVP: Autonomous, Safety-First Model Deployment

A hackathon-ready MVP demonstrating an autonomous, safety-first model deployment flow using NVIDIA NIMs (llama-3.1-nemotron-nano-8B-v1 + NeMo Retriever NIM) on Amazon SageMaker.

## 🎯 Overview

AgentOps is an autonomous MLOps system that:
- **Autonomously plans** deployments using LLM (llama-3.1-nemotron-nano-8B-v1 NIM)
- **Grounded in policy** via Agentic RAG (NeMo Retriever NIM)
- **Validates safely** with three-layer guardrails (validation, approval, audit)
- **Executes securely** on SageMaker with automatic rollback

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   User/HITL │────▶│  Orchestrator    │────▶│  LLM NIM     │
│     UI      │     │   (FastAPI)      │     │ (Coordinator) │
└─────────────┘     └────────┬─────────┘     └──────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ NeMo Retriever   │
                    │ (Embed + Rerank) │
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Guardrails     │
                    │  (Validation)     │
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ SageMaker Tool    │
                    │  (Execution)      │
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  DynamoDB +       │
                    │  CloudTrail       │
                    │  (Audit Log)      │
                    └──────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- AWS Account with $100 promotional credits
- AWS CLI configured (or credentials in environment)
- Terraform (optional, for infrastructure)

### 1. Clone and Setup

```bash
# Setup development environment
bash scripts/setup_dev.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required: AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Required: SageMaker Endpoints (deploy via SageMaker JumpStart)
LLM_ENDPOINT=llama-3.1-nemotron-nano-8b-v1-endpoint
RETRIEVER_EMBED_ENDPOINT=nemo-retriever-embed-endpoint
RETRIEVER_RERANK_ENDPOINT=nemo-retriever-rerank-endpoint

# Optional: DynamoDB (auto-created if not exists)
DYNAMODB_TABLE_NAME=agentops-audit-log

# Safety: Defaults to dry-run mode
EXECUTE=false  # Set to "true" to enable actual deployments
```

### 3. Deploy Infrastructure (Optional)

```bash
cd deploy/terraform
terraform init
terraform apply
```

This creates:
- DynamoDB table for audit logs
- S3 bucket with Object Lock for CloudTrail logs
- CloudTrail trail for DynamoDB data events
- SageMaker execution IAM role

### 4. Deploy NVIDIA NIMs on SageMaker

**Option A: SageMaker JumpStart**
1. Navigate to SageMaker JumpStart in AWS Console
2. Search for "llama-3.1-nemotron-nano-8B-v1"
3. Deploy to endpoint and note the endpoint name
4. Repeat for NeMo Retriever Embedding and Reranking NIMs

**Option B: AWS Marketplace**
1. Subscribe to NVIDIA NIM microservices
2. Deploy via SageMaker
3. Note endpoint names

### 5. Upload Policy Documents

```bash
python scripts/upload_docs.py
```

This ingests sample policies into the retriever for RAG grounding.

### 6. Start Orchestrator

```bash
# Using uvicorn
uvicorn orchestrator.main:app --reload

# Or using Make
make dev

# Or directly
python -m orchestrator.main
```

The orchestrator will start at `http://localhost:8000`

### 7. Run Demo

```bash
# In another terminal
bash demo/demo.sh

# Or using Make
make demo
```

## 📋 API Endpoints

### POST /intent
Submit deployment intent and generate plan.

```json
{
  "user_id": "alice@example.com",
  "intent": "deploy llama-3.1 8B for chatbot-x",
  "env": "staging",
  "constraints": {"budget_usd_per_hour": 15.0}
}
```

Response:
```json
{
  "plan_id": "uuid",
  "status": "deploying" | "pending_approval",
  "artifact": { /* SageMakerDeploymentConfig */ },
  "evidence": [ /* RAG snippets */ ],
  "requires_approval": false
}
```

### GET /approvals
List pending approval requests.

### POST /approve
Approve or reject a deployment plan.

```json
{
  "plan_id": "uuid",
  "approver": "bob@example.com",
  "decision": "approved" | "rejected"
}
```

### GET /plan/{plan_id}
Get deployment plan status and details.

### GET /approvals-ui
Simple HTML UI for approval queue.

## 🛡️ Safety Layers

### Layer 1: Guardrails (Validation)
- Schema validation (Pydantic models)
- Budget constraints (per environment)
- Instance type policies
- Cost estimation and limits

### Layer 2: HITL (Human-in-the-Loop)
- Production deployments require approval
- High-cost deployments require approval
- Simple web UI for approvals
- Timeout and escalation policies

### Layer 3: Audit (Immutable Logging)
- All actions logged to DynamoDB
- CloudTrail Data Events capture DynamoDB writes
- S3 Object Lock for immutability
- Full decision tracking

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/test_schemas.py -v

# Integration tests only
pytest tests/test_orchestrator_flow.py -v

# Or using Make
make test
```

## 📊 Demo Flow

1. **Staging Deployment** (Automatic)
   - User submits intent
   - RAG retrieves policies
   - LLM generates plan
   - Guardrails validate
   - Deploys automatically (dry-run by default)

2. **Production Deployment** (Requires Approval)
   - User submits prod intent
   - Plan generated and validated
   - Requires HITL approval
   - Operator approves via UI
   - Deployment proceeds

3. **Rollback Simulation**
   - CloudWatch alarm triggers
   - AutoRollbackConfiguration activates
   - Automatic rollback to previous version

4. **Audit Trail**
   - All actions in DynamoDB
   - CloudTrail logs to S3
   - Immutable with Object Lock

See [demo/demo.md](demo/demo.md) for recording instructions.

## 💰 Cost Management

The $100 promotional credits cover approximately:
- 24 hours of running two NIM microservices on SageMaker
- Minimal infrastructure (DynamoDB, S3, CloudTrail)

**Cost Optimization:**
- Default to dry-run mode (`EXECUTE=false`)
- Use small instance types for demo (ml.m5.large)
- Shut down endpoints when not testing
- Monitor usage in AWS Cost Explorer

**Important:** Set `EXECUTE=true` only when ready for actual deployments.

## 📁 Project Structure

```
/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── Makefile                  # Make commands
├── orchestrator/            # Main orchestrator code
│   ├── main.py              # FastAPI app
│   ├── llm_client.py       # LLM NIM client
│   ├── retriever_client.py  # NeMo Retriever client
│   ├── guardrail.py         # Validation guardrails
│   ├── sage_tool.py         # SageMaker deployment tool
│   ├── audit.py             # Audit logging
│   ├── models.py            # Pydantic schemas
│   ├── approvals_ui.html    # HITL approval UI
│   └── demo_data/           # Sample policy docs
├── tests/                    # Test suite
├── demo/                     # Demo scripts
├── deploy/terraform/         # Infrastructure as code
├── docs/                     # Documentation
└── scripts/                  # Utility scripts
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | Yes | AWS region |
| `LLM_ENDPOINT` | Yes* | SageMaker endpoint for LLM NIM |
| `RETRIEVER_EMBED_ENDPOINT` | Yes* | SageMaker endpoint for NeMo Retriever Embedding |
| `RETRIEVER_RERANK_ENDPOINT` | Yes* | SageMaker endpoint for NeMo Retriever Reranking |
| `DYNAMODB_TABLE_NAME` | No | DynamoDB table name (default: agentops-audit-log) |
| `EXECUTE` | No | Set to "true" to enable deployments (default: false) |

*Can use mock mode if endpoints not configured

### IAM Permissions

Minimum required permissions:
- SageMaker: `CreateModel`, `CreateEndpointConfig`, `CreateEndpoint`, `Describe*`
- DynamoDB: `PutItem`, `Query`, `Scan`
- S3: `GetObject`, `PutObject` (for model artifacts)
- CloudWatch: `PutMetricData`, `GetMetricStatistics`
- CloudTrail: `DescribeTrails`, `GetTrailStatus` (for setup)

## 🐛 Troubleshooting

### Orchestrator fails to start
- Check Python version (3.11+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check AWS credentials are configured

### LLM/Retriever endpoints not found
- Verify endpoints are deployed and running in SageMaker
- Check endpoint names in `.env` match actual endpoint names
- System will use mock mode if endpoints not configured (for testing)

### DynamoDB table not found
- Table is auto-created if permissions allow
- Or create manually: `aws dynamodb create-table ...`
- Or use Terraform: `cd deploy/terraform && terraform apply`

### Dry-run mode not working
- Verify `EXECUTE=false` in `.env` or environment
- Check logs for `[DRY-RUN]` messages

## 📚 Documentation

- [Architecture](docs/architecture.md) - Detailed architecture and design
- [Runbook](docs/runbook.md) - Operational procedures and troubleshooting
- [Demo Instructions](demo/demo.md) - How to record the demo video

## 🎯 Acceptance Criteria

✅ `scripts/setup_dev.sh` runs successfully, orchestrator starts  
✅ POST /intent returns valid SageMakerDeploymentConfig JSON  
✅ Guardrail validation passes/fails appropriately  
✅ Staging deployments execute in dry-run mode, write DynamoDB audit  
✅ Prod deployments pause for approval; POST /approve proceeds  
✅ `demo/demo.sh` runs end-to-end (dry-run unless EXECUTE=true)  
✅ `pytest tests/` passes all unit and integration tests  

## 🤝 Contributing

This is a hackathon MVP. For production use:
- Add authentication/authorization
- Implement proper error handling and retries
- Add comprehensive monitoring and alerting
- Scale retriever to use OpenSearch Serverless
- Implement EKS path as alternative to SageMaker

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- NVIDIA for NIM microservices
- AWS for SageMaker infrastructure
- Hackathon organizers for the challenge

---

**Built for AWS & NVIDIA Hackathon 2024**
