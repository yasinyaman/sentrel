"""Sentry event payload parser and models."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import orjson
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


def convert_timestamp(v: Any) -> Optional[float]:
    """Convert timestamp to float, handling ISO 8601 strings."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            # Try parsing ISO 8601 format
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return None
    return None


class SentryException(BaseModel):
    """Sentry exception representation."""

    type: str = "Error"
    value: str = ""
    module: Optional[str] = None
    stacktrace: Optional[dict] = None
    mechanism: Optional[dict] = None


class SentryUser(BaseModel):
    """Sentry user context."""

    id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    name: Optional[str] = None


class SentryRequest(BaseModel):
    """Sentry HTTP request context."""

    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    query_string: Optional[str] = None
    data: Optional[Any] = None
    env: Optional[Dict[str, str]] = None


class SentryBreadcrumb(BaseModel):
    """Sentry breadcrumb for event trail."""

    timestamp: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    message: Optional[str] = None
    level: Optional[str] = None
    data: Optional[dict] = None

    @model_validator(mode="before")
    @classmethod
    def preprocess_data(cls, data: Any) -> Any:
        """Preprocess data before validation."""
        if isinstance(data, dict) and "timestamp" in data:
            data["timestamp"] = convert_timestamp(data["timestamp"])
        return data


class SentryEvent(BaseModel):
    """
    Sentry SDK Event Model.

    This represents the full event payload sent by Sentry SDKs.
    """

    model_config = {"extra": "allow"}  # Allow additional fields from SDK

    # Identifiers
    event_id: Optional[str] = None
    timestamp: Optional[float] = None
    platform: Optional[str] = None
    level: str = "error"
    logger: Optional[str] = None
    transaction: Optional[str] = None
    server_name: Optional[str] = None
    release: Optional[str] = None
    dist: Optional[str] = None
    environment: Optional[str] = "production"

    # Message
    message: Optional[str] = None
    logentry: Optional[dict] = None  # {"message": "...", "params": [...]}

    # Exception
    exception: Optional[dict] = None  # {"values": [SentryException]}

    # Context
    user: Optional[SentryUser] = None
    request: Optional[SentryRequest] = None
    contexts: Optional[dict] = None  # browser, os, device, runtime
    tags: Optional[Dict[str, str]] = None
    extra: Optional[dict] = None
    fingerprint: Optional[List[str]] = None

    # Breadcrumbs
    breadcrumbs: Optional[dict] = None  # {"values": [SentryBreadcrumb]}

    # SDK info
    sdk: Optional[dict] = None

    # Modules/packages
    modules: Optional[Dict[str, str]] = None

    @model_validator(mode="before")
    @classmethod
    def preprocess_data(cls, data: Any) -> Any:
        """Preprocess data before validation, converting timestamp."""
        if isinstance(data, dict) and "timestamp" in data:
            data["timestamp"] = convert_timestamp(data["timestamp"])
        return data


class EventParser:
    """Sentry Event JSON payload parser."""

    def parse(self, payload: bytes) -> SentryEvent:
        """
        Parse JSON payload to SentryEvent.

        Args:
            payload: Raw JSON bytes

        Returns:
            SentryEvent object
        """
        if not payload or not payload.strip():
            return SentryEvent()

        try:
            data = orjson.loads(payload)

            # Pre-process timestamp before Pydantic validation
            if "timestamp" in data:
                data["timestamp"] = convert_timestamp(data["timestamp"])

            # Handle user as dict or model
            if "user" in data and isinstance(data["user"], dict):
                data["user"] = SentryUser(**data["user"])

            # Handle request as dict or model
            if "request" in data and isinstance(data["request"], dict):
                data["request"] = SentryRequest(**data["request"])

            return SentryEvent(**data)
        except (orjson.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse event payload: {e}")
            return SentryEvent()

    def extract_message(self, event: SentryEvent) -> str:
        """
        Extract readable message from event.

        Priority: exception > message > logentry

        Args:
            event: SentryEvent object

        Returns:
            Human-readable message string
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
            msg = event.logentry.get("message", "")
            params = event.logentry.get("params", [])
            if params and "%s" in msg:
                try:
                    return msg % tuple(params)
                except (TypeError, ValueError):
                    pass
            return msg

        return "No message"

    def extract_exceptions(self, event: SentryEvent) -> List[SentryException]:
        """
        Extract exception list from event.

        Args:
            event: SentryEvent object

        Returns:
            List of SentryException objects
        """
        if not event.exception or not event.exception.get("values"):
            return []

        exceptions = []
        for exc_data in event.exception["values"]:
            try:
                exceptions.append(SentryException(**exc_data))
            except Exception as e:
                logger.warning(f"Failed to parse exception: {e}")
                continue

        return exceptions

    def extract_stacktrace(self, event: SentryEvent) -> Optional[str]:
        """
        Format stacktrace as string.

        Args:
            event: SentryEvent object

        Returns:
            Formatted stacktrace string or None
        """
        if not event.exception or not event.exception.get("values"):
            return None

        exc = event.exception["values"][0]
        stacktrace = exc.get("stacktrace", {})
        frames = stacktrace.get("frames", [])

        if not frames:
            return None

        lines = []

        # Add exception info at top
        exc_type = exc.get("type", "Error")
        exc_value = exc.get("value", "")
        lines.append(f"{exc_type}: {exc_value}")
        lines.append("")

        # Format frames (reversed to show most recent first)
        for frame in reversed(frames):
            filename = frame.get("filename", "?")
            lineno = frame.get("lineno", "?")
            function = frame.get("function", "?")
            module = frame.get("module", "")

            if module:
                lines.append(f'  File "{filename}", line {lineno}, in {module}.{function}')
            else:
                lines.append(f'  File "{filename}", line {lineno}, in {function}')

            # Add context line if available
            context_line = frame.get("context_line")
            if context_line:
                lines.append(f"    {context_line.strip()}")

        return "\n".join(lines)

    def extract_user_agent(self, event: SentryEvent) -> Optional[str]:
        """
        Extract user-agent from request headers or contexts.

        Args:
            event: SentryEvent object

        Returns:
            User-agent string or None
        """
        # Try request headers
        if event.request and event.request.headers:
            for key, value in event.request.headers.items():
                if key.lower() == "user-agent":
                    return value

        # Try contexts
        if event.contexts:
            browser = event.contexts.get("browser", {})
            if browser.get("name"):
                version = browser.get("version", "")
                return f"{browser['name']}/{version}" if version else browser["name"]

        return None

    def extract_ip_address(self, event: SentryEvent) -> Optional[str]:
        """
        Extract IP address from user or request.

        Args:
            event: SentryEvent object

        Returns:
            IP address string or None
        """
        # Try user context
        if event.user and event.user.ip_address:
            return event.user.ip_address

        # Try request env
        if event.request and event.request.env:
            remote_addr = event.request.env.get("REMOTE_ADDR")
            if remote_addr:
                return remote_addr

        return None
