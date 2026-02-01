"""OpenSearch event indexer for bulk operations."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from .client import OpenSearchClient

logger = logging.getLogger(__name__)


class EventIndexer:
    """
    OpenSearch event indexer.

    Handles single and bulk index operations for Sentry events.
    """

    def __init__(
        self,
        client: OpenSearchClient,
        index_prefix: str = "sentry-events",
    ):
        """
        Initialize event indexer.

        Args:
            client: OpenSearchClient instance
            index_prefix: Prefix for index names
        """
        self.client = client
        self.index_prefix = index_prefix
        self._os_client: Optional[OpenSearch] = None

    @property
    def os_client(self) -> OpenSearch:
        """Get OpenSearch client instance."""
        if self._os_client is None:
            self._os_client = self.client.get_client()
        return self._os_client

    def get_index_name(self, timestamp: datetime = None) -> str:
        """
        Get index name based on timestamp.

        Format: {prefix}-YYYY.MM.DD

        Args:
            timestamp: Event timestamp (defaults to now)

        Returns:
            Index name string
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        return f"{self.index_prefix}-{timestamp.strftime('%Y.%m.%d')}"

    def index_single(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index a single event document.

        Args:
            document: Event document to index

        Returns:
            Index result dict with id and result status
        """
        timestamp = self._extract_timestamp(document)
        index_name = self.get_index_name(timestamp)
        event_id = document.get("event_id")

        try:
            result = self.os_client.index(
                index=index_name,
                id=event_id,
                body=document,
                refresh=False,  # Don't wait for refresh
            )

            logger.debug(f"Indexed event {event_id} to {index_name}")

            return {
                "id": result.get("_id"),
                "index": result.get("_index"),
                "result": result.get("result"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to index event {event_id}: {e}")
            return {
                "id": event_id,
                "success": False,
                "error": str(e),
            }

    def bulk_index(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk index multiple event documents.

        Args:
            documents: List of event documents

        Returns:
            Result dict with success/failed counts and errors
        """
        if not documents:
            return {"success": 0, "failed": 0, "errors": []}

        # Prepare bulk actions
        actions = []
        for doc in documents:
            action = self._prepare_bulk_action(doc)
            actions.append(action)

        # Execute bulk request
        try:
            success, failed = bulk(
                self.os_client,
                actions,
                raise_on_error=False,
                raise_on_exception=False,
            )

            # Process failed items
            errors = []
            if isinstance(failed, list):
                for item in failed:
                    if isinstance(item, dict):
                        errors.append(str(item))

            logger.info(f"Bulk indexed {success} events, {len(errors)} failed")

            return {
                "success": success,
                "failed": len(errors),
                "errors": errors[:10],  # Limit error messages
            }

        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            return {
                "success": 0,
                "failed": len(documents),
                "errors": [str(e)],
            }

    def _prepare_bulk_action(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare document for bulk API.

        Args:
            document: Event document

        Returns:
            Bulk action dict
        """
        timestamp = self._extract_timestamp(document)
        index_name = self.get_index_name(timestamp)

        return {
            "_index": index_name,
            "_id": document.get("event_id"),
            "_source": document,
        }

    def _extract_timestamp(self, document: Dict[str, Any]) -> datetime:
        """
        Extract timestamp from document.

        Args:
            document: Event document

        Returns:
            datetime object
        """
        timestamp = document.get("@timestamp") or document.get("timestamp")

        if timestamp is None:
            return datetime.utcnow()

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, (int, float)):
            return datetime.utcfromtimestamp(timestamp)

        if isinstance(timestamp, str):
            try:
                # Handle ISO format with Z suffix
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pass

        return datetime.utcnow()

    def delete_old_indices(self, days_to_keep: int = 90) -> List[str]:
        """
        Delete indices older than specified days.

        Args:
            days_to_keep: Number of days to keep

        Returns:
            List of deleted index names
        """
        return self.client.delete_old_indices(days_to_keep)

    def get_document_count(self, index_pattern: str = None) -> int:
        """
        Get total document count across indices.

        Args:
            index_pattern: Index pattern to match

        Returns:
            Total document count
        """
        pattern = index_pattern or f"{self.index_prefix}-*"

        try:
            result = self.os_client.count(index=pattern)
            return result.get("count", 0)
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def refresh_indices(self, index_pattern: str = None) -> bool:
        """
        Refresh indices to make documents searchable.

        Args:
            index_pattern: Index pattern to match

        Returns:
            True if successful
        """
        pattern = index_pattern or f"{self.index_prefix}-*"

        try:
            self.os_client.indices.refresh(index=pattern)
            return True
        except Exception as e:
            logger.error(f"Failed to refresh indices: {e}")
            return False
