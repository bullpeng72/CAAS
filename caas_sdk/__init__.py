"""
CAAS Python SDK

Official Python SDK for CAAS (CrewAI Agent Auto-generation System).
"""

# REST API Client (for remote CAAS API server)
from caas_sdk.client import CAAS, AsyncCAAS
from caas_sdk.exceptions import (
    AuthenticationError,
    CAASError,
    RateLimitError,
    ValidationError,
)

# Local Client (for local execution without REST API)
from caas_sdk.local_client import CAASLocalClient, generate
from caas_sdk.models import GenerationConfig, GenerationResult, Project, ProjectStatus

__version__ = "0.4.0"
__all__ = [
    # REST API Clients
    "CAAS",
    "AsyncCAAS",
    # Local Client
    "CAASLocalClient",
    "generate",
    # Models
    "Project",
    "ProjectStatus",
    "GenerationConfig",
    "GenerationResult",
    # Exceptions
    "CAASError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
]
