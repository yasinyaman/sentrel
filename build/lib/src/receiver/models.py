"""Internal data models for Sentry events."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventLevel(str, Enum):
    """Sentry event severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ItemType(str, Enum):
    """Sentry envelope item types."""

    EVENT = "event"
    TRANSACTION = "transaction"
    SESSION = "session"
    ATTACHMENT = "attachment"
    USER_REPORT = "user_report"
    CLIENT_REPORT = "client_report"


class ReceivedEvent(BaseModel):
    """Processed event model for internal use."""

    # Identifiers
    event_id: str
    project_id: int
    received_at: datetime = Field(default_factory=datetime.utcnow)

    # Core fields
    timestamp: datetime
    level: EventLevel = EventLevel.ERROR
    platform: Optional[str] = None
    environment: Optional[str] = "production"
    release: Optional[str] = None

    # Message & Exception
    message: str
    exception_type: Optional[str] = None
    exception_value: Optional[str] = None
    stacktrace: Optional[str] = None

    # User
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_ip: Optional[str] = None

    # Context
    browser_name: Optional[str] = None
    browser_version: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    device_family: Optional[str] = None

    # Request
    request_url: Optional[str] = None
    request_method: Optional[str] = None

    # Tags & Extra
    tags: Dict[str, str] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)

    # SDK
    sdk_name: Optional[str] = None
    sdk_version: Optional[str] = None

    # Raw data (optional)
    raw_event: Optional[dict] = None

    class Config:
        use_enum_values = True
