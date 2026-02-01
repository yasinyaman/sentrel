"""DSN authentication handler for Sentry SDK requests."""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


class DSNAuth:
    """
    Sentry DSN Authentication Handler.

    X-Sentry-Auth header format:
    Sentry sentry_version=7, sentry_client=sentry.python/1.0.0,
           sentry_key=<public_key>, sentry_secret=<secret_key>

    Or query parameter:
    ?sentry_key=<public_key>&sentry_version=7
    """

    def __init__(self, allowed_keys: Optional[List[str]] = None):
        """
        Initialize DSN auth handler.

        Args:
            allowed_keys: List of allowed public keys. Empty list = allow all.
        """
        self.allowed_keys = allowed_keys or []

    def parse_auth_header(self, header: str) -> Dict[str, str]:
        """
        Parse X-Sentry-Auth header.

        Args:
            header: Raw X-Sentry-Auth header value

        Returns:
            Dict with parsed key-value pairs
        """
        result = {}

        if not header:
            return result

        # Remove "Sentry " prefix if present
        if header.lower().startswith("sentry "):
            header = header[7:]

        # Parse key=value pairs
        pattern = r"(\w+)=([^,\s]+)"
        matches = re.findall(pattern, header)

        for key, value in matches:
            result[key] = value.strip()

        return result

    def extract_public_key(
        self, auth_header: Optional[str], query_params: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Extract public key from header or query params.

        Args:
            auth_header: X-Sentry-Auth header value
            query_params: URL query parameters

        Returns:
            Public key if found, None otherwise
        """
        # Try header first
        if auth_header:
            parsed = self.parse_auth_header(auth_header)
            if "sentry_key" in parsed:
                return parsed["sentry_key"]

        # Try query params
        if query_params:
            if "sentry_key" in query_params:
                return query_params["sentry_key"]

        return None

    def validate_key(self, public_key: Optional[str]) -> bool:
        """
        Validate public key against allowed list.

        Args:
            public_key: The public key to validate

        Returns:
            True if valid, False otherwise
        """
        if not public_key:
            return False

        # If no allowed keys configured, allow all
        if not self.allowed_keys:
            return True

        return public_key in self.allowed_keys

    def extract_project_id_from_dsn(self, dsn: str) -> Optional[int]:
        """
        Extract project ID from DSN string.

        DSN format: https://<public_key>@<host>/<project_id>

        Args:
            dsn: Full DSN string

        Returns:
            Project ID if found, None otherwise
        """
        if not dsn:
            return None

        try:
            parsed = urlparse(dsn)
            # Project ID is the path without leading slash
            path = parsed.path.strip("/")
            if path:
                return int(path)
        except (ValueError, AttributeError):
            pass

        return None

    def extract_public_key_from_dsn(self, dsn: str) -> Optional[str]:
        """
        Extract public key from DSN string.

        DSN format: https://<public_key>@<host>/<project_id>

        Args:
            dsn: Full DSN string

        Returns:
            Public key if found, None otherwise
        """
        if not dsn:
            return None

        try:
            parsed = urlparse(dsn)
            # Username is the public key
            return parsed.username
        except AttributeError:
            pass

        return None
