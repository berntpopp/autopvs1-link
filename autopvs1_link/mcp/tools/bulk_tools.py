"""MCP bulk tools: ``get_variants_pvs1_data_bulk`` and ``get_cnvs_pvs1_data_bulk``."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import (
    BulkCNVPVS1ResultItem,
    BulkCNVsMCPData,
    BulkPerItemMeta,
    BulkVariantPVS1ResultItem,
    BulkVariantsMCPData,
)
from autopvs1_link.mcp.envelope import (
    MCPWarning,
    ToolResponse,
    error_envelope,
    ok_envelope,
)
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.next_commands import bulk_retry_failed
from autopvs1_link.mcp.telemetry import get_call_telemetry, reset_call_telemetry
from autopvs1_link.mcp.tools._bulk_echo import echo_cnv_input, echo_variant_input
from autopvs1_link.mcp.tools._bulk_input import (
    BULK_MAX_ITEMS,
    CNV_ITEM_SCHEMA,
    META_MODE_SCHEMA,
    RESPONSE_MODE_SCHEMA,
    VARIANT_ITEM_SCHEMA,
    _aggregate_cache,
    _BulkInputError,
    _coerce_items_list,
    _dedupe_warnings,
    _parse_cnv_items,
    _parse_variant_items,
    _validate_size,
)
from autopvs1_link.mcp.tools._bulk_untrusted import (
    bulk_untrusted_limit_envelope,
    collect_untrusted_texts,
)
from autopvs1_link.mcp.tools._pvs1_runners import run_cnv_pvs1, run_variant_pvs1
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.untrusted_content import (
    UntrustedTextLimitError,
    enforce_untrusted_text_limits,
)

_VARIANTS_BULK_TOOL = "get_variants_pvs1_data_bulk"
_CNVS_BULK_TOOL = "get_cnvs_pvs1_data_bulk"


def register(mcp: FastMCP) -> None:
    """Register both bulk PVS1 scoring tools."""

    @mcp.tool(
        name="get_variants_pvs1_data_bulk",
        title="Get Variant PVS1 Data (Bulk)",
        tags={"variant", "classification", "bulk"},
        output_schema=None,  # suppressed (Tool-Surface Budget Standard v1, Rule 3)
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
                examples=[[{"genome_build": "hg38", "variant_id": "X-82763936-A-T"}]],
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
                    "Response detail level applied to each item. Default "
                    "'summary' keeps the per-item payload small enough "
                    "that 10 items still fit one turn budget. Widen to "
                    "'standard' only when an item needs the full "
                    "decision tree."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "summary",
        meta_mode: Annotated[
            Any,
            Field(
                description=(
                    "Metadata detail level: compact (default -- doi+pmid), "
                    "full (adds verbatim citation text+url), or minimal "
                    "(no citation)."
                ),
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "compact",
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

        Auto-resolution applies per item: non-canonical inputs (rsID,
        HGVS c./p./g.) round-trip through Ensembl Variant Recoder before
        scoring, mirroring ``get_variant_pvs1_data``. Multi-candidate
        resolutions return per-item ``requires_disambiguation`` with
        allele-keyed candidates so the caller picks one and re-calls that
        single item; a resolver outage returns the retryable
        ``external_resolver_unavailable`` code.

        Per-item envelope: each row in the top-level ``results`` array has
        ``{ok, input, data, error, meta}`` where ``meta.cache_status`` and
        ``meta.elapsed_ms`` echo that one upstream call's outcome (absent
        when the item short-circuited before upstream). This per-item
        shape predates and is scoped separately from the Response-Envelope
        Standard v1 outer frame. Output items preserve input order.
        ``response_mode`` and ``include_unmet`` apply per item; the outer
        ``meta_mode`` controls the envelope. Per-item failures do not stop
        the batch unless ``continue_on_error=false``. Bulk dispatch errors
        (malformed ``items``) use ``error_code='invalid_input'`` (subcode
        ``invalid_bulk_input``).

        Aggregate cache observability: top-level ``_meta.cache_status``
        echoes the unanimous status when every item agrees; on a mixed
        batch it is ``"mixed"`` and ``_meta.cached_count`` /
        ``_meta.uncached_count`` split items by warm
        (``hit``+``coalesced``) vs cold (``miss``+``bypass``).
        ``_meta.elapsed_ms`` is the SUM of per-item upstream wall-clocks
        (the honest total for a sequential bulk).

        Warning aggregation: per-item warnings are NOT echoed; they are
        collapsed into ``_meta.warnings`` at the top level. A warning code
        is aggregated only when more than one distinct item emitted it;
        single-item codes appear without ``count`` or ``affected_indices``.
        Aggregated codes carry ``count`` (distinct items) and the sorted
        ``affected_indices`` list. Order is first-seen-code-first.
        """
        normalized_meta_mode: MetaMode = "compact"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            raw_items = _coerce_items_list(items)
            _validate_size(raw_items)
            parsed_items = _parse_variant_items(raw_items)
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(
                exc, meta_mode=normalized_meta_mode, tool_name=_VARIANTS_BULK_TOOL
            )
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
                tool_name=_VARIANTS_BULK_TOOL,
            )

        results: list[BulkVariantPVS1ResultItem] = []
        aggregated_warnings: list[tuple[int, MCPWarning]] = []
        per_item_cache_status: list[str | None] = []
        per_item_elapsed_ms: list[float | None] = []
        keep_going = bool(continue_on_error) if isinstance(continue_on_error, bool) else True
        for index, item in enumerate(parsed_items):
            # Reset BEFORE each item so the ContextVar reflects only this
            # item's upstream call (or stays None for items that
            # short-circuited before upstream).
            reset_call_telemetry()
            data, warnings, error = await run_variant_pvs1(
                genome_build=item.genome_build,
                variant_id=item.variant_id,
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            item_elapsed, item_cache = get_call_telemetry()
            per_item_cache_status.append(item_cache)
            per_item_elapsed_ms.append(item_elapsed)
            item_meta = (
                BulkPerItemMeta(
                    cache_status=item_cache,
                    elapsed_ms=round(item_elapsed, 2) if item_elapsed is not None else None,
                )
                if item_cache is not None
                else None
            )
            results.append(
                BulkVariantPVS1ResultItem(
                    ok=error is None,
                    input=echo_variant_input(item),
                    data=data,
                    error=error,
                    meta=item_meta,
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
        # Response-wide ceiling over EVERY fenced object across all items,
        # not just per-item — 10 items each near the limit would otherwise
        # aggregate past the 128-object / 8 MiB-total ceiling untyped.
        try:
            enforce_untrusted_text_limits(collect_untrusted_texts(payload))
        except UntrustedTextLimitError:
            return bulk_untrusted_limit_envelope(
                meta_mode=normalized_meta_mode, tool_name=_VARIANTS_BULK_TOOL
            )
        aggregate_kwargs = _aggregate_cache(per_item_cache_status, per_item_elapsed_ms)
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
            tool_name=_VARIANTS_BULK_TOOL,
            collection_field="items",
            next_commands=bulk_retry_failed("get_variant_pvs1_data", results, "variant_id"),
            **aggregate_kwargs,
        )

    @mcp.tool(
        name="get_cnvs_pvs1_data_bulk",
        title="Get CNV PVS1 Data (Bulk)",
        tags={"cnv", "copy-number", "classification", "bulk"},
        output_schema=None,  # suppressed (Tool-Surface Budget Standard v1, Rule 3)
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
                examples=[[{"genome_build": "hg38", "cnv_id": "17-15000000-20000000-DEL"}]],
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
                    "Response detail level applied to each item. Default "
                    "'summary' keeps the per-item payload small enough "
                    "that 10 items still fit one turn budget. Widen to "
                    "'standard' only when an item needs the full "
                    "decision tree."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "summary",
        meta_mode: Annotated[
            Any,
            Field(
                description=(
                    "Metadata detail level: compact (default -- doi+pmid), "
                    "full (adds verbatim citation text+url), or minimal "
                    "(no citation)."
                ),
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "compact",
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
        upstream rate limit + cache; per-item ``{ok, input, data, error,
        meta}`` with ``meta.cache_status`` + ``meta.elapsed_ms`` echoing
        each item's upstream outcome; output items preserve input order;
        ``response_mode`` and ``include_unmet`` apply per item; the outer
        ``meta_mode`` controls the envelope. Per-item failures do not
        stop the batch unless ``continue_on_error=false``.

        Aggregate cache observability: top-level ``_meta.cache_status``
        is ``"mixed"`` when items had varied outcomes (with
        ``cached_count`` / ``uncached_count``) or echoes the unanimous
        status. ``_meta.elapsed_ms`` is the SUM of per-item upstream
        wall-clocks.

        Warning aggregation: per-item warnings collapse into
        ``_meta.warnings``; codes emitted by more than one distinct item
        carry ``count`` and ``affected_indices``; single-item codes do
        not. Order is first-seen-code-first.
        """
        normalized_meta_mode: MetaMode = "compact"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            raw_items = _coerce_items_list(items)
            _validate_size(raw_items)
            parsed_items = _parse_cnv_items(raw_items)
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(
                exc, meta_mode=normalized_meta_mode, tool_name=_CNVS_BULK_TOOL
            )
        except _BulkInputError as exc:
            return error_envelope(
                code="invalid_bulk_input",
                message=exc.message,
                retryable=False,
                suggestions=[
                    f"Pass items as a list of 1-{BULK_MAX_ITEMS} {{genome_build, cnv_id}} objects."
                ],
                meta_mode=normalized_meta_mode,
                tool_name=_CNVS_BULK_TOOL,
            )

        results: list[BulkCNVPVS1ResultItem] = []
        aggregated_warnings: list[tuple[int, MCPWarning]] = []
        per_item_cache_status: list[str | None] = []
        per_item_elapsed_ms: list[float | None] = []
        keep_going = bool(continue_on_error) if isinstance(continue_on_error, bool) else True
        for index, item in enumerate(parsed_items):
            reset_call_telemetry()
            data, warnings, error = await run_cnv_pvs1(
                genome_build=item.genome_build,
                cnv_id=item.cnv_id,
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            item_elapsed, item_cache = get_call_telemetry()
            per_item_cache_status.append(item_cache)
            per_item_elapsed_ms.append(item_elapsed)
            item_meta = (
                BulkPerItemMeta(
                    cache_status=item_cache,
                    elapsed_ms=round(item_elapsed, 2) if item_elapsed is not None else None,
                )
                if item_cache is not None
                else None
            )
            results.append(
                BulkCNVPVS1ResultItem(
                    ok=error is None,
                    input=echo_cnv_input(item),
                    data=data,
                    error=error,
                    meta=item_meta,
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
        # Response-wide ceiling over EVERY fenced object across all items.
        try:
            enforce_untrusted_text_limits(collect_untrusted_texts(payload))
        except UntrustedTextLimitError:
            return bulk_untrusted_limit_envelope(
                meta_mode=normalized_meta_mode, tool_name=_CNVS_BULK_TOOL
            )
        aggregate_kwargs = _aggregate_cache(per_item_cache_status, per_item_elapsed_ms)
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
            tool_name=_CNVS_BULK_TOOL,
            collection_field="items",
            next_commands=bulk_retry_failed("get_cnv_pvs1_data", results, "cnv_id"),
            **aggregate_kwargs,
        )
