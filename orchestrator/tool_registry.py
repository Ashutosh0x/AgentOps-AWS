"""Tool Registry - Dynamic tool discovery and usage for agents."""

import logging
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Represents a tool that agents can use."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema for parameters
    execute: Callable  # Function to execute the tool
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return self.execute(**kwargs)


class ToolRegistry:
    """Registry for managing tools that agents can discover and use."""
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()
    
    def register_tool(
        self,
        tool: Tool,
        overwrite: bool = False
    ):
        """Register a tool in the registry.
        
        Args:
            tool: Tool to register
            overwrite: Whether to overwrite if tool already exists
        """
        if tool.name in self.tools and not overwrite:
            logger.warning(f"Tool {tool.name} already registered. Use overwrite=True to replace.")
            return
        
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.category})")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool if found, None otherwise
        """
        return self.tools.get(name)
    
    def search_tools(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Tool]:
        """Search for tools matching query.
        
        Args:
            query: Search query (matches name, description, tags)
            category: Filter by category
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of matching tools
        """
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            # Filter by category
            if category and tool.category != category:
                continue
            
            # Filter by tags
            if tags:
                if not any(tag in tool.tags for tag in tags):
                    continue
            
            # Match query
            score = 0
            if query_lower in tool.name.lower():
                score += 10
            if query_lower in tool.description.lower():
                score += 5
            if any(query_lower in tag.lower() for tag in tool.tags):
                score += 3
            
            if score > 0:
                results.append((score, tool))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [tool for _, tool in results[:limit]]
    
    def list_tools(
        self,
        category: Optional[str] = None
    ) -> List[Tool]:
        """List all tools, optionally filtered by category.
        
        Args:
            category: Filter by category
            
        Returns:
            List of tools
        """
        if category:
            return [tool for tool in self.tools.values() if tool.category == category]
        return list(self.tools.values())
    
    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of all tools for LLM prompts.
        
        Returns:
            Formatted string with tool descriptions
        """
        descriptions = []
        for tool in self.tools.values():
            desc = f"- {tool.name}: {tool.description}"
            if tool.parameters:
                desc += f"\n  Parameters: {tool.parameters}"
            if tool.examples:
                desc += f"\n  Example: {tool.examples[0]}"
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    def _register_default_tools(self):
        """Register default tools for SageMaker deployment."""
        from orchestrator.sage_tool import SageMakerTool
        from orchestrator.guardrail import GuardrailService
        
        # Note: These will be registered when tools are actually needed
        # This is a placeholder for structure
        pass


# Global tool registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry

