"""Extra CLI smoke tests covering banner/print helpers."""

import pytest
from typer.testing import CliRunner

from autopvs1_link import cli

runner = CliRunner()


def test_print_banner_runs() -> None:
    cli.print_banner()


def test_print_config_table_runs() -> None:
    cli.print_config_table()


def test_settings_dict_returns_keys() -> None:
    d = cli._settings_dict()
    for key in ("api", "cache", "server", "logging", "mcp", "version"):
        assert key in d


def test_cli_version_flag() -> None:
    # --version + a subcommand triggers the callback before the subcommand runs.
    result = runner.invoke(cli.app, ["--version", "config"])
    assert result.exit_code == 0
    assert "AutoPVS1-Link" in result.stdout


def test_cli_config_json() -> None:
    result = runner.invoke(cli.app, ["config", "--format", "json"])
    assert result.exit_code == 0


def test_cli_config_invalid_format() -> None:
    result = runner.invoke(cli.app, ["config", "--format", "xml"])
    assert result.exit_code == 2


def test_cli_health_when_server_unreachable() -> None:
    # The CLI should not crash when the server is not running.
    result = runner.invoke(cli.app, ["health"])
    assert result.exit_code == 0


def test_cli_cache_when_server_unreachable() -> None:
    result = runner.invoke(cli.app, ["cache"])
    assert result.exit_code == 0


def test_cli_clear_cache_no_yes_aborts() -> None:
    # Without --yes the prompt is interactive; CliRunner answers "n" by default.
    result = runner.invoke(cli.app, ["clear-cache"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted" in result.stdout


def test_server_py_passes_command_line_arguments_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """`python server.py --host ... --port ...` reaches the `server` command (issue #192)."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "server_entry", Path(__file__).parents[2] / "server.py"
    )
    assert spec is not None and spec.loader is not None
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)

    seen: list[list[str]] = []
    monkeypatch.setattr(entry, "app", seen.append)
    monkeypatch.setattr("sys.argv", ["server.py", "--host", "127.0.0.1", "--port", "8123"])
    entry.main()
    assert seen == [["server", "--host", "127.0.0.1", "--port", "8123"]]
