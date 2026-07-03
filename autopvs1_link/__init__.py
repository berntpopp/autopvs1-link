"""AutoPVS1-Link package init."""

from __future__ import annotations

import warnings
from importlib.metadata import PackageNotFoundError, version

import defusedxml

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"defusedxml\.cElementTree is deprecated.*",
        category=DeprecationWarning,
    )
    defusedxml.defuse_stdlib()  # type: ignore[attr-defined]

try:
    __version__ = version("autopvs1-link")
except PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0.0.0"
