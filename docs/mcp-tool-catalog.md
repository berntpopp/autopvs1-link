# MCP Tool Catalog

Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`.

## Tools

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
    },
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "meta_mode": {
      "default": "full",
      "description": "Metadata detail level: full, compact, or minimal.",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "standard",
      "description": "Response detail level: summary, standard, or full.",
      "enum": [
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
              "description": "Typed copy-number variant information exposed through MCP.",
              "properties": {
                "cnv_id": {
                  "title": "Cnv Id",
                  "type": "string"
                },
                "cnv_type": {
                  "title": "Cnv Type",
                  "type": "string"
                },
                "coordinates": {
                  "title": "Coordinates",
                  "type": "string"
                },
                "gene_symbol": {
                  "title": "Gene Symbol",
                  "type": "string"
                },
                "size": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Size"
                }
              },
              "required": [
                "cnv_id",
                "cnv_type",
                "gene_symbol",
                "coordinates"
              ],
              "title": "CNVInfoMCP",
              "type": "object"
            },
            "disease_mechanisms": {
              "items": {
                "description": "Typed disease mechanism row from AutoPVS1.",
                "properties": {
                  "adjusted_strength": {
                    "title": "Adjusted Strength",
                    "type": "string"
                  },
                  "clinical_validity": {
                    "title": "Clinical Validity",
                    "type": "string"
                  },
                  "consideration": {
                    "title": "Consideration",
                    "type": "string"
                  },
                  "disease": {
                    "title": "Disease",
                    "type": "string"
                  },
                  "disease_url": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Disease Url"
                  },
                  "gene": {
                    "title": "Gene",
                    "type": "string"
                  },
                  "gene_url": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Gene Url"
                  },
                  "inheritance": {
                    "title": "Inheritance",
                    "type": "string"
                  }
                },
                "required": [
                  "gene",
                  "disease",
                  "inheritance",
                  "clinical_validity",
                  "consideration",
                  "adjusted_strength"
                ],
                "title": "DiseaseMechanismMCP",
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
              "description": "Typed PVS1 flowchart decision path and outcome.",
              "properties": {
                "decision_tree": {
                  "items": {
                    "description": "One typed step in the PVS1 decision flowchart.",
                    "properties": {
                      "code": {
                        "title": "Code",
                        "type": "string"
                      },
                      "description": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Description"
                      },
                      "note_id": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Note Id"
                      },
                      "note_text": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Note Text"
                      }
                    },
                    "required": [
                      "code"
                    ],
                    "title": "FlowchartStepMCP",
                    "type": "object"
                  },
                  "title": "Decision Tree",
                  "type": "array"
                },
                "decision_tree_raw": {
                  "anyOf": [
                    {
                      "items": {
                        "additionalProperties": true,
                        "type": "object"
                      },
                      "type": "array"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Decision Tree Raw"
                },
                "final_strength": {
                  "title": "Final Strength",
                  "type": "string"
                },
                "final_strength_source": {
                  "default": "asserted",
                  "enum": [
                    "asserted",
                    "inferred"
                  ],
                  "title": "Final Strength Source",
                  "type": "string"
                },
                "notes": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "title": "Notes",
                  "type": "object"
                },
                "preliminary_decision_path": {
                  "title": "Preliminary Decision Path",
                  "type": "string"
                }
              },
              "required": [
                "preliminary_decision_path",
                "final_strength"
              ],
              "title": "PVS1FlowchartMCP",
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

### `get_cnvs_pvs1_data_bulk`

Score 1-10 CNVs in one call.

Prefer this over ``get_cnv_pvs1_data`` when you have 2+ CNV IDs.
Same semantics as ``get_variants_pvs1_data_bulk``: sequential
server-side, respects upstream rate limit + cache; per-item
``{ok, input, data, error}``; output items preserve input order;
``response_mode`` and ``include_unmet`` apply per item; ``meta_mode``
applies to the outer envelope only. Per-item failures do not stop
the batch unless ``continue_on_error=false``.

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
      "default": "full",
      "description": "Top-level metadata detail level.",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "standard",
      "description": "Response detail level applied to each item.",
      "enum": [
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

#### Output Schema

```json
{
  "description": "Envelope schema for ``get_cnvs_pvs1_data_bulk``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "Aggregate payload for ``get_cnvs_pvs1_data_bulk``.\n\nSame semantics as :class:`BulkVariantsMCPData`.",
          "properties": {
            "attempted": {
              "title": "Attempted",
              "type": "integer"
            },
            "failed": {
              "title": "Failed",
              "type": "integer"
            },
            "items": {
              "items": {
                "description": "Per-item result for a bulk CNV PVS1 request.",
                "properties": {
                  "data": {
                    "anyOf": [
                      {
                        "description": "MCP-presented CNV data.",
                        "properties": {
                          "cnv_info": {
                            "description": "Typed copy-number variant information exposed through MCP.",
                            "properties": {
                              "cnv_id": {
                                "title": "Cnv Id",
                                "type": "string"
                              },
                              "cnv_type": {
                                "title": "Cnv Type",
                                "type": "string"
                              },
                              "coordinates": {
                                "title": "Coordinates",
                                "type": "string"
                              },
                              "gene_symbol": {
                                "title": "Gene Symbol",
                                "type": "string"
                              },
                              "size": {
                                "anyOf": [
                                  {
                                    "type": "integer"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Size"
                              }
                            },
                            "required": [
                              "cnv_id",
                              "cnv_type",
                              "gene_symbol",
                              "coordinates"
                            ],
                            "title": "CNVInfoMCP",
                            "type": "object"
                          },
                          "disease_mechanisms": {
                            "items": {
                              "description": "Typed disease mechanism row from AutoPVS1.",
                              "properties": {
                                "adjusted_strength": {
                                  "title": "Adjusted Strength",
                                  "type": "string"
                                },
                                "clinical_validity": {
                                  "title": "Clinical Validity",
                                  "type": "string"
                                },
                                "consideration": {
                                  "title": "Consideration",
                                  "type": "string"
                                },
                                "disease": {
                                  "title": "Disease",
                                  "type": "string"
                                },
                                "disease_url": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null,
                                  "title": "Disease Url"
                                },
                                "gene": {
                                  "title": "Gene",
                                  "type": "string"
                                },
                                "gene_url": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null,
                                  "title": "Gene Url"
                                },
                                "inheritance": {
                                  "title": "Inheritance",
                                  "type": "string"
                                }
                              },
                              "required": [
                                "gene",
                                "disease",
                                "inheritance",
                                "clinical_validity",
                                "consideration",
                                "adjusted_strength"
                              ],
                              "title": "DiseaseMechanismMCP",
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
                            "description": "Typed PVS1 flowchart decision path and outcome.",
                            "properties": {
                              "decision_tree": {
                                "items": {
                                  "description": "One typed step in the PVS1 decision flowchart.",
                                  "properties": {
                                    "code": {
                                      "title": "Code",
                                      "type": "string"
                                    },
                                    "description": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Description"
                                    },
                                    "note_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Note Id"
                                    },
                                    "note_text": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Note Text"
                                    }
                                  },
                                  "required": [
                                    "code"
                                  ],
                                  "title": "FlowchartStepMCP",
                                  "type": "object"
                                },
                                "title": "Decision Tree",
                                "type": "array"
                              },
                              "decision_tree_raw": {
                                "anyOf": [
                                  {
                                    "items": {
                                      "additionalProperties": true,
                                      "type": "object"
                                    },
                                    "type": "array"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Decision Tree Raw"
                              },
                              "final_strength": {
                                "title": "Final Strength",
                                "type": "string"
                              },
                              "final_strength_source": {
                                "default": "asserted",
                                "enum": [
                                  "asserted",
                                  "inferred"
                                ],
                                "title": "Final Strength Source",
                                "type": "string"
                              },
                              "notes": {
                                "additionalProperties": {
                                  "type": "string"
                                },
                                "title": "Notes",
                                "type": "object"
                              },
                              "preliminary_decision_path": {
                                "title": "Preliminary Decision Path",
                                "type": "string"
                              }
                            },
                            "required": [
                              "preliminary_decision_path",
                              "final_strength"
                            ],
                            "title": "PVS1FlowchartMCP",
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
                    ],
                    "default": null
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
                    ],
                    "default": null
                  },
                  "input": {
                    "description": "One item in a bulk CNV PVS1 request.",
                    "properties": {
                      "cnv_id": {
                        "description": "AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form.",
                        "maxLength": 128,
                        "minLength": 1,
                        "title": "Cnv Id",
                        "type": "string"
                      },
                      "genome_build": {
                        "description": "Genome build: hg19 or hg38. Invalid values yield a per-item error.",
                        "title": "Genome Build",
                        "type": "string"
                      }
                    },
                    "required": [
                      "genome_build",
                      "cnv_id"
                    ],
                    "title": "BulkCNVPVS1InputItem",
                    "type": "object"
                  },
                  "ok": {
                    "title": "Ok",
                    "type": "boolean"
                  }
                },
                "required": [
                  "ok",
                  "input"
                ],
                "title": "BulkCNVPVS1ResultItem",
                "type": "object"
              },
              "title": "Items",
              "type": "array"
            },
            "skipped": {
              "title": "Skipped",
              "type": "integer"
            },
            "succeeded": {
              "title": "Succeeded",
              "type": "integer"
            },
            "total": {
              "title": "Total",
              "type": "integer"
            }
          },
          "required": [
            "total",
            "attempted",
            "skipped",
            "succeeded",
            "failed"
          ],
          "title": "BulkCNVsMCPData",
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
  "title": "BulkCNVsMCPEnvelope",
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
                "description": "Compact ordered workflow guidance for first-turn discovery.",
                "properties": {
                  "step": {
                    "title": "Step",
                    "type": "string"
                  },
                  "when": {
                    "title": "When",
                    "type": "string"
                  }
                },
                "required": [
                  "step",
                  "when"
                ],
                "title": "WorkflowStepMCP",
                "type": "object"
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
                "description": "Compact MCP tool summary for first-turn discovery.",
                "properties": {
                  "example": {
                    "additionalProperties": true,
                    "title": "Example",
                    "type": "object"
                  },
                  "purpose": {
                    "title": "Purpose",
                    "type": "string"
                  }
                },
                "required": [
                  "purpose"
                ],
                "title": "ToolSummaryMCP",
                "type": "object"
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

### `get_server_health`

Return local MCP server health without contacting AutoPVS1 upstream.

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
  "description": "Envelope schema for ``get_server_health``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "Local MCP server health status.",
          "properties": {
            "destructive_tools_enabled": {
              "default": false,
              "title": "Destructive Tools Enabled",
              "type": "boolean"
            },
            "server": {
              "default": "AutoPVS1 Link",
              "title": "Server",
              "type": "string"
            },
            "status": {
              "const": "ok",
              "default": "ok",
              "title": "Status",
              "type": "string"
            },
            "upstream_checked": {
              "default": false,
              "title": "Upstream Checked",
              "type": "boolean"
            },
            "upstream_status": {
              "const": "not_checked",
              "default": "not_checked",
              "title": "Upstream Status",
              "type": "string"
            },
            "version": {
              "default": "1.0.0",
              "title": "Version",
              "type": "string"
            }
          },
          "title": "HealthData",
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
  "title": "HealthMCPEnvelope",
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
    "include_unmet": {
      "default": true,
      "description": "Include disease-mechanism rows with adjusted_strength=Unmet.",
      "type": "boolean"
    },
    "meta_mode": {
      "default": "full",
      "description": "Metadata detail level: full, compact, or minimal.",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "standard",
      "description": "Response detail level: summary, standard, or full.",
      "enum": [
        "summary",
        "standard",
        "full"
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
                "description": "Typed disease mechanism row from AutoPVS1.",
                "properties": {
                  "adjusted_strength": {
                    "title": "Adjusted Strength",
                    "type": "string"
                  },
                  "clinical_validity": {
                    "title": "Clinical Validity",
                    "type": "string"
                  },
                  "consideration": {
                    "title": "Consideration",
                    "type": "string"
                  },
                  "disease": {
                    "title": "Disease",
                    "type": "string"
                  },
                  "disease_url": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Disease Url"
                  },
                  "gene": {
                    "title": "Gene",
                    "type": "string"
                  },
                  "gene_url": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Gene Url"
                  },
                  "inheritance": {
                    "title": "Inheritance",
                    "type": "string"
                  }
                },
                "required": [
                  "gene",
                  "disease",
                  "inheritance",
                  "clinical_validity",
                  "consideration",
                  "adjusted_strength"
                ],
                "title": "DiseaseMechanismMCP",
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
              "description": "Typed PVS1 flowchart decision path and outcome.",
              "properties": {
                "decision_tree": {
                  "items": {
                    "description": "One typed step in the PVS1 decision flowchart.",
                    "properties": {
                      "code": {
                        "title": "Code",
                        "type": "string"
                      },
                      "description": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Description"
                      },
                      "note_id": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Note Id"
                      },
                      "note_text": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Note Text"
                      }
                    },
                    "required": [
                      "code"
                    ],
                    "title": "FlowchartStepMCP",
                    "type": "object"
                  },
                  "title": "Decision Tree",
                  "type": "array"
                },
                "decision_tree_raw": {
                  "anyOf": [
                    {
                      "items": {
                        "additionalProperties": true,
                        "type": "object"
                      },
                      "type": "array"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Decision Tree Raw"
                },
                "final_strength": {
                  "title": "Final Strength",
                  "type": "string"
                },
                "final_strength_source": {
                  "default": "asserted",
                  "enum": [
                    "asserted",
                    "inferred"
                  ],
                  "title": "Final Strength Source",
                  "type": "string"
                },
                "notes": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "title": "Notes",
                  "type": "object"
                },
                "preliminary_decision_path": {
                  "title": "Preliminary Decision Path",
                  "type": "string"
                }
              },
              "required": [
                "preliminary_decision_path",
                "final_strength"
              ],
              "title": "PVS1FlowchartMCP",
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
              "description": "Typed variant information exposed through MCP.",
              "properties": {
                "chgvs": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Chgvs"
                },
                "exon": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Exon"
                },
                "external_links": {
                  "additionalProperties": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "title": "External Links",
                  "type": "object"
                },
                "external_links_raw": {
                  "anyOf": [
                    {
                      "additionalProperties": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "External Links Raw"
                },
                "gene_symbol": {
                  "title": "Gene Symbol",
                  "type": "string"
                },
                "gene_url": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Gene Url"
                },
                "haploinsufficiency": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Haploinsufficiency"
                },
                "haploinsufficiency_url": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Haploinsufficiency Url"
                },
                "intron": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Intron"
                },
                "phgvs": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Phgvs"
                },
                "pli_score": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Pli Score"
                },
                "pli_score_display": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null,
                  "title": "Pli Score Display"
                },
                "variant_id": {
                  "title": "Variant Id",
                  "type": "string"
                },
                "variant_type": {
                  "title": "Variant Type",
                  "type": "string"
                }
              },
              "required": [
                "variant_id",
                "variant_type",
                "gene_symbol"
              ],
              "title": "VariantInfoMCP",
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

