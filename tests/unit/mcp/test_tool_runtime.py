"""Exercise MCP tool wrappers through FastMCP's call_tool runtime."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from autopvs1_link.api.variant_recoder import (
    RecoderCandidate,
    RecoderNotFoundError,
    RecoderUnavailableError,
)
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


def _recoder_candidate(
    variant_id: str = "17-43057065-G-GG",
    allele_key: str = "G",
    spdi: str = "NC_000017.11:43057065::G",
    synonyms: tuple[str, ...] = ("rs80357906",),
) -> RecoderCandidate:
    return RecoderCandidate(
        variant_id=variant_id,
        allele_key=allele_key,
        spdi=spdi,
        synonym_ids=synonyms,
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
    assert payload["success"] is False
    assert "result" not in payload
    assert "results" not in payload
    assert payload["error_code"] == code
    assert payload["retryable"] is False
    assert parameter in payload["message"]
    assert supported_values in payload["message"]
    assert payload["suggestions"]


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
    assert result.structured_content["success"] is True
    assert result.structured_content["result"]["upstream_service"] == "AutoPVS1"


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
    assert result.structured_content["success"] is True
    assert result.structured_content["result"]["upstream_service"] == "AutoPVS1"


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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_variant_id"
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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_variant_id"
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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_cnv_id"
    assert result.structured_content["suggestions"] == ["Use 17-15000000-20000000-DEL."]
    assert result.structured_content["details"] == {"corrected_id": "17-15000000-20000000-DEL"}


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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_cnv_id"
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
    assert result.structured_content["success"] is True
    assert result.structured_content["result"]["cnv_info"]["gene_symbol"] == "MYO15A"


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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True
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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True
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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True


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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_search_query"


@pytest.mark.asyncio
async def test_search_default_build_warns_that_hg38_was_assumed(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["success"] is True
    assert result.structured_content["_meta"]["warnings"][0]["code"] == "default_genome_build"


@pytest.mark.asyncio
async def test_search_empty_query_returns_invalid_search_query_without_raw_validation(
    mocker,
) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": ""})

    fake.assert_not_awaited()
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_search_query"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_no_result_hgvs_like_query_returns_guidance(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="BRCA1 c.5266dupC", genome_version="hg38", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {
            "query": " BRCA1 c.5266dupC ",
            "genome_build": "hg38",
            # ids_only (post-v1.1.0 default) drops data.suggestions; this
            # test exercises the no-result guidance surface, so pin a
            # mode that retains it.
            "response_mode": "standard",
        },
    )

    fake.assert_awaited_once_with("BRCA1 c.5266dupC", "hg38")
    assert result.structured_content["success"] is True
    assert result.structured_content["total_count"] == 0
    assert result.structured_content["suggestions"] == [
        "Search for BRCA1 only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert result.structured_content["_meta"]["warnings"][0]["code"] == (
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
    assert result.structured_content["success"] is True
    assert result.structured_content["_meta"]["warnings"][0]["code"] == "deprecated_genome_version"


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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_genome_build"


@pytest.mark.asyncio
async def test_search_numeric_genome_build_returns_invalid_genome_build_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": 5})

    fake.assert_not_awaited()
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_genome_build"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_numeric_genome_version_returns_invalid_genome_build_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_version": 5})

    fake.assert_not_awaited()
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_genome_build"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_non_integer_limit_returns_invalid_search_query_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": "abc"})

    fake.assert_not_awaited()
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_search_query"
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
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_genome_build"


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
    assert result.structured_content["success"] is True


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
    variant_info = result.structured_content["result"]["variant_info"]
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
    data = result.structured_content["result"]
    variant_info = data["variant_info"]
    # variant_info on the wire is strictly the identifier — null leaks fail.
    assert set(variant_info) == {"variant_id"}, variant_info
    # pvs1_flowchart absent on the wire (not present-with-null).
    assert "pvs1_flowchart" not in data, data


@pytest.mark.asyncio
async def test_cnv_ids_only_wire_payload_strips_null_fields(mocker) -> None:
    """End-to-end mirror of the variant ids_only test for the CNV detail
    tool. Surfaced by the 9.65 review as a coverage gap: the CNV
    presenter ids_only branch was tested directly but no test confirmed
    the wire payload through call_tool actually compacts via
    compact_data=True on the cnv_tool envelope path.
    """
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_cnv",
        new=AsyncMock(return_value=_cnv_result()),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {
            "genome_build": "hg19",
            "cnv_id": "1-1-2-DEL",
            "response_mode": "ids_only",
        },
    )
    data = result.structured_content["result"]
    cnv_info = data["cnv_info"]
    # cnv_info on the wire is strictly the identifier — null leaks fail.
    assert set(cnv_info) == {"cnv_id"}, cnv_info
    assert cnv_info["cnv_id"] == "1-1-2-DEL"
    # pvs1_flowchart absent on the wire (not present-with-null).
    assert "pvs1_flowchart" not in data, data


@pytest.mark.asyncio
async def test_search_ids_only_wire_payload_strips_descriptive_fields(mocker) -> None:
    """End-to-end mirror for search: ids_only must reach the wire as rows
    of strictly {variant_id, url} with suggestions omitted. Closes the
    9.65 review coverage gap that the search presenter ids_only branch
    was tested at presenter level but not at call_tool level.
    """
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(
            query="BRCA1",
            genome_version="hg38",
            results=[
                SearchResult(
                    variant_id=f"17-{i}-A-T",
                    gene="BRCA1",
                    variant_type="Nonsense",
                    genome_build="hg38",
                    url=f"https://autopvs1.bgi.com/variant/hg38/17-{i}-A-T",
                )
                for i in range(3)
            ],
        )
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "BRCA1", "genome_build": "hg38", "response_mode": "ids_only"},
    )
    data = result.structured_content
    assert data["returned_count"] == 3
    for row in data["results"]:
        assert set(row) == {"variant_id", "url"}, row
        assert row["variant_id"].startswith("17-")
        assert row["url"].startswith("https://autopvs1.bgi.com/variant/")
    # suggestions empty (drops to default-factory []) — must not echo
    # HGVS-like guidance at the ids_only tier.
    assert data.get("suggestions", []) == []


@pytest.mark.asyncio
async def test_every_tool_wire_payload_validates_against_published_schema(mocker) -> None:
    """Meta-test: compacted structured_content must satisfy the tool's output_schema.

    The MCP client validates ``structuredContent`` against the schema the
    server publishes via ``tools/list``. Stripping null fields from the
    wire (``exclude_none=True``) is safe only when the schema marks those
    fields non-required. This test catches the seam where a Pydantic
    field declared ``str | None`` (no default → required → schema marks
    required) is stripped on the wire and the client rejects.

    Regression for ``search_variants`` page 1 throwing
    ``Output validation error: 'previous_cursor' is a required property``.
    """
    import jsonschema

    # Mock all upstream service adapters so the test is fast + deterministic.
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_result()),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_cnv",
        new=AsyncMock(return_value=_cnv_result()),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.search_variants",
        new=AsyncMock(
            return_value=AutoPVS1SearchResults(
                query="MYH9",
                genome_version="hg38",
                results=[
                    SearchResult(
                        variant_id=f"22-{i}-A-T",
                        gene="MYH9",
                        variant_type="Nonsense",
                        genome_build="hg38",
                        url=f"https://autopvs1.bgi.com/variant/hg38/22-{i}-A-T",
                    )
                    for i in range(3)
                ],
            )
        ),
    )

    mcp = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    cases = [
        ("get_variant_pvs1_data", {"genome_build": "hg19", "variant_id": "X-1-A-T"}),
        ("get_cnv_pvs1_data", {"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"}),
        # search page 1: previous_cursor is null here — this is the regression.
        ("search_variants", {"query": "MYH9", "genome_build": "hg38"}),
        ("get_server_capabilities", {}),
    ]
    for tool_name, args in cases:
        result = await mcp.call_tool(tool_name, args)
        structured = result.structured_content
        schema = tools[tool_name].output_schema
        try:
            jsonschema.validate(instance=structured, schema=schema)
        except jsonschema.ValidationError as exc:
            raise AssertionError(
                f"tool {tool_name!r} produced wire payload that fails its own "
                f"output_schema: {exc.message} at path {list(exc.absolute_path)}"
            ) from exc


@pytest.mark.asyncio
async def test_variant_standard_mode_drops_null_default_fields_from_wire(mocker) -> None:
    """Standard-mode wire payload must drop null-default fields for tokens.

    Regression for an LLM-consumer report that ``standard`` mode shipped
    ``chgvs: null``, ``phgvs: null``, ``decision_tree_raw: null``, etc.
    The contract still declares the optional fields; the wire just omits
    null leaves so first-turn LLM calls do not waste budget.

    Explicit ``response_mode='standard'`` keeps the test's intent stable
    after the v1.1.0 default flipped to ``summary``.
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
            "response_mode": "standard",
        },
    )
    data = result.structured_content["result"]
    variant_info = data["variant_info"]
    # Fixture variant has no chgvs/phgvs/exon/intron → must NOT be on the wire.
    assert "chgvs" not in variant_info
    assert "phgvs" not in variant_info
    # The audit-trail raw fields are absent in standard mode too.
    assert "external_links_raw" not in variant_info
    assert "decision_tree_raw" not in data["pvs1_flowchart"]


