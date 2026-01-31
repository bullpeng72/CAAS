"""
Execution modes for CAAS

Includes:
- Plan Mode for user review before code generation
- Distributed Execution for parallel phase processing
"""

from caas_framework.execution.plan_mode import PlanMode
from caas_framework.execution.distributed_executor import (
    DistributedPhaseExecutor,
    DependencyGraph,
    PhaseExecutionResult,
    ExecutionStrategy
)

__all__ = [
    'PlanMode',
    'DistributedPhaseExecutor',
    'DependencyGraph',
    'PhaseExecutionResult',
    'ExecutionStrategy'
]
