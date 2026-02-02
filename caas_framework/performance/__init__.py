"""
Performance Optimization

Tools and utilities for optimizing workflow performance:
- Profiling and bottleneck detection
- Async batch execution
- Parallel phase execution
- Streaming optimization
- Performance metrics
"""

from caas_framework.performance.profiler import (
    PerformanceProfiler,
    ProfiledOperation,
    BottleneckAnalyzer
)
from caas_framework.performance.async_batch import (
    AsyncBatchExecutor,
    BatchConfig
)
from caas_framework.performance.streaming import (
    StreamingResponseHandler,
    StreamBuffer
)

__all__ = [
    "PerformanceProfiler",
    "ProfiledOperation",
    "BottleneckAnalyzer",
    "AsyncBatchExecutor",
    "BatchConfig",
    "StreamingResponseHandler",
    "StreamBuffer"
]