@pytest.mark.asyncio
async def test_variant_auto_resolves_rsid_via_recoder_with_warning(mocker) -> None:
    """rsID input is resolved via Ensembl Variant Recoder, then scored.

    LLM-consumer reclaim (pass-3, 8.4/10 → 10/10 push): the previous
    AutoPVS1-search-based resolver returned ``not_found`` for rsIDs
    because AutoPVS1's search index does not include dbSNP rsIDs. The
    new resolver delegates to Ensembl's Variant Recoder REST API, which
    is the authoritative public mapping from rsID/HGVS to canonical
    SPDI. The resolved id is then sent to AutoPVS1 for PVS1 scoring,
    and an ``auto_resolved`` warning carries the audit trail (input,
    resolved id, resolver source, allele key).
    """
    recoder_fake = AsyncMock(return_value=[_recoder_candidate()])
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "rs80357906"},
    )
    payload = result.structured_content
    assert payload["success"] is True, payload
    by_code = {w["code"]: w for w in payload["_meta"]["warnings"]}
    assert "auto_resolved" in by_code
    assert "ensembl variant recoder" in by_code["auto_resolved"]["message"].lower()
    # Score call uses the resolved canonical id, not the raw rsID.
    score_fake.assert_awaited_once_with("hg38", "17-43057065-G-GG")
    # Recoder is build-scoped to caller's genome_build (build-drift mitigation).
    recoder_fake.assert_awaited_once_with("rs80357906", "hg38")


