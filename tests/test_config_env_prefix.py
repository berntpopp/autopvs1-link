"""Tests for the AUTOPVS1_LINK_ env-prefix migration."""

import importlib
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
