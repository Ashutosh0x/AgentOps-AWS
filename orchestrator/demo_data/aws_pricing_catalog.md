# AWS Pricing Catalog & Cost Optimization

## SageMaker Instance Pricing (us-east-1)

**ml.m5.large**: $0.115/hour
- CPU: 2 vCPUs, RAM: 8 GiB
- Best for: Development, staging, low-traffic inference
- Use case: Testing, small batch jobs, cost-sensitive workloads

**ml.m5.xlarge**: $0.230/hour
- CPU: 4 vCPUs, RAM: 16 GiB
- Best for: Medium-scale inference, staging environments
- Use case: Moderate traffic, parallel processing needs

**ml.m5.2xlarge**: $0.460/hour
- CPU: 8 vCPUs, RAM: 32 GiB
- Best for: Production workloads requiring CPU power
- Use case: High-throughput inference, CPU-intensive models

**ml.g5.xlarge**: $1.408/hour
- GPU: 1x NVIDIA A10G, vCPU: 4, RAM: 16 GiB
- Best for: GPU-accelerated inference, medium-scale models
- Use case: LLM inference, computer vision, recommendation engines

**ml.g5.2xlarge**: $2.816/hour
- GPU: 1x NVIDIA A10G, vCPU: 8, RAM: 32 GiB
- Best for: Large-scale GPU workloads
- Use case: High-throughput LLM inference, large vision models

**ml.g5.4xlarge**: $5.632/hour
- GPU: 1x NVIDIA A10G, vCPU: 16, RAM: 64 GiB
- Best for: Production GPU workloads requiring high memory
- Use case: Large language models (8B+ parameters), complex vision tasks

**ml.g5.12xlarge**: $16.896/hour
- GPU: 4x NVIDIA A10G, vCPU: 48, RAM: 192 GiB
- Best for: Enterprise-scale GPU inference
- Use case: Very large models, multi-model endpoints, batch inference

**ml.p5.48xlarge**: $71.296/hour
- GPU: 8x NVIDIA H100, vCPU: 192, RAM: 2 TB
- Best for: Extreme-scale inference, training workloads
- Use case: Largest models, high-performance computing

## Cost Optimization Strategies

**POLICY:** Development and staging environments must use cost-optimized instance types.
- Recommendation: Use ml.m5.large for dev, ml.m5.xlarge for staging
- Rationale: Balance cost with adequate performance for non-production workloads
- Savings: Up to 90% compared to production GPU instances

**POLICY:** Right-sizing recommendations based on traffic patterns.
- Low traffic (< 100 req/min): ml.m5.large or ml.g5.xlarge
- Medium traffic (100-1000 req/min): ml.m5.xlarge or ml.g5.2xlarge
- High traffic (> 1000 req/min): ml.g5.4xlarge or ml.g5.12xlarge with autoscaling

**POLICY:** Use autoscaling to match demand and reduce costs.
- Implementation: Configure min=1, max=4 instances with target utilization 70%
- Benefits: Scale down during low traffic, scale up for peaks
- Estimated savings: 30-50% compared to fixed instance counts

**POLICY:** Consider spot instances for batch inference workloads.
- Use case: Non-time-critical batch processing, model evaluation
- Savings: Up to 90% discount compared to on-demand pricing
- Trade-off: Potential interruption, requires fault-tolerant workloads

## Cost Monitoring & Budgets

**POLICY:** Set budget alerts at multiple thresholds.
- Warning threshold: 50% of monthly budget
- Critical threshold: 80% of monthly budget
- Hard stop threshold: 100% of monthly budget

**POLICY:** Review and optimize costs monthly.
- Action items: Identify idle endpoints, right-size instances, review autoscaling policies
- Tools: AWS Cost Explorer, Cost Anomaly Detection, Trusted Advisor
- Target: Reduce monthly spend by 20-30% through optimization