@pytest.mark.asyncio
async def test_variant_auto_resolves_hgvs_c_via_recoder_with_warning(mocker) -> None:
    """HGVS-c input is resolved via the recoder just like rsID.

    The previous implementation tried AutoPVS1's search box with an
    HGVS string and got 0 hits more often than not. Ensembl's recoder
    handles HGVS-c/p/g uniformly so the resolver path is unified.
    """
    recoder_fake = AsyncMock(
        return_value=[
            _recoder_candidate(
                variant_id="17-43057063-G-GG",
                allele_key="G",
                spdi="NC_000017.11:43057063::G",
                synonyms=(),
            )
        ]
    )
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "NM_007294.4:c.5266dup"},
    )
    payload = result.structured_content
    assert payload["success"] is True, payload
    codes = [w["code"] for w in payload["_meta"]["warnings"]]
    assert "auto_resolved" in codes
    score_fake.assert_awaited_once_with("hg38", "17-43057063-G-GG")
    recoder_fake.assert_awaited_once_with("NM_007294.4:c.5266dup", "hg38")


@pytest.mark.asyncio
async def test_variant_recoder_multi_allele_returns_requires_disambiguation(
    mocker,
) -> None:
    """Multi-allelic recoder response MUST surface as ``requires_disambiguation``.

    Mitigates the silent-multi-allelic mis-scoring failure mode (VEP #989):
    never collapse to "best guess" by ALT-allele frequency. The recoder
    returns one candidate per ALT key under one array element; we surface
    them all and force the caller to pick.
    """
    candidates = [
        _recoder_candidate(
            variant_id="9-133256042-C-T",
            allele_key="T",
            spdi="NC_000009.12:133256041:C:T",
            synonyms=("rs56116432",),
        ),
        _recoder_candidate(
            variant_id="9-133256042-C-A",
            allele_key="A",
            spdi="NC_000009.12:133256041:C:A",
            synonyms=("rs56116432",),
        ),
    ]
    recoder_fake = AsyncMock(return_value=candidates)
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "rs56116432"},
    )
    payload = result.structured_content
    assert payload["success"] is False
    assert payload["error_code"] == "requires_disambiguation"
    candidates_payload = payload["details"]["candidates"]
    assert {c["id"] for c in candidates_payload} == {
        "9-133256042-C-T",
        "9-133256042-C-A",
    }
    # Disambiguators must include allele_key + resource_uri (LLM-actionable).
    assert all("allele_key" in c and "resource_uri" in c for c in candidates_payload)
    # No score call — disambiguation must NOT silently best-guess.
    score_fake.assert_not_awaited()


