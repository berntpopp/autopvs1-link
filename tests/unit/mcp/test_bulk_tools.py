"""Exercise bulk MCP tools through FastMCP's call_tool runtime."""

from unittest.mock import AsyncMock

import httpx
import pytest

from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    CNVInfo,
    DiseaseMechanism,
    PVS1Flowchart,
    VariantInfo,
)


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://autopvs1.example.test/variant")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("upstream", request=request, response=response)


def _variant_fixture(variant_id: str, gene: str = "GENE") -> AutoPVS1Data:
    return AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id=variant_id,
            variant_type="Nonsense",
            gene_symbol=gene,
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )


def _cnv_fixture(cnv_id: str) -> AutoPVS1CNVData:
    return AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id=cnv_id,
            cnv_type="Deletion",
            gene_symbol="GENE",
            coordinates=cnv_id,
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
async def test_bulk_variants_happy_path(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(side_effect=[_variant_fixture("X-1-A-T"), _variant_fixture("X-2-G-A")]),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
            ]
        },
    )
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["data"]["total"] == 2
    assert payload["data"]["attempted"] == 2
    assert payload["data"]["skipped"] == 0
    assert payload["data"]["succeeded"] == 2
    assert payload["data"]["failed"] == 0
    items = payload["data"]["items"]
    assert all(item["ok"] for item in items)
    assert [item["input"]["variant_id"] for item in items] == ["X-1-A-T", "X-2-G-A"]
    assert items[0]["data"]["pvs1_flowchart"]["final_strength"] == "Strong"
    assert all(item["error"] is None for item in items)


@pytest.mark.asyncio
async def test_bulk_variants_mixed_per_item_errors(mocker) -> None:
    timeout = httpx.TimeoutException("boom")
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(side_effect=[_variant_fixture("X-1-A-T"), timeout]),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
            ]
        },
    )
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["data"]["succeeded"] == 1
    assert payload["data"]["failed"] == 1
    first, second = payload["data"]["items"]
    assert first["ok"] is True and first["error"] is None
    assert second["ok"] is False
    assert second["error"]["code"] == "upstream_timeout"
    assert second["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_bulk_variants_continue_on_error_false_stops_early(mocker) -> None:
    timeout = httpx.TimeoutException("boom")
    fake = AsyncMock(side_effect=[timeout, _variant_fixture("X-2-G-A")])
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
            ],
            "continue_on_error": False,
        },
    )
    payload = result.structured_content
    assert payload["data"]["total"] == 2
    assert payload["data"]["attempted"] == 1
    assert payload["data"]["skipped"] == 1
    assert payload["data"]["succeeded"] == 0
    assert payload["data"]["failed"] == 1
    assert fake.await_count == 1


@pytest.mark.asyncio
async def test_bulk_variants_rejects_too_many_items() -> None:
    items = [{"genome_build": "hg19", "variant_id": "X-1-A-T"}] * 11
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {"items": items},
    )
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_bulk_input"
    assert "10" in payload["error"]["message"]


@pytest.mark.asyncio
async def test_bulk_variants_rejects_empty_list() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {"items": []},
    )
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_bulk_input"


@pytest.mark.asyncio
async def test_bulk_variants_per_item_input_validation_yields_per_item_error(mocker) -> None:
    fake = AsyncMock(return_value=_variant_fixture("X-2-G-A"))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "not_a_variant"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
            ]
        },
    )
    payload = result.structured_content
    first, second = payload["data"]["items"]
    assert first["ok"] is False
    assert first["error"]["code"] == "invalid_variant_id"
    assert second["ok"] is True
    fake.assert_awaited_once_with("hg19", "X-2-G-A")


@pytest.mark.asyncio
async def test_bulk_variants_propagates_response_and_meta_modes(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=_variant_fixture("X-1-A-T")),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [{"genome_build": "hg19", "variant_id": "X-1-A-T"}],
            "response_mode": "summary",
            "meta_mode": "minimal",
        },
    )
    payload = result.structured_content
    item_data = payload["data"]["items"][0]["data"]
    assert item_data["disease_mechanisms"] == []
    assert "recommended_citation" not in payload["meta"]


@pytest.mark.asyncio
async def test_bulk_cnvs_happy_path_with_size_int(mocker) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_cnv",
        new=AsyncMock(return_value=_cnv_fixture("11-2797090-2869333-DEL")),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnvs_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"},
            ]
        },
    )
    payload = result.structured_content
    assert payload["ok"] is True
    item = payload["data"]["items"][0]
    assert item["ok"] is True
    assert item["data"]["cnv_info"]["size"] == 72243
    assert item["data"]["cnv_info"]["cnv_type"] == "DEL"


@pytest.mark.asyncio
async def test_bulk_cnvs_rejects_too_many_items() -> None:
    items = [{"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"}] * 11
    mcp = build_mcp_server()
    result = await mcp.call_tool("get_cnvs_pvs1_data_bulk", {"items": items})
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_bulk_input"


@pytest.mark.asyncio
async def test_bulk_variants_rejects_non_list_items() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool("get_variants_pvs1_data_bulk", {"items": "not_a_list"})
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_bulk_input"


@pytest.mark.asyncio
async def test_bulk_variants_rejects_non_object_item() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {"items": [{"genome_build": "hg19", "variant_id": "X-1-A-T"}, "garbage"]},
    )
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_bulk_input"


