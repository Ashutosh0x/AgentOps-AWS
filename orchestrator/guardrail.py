"""Guardrail service for validating deployment plans."""

import logging
import os
import json
from typing import Dict, Any, List

from orchestrator.models import SageMakerDeploymentConfig, ValidationResult, Environment

logger = logging.getLogger(__name__)


# Instance type pricing (override via env JSON; in production, use AWS Pricing API)
DEFAULT_INSTANCE_PRICING = {
    "ml.m5.large": 0.115,  # USD per hour
    "ml.m5.xlarge": 0.230,
    "ml.m5.2xlarge": 0.460,
    "ml.g5.xlarge": 1.408,
    "ml.g5.2xlarge": 2.816,
    "ml.g5.4xlarge": 5.632,
    "ml.g5.12xlarge": 16.896,
    "ml.p5.48xlarge": 71.296,
}

# Environment-specific policies (override via env JSON)
DEFAULT_ENV_POLICIES = {
    Environment.DEV: {
        "required_instance_type": ["ml.m5.large"],
        "max_budget_usd_per_hour": 15.0,
        "min_instance_count": 1,
        "max_instance_count": 2
    },
    Environment.STAGING: {
        "required_instance_type": ["ml.m5.large", "ml.m5.xlarge"],
        "max_budget_usd_per_hour": 15.0,
        "min_instance_count": 1,
        "max_instance_count": 4
    },
    Environment.PROD: {
        "required_instance_type": None,  # Any type allowed
        "max_budget_usd_per_hour": 50.0,
        "min_instance_count": 2,  # HA requirement
        "max_instance_count": 4
    }
}