@pytest.mark.asyncio
async def test_variant_recoder_not_found_returns_not_found(mocker) -> None:
    """Ensembl 400 'not found' is mapped to ``error.code='not_found'``.

    The suggestion points the caller at confirming the rsID/HGVS exists
    or supplying a canonical CHROM-POS-REF-ALT, so the LLM has a
    concrete remediation path without guessing at a different tool.
    """
    recoder_fake = AsyncMock(
        side_effect=RecoderNotFoundError("No variant found with ID 'rs99999999999'")
    )
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "rs99999999999"},
    )
    payload = result.structured_content
    assert payload["success"] is False
    assert payload["error_code"] == "not_found"
    assert "canonical CHROM-POS-REF-ALT" in " ".join(payload["suggestions"])
    score_fake.assert_not_awaited()


@pytest.mark.asyncio
async def test_variant_recoder_unavailable_returns_external_resolver_unavailable(
    mocker,
) -> None:
    """Recoder timeout/5xx maps to ``external_resolver_unavailable`` (retryable).

    Distinguishes a permanent 'not found' from a transient upstream
    failure so an LLM caller can decide whether to retry vs. ask the
    user for a different identifier.
    """
    recoder_fake = AsyncMock(
        side_effect=RecoderUnavailableError(
            "Variant Recoder timed out resolving 'rs80357906' on hg38"
        )
    )
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "rs80357906"},
    )
    payload = result.structured_content
    assert payload["success"] is False
    assert payload["error_code"] == "external_resolver_unavailable"
    assert payload["retryable"] is True
    score_fake.assert_not_awaited()


@pytest.mark.asyncio
async def test_variant_canonical_id_does_not_call_recoder(mocker) -> None:
    """Canonical input must NOT trigger an extra recoder call.

    Mitigates the hidden-cost-spike failure mode: only non-canonical
    forms pay the extra upstream hop.
    """
    recoder_fake = AsyncMock(return_value=[_recoder_candidate()])
    score_fake = AsyncMock(return_value=_variant_result())
    mocker.patch("autopvs1_link.mcp.service_adapters.recode_variant", new=recoder_fake)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=score_fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "X-82763936-A-T"},
    )
    payload = result.structured_content
    assert payload["success"] is True
    score_fake.assert_awaited_once_with("hg38", "X-82763936-A-T")
    recoder_fake.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_clamped_limit_emits_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 999})
    codes = [w["code"] for w in result.structured_content["_meta"]["warnings"]]
    assert "limit_clamped" in codes


