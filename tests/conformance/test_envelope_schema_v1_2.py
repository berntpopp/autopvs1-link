"""Response-Envelope v1.2: every tool result validates against the published JSON Schema.

The schema is vendored from https://github.com/berntpopp/genefoundry-envelope at tag v1.2.0.
The upstream is the recorded AutoPVS1 HTML under tests/fixtures, served at the HTTP boundary,
so the real parser, the real cache and the real MCP facade run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pytest
from fastmcp import Client

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.mcp import telemetry
from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.services.autopvs1_service import AutoPVS1Service

SCHEMA_PATH = Path(__file__).with_name("envelope-v1.2.schema.json")
SCHEMA_SHA256 = "c3c47e20d7dd189aac2568fc963b5514d7a5ac2c3e5f21d126f42c96d1ad1ae3"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PAGES = {
    "/variant/": "variant_hg38_X-83508928-A-T.html",
    "/cnv/": "cnv_hg19_MYO15A_17-15000000-20000000-DEL.html",
    "/search": "search_MYH9.html",
}

VARIANT = {"genome_build": "hg38", "variant_id": "X-83508928-A-T"}
CNV = {"genome_build": "hg19", "cnv_id": "17-15000000-20000000-DEL"}
# Every data tool; get_server_health and get_server_capabilities are ops/meta tools.
DATA_CALLS: list[tuple[str, dict[str, Any]]] = [
    *[
        ("get_variant_pvs1_data", {**VARIANT, "response_mode": m})
        for m in ("ids_only", "summary", "standard", "full")
    ],
    ("get_variant_pvs1_data", {**VARIANT, "meta_mode": "minimal"}),
    ("get_cnv_pvs1_data", CNV),
    ("search_variants", {"query": "MYH9"}),
    ("get_variants_pvs1_data_bulk", {"items": [VARIANT]}),
    ("get_cnvs_pvs1_data_bulk", {"items": [CNV]}),
    # No item reaches the upstream: still a success envelope, still dated.
    ("get_variants_pvs1_data_bulk", {"items": [{"genome_build": "hg38", "variant_id": "bad"}]}),
]
OTHER_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("get_variant_pvs1_data", {"genome_build": "hg38", "variant_id": "not a variant"}),
    ("get_variant_pvs1_data", {"wrong_argument": 1}),
    ("no_such_tool", {}),
]
OPS_TOOLS = {"get_server_health", "get_server_capabilities"}


@pytest.fixture
def mcp(monkeypatch: pytest.MonkeyPatch) -> Any:
    async def recorded(_client: Any, _policy: Any, _method: str, url: str, **_: Any) -> Any:
        page = next(name for part, name in PAGES.items() if part in url)
        return httpx.Response(
            200, text=(FIXTURES / page).read_text("utf-8"), request=httpx.Request("GET", url)
        )

    monkeypatch.setattr("autopvs1_link.api.autopvs1_client.guarded_request", recorded)
    service = AutoPVS1Service(AutoPVS1Client())

    async def _service() -> AutoPVS1Service:
        return service

    monkeypatch.setattr("autopvs1_link.mcp.service_adapters._service", _service)
    for method in ("get_variant_data", "get_cnv_data", "search_variants"):
        getattr(AutoPVS1Service, method).cache_clear()
    return build_mcp_server()


async def _call(mcp: Any, tool: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    return result.structured_content, result.is_error


def test_vendored_schema_is_the_v1_2_0_release() -> None:
    assert hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest() == SCHEMA_SHA256


async def test_data_calls_cover_the_registered_data_tools(mcp: Any) -> None:
    registered = {tool.name for tool in await mcp.list_tools()}
    assert {name for name, _ in DATA_CALLS} == registered - OPS_TOOLS


@pytest.mark.parametrize(("tool", "arguments"), DATA_CALLS)
async def test_success_validates_and_carries_provenance(
    mcp: Any, tool: str, arguments: dict[str, Any]
) -> None:
    envelope, is_error = await _call(mcp, tool, arguments)
    assert envelope["success"] is True and is_error is False
    jsonschema.validate(envelope, SCHEMA)
    meta = envelope["_meta"]
    assert meta["source"] == "autopvs1"
    assert meta["data_version"] == "live"
    assert meta["retrieved_at"].endswith("Z")


@pytest.mark.parametrize(
    ("tool", "arguments"), [*OTHER_CALLS, *((t, {}) for t in sorted(OPS_TOOLS))]
)
async def test_errors_and_ops_tools_carry_the_v1_meta_core(
    mcp: Any, tool: str, arguments: dict[str, Any]
) -> None:
    envelope, is_error = await _call(mcp, tool, arguments)
    assert is_error == (not envelope["success"])
    assert isinstance(envelope["_meta"]["request_id"], str)
    assert isinstance(envelope["_meta"]["elapsed_ms"], int | float)
    if not envelope["success"]:
        jsonschema.validate(envelope, SCHEMA)


async def test_cache_hit_keeps_the_original_fetch_time(
    mcp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = iter(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"])
    monkeypatch.setattr("autopvs1_link.utils.cache_manager.utc_now", lambda: next(clock))
    first, _ = await _call(mcp, "get_variant_pvs1_data", VARIANT)
    hit, _ = await _call(mcp, "get_variant_pvs1_data", VARIANT)
    other, _ = await _call(mcp, "get_cnv_pvs1_data", CNV)
    assert first["_meta"]["cache_status"] == "miss"
    assert hit["_meta"]["cache_status"] == "hit"
    assert first["_meta"]["retrieved_at"] == hit["_meta"]["retrieved_at"] == "2026-01-01T00:00:00Z"
    # A later call does not inherit an earlier call's (older) fetch time.
    assert other["_meta"]["retrieved_at"] == "2026-01-02T00:00:00Z"


def test_several_upstream_fetches_report_the_oldest() -> None:
    telemetry.mark_call_started()
    telemetry.record_upstream_call(1.0, "hit", "2026-01-02T00:00:00Z")
    telemetry.record_upstream_call(1.0, "miss", "2026-01-01T00:00:00Z")
    telemetry.record_upstream_call(1.0, "miss", "2026-01-03T00:00:00Z")
    assert telemetry.get_retrieved_at() == "2026-01-01T00:00:00Z"
