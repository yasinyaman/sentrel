"""Transform Sentry events to OpenSearch documents."""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..receiver.event_parser import SentryEvent

logger = logging.getLogger(__name__)


class EventTransformer:
    """
    Transform Sentry events to OpenSearch documents.

    Handles field mapping, normalization, and PII hashing.
    """

    def transform(self, event: SentryEvent, project_id: int) -> Dict[str, Any]:
        """
        Transform SentryEvent to OpenSearch document.

        Args:
            event: SentryEvent object
            project_id: Project identifier

        Returns:
            OpenSearch document dict
        """
        timestamp = self._normalize_timestamp(event.timestamp)

        document = {
            # Timestamps
            "@timestamp": timestamp.isoformat(),
            "received_at": datetime.utcnow().isoformat(),
            # Identifiers
            "event_id": event.event_id,
            "project_id": project_id,
            # Core fields
            "level": event.level,
            "platform": event.platform,
            "environment": event.environment or "production",
            "release": event.release,
            "transaction": event.transaction,
            "server_name": event.server_name,
            "logger": event.logger,
            # Message & Exception
            "message": self._extract_message(event),
            "exception_type": self._extract_exception_type(event),
            "exception_value": self._extract_exception_value(event),
            "stacktrace": self._extract_stacktrace(event),
            # User
            "user": self._transform_user(event),
            # Contexts
            "browser": self._extract_browser(event),
            "os": self._extract_os(event),
            "device": self._extract_device(event),
            "runtime": self._extract_runtime(event),
            # Request
            "request": self._transform_request(event),
            # Tags
            "tags": event.tags or {},
            # SDK
            "sdk": self._transform_sdk(event),
            # Fingerprint
            "fingerprint": self._compute_fingerprint(event),
        }

        # Remove None values to keep documents clean
        return {k: v for k, v in document.items() if v is not None}

    def _normalize_timestamp(self, ts: Optional[float]) -> datetime:
        """
        Normalize timestamp to datetime.

        Args:
            ts: Unix timestamp or ISO string

        Returns:
            datetime object
        """
        if ts is None:
            return datetime.utcnow()

        if isinstance(ts, datetime):
            return ts

        if isinstance(ts, (int, float)):
            # Handle both seconds and milliseconds
            if ts > 1e12:
                ts = ts / 1000
            return datetime.utcfromtimestamp(ts)

        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                pass

        return datetime.utcnow()

    def _extract_message(self, event: SentryEvent) -> str:
        """
        Extract readable message from event.

        Priority: exception > message > logentry

        Args:
            event: SentryEvent object

        Returns:
            Message string
        """
        # 1. Exception
        if event.exception and event.exception.get("values"):
            exc = event.exception["values"][0]
            exc_type = exc.get("type", "Error")
            exc_value = exc.get("value", "")
            if exc_value:
                return f"{exc_type}: {exc_value}"
            return exc_type

        # 2. Message
        if event.message:
            return event.message

        # 3. Logentry
        if event.logentry:
            return event.logentry.get("message", "")

        return "No message"

    def _extract_exception_type(self, event: SentryEvent) -> Optional[str]:
        """Extract exception type from event."""
        if event.exception and event.exception.get("values"):
            return event.exception["values"][0].get("type")
        return None

    def _extract_exception_value(self, event: SentryEvent) -> Optional[str]:
        """Extract exception value from event."""
        if event.exception and event.exception.get("values"):
            return event.exception["values"][0].get("value")
        return None

    def _extract_stacktrace(self, event: SentryEvent) -> Optional[str]:
        """
        Format stacktrace as string.

        Args:
            event: SentryEvent object

        Returns:
            Formatted stacktrace or None
        """
        if not event.exception or not event.exception.get("values"):
            return None

        exc = event.exception["values"][0]
        stacktrace = exc.get("stacktrace", {})
        frames = stacktrace.get("frames", [])

        if not frames:
            return None

        lines = []
        for frame in reversed(frames):
            filename = frame.get("filename", "?")
            lineno = frame.get("lineno", "?")
            function = frame.get("function", "?")
            lines.append(f'  File "{filename}", line {lineno}, in {function}')

            context_line = frame.get("context_line")
            if context_line:
                lines.append(f"    {context_line.strip()}")

        return "\n".join(lines)

    def _transform_user(self, event: SentryEvent) -> Dict[str, Any]:
        """
        Transform user info with PII hashing.

        Args:
            event: SentryEvent object

        Returns:
            User dict with hashed PII
        """
        if not event.user:
            return {}

        result = {}

        if event.user.id:
            result["id"] = event.user.id

        if event.user.email:
            # Hash email for privacy
            result["email_hash"] = hashlib.sha256(
                event.user.email.lower().encode()
            ).hexdigest()[:16]

        if event.user.username:
            result["username"] = event.user.username

        if event.user.ip_address:
            result["ip"] = event.user.ip_address

        return result if result else {}

    def _extract_browser(self, event: SentryEvent) -> Dict[str, str]:
        """Extract browser info from contexts."""
        if not event.contexts:
            return {}

        browser = event.contexts.get("browser", {})
        if not browser:
            return {}

        result = {}
        if browser.get("name"):
            result["name"] = browser["name"]
        if browser.get("version"):
            result["version"] = browser["version"]

        return result if result else {}

    def _extract_os(self, event: SentryEvent) -> Dict[str, str]:
        """Extract OS info from contexts."""
        if not event.contexts:
            return {}

        os_ctx = event.contexts.get("os", {})
        if not os_ctx:
            return {}

        result = {}
        if os_ctx.get("name"):
            result["name"] = os_ctx["name"]
        if os_ctx.get("version"):
            result["version"] = os_ctx["version"]

        return result if result else {}

    def _extract_device(self, event: SentryEvent) -> Dict[str, str]:
        """Extract device info from contexts."""
        if not event.contexts:
            return {}

        device = event.contexts.get("device", {})
        if not device:
            return {}

        result = {}
        if device.get("family"):
            result["family"] = device["family"]
        if device.get("model"):
            result["model"] = device["model"]
        if device.get("brand"):
            result["brand"] = device["brand"]

        return result if result else {}

    def _extract_runtime(self, event: SentryEvent) -> Dict[str, str]:
        """Extract runtime info from contexts."""
        if not event.contexts:
            return {}

        runtime = event.contexts.get("runtime", {})
        if not runtime:
            return {}

        result = {}
        if runtime.get("name"):
            result["name"] = runtime["name"]
        if runtime.get("version"):
            result["version"] = runtime["version"]

        return result if result else {}

    def _transform_request(self, event: SentryEvent) -> Dict[str, str]:
        """Transform request info."""
        if not event.request:
            return {}

        result = {}
        if event.request.url:
            result["url"] = event.request.url
        if event.request.method:
            result["method"] = event.request.method

        return result if result else {}

    def _transform_sdk(self, event: SentryEvent) -> Dict[str, str]:
        """Transform SDK info."""
        if not event.sdk:
            return {}

        result = {}
        if event.sdk.get("name"):
            result["name"] = event.sdk["name"]
        if event.sdk.get("version"):
            result["version"] = event.sdk["version"]

        return result if result else {}

    def _compute_fingerprint(self, event: SentryEvent) -> List[str]:
        """
        Compute fingerprint for event grouping.

        Args:
            event: SentryEvent object

        Returns:
            List of fingerprint components
        """
        # Use existing fingerprint if provided
        if event.fingerprint:
            return event.fingerprint

        # Generate default fingerprint
        components = []

        # Exception type
        exc_type = self._extract_exception_type(event)
        if exc_type:
            components.append(exc_type)

        # Transaction/logger
        if event.transaction:
            components.append(event.transaction)
        elif event.logger:
            components.append(event.logger)

        # Platform
        if event.platform:
            components.append(event.platform)

        return components if components else ["{{ default }}"]
