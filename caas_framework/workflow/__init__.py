"""
Workflow Management Module

Manages workflow execution, state persistence, checkpoints, and resumption.
"""

from caas_framework.workflow.state_manager import (
    StateManager,
    Checkpoint,
    StateHistory,
)
from caas_framework.workflow.orchestrator import (
    WorkflowOrchestrator,
    WorkflowPhase,
    WorkflowResult,
)
from caas_framework.workflow.persistence import (
    PersistenceBackend,
    FilePersistenceBackend,
    DatabasePersistenceBackend,
    MemoryPersistenceBackend,
)
from caas_framework.workflow.version_control import (
    GitIntegration,
    GitCommit,
    GitStatus,
)

__all__ = [
    "StateManager",
    "Checkpoint",
    "StateHistory",
    "WorkflowOrchestrator",
    "WorkflowPhase",
    "WorkflowResult",
    "PersistenceBackend",
    "FilePersistenceBackend",
    "DatabasePersistenceBackend",
    "MemoryPersistenceBackend",
    "GitIntegration",
    "GitCommit",
    "GitStatus",
]