### `get_variants_pvs1_data_bulk`

Score 1-10 SNV/indel variants in one call.

Prefer this over ``get_variant_pvs1_data`` when you have 2+ variant
IDs of the same kind. Items run sequentially server-side and respect
the upstream rate limit (default ~1 req/s) plus the existing cache,
so a fully uncached 10-item batch can take ~10s wall time.

Per-item envelope: each result has ``{ok, input, data, error}``.
Output items preserve input order. ``response_mode`` and
``include_unmet`` apply per item; ``meta_mode`` applies to the outer
envelope only. Per-item input or upstream failures do not stop the
batch unless ``continue_on_error=false``. Bulk dispatch errors
(malformed ``items``) use error code ``invalid_bulk_input``.

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
      "default": "full",
      "description": "Top-level metadata detail level.",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "response_mode": {
      "default": "standard",
      "description": "Response detail level applied to each item.",
      "enum": [
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

#### Output Schema

```json
{
  "description": "Envelope schema for ``get_variants_pvs1_data_bulk``.",
  "properties": {
    "data": {
      "anyOf": [
        {
          "description": "Aggregate payload for ``get_variants_pvs1_data_bulk``.\n\n``total`` is always the requested item count. ``attempted`` is the count\nthat ran (= ``len(items)``). ``skipped`` is the count that the server did\nnot attempt because ``continue_on_error=False`` broke the loop early.\nInvariant: ``attempted == succeeded + failed`` and ``total == attempted + skipped``.",
          "properties": {
            "attempted": {
              "title": "Attempted",
              "type": "integer"
            },
            "failed": {
              "title": "Failed",
              "type": "integer"
            },
            "items": {
              "items": {
                "description": "Per-item result for a bulk variant PVS1 request.",
                "properties": {
                  "data": {
                    "anyOf": [
                      {
                        "description": "MCP-presented variant data.",
                        "properties": {
                          "disease_mechanisms": {
                            "items": {
                              "description": "Typed disease mechanism row from AutoPVS1.",
                              "properties": {
                                "adjusted_strength": {
                                  "title": "Adjusted Strength",
                                  "type": "string"
                                },
                                "clinical_validity": {
                                  "title": "Clinical Validity",
                                  "type": "string"
                                },
                                "consideration": {
                                  "title": "Consideration",
                                  "type": "string"
                                },
                                "disease": {
                                  "title": "Disease",
                                  "type": "string"
                                },
                                "disease_url": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null,
                                  "title": "Disease Url"
                                },
                                "gene": {
                                  "title": "Gene",
                                  "type": "string"
                                },
                                "gene_url": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null,
                                  "title": "Gene Url"
                                },
                                "inheritance": {
                                  "title": "Inheritance",
                                  "type": "string"
                                }
                              },
                              "required": [
                                "gene",
                                "disease",
                                "inheritance",
                                "clinical_validity",
                                "consideration",
                                "adjusted_strength"
                              ],
                              "title": "DiseaseMechanismMCP",
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
                            "description": "Typed PVS1 flowchart decision path and outcome.",
                            "properties": {
                              "decision_tree": {
                                "items": {
                                  "description": "One typed step in the PVS1 decision flowchart.",
                                  "properties": {
                                    "code": {
                                      "title": "Code",
                                      "type": "string"
                                    },
                                    "description": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Description"
                                    },
                                    "note_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Note Id"
                                    },
                                    "note_text": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ],
                                      "default": null,
                                      "title": "Note Text"
                                    }
                                  },
                                  "required": [
                                    "code"
                                  ],
                                  "title": "FlowchartStepMCP",
                                  "type": "object"
                                },
                                "title": "Decision Tree",
                                "type": "array"
                              },
                              "decision_tree_raw": {
                                "anyOf": [
                                  {
                                    "items": {
                                      "additionalProperties": true,
                                      "type": "object"
                                    },
                                    "type": "array"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Decision Tree Raw"
                              },
                              "final_strength": {
                                "title": "Final Strength",
                                "type": "string"
                              },
                              "final_strength_source": {
                                "default": "asserted",
                                "enum": [
                                  "asserted",
                                  "inferred"
                                ],
                                "title": "Final Strength Source",
                                "type": "string"
                              },
                              "notes": {
                                "additionalProperties": {
                                  "type": "string"
                                },
                                "title": "Notes",
                                "type": "object"
                              },
                              "preliminary_decision_path": {
                                "title": "Preliminary Decision Path",
                                "type": "string"
                              }
                            },
                            "required": [
                              "preliminary_decision_path",
                              "final_strength"
                            ],
                            "title": "PVS1FlowchartMCP",
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
                            "description": "Typed variant information exposed through MCP.",
                            "properties": {
                              "chgvs": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Chgvs"
                              },
                              "exon": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Exon"
                              },
                              "external_links": {
                                "additionalProperties": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ]
                                },
                                "title": "External Links",
                                "type": "object"
                              },
                              "external_links_raw": {
                                "anyOf": [
                                  {
                                    "additionalProperties": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "type": "null"
                                        }
                                      ]
                                    },
                                    "type": "object"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "External Links Raw"
                              },
                              "gene_symbol": {
                                "title": "Gene Symbol",
                                "type": "string"
                              },
                              "gene_url": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Gene Url"
                              },
                              "haploinsufficiency": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Haploinsufficiency"
                              },
                              "haploinsufficiency_url": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Haploinsufficiency Url"
                              },
                              "intron": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Intron"
                              },
                              "phgvs": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Phgvs"
                              },
                              "pli_score": {
                                "anyOf": [
                                  {
                                    "type": "number"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Pli Score"
                              },
                              "pli_score_display": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ],
                                "default": null,
                                "title": "Pli Score Display"
                              },
                              "variant_id": {
                                "title": "Variant Id",
                                "type": "string"
                              },
                              "variant_type": {
                                "title": "Variant Type",
                                "type": "string"
                              }
                            },
                            "required": [
                              "variant_id",
                              "variant_type",
                              "gene_symbol"
                            ],
                            "title": "VariantInfoMCP",
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
                    ],
                    "default": null
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
                    ],
                    "default": null
                  },
                  "input": {
                    "description": "One item in a bulk variant PVS1 request.",
                    "properties": {
                      "genome_build": {
                        "description": "Genome build: hg19 or hg38. Invalid values yield a per-item error.",
                        "title": "Genome Build",
                        "type": "string"
                      },
                      "variant_id": {
                        "description": "AutoPVS1 variant ID, for example X-82763936-A-T.",
                        "maxLength": 128,
                        "minLength": 1,
                        "title": "Variant Id",
                        "type": "string"
                      }
                    },
                    "required": [
                      "genome_build",
                      "variant_id"
                    ],
                    "title": "BulkVariantPVS1InputItem",
                    "type": "object"
                  },
                  "ok": {
                    "title": "Ok",
                    "type": "boolean"
                  }
                },
                "required": [
                  "ok",
                  "input"
                ],
                "title": "BulkVariantPVS1ResultItem",
                "type": "object"
              },
              "title": "Items",
              "type": "array"
            },
            "skipped": {
              "title": "Skipped",
              "type": "integer"
            },
            "succeeded": {
              "title": "Succeeded",
              "type": "integer"
            },
            "total": {
              "title": "Total",
              "type": "integer"
            }
          },
          "required": [
            "total",
            "attempted",
            "skipped",
            "succeeded",
            "failed"
          ],
          "title": "BulkVariantsMCPData",
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
  "title": "BulkVariantsMCPEnvelope",
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
    "meta_mode": {
      "default": "full",
      "description": "Metadata detail level: full, compact, or minimal.",
      "enum": [
        "full",
        "compact",
        "minimal"
      ],
      "type": "string"
    },
    "query": {
      "description": "Gene symbol, HGVS text, or partial variant string.",
      "type": "string"
    },
    "response_mode": {
      "default": "standard",
      "description": "Response detail level: summary, standard, or full.",
      "enum": [
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
                "description": "Typed AutoPVS1 search result row.",
                "properties": {
                  "gene": {
                    "title": "Gene",
                    "type": "string"
                  },
                  "genome_build": {
                    "title": "Genome Build",
                    "type": "string"
                  },
                  "url": {
                    "title": "Url",
                    "type": "string"
                  },
                  "variant_id": {
                    "title": "Variant Id",
                    "type": "string"
                  },
                  "variant_type": {
                    "title": "Variant Type",
                    "type": "string"
                  }
                },
                "required": [
                  "variant_id",
                  "gene",
                  "variant_type",
                  "genome_build",
                  "url"
                ],
                "title": "SearchResultMCP",
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

## Resources

- `autopvs1-link://cache/statistics` - Read-only snapshot of in-memory cache hit/miss/eviction counts and timing per cached service method (variant, CNV, search).
- `autopvs1-link://capabilities` - Detailed MCP usage guidance: accepted formats, examples, search behavior, error envelope, stable error and warning codes, cache statistics URI, destructive-tool gating, citation, and known upstream limitations.
