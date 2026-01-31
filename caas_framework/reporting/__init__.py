"""
CaaS Framework Reporting Package

Provides progress reporting and workflow visualization for BMAD framework execution.
"""

# Protocol interfaces (UI-independent)
from caas_framework.reporting.interfaces import (
    ProgressReporter as ProgressReporterProtocol,
    VerbosityLevel,
    PhaseInfo,
    PhaseResult,
    NullProgressReporter
)

# Concrete implementations
from caas_framework.reporting.progress_reporter import (
    ProgressReporter,
    PhaseProgress,
    PhaseStatus
)

__all__ = [
    # Protocol interfaces
    'ProgressReporterProtocol',
    'VerbosityLevel',
    'PhaseInfo',
    'PhaseResult',
    'NullProgressReporter',
    # Concrete implementations
    'ProgressReporter',
    'PhaseProgress',
    'PhaseStatus'
]
