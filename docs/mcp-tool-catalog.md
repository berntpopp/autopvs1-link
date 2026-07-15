# MCP Tool Catalog

Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`.

## Tools

### `get_cnv_pvs1_data`

Score one copy-number variant with the AutoPVS1 PVS1 rules.

First-turn LLM callers get the verdict under ~1.5KB by default
(``response_mode='summary'``). Widen to ``response_mode='standard'``
for the full decision tree. AutoPVS1 outputs are research-use only,
not clinical decision support.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "cnv_id": {
      "description": "AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form, for example 17-15000000-20000000-DEL. TYPE is DEL or DUP.",
      "examples": [
        "17-15000000-20000000-DEL"
      ],
      "type": "string"
    },
    "genome_build": {
      "description": "Genome build: hg19 or hg38.",
      "enum": [
        "hg19",
        "hg38"
      ],
      "examples": [
        "hg38",
        "hg19"
      ],
      "type": "string"
    },
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "meta_mode": {
      "default": "compact",
      "description": "Metadata detail level: compact (default -- doi+pmid), full (adds verbatim citation text+url), or minimal (no citation).",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "summary",
      "description": "Response detail level. Default 'summary' returns the verdict (preliminary path + final strength) under ~1.5KB. Widen to 'standard' for the full decision tree with hoisted note_text and disease_mechanisms when the user asks for the tree; use 'full' only for auditors who need the ``*_raw`` upstream fields; 'ids_only' is the batch-screen lookup tier.",
      "enum": [
        "ids_only",
        "summary",
        "standard",
        "full"
      ],
      "type": "string"
    }
  },
  "required": [
    "genome_build",
    "cnv_id"
  ],
  "type": "object"
}
```

### `get_cnvs_pvs1_data_bulk`

Score 1-10 CNVs in one call.

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

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "continue_on_error": {
      "default": true,
      "description": "If true (default), per-item failures do not stop the batch.",
      "type": "boolean"
    },
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "items": {
      "description": "List of 1 to 10 CNV requests. Each item: {genome_build: hg19|hg38, cnv_id: chrom-start-end-DEL|DUP}.",
      "examples": [
        [
          {
            "cnv_id": "17-15000000-20000000-DEL",
            "genome_build": "hg38"
          }
        ]
      ],
      "items": {
        "properties": {
          "cnv_id": {
            "minLength": 1,
            "type": "string"
          },
          "genome_build": {
            "enum": [
              "hg19",
              "hg38"
            ],
            "type": "string"
          }
        },
        "required": [
          "genome_build",
          "cnv_id"
        ],
        "type": "object"
      },
      "maxItems": 10,
      "minItems": 1,
      "type": "array"
    },
    "meta_mode": {
      "default": "compact",
      "description": "Metadata detail level: compact (default -- doi+pmid), full (adds verbatim citation text+url), or minimal (no citation).",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "summary",
      "description": "Response detail level applied to each item. Default 'summary' keeps the per-item payload small enough that 10 items still fit one turn budget. Widen to 'standard' only when an item needs the full decision tree.",
      "enum": [
        "ids_only",
        "summary",
        "standard",
        "full"
      ],
      "type": "string"
    }
  },
  "required": [
    "items"
  ],
  "type": "object"
}
```

### `get_server_capabilities`

Use this to discover AutoPVS1-Link MCP tools, inputs, limitations, and workflow.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {},
  "type": "object"
}
```

### `get_server_health`

Return local MCP server health.

