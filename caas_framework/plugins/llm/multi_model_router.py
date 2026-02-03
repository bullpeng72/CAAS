"""
Multi-Model Router

Enables intelligent routing across multiple LLM models with:
- Phase-specific model selection
- Automatic fallback chains
- Cost-aware routing
- Performance tracking
- Failure-based model switching
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from caas_framework.agents.base import AgentPhase
from caas_framework.plugins.llm.base import LLMMessage, LLMPlugin, LLMResponse
from caas_framework.utils.logger import get_logger


class ModelSelectionStrategy(str, Enum):
    """Model selection strategies"""

    PHASE_BASED = "phase_based"  # Select based on phase complexity
    COST_OPTIMIZED = "cost_optimized"  # Always use cheapest model
    PERFORMANCE_FIRST = "performance_first"  # Use fastest/best model
    ADAPTIVE = "adaptive"  # Learn from performance history


@dataclass
class ModelMetrics:
    """Performance metrics for a model"""

    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def average_cost_per_request(self) -> float:
        """Calculate average cost per request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_cost_usd / self.total_requests


@dataclass
class ModelConfig:
    """Configuration for a single model"""

    name: str
    plugin: LLMPlugin
    cost_per_1k_tokens: float = 0.0  # Cost per 1000 tokens
    max_tokens: int = 4096  # Maximum tokens
    suitable_phases: List[AgentPhase] = field(default_factory=list)  # Best phases for this model
    priority: int = 1  # Higher = higher priority (used in fallback)


class ModelPerformanceTracker:
    """Tracks performance metrics for all models"""

    def __init__(self):
        self.metrics: Dict[str, ModelMetrics] = {}
        self.logger = get_logger()

    def record_request(
        self,
        model_name: str,
        success: bool,
        latency_ms: float,
        tokens_used: int = 0,
        cost_per_1k: float = 0.0,
    ):
        """Record a model request"""
        if model_name not in self.metrics:
            self.metrics[model_name] = ModelMetrics(model_name=model_name)

        metrics = self.metrics[model_name]
        metrics.total_requests += 1

        if success:
            metrics.successful_requests += 1
            metrics.total_latency_ms += latency_ms
            metrics.consecutive_failures = 0
        else:
            metrics.failed_requests += 1
            metrics.last_failure = datetime.now()
            metrics.consecutive_failures += 1

        # Calculate cost
        if tokens_used > 0:
            cost = (tokens_used / 1000.0) * cost_per_1k
            metrics.total_cost_usd += cost

    def get_metrics(self, model_name: str) -> Optional[ModelMetrics]:
        """Get metrics for a model"""
        return self.metrics.get(model_name)

    def get_all_metrics(self) -> Dict[str, ModelMetrics]:
        """Get all metrics"""
        return self.metrics.copy()

    def is_model_healthy(self, model_name: str, max_consecutive_failures: int = 3) -> bool:
        """Check if model is healthy (not failing repeatedly)"""
        metrics = self.get_metrics(model_name)
        if not metrics:
            return True  # Unknown model assumed healthy

        return metrics.consecutive_failures < max_consecutive_failures

    def get_best_model_by_metric(
        self, available_models: List[str], metric: str = "success_rate"
    ) -> Optional[str]:
        """Get best model based on a metric"""
        if not available_models:
            return None

        # Filter to models we have metrics for
        models_with_metrics = [
            m for m in available_models if m in self.metrics and self.metrics[m].total_requests > 0
        ]

        if not models_with_metrics:
            # Return first available if no metrics
            return available_models[0]

        # Sort by metric
        if metric == "success_rate":
            return max(models_with_metrics, key=lambda m: self.metrics[m].success_rate)
        elif metric == "latency":
            return min(models_with_metrics, key=lambda m: self.metrics[m].average_latency_ms)
        elif metric == "cost":
            return min(models_with_metrics, key=lambda m: self.metrics[m].average_cost_per_request)
        else:
            return models_with_metrics[0]


