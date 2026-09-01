"""Guard the GeneFoundry fleet deploy contract for the numeric image user.

The fleet controller (strato_v6_docker_npm) only deploys a declared, numeric
non-root ``user`` in the overlay it actually applies (``docker-compose.npm.yml``);
the shared release gate forbids ``user`` in the Compose files it validates
(``container-release.json``), so the two must never drift onto the same key.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_USER_RE = re.compile(r"^[1-9][0-9]*:[1-9][0-9]*$")


class _TagTolerantLoader(yaml.SafeLoader):
    """SafeLoader that tolerates Compose's custom merge tags (e.g. ``!reset``)."""


_TagTolerantLoader.add_multi_constructor(
    "!",
    lambda loader, suffix, node: (
        loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else None
    ),
)


def test_npm_overlay_declares_numeric_user_for_every_service() -> None:
    compose = yaml.load(
        (ROOT / "docker" / "docker-compose.npm.yml").read_text(),
        Loader=_TagTolerantLoader,  # noqa: S506
    )
    services = compose["services"]
    assert services, "docker-compose.npm.yml declares no services"
    for name, service in services.items():
        user = service.get("user")
        assert user is not None, f"service {name!r} has no numeric user"
        assert _USER_RE.match(str(user)), f"service {name!r} user={user!r} is not numeric uid:gid"


def test_release_compose_files_do_not_declare_user() -> None:
    release_config = json.loads((ROOT / "container-release.json").read_text())
    compose_files = release_config["service"]["compose_files"]
    assert compose_files, "container-release.json lists no compose files"
    for compose_file in compose_files:
        compose = yaml.load((ROOT / compose_file).read_text(), Loader=_TagTolerantLoader)  # noqa: S506
        for name, service in compose.get("services", {}).items():
            assert "user" not in service, (
                f"{compose_file}: service {name!r} declares user; the release gate forbids this"
            )
