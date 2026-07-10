"""Tests for the Settings class branches not covered by env-prefix tests."""

import pytest
from pydantic import ValidationError

from autopvs1_link.config import (
    APIConfig,
    CacheConfig,
    LoggingConfig,
    MCPConfig,
    ServerConfig,
    Settings,
)


def test_api_config_defaults() -> None:
    cfg = APIConfig()
    assert cfg.base_url.startswith("https://")
    assert cfg.request_timeout > 0


def test_cache_config_ttl_seconds() -> None:
    cfg = CacheConfig()
    assert cfg.ttl_seconds == cfg.ttl_hours * 3600


def test_server_config_cors_validator_rejects_bad_origin() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(cors_origins="not-a-url,https://ok.example.com")


def test_server_config_cors_validator_accepts_wildcard() -> None:
    cfg = ServerConfig(cors_origins="*")
    assert cfg.cors_origins == "*"


def test_logging_config_defaults() -> None:
    cfg = LoggingConfig()
    assert cfg.level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def test_mcp_config_defaults() -> None:
    cfg = MCPConfig()
    assert cfg.name


def test_settings_environment_validator_lowercases() -> None:
    s = Settings(environment="development")
    assert s.environment == "development"


def test_settings_is_development_flag() -> None:
    s = Settings(environment="development")
    assert s.is_development
    assert not s.is_production


def test_settings_production_overrides() -> None:
    s = Settings(environment="production")
    assert s.is_production
    assert s.debug is False
    assert s.logging.json_format is True


def test_api_config_defaults_to_disabled_egress() -> None:
    cfg = APIConfig()
    assert cfg.egress_policy.mode == "disabled"
    assert cfg.egress_policy.allowed_origins == frozenset()


def test_api_config_requires_origins_in_allowlist_mode() -> None:
    cfg = APIConfig(egress_mode="allowlist", allowed_upstream_origins="")
    with pytest.raises(ValueError, match="requires at least one exact origin"):
        _ = cfg.egress_policy


def test_api_config_normalizes_allowed_origins() -> None:
    cfg = APIConfig(
        egress_mode="allowlist",
        allowed_upstream_origins="https://AUTOPVS1.BGI.COM/, https://rest.ensembl.org",
    )
    assert cfg.egress_policy.allowed_origins == frozenset(
        {"https://autopvs1.bgi.com", "https://rest.ensembl.org"}
    )