@pytest.mark.asyncio
async def test_search_clamped_zero_limit_emits_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 0})
    codes = [w["code"] for w in result.structured_content["_meta"]["warnings"]]
    assert "limit_clamped" in codes


@pytest.mark.asyncio
async def test_search_unclamped_limit_no_warning(mocker) -> None:
    fake = AsyncMock(
        return_value=AutoPVS1SearchResults(query="MYH9", genome_version="hg38", results=[])
    )
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "limit": 25})
    codes = [w["code"] for w in result.structured_content["_meta"]["warnings"]]
    assert "limit_clamped" not in codes


@pytest.mark.asyncio
async def test_search_numeric_cursor_returns_invalid_search_cursor_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "cursor": 5})

    fake.assert_not_awaited()
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "invalid_search_cursor"
    _assert_no_raw_error_leak(result.content[0].text)


@pytest.mark.asyncio
async def test_search_timeout_returns_upstream_timeout_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/search")
    fake = AsyncMock(side_effect=httpx.TimeoutException("timed out", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_timeout"
    assert result.structured_content["retryable"] is True


@pytest.mark.asyncio
async def test_search_status_error_returns_upstream_unavailable_envelope(mocker) -> None:
    fake = AsyncMock(side_effect=_http_status_error(503, "https://autopvs1.bgi.com/search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True


@pytest.mark.asyncio
async def test_search_429_status_is_retryable_upstream_unavailable(mocker) -> None:
    fake = AsyncMock(side_effect=_http_status_error(429, "https://autopvs1.bgi.com/search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True


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
    data = result.structured_content["result"]
    meta = result.structured_content["_meta"]
    assert data["variant_info"]["variant_id"] == "X-1-A-T"
    assert data["pvs1_flowchart"]["final_strength_source"] == "inferred"
    assert data["disease_mechanisms"] == []
    assert {warning["code"] for warning in meta["warnings"]} == set()
    assert meta["unsafe_for_clinical_use"] is True
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
    data = result.structured_content["result"]
    meta = result.structured_content["_meta"]
    assert data["cnv_info"]["cnv_id"] == "1-1-2-DEL"
    assert data["pvs1_flowchart"]["final_strength_source"] == "asserted"
    assert data["disease_mechanisms"] == []
    assert meta["unsafe_for_clinical_use"] is True
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
    assert result.structured_content["total_count"] == 1
    assert result.structured_content["returned_count"] == 1
    assert result.structured_content["results"] == []
    assert result.structured_content["_meta"]["unsafe_for_clinical_use"] is True
    assert "recommended_citation" not in result.structured_content["_meta"]


@pytest.mark.asyncio
async def test_search_request_error_returns_upstream_unavailable_envelope(mocker) -> None:
    request = httpx.Request("GET", "https://autopvs1.bgi.com/search")
    fake = AsyncMock(side_effect=httpx.ConnectError("connect failed", request=request))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "genome_build": "hg38"})

    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result.structured_content["success"] is False
    assert result.structured_content["error_code"] == "upstream_unavailable"
    assert result.structured_content["retryable"] is True
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
    assert result.structured_content["success"] is True
    assert result.structured_content["result"]["status"] == "ok"
    assert result.structured_content["result"]["upstream_checked"] is False
    assert result.structured_content["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
async def test_get_server_health_check_upstream_true_probes_and_reports_reachable(
    mocker,
) -> None:
    """With ``check_upstream=true`` the tool issues one short HEAD probe.

    LLM-consumer reclaim: "upstream_checked is always false with no param
    to flip it — either add an opt-in check_upstream=true or drop the
    field." Opt-in (default False) keeps the no-cost contract for cheap
    callers; explicit True surfaces an honest reachability signal so an
    agent can decide whether to attempt a scoring call.
    """

    class _FakeResp:
        status_code = 200

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.aclose_called = False

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *args) -> None:
            self.aclose_called = True

        async def head(self, url: str, **kwargs) -> _FakeResp:
            self.requested_url = url
            return _FakeResp()

    mocker.patch("autopvs1_link.mcp.tools.health_tool.httpx.AsyncClient", _FakeClient)

    mcp = build_mcp_server()
    result = await mcp.call_tool("get_server_health", {"check_upstream": True})

    assert result.structured_content["success"] is True
    data = result.structured_content["result"]
    assert data["upstream_checked"] is True
    assert data["upstream_reachable"] is True
    assert data["upstream_status"] == "reachable"


@pytest.mark.asyncio
async def test_get_server_health_check_upstream_true_reports_unreachable_on_timeout(
    mocker,
) -> None:
    """Network failure during the probe surfaces as ``unreachable``, NOT an error.

    The health tool keeps its no-throw contract — an unreachable upstream
    is a reportable state, not a tool failure. LLM callers can branch on
    ``data.upstream_reachable`` without parsing exception text.
    """

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None: ...

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def head(self, url: str, **kwargs):
            raise httpx.TimeoutException("probe timed out")

    mocker.patch("autopvs1_link.mcp.tools.health_tool.httpx.AsyncClient", _FakeClient)

    mcp = build_mcp_server()
    result = await mcp.call_tool("get_server_health", {"check_upstream": True})

    assert result.structured_content["success"] is True
    data = result.structured_content["result"]
    assert data["upstream_checked"] is True
    assert data["upstream_reachable"] is False
    assert data["upstream_status"] == "unreachable"


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
    assert result.structured_content["success"] is True
    assert result.structured_content["result"] == {
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
    data_one = page_one.structured_content
    pagination_one = data_one["pagination"]
    # Pagination block carries the four populated fields with the right
    # types. ``previous_cursor`` is null on the first page; the wire drops
    # null fields so its presence on page 2 is the round-trip signal.
    assert isinstance(pagination_one["next_cursor"], str)
    assert "previous_cursor" not in pagination_one
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
    pagination_two = page_two.structured_content["pagination"]
    assert pagination_two["offset"] == 10
    assert pagination_two["has_more"] is True
    assert pagination_two["previous_cursor"] is not None


@pytest.mark.asyncio
async def test_variant_success_offers_widen_next_command(mocker) -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T", variant_type="SNV", gene_symbol="POU3F4"
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[
                FlowchartStep(code="Nonsense or Frameshift"),
                FlowchartStep(code="Strong"),
            ],
        ),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=mocker.AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T", "response_mode": "summary"},
    )
    cmds = result.structured_content["_meta"]["next_commands"]
    assert cmds[0]["tool"] == "get_variant_pvs1_data"
    assert cmds[0]["arguments"]["response_mode"] == "standard"


@pytest.mark.asyncio
async def test_default_meta_mode_is_compact_and_validates_against_contract(mocker) -> None:
    import jsonschema

    from autopvs1_link.models.autopvs1_models import (
        AutoPVS1Data,
        FlowchartStep,
        PVS1Flowchart,
        VariantInfo,
    )

    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T", variant_type="SNV", gene_symbol="POU3F4"
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[
                FlowchartStep(code="Nonsense or Frameshift"),
                FlowchartStep(code="Strong"),
            ],
        ),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=mocker.AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    # No meta_mode passed -> must default to compact (citation trimmed to doi+pmid).
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
    )
    citation = result.structured_content["_meta"]["recommended_citation"]
    assert set(citation.keys()) == {"doi", "pmid"}

    # Honor the MEMORY null-strip lesson: the default (compact) output still
    # validates against the published envelope contract after null-stripping.
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    jsonschema.validate(
        instance=result.structured_content,
        schema=tools["get_variant_pvs1_data"].output_schema,
    )
