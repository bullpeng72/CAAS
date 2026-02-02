"""
Event-Driven Architecture for CaaS Framework

Provides event bus, async orchestration, and parallel processing
for improved performance and scalability.
"""

from caas_framework.events.async_orchestrator import AsyncOrchestrator, PhaseResult
from caas_framework.events.event_bus import EventBus, get_global_event_bus
from caas_framework.events.events import (
    Event,
    EventHandler,
    EventSubscription,
    PhaseEvent,
    create_feedback_event,
    create_phase_event,
    create_validation_event,
)

__all__ = [
    "PhaseEvent",
    "Event",
    "EventHandler",
    "EventSubscription",
    "EventBus",
    "get_global_event_bus",
    "AsyncOrchestrator",
    "PhaseResult",
    "create_phase_event",
    "create_validation_event",
    "create_feedback_event",
]
