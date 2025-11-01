# AgentOps Deployment Policies

## Environment-Specific Instance Type Requirements

**POLICY:** Development models MUST use `ml.m5.large` instance type.
- Rationale: Cost optimization for development workloads
- Exception: None

**POLICY:** Staging models may use `ml.m5.large` or `ml.m5.xlarge` instance types.
- Rationale: Balance between cost and performance for testing
- Exception: Requires approval if instance_count >= 3

**POLICY:** Production models must have `instance_count >= 2` for high availability.
- Rationale: Ensure zero-downtime deployments and fault tolerance
- Exception: None

## Budget Constraints

**POLICY:** Staging environment maximum budget: $15 USD per hour.
- Rationale: Cost control for non-production workloads
- Validation: Guardrail service enforces this limit

**POLICY:** Production environment maximum budget: $50 USD per hour.
- Rationale: Higher budget for production workloads with HA requirements
- Validation: Guardrail service enforces this limit

## Deployment Safety Requirements

**POLICY:** All production deployments require explicit human approval.
- Rationale: Prevent autonomous changes to critical production systems
- Implementation: HITL (Human-in-the-Loop) workflow

**POLICY:** All deployments must configure rollback alarms via AutoRollbackConfiguration.
- Rationale: Enable automatic rollback on model quality degradation
- Required alarms: ModelMonitorAlarm, DataDriftAlarm

## Model Monitoring

**POLICY:** Production endpoints must have Model Monitor configured.
- Rationale: Detect data drift, model quality issues, and bias
- Configuration: Baseline comparison, CloudWatch alarms

## Cost Optimization

**POLICY:** Development and staging workloads should use minimal instance counts.
- Rationale: Reduce infrastructure costs for non-production
- Default: instance_count = 1 for dev/staging

**POLICY:** Instance types must be approved per environment.
- Dev: ml.m5.large only
- Staging: ml.m5.large, ml.m5.xlarge
- Prod: Any approved type (requires approval for >$30/hour)

## Security Requirements

**POLICY:** All deployment plans must be audited and logged to DynamoDB.
- Rationale: Compliance and audit trail requirements
- Implementation: CloudTrail Data Events → S3 Object Lock

**POLICY:** All model artifacts must be stored in encrypted S3 buckets.
- Rationale: Data protection and compliance
- Encryption: SSE-S3 or SSE-KMS

