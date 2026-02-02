"""
CaaS Framework Reporting Package

Provides progress reporting and workflow visualization for BMAD framework execution.
"""

# Protocol interfaces (UI-independent)
from caas_framework.reporting.interfaces import NullProgressReporter, PhaseInfo, PhaseResult
from caas_framework.reporting.interfaces import ProgressReporter as ProgressReporterProtocol
from caas_framework.reporting.interfaces import VerbosityLevel

# Concrete implementations
from caas_framework.reporting.progress_reporter import PhaseProgress, PhaseStatus, ProgressReporter

__all__ = [
    # Protocol interfaces
    "ProgressReporterProtocol",
    "VerbosityLevel",
    "PhaseInfo",
    "PhaseResult",
    "NullProgressReporter",
    # Concrete implementations
    "ProgressReporter",
    "PhaseProgress",
    "PhaseStatus",
]
