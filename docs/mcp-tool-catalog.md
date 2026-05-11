# MCP Tool Catalog

Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`.

## Tools

### `get_variant_pvs1_data`

Return the AutoPVS1 PVS1 analysis for a single variant.

```json
{
  "additionalProperties": false,
  "properties": {
    "payload": {
      "description": "Input for ``get_variant_pvs1_data``.",
      "properties": {
        "genome_build": {
          "description": "Genome build: hg19 or hg38.",
          "enum": [
            "hg19",
            "hg38"
          ],
          "type": "string"
        },
        "variant_id": {
          "description": "Variant identifier as accepted by AutoPVS1.",
          "minLength": 1,
          "type": "string"
        }
      },
      "required": [
        "genome_build",
        "variant_id"
      ],
      "type": "object"
    }
  },
  "required": [
    "payload"
  ],
  "type": "object"
}
```

### `get_cnv_pvs1_data`

Return the AutoPVS1 PVS1 analysis for a single CNV.

```json
{
  "additionalProperties": false,
  "properties": {
    "payload": {
      "description": "Input for ``get_cnv_pvs1_data``.",
      "properties": {
        "genome_build": {
          "description": "Genome build: hg19 or hg38.",
          "enum": [
            "hg19",
            "hg38"
          ],
          "type": "string"
        },
        "cnv_id": {
          "description": "CNV identifier as accepted by AutoPVS1.",
          "minLength": 1,
          "type": "string"
        }
      },
      "required": [
        "genome_build",
        "cnv_id"
      ],
      "type": "object"
    }
  },
  "required": [
    "payload"
  ],
  "type": "object"
}
```

### `search_variants`

Search AutoPVS1 for variants matching the query.

```json
{
  "additionalProperties": false,
  "properties": {
    "payload": {
      "description": "Input for ``search_variants``.",
      "properties": {
        "query": {
          "description": "Gene symbol or partial variant string.",
          "minLength": 1,
          "type": "string"
        },
        "genome_version": {
          "default": "hg38",
          "description": "Genome build for the search.",
          "enum": [
            "hg19",
            "hg38"
          ],
          "type": "string"
        }
      },
      "required": [
        "query"
      ],
      "type": "object"
    }
  },
  "required": [
    "payload"
  ],
  "type": "object"
}
```

### `clear_cache`

Clear all service caches.

Disabled by default. Enable with
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.

```json
{
  "additionalProperties": false,
  "properties": {
    "_": {
      "anyOf": [
        {
          "description": "No fields; included for symmetry.",
          "properties": {},
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "type": "object"
}
```

## Resources

- `autopvs1-link://cache/statistics` - Read-only snapshot of in-memory cache statistics.
