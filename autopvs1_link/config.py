"""Advanced configuration management for AutoPVS1 Link."""

import os
import warnings
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from autopvs1_link import __version__

# ---------------------------------------------------------------------------
# Backward-compat shim: copy AUTOPVS1_* env vars to AUTOPVS1_LINK_* when the
# new-prefixed variable is unset. Emits one DeprecationWarning naming each
# migrated variable. Runs at import time so subsequent Settings(...) reads
# observe the migrated values.
# ---------------------------------------------------------------------------

_OLD_TO_NEW_PREFIXES: tuple[tuple[str, str], ...] = (
    ("AUTOPVS1_API_", "AUTOPVS1_LINK_API_"),
    ("AUTOPVS1_CACHE_", "AUTOPVS1_LINK_CACHE_"),
    ("AUTOPVS1_SERVER_", "AUTOPVS1_LINK_SERVER_"),
    ("AUTOPVS1_LOG_", "AUTOPVS1_LINK_LOG_"),
    ("AUTOPVS1_MCP_", "AUTOPVS1_LINK_MCP_"),
)


def _migrate_legacy_env() -> None:
    migrated: list[str] = []
    for old_prefix, new_prefix in _OLD_TO_NEW_PREFIXES:
        for key, value in list(os.environ.items()):
            if key.startswith(old_prefix):
                suffix = key[len(old_prefix) :]
                new_key = new_prefix + suffix
                if new_key not in os.environ:
                    os.environ[new_key] = value
                    migrated.append(key)
    if migrated:
        warnings.warn(
            "Detected legacy AUTOPVS1_* env vars: "
            + ", ".join(sorted(migrated))
            + ". Rename to AUTOPVS1_LINK_*. Compat shim will be removed in a "
            "future release.",
            DeprecationWarning,
            stacklevel=2,
        )


_migrate_legacy_env()


class APIConfig(BaseSettings):
    """API-specific configuration settings."""

    model_config = {"env_prefix": "AUTOPVS1_LINK_API_", "env_file": ".env"}

    base_url: str = Field(
        default="https://autopvs1.bgi.com", description="Base URL for AutoPVS1 service"
    )
    request_timeout: int = Field(
        default=30, ge=1, le=300, description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of HTTP retries")
    retry_delay: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Delay between retries in seconds"
    )
    rate_limit_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between requests for rate limiting",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for HTTP requests",
    )


class CacheConfig(BaseSettings):
    """Cache configuration settings."""

    model_config = {"env_prefix": "AUTOPVS1_LINK_CACHE_", "env_file": ".env"}

    enabled: bool = Field(default=True, description="Enable/disable caching")
    size: int = Field(default=256, ge=1, le=10000, description="Maximum number of cache entries")
    ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Cache TTL in hours",
    )
    statistics_enabled: bool = Field(default=True, description="Enable cache statistics collection")
    event_logging: bool = Field(default=False, description="Enable detailed cache event logging")

    @property
    def ttl_seconds(self) -> int:
        """Get TTL in seconds."""
        return self.ttl_hours * 3600


class ServerConfig(BaseSettings):
    """Server configuration settings."""

    model_config = {"env_prefix": "AUTOPVS1_LINK_SERVER_", "env_file": ".env"}

    host: str = Field(default="0.0.0.0", description="Server host address")  # noqa: S104
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    cors_origins: str = Field(default="*", description="CORS allowed origins (comma-separated)")
    workers: int = Field(default=1, ge=1, le=32, description="Number of worker processes")

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins format."""
        if v and v != "*":
            origins = [origin.strip() for origin in v.split(",")]
            for origin in origins:
                if not (
                    origin.startswith("http://")
                    or origin.startswith("https://")
                    or origin == "localhost"
                ):
                    raise ValueError(f"Invalid CORS origin: {origin}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins as a list (``["*"]`` for the wildcard default)."""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""

    model_config = {"env_prefix": "AUTOPVS1_LINK_LOG_", "env_file": ".env"}

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    json_format: bool = Field(default=False, description="Use JSON logging format")
    structured: bool = Field(default=True, description="Use structured logging with context")
    correlation_ids: bool = Field(default=True, description="Include correlation IDs in logs")
    performance_logging: bool = Field(default=True, description="Enable performance logging")
    suppress_third_party: bool = Field(
        default=True, description="Suppress noisy third-party loggers"
    )


class MCPConfig(BaseSettings):
    """MCP (Model Context Protocol) configuration settings."""

    model_config = {"env_prefix": "AUTOPVS1_LINK_MCP_", "env_file": ".env"}

    name: str = Field(default="AutoPVS1 Link", description="MCP server name")
    version: str = Field(default=__version__, description="MCP server version")
    description: str = Field(
        default="AutoPVS1 genetic variant analysis tools",
        description="MCP server description",
    )
    stdio_buffer_size: int = Field(
        default=8192,
        ge=1024,
        le=65536,
        description="STDIO buffer size for MCP communication",
    )
    enable_stdio_protection: bool = Field(
        default=True,
        description="Enable STDIO protection for reliable MCP communication",
    )
    custom_tool_names: bool = Field(
        default=True, description="Use custom tool names for better LLM experience"
    )


class Settings(BaseSettings):
    """Main application settings aggregating all configuration classes."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=True, description="Enable debug mode")
    version: str = Field(default=__version__, description="Application version")

    api: APIConfig = Field(default_factory=APIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate and normalize environment setting."""
        return v.lower()

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def __init__(self, **kwargs):
        """Initialize settings with environment-specific defaults."""
        super().__init__(**kwargs)

        if self.is_production:
            self.debug = False
            self.server.reload = False
            self.logging.level = "WARNING"
            self.logging.json_format = True
        elif self.environment == "staging":
            self.debug = False
            self.server.reload = False
            self.logging.level = "INFO"
            self.logging.json_format = True


# Global settings instance
settings = Settings()
