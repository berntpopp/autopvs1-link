"""Shared mapping from an upstream HTTP status to an MCP error code.

One definition so every path (single-variant, CNV, search, and the per-item bulk
runners) classifies an upstream failure the same way. HTTP 429 maps to
``rate_limited`` — a distinct, advertised enum value — so a caller can branch
throttle-vs-outage; anything else non-404 is ``upstream_unavailable``.
"""

from __future__ import annotations


def http_status_error_code(status_code: int) -> str:
    """Map an upstream HTTP status onto the MCP error code."""
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    return "upstream_unavailable"


def is_retryable_status(status_code: int) -> bool:
    """True for transient upstream statuses a caller may retry (408, 429, 5xx)."""
    return status_code in {408, 429} or status_code >= 500
