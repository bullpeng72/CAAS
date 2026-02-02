"""
Session Management Module

Multi-session support with context switching.
"""

from caas_framework.session.manager import Session, SessionContext, SessionManager

__all__ = [
    "SessionManager",
    "Session",
    "SessionContext",
]