Default behaviour: no upstream call, sub-millisecond. Pass
``check_upstream=true`` for an opt-in HEAD probe — useful when an
agent wants to confirm AutoPVS1 is reachable before scheduling a
cold scoring call.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "check_upstream": {
      "default": false,
      "description": "When true, issue one short HEAD probe against the AutoPVS1 base URL and report reachability in data.upstream_reachable. Default false keeps the cheap-tool contract (no upstream cost, sub-ms).",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

### `get_variant_pvs1_data`

Score one SNV/indel variant with the AutoPVS1 PVS1 rules.

Auto-resolves non-canonical inputs (rsID, HGVS c./p./g.) into
canonical SPDI via one Ensembl Variant Recoder REST call before
scoring (build-scoped — GRCh37 host for hg19, GRCh38 host for
hg38). Emits an ``auto_resolved`` warning carrying the input,
the resolved id, and the resolver source. Ambiguous resolutions
return ``error_code='ambiguous_query'`` (subcode
``requires_disambiguation``) with allele-keyed candidates instead
of silently picking one (mitigates multi-allelic mis-scoring).

First-turn LLM callers get the verdict under ~1.5KB by default
(``response_mode='summary'``). Widen to ``response_mode='standard'``
for the full decision tree, or ``'full'`` for the audit-trail
``*_raw`` upstream fields. AutoPVS1 outputs are research-use only,
not clinical decision support.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "genome_build": {
      "description": "Genome build: hg19 or hg38.",
      "enum": [
        "hg19",
        "hg38"
      ],
      "examples": [
        "hg38",
        "hg19"
      ],
      "type": "string"
    },
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "meta_mode": {
      "default": "compact",
      "description": "Metadata detail level: compact (default -- doi+pmid), full (adds verbatim citation text+url), or minimal (no citation).",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "summary",
      "description": "Response detail level. Default 'summary' returns the verdict (preliminary path + final strength) under ~1.5KB so first-turn LLM callers stay in budget. Widen to 'standard' for the full decision tree with hoisted note_text and disease_mechanisms when the user asks for the tree; use 'full' only for auditors who need the ``*_raw`` upstream fields; 'ids_only' is the batch-screen lookup tier.",
      "enum": [
        "ids_only",
        "summary",
        "standard",
        "full"
      ],
      "type": "string"
    },
    "variant_id": {
      "description": "Variant identifier. Canonical SPDI (CHROM-POS-REF-ALT, e.g. X-82763936-A-T) scores in one upstream call. rsID (rs80357906) or HGVS (NM_007294.4:c.5266dup, NP_000050.2:p.Glu1756fs, NC_000017.11:g.43091983C>A) auto-resolves via Ensembl Variant Recoder REST (build-scoped) then scores. Multiple resolver candidates return error_code='ambiguous_query' (error_subcode 'requires_disambiguation') with allele-keyed rows in details.candidates \u2014 caller picks one. Recoder offline returns error_code='upstream_unavailable' (error_subcode 'external_resolver_unavailable', retryable).",
      "examples": [
        "X-82763936-A-T"
      ],
      "type": "string"
    }
  },
  "required": [
    "genome_build",
    "variant_id"
  ],
  "type": "object"
}
```

### `get_variants_pvs1_data_bulk`

Score 1-10 SNV/indel variants in one call.

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

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "continue_on_error": {
      "default": true,
      "description": "If true (default), per-item failures do not stop the batch.",
      "type": "boolean"
    },
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "items": {
      "description": "List of 1 to 10 variant requests. Each item: {genome_build: hg19|hg38, variant_id: ...}.",
      "examples": [
        [
          {
            "genome_build": "hg38",
            "variant_id": "X-82763936-A-T"
          }
        ]
      ],
      "items": {
        "properties": {
          "genome_build": {
            "enum": [
              "hg19",
              "hg38"
            ],
            "type": "string"
          },
          "variant_id": {
            "minLength": 1,
            "type": "string"
          }
        },
        "required": [
          "genome_build",
          "variant_id"
        ],
        "type": "object"
      },
      "maxItems": 10,
      "minItems": 1,
      "type": "array"
    },
    "meta_mode": {
      "default": "compact",
      "description": "Metadata detail level: compact (default -- doi+pmid), full (adds verbatim citation text+url), or minimal (no citation).",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "summary",
      "description": "Response detail level applied to each item. Default 'summary' keeps the per-item payload small enough that 10 items still fit one turn budget. Widen to 'standard' only when an item needs the full decision tree.",
      "enum": [
        "ids_only",
        "summary",
        "standard",
        "full"
      ],
      "type": "string"
    }
  },
  "required": [
    "items"
  ],
  "type": "object"
}
```

