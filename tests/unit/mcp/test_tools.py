"""Smoke tests for MCP tool registration."""

import inspect
from typing import Any, get_args, get_type_hints

import pytest
from fastmcp import FastMCP

from autopvs1_link.mcp.facade import build_mcp_server

JsonSchema = dict[str, Any]


def _annotation_uses_any(annotation: Any) -> bool:
    if annotation is Any:
        return True
    return any(_annotation_uses_any(arg) for arg in get_args(annotation))


def _non_null_schema(schema: JsonSchema) -> JsonSchema:
    for branch in schema.get("anyOf", []):
        if branch.get("type") != "null":
            return branch
    return schema


def _resolve_ref(root: JsonSchema, schema: JsonSchema) -> JsonSchema:
    ref = schema.get("$ref")
    if ref is None:
        return schema

    assert isinstance(ref, str)
    assert ref.startswith("#/")
    resolved: Any = root
    for part in ref.removeprefix("#/").split("/"):
        resolved = resolved[part]
    assert isinstance(resolved, dict)
    return resolved


def _data_schema(output_schema: JsonSchema) -> JsonSchema:
    return _non_null_schema(output_schema["properties"]["data"])


def _property_schema(root: JsonSchema, schema: JsonSchema, property_name: str) -> JsonSchema:
    return _resolve_ref(root, schema["properties"][property_name])


def _assert_typed_object_schema(
    root: JsonSchema,
    schema: JsonSchema,
    expected_properties: set[str],
) -> JsonSchema:
    resolved = _resolve_ref(root, schema)
    assert "properties" in resolved
    assert expected_properties <= set(resolved["properties"])
    assert resolved.get("additionalProperties") is not True
    return resolved


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
    assert set(variant_schema["properties"]) == {
        "genome_build",
        "variant_id",
        "response_mode",
        "meta_mode",
        "include_unmet",
    }
    assert variant_schema["required"] == ["genome_build", "variant_id"]
    assert _enum_values(variant_schema["properties"]["response_mode"]) == {
        "summary",
        "standard",
        "full",
    }
    assert _enum_values(variant_schema["properties"]["meta_mode"]) == {
        "full",
        "compact",
        "minimal",
    }

    search_schema = tools["search_variants"].parameters
    assert set(search_schema["properties"]) == {
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
        "response_mode",
        "meta_mode",
    }
    assert search_schema["required"] == ["query"]
    assert "deprecated" in search_schema["properties"]["genome_version"]["description"].lower()
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_build"])
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_version"])
    assert _schema_allows_null(search_schema["properties"]["cursor"])
    assert _enum_values(search_schema["properties"]["response_mode"]) == {
        "summary",
        "standard",
        "full",
    }
    assert _enum_values(search_schema["properties"]["meta_mode"]) == {
        "full",
        "compact",
        "minimal",
    }


@pytest.mark.asyncio
async def test_search_variants_parameters_use_clean_runtime_annotations() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    signature = inspect.signature(tools["search_variants"].fn)
    type_hints = get_type_hints(tools["search_variants"].fn, include_extras=True)

    for name in (
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
        "response_mode",
        "meta_mode",
    ):
        assert name in signature.parameters
        assert not _annotation_uses_any(type_hints[name])


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
async def test_data_tool_output_schemas_expose_typed_nested_payloads() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    variant_schema = tools["get_variant_pvs1_data"].output_schema
    variant_data = _data_schema(variant_schema)
    variant_info = _property_schema(variant_schema, variant_data, "variant_info")
    _assert_typed_object_schema(
        variant_schema,
        variant_info,
        {"variant_id", "variant_type", "gene_symbol", "pli_score_display", "external_links"},
    )
    pvs1_flowchart = _property_schema(variant_schema, variant_data, "pvs1_flowchart")
    resolved_flowchart = _assert_typed_object_schema(
        variant_schema,
        pvs1_flowchart,
        {
            "preliminary_decision_path",
            "final_strength",
            "final_strength_source",
            "decision_tree",
            "notes",
        },
    )
    flowchart_step = _resolve_ref(
        variant_schema,
        resolved_flowchart["properties"]["decision_tree"]["items"],
    )
    _assert_typed_object_schema(
        variant_schema,
        flowchart_step,
        {"code", "description", "note_id", "note_text"},
    )
    disease_mechanism = _resolve_ref(
        variant_schema,
        variant_data["properties"]["disease_mechanisms"]["items"],
    )
    _assert_typed_object_schema(
        variant_schema,
        disease_mechanism,
        {"gene", "disease", "inheritance", "clinical_validity", "adjusted_strength"},
    )

    cnv_schema = tools["get_cnv_pvs1_data"].output_schema
    cnv_data = _data_schema(cnv_schema)
    cnv_info = _property_schema(cnv_schema, cnv_data, "cnv_info")
    _assert_typed_object_schema(
        cnv_schema,
        cnv_info,
        {"cnv_id", "cnv_type", "gene_symbol", "coordinates", "size"},
    )
    _assert_typed_object_schema(
        cnv_schema,
        _property_schema(cnv_schema, cnv_data, "pvs1_flowchart"),
        {"preliminary_decision_path", "final_strength", "decision_tree"},
    )

    search_schema = tools["search_variants"].output_schema
    search_data = _data_schema(search_schema)
    search_result = _resolve_ref(search_schema, search_data["properties"]["results"]["items"])
    _assert_typed_object_schema(
        search_schema,
        search_result,
        {"variant_id", "gene", "variant_type", "genome_build", "url"},
    )


@pytest.mark.asyncio
async def test_clear_cache_schema_accepts_empty_object_without_dummy_field() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    schema = tools["clear_cache"].parameters
    assert schema.get("properties", {}) == {}
    assert "_" not in schema.get("properties", {})
    assert set(tools["clear_cache"].output_schema["properties"]) == {"ok", "data", "error", "meta"}
