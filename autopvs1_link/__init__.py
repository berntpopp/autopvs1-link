"""AutoPVS1-Link package init."""

from __future__ import annotations

import warnings

import defusedxml

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"defusedxml\.cElementTree is deprecated.*",
        category=DeprecationWarning,
    )
    defusedxml.defuse_stdlib()  # type: ignore[attr-defined]

__version__ = "2.0.0"
