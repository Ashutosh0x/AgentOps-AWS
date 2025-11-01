"""Monitoring Agent - Tracks progress, detects failures, triggers retries."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from orchestrator.models import MonitoringResult, TaskStep, ExecutionPlan

logger = logging.getLogger(__name__)


class MonitoringAgent:
    """Agent that monitors deployment progress and handles self-correction."""
    
    def __init__(self, max_retries: int = 3, retry_delay_seconds: int = 5):
        """Initialize Monitoring Agent.
        
        Args:
            max_retries: Maximum retry attempts for failed steps
            retry_delay_seconds: Delay between retries
        """
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
    
    def monitor_deployment(self, execution_plan: ExecutionPlan) -> MonitoringResult:
        """Monitor deployment progress and detect issues.
        
        Args:
            execution_plan: Execution plan to monitor
            
        Returns:
            MonitoringResult with status and check results
        """
        checks = []
        
        # Check each step status
        failed_steps = [step for step in execution_plan.steps if step.status == "failed"]
        in_progress_steps = [step for step in execution_plan.steps if step.status in ["thinking", "executing"]]
        completed_steps = [step for step in execution_plan.steps if step.status == "completed"]
        
        # Overall status assessment
        if failed_steps:
            status = "failed"
            requires_action = True
        elif in_progress_steps:
            status = "in_progress"
            requires_action = False
        elif len(completed_steps) == len(execution_plan.steps):
            status = "completed"
            requires_action = False
        else:
            status = "unknown"
            requires_action = True
        
        # Individual step checks
        for step in execution_plan.steps:
            check_result = {
                "step_id": step.step_id,
                "action": step.action,
                "status": step.status,
                "timestamp": step.timestamp.isoformat() if isinstance(step.timestamp, datetime) else str(step.timestamp),
                "retry_count": step.retry_count
            }
            
            if step.status == "failed" and step.retry_count < self.max_retries:
                check_result["should_retry"] = True
                check_result["retry_delay"] = self.retry_delay_seconds
            else:
                check_result["should_retry"] = False
            
            if step.error:
                check_result["error"] = step.error
            
            checks.append(check_result)
        
        return MonitoringResult(
            plan_id=execution_plan.plan_id,
            status=status,
            checks=checks,
            requires_action=requires_action,
            timestamp=datetime.utcnow()
        )
    
    def should_retry_step(self, step: TaskStep) -> bool:
        """Determine if a failed step should be retried.
        
        Args:
            step: Failed step to check
            
        Returns:
            True if step should be retried
        """
        if step.status != "failed":
            return False
        
        if step.retry_count >= self.max_retries:
            logger.warning(f"[Monitor] Step {step.step_id} exceeded max retries ({self.max_retries})")
            return False
        
        # Don't retry validation failures (these need human intervention)
        if step.action == "validate_plan" and step.error:
            return False
        
        return True
    
    def get_next_retry_delay(self, retry_count: int) -> int:
        """Get delay before next retry (exponential backoff).
        
        Args:
            retry_count: Current retry count
            
        Returns:
            Delay in seconds
        """
        return self.retry_delay_seconds * (2 ** retry_count)
    
    def mark_step_for_retry(self, step: TaskStep) -> TaskStep:
        """Mark a step for retry.
        
        Args:
            step: Step to mark for retry
            
        Returns:
            Updated step
        """
        step.retry_count += 1
        step.status = "retrying"
        step.timestamp = datetime.utcnow()
        
        logger.info(f"[Monitor] Marking step {step.step_id} for retry (attempt {step.retry_count})")
        
        return step

