"""
CaaS Framework Modes Package

Provides different execution modes for the CAAS framework.
"""

# Protocol interfaces (UI-independent)
from caas_framework.modes.interfaces import ApprovalDecision, NullReviewHandler, ReviewHandler

# Backward compatible wrapper
from caas_framework.modes.plan_mode import PlanMode, create_plan_mode

# Core implementations
from caas_framework.modes.plan_mode_core import ApprovalGate, PlanModeCore

__all__ = [
    # Protocol interfaces
    "ReviewHandler",
    "ApprovalDecision",
    "NullReviewHandler",
    # Core implementations
    "PlanModeCore",
    "ApprovalGate",
    # Wrapper (backward compatible)
    "PlanMode",
    "create_plan_mode",
]
