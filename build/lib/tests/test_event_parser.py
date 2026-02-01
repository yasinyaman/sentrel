"""Tests for event parser."""

import pytest

from src.receiver.event_parser import EventParser, SentryEvent, SentryException


class TestEventParser:
    """Test cases for EventParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EventParser()

    def test_parse_empty_payload(self):
        """Test parsing empty payload."""
        result = self.parser.parse(b"")
        assert result.event_id is None
        assert result.level == "error"

    def test_parse_simple_event(self):
        """Test parsing simple event."""
        payload = b'{"event_id":"abc123","level":"error","message":"Test error"}'
        result = self.parser.parse(payload)

        assert result.event_id == "abc123"
        assert result.level == "error"
        assert result.message == "Test error"

    def test_parse_event_with_exception(self):
        """Test parsing event with exception."""
        payload = b'''{
            "event_id": "abc123",
            "exception": {
                "values": [
                    {"type": "ValueError", "value": "invalid value"}
                ]
            }
        }'''
        result = self.parser.parse(payload)

        assert result.event_id == "abc123"
        assert result.exception is not None
        assert result.exception["values"][0]["type"] == "ValueError"

    def test_parse_event_with_user(self):
        """Test parsing event with user context."""
        payload = b'''{
            "event_id": "abc123",
            "user": {
                "id": "user123",
                "email": "test@example.com",
                "ip_address": "192.168.1.1"
            }
        }'''
        result = self.parser.parse(payload)

        assert result.user is not None
        assert result.user.id == "user123"
        assert result.user.email == "test@example.com"
        assert result.user.ip_address == "192.168.1.1"

    def test_parse_event_with_contexts(self):
        """Test parsing event with contexts."""
        payload = b'''{
            "event_id": "abc123",
            "contexts": {
                "browser": {"name": "Chrome", "version": "120.0"},
                "os": {"name": "Windows", "version": "10"}
            }
        }'''
        result = self.parser.parse(payload)

        assert result.contexts is not None
        assert result.contexts["browser"]["name"] == "Chrome"
        assert result.contexts["os"]["name"] == "Windows"

    def test_extract_message_from_exception(self):
        """Test extracting message from exception."""
        event = SentryEvent(
            exception={
                "values": [{"type": "ValueError", "value": "invalid value"}]
            }
        )
        message = self.parser.extract_message(event)
        assert message == "ValueError: invalid value"

    def test_extract_message_from_message_field(self):
        """Test extracting message from message field."""
        event = SentryEvent(message="Direct message")
        message = self.parser.extract_message(event)
        assert message == "Direct message"

    def test_extract_message_from_logentry(self):
        """Test extracting message from logentry."""
        event = SentryEvent(logentry={"message": "Log message"})
        message = self.parser.extract_message(event)
        assert message == "Log message"

    def test_extract_message_priority(self):
        """Test message extraction priority (exception > message > logentry)."""
        event = SentryEvent(
            message="Direct message",
            exception={"values": [{"type": "Error", "value": "Exception message"}]},
            logentry={"message": "Log message"},
        )
        message = self.parser.extract_message(event)
        assert message == "Error: Exception message"

    def test_extract_exceptions(self):
        """Test extracting exceptions list."""
        event = SentryEvent(
            exception={
                "values": [
                    {"type": "ValueError", "value": "first"},
                    {"type": "KeyError", "value": "second"},
                ]
            }
        )
        exceptions = self.parser.extract_exceptions(event)

        assert len(exceptions) == 2
        assert exceptions[0].type == "ValueError"
        assert exceptions[1].type == "KeyError"

    def test_extract_stacktrace(self):
        """Test extracting stacktrace."""
        event = SentryEvent(
            exception={
                "values": [
                    {
                        "type": "ValueError",
                        "value": "test",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "test.py",
                                    "lineno": 10,
                                    "function": "test_func",
                                    "context_line": "raise ValueError('test')",
                                }
                            ]
                        },
                    }
                ]
            }
        )
        stacktrace = self.parser.extract_stacktrace(event)

        assert stacktrace is not None
        assert "test.py" in stacktrace
        assert "line 10" in stacktrace
        assert "test_func" in stacktrace

    def test_extract_user_agent_from_request(self):
        """Test extracting user-agent from request."""
        from src.receiver.event_parser import SentryRequest

        event = SentryEvent(
            request=SentryRequest(
                headers={"User-Agent": "Mozilla/5.0 Chrome/120.0"}
            )
        )
        user_agent = self.parser.extract_user_agent(event)
        assert user_agent == "Mozilla/5.0 Chrome/120.0"

    def test_extract_ip_address(self):
        """Test extracting IP address."""
        from src.receiver.event_parser import SentryUser

        event = SentryEvent(user=SentryUser(ip_address="192.168.1.1"))
        ip = self.parser.extract_ip_address(event)
        assert ip == "192.168.1.1"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        payload = b"not valid json"
        result = self.parser.parse(payload)
        assert result.event_id is None

    def test_parse_with_tags(self):
        """Test parsing event with tags."""
        payload = b'''{
            "event_id": "abc123",
            "tags": {"environment": "production", "server": "web-1"}
        }'''
        result = self.parser.parse(payload)

        assert result.tags is not None
        assert result.tags["environment"] == "production"
        assert result.tags["server"] == "web-1"
