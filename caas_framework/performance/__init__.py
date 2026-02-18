"""
Performance Optimization

Tools and utilities for optimizing workflow performance:
- Profiling and bottleneck detection
- Async batch execution
- Parallel phase execution
- Streaming optimization
- Performance metrics
"""

from caas_framework.performance.async_batch import AsyncBatchExecutor, BatchConfig
from caas_framework.performance.profiler import (
    BottleneckAnalyzer,
    PerformanceProfiler,
    ProfiledOperation,
)
from caas_framework.performance.streaming import StreamBuffer, StreamingResponseHandler

# Global profiler instance
_profiler = None


def get_profiler() -> "PerformanceProfiler":
    """Get or create the global PerformanceProfiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler


__all__ = [
    "PerformanceProfiler",
    "ProfiledOperation",
    "BottleneckAnalyzer",
    "AsyncBatchExecutor",
    "BatchConfig",
    "StreamingResponseHandler",
    "StreamBuffer",
    "get_profiler",
]
