"""
Event Bus Implementation

Provides publish-subscribe event bus for decoupled communication
between system components.
"""

import asyncio
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from caas_framework.events.events import (
    Event,
    EventHandler,
    EventSubscription,
    PhaseEvent,
)
from caas_framework.utils.logger import get_logger

logger = get_logger()


class EventBus:
    """
    Central event bus for publish-subscribe pattern.

    Allows components to publish events and subscribe to event types
    without direct coupling.
    """

    def __init__(self, name: str = "default"):
        """
        Initialize event bus.

        Args:
            name: Name of the event bus
        """
        self.name = name
        self._subscriptions: Dict[PhaseEvent, List[EventSubscription]] = defaultdict(
            list
        )
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._enabled = True

    def subscribe(
        self,
        event_type: PhaseEvent,
        handler: EventHandler,
        filter_fn: Optional[Callable[[Event], bool]] = None,
        priority: int = 0,
    ) -> EventSubscription:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle events
            filter_fn: Optional filter function
            priority: Handler priority (higher = called first)

        Returns:
            EventSubscription instance
        """
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            priority=priority,
        )

        self._subscriptions[event_type].append(subscription)

        # Sort by priority (descending)
        self._subscriptions[event_type].sort(key=lambda s: s.priority, reverse=True)

        logger.debug(f"Subscribed to {event_type.value} (priority={priority})")

        return subscription

    def unsubscribe(self, subscription: EventSubscription):
        """
        Unsubscribe from event type.

        Args:
            subscription: Subscription to remove
        """
        if subscription.event_type in self._subscriptions:
            try:
                self._subscriptions[subscription.event_type].remove(subscription)
                logger.debug(f"Unsubscribed from {subscription.event_type.value}")
            except ValueError:
                pass

    def publish(self, event: Event, async_mode: bool = False):
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
            async_mode: Whether to handle async (non-blocking)
        """
        if not self._enabled:
            logger.warning("EventBus is disabled, event not published")
            return

        # Add to history
        self._add_to_history(event)

        logger.debug(f"Publishing event: {event}")

        # Get subscriptions for this event type
        subscriptions = self._subscriptions.get(event.type, [])

        if not subscriptions:
            logger.debug(f"No subscribers for {event.type.value}")
            return

        # Call handlers
        for subscription in subscriptions:
            if subscription.should_handle(event):
                try:
                    if async_mode:
                        # Fire and forget
                        asyncio.create_task(
                            self._async_handle(subscription.handler, event)
                        )
                    else:
                        subscription.handler(event)
                except Exception as e:
                    logger.error(
                        f"Error in event handler for {event.type.value}: {e}",
                        exc_info=True,
                    )

    async def publish_async(self, event: Event):
        """
        Publish event asynchronously to all subscribers.

        Args:
            event: Event to publish
        """
        if not self._enabled:
            logger.warning("EventBus is disabled, event not published")
            return

        # Add to history
        self._add_to_history(event)

        logger.debug(f"Publishing event (async): {event}")

        # Get subscriptions
        subscriptions = self._subscriptions.get(event.type, [])

        if not subscriptions:
            return

        # Call all handlers concurrently
        tasks = []
        for subscription in subscriptions:
            if subscription.should_handle(event):
                tasks.append(self._async_handle(subscription.handler, event))

        # Wait for all handlers
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _async_handle(self, handler: EventHandler, event: Event):
        """Handle event asynchronously."""
        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync handler in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)
        except Exception as e:
            logger.error(
                f"Error in async event handler for {event.type.value}: {e}",
                exc_info=True,
            )

    def _add_to_history(self, event: Event):
        """Add event to history."""
        self._event_history.append(event)

        # Trim history if needed
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

    def get_event_history(
        self, event_type: Optional[PhaseEvent] = None, limit: Optional[int] = None
    ) -> List[Event]:
        """
        Get event history.

        Args:
            event_type: Optional filter by event type
            limit: Optional limit on number of events

        Returns:
            List of events
        """
        history = self._event_history

        if event_type:
            history = [e for e in history if e.type == event_type]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()

    def enable(self):
        """Enable event bus."""
        self._enabled = True
        logger.info("EventBus enabled")

    def disable(self):
        """Disable event bus."""
        self._enabled = False
        logger.info("EventBus disabled")

    def is_enabled(self) -> bool:
        """Check if event bus is enabled."""
        return self._enabled

    def get_subscription_count(self, event_type: Optional[PhaseEvent] = None) -> int:
        """
        Get number of subscriptions.

        Args:
            event_type: Optional filter by event type

        Returns:
            Number of subscriptions
        """
        if event_type:
            return len(self._subscriptions.get(event_type, []))
        else:
            return sum(len(subs) for subs in self._subscriptions.values())

    def get_statistics(self) -> Dict[str, any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with statistics
        """
        event_type_counts = defaultdict(int)
        for event in self._event_history:
            event_type_counts[event.type.value] += 1

        return {
            "name": self.name,
            "enabled": self._enabled,
            "total_subscriptions": self.get_subscription_count(),
            "subscriptions_by_type": {
                event_type.value: len(subs)
                for event_type, subs in self._subscriptions.items()
            },
            "total_events_published": len(self._event_history),
            "events_by_type": dict(event_type_counts),
        }


# Global event bus instance
_global_event_bus = EventBus(name="global")


def get_global_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return _global_event_bus


def reset_global_event_bus():
    """Reset the global event bus (useful for testing)."""
    global _global_event_bus
    _global_event_bus = EventBus(name="global")
