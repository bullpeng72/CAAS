"""
Tests for Performance Optimization

Tests profiler, batch executor, and streaming handler.
"""

import pytest
import asyncio
from datetime import datetime

from caas_framework.performance.profiler import (
    PerformanceProfiler,
    ProfiledOperation,
    BottleneckAnalyzer
)
from caas_framework.performance.async_batch import (
    AsyncBatchExecutor,
    BatchConfig,
    run_parallel,
    batch_process
)
from caas_framework.performance.streaming import (
    StreamingResponseHandler,
    StreamBuffer,
    consume_stream,
    stream_to_list
)


# ==================== Profiler Tests ====================

@pytest.mark.asyncio
async def test_profiler_basic():
    """Test basic profiling"""
    profiler = PerformanceProfiler(enabled=True)

    async with profiler.profile("test_operation", {"key": "value"}):
        await asyncio.sleep(0.01)  # Simulate work

    operations = profiler.get_operations()
    assert len(operations) == 1
    assert operations[0].name == "test_operation"
    assert operations[0].duration_ms is not None
    assert operations[0].duration_ms >= 10  # At least 10ms
    assert operations[0].success is True
    assert operations[0].metadata["key"] == "value"


@pytest.mark.asyncio
async def test_profiler_nested():
    """Test nested profiling"""
    profiler = PerformanceProfiler(enabled=True)

    async with profiler.profile("parent"):
        await asyncio.sleep(0.01)

        async with profiler.profile("child1"):
            await asyncio.sleep(0.01)

        async with profiler.profile("child2"):
            await asyncio.sleep(0.01)

    operations = profiler.get_operations()
    assert len(operations) == 1
    assert operations[0].name == "parent"
    assert len(operations[0].children) == 2
    assert operations[0].children[0].name == "child1"
    assert operations[0].children[1].name == "child2"


@pytest.mark.asyncio
async def test_profiler_error_handling():
    """Test profiling with errors"""
    profiler = PerformanceProfiler(enabled=True)

    try:
        async with profiler.profile("failing_operation"):
            raise ValueError("Test error")
    except ValueError:
        pass

    operations = profiler.get_operations()
    assert len(operations) == 1
    assert operations[0].success is False
    assert "error" in operations[0].metadata


def test_profiler_stats():
    """Test operation statistics"""
    profiler = PerformanceProfiler(enabled=True)

    # Add some operations manually
    for i in range(3):
        op = ProfiledOperation(name="test_op", start_time=0)
        op.finish(success=True)
        op.duration_ms = 100.0
        profiler.operations.append(op)

    stats = profiler.get_operation_stats()

    assert "test_op" in stats
    assert stats["test_op"]["count"] == 3
    assert stats["test_op"]["total_time_ms"] == 300.0
    assert stats["test_op"]["avg_time_ms"] == 100.0
    assert stats["test_op"]["success_count"] == 3


def test_profiler_disabled():
    """Test that disabled profiler doesn't collect data"""
    profiler = PerformanceProfiler(enabled=False)

    # This should not collect any data
    import asyncio
    async def test():
        async with profiler.profile("test"):
            await asyncio.sleep(0.01)

    asyncio.run(test())

    assert len(profiler.get_operations()) == 0


def test_bottleneck_analyzer():
    """Test bottleneck detection"""
    profiler = PerformanceProfiler(enabled=True)

    # Add operations with different durations
    op1 = ProfiledOperation(name="fast_op", start_time=0)
    op1.finish()
    op1.duration_ms = 10.0
    profiler.operations.append(op1)

    op2 = ProfiledOperation(name="slow_llm_call", start_time=0)
    op2.finish()
    op2.duration_ms = 1000.0
    profiler.operations.append(op2)

    analyzer = BottleneckAnalyzer(profiler)
    bottlenecks = analyzer.identify_bottlenecks(threshold_percent=50.0)

    assert len(bottlenecks) >= 1
    assert bottlenecks[0]["operation"] == "slow_llm_call"
    assert len(bottlenecks[0]["recommendations"]) > 0


# ==================== Async Batch Tests ====================

@pytest.mark.asyncio
async def test_batch_executor_basic():
    """Test basic batch execution"""
    config = BatchConfig(max_concurrent=2, batch_size=3)
    executor = AsyncBatchExecutor(config=config)

    async def double(x):
        await asyncio.sleep(0.01)
        return x * 2

    items = [1, 2, 3, 4, 5]
    results = await executor.execute_batch(items, double)

    assert len(results) == 5
    for item, result, error in results:
        assert error is None
        assert result == item * 2


@pytest.mark.asyncio
async def test_batch_executor_map_parallel():
    """Test map_parallel functionality"""
    config = BatchConfig(max_concurrent=3)
    executor = AsyncBatchExecutor(config=config)

    async def square(x):
        return x ** 2

    items = [1, 2, 3, 4, 5]
    results = await executor.map_parallel(items, square)

    assert results == [1, 4, 9, 16, 25]


