"""MCP bulk tools: ``get_variants_pvs1_data_bulk`` and ``get_cnvs_pvs1_data_bulk``."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import (
    BulkCNVPVS1InputItem,
    BulkCNVPVS1ResultItem,
    BulkCNVsMCPData,
    BulkCNVsMCPEnvelope,
    BulkVariantPVS1InputItem,
    BulkVariantPVS1ResultItem,
    BulkVariantsMCPData,
    BulkVariantsMCPEnvelope,
)
from autopvs1_link.mcp.envelope import MCPWarning, ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.tools._pvs1_runners import run_cnv_pvs1, run_variant_pvs1
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope

BULK_MAX_ITEMS = 10


def _dedupe_warnings(
    indexed_warnings: list[tuple[int, MCPWarning]],
) -> list[MCPWarning]:
    """Collapse per-item warnings by code.

    Input: ``[(item_index, warning), ...]`` in order of emission.
    Output: one ``MCPWarning`` per unique code, in first-seen order.

    Aggregation gate is per-item, not per-emission: when a code is emitted
    by more than one distinct item, the returned warning carries ``count``
    (the number of distinct affected items) and ``affected_indices`` (the
    sorted, deduplicated item index list). When a code is emitted only by
    a single item — even if that item emits the same code multiple times
    — the original ``MCPWarning`` is returned unchanged so single-tool
    callers see the wire shape they have always seen.
    """
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for idx, warning in indexed_warnings:
        bucket = buckets.get(warning.code)
        if bucket is None:
            buckets[warning.code] = {
                "first": warning,
                "indices": [idx],
            }
            order.append(warning.code)
        else:
            bucket["indices"].append(idx)

    deduped: list[MCPWarning] = []
    for code in order:
        bucket = buckets[code]
        first: MCPWarning = bucket["first"]
        indices = sorted(set(bucket["indices"]))
        if len(indices) > 1:
            deduped.append(
                MCPWarning(
                    code=first.code,
                    message=first.message,
                    count=len(indices),
                    affected_indices=indices,
                )
            )
        else:
            deduped.append(first)
    return deduped


RESPONSE_MODE_SCHEMA = {"type": "string", "enum": ["ids_only", "summary", "standard", "full"]}
META_MODE_SCHEMA = {"type": "string", "enum": ["full", "compact", "minimal"]}
VARIANT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "genome_build": {"type": "string", "enum": ["hg19", "hg38"]},
        "variant_id": {"type": "string", "minLength": 1},
    },
    "required": ["genome_build", "variant_id"],
}
CNV_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "genome_build": {"type": "string", "enum": ["hg19", "hg38"]},
        "cnv_id": {"type": "string", "minLength": 1},
    },
    "required": ["genome_build", "cnv_id"],
}


def _coerce_items_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise _bulk_input_error("items must be a list.")
    return [_coerce_item_dict(item, index) for index, item in enumerate(raw)]


def _coerce_item_dict(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise _bulk_input_error(f"items[{index}] must be an object.")
    return item


class _BulkInputError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _bulk_input_error(message: str) -> _BulkInputError:
    return _BulkInputError(message)


def _validate_size(items: list[Any]) -> None:
    if not items:
        raise _bulk_input_error("items must contain at least one entry.")
    if len(items) > BULK_MAX_ITEMS:
        raise _bulk_input_error(
            f"items must contain at most {BULK_MAX_ITEMS} entries; received {len(items)}."
        )


def _parse_variant_items(raw_items: list[dict[str, Any]]) -> list[BulkVariantPVS1InputItem]:
    parsed: list[BulkVariantPVS1InputItem] = []
    for index, item in enumerate(raw_items):
        try:
            parsed.append(BulkVariantPVS1InputItem.model_validate(item))
        except Exception as exc:
            raise _bulk_input_error(
                f"items[{index}] is missing required fields or has invalid values: {exc}"
            ) from exc
    return parsed


def _parse_cnv_items(raw_items: list[dict[str, Any]]) -> list[BulkCNVPVS1InputItem]:
    parsed: list[BulkCNVPVS1InputItem] = []
    for index, item in enumerate(raw_items):
        try:
            parsed.append(BulkCNVPVS1InputItem.model_validate(item))
        except Exception as exc:
            raise _bulk_input_error(
                f"items[{index}] is missing required fields or has invalid values: {exc}"
            ) from exc
    return parsed


def register(mcp: FastMCP) -> None:
    """Register both bulk PVS1 scoring tools."""

    @mcp.tool(
        name="get_variants_pvs1_data_bulk",
        title="Get Variant PVS1 Data (Bulk)",
        output_schema=BulkVariantsMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_variants_pvs1_data_bulk(
        items: Annotated[
            Any,
            Field(
                description=(
                    f"List of 1 to {BULK_MAX_ITEMS} variant requests. Each item: "
                    "{genome_build: hg19|hg38, variant_id: ...}."
                ),
                json_schema_extra={
                    "type": "array",
                    "items": VARIANT_ITEM_SCHEMA,
                    "minItems": 1,
                    "maxItems": BULK_MAX_ITEMS,
                },
            ),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description=(
                    "Response detail level applied to each item. Default to "
                    "'summary' for bulk batch screens — keeps the per-item "
                    "payload small enough that 10 items still fit a turn. "
                    "Widen to 'standard' only when an item needs the full "
                    "decision tree."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "standard",
        meta_mode: Annotated[
            Any,
            Field(
                description="Top-level metadata detail level.",
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "full",
        include_unmet: Annotated[
            Any,
            Field(
                description="Include disease-mechanism rows with adjusted_strength=Unmet.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
        continue_on_error: Annotated[
            Any,
            Field(
                description="If true (default), per-item failures do not stop the batch.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
    ) -> ToolResponse:
        """Score 1-10 SNV/indel variants in one call.

        Prefer this over ``get_variant_pvs1_data`` when you have 2+ variant
        IDs of the same kind. For LLM batch screens, default to
        ``response_mode='summary'`` so 10 verdicts share one turn budget;
        widen per-item only when reasoning needs the full decision tree.
        Items run sequentially server-side and respect the upstream rate
        limit (default ~1 req/s) plus the existing cache, so a fully
        uncached 10-item batch can take ~10s wall time and a fully cached
        one returns in milliseconds.

        Per-item envelope: each result has ``{ok, input, data, error}``.
        Output items preserve input order. ``response_mode`` and
        ``include_unmet`` apply per item; ``meta_mode`` applies to the outer
        envelope only. Per-item input or upstream failures do not stop the
        batch unless ``continue_on_error=false``. Bulk dispatch errors
        (malformed ``items``) use error code ``invalid_bulk_input``.

        Warning aggregation: per-item warnings are NOT echoed; they are
        collapsed into ``meta.warnings`` at the top level. A warning code
        is aggregated only when more than one distinct item emitted it;
        single-item codes appear without ``count`` or ``affected_indices``.
        Aggregated codes carry ``count`` (distinct items) and the sorted
        ``affected_indices`` list. Order is first-seen-code-first.
        """
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            raw_items = _coerce_items_list(items)
            _validate_size(raw_items)
            parsed_items = _parse_variant_items(raw_items)
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(exc, meta_mode=normalized_meta_mode)
        except _BulkInputError as exc:
            return error_envelope(
                code="invalid_bulk_input",
                message=exc.message,
                retryable=False,
                suggestions=[
                    f"Pass items as a list of 1-{BULK_MAX_ITEMS} "
                    "{genome_build, variant_id} objects."
                ],
                meta_mode=normalized_meta_mode,
            )

        results: list[BulkVariantPVS1ResultItem] = []
        aggregated_warnings: list[tuple[int, MCPWarning]] = []
        keep_going = bool(continue_on_error) if isinstance(continue_on_error, bool) else True
        for index, item in enumerate(parsed_items):
            data, warnings, error = await run_variant_pvs1(
                genome_build=item.genome_build,
                variant_id=item.variant_id,
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            results.append(
                BulkVariantPVS1ResultItem(
                    ok=error is None,
                    input=item,
                    data=data,
                    error=error,
                )
            )
            aggregated_warnings.extend((index, w) for w in warnings)
            if error is not None and not keep_going:
                break

        total = len(parsed_items)
        attempted = len(results)
        skipped = total - attempted
        succeeded = sum(1 for result in results if result.ok)
        failed = attempted - succeeded
        payload = BulkVariantsMCPData(
            total=total,
            attempted=attempted,
            skipped=skipped,
            succeeded=succeeded,
            failed=failed,
            items=results,
        )
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
        )

    @mcp.tool(
        name="get_cnvs_pvs1_data_bulk",
        title="Get CNV PVS1 Data (Bulk)",
        output_schema=BulkCNVsMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_cnvs_pvs1_data_bulk(
        items: Annotated[
            Any,
            Field(
                description=(
                    f"List of 1 to {BULK_MAX_ITEMS} CNV requests. Each item: "
                    "{genome_build: hg19|hg38, cnv_id: chrom-start-end-DEL|DUP}."
                ),
                json_schema_extra={
                    "type": "array",
                    "items": CNV_ITEM_SCHEMA,
                    "minItems": 1,
                    "maxItems": BULK_MAX_ITEMS,
                },
            ),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description=(
                    "Response detail level applied to each item. Default to "
                    "'summary' for bulk batch screens — keeps the per-item "
                    "payload small enough that 10 items still fit a turn. "
                    "Widen to 'standard' only when an item needs the full "
                    "decision tree."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "standard",
        meta_mode: Annotated[
            Any,
            Field(
                description="Top-level metadata detail level.",
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "full",
        include_unmet: Annotated[
            Any,
            Field(
                description="Include disease-mechanism rows with adjusted_strength=Unmet.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
        continue_on_error: Annotated[
            Any,
            Field(
                description="If true (default), per-item failures do not stop the batch.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
    ) -> ToolResponse:
        """Score 1-10 CNVs in one call.

        Prefer this over ``get_cnv_pvs1_data`` when you have 2+ CNV IDs.
        For LLM batch screens, default to ``response_mode='summary'`` so
        10 verdicts share one turn budget. Same semantics as
        ``get_variants_pvs1_data_bulk``: sequential server-side, respects
        upstream rate limit + cache; per-item ``{ok, input, data,
        error}``; output items preserve input order; ``response_mode``
        and ``include_unmet`` apply per item; ``meta_mode`` applies to
        the outer envelope only. Per-item failures do not stop the batch
        unless ``continue_on_error=false``.

        Warning aggregation: per-item warnings collapse into
        ``meta.warnings``; codes emitted by more than one distinct item
        carry ``count`` and ``affected_indices``; single-item codes do
        not. Order is first-seen-code-first.
        """
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            raw_items = _coerce_items_list(items)
            _validate_size(raw_items)
            parsed_items = _parse_cnv_items(raw_items)
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(exc, meta_mode=normalized_meta_mode)
        except _BulkInputError as exc:
            return error_envelope(
                code="invalid_bulk_input",
                message=exc.message,
                retryable=False,
                suggestions=[
                    f"Pass items as a list of 1-{BULK_MAX_ITEMS} {{genome_build, cnv_id}} objects."
                ],
                meta_mode=normalized_meta_mode,
            )

        results: list[BulkCNVPVS1ResultItem] = []
        aggregated_warnings: list[tuple[int, MCPWarning]] = []
        keep_going = bool(continue_on_error) if isinstance(continue_on_error, bool) else True
        for index, item in enumerate(parsed_items):
            data, warnings, error = await run_cnv_pvs1(
                genome_build=item.genome_build,
                cnv_id=item.cnv_id,
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            results.append(
                BulkCNVPVS1ResultItem(
                    ok=error is None,
                    input=item,
                    data=data,
                    error=error,
                )
            )
            aggregated_warnings.extend((index, w) for w in warnings)
            if error is not None and not keep_going:
                break

        total = len(parsed_items)
        attempted = len(results)
        skipped = total - attempted
        succeeded = sum(1 for result in results if result.ok)
        failed = attempted - succeeded
        payload = BulkCNVsMCPData(
            total=total,
            attempted=attempted,
            skipped=skipped,
            succeeded=succeeded,
            failed=failed,
            items=results,
        )
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
        )
