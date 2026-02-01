"""Tests for DSN authentication."""

import pytest

from src.receiver.auth import DSNAuth


class TestDSNAuth:
    """Test cases for DSNAuth."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth = DSNAuth()
        self.auth_with_keys = DSNAuth(allowed_keys=["key1", "key2"])

    def test_parse_auth_header(self):
        """Test parsing X-Sentry-Auth header."""
        header = "Sentry sentry_version=7, sentry_client=sentry.python/1.0.0, sentry_key=abc123"
        result = self.auth.parse_auth_header(header)

        assert result["sentry_version"] == "7"
        assert result["sentry_client"] == "sentry.python/1.0.0"
        assert result["sentry_key"] == "abc123"

    def test_parse_auth_header_without_prefix(self):
        """Test parsing header without Sentry prefix."""
        header = "sentry_version=7, sentry_key=abc123"
        result = self.auth.parse_auth_header(header)

        assert result["sentry_version"] == "7"
        assert result["sentry_key"] == "abc123"

    def test_parse_auth_header_empty(self):
        """Test parsing empty header."""
        result = self.auth.parse_auth_header("")
        assert result == {}

    def test_parse_auth_header_none(self):
        """Test parsing None header."""
        result = self.auth.parse_auth_header(None)
        assert result == {}

    def test_extract_public_key_from_header(self):
        """Test extracting public key from header."""
        header = "Sentry sentry_key=abc123"
        key = self.auth.extract_public_key(header)
        assert key == "abc123"

    def test_extract_public_key_from_query_params(self):
        """Test extracting public key from query params."""
        key = self.auth.extract_public_key(None, {"sentry_key": "xyz789"})
        assert key == "xyz789"

    def test_extract_public_key_header_priority(self):
        """Test that header takes priority over query params."""
        header = "Sentry sentry_key=from_header"
        key = self.auth.extract_public_key(header, {"sentry_key": "from_query"})
        assert key == "from_header"

    def test_validate_key_allow_all(self):
        """Test that empty allowed_keys allows all."""
        assert self.auth.validate_key("any_key")
        assert self.auth.validate_key("another_key")

    def test_validate_key_with_whitelist(self):
        """Test validation with allowed keys list."""
        assert self.auth_with_keys.validate_key("key1")
        assert self.auth_with_keys.validate_key("key2")
        assert not self.auth_with_keys.validate_key("key3")
        assert not self.auth_with_keys.validate_key("invalid")

    def test_validate_key_none(self):
        """Test validation with None key."""
        assert not self.auth.validate_key(None)
        assert not self.auth_with_keys.validate_key(None)

    def test_extract_project_id_from_dsn(self):
        """Test extracting project ID from DSN."""
        dsn = "https://abc123@sentry.example.com/42"
        project_id = self.auth.extract_project_id_from_dsn(dsn)
        assert project_id == 42

    def test_extract_project_id_from_dsn_with_path(self):
        """Test extracting project ID from DSN with extra path."""
        dsn = "https://abc123@sentry.example.com/1"
        project_id = self.auth.extract_project_id_from_dsn(dsn)
        assert project_id == 1

    def test_extract_project_id_from_dsn_invalid(self):
        """Test extracting project ID from invalid DSN."""
        assert self.auth.extract_project_id_from_dsn("invalid") is None
        assert self.auth.extract_project_id_from_dsn("") is None
        assert self.auth.extract_project_id_from_dsn(None) is None

    def test_extract_public_key_from_dsn(self):
        """Test extracting public key from DSN."""
        dsn = "https://abc123@sentry.example.com/1"
        key = self.auth.extract_public_key_from_dsn(dsn)
        assert key == "abc123"

    def test_extract_public_key_from_dsn_with_secret(self):
        """Test extracting public key from DSN with secret key."""
        dsn = "https://public:secret@sentry.example.com/1"
        key = self.auth.extract_public_key_from_dsn(dsn)
        assert key == "public"

    def test_extract_public_key_from_dsn_invalid(self):
        """Test extracting public key from invalid DSN."""
        assert self.auth.extract_public_key_from_dsn("invalid") is None
        assert self.auth.extract_public_key_from_dsn("") is None
        assert self.auth.extract_public_key_from_dsn(None) is None
