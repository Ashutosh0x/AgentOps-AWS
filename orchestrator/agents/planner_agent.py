"""Planner Agent - Breaks down user queries into executable subtasks using ReAct pattern."""

import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from orchestrator.models import (
    ExecutionPlan, TaskStep, RAGEvidence, ReasoningChain, ReasoningStep
)
from orchestrator.llm_client import LLMClient
from orchestrator.agent_memory import AgentMemory, MemoryType

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Agent that decomposes user intent into structured execution plan using ReAct pattern."""
    
    def __init__(
        self,
        llm_client: LLMClient = None,
        memory: AgentMemory = None,
        max_iterations: int = 5
    ):
        """Initialize Planner Agent.
        
        Args:
            llm_client: LLM client for plan generation
            memory: Agent memory for learning from past experiences
            max_iterations: Maximum ReAct loop iterations
        """
        self.llm_client = llm_client
        self.memory = memory
        self.max_iterations = max_iterations
        self.agent_name = "planner"
    
    def create_execution_plan(
        self,
        plan_id: str,
        intent: str,
        env: str,
        rag_evidence: List[RAGEvidence],
        constraints: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """Create a multi-step execution plan using ReAct pattern with Chain-of-Thought reasoning.
        
        Args:
            plan_id: Associated deployment plan ID
            intent: User's natural language intent
            env: Target environment (dev/staging/prod)
            rag_evidence: RAG evidence snippets
            constraints: Optional constraints
            
        Returns:
            ExecutionPlan with ordered steps and reasoning chain
        """
        constraints = constraints or {}
        
        # Initialize reasoning chain
        reasoning_chain = ReasoningChain(
            agent_name=self.agent_name,
            context=f"Planning deployment: {intent} for {env} environment"
        )
        
        # ReAct loop: Think → Act → Observe → Reflect
        current_state = {
            "intent": intent,
            "env": env,
            "constraints": constraints,
            "evidence_count": len(rag_evidence)
        }
        
        # Recall similar past experiences
        similar_experiences = []
        if self.memory:
            similar_experiences = self.memory.get_similar_experiences(
                agent_name=self.agent_name,
                current_situation=current_state,
                limit=3
            )
            
            if similar_experiences:
                reasoning_step = ReasoningStep(
                    thought="Checking past similar deployments",
                    reasoning=f"Found {len(similar_experiences)} similar past experiences. Learning from outcomes.",
                    confidence=0.8,
                    evidence=[exp["event"] for exp in similar_experiences[:2]],
                    decision="Use insights from past deployments"
                )
                reasoning_chain.steps.append(reasoning_step)
        
        # Format RAG evidence for context
        evidence_text = "\n".join([
            f"- {ev.title}: {ev.snippet[:200]}" for ev in rag_evidence[:3]
        ])
        
        # ReAct: Think about the planning approach
        thought = self._reason_about_planning(
            intent, env, rag_evidence, constraints, similar_experiences, reasoning_chain
        )
        
        # ReAct: Act - Generate the plan
        steps_data = self._generate_plan_steps(
            intent, env, evidence_text, constraints, thought, reasoning_chain
        )
        
        # ReAct: Observe - Validate the plan makes sense
        validation_result = self._validate_generated_plan(steps_data, reasoning_chain)
        
        # Convert to TaskStep objects with reasoning
        task_steps = []
        for idx, step_data in enumerate(steps_data):
            # Generate reasoning for each step
            step_reasoning = ReasoningStep(
                thought=f"Planning step {idx+1}: {step_data.get('action', '')}",
                reasoning=step_data.get("description", ""),
                confidence=0.85,
                evidence=[ev.snippet[:100] for ev in rag_evidence[:2]],
                decision=step_data.get("action")
            )
            
            step = TaskStep(
                step_id=f"{plan_id}-step-{idx+1}",
                agent_type=step_data.get("agent_type", "executor"),
                action=step_data.get("action", step_data.get("description", "").lower().replace(" ", "_")),
                status="thinking",
                input={"intent": intent, "env": env, "step_index": idx},
                output={},
                timestamp=datetime.utcnow(),
                reasoning_chain=ReasoningChain(
                    agent_name=self.agent_name,
                    context=f"Step {idx+1}: {step_data.get('action')}",
                    steps=[step_reasoning]
                )
            )
            task_steps.append(step)
        
        # Final conclusion
        reasoning_chain.conclusion = f"Created execution plan with {len(task_steps)} steps for {intent}"
        reasoning_chain.overall_confidence = 0.85
        
        execution_plan = ExecutionPlan(
            plan_id=plan_id,
            steps=task_steps,
            created_at=datetime.utcnow(),
            reasoning_chain=reasoning_chain
        )
        
        # Remember this planning session
        if self.memory:
            self.memory.remember(
                agent_name=self.agent_name,
                event=f"Planned deployment: {intent}",
                outcome={
                    "steps_count": len(task_steps),
                    "env": env,
                    "success": True,
                    "plan_id": plan_id
                },
                memory_type=MemoryType.EPISODIC,
                metadata={"intent": intent, "env": env}
            )
        
        return execution_plan
    
    def _reason_about_planning(
        self,
        intent: str,
        env: str,
        rag_evidence: List[RAGEvidence],
        constraints: Dict[str, Any],
        similar_experiences: List[Dict],
        reasoning_chain: ReasoningChain
    ) -> Dict[str, Any]:
        """ReAct: Think step - Reason about how to approach planning."""
        reasoning_step = ReasoningStep(
            thought="Analyzing deployment requirements",
            reasoning=f"Need to plan deployment for '{intent}' in {env} environment. "
                     f"Have {len(rag_evidence)} policy documents and {len(constraints)} constraints.",
            confidence=0.9,
            alternatives=[
                "Simple sequential plan",
                "Parallel execution where possible",
                "Conservative step-by-step approach"
            ],
            evidence=[ev.title for ev in rag_evidence[:3]],
            decision="Use structured sequential plan with validation checkpoints"
        )
        reasoning_chain.steps.append(reasoning_step)
        
        # If we have similar experiences, incorporate learnings
        if similar_experiences:
            lessons = []
            for exp in similar_experiences:
                outcome = exp.get("outcome", {})
                if isinstance(outcome, dict):
                    if outcome.get("success"):
                        lessons.append(f"Success pattern: {exp['event']}")
                    else:
                        lessons.append(f"Failed pattern to avoid: {exp['event']}")
            
            if lessons:
                learning_step = ReasoningStep(
                    thought="Applying lessons from past deployments",
                    reasoning=f"Learned from {len(similar_experiences)} past experiences",
                    confidence=0.75,
                    evidence=lessons[:2],
                    decision="Adjust plan based on historical patterns"
                )
                reasoning_chain.steps.append(learning_step)
        
        return {
            "approach": "structured_sequential",
            "has_constraints": len(constraints) > 0,
            "evidence_count": len(rag_evidence)
        }
    
    def _generate_plan_steps(
        self,
        intent: str,
        env: str,
        evidence_text: str,
        constraints: Dict[str, Any],
        thought: Dict[str, Any],
        reasoning_chain: ReasoningChain
    ) -> List[Dict[str, Any]]:
        """ReAct: Act step - Generate the execution plan steps."""
        # Build system prompt for planning
        system_prompt = """You are a Planning Agent for AgentOps. Your job is to break down a deployment intent into a structured, step-by-step execution plan.