class GuardrailService:
    """Service for validating deployment plans against policies and constraints."""

    def __init__(self):
        """Initialize guardrail service."""
        pricing_json = os.getenv("INSTANCE_PRICING_JSON")
        policies_json = os.getenv("ENV_POLICIES_JSON")
        self.cost_source = os.getenv("COST_SOURCE", "env").lower()  # env | aws_pricing
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self._pricing_cache: Dict[str, float] = {}

        try:
            self.instance_pricing = json.loads(pricing_json) if pricing_json else DEFAULT_INSTANCE_PRICING.copy()
        except Exception as e:
            logger.warning(f"Failed to parse INSTANCE_PRICING_JSON: {e}, using defaults")
            self.instance_pricing = DEFAULT_INSTANCE_PRICING.copy()

        try:
            raw_policies = json.loads(policies_json) if policies_json else DEFAULT_ENV_POLICIES.copy()
            if isinstance(raw_policies, dict) and all(isinstance(k, str) for k in raw_policies.keys()):
                mapped = {}
                for k, v in raw_policies.items():
                    try:
                        mapped[Environment(k)] = v
                    except Exception:
                        mapped[k] = v
                self.env_policies = mapped
            else:
                self.env_policies = raw_policies
        except Exception as e:
            logger.warning(f"Failed to parse ENV_POLICIES_JSON: {e}, using defaults")
            self.env_policies = DEFAULT_ENV_POLICIES.copy()

    def _get_price_from_cache_or_source(self, instance_type: str) -> float:
        # Cache first
        if instance_type in self._pricing_cache:
            return self._pricing_cache[instance_type]
        # Env source
        if self.cost_source != "aws_pricing":
            price = self.instance_pricing.get(instance_type, 1.0)
            self._pricing_cache[instance_type] = price
            return price
        # AWS Pricing API
        try:
            import boto3
            pricing = boto3.client('pricing', region_name='us-east-1')
            resp = pricing.get_products(
                ServiceCode='AmazonSageMaker',
                Filters=[
                    { 'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type },
                    { 'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(self.aws_region) },
                    { 'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'OnDemand' },
                ],
                MaxResults=1,
            )
            price = self._parse_price(resp)
            if price:
                self._pricing_cache[instance_type] = price
                return price
        except Exception as e:
            logger.warning(f"AWS Pricing lookup failed for {instance_type}: {e}; falling back to env pricing")
        return self.instance_pricing.get(instance_type, 1.0)

    @staticmethod
    def _region_to_location(region: str) -> str:
        # Minimal mapping; extend as needed
        mapping = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-2': 'US West (Oregon)',
        }
        return mapping.get(region, 'US East (N. Virginia)')

    @staticmethod
    def _parse_price(resp: Any) -> float:
        try:
            import json as _json
            for p in resp.get('PriceList', []):
                data = _json.loads(p)
                terms = data.get('terms', {}).get('OnDemand', {})
                for _, term in terms.items():
                    price_dimensions = term.get('priceDimensions', {})
                    for _, dim in price_dimensions.items():
                        usd = dim.get('pricePerUnit', {}).get('USD')
                        if usd:
                            return float(usd)
        except Exception:
            return None
        return None
    
    def estimate_cost(self, config: SageMakerDeploymentConfig) -> float:
        """Estimate hourly cost for deployment configuration.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Estimated hourly cost in USD
        """
        base_price = self._get_price_from_cache_or_source(config.instance_type)
        return base_price * config.instance_count
    
    def validate_plan(
        self,
        config: SageMakerDeploymentConfig,
        env: Environment,
        user_constraints: Dict[str, Any] = None
    ) -> ValidationResult:
        """Validate deployment plan against guardrails.
        
        Args:
            config: Deployment configuration to validate
            env: Target environment
            user_constraints: Optional user-provided constraints
            
        Returns:
            ValidationResult with validation status and errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []
        user_constraints = user_constraints or {}
        
        # Get environment-specific policies
        env_policy = self.env_policies.get(env, {})
        
        # 1. Schema validation (already done by Pydantic, but check boundaries)
        if config.instance_count < 1 or config.instance_count > 4:
            errors.append(f"instance_count must be between 1 and 4, got {config.instance_count}")
        
        if config.budget_usd_per_hour <= 0:
            errors.append(f"budget_usd_per_hour must be positive, got {config.budget_usd_per_hour}")
        
        # 2. Instance type validation
        if env_policy.get("required_instance_type"):
            allowed_types = env_policy["required_instance_type"]
            if config.instance_type not in allowed_types:
                errors.append(
                    f"Environment {env.value} requires instance types: {allowed_types}, "
                    f"got {config.instance_type}"
                )
        
        # 3. Instance count validation
        min_instances = env_policy.get("min_instance_count", 1)
        max_instances = env_policy.get("max_instance_count", 4)
        
        if config.instance_count < min_instances:
            errors.append(
                f"Environment {env.value} requires minimum {min_instances} instances, "
                f"got {config.instance_count}"
            )
        
        if config.instance_count > max_instances:
            errors.append(
                f"Environment {env.value} allows maximum {max_instances} instances, "
                f"got {config.instance_count}"
            )
        
        # 4. Budget validation
        estimated_cost = self.estimate_cost(config)
        
        # Check against environment policy
        env_max_budget = env_policy.get("max_budget_usd_per_hour")
        if env_max_budget and estimated_cost > env_max_budget:
            errors.append(
                f"Estimated cost ${estimated_cost:.2f}/hour exceeds environment max budget "
                f"${env_max_budget}/hour"
            )
        
        # Check against user constraints
        user_max_budget = user_constraints.get("budget_usd_per_hour")
        if user_max_budget:
            if estimated_cost > user_max_budget:
                errors.append(
                    f"Estimated cost ${estimated_cost:.2f}/hour exceeds user constraint "
                    f"${user_max_budget}/hour"
                )
            elif estimated_cost > user_max_budget * 0.8:
                warnings.append(
                    f"Estimated cost ${estimated_cost:.2f}/hour is close to budget limit "
                    f"${user_max_budget}/hour"
                )
        
        # Check against config budget
        if estimated_cost > config.budget_usd_per_hour:
            errors.append(
                f"Estimated cost ${estimated_cost:.2f}/hour exceeds configured budget "
                f"${config.budget_usd_per_hour}/hour"
            )
        
        # 5. Instance type cost warning
        if config.instance_type not in self.instance_pricing:
            warnings.append(
                f"Unknown instance type {config.instance_type}, cost estimation may be inaccurate"
            )
        
        # 6. Autoscaling validation
        if config.autoscaling_min > config.autoscaling_max:
            errors.append(
                f"autoscaling_min ({config.autoscaling_min}) must be <= "
                f"autoscaling_max ({config.autoscaling_max})"
            )
        
        if config.autoscaling_max > 8:
            errors.append("autoscaling_max must be <= 8")
        
        # 7. Production-specific validations
        if env == Environment.PROD:
            if not config.rollback_alarms:
                warnings.append("Production deployments should have rollback alarms configured")
            
            if config.instance_count < 2:
                errors.append("Production deployments require instance_count >= 2 for HA")
        
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings
        )
    
    def requires_approval(self, config: SageMakerDeploymentConfig, env: Environment) -> bool:
        """Determine if deployment requires human approval.
        
        Args:
            config: Deployment configuration
            env: Target environment
            
        Returns:
            True if approval is required
        """
        # Production always requires approval
        if env == Environment.PROD:
            return True
        
        # High-cost deployments require approval
        estimated_cost = self.estimate_cost(config)
        if estimated_cost > 20.0:  # $20/hour threshold
            return True
        
        # Multiple instances in staging might require approval
        if env == Environment.STAGING and config.instance_count >= 3:
            return True
        
        return False

