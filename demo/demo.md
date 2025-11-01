# AgentOps Demo Recording Instructions

## Demo Script Timeline (3 minutes)

### 0:00 - 0:10: Introduction
- Title card: "AgentOps: Autonomous, Safety-First MLOps"
- Brief intro: "Demonstrating autonomous model deployment with three-layer safety framework"

### 0:10 - 0:30: Staging Deployment (Automatic)
1. Show terminal/UI
2. Run: `curl -X POST http://localhost:8000/intent ...` (staging environment)
3. Show response: plan generated, validated, deployed automatically
4. Highlight: No approval needed for staging

### 0:30 - 0:55: RAG Grounding & Plan Generation
1. Show RAG evidence snippets (policy documents retrieved)
2. Show generated JSON plan (SageMakerDeploymentConfig)
3. Highlight: Plan grounded in policy documents
4. Show guardrail validation passing

### 0:55 - 1:20: Production Approval Flow (HITL)
1. Run production intent request
2. Show: Status = "pending_approval"
3. Open approval UI: `http://localhost:8000/approvals-ui`
4. Show pending approval card with plan details
5. Click "Approve" button
6. Show: Deployment proceeds after approval

### 1:20 - 1:40: Deployment Execution
1. Show deployment logs (dry-run mode)
2. Highlight: AutoRollbackConfiguration configured
3. Show: Model Monitor alarms configured
4. Show: DynamoDB audit log entry

### 1:40 - 2:10: Rollback Simulation
1. Simulate CloudWatch alarm trigger
2. Show: AutoRollbackConfiguration detecting alarm
3. Show: Automatic rollback to previous version
4. Highlight: Zero-touch safety mechanism

### 2:10 - 2:40: Audit Trail
1. Show DynamoDB audit log entries
2. Show CloudTrail logs (if configured)
3. Highlight: Immutable audit trail with S3 Object Lock
4. Show: Full decision tracking and transparency

### 2:40 - 3:00: Wrap-up
- Summary of safety layers:
  - Layer 1: Guardrails (validation)
  - Layer 2: HITL (approval)
  - Layer 3: Audit (logging)
- Show architecture diagram
- Call to action: Try it yourself

## Recording Tips

1. **Screen Setup**: 
   - Terminal on left (showing API calls)
   - Browser on right (showing approval UI)
   - Keep terminal font readable (14-16px)

2. **Audio**: 
   - Clear narration explaining each step
   - Pause briefly after each major action

3. **Highlights**:
   - Use cursor to point at important parts
   - Zoom in on JSON responses
   - Show RAG evidence clearly

4. **Errors**: 
   - If something fails, show the error handling
   - Demonstrate resilience

5. **Editing**:
   - Keep transitions smooth
   - Remove long waits/pauses
   - Add captions for key points

## Pre-Recording Checklist

- [ ] Orchestrator running and accessible
- [ ] Policy documents uploaded to retriever
- [ ] DynamoDB table created (optional for demo)
- [ ] Browser ready with approval UI
- [ ] Terminal with demo commands ready
- [ ] Screen recording software configured
- [ ] Audio levels tested