### `search_variants`

Search AutoPVS1 by gene symbol or variant text.

Use ``response_mode='ids_only'`` (lowest-bandwidth lookup) to
resolve a query to an AutoPVS1 ``variant_id`` you can hand to
``get_variant_pvs1_data``. ``next_cursor`` is base64url JSON today
(decodable) but treat it as an echo-back token; it MAY become
opaque later. AutoPVS1 outputs are research-use only,
not clinical decision support.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "cursor": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Pagination token from a prior response's next_cursor. Transparent base64url JSON today (you MAY decode it), but prefer echoing it back unchanged; it MAY become opaque later."
    },
    "genome_build": {
      "anyOf": [
        {
          "enum": [
            "hg19",
            "hg38"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Canonical genome build for MCP search: hg19 or hg38."
    },
    "genome_version": {
      "anyOf": [
        {
          "enum": [
            "hg19",
            "hg38"
          ],
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deprecated alias for genome_build; accepted for one release."
    },
    "limit": {
      "default": 10,
      "description": "Maximum results to return; default 10. Values below 1 are treated as 1 and values above 50 are treated as 50.",
      "type": "integer"
    },
    "meta_mode": {
      "default": "compact",
      "description": "Metadata detail level: compact (default -- doi+pmid), full (adds verbatim citation text+url), or minimal (no citation).",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "query": {
      "description": "Gene symbol, HGVS text, or partial variant string.",
      "examples": [
        "BRCA1"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "ids_only",
      "description": "Response detail level. Default 'ids_only' emits the AutoPVS1 variant_id and url per row \u2014 the leanest shape for hand-off to get_variant_pvs1_data. 'summary' keeps variant_id + url per row plus suggestions (lean navigable page); 'standard' returns rich rows with gene + variant_type; 'full' is identical to 'standard' for search.",
      "enum": [
        "ids_only",
        "summary",
        "standard",
        "full"
      ],
      "type": "string"
    }
  },
  "required": [
    "query"
  ],
  "type": "object"
}
```

## Prompts

### `classify_cnv`

Title: Classify CNV with AutoPVS1

Guide a research-use AutoPVS1 CNV PVS1 workflow.

#### Arguments

- `genome_build` (required): Genome build, usually hg19 or hg38.

Provide as a JSON string matching the following schema: {"type":"string"}
- `cnv_id` (required): AutoPVS1 CNV ID such as 17-15000000-20000000-DEL.

Provide as a JSON string matching the following schema: {"type":"string"}

### `classify_variant`

Title: Classify SNV/Indel with AutoPVS1

Guide a research-use AutoPVS1 SNV/indel PVS1 workflow.

#### Arguments

- `genome_build` (required): Genome build, usually hg19 or hg38.

Provide as a JSON string matching the following schema: {"type":"string"}
- `variant_id` (required): AutoPVS1 variant ID such as X-82763936-A-T.

Provide as a JSON string matching the following schema: {"type":"string"}

### `pvs1_workflow_help`

Title: AutoPVS1 Workflow Guidance

Return concrete tool-chain guidance for one of three tasks: clinical_review, batch_screen, or search_first.

#### Arguments

- `task` (required): One of clinical_review, batch_screen, or search_first.

Provide as a JSON string matching the following schema: {"type":"string"}

## Resources

- `autopvs1-link://cache/statistics` - Read-only snapshot of in-memory cache hit/miss/eviction counts and timing per cached service method (variant, CNV, search).
- `autopvs1-link://capabilities` - Detailed MCP usage guidance: accepted formats, examples, search behavior, error envelope, stable error and warning codes, cache statistics URI, destructive-tool gating, citation, and known upstream limitations.
