"""Smoke tests for the typer-based CLI."""

from typer.testing import CliRunner

from autopvs1_link.cli import app

runner = CliRunner()


def test_cli_root_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("server", "mcp", "health", "cache", "clear-cache", "config"):
        assert command in result.stdout


def test_cli_config_runs() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
