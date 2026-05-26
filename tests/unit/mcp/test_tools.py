"""Smoke tests for MCP tool registration."""

import pytest
from fastmcp import FastMCP

from autopvs1_link.mcp.facade import build_mcp_server


def _schema_allows_null(schema: dict) -> bool:
    return schema.get("type") == "null" or any(
        branch.get("type") == "null" for branch in schema.get("anyOf", [])
    )


def _assert_optional_enum_is_coherent(schema: dict) -> None:
    assert _schema_allows_null(schema)
    if "enum" in schema:
        assert None in schema["enum"]


def _enum_values(schema: dict) -> set[str]:
    values = {value for value in schema.get("enum", []) if isinstance(value, str)}
    for branch in schema.get("anyOf", []):
        values.update(value for value in branch.get("enum", []) if isinstance(value, str))
    return values


def _assert_optional_genome_build_schema(schema: dict) -> None:
    _assert_optional_enum_is_coherent(schema)
    assert {"hg19", "hg38"} <= _enum_values(schema)


@pytest.mark.asyncio
async def test_build_mcp_server_registers_expected_tools() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert {
        "get_server_capabilities",
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
        "clear_cache",
    } <= tool_names


@pytest.mark.asyncio
async def test_data_tools_use_direct_arguments_for_llm_discovery() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    variant_schema = tools["get_variant_pvs1_data"].parameters
    assert set(variant_schema["properties"]) == {"genome_build", "variant_id"}
    assert variant_schema["required"] == ["genome_build", "variant_id"]

    search_schema = tools["search_variants"].parameters
    assert set(search_schema["properties"]) == {
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
    }
    assert search_schema["required"] == ["query"]
    assert "deprecated" in search_schema["properties"]["genome_version"]["description"].lower()
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_build"])
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_version"])
    assert _schema_allows_null(search_schema["properties"]["cursor"])


@pytest.mark.asyncio
async def test_data_tools_have_titles_annotations_and_output_schemas() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    for name in ("get_server_capabilities", "get_variant_pvs1_data", "get_cnv_pvs1_data"):
        tool = tools[name]
        assert tool.title
        assert tool.output_schema is not None
        assert set(tool.output_schema["properties"]) == {"ok", "data", "error", "meta"}
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True


@pytest.mark.asyncio
async def test_clear_cache_schema_accepts_empty_object_without_dummy_field() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    schema = tools["clear_cache"].parameters
    assert schema.get("properties", {}) == {}
    assert "_" not in schema.get("properties", {})
    assert set(tools["clear_cache"].output_schema["properties"]) == {"ok", "data", "error", "meta"}