class MultiModelRouter(LLMPlugin):
    """
    Multi-model router with intelligent model selection and fallback.

    Features:
    - Automatic model selection based on phase/task
    - Fallback chain (try models in order until success)
    - Performance tracking and adaptive routing
    - Cost optimization
    """

    def __init__(
        self,
        name: str,
        models: List[ModelConfig],
        strategy: ModelSelectionStrategy = ModelSelectionStrategy.PHASE_BASED,
        enable_fallback: bool = True,
        max_retries_per_model: int = 1,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize multi-model router.

        Args:
            name: Router name
            models: List of model configurations
            strategy: Model selection strategy
            enable_fallback: Enable automatic fallback to other models
            max_retries_per_model: Max retries per model before fallback
            logger: Optional logger
        """
        # Initialize as LLMPlugin with first model's config
        if not models:
            raise ValueError("At least one model must be provided")

        first_model = models[0].plugin
        super().__init__(
            name=name,
            config={
                "model": first_model.model,
                "temperature": first_model.temperature,
                "max_tokens": first_model.max_tokens,
            },
        )

        self.models = {model.name: model for model in models}
        self.strategy = strategy
        self.enable_fallback = enable_fallback
        self.max_retries_per_model = max_retries_per_model
        self.logger = logger or logging.getLogger(__name__)
        self.performance_tracker = ModelPerformanceTracker()

        # Phase-to-model mapping (for PHASE_BASED strategy)
        self.phase_model_map = self._build_phase_model_map()

        self.logger.info(
            f"🔀 MultiModelRouter initialized with {len(models)} models: "
            f"{', '.join(self.models.keys())}"
        )

    async def initialize(self) -> None:
        """
        Initialize all managed models.

        Calls initialize() on each model plugin.
        """
        for model_config in self.models.values():
            if not model_config.plugin.is_initialized:
                await model_config.plugin.initialize()

        self._initialized = True
        self.logger.debug("✅ MultiModelRouter initialized")

    async def close(self) -> None:
        """
        Close all managed models.

        Calls close() on each model plugin.
        """
        for model_config in self.models.values():
            await model_config.plugin.close()

        self.logger.debug("🔌 MultiModelRouter closed")

    async def health_check(self) -> bool:
        """
        Check health of all models.

        Returns True if at least one model is healthy.
        """
        healthy_count = 0

        for model_config in self.models.values():
            try:
                if await model_config.plugin.health_check():
                    healthy_count += 1
            except Exception as e:
                self.logger.warning(f"Health check failed for {model_config.name}: {e}")

        is_healthy = healthy_count > 0
        self.logger.debug(f"📊 Health check: {healthy_count}/{len(self.models)} models healthy")

        return is_healthy

    def _build_phase_model_map(self) -> Dict[AgentPhase, str]:
        """Build phase-to-model mapping based on model configurations"""
        phase_map = {}

        for model_config in self.models.values():
            for phase in model_config.suitable_phases:
                # Use highest priority model for each phase
                if phase not in phase_map:
                    phase_map[phase] = model_config.name
                else:
                    current_priority = self.models[phase_map[phase]].priority
                    if model_config.priority > current_priority:
                        phase_map[phase] = model_config.name

        return phase_map

    def select_model(
        self, phase: Optional[AgentPhase] = None, prefer_low_cost: bool = False
    ) -> str:
        """
        Select best model based on strategy and context.

        Args:
            phase: Current agent phase
            prefer_low_cost: Prefer lower cost models

        Returns:
            Model name
        """
        if self.strategy == ModelSelectionStrategy.PHASE_BASED and phase:
            # Use phase-specific model if available
            if phase in self.phase_model_map:
                model_name = self.phase_model_map[phase]
                if self.performance_tracker.is_model_healthy(model_name):
                    return model_name

        elif self.strategy == ModelSelectionStrategy.COST_OPTIMIZED:
            # Select cheapest model
            cheapest = min(self.models.values(), key=lambda m: m.cost_per_1k_tokens)
            return cheapest.name

        elif self.strategy == ModelSelectionStrategy.PERFORMANCE_FIRST:
            # Select best performing model
            best = self.performance_tracker.get_best_model_by_metric(
                list(self.models.keys()), metric="success_rate"
            )
            if best and self.performance_tracker.is_model_healthy(best):
                return best

        elif self.strategy == ModelSelectionStrategy.ADAPTIVE:
            # Adaptive: balance cost and performance
            if prefer_low_cost:
                # Optimize for cost while maintaining quality
                best = self.performance_tracker.get_best_model_by_metric(
                    list(self.models.keys()), metric="cost"
                )
            else:
                # Optimize for performance
                best = self.performance_tracker.get_best_model_by_metric(
                    list(self.models.keys()), metric="success_rate"
                )

            if best and self.performance_tracker.is_model_healthy(best):
                return best

        # Fallback: return highest priority model
        return max(self.models.values(), key=lambda m: m.priority).name

    def get_fallback_chain(self, primary_model: str) -> List[str]:
        """
        Get fallback chain starting from primary model.

        Args:
            primary_model: Primary model to try first

        Returns:
            List of model names in priority order
        """
        # Start with primary
        chain = [primary_model]

        # Add other models by priority, excluding unhealthy ones
        other_models = sorted(
            [m for name, m in self.models.items() if name != primary_model],
            key=lambda m: m.priority,
            reverse=True,
        )

        for model_config in other_models:
            if self.performance_tracker.is_model_healthy(model_config.name):
                chain.append(model_config.name)

        return chain

    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        phase: Optional[AgentPhase] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Async LLM call with automatic model selection and fallback.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            response_format: "text" or "json"
            phase: Current agent phase (for phase-based selection)
            **kwargs: Provider-specific args

        Returns:
            LLMResponse
        """
        # Select primary model
        primary_model_name = self.select_model(phase=phase)

        # Get fallback chain
        if self.enable_fallback:
            model_chain = self.get_fallback_chain(primary_model_name)
        else:
            model_chain = [primary_model_name]

        last_error = None

        # Try models in fallback chain
        for model_name in model_chain:
            model_config = self.models[model_name]
            start_time = time.time()

            try:
                self.logger.debug(f"🔀 Trying model: {model_name}")

                # Call model
                response = await model_config.plugin.ainvoke(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    **kwargs,
                )

                # Record success
                latency_ms = (time.time() - start_time) * 1000
                tokens_used = response.usage.get("total_tokens", 0) if response.usage else 0
                self.performance_tracker.record_request(
                    model_name=model_name,
                    success=True,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    cost_per_1k=model_config.cost_per_1k_tokens,
                )

                self.logger.debug(
                    f"✅ Model {model_name} succeeded "
                    f"({latency_ms:.0f}ms, {tokens_used} tokens)"
                )

                return response

            except Exception as e:
                # Record failure
                latency_ms = (time.time() - start_time) * 1000
                self.performance_tracker.record_request(
                    model_name=model_name, success=False, latency_ms=latency_ms
                )

                last_error = e
                self.logger.warning(f"❌ Model {model_name} failed: {str(e)}")

                # Continue to next model in chain
                continue

        # All models failed
        error_msg = f"All models failed. Last error: {str(last_error)}"
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        phase: Optional[AgentPhase] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Streaming LLM call with model selection.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            phase: Current agent phase
            **kwargs: Provider-specific args

        Yields:
            Token chunks
        """
        # Select model (streaming doesn't use fallback for simplicity)
        model_name = self.select_model(phase=phase)
        model_config = self.models[model_name]

        self.logger.debug(f"🔀 Streaming with model: {model_name}")

        # Stream from selected model
        async for chunk in model_config.plugin.stream(
            messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        ):
            yield chunk

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get performance report for all models.

        Returns:
            Dictionary with performance metrics
        """
        report = {"strategy": self.strategy.value, "total_models": len(self.models), "models": {}}

        for model_name, metrics in self.performance_tracker.get_all_metrics().items():
            report["models"][model_name] = {
                "total_requests": metrics.total_requests,
                "success_rate": f"{metrics.success_rate * 100:.1f}%",
                "average_latency_ms": f"{metrics.average_latency_ms:.0f}ms",
                "total_cost_usd": f"${metrics.total_cost_usd:.4f}",
                "average_cost_per_request": f"${metrics.average_cost_per_request:.4f}",
                "consecutive_failures": metrics.consecutive_failures,
            }

        return report
