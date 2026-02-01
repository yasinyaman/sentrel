"""Event batching for efficient bulk processing."""

import asyncio
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BatchedEvent:
    """Container for a batched event."""
    
    event_dict: Dict[str, Any]
    project_id: int
    event_id: str
    received_at: float = field(default_factory=time.time)


class EventBatcher:
    """
    Event batcher for efficient bulk processing.
    
    Collects events and flushes them:
    - When batch_size is reached
    - When batch_timeout_seconds has elapsed since first event in batch
    
    Thread-safe for use in async context.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        batch_timeout_seconds: float = 5.0,
        flush_callback: Optional[callable] = None,
    ):
        """
        Initialize event batcher.
        
        Args:
            batch_size: Maximum events before auto-flush
            batch_timeout_seconds: Maximum seconds before auto-flush
            flush_callback: Async callback function for batch processing
        """
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.flush_callback = flush_callback
        
        self._buffer: List[BatchedEvent] = []
        self._lock = Lock()
        self._first_event_time: Optional[float] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the background flush task."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"Event batcher started (size={self.batch_size}, "
            f"timeout={self.batch_timeout_seconds}s)"
        )
    
    async def stop(self) -> None:
        """Stop the batcher and flush remaining events."""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
        logger.info("Event batcher stopped")
    
    async def add(self, event_dict: Dict[str, Any], project_id: int, event_id: str) -> None:
        """
        Add an event to the batch.
        
        Args:
            event_dict: Event data as dictionary
            project_id: Project identifier
            event_id: Event identifier
        """
        batched = BatchedEvent(
            event_dict=event_dict,
            project_id=project_id,
            event_id=event_id,
        )
        
        should_flush = False
        
        with self._lock:
            self._buffer.append(batched)
            
            # Track first event time for timeout
            if self._first_event_time is None:
                self._first_event_time = time.time()
            
            # Check if we should flush
            if len(self._buffer) >= self.batch_size:
                should_flush = True
        
        if should_flush:
            await self.flush()
    
    async def flush(self) -> int:
        """
        Flush current batch for processing.
        
        Returns:
            Number of events flushed
        """
        events_to_process: List[BatchedEvent] = []
        
        with self._lock:
            if not self._buffer:
                return 0
            
            events_to_process = self._buffer.copy()
            self._buffer.clear()
            self._first_event_time = None
        
        if not events_to_process:
            return 0
        
        count = len(events_to_process)
        logger.info(f"Flushing batch of {count} events")
        
        # Process via callback if provided
        if self.flush_callback:
            try:
                await self.flush_callback(events_to_process)
            except Exception as e:
                logger.error(f"Batch flush callback failed: {e}")
                # Re-queue failed events? For now, log and continue
        
        return count
    
    async def _flush_loop(self) -> None:
        """Background task to flush on timeout."""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                should_flush = False
                
                with self._lock:
                    if self._first_event_time is not None:
                        elapsed = time.time() - self._first_event_time
                        if elapsed >= self.batch_timeout_seconds:
                            should_flush = True
                
                if should_flush:
                    await self.flush()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
    
    @property
    def pending_count(self) -> int:
        """Get number of pending events in buffer."""
        with self._lock:
            return len(self._buffer)
    
    @property
    def is_running(self) -> bool:
        """Check if batcher is running."""
        return self._running


# Global batcher instance
_batcher: Optional[EventBatcher] = None


async def get_batcher(
    batch_size: int = 100,
    batch_timeout_seconds: float = 5.0,
) -> EventBatcher:
    """
    Get or create global event batcher.
    
    Args:
        batch_size: Maximum events before auto-flush
        batch_timeout_seconds: Maximum seconds before auto-flush
    
    Returns:
        EventBatcher instance
    """
    global _batcher
    
    if _batcher is None:
        from ..etl.pipeline import get_pipeline
        
        async def process_batch(events: List[BatchedEvent]) -> None:
            """Process a batch of events."""
            pipeline = get_pipeline()
            
            # Convert to format expected by pipeline
            event_tuples: List[Tuple[Any, int]] = []
            
            for batched in events:
                try:
                    from .event_parser import SentryEvent
                    event = SentryEvent(**batched.event_dict)
                    event_tuples.append((event, batched.project_id))
                except Exception as e:
                    logger.error(f"Failed to reconstruct event: {e}")
            
            if event_tuples:
                result = pipeline.process_batch(event_tuples)
                logger.info(
                    f"Batch processed: {result.processed} success, "
                    f"{result.failed} failed"
                )
        
        _batcher = EventBatcher(
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout_seconds,
            flush_callback=process_batch,
        )
        await _batcher.start()
    
    return _batcher


async def shutdown_batcher() -> None:
    """Shutdown global batcher."""
    global _batcher
    
    if _batcher:
        await _batcher.stop()
        _batcher = None
