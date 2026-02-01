"""Celery async task definitions for event processing."""

from threading import Lock
from typing import Any, Dict, List, Optional

import structlog
from celery import Celery

from ..config import settings

logger = structlog.get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "sentrel",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "process_event": {"queue": "events"},
        "process_batch": {"queue": "batch"},
        "cleanup_indices": {"queue": "maintenance"},
    },
    task_default_queue="events",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=4,
)


# Lazy pipeline initialization with thread safety
_pipeline: Optional[Any] = None
_pipeline_lock = Lock()


def get_pipeline() -> Any:
    """
    Get ETL pipeline instance (lazy initialization).
    
    Thread-safe singleton pattern.
    
    Returns:
        ETLPipeline instance
    """
    global _pipeline
    
    if _pipeline is None:
        with _pipeline_lock:
            # Double-check locking pattern
            if _pipeline is None:
                from ..etl.pipeline import get_pipeline as _get_pipeline
                _pipeline = _get_pipeline()
    
    return _pipeline


@celery_app.task(name="process_event", bind=True, max_retries=3)
def process_event_task(self, event_data: Dict[str, Any], project_id: int) -> Dict[str, Any]:
    """
    Process single event asynchronously.

    Args:
        event_data: Event data as dict
        project_id: Project identifier

    Returns:
        Result dict with status and event_id
    
    Raises:
        Retry: On transient failures (up to max_retries)
    """
    event_id = event_data.get("event_id", "unknown")

    try:
        logger.info(f"Processing event {event_id} for project {project_id}")

        pipeline = get_pipeline()
        success = pipeline.process_event_dict(event_data, project_id)

        if not success:
            raise RuntimeError("Pipeline processing failed")

        logger.info(f"Successfully processed event {event_id}")

        return {
            "status": "success",
            "event_id": event_id,
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(f"Failed to process event {event_id}: {e}")

        # Retry with exponential backoff
        countdown = 2**self.request.retries
        raise self.retry(exc=e, countdown=countdown)


@celery_app.task(name="process_batch")
def process_batch_task(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process batch of events.

    Args:
        events: List of dicts with 'event' and 'project_id' keys

    Returns:
        Result dict with processed/failed counts
    """
    logger.info(f"Processing batch of {len(events)} events")

    try:
        from ..receiver.event_parser import SentryEvent

        pipeline = get_pipeline()

        # Parse events
        parsed_events = []
        for item in events:
            try:
                event = SentryEvent(**item["event"])
                parsed_events.append((event, item["project_id"]))
            except Exception as e:
                logger.warning(f"Failed to parse event in batch: {e}")
                continue

        # Process batch
        result = pipeline.process_batch(parsed_events)

        logger.info(
            f"Batch complete: {result.processed} processed, {result.failed} failed"
        )

        return {
            "processed": result.processed,
            "failed": result.failed,
            "errors": result.errors[:10],  # Limit error messages
        }

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return {
            "processed": 0,
            "failed": len(events),
            "errors": [str(e)],
        }


@celery_app.task(name="cleanup_indices")
def cleanup_indices_task(days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Clean up old indices.

    Args:
        days_to_keep: Number of days to keep

    Returns:
        Result dict with deleted indices
    """
    logger.info(f"Starting index cleanup, keeping {days_to_keep} days")

    try:
        pipeline = get_pipeline()
        deleted = pipeline.indexer.delete_old_indices(days_to_keep)

        logger.info(f"Deleted {len(deleted)} old indices")

        return {
            "status": "success",
            "deleted_indices": deleted,
            "count": len(deleted),
        }

    except Exception as e:
        logger.error(f"Index cleanup failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(name="health_check")
def health_check_task() -> Dict[str, Any]:
    """
    Health check task for monitoring.

    Returns:
        Health status dict with status and metrics
    """
    try:
        pipeline = get_pipeline()
        doc_count = pipeline.indexer.get_document_count()

        return {
            "status": "healthy",
            "document_count": doc_count,
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# Periodic task schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-old-indices": {
        "task": "cleanup_indices",
        "schedule": 86400.0,  # Daily (24 hours)
        "args": (90,),  # Keep 90 days
    },
    "health-check": {
        "task": "health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
}
