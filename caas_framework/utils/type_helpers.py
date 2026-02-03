"""
Type Helpers and Type Aliases

Provides common type aliases and type checking utilities
for the CAAS framework.
"""

from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
)

# ==================== Type Variables ====================

T = TypeVar("T")
AgentT = TypeVar("AgentT", bound="BaseExpertAgent")
PhaseT = TypeVar("PhaseT", bound="AgentPhase")


# ==================== Protocol Definitions ====================


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def ainvoke(self, messages: List[Dict[str, str]], **kwargs: Any) -> Any:
        """Invoke LLM asynchronously."""
        ...

    def invoke(self, messages: List[Dict[str, str]], **kwargs: Any) -> Any:
        """Invoke LLM synchronously."""
        ...


class Validator(Protocol):
    """Protocol for validators."""

    def validate(self, output: Dict[str, Any], schema: type) -> bool:
        """Validate output against schema."""
        ...


# ==================== TypedDict Definitions ====================


class AgentDict(TypedDict, total=False):
    """Type definition for agent dictionary."""

    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str]
    verbose: bool
    allow_delegation: bool


class TaskDict(TypedDict, total=False):
    """Type definition for task dictionary."""

    id: str
    description: str
    expected_output: str
    agent: str
    context: List[str]
    human_input: bool


class DesignOutput(TypedDict):
    """Type definition for design phase output."""

    agents: List[AgentDict]
    tasks: List[TaskDict]


class ValidationResult(TypedDict):
    """Type definition for validation result."""

    passed: bool
    errors: List[str]
    warnings: List[str]


class CodeFiles(TypedDict):
    """Type definition for generated code files."""

    files: Dict[str, str]  # filename -> content


# ==================== Type Aliases ====================

# Common type aliases
JSON = Dict[str, Any]
AgentList = List[AgentDict]
TaskList = List[TaskDict]
FileDict = Dict[str, str]

# Callback types
ProgressCallback = Callable[[str, str], None]
AsyncProgressCallback = Callable[[str, str], Awaitable[None]]

# Result types
AgentResult = Dict[str, Any]
PhaseResult = Union[Dict[str, Any], None]


# ==================== Enum for Phase Status ====================


class PhaseStatus(str, Enum):
    """Status of a phase execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ==================== Runtime Type Checking ====================


def is_agent_dict(obj: Any) -> bool:
    """Check if object is a valid agent dictionary."""
    if not isinstance(obj, dict):
        return False

    required_fields = {"id", "role", "goal", "backstory"}
    return required_fields.issubset(obj.keys())


def is_task_dict(obj: Any) -> bool:
    """Check if object is a valid task dictionary."""
    if not isinstance(obj, dict):
        return False

    required_fields = {"id", "description", "expected_output", "agent"}
    return required_fields.issubset(obj.keys())


def validate_design_output(output: Any) -> bool:
    """Validate design output structure."""
    if not isinstance(output, dict):
        return False

    if "agents" not in output or "tasks" not in output:
        return False

    agents = output["agents"]
    tasks = output["tasks"]

    if not isinstance(agents, list) or not isinstance(tasks, list):
        return False

    # Validate each agent
    for agent in agents:
        if not is_agent_dict(agent):
            return False

    # Validate each task
    for task in tasks:
        if not is_task_dict(task):
            return False

    return True


# ==================== Type Guards ====================


def assert_agent_dict(obj: Any) -> AgentDict:
    """Assert and return as AgentDict."""
    if not is_agent_dict(obj):
        raise TypeError(f"Expected AgentDict, got {type(obj)}")
    return obj  # type: ignore


def assert_task_dict(obj: Any) -> TaskDict:
    """Assert and return as TaskDict."""
    if not is_task_dict(obj):
        raise TypeError(f"Expected TaskDict, got {type(obj)}")
    return obj  # type: ignore


def assert_design_output(obj: Any) -> DesignOutput:
    """Assert and return as DesignOutput."""
    if not validate_design_output(obj):
        raise TypeError(f"Expected DesignOutput, got {type(obj)}")
    return obj  # type: ignore