@pytest.mark.asyncio
async def test_batch_executor_error_handling():
    """Test error handling in batch execution"""
    config = BatchConfig(max_concurrent=2, continue_on_error=True)
    executor = AsyncBatchExecutor(config=config)

    async def maybe_fail(x):
        if x == 3:
            raise ValueError("Test error")
        return x

    items = [1, 2, 3, 4, 5]
    results = await executor.execute_batch(items, maybe_fail)

    assert len(results) == 5
    # Item 3 should have error
    _, result, error = results[2]
    assert result is None
    assert error is not None


@pytest.mark.asyncio
async def test_batch_executor_timeout():
    """Test timeout handling"""
    config = BatchConfig(max_concurrent=2, timeout_per_item=0.05)
    executor = AsyncBatchExecutor(config=config)

    async def slow_operation(x):
        await asyncio.sleep(1.0)  # Longer than timeout
        return x

    items = [1, 2, 3]
    results = await executor.execute_batch(items, slow_operation)

    # All should timeout
    for _, result, error in results:
        assert result is None
        assert isinstance(error, asyncio.TimeoutError)


@pytest.mark.asyncio
async def test_run_parallel():
    """Test run_parallel convenience function"""
    async def task1():
        await asyncio.sleep(0.01)
        return 1

    async def task2():
        await asyncio.sleep(0.01)
        return 2

    async def task3():
        await asyncio.sleep(0.01)
        return 3

    results = await run_parallel(
        task1(), task2(), task3(),
        max_concurrent=2
    )

    assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_batch_process():
    """Test batch_process convenience function"""
    async def add_ten(x):
        return x + 10

    results = await batch_process(
        items=[1, 2, 3, 4, 5],
        process_fn=add_ten,
        batch_size=2,
        max_concurrent=3
    )

    assert results == [11, 12, 13, 14, 15]


# ==================== Streaming Tests ====================

async def mock_stream(chunks: list):
    """Mock async stream"""
    for chunk in chunks:
        await asyncio.sleep(0.001)
        yield chunk


@pytest.mark.asyncio
async def test_stream_buffer():
    """Test StreamBuffer"""
    buffer = StreamBuffer()

    buffer.add_chunk("Hello")
    buffer.add_chunk(" ")
    buffer.add_chunk("World")
    buffer.mark_complete()

    assert buffer.get_content() == "Hello World"
    assert buffer.complete is True
    assert buffer.error is None


@pytest.mark.asyncio
async def test_streaming_handler_basic():
    """Test basic streaming"""
    handler = StreamingResponseHandler()

    chunks = ["Hello", " ", "World"]
    stream = mock_stream(chunks)

    buffer = await handler.stream_and_collect(stream)

    assert buffer.get_content() == "Hello World"
    assert buffer.complete is True
    assert len(buffer.chunks) == 3


@pytest.mark.asyncio
async def test_streaming_handler_callback():
    """Test chunk callbacks"""
    collected_chunks = []

    def chunk_callback(chunk):
        collected_chunks.append(chunk)

    handler = StreamingResponseHandler(chunk_callback=chunk_callback)

    chunks = ["A", "B", "C"]
    stream = mock_stream(chunks)

    await handler.stream_and_collect(stream)

    assert collected_chunks == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_streaming_handler_batching():
    """Test batch callbacks"""
    collected_batches = []

    def batch_callback(batch):
        collected_batches.append(list(batch))

    handler = StreamingResponseHandler(buffer_size=2)

    chunks = ["A", "B", "C", "D", "E"]
    stream = mock_stream(chunks)

    content = await handler.stream_with_batching(stream, batch_callback)

    assert content == "ABCDE"
    assert len(collected_batches) == 3  # [AB], [CD], [E]


@pytest.mark.asyncio
async def test_streaming_timeout():
    """Test streaming with timeout"""
    handler = StreamingResponseHandler()

    async def slow_stream():
        yield "A"
        await asyncio.sleep(2.0)  # Longer than timeout
        yield "B"

    buffer = await handler.stream_with_timeout(
        slow_stream(),
        timeout_seconds=0.1
    )

    assert len(buffer.chunks) == 1  # Only got "A" before timeout
    assert buffer.error is not None


@pytest.mark.asyncio
async def test_consume_stream():
    """Test consume_stream convenience function"""
    chunks = ["Hello", " ", "Stream"]
    stream = mock_stream(chunks)

    content = await consume_stream(stream)

    assert content == "Hello Stream"


@pytest.mark.asyncio
async def test_stream_to_list():
    """Test stream_to_list convenience function"""
    chunks = ["A", "B", "C"]
    stream = mock_stream(chunks)

    result = await stream_to_list(stream)

    assert result == ["A", "B", "C"]


def test_profiled_operation_to_dict():
    """Test ProfiledOperation serialization"""
    op = ProfiledOperation(name="test", start_time=0.0)
    op.finish()
    op.duration_ms = 100.0

    data = op.to_dict()

    assert data["name"] == "test"
    assert "100.00" in data["duration_ms"]
    assert data["success"] is True
