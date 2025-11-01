# AWS Security Policies & Best Practices

## IAM Policy Best Practices

**POLICY:** All IAM policies must follow the principle of least privilege.
- Rationale: Minimize attack surface and reduce risk of privilege escalation
- Implementation: Grant only the minimum permissions required for specific tasks
- Validation: Policies should be reviewed for wildcard permissions (*) and overly broad actions

**POLICY:** Production IAM roles must use condition keys for additional security controls.
- Rationale: Add context-based access control (IP restrictions, time windows, MFA)
- Example: `"Condition": {"IpAddress": {"aws:SourceIp": "10.0.0.0/8"}}`
- Required for: Production deployments, sensitive data access

**POLICY:** IAM policies must explicitly deny public access to sensitive resources.
- Rationale: Prevent accidental public exposure
- Implementation: Use explicit Deny statements with `"Effect": "Deny"` for public principals
- Applies to: S3 buckets, SageMaker endpoints, Lambda functions

## S3 Security Requirements

**POLICY:** S3 buckets containing model artifacts must have encryption at rest enabled.
- Rationale: Protect intellectual property and comply with data protection regulations
- Implementation: Use SSE-S3 (default) or SSE-KMS for production workloads
- Validation: Bucket encryption must be verified before storing sensitive artifacts

**POLICY:** S3 buckets must have public access blocked by default.
- Rationale: Prevent accidental data exposure
- Implementation: Block all public access, use bucket policies for specific access needs
- Exception: Public datasets explicitly approved for research purposes

**POLICY:** S3 bucket versioning must be enabled for production model artifacts.
- Rationale: Enable recovery from accidental deletions or corruptions
- Implementation: Enable versioning via bucket configuration
- Applies to: Production model storage, critical data buckets

## VPC Security Requirements

**POLICY:** SageMaker endpoints in production must be deployed within VPC.
- Rationale: Network isolation and security group-based access control
- Implementation: Configure VPC endpoints and security groups with least-privilege rules
- Required for: Production deployments handling sensitive data

**POLICY:** Security groups must use explicit deny rules for unknown traffic.
- Rationale: Default-deny approach for network security
- Implementation: Explicitly allow required ports/protocols, deny all others
- Example: Allow HTTPS (443) for SageMaker inference, deny all other inbound traffic

## Model Deployment Security

**POLICY:** Production model endpoints must use authentication and authorization.
- Rationale: Prevent unauthorized access to inference endpoints
- Implementation: Use IAM-based endpoint authorization or API Gateway with Cognito
- Applies to: All production SageMaker endpoints

**POLICY:** Model artifacts must be signed and verified before deployment.
- Rationale: Ensure model integrity and prevent tampering
- Implementation: Use AWS Signer for model signing, verify signatures on deployment
- Required for: Production models, models handling sensitive data

## Cost & Resource Security

**POLICY:** Budget alerts must be configured for all production deployments.
- Rationale: Detect and prevent cost overruns from compromised or misconfigured resources
- Implementation: CloudWatch Billing Alarms set at 80% and 100% of budget thresholds
- Notification: SNS topics for DevOps and finance teams

**POLICY:** Unused or idle SageMaker endpoints must be automatically stopped after 24 hours of inactivity.
- Rationale: Reduce costs and attack surface of unused resources
- Implementation: CloudWatch Events + Lambda function to monitor endpoint invocation metrics
- Exception: Endpoints explicitly marked as "always-on" for critical workloads

