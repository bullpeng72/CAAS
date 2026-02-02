"""
Design Patterns Module

Implements common AI agent collaboration patterns for enhanced quality and reliability.
"""

from caas_framework.patterns.producer_critic import (
    CriticAgent,
    CriticReview,
    CriticRole,
    ProducerCriticPattern,
    ProducerCriticResult,
    collaborate_with_critic,
)

__all__ = [
    # Producer-Critic Pattern
    "ProducerCriticPattern",
    "CriticAgent",
    "CriticRole",
    "CriticReview",
    "ProducerCriticResult",
    "collaborate_with_critic",
]
