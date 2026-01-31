"""
Event Definitions

Defines event types and event data structures for the event-driven system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Protocol
from datetime import datetime
import time


class PhaseEvent(Enum):
    """Event types for different phases and operations."""
    # Phase lifecycle events
    PHASE_STARTED = "phase.started"
    PHASE_COMPLETED = "phase.completed"
    PHASE_FAILED = "phase.failed"

    # Validation events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"

    # Feedback events
    FEEDBACK_REQUESTED = "feedback.requested"
    FEEDBACK_RECEIVED = "feedback.received"

    # Generation events
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"

    # Quality events
    QUALITY_CHECK_STARTED = "quality_check.started"
    QUALITY_CHECK_PASSED = "quality_check.passed"
    QUALITY_CHECK_FAILED = "quality_check.failed"

    # System events
    SYSTEM_READY = "system.ready"
    SYSTEM_ERROR = "system.error"


@dataclass
class Event:
    """
    Represents an event in the system.

    Events are published to the event bus and handled by subscribers.
    """
    type: PhaseEvent
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def datetime(self) -> datetime:
        """Get event timestamp as datetime."""
        return datetime.fromtimestamp(self.timestamp)

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data value safely."""
        return self.data.get(key, default)

    def __str__(self) -> str:
        """String representation of event."""
        return f"Event({self.type.value}, source={self.source}, data_keys={list(self.data.keys())})"


class EventHandler(Protocol):
    """Protocol for event handlers."""

    def __call__(self, event: Event) -> None:
        """Handle an event."""
        ...


@dataclass
class EventSubscription:
    """Represents a subscription to an event type."""
    event_type: PhaseEvent
    handler: EventHandler
    filter_fn: Optional[Callable[[Event], bool]] = None
    priority: int = 0  # Higher priority handlers are called first

    def should_handle(self, event: Event) -> bool:
        """Check if this subscription should handle the event."""
        if event.type != self.event_type:
            return False
        if self.filter_fn:
            return self.filter_fn(event)
        return True


def create_phase_event(
    event_type: PhaseEvent,
    phase_name: str,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Event:
    """
    Convenience function to create a phase event.

    Args:
        event_type: Type of event
        phase_name: Name of the phase
        data: Event data
        **kwargs: Additional metadata

    Returns:
        Event instance
    """
    event_data = data or {}
    event_data['phase'] = phase_name

    return Event(
        type=event_type,
        data=event_data,
        source=phase_name,
        metadata=kwargs
    )


def create_validation_event(
    passed: bool,
    phase_name: str,
    issues: Optional[list] = None,
    **kwargs
) -> Event:
    """
    Convenience function to create a validation event.

    Args:
        passed: Whether validation passed
        phase_name: Name of the phase
        issues: List of validation issues
        **kwargs: Additional metadata

    Returns:
        Event instance
    """
    event_type = PhaseEvent.VALIDATION_PASSED if passed else PhaseEvent.VALIDATION_FAILED

    data = {
        'phase': phase_name,
        'passed': passed,
        'issues': issues or []
    }

    return Event(
        type=event_type,
        data=data,
        source=f"{phase_name}_validator",
        metadata=kwargs
    )


def create_feedback_event(
    message: str,
    phase_name: str,
    feedback_type: str = "info",
    **kwargs
) -> Event:
    """
    Convenience function to create a feedback event.

    Args:
        message: Feedback message
        phase_name: Name of the phase
        feedback_type: Type of feedback (info, warning, error)
        **kwargs: Additional metadata

    Returns:
        Event instance
    """
    data = {
        'phase': phase_name,
        'message': message,
        'feedback_type': feedback_type
    }

    return Event(
        type=PhaseEvent.FEEDBACK_REQUESTED,
        data=data,
        source=phase_name,
        metadata=kwargs
    )