@pytest.mark.asyncio
async def test_bulk_variants_per_item_invalid_genome_build_yields_per_item_error(mocker) -> None:
    fake = AsyncMock(return_value=_variant_fixture("X-2-G-A"))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg99", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
            ]
        },
    )
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["data"]["succeeded"] == 1
    assert payload["data"]["failed"] == 1
    first, second = payload["data"]["items"]
    assert first["ok"] is False
    assert first["error"]["code"] == "invalid_genome_build"
    assert second["ok"] is True
    fake.assert_awaited_once_with("hg19", "X-2-G-A")


@pytest.mark.parametrize(
    ("exc", "expected_code", "expected_retryable"),
    [
        (_http_status_error(404), "not_found", False),
        (_http_status_error(500), "upstream_unavailable", True),
        (_http_status_error(429), "upstream_unavailable", True),
        (httpx.ConnectError("boom"), "upstream_unavailable", True),
        (ValueError("parse fail"), "parse_error", False),
    ],
)
@pytest.mark.asyncio
async def test_bulk_variants_maps_upstream_errors_per_item(
    mocker, exc, expected_code, expected_retryable
) -> None:
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(side_effect=exc),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {"items": [{"genome_build": "hg19", "variant_id": "X-1-A-T"}]},
    )
    payload = result.structured_content
    item = payload["data"]["items"][0]
    assert item["ok"] is False
    assert item["error"]["code"] == expected_code
    assert item["error"]["retryable"] is expected_retryable


@pytest.mark.asyncio
async def test_bulk_variants_propagates_include_unmet_false(mocker) -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
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
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Met disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            ),
            DiseaseMechanism(
                gene="GENE",
                disease="Unmet disease",
                inheritance="AD",
                clinical_validity="Limited",
                consideration="Not applicable",
                adjusted_strength="Unmet",
            ),
        ],
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [{"genome_build": "hg19", "variant_id": "X-1-A-T"}],
            "include_unmet": False,
        },
    )
    rows = result.structured_content["data"]["items"][0]["data"]["disease_mechanisms"]
    assert [row["adjusted_strength"] for row in rows] == ["Strong"]


@pytest.mark.asyncio
async def test_bulk_variants_invalid_response_mode_returns_top_level_error() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [{"genome_build": "hg19", "variant_id": "X-1-A-T"}],
            "response_mode": "terse",
        },
    )
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_response_mode"


@pytest.mark.asyncio
async def test_bulk_per_item_error_details_absent_when_null(mocker) -> None:
    """Per-item errors must match single-tool envelope: details absent (not null) when no details exist."""
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {"items": [{"genome_build": "hg19", "variant_id": "not_a_variant"}]},
    )
    payload = result.structured_content
    error_obj = payload["data"]["items"][0]["error"]
    assert error_obj is not None
    assert "details" not in error_obj


@pytest.mark.asyncio
async def test_bulk_variants_dedupes_warnings_by_code(mocker) -> None:
    """Aggregated warnings collapse repeats by code so 10-item batches stay scannable."""
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            external_links={"gnomAD": "https://example.test/variant"},
            invalid_external_links={"ClinVar": "https://bad/"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(side_effect=[parsed, parsed, parsed]),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
                {"genome_build": "hg19", "variant_id": "X-3-T-C"},
            ]
        },
    )
    codes = [w["code"] for w in result.structured_content["meta"]["warnings"]]
    # Three items each emit invalid_external_link — aggregated must collapse to one.
    assert codes.count("invalid_external_link") == 1


@pytest.mark.asyncio
async def test_bulk_aggregated_warning_carries_count_and_affected_indices(mocker) -> None:
    """3 items each emit invalid_external_link → 1 aggregated warning
    with count=3 and affected_indices=[0,1,2]."""
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            external_links={"gnomAD": "https://example.test/variant"},
            invalid_external_links={"ClinVar": "https://bad/"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(side_effect=[parsed, parsed, parsed]),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variants_pvs1_data_bulk",
        {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-1-A-T"},
                {"genome_build": "hg19", "variant_id": "X-2-G-A"},
                {"genome_build": "hg19", "variant_id": "X-3-T-C"},
            ]
        },
    )
    warnings = [
        w
        for w in result.structured_content["meta"]["warnings"]
        if w["code"] == "invalid_external_link"
    ]
    assert len(warnings) == 1
    aggregated = warnings[0]
    assert aggregated["count"] == 3
    assert aggregated["affected_indices"] == [0, 1, 2]


@pytest.mark.asyncio
async def test_single_tool_warning_omits_aggregate_fields(mocker) -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            external_links={"gnomAD": "https://example.test/variant"},
            invalid_external_links={"ClinVar": "https://bad/"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-1-A-T"},
    )
    warnings = result.structured_content["meta"]["warnings"]
    assert warnings, "expected at least one warning"
    for w in warnings:
        assert "count" not in w
        assert "affected_indices" not in w


@pytest.mark.asyncio
async def test_bulk_cnvs_invalid_mode_returns_top_level_error() -> None:
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnvs_pvs1_data_bulk",
        {
            "items": [{"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"}],
            "meta_mode": "verbose",
        },
    )
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_meta_mode"
