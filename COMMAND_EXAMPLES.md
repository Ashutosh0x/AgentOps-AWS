# Command Examples for AgentOps Dashboard

## How to Use the Command Bar

The command bar accepts natural language commands that describe what you want to deploy. The system will:
1. Parse your command
2. Generate a deployment plan
3. Validate it with guardrails
4. Deploy (or request approval for production)

## ✅ Example Commands to Try

### Basic Staging Deployments

```
deploy llama-3.1 8B for chatbot-x
```

**Expected Result:**
- Creates deployment plan for `chatbot-x-staging` endpoint
- Uses `ml.m5.large` instance (staging default)
- Auto-deploys immediately (no approval needed)

---

```
deploy llama-3.1 8B model for customer support bot
```

**Expected Result:**
- Creates deployment plan for customer support bot
- Generates appropriate endpoint name
- Deploys to staging automatically

---

```
deploy nemotron nano 8B for testing environment
```

**Expected Result:**
- Creates deployment for testing
- Uses staging environment defaults
- Deploys automatically

---

### Production Deployments (Requires Approval)

```
deploy llama-3.1 8B for chatbot-x production
```

**Expected Result:**
- Creates production deployment plan
- Uses `ml.g5.12xlarge` instance (production default)
- Status: `PENDING_APPROVAL`
- Appears in "Pending Approvals" counter
- Requires manual approval via `/approve` endpoint

---

```
deploy llama-3.1 8B for production chatbot with 2 instances
```

**Expected Result:**
- Production deployment
- 2 instances configured
- Requires approval before deployment

---

### With Budget Constraints

```
deploy llama-3.1 8B for chatbot-x with budget $20 per hour
```

**Expected Result:**
- Creates deployment with budget constraint
- Validated against guardrails
- Deploys if within limits

---

### Multiple Variations

Try these natural language variations:

1. **Simple:**
   ```
   deploy llama model for chatbot
   ```

2. **Detailed:**
   ```
   deploy llama-3.1-nemotron-nano-8B-v1 for production chatbot-x application
   ```

3. **With Context:**
   ```
   deploy llama 8B model for customer service chatbot in staging
   ```

4. **Casual:**
   ```
   set up llama model for my chatbot
   ```

## 🎯 What Happens After You Send a Command

### For Staging Deployments:
1. ✅ Command appears immediately in table
2. ✅ Status shows "DEPLOYING"
3. ✅ Status updates to "DEPLOYED" when complete
4. ✅ Active deployments counter increases
5. ✅ Success message shows endpoint name

### For Production Deployments:
1. ✅ Command appears in table with "PENDING_APPROVAL" status
2. ⚠️ Pending Approvals counter increases
3. ⚠️ Deployment waits for approval
4. ✅ After approval, status changes to "DEPLOYING"
5. ✅ Then updates to "DEPLOYED"

## 📊 What You'll See in the Dashboard

### KPI Cards:
- **Active Deployments**: Count of deployments with status "deployed" or "deploying"
- **Pending Approvals**: Count of plans waiting for approval
- **Monthly GPU Spend**: Cost metrics (may show mock data if Cost Explorer not configured)

### Deployment Table:
Shows all deployments with:
- Intent (your command)
- Endpoint name
- Environment (STAGING/PROD)
- Instance type and count
- Status badge (color-coded)
- Creation timestamp

## 🔍 Testing Different Scenarios

### Test 1: Quick Staging Deploy
```
deploy llama-3.1 8B for chatbot-x
```
**Select:** STAGING  
**Expected:** Immediate deployment, appears in table right away

### Test 2: Production with Approval
```
deploy llama-3.1 8B for production chatbot
```
**Select:** PROD  
**Expected:** Shows "PENDING_APPROVAL", approval counter increases

### Test 3: Multiple Deployments
Send multiple commands quickly:
```
deploy model A for service 1
deploy model B for service 2
deploy model C for service 3
```
**Expected:** All appear in table, can track multiple deployments

## 💡 Pro Tips

1. **Be Descriptive**: More details help the system generate better plans
   - ✅ Good: "deploy llama-3.1 8B for customer support chatbot"
   - ⚠️ Too vague: "deploy model"

2. **Specify Environment**: Use "staging" or "production" in command if needed
   - The dropdown also sets the environment

3. **Check Status**: Watch the status badge in the table
   - 🟡 DEPLOYING - In progress
   - 🟢 DEPLOYED - Success
   - 🟠 PENDING_APPROVAL - Waiting for approval
   - 🔴 FAILED - Error occurred

4. **Refresh Automatically**: Table auto-refreshes every 5 seconds during deployments

## 🚨 Troubleshooting

**Command doesn't appear in table?**
- Check browser console for errors
- Verify API is accessible (proxy configured)
- Refresh the page

**Status stuck on "DEPLOYING"?**
- Check Lambda logs in CloudWatch
- Verify SageMaker tool is configured
- May be in dry-run mode (check `EXECUTE` env var)

**Production deployment not showing approval?**
- Check if `requires_approval` logic is triggered
- Verify guardrail service is working
- Check pending approvals endpoint: `/api/metrics/approvals/pending`

## 📝 Command Format

The system accepts natural language, but here's what it's looking for:

**Pattern:**
```
deploy [MODEL] for [PURPOSE] [ENVIRONMENT] [CONSTRAINTS]
```

**Examples:**
- `deploy llama-3.1 8B for chatbot-x staging`
- `deploy nemotron nano for testing with budget $15/hour`
- `deploy model for production app`

The system is flexible - it will parse and understand your intent!

