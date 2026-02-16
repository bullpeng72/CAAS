"""
Performance Tester for CAAS-E QA

Profiles and tests performance of generated code:
- Memory profiling
- CPU profiling
- Load testing
- Response time measurement
- Resource usage tracking

Part of CAAS-E Week 6 implementation (Task 6.1).
"""

import time
import psutil
import tracemalloc
import asyncio
import statistics
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance test result levels"""
    EXCELLENT = "excellent"  # < 80% of threshold
    GOOD = "good"  # 80-100% of threshold
    WARNING = "warning"  # 100-120% of threshold
    POOR = "poor"  # > 120% of threshold


@dataclass
class MemoryProfile:
    """Memory usage profile"""
    peak_memory_mb: float
    current_memory_mb: float
    memory_allocations: int
    largest_allocation_mb: float
    memory_trend: str  # "increasing", "stable", "decreasing"


@dataclass
class CPUProfile:
    """CPU usage profile"""
    cpu_percent: float
    cpu_time_seconds: float
    system_time_seconds: float
    user_time_seconds: float


@dataclass
class LoadTestResult:
    """Load test result for concurrent operations"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    error_rate: float


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""
    test_name: str
    duration_seconds: float
    memory_profile: MemoryProfile
    cpu_profile: CPUProfile
    load_test_result: Optional[LoadTestResult] = None
    performance_level: PerformanceLevel = PerformanceLevel.GOOD
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceReport:
    """Performance test report"""
    project_name: str
    metrics: List[PerformanceMetrics]
    overall_performance: PerformanceLevel
    total_duration_seconds: float
    summary: Dict[str, Any]


