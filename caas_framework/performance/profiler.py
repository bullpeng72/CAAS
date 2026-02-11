"""
Performance Profiler

Tools for profiling workflow execution and identifying bottlenecks.
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from caas_framework.utils.logger import get_logger


@dataclass
class ProfiledOperation:
    """Profiled operation metrics"""

    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["ProfiledOperation"] = field(default_factory=list)

    def finish(self, success: bool = True):
        """Mark operation as finished"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success

    def add_child(self, child: "ProfiledOperation"):
        """Add child operation"""
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "duration_ms": f"{self.duration_ms:.2f}" if self.duration_ms else "N/A",
            "success": self.success,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class PerformanceProfiler:
    """
    Performance profiler for tracking operation timing.

    Features:
    - Hierarchical operation tracking
    - Async context manager support
    - Bottleneck detection
    - Detailed metrics collection
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize profiler.

        Args:
            enabled: Enable profiling (can be disabled in production)
        """
        self.enabled = enabled
        self.operations: List[ProfiledOperation] = []
        self.current_stack: List[ProfiledOperation] = []
        self.logger = get_logger()

    @asynccontextmanager
    async def profile(
        self, operation_name: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Profile an async operation.

        Args:
            operation_name: Name of operation
            metadata: Optional metadata

        Example:
            async with profiler.profile("llm_call", {"model": "gpt-4"}):
                result = await llm.generate(...)
        """
        if not self.enabled:
            yield
            return

        operation = ProfiledOperation(
            name=operation_name, start_time=time.time(), metadata=metadata or {}
        )

        # Add to current parent if exists
        if self.current_stack:
            self.current_stack[-1].add_child(operation)
        else:
            self.operations.append(operation)

        self.current_stack.append(operation)

        try:
            yield operation
            operation.finish(success=True)
        except Exception as e:
            operation.finish(success=False)
            operation.metadata["error"] = str(e)
            raise
        finally:
            self.current_stack.pop()

    def get_operations(self) -> List[ProfiledOperation]:
        """Get all profiled operations"""
        return self.operations

    def get_total_time(self) -> float:
        """Get total execution time (ms)"""
        if not self.operations:
            return 0.0

        return sum(
            op.duration_ms for op in self.operations if op.duration_ms is not None
        )

    def get_operation_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get aggregated statistics by operation name.

        Returns:
            Dict mapping operation names to stats
        """
        stats = defaultdict(
            lambda: {
                "count": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "min_time_ms": float("inf"),
                "max_time_ms": 0.0,
                "success_count": 0,
                "failure_count": 0,
            }
        )

        def collect_stats(operations: List[ProfiledOperation]):
            for op in operations:
                if op.duration_ms is not None:
                    s = stats[op.name]
                    s["count"] += 1
                    s["total_time_ms"] += op.duration_ms
                    s["min_time_ms"] = min(s["min_time_ms"], op.duration_ms)
                    s["max_time_ms"] = max(s["max_time_ms"], op.duration_ms)

                    if op.success:
                        s["success_count"] += 1
                    else:
                        s["failure_count"] += 1

                # Recurse into children
                if op.children:
                    collect_stats(op.children)

        collect_stats(self.operations)

        # Calculate averages
        for s in stats.values():
            if s["count"] > 0:
                s["avg_time_ms"] = s["total_time_ms"] / s["count"]

        return dict(stats)

    def print_report(self, min_duration_ms: float = 0.0):
        """
        Print performance report.

        Args:
            min_duration_ms: Only show operations taking longer than this
        """
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE PROFILE REPORT")
        logger.info("=" * 80)
        stats = self.get_operation_stats()

        # Sort by total time descending
        sorted_stats = sorted(
            stats.items(), key=lambda x: x[1]["total_time_ms"], reverse=True
        )

        logger.info(
            f"\n{'Operation':<40} {'Count':>8} {'Total (ms)':>12} {'Avg (ms)':>12} {'Success Rate':>12}"
        )
        logger.info("-" * 80)
        for name, s in sorted_stats:
            if s["total_time_ms"] < min_duration_ms:
                continue

            success_rate = (
                (s["success_count"] / s["count"] * 100) if s["count"] > 0 else 0
            )

            logger.info(
                f"{name:<40} {s['count']:>8} "
                f"{s['total_time_ms']:>12.2f} {s['avg_time_ms']:>12.2f} "
                f"{success_rate:>11.1f}%"
            )

        logger.info("-" * 80)
        logger.info(f"{'TOTAL':<40} {'':<8} {self.get_total_time():>12.2f}")
        logger.info("=" * 80 + "\n")
    def clear(self):
        """Clear all profiling data"""
        self.operations.clear()
        self.current_stack.clear()


class BottleneckAnalyzer:
    """
    Analyze profiling data to identify bottlenecks.

    Provides recommendations for optimization.
    """

    def __init__(self, profiler: PerformanceProfiler):
        """
        Initialize analyzer.

        Args:
            profiler: Performance profiler with collected data
        """
        self.profiler = profiler
        self.logger = get_logger()

    def identify_bottlenecks(
        self, threshold_percent: float = 10.0, min_duration_ms: float = 100.0
    ) -> List[Dict[str, Any]]:
        """
        Identify bottleneck operations.

        Args:
            threshold_percent: Operation taking > this % of total time is a bottleneck
            min_duration_ms: Minimum duration to consider

        Returns:
            List of bottleneck operations with recommendations
        """
        total_time = self.profiler.get_total_time()
        stats = self.profiler.get_operation_stats()

        bottlenecks = []

        for name, s in stats.items():
            time_percent = (
                (s["total_time_ms"] / total_time * 100) if total_time > 0 else 0
            )

            if (
                time_percent > threshold_percent
                and s["total_time_ms"] > min_duration_ms
            ):
                bottleneck = {
                    "operation": name,
                    "total_time_ms": s["total_time_ms"],
                    "percentage_of_total": time_percent,
                    "call_count": s["count"],
                    "avg_time_ms": s["avg_time_ms"],
                    "recommendations": self._get_recommendations(name, s),
                }
                bottlenecks.append(bottleneck)

        # Sort by percentage descending
        bottlenecks.sort(key=lambda x: x["percentage_of_total"], reverse=True)

        return bottlenecks

    def _get_recommendations(
        self, operation_name: str, stats: Dict[str, Any]
    ) -> List[str]:
        """
        Get optimization recommendations for an operation.

        Args:
            operation_name: Name of operation
            stats: Operation statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # High call count
        if stats["count"] > 10:
            recommendations.append(
                f"High call count ({stats['count']}). Consider caching or batching."
            )

        # LLM-related operations
        if "llm" in operation_name.lower():
            recommendations.append(
                "LLM call detected. Enable caching with LLMCacheWrapper."
            )
            if stats["count"] > 5:
                recommendations.append(
                    "Multiple LLM calls. Consider batching prompts or using streaming."
                )

        # Validation operations
        if "validation" in operation_name.lower():
            recommendations.append(
                "Validation overhead detected. Use validation caching."
            )

        # Long average time
        if stats["avg_time_ms"] > 1000:
            recommendations.append(
                f"Long average duration ({stats['avg_time_ms']:.0f}ms). "
                f"Consider parallelization or optimization."
            )

        # High failure rate
        failure_rate = (
            stats["failure_count"] / stats["count"] if stats["count"] > 0 else 0
        )
        if failure_rate > 0.1:
            recommendations.append(
                f"High failure rate ({failure_rate*100:.1f}%). "
                f"Investigate error handling and retries."
            )

        if not recommendations:
            recommendations.append("No specific recommendations.")

        return recommendations

    def print_bottleneck_report(self):
        """Print bottleneck analysis report"""
        bottlenecks = self.identify_bottlenecks()

        logger.info("\n" + "=" * 80)
        logger.info("BOTTLENECK ANALYSIS")
        logger.info("=" * 80)
        if not bottlenecks:
            logger.info("\n✅ No significant bottlenecks detected!\n")
            return

        for i, b in enumerate(bottlenecks, 1):
            logger.info(f"\n🔴 Bottleneck #{i}: {b['operation']}")
            logger.info(
                f"   Time: {b['total_time_ms']:.2f}ms ({b['percentage_of_total']:.1f}% of total)"
            )
            logger.info(
                f"   Calls: {b['call_count']} (avg: {b['avg_time_ms']:.2f}ms per call)"
            )
            logger.info("   Recommendations:")
            for rec in b["recommendations"]:
                logger.info(f"   - {rec}")
        logger.info("\n" + "=" * 80 + "\n")
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get optimization summary with key metrics.

        Returns:
            Summary dictionary
        """
        bottlenecks = self.identify_bottlenecks()
        stats = self.profiler.get_operation_stats()

        # Count operation types
        llm_operations = sum(1 for name in stats.keys() if "llm" in name.lower())
        validation_operations = sum(
            1 for name in stats.keys() if "validation" in name.lower()
        )

        return {
            "total_time_ms": self.profiler.get_total_time(),
            "total_operations": len(stats),
            "bottleneck_count": len(bottlenecks),
            "llm_operation_count": llm_operations,
            "validation_operation_count": validation_operations,
            "optimization_potential": self._calculate_optimization_potential(
                bottlenecks
            ),
        }

    def _calculate_optimization_potential(
        self, bottlenecks: List[Dict[str, Any]]
    ) -> str:
        """
        Calculate potential time savings from optimizations.

        Args:
            bottlenecks: List of bottlenecks

        Returns:
            Optimization potential description
        """
        if not bottlenecks:
            return "Low (< 10% improvement expected)"

        # Assume 50% reduction for cacheable operations
        cacheable_time = sum(
            b["total_time_ms"] * 0.5
            for b in bottlenecks
            if "llm" in b["operation"].lower() or "validation" in b["operation"].lower()
        )

        total_time = self.profiler.get_total_time()
        potential_percent = (cacheable_time / total_time * 100) if total_time > 0 else 0

        if potential_percent > 30:
            return f"High ({potential_percent:.1f}% improvement with caching)"
        elif potential_percent > 15:
            return f"Medium ({potential_percent:.1f}% improvement with caching)"
        else:
            return f"Low ({potential_percent:.1f}% improvement with caching)"
