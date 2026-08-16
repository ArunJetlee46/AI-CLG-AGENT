from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.api.deps import require_role
from app.agents.plugin import (
    AgentPluginRegistry,
    get_plugin_registry,
    register_agent_plugin,
    AgentPlugin,
)
from app.models.entities import User

router = APIRouter(prefix="/agent-plugins", tags=["agent-plugins"])


class PluginCreate(BaseModel):
    name: str
    intent_keywords: List[str]
    description: str
    handler_code: str  # Python code as string for dynamic handlers
    priority: int = 0
    enabled: bool = True
    metadata: dict = {}


class PluginUpdate(BaseModel):
    intent_keywords: Optional[List[str]] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    metadata: Optional[dict] = None


class PluginResponse(BaseModel):
    name: str
    description: str
    intent_keywords: List[str]
    priority: int
    enabled: bool
    metadata: dict


@router.get("", response_model=List[PluginResponse])
def list_plugins(
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """List all registered agent plugins."""
    plugins = registry.list_plugins()
    return [PluginResponse(**p) for p in plugins]


@router.get("/{name}", response_model=PluginResponse)
def get_plugin(
    name: str,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Get a specific plugin by name."""
    plugin = registry.get(name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return PluginResponse(
        name=plugin.name,
        description=plugin.description,
        intent_keywords=plugin.intent_keywords,
        priority=plugin.priority,
        enabled=plugin.enabled,
        metadata=plugin.metadata,
    )


@router.post("", response_model=PluginResponse)
def create_plugin(
    data: PluginCreate,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Register a new agent plugin.
    
    Note: handler_code is stored but not executed for security.
    Custom handlers should be added to the plugin module directly.
    """
    if registry.get(data.name):
        raise HTTPException(status_code=400, detail="Plugin with this name already exists")

    # For security, we don't execute arbitrary code
    # In production, plugins should be added as Python modules
    def placeholder_handler(state):
        state["answer"] = f"Plugin '{data.name}' is registered but handler not implemented"
        return state

    plugin = register_agent_plugin(
        name=data.name,
        intent_keywords=data.intent_keywords,
        description=data.description,
        handler=placeholder_handler,
        priority=data.priority,
        enabled=data.enabled,
        **data.metadata,
    )

    return PluginResponse(
        name=plugin.name,
        description=plugin.description,
        intent_keywords=plugin.intent_keywords,
        priority=plugin.priority,
        enabled=plugin.enabled,
        metadata=plugin.metadata,
    )


@router.patch("/{name}", response_model=PluginResponse)
def update_plugin(
    name: str,
    data: PluginUpdate,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Update a plugin's configuration."""
    plugin = registry.get(name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    if data.intent_keywords is not None:
        # Re-register with new keywords
        registry.unregister(name)
        plugin.intent_keywords = data.intent_keywords
        registry.register(plugin)

    if data.description is not None:
        plugin.description = data.description
    if data.priority is not None:
        plugin.priority = data.priority
    if data.enabled is not None:
        plugin.enabled = data.enabled
    if data.metadata is not None:
        plugin.metadata = data.metadata

    return PluginResponse(
        name=plugin.name,
        description=plugin.description,
        intent_keywords=plugin.intent_keywords,
        priority=plugin.priority,
        enabled=plugin.enabled,
        metadata=plugin.metadata,
    )


@router.delete("/{name}")
def delete_plugin(
    name: str,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Unregister a plugin."""
    if not registry.unregister(name):
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"message": f"Plugin '{name}' unregistered"}


@router.post("/{name}/enable")
def enable_plugin(
    name: str,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Enable a plugin."""
    plugin = registry.get(name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    plugin.enabled = True
    return {"message": f"Plugin '{name}' enabled"}


@router.post("/{name}/disable")
def disable_plugin(
    name: str,
    user: User = Depends(require_role("admin")),
    registry: AgentPluginRegistry = Depends(get_plugin_registry),
):
    """Disable a plugin."""
    plugin = registry.get(name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    plugin.enabled = False
    return {"message": f"Plugin '{name}' disabled"}