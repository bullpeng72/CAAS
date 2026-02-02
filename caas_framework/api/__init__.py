"""
Framework API Layer

UI-independent API for CAAS Framework.
Supports multiple UIs: CLI, Streamlit, VSCode Extension, etc.
"""

# Unified API
from caas_framework.api.caas_api import CAAS_API, GenerationConfig, GenerationResult

# Protocol interfaces
from caas_framework.api.interfaces import (
    EventData,
    ReviewHandler,
    ReviewRequest,
    ReviewType,
    UICallback,
    UIEvent,
)

__all__ = [
    # Protocol interfaces
    "UICallback",
    "EventData",
    "UIEvent",
    "ReviewHandler",
    "ReviewRequest",
    "ReviewType",
    # Unified API
    "CAAS_API",
    "GenerationConfig",
    "GenerationResult",
]
