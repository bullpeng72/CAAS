"""
Tests for Multi-Model Router

Tests model selection, fallback, and performance tracking.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from caas_framework.plugins.llm.base import LLMMessage, LLMResponse
from caas_framework.plugins.llm.multi_model_router import (
    MultiModelRouter,
    ModelConfig,
    ModelSelectionStrategy,
    ModelPerformanceTracker,
    ModelMetrics
)
from caas_framework.agents.base import AgentPhase


class MockLLMPlugin:
    """Mock LLM plugin for testing"""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.model = name
        self.temperature = 0.3
        self.max_tokens = 4096
        self.should_fail = should_fail
        self.call_count = 0

    async def ainvoke(self, messages, **kwargs):
        self.call_count += 1

        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")

        return LLMResponse(
            content=f"Response from {self.name}",
            model=self.name,
            usage={"total_tokens": 100}
        )

    async def stream(self, messages, **kwargs):
        async def _stream():
            yield f"Chunk from {self.name}"

        return _stream()


def test_model_metrics():
    """Test ModelMetrics tracking"""
    metrics = ModelMetrics(model_name="test-model")

    assert metrics.total_requests == 0
    assert metrics.success_rate == 1.0
    assert metrics.average_latency_ms == 0.0


def test_performance_tracker():
    """Test ModelPerformanceTracker"""
    tracker = ModelPerformanceTracker()

    # Record successful request
    tracker.record_request(
        model_name="model-1",
        success=True,
        latency_ms=100.0,
        tokens_used=50,
        cost_per_1k=0.01
    )

    metrics = tracker.get_metrics("model-1")
    assert metrics is not None
    assert metrics.total_requests == 1
    assert metrics.successful_requests == 1
    assert metrics.success_rate == 1.0

    # Record failed request
    tracker.record_request(
        model_name="model-1",
        success=False,
        latency_ms=50.0
    )

    metrics = tracker.get_metrics("model-1")
    assert metrics.total_requests == 2
    assert metrics.failed_requests == 1
    assert metrics.consecutive_failures == 1


def test_model_health_check():
    """Test model health checking"""
    tracker = ModelPerformanceTracker()

    # Model is healthy initially
    assert tracker.is_model_healthy("model-1")

    # After 2 failures, still healthy
    tracker.record_request("model-1", success=False, latency_ms=100)
    tracker.record_request("model-1", success=False, latency_ms=100)
    assert tracker.is_model_healthy("model-1", max_consecutive_failures=3)

    # After 3 failures, unhealthy
    tracker.record_request("model-1", success=False, latency_ms=100)
    assert not tracker.is_model_healthy("model-1", max_consecutive_failures=3)

    # Success resets consecutive failures
    tracker.record_request("model-1", success=True, latency_ms=100)
    assert tracker.is_model_healthy("model-1", max_consecutive_failures=3)


@pytest.mark.asyncio
async def test_multi_model_router_basic():
    """Test basic multi-model router functionality"""
    # Create mock plugins
    plugin1 = MockLLMPlugin("model-1")
    plugin2 = MockLLMPlugin("model-2")

    # Create model configs
    models = [
        ModelConfig(
            name="model-1",
            plugin=plugin1,
            cost_per_1k_tokens=0.01,
            suitable_phases=[AgentPhase.DISCOVERY],
            priority=2
        ),
        ModelConfig(
            name="model-2",
            plugin=plugin2,
            cost_per_1k_tokens=0.005,
            suitable_phases=[AgentPhase.DELIVERY],
            priority=1
        )
    ]

    # Create router
    router = MultiModelRouter(
        name="test-router",
        models=models,
        strategy=ModelSelectionStrategy.PHASE_BASED
    )

    # Test invocation
    messages = [LLMMessage(role="user", content="test")]
    response = await router.ainvoke(messages, phase=AgentPhase.DISCOVERY)

    assert response.content == "Response from model-1"
    assert plugin1.call_count == 1


@pytest.mark.asyncio
async def test_multi_model_fallback():
    """Test automatic fallback when primary model fails"""
    # Create mock plugins (first fails, second succeeds)
    plugin1 = MockLLMPlugin("model-1", should_fail=True)
    plugin2 = MockLLMPlugin("model-2", should_fail=False)

    models = [
        ModelConfig(
            name="model-1",
            plugin=plugin1,
            priority=2  # Higher priority (tried first)
        ),
        ModelConfig(
            name="model-2",
            plugin=plugin2,
            priority=1  # Lower priority (fallback)
        )
    ]

    router = MultiModelRouter(
        name="test-router",
        models=models,
        enable_fallback=True
    )

    messages = [LLMMessage(role="user", content="test")]
    response = await router.ainvoke(messages)

    # Should fallback to model-2
    assert response.content == "Response from model-2"
    assert plugin1.call_count == 1  # Tried first
    assert plugin2.call_count == 1  # Succeeded on fallback


@pytest.mark.asyncio
async def test_multi_model_all_fail():
    """Test behavior when all models fail"""
    plugin1 = MockLLMPlugin("model-1", should_fail=True)
    plugin2 = MockLLMPlugin("model-2", should_fail=True)

    models = [
        ModelConfig(name="model-1", plugin=plugin1, priority=2),
        ModelConfig(name="model-2", plugin=plugin2, priority=1)
    ]

    router = MultiModelRouter(
        name="test-router",
        models=models,
        enable_fallback=True
    )

    messages = [LLMMessage(role="user", content="test")]

    with pytest.raises(RuntimeError, match="All models failed"):
        await router.ainvoke(messages)


def test_phase_based_selection():
    """Test phase-based model selection"""
    plugin1 = MockLLMPlugin("model-1")
    plugin2 = MockLLMPlugin("model-2")

    models = [
        ModelConfig(
            name="model-1",
            plugin=plugin1,
            suitable_phases=[AgentPhase.DISCOVERY, AgentPhase.ARCHITECTURE],
            priority=2
        ),
        ModelConfig(
            name="model-2",
            plugin=plugin2,
            suitable_phases=[AgentPhase.DELIVERY],
            priority=1
        )
    ]

    router = MultiModelRouter(
        name="test-router",
        models=models,
        strategy=ModelSelectionStrategy.PHASE_BASED
    )

    # Should select model-1 for DISCOVERY
    selected = router.select_model(phase=AgentPhase.DISCOVERY)
    assert selected == "model-1"

    # Should select model-2 for DELIVERY
    selected = router.select_model(phase=AgentPhase.DELIVERY)
    assert selected == "model-2"


def test_cost_optimized_selection():
    """Test cost-optimized model selection"""
    plugin1 = MockLLMPlugin("expensive-model")
    plugin2 = MockLLMPlugin("cheap-model")

    models = [
        ModelConfig(
            name="expensive-model",
            plugin=plugin1,
            cost_per_1k_tokens=0.03,  # Expensive
            priority=2
        ),
        ModelConfig(
            name="cheap-model",
            plugin=plugin2,
            cost_per_1k_tokens=0.001,  # Cheap
            priority=1
        )
    ]

    router = MultiModelRouter(
        name="test-router",
        models=models,
        strategy=ModelSelectionStrategy.COST_OPTIMIZED
    )

    # Should select cheapest model
    selected = router.select_model()
    assert selected == "cheap-model"


def test_performance_report():
    """Test performance report generation"""
    plugin1 = MockLLMPlugin("model-1")

    models = [
        ModelConfig(name="model-1", plugin=plugin1, cost_per_1k_tokens=0.01)
    ]

    router = MultiModelRouter(
        name="test-router",
        models=models
    )

    # Record some metrics
    router.performance_tracker.record_request(
        model_name="model-1",
        success=True,
        latency_ms=150.0,
        tokens_used=100,
        cost_per_1k=0.01
    )

    # Get report
    report = router.get_performance_report()

    assert report["total_models"] == 1
    assert "model-1" in report["models"]
    assert report["models"]["model-1"]["total_requests"] == 1
    assert "100.0%" in report["models"]["model-1"]["success_rate"]
