"""Configuration management using Pydantic Settings."""

from typing import List, Optional

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

    # Authentication - DSN public keys
    allowed_public_keys: List[str] = []  # Empty = allow all

    # Projects
    project_ids: List[int] = []  # Empty = allow all

    # OpenSearch
    opensearch_hosts: List[str] = ["http://localhost:9200"]
    opensearch_username: Optional[str] = None
    opensearch_password: Optional[str] = None
    opensearch_index_prefix: str = "sentry-events"
    opensearch_use_ssl: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Processing
    batch_size: int = 100
    batch_timeout_seconds: int = 5
    use_celery: bool = True  # Set to False for synchronous processing

    # Enrichment
    geoip_database_path: Optional[str] = None
    enable_geoip: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()