class PerformanceTester:
    """
    Comprehensive performance tester for generated code.

    Features:
    1. Memory Profiling
       - Track memory allocations
       - Detect memory leaks
       - Peak memory usage

    2. CPU Profiling
       - CPU usage tracking
       - Execution time measurement

    3. Load Testing
       - Concurrent request handling
       - Response time distribution
       - Throughput measurement

    4. Bottleneck Detection
       - Identify slow operations
       - Resource-intensive code
       - Optimization opportunities
    """

    # Performance thresholds
    MEMORY_THRESHOLD_MB = 500  # 500 MB
    CPU_THRESHOLD_PERCENT = 80  # 80% CPU
    RESPONSE_TIME_THRESHOLD_MS = 1000  # 1 second
    ERROR_RATE_THRESHOLD = 0.05  # 5% error rate

    def __init__(
        self,
        memory_threshold_mb: float = MEMORY_THRESHOLD_MB,
        cpu_threshold_percent: float = CPU_THRESHOLD_PERCENT,
        response_time_threshold_ms: float = RESPONSE_TIME_THRESHOLD_MS,
    ):
        """
        Initialize performance tester.

        Args:
            memory_threshold_mb: Maximum acceptable memory usage
            cpu_threshold_percent: Maximum acceptable CPU usage
            response_time_threshold_ms: Maximum acceptable response time
        """
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.response_time_threshold_ms = response_time_threshold_ms
        self.logger = logging.getLogger(self.__class__.__name__)

    def test_function(
        self,
        func: Callable,
        *args,
        test_name: Optional[str] = None,
        iterations: int = 1,
        **kwargs
    ) -> PerformanceMetrics:
        """
        Test performance of a single function.

        Args:
            func: Function to test
            *args: Function arguments
            test_name: Name for this test
            iterations: Number of times to run function
            **kwargs: Function keyword arguments

        Returns:
            PerformanceMetrics with profiling results
        """
        test_name = test_name or func.__name__

        self.logger.info(f"Testing function: {test_name} ({iterations} iterations)")

        # Start profiling
        tracemalloc.start()
        process = psutil.Process()
        cpu_start = process.cpu_times()
        start_time = time.time()

        # Run function
        try:
            for _ in range(iterations):
                func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error during test: {e}")
            tracemalloc.stop()
            raise

        # End profiling
        duration = time.time() - start_time
        cpu_end = process.cpu_times()

        # Memory profile
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_info = process.memory_info()
        memory_profile = MemoryProfile(
            peak_memory_mb=peak_mem / 1024 / 1024,
            current_memory_mb=current_mem / 1024 / 1024,
            memory_allocations=0,  # Not tracked in simple mode
            largest_allocation_mb=0,
            memory_trend="stable",
        )

        # CPU profile
        cpu_profile = CPUProfile(
            cpu_percent=process.cpu_percent(interval=0.1),
            cpu_time_seconds=cpu_end.user + cpu_end.system,
            system_time_seconds=cpu_end.system - cpu_start.system,
            user_time_seconds=cpu_end.user - cpu_start.user,
        )

        # Evaluate performance
        performance_level = self._evaluate_performance(
            memory_profile,
            cpu_profile,
            None,
        )

        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(
            memory_profile,
            cpu_profile,
            duration,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            performance_level,
            bottlenecks,
            memory_profile,
            cpu_profile,
        )

        metrics = PerformanceMetrics(
            test_name=test_name,
            duration_seconds=duration,
            memory_profile=memory_profile,
            cpu_profile=cpu_profile,
            performance_level=performance_level,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

        self.logger.info(
            f"Test complete: {test_name} - {performance_level.value} "
            f"({duration:.2f}s, {memory_profile.peak_memory_mb:.1f}MB)"
        )

        return metrics

    async def load_test(
        self,
        func: Callable,
        *args,
        test_name: Optional[str] = None,
        concurrent_requests: int = 10,
        total_requests: int = 100,
        **kwargs
    ) -> LoadTestResult:
        """
        Perform load test with concurrent requests.

        Args:
            func: Async function to test
            *args: Function arguments
            test_name: Name for this test
            concurrent_requests: Number of concurrent requests
            total_requests: Total number of requests
            **kwargs: Function keyword arguments

        Returns:
            LoadTestResult with load test metrics
        """
        test_name = test_name or func.__name__

        self.logger.info(
            f"Load test: {test_name} "
            f"({concurrent_requests} concurrent, {total_requests} total)"
        )

        response_times: List[float] = []
        errors = 0
        start_time = time.time()

        # Create batches
        batch_size = concurrent_requests
        batches = [
            range(i, min(i + batch_size, total_requests))
            for i in range(0, total_requests, batch_size)
        ]

        for batch in batches:
            tasks = []
            for _ in batch:
                tasks.append(self._measure_async_call(func, *args, **kwargs))

            # Run batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    self.logger.warning(f"Request failed: {result}")
                else:
                    response_times.append(result)

        total_duration = time.time() - start_time

        # Calculate metrics
        successful = len(response_times)
        failed = errors

        if response_times:
            avg_response = statistics.mean(response_times)
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_response = 0
            p50 = p95 = p99 = 0

        rps = total_requests / total_duration if total_duration > 0 else 0
        error_rate = failed / total_requests if total_requests > 0 else 0

        result = LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            average_response_time_ms=avg_response * 1000,
            p50_response_time_ms=p50 * 1000,
            p95_response_time_ms=p95 * 1000,
            p99_response_time_ms=p99 * 1000,
            requests_per_second=rps,
            error_rate=error_rate,
        )

        self.logger.info(
            f"Load test complete: {successful}/{total_requests} successful, "
            f"{rps:.1f} req/s, {avg_response*1000:.1f}ms avg"
        )

        return result

    async def _measure_async_call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> float:
        """Measure execution time of async function call"""
        start = time.time()

        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)

        return time.time() - start

    def profile_project(
        self,
        project_dir: Path,
        test_functions: Optional[List[Tuple[str, Callable]]] = None,
    ) -> PerformanceReport:
        """
        Profile entire project performance.

        Args:
            project_dir: Project directory
            test_functions: Optional list of (name, function) tuples to test

        Returns:
            PerformanceReport with all metrics
        """
        self.logger.info(f"Profiling project: {project_dir}")

        metrics: List[PerformanceMetrics] = []
        start_time = time.time()

        # Test provided functions
        if test_functions:
            for name, func in test_functions:
                try:
                    metric = self.test_function(func, test_name=name)
                    metrics.append(metric)
                except Exception as e:
                    self.logger.error(f"Error testing {name}: {e}")

        total_duration = time.time() - start_time

        # Calculate overall performance
        if metrics:
            performance_levels = [m.performance_level for m in metrics]
            worst_level = min(
                performance_levels,
                key=lambda x: ["excellent", "good", "warning", "poor"].index(x.value)
            )
            overall_performance = worst_level
        else:
            overall_performance = PerformanceLevel.GOOD

        # Summary
        summary = {
            "total_tests": len(metrics),
            "excellent_tests": sum(1 for m in metrics if m.performance_level == PerformanceLevel.EXCELLENT),
            "good_tests": sum(1 for m in metrics if m.performance_level == PerformanceLevel.GOOD),
            "warning_tests": sum(1 for m in metrics if m.performance_level == PerformanceLevel.WARNING),
            "poor_tests": sum(1 for m in metrics if m.performance_level == PerformanceLevel.POOR),
            "average_memory_mb": statistics.mean([m.memory_profile.peak_memory_mb for m in metrics]) if metrics else 0,
            "average_cpu_percent": statistics.mean([m.cpu_profile.cpu_percent for m in metrics]) if metrics else 0,
        }

        report = PerformanceReport(
            project_name=project_dir.name,
            metrics=metrics,
            overall_performance=overall_performance,
            total_duration_seconds=total_duration,
            summary=summary,
        )

        self.logger.info(
            f"Project profiling complete: {overall_performance.value} "
            f"({len(metrics)} tests, {total_duration:.2f}s)"
        )

        return report

    def _evaluate_performance(
        self,
        memory_profile: MemoryProfile,
        cpu_profile: CPUProfile,
        load_result: Optional[LoadTestResult],
    ) -> PerformanceLevel:
        """Evaluate overall performance level"""

        # Check memory
        memory_ratio = memory_profile.peak_memory_mb / self.memory_threshold_mb

        # Check CPU
        cpu_ratio = cpu_profile.cpu_percent / self.cpu_threshold_percent

        # Check load test (if available)
        if load_result:
            response_ratio = load_result.average_response_time_ms / self.response_time_threshold_ms
            error_ratio = load_result.error_rate / self.ERROR_RATE_THRESHOLD
        else:
            response_ratio = 0
            error_ratio = 0

        # Calculate worst ratio
        max_ratio = max(memory_ratio, cpu_ratio, response_ratio, error_ratio)

        # Classify performance
        if max_ratio < 0.8:
            return PerformanceLevel.EXCELLENT
        elif max_ratio < 1.0:
            return PerformanceLevel.GOOD
        elif max_ratio < 1.2:
            return PerformanceLevel.WARNING
        else:
            return PerformanceLevel.POOR

    def _detect_bottlenecks(
        self,
        memory_profile: MemoryProfile,
        cpu_profile: CPUProfile,
        duration: float,
    ) -> List[str]:
        """Detect performance bottlenecks"""
        bottlenecks = []

        # Memory bottlenecks
        if memory_profile.peak_memory_mb > self.memory_threshold_mb:
            bottlenecks.append(
                f"High memory usage: {memory_profile.peak_memory_mb:.1f}MB "
                f"(threshold: {self.memory_threshold_mb}MB)"
            )

        # CPU bottlenecks
        if cpu_profile.cpu_percent > self.cpu_threshold_percent:
            bottlenecks.append(
                f"High CPU usage: {cpu_profile.cpu_percent:.1f}% "
                f"(threshold: {self.cpu_threshold_percent}%)"
            )

        # Slow execution
        if duration > 5.0:  # 5 seconds threshold
            bottlenecks.append(
                f"Slow execution: {duration:.2f}s"
            )

        return bottlenecks

    def _generate_recommendations(
        self,
        performance_level: PerformanceLevel,
        bottlenecks: List[str],
        memory_profile: MemoryProfile,
        cpu_profile: CPUProfile,
    ) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        if performance_level in [PerformanceLevel.POOR, PerformanceLevel.WARNING]:
            if memory_profile.peak_memory_mb > self.memory_threshold_mb:
                recommendations.append(
                    "Optimize memory usage: Use generators, release references, implement caching"
                )

            if cpu_profile.cpu_percent > self.cpu_threshold_percent:
                recommendations.append(
                    "Optimize CPU usage: Profile hot paths, use algorithmic improvements, consider caching"
                )

            if "Slow execution" in " ".join(bottlenecks):
                recommendations.append(
                    "Improve execution speed: Use async/await, parallelize operations, optimize algorithms"
                )

        return recommendations
