"""
Tests for Event-Driven Architecture

Tests the event bus, async orchestration, and parallel execution.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest

from caas_framework.events import (
    AsyncOrchestrator,
    Event,
    EventBus,
    PhaseEvent,
    PhaseResult,
    create_feedback_event,
    create_phase_event,
    create_validation_event,
    get_global_event_bus,
)
from caas_framework.events.async_orchestrator import (
    PhaseDefinition,
    create_phase_definition,
)


class TestEvent:
    """Test Event class."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=PhaseEvent.PHASE_STARTED,
            data={'phase': 'concretization'},
            source='concretizer'
        )

        assert event.type == PhaseEvent.PHASE_STARTED
        assert event.data['phase'] == 'concretization'
        assert event.source == 'concretizer'

    def test_event_get_data(self):
        """Test getting data from event."""
        event = Event(
            type=PhaseEvent.PHASE_COMPLETED,
            data={'result': 'success'}
        )

        assert event.get_data('result') == 'success'
        assert event.get_data('missing', 'default') == 'default'

    def test_create_phase_event(self):
        """Test creating phase event."""
        event = create_phase_event(
            PhaseEvent.PHASE_STARTED,
            'design',
            {'agents': 3}
        )

        assert event.type == PhaseEvent.PHASE_STARTED
        assert event.data['phase'] == 'design'
        assert event.data['agents'] == 3

    def test_create_validation_event(self):
        """Test creating validation event."""
        event = create_validation_event(
            passed=False,
            phase_name='architecture',
            issues=['Missing component']
        )

        assert event.type == PhaseEvent.VALIDATION_FAILED
        assert event.data['passed'] is False
        assert len(event.data['issues']) == 1

    def test_create_feedback_event(self):
        """Test creating feedback event."""
        event = create_feedback_event(
            message="Need more details",
            phase_name="concretization",
            feedback_type="warning"
        )

        assert event.type == PhaseEvent.FEEDBACK_REQUESTED
        assert event.data['message'] == "Need more details"
        assert event.data['feedback_type'] == "warning"


class TestEventBus:
    """Test EventBus class."""

    @pytest.fixture
    def event_bus(self):
        """Create event bus for testing."""
        return EventBus(name="test")

    def test_event_bus_creation(self, event_bus):
        """Test creating event bus."""
        assert event_bus.name == "test"
        assert event_bus.is_enabled()

    def test_subscribe(self, event_bus):
        """Test subscribing to events."""
        handler = Mock()

        subscription = event_bus.subscribe(
            PhaseEvent.PHASE_STARTED,
            handler
        )

        assert subscription.event_type == PhaseEvent.PHASE_STARTED
        assert event_bus.get_subscription_count(PhaseEvent.PHASE_STARTED) == 1

    def test_publish_and_receive(self, event_bus):
        """Test publishing and receiving events."""
        handler = Mock()

        event_bus.subscribe(PhaseEvent.PHASE_COMPLETED, handler)

        event = Event(
            type=PhaseEvent.PHASE_COMPLETED,
            data={'result': 'success'}
        )

        event_bus.publish(event)

        handler.assert_called_once()
        assert handler.call_args[0][0].type == PhaseEvent.PHASE_COMPLETED

    def test_multiple_handlers(self, event_bus):
        """Test multiple handlers for same event type."""
        handler1 = Mock()
        handler2 = Mock()

        event_bus.subscribe(PhaseEvent.PHASE_STARTED, handler1)
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, handler2)

        event = Event(type=PhaseEvent.PHASE_STARTED)
        event_bus.publish(event)

        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_handler_priority(self, event_bus):
        """Test handler priority ordering."""
        call_order = []

        def handler1(event):
            call_order.append(1)

        def handler2(event):
            call_order.append(2)

        # Subscribe with priorities
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, handler1, priority=1)
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, handler2, priority=2)

        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))

        # Higher priority (2) should be called first
        assert call_order == [2, 1]

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        handler = Mock()

        subscription = event_bus.subscribe(PhaseEvent.PHASE_FAILED, handler)

        assert event_bus.get_subscription_count(PhaseEvent.PHASE_FAILED) == 1

        event_bus.unsubscribe(subscription)

        assert event_bus.get_subscription_count(PhaseEvent.PHASE_FAILED) == 0

    def test_event_history(self, event_bus):
        """Test event history tracking."""
        event1 = Event(type=PhaseEvent.PHASE_STARTED)
        event2 = Event(type=PhaseEvent.PHASE_COMPLETED)

        event_bus.publish(event1)
        event_bus.publish(event2)

        history = event_bus.get_event_history()
        assert len(history) == 2

    def test_filter_event_history(self, event_bus):
        """Test filtering event history."""
        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))
        event_bus.publish(Event(type=PhaseEvent.PHASE_COMPLETED))
        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))

        started_events = event_bus.get_event_history(
            event_type=PhaseEvent.PHASE_STARTED
        )

        assert len(started_events) == 2

    def test_clear_history(self, event_bus):
        """Test clearing event history."""
        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))
        assert len(event_bus.get_event_history()) == 1

        event_bus.clear_history()
        assert len(event_bus.get_event_history()) == 0

    def test_disable_event_bus(self, event_bus):
        """Test disabling event bus."""
        handler = Mock()
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, handler)

        event_bus.disable()

        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))

        # Handler should not be called
        handler.assert_not_called()

    def test_get_statistics(self, event_bus):
        """Test getting event bus statistics."""
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, Mock())
        event_bus.subscribe(PhaseEvent.PHASE_COMPLETED, Mock())

        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))
        event_bus.publish(Event(type=PhaseEvent.PHASE_STARTED))

        stats = event_bus.get_statistics()

        assert stats['total_subscriptions'] == 2
        assert stats['total_events_published'] == 2

    @pytest.mark.asyncio
    async def test_publish_async(self, event_bus):
        """Test async event publishing."""
        handler = AsyncMock()

        event_bus.subscribe(PhaseEvent.PHASE_COMPLETED, handler)

        event = Event(type=PhaseEvent.PHASE_COMPLETED)
        await event_bus.publish_async(event)

        handler.assert_called_once()

    def test_global_event_bus(self):
        """Test global event bus."""
        global_bus = get_global_event_bus()

        assert global_bus is not None
        assert global_bus.name == "global"


