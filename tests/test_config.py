"""Tests for configuration management."""

import pytest
from unittest.mock import patch
import os


class TestSettingsValidation:
    """Tests for settings validation and parsing."""

    def test_parse_allowed_public_keys_empty_string(self):
        """Test parsing empty string for allowed_public_keys."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"ALLOWED_PUBLIC_KEYS": ""}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.allowed_public_keys == []

    def test_parse_allowed_public_keys_json_array(self):
        """Test parsing JSON array for allowed_public_keys."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"ALLOWED_PUBLIC_KEYS": '["key1", "key2"]'}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.allowed_public_keys == ["key1", "key2"]

    def test_parse_allowed_public_keys_comma_separated(self):
        """Test parsing comma-separated string for allowed_public_keys."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"ALLOWED_PUBLIC_KEYS": "key1,key2,key3"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.allowed_public_keys == ["key1", "key2", "key3"]

    def test_parse_project_ids_empty_string(self):
        """Test parsing empty string for project_ids."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"PROJECT_IDS": ""}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.project_ids == []

    def test_parse_project_ids_json_array(self):
        """Test parsing JSON array for project_ids."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"PROJECT_IDS": "[1, 2, 3]"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.project_ids == [1, 2, 3]

    def test_parse_project_ids_comma_separated(self):
        """Test parsing comma-separated string for project_ids."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"PROJECT_IDS": "1,2,3"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.project_ids == [1, 2, 3]

    def test_parse_opensearch_hosts_single(self):
        """Test parsing single OpenSearch host."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"OPENSEARCH_HOSTS": "http://localhost:9200"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.opensearch_hosts == ["http://localhost:9200"]

    def test_parse_opensearch_hosts_json_array(self):
        """Test parsing JSON array for OpenSearch hosts."""
        from src.config import Settings
        
        with patch.dict(
            os.environ,
            {"OPENSEARCH_HOSTS": '["http://host1:9200", "http://host2:9200"]'},
            clear=False
        ):
            settings = Settings(_env_file=None)
            assert settings.opensearch_hosts == ["http://host1:9200", "http://host2:9200"]

    def test_parse_allowed_cors_origins_empty(self):
        """Test parsing empty CORS origins."""
        from src.config import Settings
        
        with patch.dict(os.environ, {"ALLOWED_CORS_ORIGINS": ""}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.allowed_cors_origins == []

    def test_parse_allowed_cors_origins_json_array(self):
        """Test parsing JSON array for CORS origins."""
        from src.config import Settings
        
        with patch.dict(
            os.environ,
            {"ALLOWED_CORS_ORIGINS": '["http://localhost:3000", "http://localhost:8080"]'},
            clear=False
        ):
            settings = Settings(_env_file=None)
            assert settings.allowed_cors_origins == ["http://localhost:3000", "http://localhost:8080"]

    def test_default_values(self):
        """Test default configuration values."""
        from src.config import Settings
        
        # Clear relevant env vars
        env_overrides = {
            "ALLOWED_PUBLIC_KEYS": "[]",
            "PROJECT_IDS": "[]",
            "OPENSEARCH_HOSTS": '["http://localhost:9200"]',
            "ALLOWED_CORS_ORIGINS": "[]",
        }
        
        with patch.dict(os.environ, env_overrides, clear=False):
            settings = Settings(_env_file=None)
            
            assert settings.app_name == "sentrel"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.auth_required is True
            assert settings.max_request_size == 5 * 1024 * 1024
            assert settings.batch_size == 100
            assert settings.batch_timeout_seconds == 5
            assert settings.use_celery is True
            assert settings.rate_limit_enabled is True
            assert settings.rate_limit_requests == 1000
            assert settings.rate_limit_window == 60

    def test_security_defaults(self):
        """Test security-related default values."""
        from src.config import Settings
        
        env_overrides = {
            "ALLOWED_PUBLIC_KEYS": "[]",
            "PROJECT_IDS": "[]",
            "OPENSEARCH_HOSTS": '["http://localhost:9200"]',
            "ALLOWED_CORS_ORIGINS": "[]",
        }
        
        with patch.dict(os.environ, env_overrides, clear=False):
            settings = Settings(_env_file=None)
            
            # Security settings should default to safe values
            assert settings.auth_required is True
            assert settings.opensearch_verify_certs is True
            assert settings.opensearch_use_ssl is False  # Local dev default
