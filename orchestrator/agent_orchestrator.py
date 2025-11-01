"""Agent Orchestrator - Coordinates multi-agent workflow."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from typing import Optional
from orchestrator.models import (
    ExecutionPlan, TaskStep, ExecutionResult, MonitoringResult,
    SageMakerDeploymentConfig, RAGEvidence, ReasoningChain, ReasoningStep
)
from orchestrator.agents.planner_agent import PlannerAgent
from orchestrator.agents.executor_agent import ExecutorAgent
from orchestrator.agents.monitoring_agent import MonitoringAgent
from orchestrator.retriever_client import RetrieverClient

logger = logging.getLogger(__name__)

# Forward reference for AgentMemory to avoid circular imports
try:
    from orchestrator.agent_memory import AgentMemory
except ImportError:
    AgentMemory = None  # Type: ignore


class AgentOrchestrator:
    """Orchestrates multi-agent workflow for deployment execution."""
    
    def __init__(
        self,
        planner_agent: PlannerAgent = None,
        executor_agent: ExecutorAgent = None,
        monitoring_agent: MonitoringAgent = None,
        retriever_client: RetrieverClient = None,
        agent_memory = None
    ):
        """Initialize Agent Orchestrator.
        
        Args:
            planner_agent: Planner agent instance
            executor_agent: Executor agent instance
            monitoring_agent: Monitoring agent instance
            retriever_client: Retriever client for RAG (for iterative retrieval)
            agent_memory: Agent memory system for learning
        """
        self.planner_agent = planner_agent or PlannerAgent()
        self.executor_agent = executor_agent or ExecutorAgent()
        self.monitoring_agent = monitoring_agent or MonitoringAgent()
        self.retriever_client = retriever_client
        self.agent_memory = agent_memory
    
    def execute_deployment_plan(
        self,
        plan_id: str,
        intent: str,
        env: str,
        deployment_config: SageMakerDeploymentConfig,
        rag_evidence: List[RAGEvidence],
        constraints: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """Execute a complete deployment plan using multi-agent coordination.
        
        Args:
            plan_id: Deployment plan ID
            intent: User intent
            env: Target environment
            deployment_config: Deployment configuration
            rag_evidence: RAG evidence snippets
            constraints: Optional constraints
            
        Returns:
            ExecutionPlan with completed steps and reasoning chain
        """
        logger.info(f"[Orchestrator] Starting deployment execution for plan: {plan_id}")
        
        # Step 1: Planner Agent creates execution plan
        logger.info(f"[Orchestrator] Planner Agent creating execution plan...")
        execution_plan = self.planner_agent.create_execution_plan(
            plan_id=plan_id,
            intent=intent,
            env=env,
            rag_evidence=rag_evidence,
            constraints=constraints
        )
        
        # Step 2: Execute each step sequentially with dynamic replanning
        step_idx = 0
        while step_idx < len(execution_plan.steps):
            step = execution_plan.steps[step_idx]
            logger.info(f"[Orchestrator] Executing step {step_idx + 1}/{len(execution_plan.steps)}: {step.action}")
            
            # Iterative RAG: Retrieve additional context if step needs it
            if step.agent_type == "retriever" or (hasattr(step, "input") and step.input.get("needs_context")):
                if self.retriever_client:
                    additional_query = f"{step.action} {intent} {env}"
                    additional_evidence = self.retriever_client.query(additional_query, top_k=2)
                    if additional_evidence:
                        logger.info(f"[Orchestrator] Retrieved {len(additional_evidence)} additional context documents for step {step.action}")
                        # Update step context with new evidence
                        step.input["additional_evidence"] = [ev.dict() for ev in additional_evidence]
            
            # Handle retriever steps separately (they were already done, just log)
            if step.agent_type == "retriever":
                step.status = "completed"
                step.output = {
                    "message": "RAG retrieval already completed",
                    "evidence_count": len(rag_evidence)
                }
                step.timestamp = datetime.utcnow()
                step_idx += 1
                continue
            
            # Handle planner steps (config generation already done)
            if step.agent_type == "planner" and step.action == "generate_config":
                step.status = "completed"
                step.output = {
                    "message": "Deployment configuration generated",
                    "endpoint_name": deployment_config.endpoint_name,
                    "instance_type": deployment_config.instance_type
                }
                step.timestamp = datetime.utcnow()
                step_idx += 1
                continue
            
            # Execute step via Executor Agent
            if step.agent_type == "executor":
                result = self.executor_agent.execute_step(
                    step=step,
                    deployment_config=deployment_config,
                    env=env,
                    constraints=constraints
                )
                
                # If step failed, check if we should retry or replan
                if not result.success:
                    # Check memory for similar failures
                    should_retry = self.monitoring_agent.should_retry_step(step)
                    
                    if self.agent_memory:
                        memory_retry = self.agent_memory.should_retry_based_on_memory(
                            agent_name="executor",
                            action=step.action,
                            error=result.error or "unknown"
                        )
                        should_retry = should_retry and memory_retry
                    
                    if should_retry:
                        logger.warning(f"[Orchestrator] Step {step.action} failed, retrying...")
                        step = self.monitoring_agent.mark_step_for_retry(step)
                        
                        # Retry the step
                        result = self.executor_agent.execute_step(
                            step=step,
                            deployment_config=deployment_config,
                            env=env,
                            constraints=constraints
                        )
                    
                    # If still failed and needs replanning
                    if not result.success and step.needs_replan:
                        if execution_plan.replan_count < execution_plan.max_replans:
                            logger.info(f"[Orchestrator] Step {step.action} failed, triggering replanning (attempt {execution_plan.replan_count + 1})")
                            execution_plan = self._replan(
                                execution_plan=execution_plan,
                                failed_step=step,
                                intent=intent,
                                env=env,
                                deployment_config=deployment_config,
                                rag_evidence=rag_evidence,
                                constraints=constraints
                            )
                            # Reset to start of new plan
                            step_idx = 0
                            continue
                        else:
                            logger.error(f"[Orchestrator] Max replans ({execution_plan.max_replans}) reached. Stopping.")
                            break
            
            # Handle monitor steps
            if step.agent_type == "monitor":
                step.status = "completed"
                step.output = {
                    "message": f"Monitoring configured for {step.action}",
                    "status": "active"
                }
                step.timestamp = datetime.utcnow()
            
            step_idx += 1
        
        # Step 3: Final monitoring check
        monitoring_result = self.monitoring_agent.monitor_deployment(execution_plan)
        logger.info(f"[Orchestrator] Deployment monitoring status: {monitoring_result.status}")
        
        # Update execution plan timestamp
        execution_plan.updated_at = datetime.utcnow()
        
        return execution_plan
    
    def _replan(
        self,
        execution_plan: ExecutionPlan,
        failed_step: TaskStep,
        intent: str,
        env: str,
        deployment_config: SageMakerDeploymentConfig,
        rag_evidence: List[RAGEvidence],
        constraints: Dict[str, Any]
    ) -> ExecutionPlan:
        """Dynamically replan when a step fails.
        
        Args:
            execution_plan: Current execution plan
            failed_step: The step that failed
            intent: Original user intent
            env: Target environment
            deployment_config: Deployment configuration
            rag_evidence: RAG evidence
            constraints: Constraints
            
        Returns:
            Updated execution plan
        """
        logger.info(f"[Orchestrator] Replanning after failure of step: {failed_step.action}")
        
        # Add reasoning about replanning
        if execution_plan.reasoning_chain:
            replan_reasoning = ReasoningStep(
                thought=f"Replanning due to failure of step: {failed_step.action}",
                reasoning=f"Step {failed_step.step_id} failed with error: {failed_step.error}. "
                         f"Need to adjust plan to work around this issue.",
                confidence=0.7,
                alternatives=[
                    "Skip this step",
                    "Use alternative approach",
                    "Simplify deployment"
                ],
                decision="Replan with alternative approach"
            )
            execution_plan.reasoning_chain.steps.append(replan_reasoning)
        
        # Get additional context if needed
        if self.retriever_client:
            replan_query = f"alternative approach for {failed_step.action} {intent}"
            additional_evidence = self.retriever_client.query(replan_query, top_k=2)
            if additional_evidence:
                rag_evidence.extend(additional_evidence)
        
        # Ask planner to create a new plan with context about failure
        new_plan = self.planner_agent.create_execution_plan(
            plan_id=execution_plan.plan_id,
            intent=f"{intent} (replan after {failed_step.action} failure)",
            env=env,
            rag_evidence=rag_evidence,
            constraints=constraints
        )
        
        # Merge: keep completed steps, replace from failed step onwards
        completed_steps = [s for s in execution_plan.steps if s.status == "completed"]
        new_plan.steps = completed_steps + new_plan.steps[len(completed_steps):]
        
        # Update replan count
        new_plan.replan_count = execution_plan.replan_count + 1
        new_plan.updated_at = datetime.utcnow()
        
        # Remember the replanning
        if self.agent_memory:
            self.agent_memory.remember(
                agent_name="orchestrator",
                event=f"Replanned after {failed_step.action} failure",
                outcome={
                    "failed_step": failed_step.action,
                    "error": failed_step.error,
                    "replan_count": new_plan.replan_count,
                    "success": True
                }
            )
        
        logger.info(f"[Orchestrator] Replanning complete. New plan has {len(new_plan.steps)} steps.")
        return new_plan

