"""
CAAS Factory Package

CrewAI 에이전트, 태스크, 도구, Crew 생성 팩토리를 제공합니다.
"""

from caas_framework.factory.agent_factory import AgentDefinition, AgentFactory
from caas_framework.factory.crew_assembler import CrewAssembler, CrewDefinition
from caas_framework.factory.task_factory import TaskDefinition, TaskFactory
from caas_framework.factory.tool_factory import (
    TOOL_ALIASES,
    ToolCapability,
    ToolDefinition,
    ToolFactory,
    ToolType,
    resolve_tool_alias,
)

__all__ = [
    # Agent
    "AgentDefinition",
    "AgentFactory",
    # Task
    "TaskDefinition",
    "TaskFactory",
    # Tool
    "ToolDefinition",
    "ToolFactory",
    "ToolType",
    "ToolCapability",
    "TOOL_ALIASES",
    "resolve_tool_alias",
    # Crew
    "CrewDefinition",
    "CrewAssembler",
]
