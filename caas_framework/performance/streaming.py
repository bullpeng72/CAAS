"""
Streaming Response Handler

Optimized streaming for LLM responses to provide faster user feedback.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Callable, List, Optional


@dataclass
class StreamBuffer:
    """
    Buffer for streaming responses.

    Collects chunks and provides utilities for processing.
    """

    chunks: List[str] = field(default_factory=list)
    complete: bool = False
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_chunk(self, chunk: str):
        """Add chunk to buffer"""
        if self.start_time is None:
            self.start_time = datetime.now()
        self.chunks.append(chunk)

    def get_content(self) -> str:
        """Get complete buffered content"""
        return "".join(self.chunks)

    def mark_complete(self):
        """Mark stream as complete"""
        self.complete = True
        self.end_time = datetime.now()

    def mark_error(self, error: Exception):
        """Mark stream as errored"""
        self.error = error
        self.end_time = datetime.now()

    def get_duration_ms(self) -> float:
        """Get streaming duration in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


class StreamingResponseHandler:
    """
    Handle streaming LLM responses with optimizations.

    Features:
    - Chunk buffering
    - Real-time callbacks
    - Error handling
    - Performance tracking
    """

    def __init__(
        self,
        chunk_callback: Optional[Callable[[str], None]] = None,
        buffer_size: int = 10,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize streaming handler.

        Args:
            chunk_callback: Optional callback for each chunk
            buffer_size: Number of chunks to buffer before flushing
            logger: Optional logger
        """
        self.chunk_callback = chunk_callback
        self.buffer_size = buffer_size
        self.logger = logger or logging.getLogger(__name__)

    async def stream_and_collect(
        self,
        stream: AsyncIterator[str],
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> StreamBuffer:
        """
        Stream and collect all chunks.

        Args:
            stream: Async iterator of chunks
            progress_callback: Optional callback with chunk count

        Returns:
            StreamBuffer with all chunks
        """
        buffer = StreamBuffer()
        chunk_count = 0

        try:
            async for chunk in stream:
                buffer.add_chunk(chunk)
                chunk_count += 1

                # Call chunk callback
                if self.chunk_callback:
                    self.chunk_callback(chunk)

                # Call progress callback
                if progress_callback:
                    progress_callback(chunk_count)

            buffer.mark_complete()
            self.logger.debug(
                f"✅ Streaming completed: {chunk_count} chunks, "
                f"{len(buffer.get_content())} chars, "
                f"{buffer.get_duration_ms():.0f}ms"
            )

        except Exception as e:
            buffer.mark_error(e)
            self.logger.error(f"❌ Streaming error: {e}")

        return buffer

    async def stream_with_batching(
        self, stream: AsyncIterator[str], batch_callback: Callable[[List[str]], None]
    ) -> str:
        """
        Stream with batch callbacks.

        Collects chunks in batches and calls callback with batch.
        More efficient than per-chunk callbacks.

        Args:
            stream: Async iterator of chunks
            batch_callback: Callback for each batch

        Returns:
            Complete content
        """
        chunks = []
        batch = []

        async for chunk in stream:
            chunks.append(chunk)
            batch.append(chunk)

            # Flush batch when size reached
            if len(batch) >= self.buffer_size:
                batch_callback(batch)
                batch = []

        # Flush remaining batch
        if batch:
            batch_callback(batch)

        return "".join(chunks)

    async def stream_parallel(
        self, streams: List[AsyncIterator[str]]
    ) -> List[StreamBuffer]:
        """
        Handle multiple streams in parallel.

        Args:
            streams: List of async iterators

        Returns:
            List of StreamBuffers
        """
        tasks = [self.stream_and_collect(stream) for stream in streams]

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def stream_with_timeout(
        self, stream: AsyncIterator[str], timeout_seconds: float = 30.0
    ) -> StreamBuffer:
        """
        Stream with timeout protection.

        Args:
            stream: Async iterator
            timeout_seconds: Timeout in seconds

        Returns:
            StreamBuffer (may be incomplete if timeout)
        """
        buffer = StreamBuffer()

        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in stream:
                    buffer.add_chunk(chunk)

            buffer.mark_complete()

        except asyncio.TimeoutError:
            self.logger.warning(
                f"⏱️ Streaming timeout after {timeout_seconds}s "
                f"({len(buffer.chunks)} chunks received)"
            )
            buffer.mark_error(asyncio.TimeoutError("Stream timeout"))

        except Exception as e:
            buffer.mark_error(e)

        return buffer


async def consume_stream(
    stream: AsyncIterator[str], callback: Optional[Callable[[str], None]] = None
) -> str:
    """
    Convenience function to consume a stream.

    Args:
        stream: Async iterator of chunks
        callback: Optional callback for each chunk

    Returns:
        Complete content

    Example:
        content = await consume_stream(
            llm.stream(messages),
            callback=lambda chunk: print(chunk, end="")
        )
    """
    handler = StreamingResponseHandler(chunk_callback=callback)
    buffer = await handler.stream_and_collect(stream)

    if buffer.error:
        raise buffer.error

    return buffer.get_content()


async def stream_to_list(stream: AsyncIterator[str]) -> List[str]:
    """
    Convert async stream to list.

    Args:
        stream: Async iterator

    Returns:
        List of chunks

    Example:
        chunks = await stream_to_list(llm.stream(messages))
    """
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return chunks
