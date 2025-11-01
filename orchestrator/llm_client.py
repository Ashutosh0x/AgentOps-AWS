"""LLM client for llama-3.1-nemotron-nano-8B-v1 NIM on SageMaker."""

import json
import os
import logging
from typing import List, Dict, Any

import boto3
from botocore.exceptions import ClientError

from orchestrator.models import SageMakerDeploymentConfig, RAGEvidence

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with llama-3.1-nemotron-nano-8B-v1 NIM on SageMaker."""

    def __init__(self, endpoint_name: str = None, region: str = None):
        """Initialize LLM client.
        
        Args:
            endpoint_name: SageMaker endpoint name (defaults to LLM_ENDPOINT env var)
            region: AWS region (defaults to AWS_REGION env var)
        """
        self.endpoint_name = endpoint_name or os.getenv("LLM_ENDPOINT")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        if not self.endpoint_name:
            raise ValueError("LLM_ENDPOINT environment variable or endpoint_name must be provided")
        
        self.runtime_client = boto3.client("sagemaker-runtime", region_name=self.region)
        
    def generate_plan(
        self,
        intent: str,
        env: str,
        rag_evidence: List[RAGEvidence],
        constraints: Dict[str, Any] = None
    ) -> SageMakerDeploymentConfig:
        """Generate deployment plan from user intent and RAG context.
        
        Args:
            intent: User's natural language intent
            env: Target environment (dev/staging/prod)
            rag_evidence: List of RAG evidence snippets
            constraints: Optional constraints dictionary
            
        Returns:
            SageMakerDeploymentConfig: Validated deployment configuration
            
        Raises:
            ValueError: If LLM response is invalid or cannot be parsed
            ClientError: If SageMaker API call fails
        """
        constraints = constraints or {}
        
        # Format RAG evidence
        evidence_text = "\n".join([
            f"- {ev.title}: {ev.snippet}" for ev in rag_evidence[:3]
        ])
        
        # Build system prompt
        system_prompt = """You are AgentOps Coordinator. Given user intent and RAG docs, produce a valid SageMakerDeploymentConfig JSON that satisfies the Pydantic schema. Always cite top-3 retrieval snippets as "evidence". Do not execute any commands. If policy violation occurs, return {"error": "policy_violation", "details": "..."}.

The JSON must conform to this schema:
{
  "model_name": "string (lowercase, hyphens only)",
  "endpoint_name": "string (lowercase, hyphens only)",
  "instance_type": "string (e.g., ml.m5.large, ml.g5.12xlarge)",
  "instance_count": 1-4,
  "max_payload_mb": 1-1024,
  "autoscaling_min": 1-4,
  "autoscaling_max": 1-8,
  "rollback_alarms": ["array of alarm names"],
  "budget_usd_per_hour": float > 0
}

Important constraints:
- Development models must use ml.m5.large instance type
- Production models must have instance_count >= 2 for high availability
- Staging max budget: $15/hour, Production max budget: $50/hour
"""
        
        # Build user prompt
        budget_constraint = constraints.get("budget_usd_per_hour", "")
        budget_text = f"\nBudget constraint: ${budget_constraint}/hour" if budget_constraint else ""
        
        user_prompt = f"""User Intent: {intent}
Target Environment: {env}

Relevant Policy Documents (RAG Evidence):
{evidence_text}
{budget_text}

Generate a SageMakerDeploymentConfig JSON for this deployment intent. Return ONLY valid JSON, no markdown, no explanation."""
        
        # Prepare request payload
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            # Invoke SageMaker endpoint
            response = self.runtime_client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            # Parse response
            response_body = json.loads(response["Body"].read().decode("utf-8"))
            
            # Extract generated text (adjust based on actual NIM response format)
            if "choices" in response_body:
                generated_text = response_body["choices"][0]["message"]["content"]
            elif "outputs" in response_body:
                generated_text = response_body["outputs"][0]
            elif isinstance(response_body, str):
                generated_text = response_body
            else:
                generated_text = json.dumps(response_body)
            
            # Clean up markdown code blocks if present
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0].strip()
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            try:
                config_dict = json.loads(generated_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{[^{}]*\}', generated_text, re.DOTALL)
                if json_match:
                    config_dict = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from LLM response: {generated_text}")
            
            # Check for error responses
            if "error" in config_dict:
                raise ValueError(f"LLM returned error: {config_dict.get('details', 'Unknown error')}")
            
            # Validate and create Pydantic model
            return SageMakerDeploymentConfig(**config_dict)
            
        except ClientError as e:
            logger.error(f"SageMaker API error: {e}")
            raise
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing LLM response: {e}")
            raise ValueError(f"Failed to parse LLM response: {e}")

