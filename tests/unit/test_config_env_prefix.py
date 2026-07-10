"""Tests for the AUTOPVS1_LINK_ env-prefix migration."""

import importlib
import os
import subprocess
import sys
import warnings


def test_new_prefix_overrides_default(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_CACHE_SIZE", "999")
    import autopvs1_link.config as config

    importlib.reload(config)
    assert config.settings.cache.size == 999


def test_old_prefix_still_read_with_deprecation_warning(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPVS1_LINK_CACHE_SIZE", raising=False)
    monkeypatch.setenv("AUTOPVS1_CACHE_SIZE", "111")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        import autopvs1_link.config as config

        importlib.reload(config)
        assert config.settings.cache.size == 111
        msgs = [str(w.message) for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert any("AUTOPVS1_CACHE_SIZE" in m for m in msgs)


def test_new_prefix_wins_over_old(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_CACHE_SIZE", "222")
    monkeypatch.setenv("AUTOPVS1_CACHE_SIZE", "333")
    import autopvs1_link.config as config

    importlib.reload(config)
    assert config.settings.cache.size == 222


def test_prefixed_production_environment_activates_secure_preset() -> None:
    code = """
from autopvs1_link.config import settings
print(settings.environment, settings.debug, settings.logging.level)
"""
    env = os.environ.copy()
    env["AUTOPVS1_LINK_ENVIRONMENT"] = "production"
    result = subprocess.run(  # noqa: S603 - fixed interpreter and inline test code
        [sys.executable, "-c", code],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.strip() == "production False WARNING"
