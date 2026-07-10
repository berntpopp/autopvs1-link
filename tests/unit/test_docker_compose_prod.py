"""Guard the production compose against the debug/log-level footgun."""

from pathlib import Path

import yaml

from autopvs1_link.config import Settings


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates the Compose ``!reset`` merge tag."""


_ComposeLoader.add_constructor("!reset", lambda loader, node: None)

_COMPOSE = Path(__file__).resolve().parents[2] / "docker" / "docker-compose.prod.yml"


def _prod_env() -> dict[str, object]:
    data = yaml.load(_COMPOSE.read_text(), Loader=_ComposeLoader)  # noqa: S506
    return data["services"]["autopvs1-link"]["environment"]


def test_prod_compose_sets_environment_production() -> None:
    assert _prod_env().get("AUTOPVS1_LINK_ENVIRONMENT") == "production"


def test_prod_compose_does_not_pin_info_request_logging() -> None:
    # The production preset forces WARNING; pinning INFO would re-enable the
    # per-request log line that can carry variant IDs.
    assert _prod_env().get("AUTOPVS1_LINK_LOG_LEVEL") != "INFO"


def test_production_preset_disables_debug_and_raises_log_level() -> None:
    settings = Settings(environment="production")
    assert settings.debug is False
    assert settings.logging.level == "WARNING"


def test_public_research_compose_explicitly_allows_current_origins() -> None:
    env = _prod_env()
    assert env["AUTOPVS1_LINK_API_EGRESS_MODE"] == "allowlist"
    assert set(env["AUTOPVS1_LINK_API_ALLOWED_UPSTREAM_ORIGINS"].split(",")) == {
        "https://autopvs1.bgi.com",
        "https://rest.ensembl.org",
        "https://grch37.rest.ensembl.org",
    }
