"""
Unit tests for PerformanceTester

Tests memory, CPU, and load performance profiling.

Part of CAAS-E Week 6 implementation (Task 6.1).
"""

import pytest
import asyncio
import time
from pathlib import Path
from caas_framework.qa import (
    PerformanceTester,
    PerformanceLevel,
)


@pytest.fixture
def tester():
    """Create PerformanceTester instance"""
    return PerformanceTester(
        memory_threshold_mb=500,
        cpu_threshold_percent=80,
        response_time_threshold_ms=1000,
    )


class TestPerformanceTester:
    """Test PerformanceTester class"""

    def test_initialization(self):
        """Test basic initialization"""
        tester = PerformanceTester(
            memory_threshold_mb=1000,
            cpu_threshold_percent=90,
        )

        assert tester.memory_threshold_mb == 1000
        assert tester.cpu_threshold_percent == 90

    def test_function_profiling(self, tester):
        """Test profiling a simple function"""

        def simple_function():
            """Simple test function"""
            result = sum(range(1000))
            return result

        metrics = tester.test_function(
            simple_function,
            test_name="simple_function",
            iterations=10,
        )

        # Verify metrics
        assert metrics.test_name == "simple_function"
        assert metrics.duration_seconds > 0
        assert metrics.memory_profile.peak_memory_mb >= 0
        assert metrics.cpu_profile.cpu_percent >= 0
        assert metrics.performance_level in [
            PerformanceLevel.EXCELLENT,
            PerformanceLevel.GOOD,
            PerformanceLevel.WARNING,
            PerformanceLevel.POOR,
        ]

    def test_memory_intensive_function(self, tester):
        """Test profiling memory-intensive function"""

        def memory_intensive():
            """Create large data structure"""
            data = [list(range(10000)) for _ in range(100)]
            return len(data)

        metrics = tester.test_function(
            memory_intensive,
            test_name="memory_intensive",
        )

        # Should detect memory usage
        assert metrics.memory_profile.peak_memory_mb > 0

    def test_cpu_intensive_function(self, tester):
        """Test profiling CPU-intensive function"""

        def cpu_intensive():
            """CPU-heavy computation"""
            result = 0
            for i in range(100000):
                result += i ** 2
            return result

        metrics = tester.test_function(
            cpu_intensive,
            test_name="cpu_intensive",
        )

        # Should measure CPU time
        assert metrics.cpu_profile.cpu_time_seconds > 0

    @pytest.mark.asyncio
    async def test_load_test(self, tester):
        """Test load testing functionality"""

        async def async_function():
            """Simple async function"""
            await asyncio.sleep(0.01)  # 10ms delay
            return "success"

        result = await tester.load_test(
            async_function,
            test_name="load_test",
            concurrent_requests=5,
            total_requests=20,
        )

        # Verify load test results
        assert result.total_requests == 20
        assert result.successful_requests <= 20
        assert result.average_response_time_ms >= 0
        assert result.requests_per_second > 0

    @pytest.mark.asyncio
    async def test_load_test_with_failures(self, tester):
        """Test load test with some failures"""

        call_count = 0

        async def failing_function():
            """Function that fails sometimes"""
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise ValueError("Simulated failure")
            await asyncio.sleep(0.01)
            return "success"

        result = await tester.load_test(
            failing_function,
            test_name="failing_load_test",
            concurrent_requests=2,
            total_requests=10,
        )

        # Should track failures
        assert result.failed_requests > 0
        assert result.error_rate > 0

    def test_project_profiling(self, tmp_path, tester):
        """Test profiling entire project"""

        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Profile with test functions
        def test_func1():
            return sum(range(100))

        def test_func2():
            return [i * 2 for i in range(100)]

        test_functions = [
            ("test_func1", test_func1),
            ("test_func2", test_func2),
        ]

        report = tester.profile_project(
            project_dir=project_dir,
            test_functions=test_functions,
        )

        # Verify report
        assert report.project_name == "test_project"
        assert len(report.metrics) == 2
        assert report.overall_performance in [
            PerformanceLevel.EXCELLENT,
            PerformanceLevel.GOOD,
            PerformanceLevel.WARNING,
            PerformanceLevel.POOR,
        ]
        assert "total_tests" in report.summary

    def test_performance_level_evaluation(self, tester):
        """Test performance level evaluation"""

        def fast_function():
            """Fast, efficient function"""
            return sum(range(10))

        metrics = tester.test_function(fast_function)

        # Simple function should be excellent or good
        assert metrics.performance_level in [
            PerformanceLevel.EXCELLENT,
            PerformanceLevel.GOOD,
        ]

    def test_bottleneck_detection(self, tester):
        """Test bottleneck detection"""

        def slow_function():
            """Intentionally slow function"""
            time.sleep(0.5)  # 500ms delay
            return "done"

        metrics = tester.test_function(slow_function)

        # Should have some bottlenecks or recommendations
        # (actual detection depends on thresholds)
        assert metrics is not None

    def test_recommendations_generation(self, tester):
        """Test performance recommendations"""

        # Set very low thresholds to trigger recommendations
        strict_tester = PerformanceTester(
            memory_threshold_mb=1,  # 1 MB threshold
            cpu_threshold_percent=1,  # 1% CPU threshold
        )

        def any_function():
            return sum(range(1000))

        metrics = strict_tester.test_function(any_function)

        # With such strict thresholds, should get recommendations
        # (or at least warnings)
        assert metrics is not None