class TestAsyncOrchestrator:
    """Test AsyncOrchestrator class."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for testing."""
        event_bus = EventBus(name="test")
        return AsyncOrchestrator(event_bus=event_bus, max_workers=2)

    @pytest.mark.asyncio
    async def test_execute_phase_async(self, orchestrator):
        """Test executing a phase asynchronously."""
        def executor(context):
            return "result"

        phase_def = PhaseDefinition(
            name="test_phase",
            executor=executor
        )

        result = await orchestrator.execute_phase_async(phase_def, {})

        assert result.success
        assert result.result == "result"
        assert result.phase_name == "test_phase"

    @pytest.mark.asyncio
    async def test_execute_phase_async_with_async_executor(self, orchestrator):
        """Test executing phase with async executor."""
        async def async_executor(context):
            await asyncio.sleep(0.01)
            return "async_result"

        phase_def = PhaseDefinition(
            name="async_phase",
            executor=async_executor
        )

        result = await orchestrator.execute_phase_async(phase_def, {})

        assert result.success
        assert result.result == "async_result"

    @pytest.mark.asyncio
    async def test_execute_phase_failure(self, orchestrator):
        """Test phase execution failure."""
        def failing_executor(context):
            raise ValueError("Test error")

        phase_def = PhaseDefinition(
            name="failing_phase",
            executor=failing_executor
        )

        result = await orchestrator.execute_phase_async(phase_def, {})

        assert not result.success
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_execute_phase_timeout(self, orchestrator):
        """Test phase execution timeout."""
        async def slow_executor(context):
            await asyncio.sleep(1.0)
            return "too_slow"

        phase_def = PhaseDefinition(
            name="slow_phase",
            executor=slow_executor,
            timeout=0.1  # 100ms timeout
        )

        result = await orchestrator.execute_phase_async(phase_def, {})

        assert not result.success
        assert isinstance(result.error, TimeoutError)

    @pytest.mark.asyncio
    async def test_execute_parallel(self, orchestrator):
        """Test parallel phase execution."""
        def executor1(context):
            time.sleep(0.01)
            return "result1"

        def executor2(context):
            time.sleep(0.01)
            return "result2"

        phase_defs = [
            PhaseDefinition(name="phase1", executor=executor1),
            PhaseDefinition(name="phase2", executor=executor2)
        ]

        start = time.time()
        results = await orchestrator.execute_parallel(phase_defs, {})
        duration = time.time() - start

        # Should run in parallel, so total time < sum of individual times
        assert len(results) == 2
        assert all(r.success for r in results)
        # Parallel execution should be faster than sequential (0.02s)
        assert duration < 0.03

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self, orchestrator):
        """Test execution with dependencies."""
        def executor1(context):
            return "result1"

        def executor2(context):
            # Depends on phase1
            return f"result2_after_{context.get('phase1')}"

        def executor3(context):
            # Depends on phase2
            return f"result3_after_{context.get('phase2')}"

        phase_defs = [
            PhaseDefinition(name="phase1", executor=executor1),
            PhaseDefinition(name="phase2", executor=executor2, dependencies=["phase1"]),
            PhaseDefinition(name="phase3", executor=executor3, dependencies=["phase2"])
        ]

        results = await orchestrator.execute_with_dependencies(phase_defs, {})

        assert len(results) == 3
        assert all(r.success for r in results.values())
        assert results["phase2"].result == "result2_after_result1"
        assert results["phase3"].result == "result3_after_result2_after_result1"

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, orchestrator):
        """Test executing complete pipeline."""
        def phase_a(context):
            return "A"

        def phase_b(context):
            return f"B-{context['phase_a']}"

        def phase_c(context):
            return f"C-{context['phase_b']}"

        phase_defs = [
            create_phase_definition("phase_a", phase_a),
            create_phase_definition("phase_b", phase_b, dependencies=["phase_a"]),
            create_phase_definition("phase_c", phase_c, dependencies=["phase_b"])
        ]

        results = await orchestrator.execute_pipeline(phase_defs)

        assert len(results) == 3
        assert results["phase_c"].result == "C-B-A"

    @pytest.mark.asyncio
    async def test_parallel_independent_phases(self, orchestrator):
        """Test parallel execution of independent phases."""
        execution_order = []

        def phase_a(context):
            execution_order.append("A")
            time.sleep(0.02)
            return "A"

        def phase_b(context):
            execution_order.append("B")
            time.sleep(0.02)
            return "B"

        def phase_c(context):
            # Depends on both A and B
            execution_order.append("C")
            return f"C-{context['phase_a']}-{context['phase_b']}"

        phase_defs = [
            PhaseDefinition(name="phase_a", executor=phase_a),
            PhaseDefinition(name="phase_b", executor=phase_b),
            PhaseDefinition(name="phase_c", executor=phase_c, dependencies=["phase_a", "phase_b"])
        ]

        start = time.time()
        results = await orchestrator.execute_with_dependencies(phase_defs, {})
        duration = time.time() - start

        # A and B should run in parallel
        assert len(results) == 3
        # C should run after both A and B
        assert execution_order[-1] == "C"
        # Parallel should be faster than sequential (0.06s)
        assert duration < 0.05

    def test_get_execution_summary(self, orchestrator):
        """Test getting execution summary."""
        results = {
            'phase1': PhaseResult('phase1', True, 'result1', execution_time=1.0),
            'phase2': PhaseResult('phase2', True, 'result2', execution_time=2.0),
            'phase3': PhaseResult('phase3', False, error=ValueError(), execution_time=0.5)
        }

        summary = orchestrator.get_execution_summary(results)

        assert summary['total_phases'] == 3
        assert summary['successful'] == 2
        assert summary['failed'] == 1
        assert summary['total_execution_time'] == 3.5


