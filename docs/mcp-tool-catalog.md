# MCP Tool Catalog

Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`.

## Tools

### `clear_cache`

Clear all service caches.

Disabled by default. Enable with
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {},
  "type": "object"
}
```

#### Output Schema

```json
{
  "description": "Envelope schema for ``clear_cache``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "Clear-cache result data.",
          "properties": {
            "cleared": {
              "title": "Cleared",
              "type": "boolean"
            },
            "message": {
              "title": "Message",
              "type": "string"
            }
          },
          "required": [
            "cleared",
            "message"
          ],
          "title": "ClearCacheData",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "description": "Structured MCP tool error.",
          "properties": {
            "code": {
              "title": "Code",
              "type": "string"
            },
            "message": {
              "title": "Message",
              "type": "string"
            },
            "retryable": {
              "title": "Retryable",
              "type": "boolean"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            }
          },
          "required": [
            "code",
            "message",
            "retryable"
          ],
          "title": "MCPError",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "meta": {
      "description": "Common metadata on every MCP tool envelope.",
      "properties": {
        "recommended_citation": {
          "description": "Recommended citation for AutoPVS1 research-use outputs.",
          "properties": {
            "doi": {
              "default": "10.1002/humu.24051",
              "title": "Doi",
              "type": "string"
            },
            "pmid": {
              "default": "32442321",
              "title": "Pmid",
              "type": "string"
            },
            "text": {
              "default": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
              "title": "Text",
              "type": "string"
            },
            "url": {
              "default": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
              "title": "Url",
              "type": "string"
            }
          },
          "title": "RecommendedCitation",
          "type": "object"
        },
        "request_id": {
          "title": "Request Id",
          "type": "string"
        },
        "research_use_only": {
          "default": true,
          "title": "Research Use Only",
          "type": "boolean"
        },
        "server_version": {
          "default": "1.0.0",
          "title": "Server Version",
          "type": "string"
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.",
            "properties": {
              "code": {
                "title": "Code",
                "type": "string"
              },
              "message": {
                "title": "Message",
                "type": "string"
              }
            },
            "required": [
              "code",
              "message"
            ],
            "title": "MCPWarning",
            "type": "object"
          },
          "title": "Warnings",
          "type": "array"
        }
      },
      "title": "MCPMeta",
      "type": "object"
    },
    "ok": {
      "title": "Ok",
      "type": "boolean"
    }
  },
  "required": [
    "ok",
    "data",
    "error",
    "meta"
  ],
  "title": "ClearCacheMCPEnvelope",
  "type": "object"
}
```

### `get_cnv_pvs1_data`

Use this to score one copy-number variant with AutoPVS1 PVS1 rules.

