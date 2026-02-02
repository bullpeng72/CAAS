"""
API Interfaces for UI Independence

Defines protocols and interfaces that UIs must implement
to interact with the CAAS Framework.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol


class UIEvent(Enum):
    """Events sent from Framework to UI"""

    # Progress events
    PHASE_STARTED = "phase.started"
    PHASE_PROGRESS = "phase.progress"
    PHASE_COMPLETED = "phase.completed"

    # Review events
    REVIEW_REQUESTED = "review.requested"

    # Quality events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"

    # Error events
    ERROR_OCCURRED = "error.occurred"


@dataclass
class EventData:
    """Event data sent to UI"""

    event_type: UIEvent
    phase: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0


class UICallback(Protocol):
    """
    UI Callback Interface

    UI implementations must provide this interface
    to receive events from the Framework.
    """

    def on_event(self, event: EventData) -> None:
        """
        Called when Framework emits an event.

        Args:
            event: Event data
        """
        ...


class ReviewType(Enum):
    """Review types for Plan Mode"""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    CODE = "code"


@dataclass
class ReviewRequest:
    """
    Review request data (UI-independent)

    Contains all data needed for UI to display review.
    """

    review_type: ReviewType
    data: Dict[str, Any]  # UI-independent data structure
    options: list[str]  # Available options: ["approve", "edit", "reject"]


class ReviewHandler(Protocol):
    """
    Review Handler Interface

    UI implementations must provide this interface
    to handle review requests from Plan Mode.
    """

    def handle_review(self, request: ReviewRequest) -> str:
        """
        Handle a review request and return user decision.

        Args:
            request: Review request with UI-independent data

        Returns:
            User decision: "approve", "edit", "reject", etc.
        """
        ...
