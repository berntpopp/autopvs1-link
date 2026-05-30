"""Exercise MCP tool wrappers through FastMCP's call_tool runtime."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
    CNVInfo,
    DiseaseMechanism,
    FlowchartStep,
    PVS1Flowchart,
    SearchResult,
    VariantInfo,
)


class _FakeResult(BaseModel):
    """Minimal Pydantic model so tools take the model_dump branch."""

    ok: bool = True
    method: str = ""


def _assert_no_raw_error_leak(text: str) -> None:
    lowered = text.lower()
    assert "mdn" not in text
    assert "errors.pydantic.dev" not in lowered
    assert "string should have at least" not in lowered
    assert "<html" not in lowered
    assert "traceback" not in lowered


def _http_status_error(status_code: int, url: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", url)
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"AutoPVS1 returned HTTP {status_code}",
        request=request,
        response=response,
    )


def _assert_input_mode_error(
    payload: dict,
    *,
    code: str,
    parameter: str,
    supported_values: str,
) -> None:
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == code
    assert payload["error"]["retryable"] is False
    assert parameter in payload["error"]["message"]
    assert supported_values in payload["error"]["message"]
    assert payload["error"]["suggestions"]


def _variant_result() -> AutoPVS1Data:
    return AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )


def _cnv_result() -> AutoPVS1CNVData:
    return AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="1-1-2-DEL",
            cnv_type="Deletion",
            gene_symbol="GENE",
            coordinates="1-1-2-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )


@pytest.mark.asyncio
async def test_get_variant_pvs1_data_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-1-A-T"},
    )
    fake.assert_awaited_once_with("hg38", "X-1-A-T")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["upstream_service"] == "AutoPVS1"


@pytest.mark.asyncio
async def test_get_variant_invalid_response_mode_returns_envelope_without_calling_upstream(
    mocker,
) -> None:
    fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {
            "genome_build": "hg38",
            "variant_id": "X-1-A-T",
            "response_mode": "verbose",
        },
    )

    fake.assert_not_awaited()
    _assert_input_mode_error(
        result.structured_content,
        code="invalid_response_mode",
        parameter="response_mode",
        supported_values="ids_only, summary, standard, or full",
    )
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_variant_invalid_meta_mode_returns_envelope_without_calling_upstream(
    mocker,
) -> None:
    fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {
            "genome_build": "hg38",
            "variant_id": "X-1-A-T",
            "meta_mode": "tiny",
        },
    )

    fake.assert_not_awaited()
    _assert_input_mode_error(
        result.structured_content,
        code="invalid_meta_mode",
        parameter="meta_mode",
        supported_values="full, compact, or minimal",
    )
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_cnv_pvs1_data_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_cnv_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "1-1-2-DEL"},
    )
    fake.assert_awaited_once_with("hg19", "1-1-2-DEL")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["upstream_service"] == "AutoPVS1"


@pytest.mark.asyncio
async def test_search_invalid_response_mode_returns_envelope_without_calling_upstream(
    mocker,
) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="BRCA1", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {
            "query": "BRCA1",
            "genome_build": "hg38",
            "response_mode": "verbose",
        },
    )

    fake.assert_not_awaited()
    _assert_input_mode_error(
        result.structured_content,
        code="invalid_response_mode",
        parameter="response_mode",
        supported_values="ids_only, summary, standard, or full",
    )
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_invalid_meta_mode_returns_envelope_without_calling_upstream(
    mocker,
) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="BRCA1", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {
            "query": "BRCA1",
            "genome_build": "hg38",
            "meta_mode": "tiny",
        },
    )

    fake.assert_not_awaited()
    _assert_input_mode_error(
        result.structured_content,
        code="invalid_meta_mode",
        parameter="meta_mode",
        supported_values="full, compact, or minimal",
    )
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_variant_invalid_id_returns_envelope_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "NOT-A-VARIANT"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_variant_id"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_variant_empty_id_returns_envelope_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": ""},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_variant_id"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_cnv_colon_format_returns_guidance_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "chr17:15000000-20000000:DEL"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_cnv_id"
    assert result.structured_content["error"]["suggestions"] == ["Use 17-15000000-20000000-DEL."]
    assert result.structured_content["error"]["details"] == {
        "corrected_id": "17-15000000-20000000-DEL"
    }


@pytest.mark.asyncio
async def test_get_cnv_empty_id_returns_envelope_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": ""},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_cnv_id"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_get_cnv_hyphenated_format_forwards_upstream(mocker) -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="17-15000000-20000000-DEL",
            cnv_type="Deletion",
            gene_symbol="MYO15A",
            coordinates="17-15000000-20000000-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="VeryStrong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "17-15000000-20000000-DEL"},
    )

    fake.assert_awaited_once_with("hg19", "17-15000000-20000000-DEL")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["cnv_info"]["gene_symbol"] == "MYO15A"


@pytest.mark.asyncio
async def test_get_variant_connect_error_returns_upstream_unavailable_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/variant/hg38/X-1-A-T")
    fake = AsyncMock(side_effect=httpx.ConnectError("connect failed", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-1-A-T"},
    )

    fake.assert_awaited_once_with("hg38", "X-1-A-T")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True
    assert "connect failed" not in result.content[0].text


@pytest.mark.asyncio
async def test_get_cnv_connect_error_returns_upstream_unavailable_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/cnv/hg19/1-1-2-DEL")
    fake = AsyncMock(side_effect=httpx.ConnectError("connect failed", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "1-1-2-DEL"},
    )

    fake.assert_awaited_once_with("hg19", "1-1-2-DEL")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True
    assert "connect failed" not in result.content[0].text


@pytest.mark.asyncio
async def test_get_variant_429_status_is_retryable_upstream_unavailable(mocker) -> None:
    fake = AsyncMock(
        side_effect=_http_status_error(
            429,
            "https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        )
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-1-A-T"},
    )

    fake.assert_awaited_once_with("hg38", "X-1-A-T")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_search_variants_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_FakeResult(method="search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "MYH9", "genome_version": "hg38"},
    )
    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result is not None


@pytest.mark.asyncio
async def test_search_whitespace_returns_invalid_search_query(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "   "})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_query"


@pytest.mark.asyncio
async def test_search_default_build_warns_that_hg38_was_assumed(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["ok"] is True
    assert result.structured_content["meta"]["warnings"][0]["code"] == "default_genome_build"


@pytest.mark.asyncio
async def test_search_empty_query_returns_invalid_search_query_without_raw_validation(
    mocker,
) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": ""})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_query"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_no_result_hgvs_like_query_returns_guidance(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="BRCA1 c.5266dupC", genome_version="hg38", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": " BRCA1 c.5266dupC ", "genome_build": "hg38"},
    )

    fake.assert_awaited_once_with("BRCA1 c.5266dupC", "hg38")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["total_count"] == 0
    assert result.structured_content["data"]["suggestions"] == [
        "Search for BRCA1 only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert result.structured_content["meta"]["warnings"][0]["code"] == (
        "unsupported_hgvs_like_search"
    )


@pytest.mark.asyncio
async def test_search_deprecated_genome_version_alias_still_works(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="MYH9", genome_version="hg19", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "MYH9", "genome_version": "hg19"},
    )

    fake.assert_awaited_once_with("MYH9", "hg19")
    assert result.structured_content["ok"] is True
    assert result.structured_content["meta"]["warnings"][0]["code"] == "deprecated_genome_version"


@pytest.mark.asyncio
async def test_search_conflicting_genome_build_alias_returns_error(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "MYH9", "genome_build": "hg19", "genome_version": "hg38"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_genome_build"


@pytest.mark.asyncio
async def test_search_numeric_genome_build_returns_invalid_genome_build_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": 5})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_genome_build"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_numeric_genome_version_returns_invalid_genome_build_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_version": 5})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_genome_build"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_non_integer_limit_returns_invalid_search_query_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": "abc"})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_query"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_error_envelopes_set_is_error_true_on_wire(mocker) -> None:
    """Spec requirement (MCP 2025-06-18 / server/tools §Error Handling):

    Tool execution errors MUST set CallToolResult.isError=true so clients
    can distinguish failed calls without parsing the structured payload.
    """
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg99", "variant_id": "X-1-A-T"},
    )
    # The wire-level CallToolResult.isError is what spec-aware clients read.
    mcp_result = result.to_mcp_result()
    assert getattr(mcp_result, "isError", False) is True
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_genome_build"


@pytest.mark.asyncio
async def test_success_envelopes_remain_is_error_false(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_result()),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-1-A-T"},
    )
    # to_mcp_result returns either CallToolResult or a tuple for content-only;
    # for our successful envelope it's the (content, structured) tuple form
    # because we don't override the helper. Either way isError must not be true.
    mcp_result = result.to_mcp_result()
    is_error = getattr(mcp_result, "isError", False) if hasattr(mcp_result, "isError") else False
    assert is_error is False
    assert result.structured_content["ok"] is True


@pytest.mark.asyncio
async def test_variant_summary_mode_drops_null_default_fields(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_result()),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {
            "genome_build": "hg38",
            "variant_id": "X-1-A-T",
            "response_mode": "summary",
        },
    )
    variant_info = result.structured_content["data"]["variant_info"]
    # In summary mode, fields that default to None must NOT serialize.
    assert "chgvs" not in variant_info
    assert "phgvs" not in variant_info
    assert "pli_score" not in variant_info
    assert "gene_url" not in variant_info
    # Real values still present.
    assert variant_info["variant_id"] == "X-1-A-T"
    assert variant_info["gene_symbol"] == "GENE"


@pytest.mark.asyncio
async def test_variant_ids_only_wire_payload_strips_null_fields(mocker) -> None:
    """End-to-end check: response_mode='ids_only' must reach the wire as a
    truly minimal payload — variant_info contains only variant_id, and
    pvs1_flowchart/external_links/etc. are absent (not null). Without
    routing ids_only through compact_data on ok_envelope, the widened
    Optional fields serialize as nulls and blow up the payload size.
    """
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_result()),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {
            "genome_build": "hg38",
            "variant_id": "X-1-A-T",
            "response_mode": "ids_only",
        },
    )
    data = result.structured_content["data"]
    variant_info = data["variant_info"]
    # variant_info on the wire is strictly the identifier — null leaks fail.
    assert set(variant_info) == {"variant_id"}, variant_info
    # pvs1_flowchart absent on the wire (not present-with-null).
    assert "pvs1_flowchart" not in data, data


@pytest.mark.asyncio
async def test_variant_standard_mode_preserves_null_default_fields(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_result()),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-1-A-T"},
    )
    variant_info = result.structured_content["data"]["variant_info"]
    # In standard mode, the typed schema's null defaults stay visible.
    assert "chgvs" in variant_info and variant_info["chgvs"] is None


@pytest.mark.asyncio
async def test_search_clamped_limit_emits_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 999})
    codes = [w["code"] for w in result.structured_content["meta"]["warnings"]]
    assert "limit_clamped" in codes


@pytest.mark.asyncio
async def test_search_clamped_zero_limit_emits_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 0})
    codes = [w["code"] for w in result.structured_content["meta"]["warnings"]]
    assert "limit_clamped" in codes


@pytest.mark.asyncio
async def test_search_unclamped_limit_no_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 25})
    codes = [w["code"] for w in result.structured_content["meta"]["warnings"]]
    assert "limit_clamped" not in codes


@pytest.mark.asyncio
async def test_search_numeric_cursor_returns_invalid_search_cursor_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "cursor": 5})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_cursor"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_timeout_returns_upstream_timeout_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/search")
    fake = AsyncMock(side_effect=httpx.TimeoutException("timed out", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_timeout"
    assert result.structured_content["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_search_status_error_returns_upstream_unavailable_envelope(mocker) -> None:
    fake = AsyncMock(side_effect=_http_status_error(503, "https://autopvs1.bgi.com/search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_search_429_status_is_retryable_upstream_unavailable(mocker) -> None:
    fake = AsyncMock(side_effect=_http_status_error(429, "https://autopvs1.bgi.com/search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_get_variant_summary_response_and_compact_meta_mode(mocker) -> None:
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            chgvs="c.1A>T",
            external_links={"gnomAD": "https://example.test/variant"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            final_strength_inferred=True,
            decision_tree=[FlowchartStep(code="NF1", note_id="#1")],
            notes={"#1": "Resolved note text."},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            )
        ],
    )
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {
            "genome_build": "hg38",
            "variant_id": "X-1-A-T",
            "response_mode": "summary",
            "meta_mode": "compact",
        },
    )

    fake.assert_awaited_once_with("hg38", "X-1-A-T")
    data = result.structured_content["data"]
    meta = result.structured_content["meta"]
    assert data["variant_info"]["variant_id"] == "X-1-A-T"
    assert data["pvs1_flowchart"]["final_strength_source"] == "inferred"
    assert data["disease_mechanisms"] == []
    assert {warning["code"] for warning in meta["warnings"]} == set()
    assert meta["research_use_only"] is True
    assert meta["recommended_citation"] == {
        "doi": "10.1002/humu.24051",
        "pmid": "32442321",
    }


@pytest.mark.asyncio
async def test_get_cnv_summary_response_and_minimal_meta_mode(mocker) -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="1-1-2-DEL",
            cnv_type="Deletion",
            gene_symbol="GENE",
            coordinates="1-1-2-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            )
        ],
    )
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {
            "genome_build": "hg19",
            "cnv_id": "1-1-2-DEL",
            "response_mode": "summary",
            "meta_mode": "minimal",
        },
    )

    fake.assert_awaited_once_with("hg19", "1-1-2-DEL")
    data = result.structured_content["data"]
    meta = result.structured_content["meta"]
    assert data["cnv_info"]["cnv_id"] == "1-1-2-DEL"
    assert data["pvs1_flowchart"]["final_strength_source"] == "asserted"
    assert data["disease_mechanisms"] == []
    assert meta["research_use_only"] is True
    assert meta["warnings"] == []
    assert "request_id" in meta
    assert "server_version" in meta
    assert "recommended_citation" not in meta


@pytest.mark.asyncio
async def test_search_variants_summary_response_mode(mocker) -> None:
    parsed = AutoPVS1SearchResults(
        query="BRCA1",
        genome_version="hg38",
        results=[
            SearchResult(
                variant_id="17-1-A-T",
                gene="BRCA1",
                variant_type="Nonsense",
                genome_build="hg38",
                url="https://autopvs1.bgi.com/variant/hg38/17-1-A-T",
            )
        ],
    )
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {
            "query": "BRCA1",
            "genome_build": "hg38",
            "response_mode": "summary",
            "meta_mode": "minimal",
        },
    )

    fake.assert_awaited_once_with("BRCA1", "hg38")
    assert result.structured_content["data"]["total_count"] == 1
    assert result.structured_content["data"]["returned_count"] == 1
    assert result.structured_content["data"]["results"] == []
    assert result.structured_content["meta"]["research_use_only"] is True
    assert "recommended_citation" not in result.structured_content["meta"]


@pytest.mark.asyncio
async def test_search_request_error_returns_upstream_unavailable_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/search")
    fake = AsyncMock(side_effect=httpx.ConnectError("connect failed", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "upstream_unavailable"
    assert result.structured_content["error"]["retryable"] is True
    assert "connect failed" not in result.content[0].text


@pytest.mark.asyncio
async def test_get_server_capabilities_tool_runtime() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool("get_server_capabilities", {})
    assert result is not None


@pytest.mark.asyncio
async def test_get_server_health_is_local_read_only_and_does_not_call_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=fake,
    )

    mcp = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    health_tool = tools["get_server_health"]

    assert health_tool.annotations is not None
    assert health_tool.annotations.readOnlyHint is True
    assert health_tool.annotations.destructiveHint is False

    result = await mcp.call_tool("get_server_health", {})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["status"] == "ok"
    assert result.structured_content["data"]["upstream_checked"] is False
    assert result.structured_content["meta"]["research_use_only"] is True


@pytest.mark.asyncio
async def test_clear_cache_tool_runtime_when_enabled(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool("clear_cache", {})
    assert result is not None
    fake.clear_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_resource_runtime(mocker) -> None:
    fake = AsyncMock()
    fake.get_cache_statistics = AsyncMock(return_value={"hits": 5, "misses": 2})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.read_resource("autopvs1-link://cache/statistics")
    assert result is not None


@pytest.mark.asyncio
async def test_clear_cache_is_not_registered_by_default(monkeypatch, mocker) -> None:
    monkeypatch.delenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", raising=False)
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    tools = {tool.name for tool in await mcp.list_tools()}

    assert "clear_cache" not in tools
    fake.clear_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_cache_enabled_accepts_empty_input(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.call_tool("clear_cache", {})

    fake.clear_cache.assert_awaited_once()
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"] == {
        "cleared": True,
        "message": "All service caches and cache statistics cleared.",
    }


@pytest.mark.asyncio
async def test_cache_resource_returns_stable_method_keys(mocker) -> None:
    fake = AsyncMock()
    fake.get_cache_statistics = AsyncMock(return_value={})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.read_resource("autopvs1-link://cache/statistics")

    assert result is not None
    assert result.contents
    payload = json.loads(result.contents[0].content)
    assert set(payload["statistics"]) == {
        "get_variant_data",
        "get_cnv_data",
        "search_variants",
        "search_with_redirect_detection",
        "resolve_hgvs_notation",
    }


@pytest.mark.asyncio
async def test_search_variants_wire_returns_pagination_block_with_five_fields(mocker) -> None:
    """End-to-end: search_variants via mcp.call_tool returns a pagination
    block carrying all five SearchPaginationMCP fields with correct types.
    Round-trips the opaque next_cursor through a second call and asserts the
    decoded offset advances."""
    fake_results = AutoPVS1SearchResults(
        query="POU3F4",
        genome_version="hg38",
        results=[
            SearchResult(
                variant_id=f"X-{i}-A-T",
                gene="POU3F4",
                variant_type="Nonsense",
                genome_build="hg38",
                url=f"https://autopvs1.bgi.com/variant/hg38/X-{i}-A-T",
            )
            for i in range(25)
        ],
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.search_variants",
        new=AsyncMock(return_value=fake_results),
    )
    mcp = build_mcp_server()

    page_one = await mcp.call_tool(
        "search_variants",
        {"query": "POU3F4", "genome_build": "hg38", "limit": 10},
    )
    data_one = page_one.structured_content["data"]
    pagination_one = data_one["pagination"]
    # Pagination block carries all five fields with the right types.
    assert isinstance(pagination_one["next_cursor"], str)
    assert pagination_one["previous_cursor"] is None
    assert pagination_one["has_more"] is True
    assert pagination_one["offset"] == 0
    assert pagination_one["total_count_kind"] == "upstream_page"

    # Round-trip: passing the opaque next_cursor back yields page 2.
    page_two = await mcp.call_tool(
        "search_variants",
        {
            "query": "POU3F4",
            "genome_build": "hg38",
            "limit": 10,
            "cursor": pagination_one["next_cursor"],
        },
    )
    pagination_two = page_two.structured_content["data"]["pagination"]
    assert pagination_two["offset"] == 10
    assert pagination_two["has_more"] is True
    assert pagination_two["previous_cursor"] is not None
