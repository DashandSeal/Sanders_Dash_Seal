"""
Module: core_platform.agent_registry
Description: Sanders Dash & Seal exact IT AI Manager agent matrix registry.
Registry and authorization boundary only; strict interface control.
"""

from dataclasses import dataclass

PLATFORM = "Sanders Dash & Seal"
IT_MANAGER = "IT_AI_Manager_v15.0"

IT_AGENT_NAMES = (
    "Uptime Agent",
    "Application Agent",
    "Database Agent",
    "Deployment Agent",
    "Infrastructure Agent",
    "Integration Agent",
    "Performance Agent",
    "Backup & Recovery Agent",
    "Observability Agent",
    "Quality Agent",
    "Configuration Agent",
    "IT Support Agent",
)

@dataclass(frozen=True)
class AgentDescriptor:
    name: str
    commanding_authority: str = IT_MANAGER
    implementation_status: str = "INTERFACE_ONLY"
    external_execution_enabled: bool = False

# Construct immutable agent registry mapping
AGENTS = {name: AgentDescriptor(name=name) for name in IT_AGENT_NAMES}

def require_registered_agent(name: str) -> AgentDescriptor:
    """Validates and returns the agent descriptor if registered within the matrix."""
    try:
        return AGENTS[name]
    except KeyError as exc:
        raise PermissionError("UNKNOWN_AGENT") from exc

def require_executable_agent(name: str) -> AgentDescriptor:
    """Validates that the registered agent is explicitly authorized for external execution."""
    agent = require_registered_agent(name)
    if not agent.external_execution_enabled:
        raise PermissionError("AGENT_NOT_IMPLEMENTED_OR_AUTHORIZED")
    return agent
