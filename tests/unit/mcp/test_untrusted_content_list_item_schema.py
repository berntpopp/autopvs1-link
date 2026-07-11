"""List-item schema conformance for every fenced array field.

Response-Envelope v1.1: a fenced field that sits inside an array must have
its array ITEM schema declare the ``untrusted_text`` object (``kind``
const), not a bare permissive ``{"type": "object"}`` — a permissive item
schema hides the literal from the published output schema even when the
runtime data is correctly fenced. ``decision_tree_raw`` was originally typed
``list[dict[str, Any]]`` (permissive); this guards the fix that made it
``list[FlowchartStepMCP]`` instead.
"""

from __future__ import annotations

from typing import Any

import pytest

from autopvs1_link.mcp.facade import build_mcp_server

JsonSchema = dict[str, Any]


def _resolve_ref(root: JsonSchema, schema: JsonSchema) -> JsonSchema:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    resolved: Any = root
    for part in ref.removeprefix("#/").split("/"):
        resolved = resolved[part]
    assert isinstance(resolved, dict)
    return resolved


def _non_null(schema: JsonSchema) -> JsonSchema:
    for branch in schema.get("anyOf", []):
        if branch.get("type") != "null":
            return branch
    return schema


def _untrusted_text_item_schema(root: JsonSchema, array_schema: JsonSchema) -> JsonSchema:
    """Resolve an array property schema down to its item object's schema."""
    resolved = _resolve_ref(root, _non_null(array_schema))
    assert resolved.get("type") == "array", resolved
    items = _resolve_ref(root, _non_null(resolved["items"]))
    assert items.get("additionalProperties") is not True, (
        "array item schema must not be a bare permissive object"
    )
    return items


def _assert_kind_const_untrusted_text(root: JsonSchema, field_schema: JsonSchema) -> None:
    resolved = _resolve_ref(root, _non_null(field_schema))
    kind_schema = resolved["properties"]["kind"]
    # pydantic emits a Literal["untrusted_text"] as either "const" or a
    # single-value "enum" depending on schema-generation mode; accept both.
    literal_value = kind_schema.get("const") or (kind_schema.get("enum") or [None])[0]
    assert literal_value == "untrusted_text", kind_schema


@pytest.mark.asyncio
async def test_decision_tree_array_item_declares_untrusted_text_kind_const() -> None:
    mcp = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    schema = tools["get_variant_pvs1_data"].output_schema
    result_schema = _resolve_ref(schema, _non_null(schema["properties"]["result"]))
    flowchart = _resolve_ref(schema, _non_null(result_schema["properties"]["pvs1_flowchart"]))
    step_item = _untrusted_text_item_schema(schema, flowchart["properties"]["decision_tree"])
    _assert_kind_const_untrusted_text(schema, step_item["properties"]["code"])


@pytest.mark.asyncio
async def test_flowchart_schema_drops_duplicative_notes_and_decision_tree_raw() -> None:
    """v1.1 no-duplication: the notes legend and decision_tree_raw audit copy
    were removed (they re-embedded decision_tree's scraped prose), so they must
    not appear in the published output schema at all."""
    mcp = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    schema = tools["get_variant_pvs1_data"].output_schema
    result_schema = _resolve_ref(schema, _non_null(schema["properties"]["result"]))
    flowchart = _resolve_ref(schema, _non_null(result_schema["properties"]["pvs1_flowchart"]))
    assert "notes" not in flowchart["properties"]
    assert "decision_tree_raw" not in flowchart["properties"]


@pytest.mark.asyncio
async def test_disease_mechanisms_array_item_declares_untrusted_text_kind_const() -> None:
    mcp = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    schema = tools["get_variant_pvs1_data"].output_schema
    result_schema = _resolve_ref(schema, _non_null(schema["properties"]["result"]))
    row_item = _untrusted_text_item_schema(
        schema, result_schema["properties"]["disease_mechanisms"]
    )
    _assert_kind_const_untrusted_text(schema, row_item["properties"]["disease"])