#### Input Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "cnv_id": {
      "description": "AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form, for example 17-15000000-20000000-DEL. TYPE is DEL or DUP.",
      "type": "string"
    },
    "genome_build": {
      "description": "Genome build: hg19 or hg38.",
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
}
```

#### Output Schema

```json
{
  "description": "Envelope schema for ``get_cnv_pvs1_data``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "MCP-presented CNV data.",
          "properties": {
            "cnv_info": {
              "additionalProperties": true,
              "title": "Cnv Info",
              "type": "object"
            },
            "disease_mechanisms": {
              "items": {
                "additionalProperties": true,
                "type": "object"
              },
              "title": "Disease Mechanisms",
              "type": "array"
            },
            "genome_build": {
              "title": "Genome Build",
              "type": "string"
            },
            "pvs1_flowchart": {
              "additionalProperties": true,
              "title": "Pvs1 Flowchart",
              "type": "object"
            },
            "source_url": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Source Url"
            },
            "upstream_service": {
              "default": "AutoPVS1",
              "title": "Upstream Service",
              "type": "string"
            }
          },
          "required": [
            "genome_build",
            "cnv_info",
            "pvs1_flowchart"
          ],
          "title": "CNVMCPData",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "description": "Structured MCP tool error.",
          "properties": {
            "code": {
              "title": "Code",
              "type": "string"
            },
            "message": {
              "title": "Message",
              "type": "string"
            },
            "retryable": {
              "title": "Retryable",
              "type": "boolean"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            }
          },
          "required": [
            "code",
            "message",
            "retryable"
          ],
          "title": "MCPError",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "meta": {
      "description": "Common metadata on every MCP tool envelope.",
      "properties": {
        "recommended_citation": {
          "description": "Recommended citation for AutoPVS1 research-use outputs.",
          "properties": {
            "doi": {
              "default": "10.1002/humu.24051",
              "title": "Doi",
              "type": "string"
            },
            "pmid": {
              "default": "32442321",
              "title": "Pmid",
              "type": "string"
            },
            "text": {
              "default": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
              "title": "Text",
              "type": "string"
            },
            "url": {
              "default": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
              "title": "Url",
              "type": "string"
            }
          },
          "title": "RecommendedCitation",
          "type": "object"
        },
        "request_id": {
          "title": "Request Id",
          "type": "string"
        },
        "research_use_only": {
          "default": true,
          "title": "Research Use Only",
          "type": "boolean"
        },
        "server_version": {
          "default": "1.0.0",
          "title": "Server Version",
          "type": "string"
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.",
            "properties": {
              "code": {
                "title": "Code",
                "type": "string"
              },
              "message": {
                "title": "Message",
                "type": "string"
              }
            },
            "required": [
              "code",
              "message"
            ],
            "title": "MCPWarning",
            "type": "object"
          },
          "title": "Warnings",
          "type": "array"
        }
      },
      "title": "MCPMeta",
      "type": "object"
    },
    "ok": {
      "title": "Ok",
      "type": "boolean"
    }
  },
  "required": [
    "ok",
    "data",
    "error",
    "meta"
  ],
  "title": "CNVMCPEnvelope",
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

#### Output Schema

```json
{
  "description": "Envelope schema for ``get_server_capabilities``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "Compact first-turn MCP capabilities payload.",
          "properties": {
            "canonical_parameters": {
              "additionalProperties": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "title": "Canonical Parameters",
              "type": "object"
            },
            "compact_workflow": {
              "items": {
                "type": "string"
              },
              "title": "Compact Workflow",
              "type": "array"
            },
            "details_resource": {
              "title": "Details Resource",
              "type": "string"
            },
            "endpoint": {
              "title": "Endpoint",
              "type": "string"
            },
            "research_use_only": {
              "title": "Research Use Only",
              "type": "boolean"
            },
            "server": {
              "title": "Server",
              "type": "string"
            },
            "tool_summaries": {
              "additionalProperties": {
                "type": "string"
              },
              "title": "Tool Summaries",
              "type": "object"
            },
            "transport": {
              "title": "Transport",
              "type": "string"
            },
            "version": {
              "title": "Version",
              "type": "string"
            }
          },
          "required": [
            "server",
            "version",
            "transport",
            "endpoint",
            "research_use_only",
            "tool_summaries",
            "canonical_parameters",
            "compact_workflow",
            "details_resource"
          ],
          "title": "CompactCapabilitiesData",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "description": "Structured MCP tool error.",
          "properties": {
            "code": {
              "title": "Code",
              "type": "string"
            },
            "message": {
              "title": "Message",
              "type": "string"
            },
            "retryable": {
              "title": "Retryable",
              "type": "boolean"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            }
          },
          "required": [
            "code",
            "message",
            "retryable"
          ],
          "title": "MCPError",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "meta": {
      "description": "Common metadata on every MCP tool envelope.",
      "properties": {
        "recommended_citation": {
          "description": "Recommended citation for AutoPVS1 research-use outputs.",
          "properties": {
            "doi": {
              "default": "10.1002/humu.24051",
              "title": "Doi",
              "type": "string"
            },
            "pmid": {
              "default": "32442321",
              "title": "Pmid",
              "type": "string"
            },
            "text": {
              "default": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
              "title": "Text",
              "type": "string"
            },
            "url": {
              "default": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
              "title": "Url",
              "type": "string"
            }
          },
          "title": "RecommendedCitation",
          "type": "object"
        },
        "request_id": {
          "title": "Request Id",
          "type": "string"
        },
        "research_use_only": {
          "default": true,
          "title": "Research Use Only",
          "type": "boolean"
        },
        "server_version": {
          "default": "1.0.0",
          "title": "Server Version",
          "type": "string"
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.",
            "properties": {
              "code": {
                "title": "Code",
                "type": "string"
              },
              "message": {
                "title": "Message",
                "type": "string"
              }
            },
            "required": [
              "code",
              "message"
            ],
            "title": "MCPWarning",
            "type": "object"
          },
          "title": "Warnings",
          "type": "array"
        }
      },
      "title": "MCPMeta",
      "type": "object"
    },
    "ok": {
      "title": "Ok",
      "type": "boolean"
    }
  },
  "required": [
    "ok",
    "data",
    "error",
    "meta"
  ],
  "title": "CompactCapabilitiesMCPEnvelope",
  "type": "object"
}
```

