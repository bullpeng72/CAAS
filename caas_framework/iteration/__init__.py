"""
Iteration Control Module for CAAS-E

3-level iteration system:
- Nano: TDD cycle (RED-GREEN-REFACTOR)
- Micro: Story-level retry with checkpointing
- Macro: Epic-level multi-story coordination

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

from caas_framework.iteration.controller import IterationController
from caas_framework.iteration.nano_iterator import NanoIterator
from caas_framework.iteration.micro_iterator import MicroIterator
from caas_framework.iteration.macro_iterator import MacroIterator

from caas_framework.models.iteration import (
    IterationLevel,
    IterationStatus,
    FailureReason,
    IterationResult,
    IterationConfig,
    IterationMetrics,
    NanoIteration,
    MicroIteration,
    MacroIteration,
)

__all__ = [
    # Main Controller
    "IterationController",
    # Iterators
    "NanoIterator",
    "MicroIterator",
    "MacroIterator",
    # Enums
    "IterationLevel",
    "IterationStatus",
    "FailureReason",
    # Models
    "IterationResult",
    "IterationConfig",
    "IterationMetrics",
    "NanoIteration",
    "MicroIteration",
    "MacroIteration",
]
