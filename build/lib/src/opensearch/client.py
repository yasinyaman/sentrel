"""OpenSearch client wrapper with connection management."""

import logging
from typing import Optional

from opensearchpy import OpenSearch
from opensearchpy.exceptions import RequestError

from ..config import Settings
from .mappings import INDEX_TEMPLATE, ISM_POLICY, SENTRY_EVENTS_MAPPING

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    Singleton OpenSearch client wrapper.

    Manages connection lifecycle and provides helper methods
    for index management.
    """

    _instance: Optional[OpenSearch] = None
    _settings: Optional[Settings] = None

    def __init__(self, settings: Settings):
        """
        Initialize OpenSearch client wrapper.

        Args:
            settings: Application settings
        """
        self.settings = settings
        OpenSearchClient._settings = settings

    def get_client(self) -> OpenSearch:
        """
        Get OpenSearch client instance (singleton).

        Returns:
            OpenSearch client instance
        """
        if OpenSearchClient._instance is None:
            auth = None
            if self.settings.opensearch_username:
                auth = (
                    self.settings.opensearch_username,
                    self.settings.opensearch_password or "",
                )

            OpenSearchClient._instance = OpenSearch(
                hosts=self.settings.opensearch_hosts,
                http_auth=auth,
                use_ssl=self.settings.opensearch_use_ssl,
                verify_certs=False,
                ssl_show_warn=False,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )

            logger.info(
                f"OpenSearch client initialized: {self.settings.opensearch_hosts}"
            )

        return OpenSearchClient._instance

    def health_check(self) -> dict:
        """
        Check cluster health.

        Returns:
            Cluster health info dict
        """
        client = self.get_client()
        return client.cluster.health()

    def ensure_index_template(self) -> bool:
        """
        Create or update index template.

        Returns:
            True if successful
        """
        client = self.get_client()
        template_name = f"{self.settings.opensearch_index_prefix}-template"

        try:
            # Use composable template API (OpenSearch 2.x)
            client.indices.put_index_template(
                name=template_name,
                body={
                    "index_patterns": [f"{self.settings.opensearch_index_prefix}-*"],
                    "template": SENTRY_EVENTS_MAPPING,
                    "priority": 100,
                },
            )
            logger.info(f"Index template '{template_name}' created/updated")
            return True

        except RequestError as e:
            logger.error(f"Failed to create index template: {e}")
            return False

    def ensure_ism_policy(self) -> bool:
        """
        Create or update ISM policy.

        Returns:
            True if successful
        """
        client = self.get_client()
        policy_name = f"{self.settings.opensearch_index_prefix}-policy"

        try:
            # Check if policy exists
            try:
                client.transport.perform_request(
                    "GET", f"/_plugins/_ism/policies/{policy_name}"
                )
                # Policy exists, update it
                client.transport.perform_request(
                    "PUT",
                    f"/_plugins/_ism/policies/{policy_name}",
                    body=ISM_POLICY,
                )
                logger.info(f"ISM policy '{policy_name}' updated")

            except Exception:
                # Policy doesn't exist, create it
                client.transport.perform_request(
                    "PUT",
                    f"/_plugins/_ism/policies/{policy_name}",
                    body=ISM_POLICY,
                )
                logger.info(f"ISM policy '{policy_name}' created")

            return True

        except Exception as e:
            logger.warning(f"Failed to create ISM policy (may not be supported): {e}")
            return False

    def create_index_if_not_exists(self, index_name: str) -> bool:
        """
        Create index if it doesn't exist.

        Args:
            index_name: Name of the index

        Returns:
            True if index exists or was created
        """
        client = self.get_client()

        try:
            if not client.indices.exists(index=index_name):
                client.indices.create(index=index_name, body=SENTRY_EVENTS_MAPPING)
                logger.info(f"Index '{index_name}' created")
            return True

        except RequestError as e:
            # Index might have been created by another process
            if "resource_already_exists_exception" in str(e):
                return True
            logger.error(f"Failed to create index '{index_name}': {e}")
            return False

    def get_index_stats(self, index_pattern: str = None) -> dict:
        """
        Get index statistics.

        Args:
            index_pattern: Index pattern to match

        Returns:
            Index stats dict
        """
        client = self.get_client()
        pattern = index_pattern or f"{self.settings.opensearch_index_prefix}-*"

        try:
            return client.indices.stats(index=pattern)
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

    def delete_old_indices(self, days_to_keep: int = 90) -> list:
        """
        Delete indices older than specified days.

        Args:
            days_to_keep: Number of days to keep

        Returns:
            List of deleted index names
        """
        from datetime import datetime, timedelta

        client = self.get_client()
        prefix = self.settings.opensearch_index_prefix
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        deleted = []

        try:
            # Get all matching indices
            indices = client.indices.get(index=f"{prefix}-*")

            for index_name in indices:
                # Parse date from index name (format: prefix-YYYY.MM.DD)
                try:
                    date_str = index_name.replace(f"{prefix}-", "")
                    index_date = datetime.strptime(date_str, "%Y.%m.%d")

                    if index_date < cutoff_date:
                        client.indices.delete(index=index_name)
                        deleted.append(index_name)
                        logger.info(f"Deleted old index: {index_name}")

                except ValueError:
                    # Index name doesn't match expected format
                    continue

        except Exception as e:
            logger.error(f"Failed to delete old indices: {e}")

        return deleted

    def close(self):
        """Close the client connection."""
        if OpenSearchClient._instance:
            OpenSearchClient._instance.close()
            OpenSearchClient._instance = None
            logger.info("OpenSearch client closed")


# Convenience function for getting global client
_global_client: Optional[OpenSearchClient] = None


def get_opensearch_client(settings: Settings = None) -> OpenSearchClient:
    """
    Get global OpenSearch client instance.

    Args:
        settings: Optional settings to initialize with

    Returns:
        OpenSearchClient instance
    """
    global _global_client

    if _global_client is None:
        if settings is None:
            from ..config import settings as default_settings

            settings = default_settings
        _global_client = OpenSearchClient(settings)

    return _global_client
