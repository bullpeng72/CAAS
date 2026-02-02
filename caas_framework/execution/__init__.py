"""
Execution modes for CAAS

Includes:
- Plan Mode for user review before code generation
- Distributed Execution for parallel phase processing
"""

from caas_framework.execution.distributed_executor import (
    DependencyGraph,
    DistributedPhaseExecutor,
    ExecutionStrategy,
    PhaseExecutionResult,
)
from caas_framework.execution.plan_mode import PlanMode

__all__ = [
    "PlanMode",
    "DistributedPhaseExecutor",
    "DependencyGraph",
    "PhaseExecutionResult",
    "ExecutionStrategy",
]
