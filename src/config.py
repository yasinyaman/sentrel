"""Configuration management using Pydantic Settings."""

from typing import List, Optional, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "sentrel"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    auth_required: bool = True  # Require authentication (set False only for development)
    allowed_public_keys: List[str] = []  # DSN public keys (required if auth_required=True)
    allowed_cors_origins: List[str] = []  # CORS origins (empty = deny all in production)
    max_request_size: int = 5 * 1024 * 1024  # 5MB default max request size

    # Projects
    project_ids: List[int] = []  # Empty = allow all

    # OpenSearch
    opensearch_hosts: List[str] = ["http://localhost:9200"]
    opensearch_username: Optional[str] = None
    opensearch_password: Optional[str] = None
    opensearch_index_prefix: str = "sentry-events"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = True  # Enable SSL certificate verification
    opensearch_ca_certs: Optional[str] = None  # Path to CA certificates

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Processing
    batch_size: int = 100
    batch_timeout_seconds: int = 5
    use_celery: bool = True  # Set to False for synchronous processing

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000  # Max requests per window
    rate_limit_window: int = 60  # Window in seconds

    # Enrichment
    geoip_database_path: Optional[str] = None
    enable_geoip: bool = False

    @field_validator("allowed_public_keys", mode="before")
    @classmethod
    def parse_allowed_public_keys(cls, v: Any) -> List[str]:
        """Parse allowed_public_keys from string or list."""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return []

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def parse_allowed_cors_origins(cls, v: Any) -> List[str]:
        """Parse allowed_cors_origins from string or list."""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return []

    @field_validator("project_ids", mode="before")
    @classmethod
    def parse_project_ids(cls, v: Any) -> List[int]:
        """Parse project_ids from string or list."""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            result = []
            for x in v.split(","):
                x = x.strip()
                if x:
                    try:
                        result.append(int(x))
                    except ValueError:
                        pass
            return result
        return []

    @field_validator("opensearch_hosts", mode="before")
    @classmethod
    def parse_opensearch_hosts(cls, v: Any) -> List[str]:
        """Parse opensearch_hosts from string or list."""
        if v is None or v == "":
            return ["http://localhost:9200"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return ["http://localhost:9200"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()
