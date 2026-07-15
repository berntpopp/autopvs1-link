"""Input coercion, validation, and per-batch aggregation for the bulk PVS1 tools.

Extracted from ``bulk_tools.py`` so each tool body stays small (per-file line
budget); the two registered tools import these helpers and the item schemas.
"""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import BulkCNVPVS1InputItem, BulkVariantPVS1InputItem
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.validation import contains_forbidden_codepoint

BULK_MAX_ITEMS = 10

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

_WARM_CACHE_STATUSES = frozenset({"hit", "coalesced"})
_COLD_CACHE_STATUSES = frozenset({"miss", "bypass"})


class _BulkInputError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _bulk_input_error(message: str) -> _BulkInputError:
    return _BulkInputError(message)


def _coerce_item_dict(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise _bulk_input_error(f"items[{index}] must be an object.")
    # Reject forbidden code points before a row could echo a hostile identifier.
    for value in item.values():
        if isinstance(value, str) and contains_forbidden_codepoint(value):
            raise _bulk_input_error(f"items[{index}] contains disallowed control characters.")
    return item


def _coerce_items_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise _bulk_input_error("items must be a list.")
    return [_coerce_item_dict(item, index) for index, item in enumerate(raw)]


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
        try:  # FIXED message (no {exc}): a pydantic error echoes the offending input
            parsed.append(BulkVariantPVS1InputItem.model_validate(item))
        except Exception as exc:
            raise _bulk_input_error(
                f"items[{index}] is missing required fields or has invalid values."
            ) from exc
    return parsed


def _parse_cnv_items(raw_items: list[dict[str, Any]]) -> list[BulkCNVPVS1InputItem]:
    parsed: list[BulkCNVPVS1InputItem] = []
    for index, item in enumerate(raw_items):
        try:
            parsed.append(BulkCNVPVS1InputItem.model_validate(item))
        except Exception as exc:
            raise _bulk_input_error(
                f"items[{index}] is missing required fields or has invalid values."
            ) from exc
    return parsed


def _dedupe_warnings(indexed_warnings: list[tuple[int, MCPWarning]]) -> list[MCPWarning]:
    """Collapse per-item warnings by code.

    Input: ``[(item_index, warning), ...]`` in order of emission. Output: one
    ``MCPWarning`` per unique code, in first-seen order. When a code is emitted by
    more than one distinct item the returned warning carries ``count`` (distinct
    affected items) and the sorted ``affected_indices``; a single-item code is
    returned unchanged so single-tool callers see the wire shape they always have.
    """
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for idx, warning in indexed_warnings:
        bucket = buckets.get(warning.code)
        if bucket is None:
            buckets[warning.code] = {"first": warning, "indices": [idx]}
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


def _aggregate_cache(
    per_item_statuses: list[str | None],
    per_item_elapsed: list[float | None],
) -> dict[str, Any]:
    """Compute aggregate cache observability from per-item telemetry.

    Returns kwargs ready to spread into ``ok_envelope``. The aggregate
    ``cache_status`` is the single underlying value when all items agree and
    ``"mixed"`` otherwise; ``cached_count``/``uncached_count`` populate only on a
    mixed batch. ``elapsed_ms_override`` is the SUM of per-item elapsed_ms (the
    honest aggregate for a sequential bulk wall-time), or absent when no item
    touched upstream.
    """
    observed = [s for s in per_item_statuses if s is not None]
    if not observed:
        return {}
    if len(set(observed)) == 1:
        kwargs: dict[str, Any] = {"cache_status_override": observed[0]}
    else:
        cached = sum(1 for s in observed if s in _WARM_CACHE_STATUSES)
        uncached = sum(1 for s in observed if s in _COLD_CACHE_STATUSES)
        kwargs = {
            "cache_status_override": "mixed",
            "cached_count": cached,
            "uncached_count": uncached,
        }
    elapsed_sum = sum(ms for ms in per_item_elapsed if ms is not None)
    if elapsed_sum:
        kwargs["elapsed_ms_override"] = round(elapsed_sum, 2)
    return kwargs
