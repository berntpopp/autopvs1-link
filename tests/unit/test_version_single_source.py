"""Guard: pyproject -> installed metadata -> __version__/SERVER_VERSION/settings -> serverInfo -> /health."""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient

from autopvs1_link import __version__
from autopvs1_link.config import settings
from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.mcp.server_info import SERVER_VERSION

DIST = "autopvs1-link"


def _pyproject_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def test_pyproject_is_the_single_source() -> None:
    assert version(DIST) == _pyproject_version()


def test_all_constants_are_metadata_derived() -> None:
    assert __version__ == version(DIST)
    assert version(DIST) == SERVER_VERSION
    assert settings.version == version(DIST)


def test_mcp_server_info_version_matches_package() -> None:
    assert build_mcp_server().version == version(DIST)


def test_health_version_matches_package() -> None:
    from autopvs1_link.server_manager import app

    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == version(DIST)
