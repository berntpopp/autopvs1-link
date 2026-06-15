"""MCP tool: get_server_health."""

from __future__ import annotations

from typing import Annotated, Any, Literal

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from autopvs1_link.config import settings
from autopvs1_link.mcp.annotations import READ_ONLY_CLOSED_WORLD
from autopvs1_link.mcp.envelope import MCPEnvelope, ok_envelope
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION
from autopvs1_link.mcp.tools.cache_tools import destructive_tools_enabled

_UPSTREAM_PROBE_TIMEOUT_SECONDS = 3.0
_TOOL_NAME = "get_server_health"

UpstreamStatus = Literal["not_checked", "reachable", "unreachable"]


class HealthData(BaseModel):
    """Local MCP server health status.

    ``upstream_reachable`` and ``upstream_status`` are populated only when
    the caller passes ``check_upstream=true``; otherwise the fields stay
    at their default ``False`` / ``"not_checked"`` so the cheap-tool
    contract (no upstream cost, sub-millisecond) is preserved.
    """

    status: Literal["ok"] = "ok"
    server: str = SERVER_NAME
    version: str = SERVER_VERSION
    upstream_checked: bool = False
    upstream_reachable: bool = False
    upstream_status: UpstreamStatus = "not_checked"
    destructive_tools_enabled: bool = False


class HealthMCPEnvelope(MCPEnvelope[HealthData]):
    """Envelope schema for ``get_server_health``."""


async def _probe_upstream() -> tuple[bool, UpstreamStatus]:
    """Issue one short HEAD request against the AutoPVS1 base URL.

    Returns ``(reachable, status)``. Network failures degrade to
    ``(False, "unreachable")`` instead of raising so the tool can keep its
    no-throw contract and surface the result as data rather than an error
    envelope. Any 2xx/3xx/4xx HTTP response is treated as ``reachable``:
    the base URL may legitimately respond with 405 to HEAD or 404 to "/",
    and either still proves the host is up.
    """
    url = settings.api.base_url
    try:
        async with httpx.AsyncClient(timeout=_UPSTREAM_PROBE_TIMEOUT_SECONDS) as client:
            response = await client.head(url, follow_redirects=True)
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPError):
        return False, "unreachable"
    # Any HTTP response code proves the host is up; 5xx still means we
    # reached the server but it's degraded — surface as reachable so the
    # caller can still distinguish "AutoPVS1-Link can connect" from
    # "AutoPVS1-Link cannot connect" without us second-guessing upstream
    # health.
    if 200 <= response.status_code < 600:
        return True, "reachable"
    return False, "unreachable"


def register(mcp: FastMCP) -> None:
    """Register the local read-only health tool."""

    @mcp.tool(
        name="get_server_health",
        title="Get AutoPVS1-Link Health",
        tags={"meta", "health"},
        output_schema=HealthMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_CLOSED_WORLD,
    )
    async def get_server_health(
        check_upstream: Annotated[
            bool,
            Field(
                description=(
                    "When true, issue one short HEAD probe against the "
                    "AutoPVS1 base URL and report reachability in "
                    "data.upstream_reachable. Default false keeps the "
                    "cheap-tool contract (no upstream cost, sub-ms)."
                ),
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Return local MCP server health.

        Default behaviour: no upstream call, sub-millisecond. Pass
        ``check_upstream=true`` for an opt-in HEAD probe — useful when an
        agent wants to confirm AutoPVS1 is reachable before scheduling a
        cold scoring call.
        """
        if check_upstream:
            reachable, status = await _probe_upstream()
            data = HealthData(
                upstream_checked=True,
                upstream_reachable=reachable,
                upstream_status=status,
                destructive_tools_enabled=destructive_tools_enabled(),
            )
        else:
            data = HealthData(destructive_tools_enabled=destructive_tools_enabled())
        return ok_envelope(data, tool_name=_TOOL_NAME)