Given a user intent, decompose it into discrete, executable steps. Each step should be:
1. Specific and actionable
2. Sequentially ordered (dependencies clear)
3. Include the agent type responsible (planner, retriever, executor, monitor)

Return a JSON array of steps in this format:
[
  {
    "agent_type": "retriever",
    "action": "retrieve_policies",
    "description": "Retrieve relevant deployment policies from knowledge base"
  },
  {
    "agent_type": "planner",
    "action": "generate_config",
    "description": "Generate SageMaker deployment configuration from intent and policies"
  },
  {
    "agent_type": "executor",
    "action": "validate_plan",
    "description": "Validate deployment plan against guardrails and constraints"
  },
  {
    "agent_type": "executor",
    "action": "create_model",
    "description": "Create SageMaker model artifact"
  },
  {
    "agent_type": "executor",
    "action": "create_endpoint_config",
    "description": "Create SageMaker endpoint configuration"
  },
  {
    "agent_type": "executor",
    "action": "create_endpoint",
    "description": "Create and deploy SageMaker endpoint"
  },
  {
    "agent_type": "monitor",
    "action": "configure_monitoring",
    "description": "Configure Model Monitor and rollback alarms"
  },
  {
    "agent_type": "monitor",
    "action": "verify_deployment",
    "description": "Verify deployment success and health checks"
  }
]

Return ONLY the JSON array, no markdown, no explanation."""
        
        # Build user prompt
        budget_text = f"\nBudget constraint: ${constraints.get('budget_usd_per_hour', '')}/hour" if constraints.get('budget_usd_per_hour') else ""
        
        user_prompt = f"""User Intent: {intent}
