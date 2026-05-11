"""Tests for autopvs1_link.mcp.errors envelopes."""

import pytest

from autopvs1_link.mcp.errors import (
    DestructiveOperationDisabledError,
    MCPToolError,
    UpstreamUnavailableError,
)


def test_mcp_tool_error_basic() -> None:
    e = MCPToolError("boom")
    assert str(e) == "boom"
    assert e.code == "tool_error"
    assert e.details == {}


def test_mcp_tool_error_with_code_and_details() -> None:
    e = MCPToolError("nope", code="custom", details={"k": "v"})
    assert e.code == "custom"
    assert e.details == {"k": "v"}


def test_upstream_unavailable_error_carries_details() -> None:
    e = UpstreamUnavailableError("upstream timed out", url="x", attempt=3)
    assert e.code == "upstream_unavailable"
    assert e.details == {"url": "x", "attempt": 3}


def test_destructive_op_disabled_error_message() -> None:
    e = DestructiveOperationDisabledError("clear_cache")
    assert e.code == "destructive_disabled"
    assert "clear_cache" in str(e)
    assert e.details == {"op": "clear_cache"}


def test_mcp_tool_error_is_exception() -> None:
    with pytest.raises(MCPToolError):
        raise MCPToolError("x")
