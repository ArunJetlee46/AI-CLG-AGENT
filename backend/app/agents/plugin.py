"""Agent Plugin System.

Allows dynamic registration and discovery of specialist agents
without modifying the core supervisor graph.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


@dataclass
class AgentPlugin:
    """Metadata for a registered agent plugin."""
    name: str
    intent_keywords: List[str]
    description: str
    handler: Callable[[AgentState], AgentState]
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentPluginRegistry:
    """Registry for managing agent plugins."""

    def __init__(self):
        self._plugins: Dict[str, AgentPlugin] = {}
        self._intent_map: Dict[str, List[str]] = {}

    def register(self, plugin: AgentPlugin) -> None:
        """Register a new agent plugin."""
        if plugin.name in self._plugins:
            logger.warning(f"Overwriting existing plugin: {plugin.name}")
        self._plugins[plugin.name] = plugin

        # Update intent mapping
        for keyword in plugin.intent_keywords:
            if keyword not in self._intent_map:
                self._intent_map[keyword] = []
            self._intent_map[keyword].append(plugin.name)

        # Sort by priority (higher first)
        for keyword in plugin.intent_keywords:
            self._intent_map[keyword].sort(
                key=lambda name: self._plugins[name].priority,
                reverse=True
            )

        logger.info(f"Registered agent plugin: {plugin.name} (keywords: {plugin.intent_keywords})")

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name not in self._plugins:
            return False
        plugin = self._plugins.pop(name)
        for keyword in plugin.intent_keywords:
            if keyword in self._intent_map:
                self._intent_map[keyword] = [n for n in self._intent_map[keyword] if n != name]
        logger.info(f"Unregistered agent plugin: {name}")
        return True

    def get(self, name: str) -> Optional[AgentPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def get_for_intent(self, intent: str) -> List[AgentPlugin]:
        """Get plugins that handle a specific intent, sorted by priority."""
        plugin_names = self._intent_map.get(intent, [])
        return [self._plugins[name] for name in plugin_names if self._plugins[name].enabled]

    def get_all_enabled(self) -> List[AgentPlugin]:
        """Get all enabled plugins sorted by priority."""
        return sorted(
            [p for p in self._plugins.values() if p.enabled],
            key=lambda p: p.priority,
            reverse=True
        )

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins with their metadata."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "intent_keywords": p.intent_keywords,
                "priority": p.priority,
                "enabled": p.enabled,
                "metadata": p.metadata,
            }
            for p in self._plugins.values()
        ]


# Global registry instance
_registry = AgentPluginRegistry()


def get_plugin_registry() -> AgentPluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_agent_plugin(
    name: str,
    intent_keywords: List[str],
    description: str,
    handler: Callable[[AgentState], AgentState],
    priority: int = 0,
    enabled: bool = True,
    **metadata,
) -> AgentPlugin:
    """Convenience function to register a plugin."""
    plugin = AgentPlugin(
        name=name,
        intent_keywords=intent_keywords,
        description=description,
        handler=handler,
        priority=priority,
        enabled=enabled,
        metadata=metadata,
    )
    _registry.register(plugin)
    return plugin


class BaseAgentPlugin(ABC):
    """Base class for agent plugins."""

    name: str
    intent_keywords: List[str]
    description: str
    priority: int = 0

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        """Execute the agent logic."""
        pass

    def as_plugin(self) -> AgentPlugin:
        """Convert to AgentPlugin for registration."""
        return AgentPlugin(
            name=self.name,
            intent_keywords=self.intent_keywords,
            description=self.description,
            handler=self.run,
            priority=self.priority,
        )


# Example: Registering a custom plugin
def create_sample_plugins() -> None:
    """Create sample plugins to demonstrate the system."""

    # Example: Research Agent
    def research_agent(state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        state["answer"] = f"Research Agent: I would search academic papers for '{text}'"
        state["data"] = {"agent": "research", "query": text}
        state["audit_events"].append({
            "action": "research_query",
            "entity_type": "research",
            "payload": {"query": text},
        })
        return state

    register_agent_plugin(
        name="research",
        intent_keywords=["research", "paper", "publication", "cite", "literature"],
        description="Searches academic papers and publications",
        handler=research_agent,
        priority=10,
    )

    # Example: Career Agent
    def career_agent(state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        state["answer"] = f"Career Agent: I would provide career guidance for '{text}'"
        state["data"] = {"agent": "career", "query": text}
        state["audit_events"].append({
            "action": "career_query",
            "entity_type": "career",
            "payload": {"query": text},
        })
        return state

    register_agent_plugin(
        name="career",
        intent_keywords=["career", "job", "internship", "resume", "interview", "placement"],
        description="Provides career guidance and job search help",
        handler=career_agent,
        priority=10,
    )


# Auto-register sample plugins on import
create_sample_plugins()