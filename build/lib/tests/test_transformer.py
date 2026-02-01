"""Tests for event transformer."""

import pytest
from datetime import datetime

from src.etl.transformer import EventTransformer
from src.receiver.event_parser import SentryEvent, SentryUser, SentryRequest


class TestEventTransformer:
    """Test cases for EventTransformer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = EventTransformer()

    def test_transform_simple_event(self):
        """Test transforming simple event."""
        event = SentryEvent(
            event_id="abc123",
            timestamp=1705312800.0,  # 2024-01-15 10:00:00 UTC
            level="error",
            message="Test error",
            platform="python",
            environment="production",
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["event_id"] == "abc123"
        assert result["project_id"] == 1
        assert result["level"] == "error"
        assert result["message"] == "Test error"
        assert result["platform"] == "python"
        assert result["environment"] == "production"
        assert "@timestamp" in result
        assert "received_at" in result

    def test_transform_with_exception(self):
        """Test transforming event with exception."""
        event = SentryEvent(
            event_id="abc123",
            exception={
                "values": [{"type": "ValueError", "value": "invalid value"}]
            },
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["exception_type"] == "ValueError"
        assert result["exception_value"] == "invalid value"
        assert result["message"] == "ValueError: invalid value"

    def test_transform_user_with_pii_hashing(self):
        """Test that email is hashed for privacy."""
        event = SentryEvent(
            event_id="abc123",
            user=SentryUser(
                id="user123",
                email="test@example.com",
                ip_address="192.168.1.1",
            ),
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["user"]["id"] == "user123"
        assert "email_hash" in result["user"]
        assert result["user"]["email_hash"] != "test@example.com"
        assert len(result["user"]["email_hash"]) == 16  # Truncated hash
        assert result["user"]["ip"] == "192.168.1.1"

    def test_transform_with_contexts(self):
        """Test transforming event with browser/OS contexts."""
        event = SentryEvent(
            event_id="abc123",
            contexts={
                "browser": {"name": "Chrome", "version": "120.0"},
                "os": {"name": "Windows", "version": "10"},
                "device": {"family": "Desktop", "model": "PC"},
                "runtime": {"name": "CPython", "version": "3.11"},
            },
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["browser"]["name"] == "Chrome"
        assert result["browser"]["version"] == "120.0"
        assert result["os"]["name"] == "Windows"
        assert result["device"]["family"] == "Desktop"
        assert result["runtime"]["name"] == "CPython"

    def test_transform_with_request(self):
        """Test transforming event with request info."""
        event = SentryEvent(
            event_id="abc123",
            request=SentryRequest(
                url="https://example.com/api/users",
                method="GET",
            ),
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["request"]["url"] == "https://example.com/api/users"
        assert result["request"]["method"] == "GET"

    def test_transform_with_sdk(self):
        """Test transforming event with SDK info."""
        event = SentryEvent(
            event_id="abc123",
            sdk={"name": "sentry.python", "version": "1.0.0"},
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["sdk"]["name"] == "sentry.python"
        assert result["sdk"]["version"] == "1.0.0"

    def test_transform_with_tags(self):
        """Test transforming event with tags."""
        event = SentryEvent(
            event_id="abc123",
            tags={"server": "web-1", "region": "us-east"},
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["tags"]["server"] == "web-1"
        assert result["tags"]["region"] == "us-east"

    def test_normalize_timestamp_from_float(self):
        """Test timestamp normalization from float."""
        ts = self.transformer._normalize_timestamp(1705312800.0)
        assert isinstance(ts, datetime)
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15

    def test_normalize_timestamp_from_milliseconds(self):
        """Test timestamp normalization from milliseconds."""
        ts = self.transformer._normalize_timestamp(1705312800000.0)
        assert isinstance(ts, datetime)
        assert ts.year == 2024

    def test_normalize_timestamp_from_string(self):
        """Test timestamp normalization from ISO string."""
        ts = self.transformer._normalize_timestamp("2024-01-15T10:00:00Z")
        assert isinstance(ts, datetime)
        assert ts.year == 2024

    def test_normalize_timestamp_none(self):
        """Test timestamp normalization with None."""
        ts = self.transformer._normalize_timestamp(None)
        assert isinstance(ts, datetime)

    def test_compute_fingerprint_from_exception(self):
        """Test fingerprint computation from exception."""
        event = SentryEvent(
            event_id="abc123",
            exception={"values": [{"type": "ValueError"}]},
            platform="python",
        )

        result = self.transformer.transform(event, project_id=1)

        assert "fingerprint" in result
        assert "ValueError" in result["fingerprint"]

    def test_compute_fingerprint_preserves_existing(self):
        """Test that existing fingerprint is preserved."""
        event = SentryEvent(
            event_id="abc123",
            fingerprint=["custom", "fingerprint"],
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["fingerprint"] == ["custom", "fingerprint"]

    def test_transform_removes_none_values(self):
        """Test that None values are removed from result."""
        event = SentryEvent(event_id="abc123")

        result = self.transformer.transform(event, project_id=1)

        # Check that optional fields with None are not in result
        assert "release" not in result or result.get("release") is not None

    def test_extract_stacktrace_formatting(self):
        """Test stacktrace formatting."""
        event = SentryEvent(
            exception={
                "values": [
                    {
                        "type": "ValueError",
                        "value": "test",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "app.py",
                                    "lineno": 42,
                                    "function": "main",
                                    "context_line": "raise ValueError('test')",
                                },
                                {
                                    "filename": "utils.py",
                                    "lineno": 10,
                                    "function": "helper",
                                },
                            ]
                        },
                    }
                ]
            }
        )

        result = self.transformer.transform(event, project_id=1)

        assert result["stacktrace"] is not None
        assert "app.py" in result["stacktrace"]
        assert "utils.py" in result["stacktrace"]
        assert "line 42" in result["stacktrace"]
