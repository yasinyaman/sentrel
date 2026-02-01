"""Tests for envelope parser."""

import pytest

from src.receiver.envelope_parser import EnvelopeParser, EnvelopeHeader, EnvelopeItem


class TestEnvelopeParser:
    """Test cases for EnvelopeParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EnvelopeParser()

    def test_parse_empty_body(self):
        """Test parsing empty body."""
        result = self.parser.parse(b"")
        assert result.header.event_id is None
        assert len(result.items) == 0

    def test_parse_header_only(self):
        """Test parsing envelope with only header."""
        body = b'{"event_id":"abc123","dsn":"https://key@host/1","sent_at":"2024-01-15T10:00:00Z"}'
        result = self.parser.parse(body)

        assert result.header.event_id == "abc123"
        assert result.header.dsn == "https://key@host/1"
        assert result.header.sent_at == "2024-01-15T10:00:00Z"

    def test_parse_with_event_item(self):
        """Test parsing envelope with event item."""
        body = b'{"event_id":"abc123"}\n{"type":"event","length":50}\n{"exception":{"values":[{"type":"ValueError"}]}}'
        result = self.parser.parse(body)

        assert result.header.event_id == "abc123"
        assert len(result.items) == 1
        assert result.items[0].item_type == "event"

    def test_parse_multiple_items(self):
        """Test parsing envelope with multiple items."""
        body = (
            b'{"event_id":"abc123"}\n'
            b'{"type":"event"}\n'
            b'{"exception":{"values":[]}}\n'
            b'{"type":"session"}\n'
            b'{"sid":"xyz789","status":"ok"}'
        )
        result = self.parser.parse(body)

        assert result.header.event_id == "abc123"
        assert len(result.items) == 2
        assert result.items[0].item_type == "event"
        assert result.items[1].item_type == "session"

    def test_parse_invalid_header(self):
        """Test parsing with invalid header."""
        body = b"not valid json\n"
        result = self.parser.parse(body)

        assert result.header.event_id is None

    def test_extract_events(self):
        """Test extracting event payloads."""
        body = (
            b'{"event_id":"abc123"}\n'
            b'{"type":"event"}\n'
            b'{"message":"test error"}\n'
            b'{"type":"session"}\n'
            b'{"sid":"xyz"}'
        )
        envelope = self.parser.parse(body)
        events = self.parser.extract_events(envelope)

        assert len(events) == 1
        assert b"test error" in events[0]

    def test_extract_sessions(self):
        """Test extracting session payloads."""
        body = (
            b'{"event_id":"abc123"}\n'
            b'{"type":"event"}\n'
            b'{"message":"test"}\n'
            b'{"type":"session"}\n'
            b'{"sid":"xyz789"}'
        )
        envelope = self.parser.parse(body)
        sessions = self.parser.extract_sessions(envelope)

        assert len(sessions) == 1
        assert b"xyz789" in sessions[0]

    def test_parse_with_sdk_info(self):
        """Test parsing envelope with SDK info in header."""
        body = b'{"event_id":"abc123","sdk":{"name":"sentry.python","version":"1.0.0"}}'
        result = self.parser.parse(body)

        assert result.header.sdk is not None
        assert result.header.sdk["name"] == "sentry.python"
        assert result.header.sdk["version"] == "1.0.0"

    def test_parse_transaction_item(self):
        """Test parsing envelope with transaction item."""
        body = (
            b'{"event_id":"abc123"}\n'
            b'{"type":"transaction"}\n'
            b'{"transaction":"GET /api/users","spans":[]}'
        )
        result = self.parser.parse(body)
        events = self.parser.extract_events(result)

        # Transactions should be extracted as events
        assert len(events) == 1