### `get_variant_pvs1_data`

Use this to score one SNV/indel variant with AutoPVS1 PVS1 rules.

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
      "type": "string"
    },
    "variant_id": {
      "description": "Variant identifier, for example X-82763936-A-T.",
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

#### Output Schema

```json
{
  "description": "Envelope schema for ``get_variant_pvs1_data``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "MCP-presented variant data.",
          "properties": {
            "disease_mechanisms": {
              "items": {
                "additionalProperties": true,
                "type": "object"
              },
              "title": "Disease Mechanisms",
              "type": "array"
            },
            "genome_build": {
              "title": "Genome Build",
              "type": "string"
            },
            "pvs1_flowchart": {
              "additionalProperties": true,
              "title": "Pvs1 Flowchart",
              "type": "object"
            },
            "source_url": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Source Url"
            },
            "upstream_service": {
              "default": "AutoPVS1",
              "title": "Upstream Service",
              "type": "string"
            },
            "variant_info": {
              "additionalProperties": true,
              "title": "Variant Info",
              "type": "object"
            }
          },
          "required": [
            "genome_build",
            "variant_info",
            "pvs1_flowchart"
          ],
          "title": "VariantMCPData",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "description": "Structured MCP tool error.",
          "properties": {
            "code": {
              "title": "Code",
              "type": "string"
            },
            "message": {
              "title": "Message",
              "type": "string"
            },
            "retryable": {
              "title": "Retryable",
              "type": "boolean"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            }
          },
          "required": [
            "code",
            "message",
            "retryable"
          ],
          "title": "MCPError",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "meta": {
      "description": "Common metadata on every MCP tool envelope.",
      "properties": {
        "recommended_citation": {
          "description": "Recommended citation for AutoPVS1 research-use outputs.",
          "properties": {
            "doi": {
              "default": "10.1002/humu.24051",
              "title": "Doi",
              "type": "string"
            },
            "pmid": {
              "default": "32442321",
              "title": "Pmid",
              "type": "string"
            },
            "text": {
              "default": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
              "title": "Text",
              "type": "string"
            },
            "url": {
              "default": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
              "title": "Url",
              "type": "string"
            }
          },
          "title": "RecommendedCitation",
          "type": "object"
        },
        "request_id": {
          "title": "Request Id",
          "type": "string"
        },
        "research_use_only": {
          "default": true,
          "title": "Research Use Only",
          "type": "boolean"
        },
        "server_version": {
          "default": "1.0.0",
          "title": "Server Version",
          "type": "string"
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.",
            "properties": {
              "code": {
                "title": "Code",
                "type": "string"
              },
              "message": {
                "title": "Message",
                "type": "string"
              }
            },
            "required": [
              "code",
              "message"
            ],
            "title": "MCPWarning",
            "type": "object"
          },
          "title": "Warnings",
          "type": "array"
        }
      },
      "title": "MCPMeta",
      "type": "object"
    },
    "ok": {
      "title": "Ok",
      "type": "boolean"
    }
  },
  "required": [
    "ok",
    "data",
    "error",
    "meta"
  ],
  "title": "VariantMCPEnvelope",
  "type": "object"
}
```

### `search_variants`

Use this to search AutoPVS1 by gene symbol or variant text.

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
      "description": "Opaque integer-offset cursor returned as next_cursor."
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
    "query": {
      "description": "Gene symbol, HGVS text, or partial variant string.",
      "type": "string"
    }
  },
  "required": [
    "query"
  ],
  "type": "object"
}
```

#### Output Schema

```json
{
  "description": "Envelope schema for ``search_variants``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "MCP-presented search page.",
          "properties": {
            "genome_build": {
              "title": "Genome Build",
              "type": "string"
            },
            "next_cursor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Next Cursor"
            },
            "ordering": {
              "const": "upstream",
              "default": "upstream",
              "title": "Ordering",
              "type": "string"
            },
            "query": {
              "title": "Query",
              "type": "string"
            },
            "results": {
              "items": {
                "additionalProperties": true,
                "type": "object"
              },
              "title": "Results",
              "type": "array"
            },
            "returned_count": {
              "title": "Returned Count",
              "type": "integer"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            },
            "total_count": {
              "title": "Total Count",
              "type": "integer"
            }
          },
          "required": [
            "query",
            "genome_build",
            "total_count",
            "returned_count",
            "next_cursor"
          ],
          "title": "SearchMCPData",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "error": {
      "anyOf": [
        {
          "description": "Structured MCP tool error.",
          "properties": {
            "code": {
              "title": "Code",
              "type": "string"
            },
            "message": {
              "title": "Message",
              "type": "string"
            },
            "retryable": {
              "title": "Retryable",
              "type": "boolean"
            },
            "suggestions": {
              "items": {
                "type": "string"
              },
              "title": "Suggestions",
              "type": "array"
            }
          },
          "required": [
            "code",
            "message",
            "retryable"
          ],
          "title": "MCPError",
          "type": "object"
        },
        {
          "type": "null"
        }
      ]
    },
    "meta": {
      "description": "Common metadata on every MCP tool envelope.",
      "properties": {
        "recommended_citation": {
          "description": "Recommended citation for AutoPVS1 research-use outputs.",
          "properties": {
            "doi": {
              "default": "10.1002/humu.24051",
              "title": "Doi",
              "type": "string"
            },
            "pmid": {
              "default": "32442321",
              "title": "Pmid",
              "type": "string"
            },
            "text": {
              "default": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
              "title": "Text",
              "type": "string"
            },
            "url": {
              "default": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
              "title": "Url",
              "type": "string"
            }
          },
          "title": "RecommendedCitation",
          "type": "object"
        },
        "request_id": {
          "title": "Request Id",
          "type": "string"
        },
        "research_use_only": {
          "default": true,
          "title": "Research Use Only",
          "type": "boolean"
        },
        "server_version": {
          "default": "1.0.0",
          "title": "Server Version",
          "type": "string"
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.",
            "properties": {
              "code": {
                "title": "Code",
                "type": "string"
              },
              "message": {
                "title": "Message",
                "type": "string"
              }
            },
            "required": [
              "code",
              "message"
            ],
            "title": "MCPWarning",
            "type": "object"
          },
          "title": "Warnings",
          "type": "array"
        }
      },
      "title": "MCPMeta",
      "type": "object"
    },
    "ok": {
      "title": "Ok",
      "type": "boolean"
    }
  },
  "required": [
    "ok",
    "data",
    "error",
    "meta"
  ],
  "title": "SearchMCPEnvelope",
  "type": "object"
}
```

## Resources

- `autopvs1-link://cache/statistics` - Read-only snapshot of in-memory cache statistics.
- `autopvs1-link://capabilities` - Detailed MCP usage guidance, examples, limitations, and citation.
