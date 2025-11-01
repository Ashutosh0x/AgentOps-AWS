"""Agent Memory System - Episodic and semantic memory for agent learning."""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of agent memory."""
    EPISODIC = "episodic"  # Specific events/experiences
    SEMANTIC = "semantic"  # General knowledge/patterns
    PROCEDURAL = "procedural"  # How to do things


class AgentMemory:
    """Manages agent memory for learning and state persistence."""
    
    def __init__(self, table_name: str = None, region: str = None):
        """Initialize Agent Memory.
        
        Args:
            table_name: DynamoDB table name for memory (defaults to env var)
            region: AWS region
        """
        self.table_name = table_name or os.getenv("AGENT_MEMORY_TABLE", "agentops-agent-memory")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # In-memory cache for quick access
        self.episodic_cache: List[Dict[str, Any]] = []
        self.semantic_cache: Dict[str, Any] = {}
        
        # Initialize DynamoDB
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
            try:
                self.table.meta.client.describe_table(TableName=self.table_name)
                logger.info(f"Agent memory connected to DynamoDB: {self.table_name}")
                self.enabled = True
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"DynamoDB table {self.table_name} not found. Attempting to create...")
                    try:
                        self._create_table_if_not_exists()
                    except Exception as create_error:
                        logger.warning(f"Could not create table: {create_error}. Using in-memory only.")
                        self.table = None
                        self.enabled = False
                else:
                    logger.warning(f"DynamoDB table {self.table_name} access error: {e}. Using in-memory only.")
                    self.table = None
                    self.enabled = False
        except Exception as e:
            logger.warning(f"Failed to initialize DynamoDB: {e}. Using in-memory only.")
            self.table = None
            self.enabled = False
        
        # Memory expiration settings (for cleanup)
        self.memory_expiration_days = int(os.getenv("AGENT_MEMORY_EXPIRATION_DAYS", "90"))  # Default 90 days
    
    def remember(
        self,
        agent_name: str,
        event: str,
        outcome: Dict[str, Any],
        memory_type: MemoryType = MemoryType.EPISODIC,
        metadata: Dict[str, Any] = None
    ):
        """Store a memory for future recall.
        
        Args:
            agent_name: Name of the agent (e.g., "planner", "executor")
            event: Description of the event/action
            outcome: Result of the event (success, failure, observations)
            memory_type: Type of memory to store
            metadata: Additional metadata
        """
        memory_item = {
            "agent_name": agent_name,
            "event": event,
            "outcome": outcome,
            "memory_type": memory_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Add to cache
        if memory_type == MemoryType.EPISODIC:
            self.episodic_cache.append(memory_item)
            # Keep only last 100 in memory
            if len(self.episodic_cache) > 100:
                self.episodic_cache = self.episodic_cache[-100:]
        elif memory_type == MemoryType.SEMANTIC:
            key = f"{agent_name}:{event}"
            self.semantic_cache[key] = memory_item
        
        # Persist to DynamoDB
        if self.enabled and self.table:
            try:
                item = {
                    "memory_id": f"{agent_name}#{datetime.utcnow().timestamp()}",
                    "agent_name": agent_name,
                    "event": event,
                    "outcome": json.dumps(outcome) if isinstance(outcome, dict) else str(outcome),
                    "memory_type": memory_type.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": json.dumps(metadata or {}),
                    "ttl": int((datetime.utcnow() + timedelta(days=self.memory_expiration_days)).timestamp()) if self.memory_expiration_days > 0 else None
                }
                self.table.put_item(Item=item)
                logger.debug(f"[Memory] Stored {memory_type.value} memory for {agent_name}")
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
    
    def recall(
        self,
        agent_name: str,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 5,
        time_window_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Recall relevant memories.
        
        Args:
            agent_name: Name of the agent
            query: Query to search for (event description or pattern)
            memory_type: Filter by memory type (None = all types)
            limit: Maximum number of memories to return
            time_window_days: Only recall memories within this window
            
        Returns:
            List of relevant memories
        """
        results = []
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        
        # Search in-memory cache first
        if memory_type is None or memory_type == MemoryType.EPISODIC:
            for mem in self.episodic_cache:
                if mem["agent_name"] == agent_name:
                    mem_date = datetime.fromisoformat(mem["timestamp"])
                    if mem_date >= cutoff_date:
                        if query.lower() in mem["event"].lower() or query.lower() in str(mem["outcome"]).lower():
                            results.append(mem)
        
        if memory_type is None or memory_type == MemoryType.SEMANTIC:
            for key, mem in self.semantic_cache.items():
                if agent_name in key:
                    if query.lower() in mem["event"].lower():
                        results.append(mem)
        
        # Search DynamoDB if enabled
        if self.enabled and self.table:
            try:
                response = self.table.query(
                    IndexName="agent_name-timestamp-index",  # Assume GSI exists
                    KeyConditionExpression="agent_name = :agent",
                    FilterExpression="contains(event, :query) OR contains(#outcome, :query)",
                    ExpressionAttributeNames={"#outcome": "outcome"},
                    ExpressionAttributeValues={
                        ":agent": agent_name,
                        ":query": query
                    },
                    Limit=limit * 2  # Get more to filter by date
                )
                
                for item in response.get("Items", []):
                    item_date = datetime.fromisoformat(item["timestamp"])
                    if item_date >= cutoff_date:
                        # Parse outcome if it's a string
                        outcome = item.get("outcome")
                        if isinstance(outcome, str):
                            try:
                                outcome = json.loads(outcome)
                            except:
                                pass
                        
                        results.append({
                            "agent_name": item["agent_name"],
                            "event": item["event"],
                            "outcome": outcome,
                            "memory_type": item.get("memory_type", "episodic"),
                            "timestamp": item["timestamp"]
                        })
            except Exception as e:
                logger.warning(f"Failed to query DynamoDB memory: {e}")
        
        # Sort by timestamp (most recent first) and limit
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]
    
    def learn_pattern(
        self,
        agent_name: str,
        pattern: str,
        lesson: str,
        success_rate: float = None,
        example_count: int = 0
    ):
        """Learn a pattern/rule from experiences.
        
        Args:
            agent_name: Name of the agent
            pattern: Pattern description (e.g., "production deployments require approval")
            lesson: Lesson learned
            success_rate: Success rate if applicable
            example_count: Number of examples this is based on
        """
        semantic_memory = {
            "pattern": pattern,
            "lesson": lesson,
            "success_rate": success_rate,
            "example_count": example_count,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        self.remember(
            agent_name=agent_name,
            event=f"Pattern: {pattern}",
            outcome={"lesson": lesson, "success_rate": success_rate, "examples": example_count},
            memory_type=MemoryType.SEMANTIC,
            metadata={"pattern": True}
        )
        
        logger.info(f"[Memory] {agent_name} learned pattern: {pattern}")
    
    def get_similar_experiences(
        self,
        agent_name: str,
        current_situation: Dict[str, Any],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get similar past experiences to current situation.
        
        Args:
            agent_name: Name of the agent
            current_situation: Current situation description
            limit: Maximum number of experiences to return
            
        Returns:
            List of similar experiences
        """
        # Build query from current situation
        query_parts = []
        if "intent" in current_situation:
            query_parts.append(current_situation["intent"])
        if "env" in current_situation:
            query_parts.append(current_situation["env"])
        if "action" in current_situation:
            query_parts.append(current_situation["action"])
        
        query = " ".join(query_parts)
        return self.recall(agent_name=agent_name, query=query, limit=limit)
    
    def should_retry_based_on_memory(
        self,
        agent_name: str,
        action: str,
        error: str
    ) -> bool:
        """Determine if action should be retried based on past experiences.
        
        Args:
            agent_name: Name of the agent
            action: Action that failed
            error: Error message
            
        Returns:
            True if past experiences suggest retry will succeed
        """
        # Search for similar failures that eventually succeeded
        similar = self.recall(
            agent_name=agent_name,
            query=f"{action} {error}",
            limit=5
        )
        
        if not similar:
            return True  # No prior experience, default to retry
        
        # Check if any similar situations eventually succeeded
        for mem in similar:
            outcome = mem.get("outcome", {})
            if isinstance(outcome, dict):
                # Check if there's a follow-up success
                if outcome.get("eventually_succeeded", False):
                    return True
        
        # If all similar situations failed, don't retry
        failed_count = sum(1 for mem in similar if mem.get("outcome", {}).get("success") is False)
        if failed_count >= 3:  # Multiple failures for similar situation
            return False
        
        return True
    
    def delete_memories_for_plan(self, plan_id: str) -> int:
        """Delete all agent memories associated with a deployment plan.
        
        Args:
            plan_id: Deployment plan ID
            
        Returns:
            Number of memories deleted
        """
        deleted_count = 0
        
        # Delete from cache
        cache_deleted = 0
        if plan_id:
            # Filter episodic cache by plan_id in metadata
            self.episodic_cache = [
                mem for mem in self.episodic_cache 
                if mem.get("metadata", {}).get("plan_id") != plan_id
            ]
            cache_deleted = len(self.episodic_cache) - cache_deleted
            
            # Filter semantic cache
            keys_to_delete = [
                key for key, mem in self.semantic_cache.items()
                if mem.get("metadata", {}).get("plan_id") == plan_id
            ]
            for key in keys_to_delete:
                del self.semantic_cache[key]
                cache_deleted += 1
        
        deleted_count = cache_deleted
        
        # Delete from DynamoDB
        if self.enabled and self.table:
            try:
                # Query all memories with plan_id in metadata
                response = self.table.scan(
                    FilterExpression="contains(metadata, :plan_id)",
                    ExpressionAttributeValues={":plan_id": plan_id}
                )
                
                for item in response.get("Items", []):
                    try:
                        # Parse metadata to check if it contains plan_id
                        metadata_str = item.get("metadata", "{}")
                        metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                        
                        if metadata.get("plan_id") == plan_id:
                            self.table.delete_item(Key={"memory_id": item["memory_id"]})
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete memory item: {e}")
                        continue
                
                # Continue scanning if paginated
                while "LastEvaluatedKey" in response:
                    response = self.table.scan(
                        FilterExpression="contains(metadata, :plan_id)",
                        ExpressionAttributeValues={":plan_id": plan_id},
                        ExclusiveStartKey=response["LastEvaluatedKey"]
                    )
                    for item in response.get("Items", []):
                        try:
                            metadata_str = item.get("metadata", "{}")
                            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                            
                            if metadata.get("plan_id") == plan_id:
                                self.table.delete_item(Key={"memory_id": item["memory_id"]})
                                deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete memory item: {e}")
                            continue
                
                logger.info(f"Deleted {deleted_count} agent memories for plan: {plan_id}")
            except Exception as e:
                logger.error(f"Failed to delete memories from DynamoDB: {e}")
        
        return deleted_count

