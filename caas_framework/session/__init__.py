"""
Session Management Module

Multi-session support with context switching.
"""

from caas_framework.session.manager import (
    SessionManager,
    Session,
    SessionContext,
)

__all__ = [
    "SessionManager",
    "Session",
    "SessionContext",
]
