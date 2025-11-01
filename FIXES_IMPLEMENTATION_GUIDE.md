# Fixes Implementation Guide

## Quick Reference: What to Fix & How

### 🚨 Critical Fix #1: Data Persistence (RECOMMENDED)

**Problem**: Deployments lost on Lambda cold start

**Solution**: Store plans in DynamoDB instead of memory

**Implementation Steps**:

1. **Create Storage Service** (`orchestrator/storage.py`):
```python
import boto3
from typing import Dict, Optional, List
from orchestrator.models import DeploymentPlan, ApprovalRequest
import json
from datetime import datetime

class PlanStorage:
    def __init__(self, table_name: str = None):
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "agentops-audit-log")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
    
    def save_plan(self, plan: DeploymentPlan):
        """Save deployment plan to DynamoDB."""
        item = {
            "plan_id": plan.plan_id,
            "PK": f"PLAN#{plan.plan_id}",
            "SK": f"METADATA#{plan.plan_id}",
            "status": plan.status.value,
            "user_id": plan.user_id,
            "intent": plan.intent,
            "env": plan.env.value,
            "artifact": json.dumps(plan.artifact.dict()),
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "data": json.dumps(plan.dict())  # Full plan as JSON
        }
        self.table.put_item(Item=item)
    
    def get_plan(self, plan_id: str) -> Optional[DeploymentPlan]:
        """Get deployment plan from DynamoDB."""
        response = self.table.get_item(
            Key={"PK": f"PLAN#{plan_id}", "SK": f"METADATA#{plan_id}"}
        )
        if "Item" in response:
            return json.loads(response["Item"]["data"])
        return None
    
    def list_plans(self) -> List[Dict]:
        """List all deployment plans."""
        # Use GSI or scan (for MVP, scan is fine)
        response = self.table.scan(
            FilterExpression="begins_with(PK, :pk)",
            ExpressionAttributeValues={":pk": "PLAN#"}
        )
        return [json.loads(item["data"]) for item in response.get("Items", [])]
```

2. **Update main.py**:
   - Replace `plans_store[plan_id] = plan` with `storage.save_plan(plan)`
   - Replace `plans_store.get(plan_id)` with `storage.get_plan(plan_id)`
   - Update `/api/deployments` to use `storage.list_plans()`

**Time**: 2-3 hours  
**Priority**: HIGH (judges will test, data shouldn't disappear)

---

### ✅ Quick Fix #2: Error Display (IMPLEMENTED)

**Status**: ✅ **ALREADY FIXED** in latest update

**What Was Done**:
- Added validation error display
- Shows error details from API response
- Better error formatting

---

### 🎯 Hackathon Submission Tasks

#### Task 1: Record Demo Video

**What to Show** (2-3 minutes):
1. Open dashboard
2. Show KPIs (Active Deployments, Pending Approvals, Costs)
3. Submit command: "deploy llama-3.1 8B for chatbot-x"
4. Show deployment appearing in table
5. Toggle dark mode
6. Show production deployment requiring approval
7. Show success message

**Tools**: 
- Screen recording: OBS, Loom, QuickTime
- Edit: iMovie, Windows Video Editor, or online tools

**Time**: 30-60 minutes

---

#### Task 2: Push to GitHub

```bash
# Initialize repo (if not done)
git init
git add .
git commit -m "AgentOps MVP - Hackathon Submission"

# Create GitHub repo, then:
git remote add origin https://github.com/yourusername/agentops.git
git branch -M main
git push -u origin main
```

**Update README**:
- Add Lambda Function URL
- Add demo video link
- Add screenshots
- Update quickstart with live URL

**Time**: 15 minutes

---

#### Task 3: Final Testing

**Checklist**:
```bash
# 1. Test root endpoint
curl https://your-lambda-url/

# 2. Test command endpoint
curl -X POST https://your-lambda-url/api/agent/command \
  -H "Content-Type: application/json" \
  -d '{"command":"deploy llama-3.1 8B for test","env":"staging"}'

# 3. Test deployments endpoint
curl https://your-lambda-url/api/deployments

# 4. Test frontend locally
cd frontend
npm run dev
# Open browser, test all features
```

**Time**: 20 minutes

---

## 📊 Priority Decision Matrix

### Must Do (Before Submission):
1. ✅ **Record demo video** - Required by hackathon
2. ✅ **Push to GitHub** - Required submission format
3. ✅ **Final testing** - Ensure nothing broke
4. ⚠️ **Data persistence** - If judges test extensively

### Should Do (If 2-3 hours available):
5. **Error display** - ✅ Already done!
6. **Deployment details modal** - Nice UX polish

### Nice to Have (Post-hackathon):
7. Status animations
8. Toast notifications
9. Command history
10. Real-time WebSocket updates

---

## 🎯 Recommended Action Plan

### Today (1 hour):
- [ ] Record demo video
- [ ] Push to GitHub
- [ ] Final testing
- [ ] Update README

### Tomorrow (if time):
- [ ] Implement data persistence (2-3 hours)
- [ ] Add deployment details modal (1-2 hours)

### Total Time to Submit: ~1 hour minimum

---

## ✅ Current Status: READY FOR DEMO

**What Works:**
- ✅ All endpoints functional
- ✅ Frontend dashboard complete
- ✅ Command processing works
- ✅ Deployment tracking works
- ✅ Dark mode works
- ✅ Error handling improved
- ✅ Optimistic UI updates

**What's Missing:**
- ⚠️ Data persistence (DynamoDB) - Important but not blocking
- ⚠️ Demo video - Must do
- ⚠️ GitHub repo - Must do

**Verdict**: **Ready to submit!** Focus on demo video and GitHub first, then data persistence if time permits.