Target Environment: {env}

Relevant Context:
{evidence_text}
{budget_text}

Generate a step-by-step execution plan as a JSON array of steps."""
        
        # Add reasoning step for generation
        reasoning_step = ReasoningStep(
            thought="Generating execution plan steps",
            reasoning=f"Using {thought['approach']} approach with {thought['evidence_count']} evidence documents",
            confidence=0.85,
            decision="Generate structured sequential plan"
        )
        reasoning_chain.steps.append(reasoning_step)
        
        # Create steps using LLM or fallback to default plan
        try:
            if self.llm_client and self.llm_client.endpoint_name:
                steps_data = self._generate_steps_via_llm(system_prompt, user_prompt)
            else:
                # Fallback to default execution plan structure
                logger.warning("LLM client not available, using default execution plan")
                steps_data = self._get_default_steps(intent, env)
        except Exception as e:
            logger.warning(f"Failed to generate steps via LLM: {e}. Using default plan.")
            steps_data = self._get_default_steps(intent, env)
        
        return steps_data
    
    def _validate_generated_plan(
        self,
        steps_data: List[Dict[str, Any]],
        reasoning_chain: ReasoningChain
    ) -> Dict[str, Any]:
        """ReAct: Observe step - Validate the generated plan."""
        # Check if plan has required steps
        required_actions = ["validate_plan", "create_model", "create_endpoint"]
        found_actions = [step.get("action", "") for step in steps_data]
        
        missing = [action for action in required_actions if not any(action in fa for fa in found_actions)]
        
        validation_step = ReasoningStep(
            thought="Validating generated plan",
            reasoning=f"Plan has {len(steps_data)} steps. Checking for required actions.",
            confidence=0.9 if not missing else 0.6,
            alternatives=[],
            decision="Plan validated" if not missing else f"Plan missing: {missing}"
        )
        reasoning_chain.steps.append(validation_step)
        
        return {
            "valid": len(missing) == 0,
            "steps_count": len(steps_data),
            "missing_actions": missing
        }
    
    def _generate_steps_via_llm(self, system_prompt: str, user_prompt: str) -> List[Dict[str, Any]]:
        """Generate execution steps using LLM.
        
        Args:
            system_prompt: System prompt for planning
            user_prompt: User prompt with intent
            
        Returns:
            List of step dictionaries
        """
        import boto3
        from botocore.exceptions import ClientError
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        try:
            runtime_client = boto3.client("sagemaker-runtime", region_name=self.llm_client.region)
            response = runtime_client.invoke_endpoint(
                EndpointName=self.llm_client.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            response_body = json.loads(response["Body"].read().decode("utf-8"))
            
            # Extract generated text
            if "choices" in response_body:
                generated_text = response_body["choices"][0]["message"]["content"]
            elif "outputs" in response_body:
                generated_text = response_body["outputs"][0]
            else:
                generated_text = json.dumps(response_body)
            
            # Clean up markdown code blocks
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0].strip()
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON array
            steps_data = json.loads(generated_text)
            if not isinstance(steps_data, list):
                raise ValueError("Expected JSON array of steps")
            
            return steps_data
            
        except (ClientError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error generating steps via LLM: {e}")
            raise
    
    def _get_default_steps(self, intent: str, env: str) -> List[Dict[str, Any]]:
        """Get default execution plan steps (fallback).
        
        Args:
            intent: User intent
            env: Target environment
            
        Returns:
            List of default step dictionaries
        """
        return [
            {
                "agent_type": "retriever",
                "action": "retrieve_policies",
                "description": "Retrieve relevant deployment policies from knowledge base"
            },
            {
                "agent_type": "planner",
                "action": "generate_config",
                "description": "Generate SageMaker deployment configuration from intent and policies"
            },
            {
                "agent_type": "executor",
                "action": "validate_plan",
                "description": "Validate deployment plan against guardrails and constraints"
            },
            {
                "agent_type": "executor",
                "action": "create_model",
                "description": "Create SageMaker model artifact"
            },
            {
                "agent_type": "executor",
                "action": "create_endpoint_config",
                "description": "Create SageMaker endpoint configuration with monitoring"
            },
            {
                "agent_type": "executor",
                "action": "create_endpoint",
                "description": "Create and deploy SageMaker endpoint"
            },
            {
                "agent_type": "monitor",
                "action": "configure_monitoring",
                "description": "Configure Model Monitor and rollback alarms"
            },
            {
                "agent_type": "monitor",
                "action": "verify_deployment",
                "description": "Verify deployment success and perform health checks"
            }
        ]