class TestPhaseDefinition:
    """Test PhaseDefinition."""

    def test_phase_definition_creation(self):
        """Test creating phase definition."""
        def executor(context):
            return "result"

        phase_def = PhaseDefinition(
            name="test",
            executor=executor,
            dependencies=["phase1"],
            timeout=10.0
        )

        assert phase_def.name == "test"
        assert phase_def.dependencies == ["phase1"]
        assert phase_def.timeout == 10.0

    def test_create_phase_definition_convenience(self):
        """Test convenience function."""
        def executor(context):
            return "result"

        phase_def = create_phase_definition(
            "test",
            executor,
            dependencies=["phase1"]
        )

        assert phase_def.name == "test"
        assert phase_def.dependencies == ["phase1"]


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_event_driven_workflow(self):
        """Test complete event-driven workflow."""
        event_bus = EventBus(name="integration_test")
        orchestrator = AsyncOrchestrator(event_bus=event_bus)

        # Track events
        events_received = []

        def event_handler(event):
            events_received.append(event.type)

        # Subscribe to all phase events
        event_bus.subscribe(PhaseEvent.PHASE_STARTED, event_handler)
        event_bus.subscribe(PhaseEvent.PHASE_COMPLETED, event_handler)

        # Define phases
        def phase1(context):
            return "data1"

        def phase2(context):
            return f"data2-{context['phase1']}"

        phases = [
            create_phase_definition("phase1", phase1),
            create_phase_definition("phase2", phase2, dependencies=["phase1"])
        ]

        # Execute pipeline
        results = await orchestrator.execute_pipeline(phases)

        # Verify execution
        assert all(r.success for r in results.values())
        assert results["phase2"].result == "data2-data1"

        # Verify events
        assert PhaseEvent.PHASE_STARTED in events_received
        assert PhaseEvent.PHASE_COMPLETED in events_received

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self):
        """Test error handling in pipeline."""
        orchestrator = AsyncOrchestrator()

        def phase1(context):
            return "success"

        def phase2(context):
            raise ValueError("Intentional error")

        def phase3(context):
            # Should not execute due to phase2 failure
            return "should_not_run"

        phases = [
            create_phase_definition("phase1", phase1),
            create_phase_definition("phase2", phase2, dependencies=["phase1"]),
            create_phase_definition("phase3", phase3, dependencies=["phase2"])
        ]

        results = await orchestrator.execute_with_dependencies(phases, {})

        # Phase1 should succeed
        assert results["phase1"].success

        # Phase2 should fail
        assert not results["phase2"].success

        # Phase3 should not be in results (dependency failed)
        assert "phase3" not in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
