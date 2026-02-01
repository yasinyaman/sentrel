"""ETL pipeline orchestration for Sentry events."""

from dataclasses import dataclass, field
from threading import Lock
from typing import List, Optional, Tuple

import structlog

from ..config import settings
from ..opensearch.client import OpenSearchClient, get_opensearch_client
from ..opensearch.indexer import EventIndexer
from ..receiver.event_parser import SentryEvent
from .enricher import EventEnricher, get_enricher
from .transformer import EventTransformer

logger = structlog.get_logger(__name__)

# Lock for thread-safe pipeline initialization
_pipeline_lock = Lock()


@dataclass
class PipelineResult:
    """Result of pipeline processing."""

    processed: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)


class ETLPipeline:
    """
    Event processing pipeline.

    Orchestrates: Transform -> Enrich -> Index
    """

    def __init__(
        self,
        transformer: EventTransformer,
        enricher: EventEnricher,
        indexer: EventIndexer,
    ):
        """
        Initialize pipeline.

        Args:
            transformer: Event transformer instance
            enricher: Event enricher instance
            indexer: Event indexer instance
        """
        self.transformer = transformer
        self.enricher = enricher
        self.indexer = indexer

    def process_event(self, event: SentryEvent, project_id: int) -> bool:
        """
        Process single event through pipeline (synchronous).

        Args:
            event: SentryEvent object
            project_id: Project identifier

        Returns:
            True if successful
        """
        try:
            # Transform
            document = self.transformer.transform(event, project_id)

            # Enrich
            document = self.enricher.enrich(document)

            # Index
            result = self.indexer.index_single(document)

            if result.get("success"):
                logger.debug(f"Processed event {event.event_id}")
                return True
            else:
                logger.error(f"Failed to index event: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            return False

    async def process_event_async(self, event: SentryEvent, project_id: int) -> bool:
        """
        Process single event through pipeline (asynchronous).

        Uses async OpenSearch operations to avoid blocking the event loop.

        Args:
            event: SentryEvent object
            project_id: Project identifier

        Returns:
            True if successful
        """
        try:
            # Transform (CPU-bound, runs sync)
            document = self.transformer.transform(event, project_id)

            # Enrich (CPU-bound, runs sync)
            document = self.enricher.enrich(document)

            # Index (I/O-bound, runs async)
            result = await self.indexer.index_single_async(document)

            if result.get("success"):
                logger.debug(f"Processed event {event.event_id}")
                return True
            else:
                logger.error(f"Failed to index event: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            return False

    def process_batch(
        self, events: List[Tuple[SentryEvent, int]]
    ) -> PipelineResult:
        """
        Process batch of events.

        Args:
            events: List of (SentryEvent, project_id) tuples

        Returns:
            PipelineResult with counts
        """
        documents = []
        errors = []

        # Transform and enrich all events
        for event, project_id in events:
            try:
                doc = self.transformer.transform(event, project_id)
                doc = self.enricher.enrich(doc)
                documents.append(doc)
            except Exception as e:
                errors.append(f"Transform error: {e}")
                logger.error(f"Failed to transform event: {e}")

        # Bulk index
        if documents:
            result = self.indexer.bulk_index(documents)
            return PipelineResult(
                processed=result["success"],
                failed=result["failed"] + len(errors),
                errors=errors + result.get("errors", []),
            )

        return PipelineResult(
            processed=0,
            failed=len(errors),
            errors=errors,
        )

    def process_event_dict(self, event_dict: dict, project_id: int) -> bool:
        """
        Process event from dict (for Celery tasks).

        Args:
            event_dict: Event as dictionary
            project_id: Project identifier

        Returns:
            True if successful
        """
        try:
            event = SentryEvent(**event_dict)
            return self.process_event(event, project_id)
        except Exception as e:
            logger.error(f"Failed to process event dict: {e}")
            return False


# Global pipeline instance
_pipeline: Optional[ETLPipeline] = None


def get_pipeline() -> ETLPipeline:
    """
    Get global pipeline instance.

    Thread-safe initialization of all components.

    Returns:
        ETLPipeline instance
    """
    global _pipeline

    if _pipeline is None:
        with _pipeline_lock:
            # Double-check locking pattern
            if _pipeline is None:
                # Initialize components
                transformer = EventTransformer()

                enricher = get_enricher(
                    geoip_db_path=settings.geoip_database_path if settings.enable_geoip else None
                )

                os_client = get_opensearch_client(settings)
                indexer = EventIndexer(
                    client=os_client,
                    index_prefix=settings.opensearch_index_prefix,
                )

                _pipeline = ETLPipeline(
                    transformer=transformer,
                    enricher=enricher,
                    indexer=indexer,
                )

                logger.info("pipeline_initialized")

    return _pipeline


def reset_pipeline() -> None:
    """Reset global pipeline instance."""
    global _pipeline
    with _pipeline_lock:
        _pipeline = None
