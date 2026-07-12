"""Reproducible builder bootstrap guard (finding F-19).

The builder stage must not bootstrap a floating pip/uv (`pip install --upgrade`);
uv must be copied from the fleet's digest-pinned installer image so the build is
reproducible and supply-chain-anchored.
"""

from pathlib import Path

_DOCKERFILE = Path(__file__).resolve().parents[2] / "docker" / "Dockerfile"

# Verbatim fleet-shared uv anchor (the router's docker/Dockerfile pin).
_UV_COPY = (
    "COPY --from=ghcr.io/astral-sh/uv:0.8.7@sha256:"
    "1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab "
    "/uv /usr/local/bin/uv"
)


def test_dockerfile_has_no_floating_pip_upgrade() -> None:
    text = _DOCKERFILE.read_text(encoding="utf-8")
    assert "pip install --upgrade" not in text, "floating pip/uv upgrade must be removed"


def test_dockerfile_pins_uv_from_digest_image() -> None:
    text = _DOCKERFILE.read_text(encoding="utf-8")
    assert _UV_COPY in text, "uv must be copied from the digest-pinned installer image"
