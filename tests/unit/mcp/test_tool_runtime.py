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
        supported_values="summary, standard, or full",
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
        supported_values="summary, standard, or full",
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
async def test_search_numeric_cursor_returns_invalid_search_query_envelope(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "MYH9", "cursor": 5})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_query"
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
