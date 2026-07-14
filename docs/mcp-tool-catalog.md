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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "result": {
      "description": "MCP-presented CNV data.\n\n``pvs1_flowchart`` is required in summary/standard/full modes but\nomitted entirely when ``response_mode='ids_only'`` returns just the\nupstream identifier.",
      "properties": {
        "cnv_info": {
          "description": "Typed copy-number variant information exposed through MCP.\n\nOnly ``cnv_id`` is required at the contract level; the other fields\nare dropped when ``response_mode='ids_only'``.",
          "properties": {
            "cnv_id": {
              "title": "Cnv Id",
              "type": "string"
            },
            "cnv_type": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Cnv Type"
            },
            "coordinates": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Coordinates"
            },
            "gene_symbol": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Gene Symbol"
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
            "cnv_id"
          ],
          "title": "CNVInfoMCP",
          "type": "object"
        },
        "disease_mechanisms": {
          "items": {
            "description": "Typed disease mechanism row from AutoPVS1.\n\n``disease`` is a scraped free-text disease name (from AutoPVS1's\nClinGen-sourced gene-disease table) \u2014 the same class of surface as\nclingen-link's ``get_gene_validity /assertions/*/disease_name`` \u2014 so it\nships as ``untrusted_text``. ``gene``/``inheritance``/``clinical_validity``\n/``consideration``/``adjusted_strength`` are short controlled-vocabulary\nvalues (HGNC symbol; ClinGen validity/inheritance/PVS1-adjustment\ncategories), not free prose.",
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
                "description": "External prose represented as typed data with digest and provenance.",
                "properties": {
                  "kind": {
                    "const": "untrusted_text",
                    "default": "untrusted_text",
                    "title": "Kind",
                    "type": "string"
                  },
                  "provenance": {
                    "description": "Source identity for one fenced external text object.",
                    "properties": {
                      "record_id": {
                        "title": "Record Id",
                        "type": "string"
                      },
                      "retrieved_at": {
                        "format": "date-time",
                        "title": "Retrieved At",
                        "type": "string"
                      },
                      "source": {
                        "title": "Source",
                        "type": "string"
                      }
                    },
                    "required": [
                      "source",
                      "record_id",
                      "retrieved_at"
                    ],
                    "title": "UntrustedTextProvenance",
                    "type": "object"
                  },
                  "raw_sha256": {
                    "pattern": "^[0-9a-f]{64}$",
                    "title": "Raw Sha256",
                    "type": "string"
                  },
                  "text": {
                    "title": "Text",
                    "type": "string"
                  }
                },
                "required": [
                  "text",
                  "provenance",
                  "raw_sha256"
                ],
                "title": "UntrustedText",
                "type": "object"
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
          "anyOf": [
            {
              "description": "Typed PVS1 flowchart decision path and outcome.\n\n``decision_tree`` is the single canonical carrier of every scraped\ncriterion description (``code``) and its hoisted footnote\n(``note_text``). Response-Envelope v1.1 forbids the same upstream\nprose in more than one field (even when both copies are fenced), so\nthere is deliberately no ``notes`` legend dict and no\n``decision_tree_raw`` audit copy \u2014 both re-embedded prose that\n``decision_tree`` already carries. A caller that needs the raw\n``#N -> prose`` legend reads it off ``decision_tree[*].note_id`` +\n``note_text``.\n\n``terminal_note`` is the one-line rationale for the verdict, hoisted\nfrom the leaf step's note_text (or ``notes[preliminary_decision_path]``\nwhen the decision tree is empty). Populated ONLY in ``summary`` mode\n(where ``decision_tree`` is stripped, so it duplicates nothing) for\ncallers that need to explain non-Strong / non-Very-Strong outcomes\nwithout re-fetching the full decision tree. Absent when the upstream\nnote is empty or the verdict is unambiguous (PVS1_Strong /\nPVS1_Very_Strong).\n\n``path_gloss`` is a one-line, deterministic compression of the\ndecision-tree branch the variant traversed plus the terminal strength\n(ASCII ``->`` separated). It embeds the scraped node text, so to avoid\nduplicating ``decision_tree[*].code`` it is emitted ONLY in ``summary``\nmode \u2014 the tier where ``decision_tree`` is absent and the gloss is the\nsole prose carrier. Built only from upstream scraped node text \u2014 no\nhand-authored clinical mappings.\n\n``terminal_note`` and ``path_gloss`` ship as ``untrusted_text`` objects\n(Response-Envelope v1.1), the same as each ``decision_tree`` step's\n``code`` / ``note_text``.",
              "properties": {
                "decision_tree": {
                  "items": {
                    "description": "One typed step in the PVS1 decision flowchart.\n\n``code``, ``description``, and ``note_text`` are AutoPVS1's own scraped\nHTML prose (low-trust provenance: autopvs1.bgi.com) and ship as the\nResponse-Envelope v1.1 ``untrusted_text`` object, never a bare string.\n``note_id`` is a short upstream marker (``#1``, ``#2``, ...), not prose.",
                    "properties": {
                      "code": {
                        "description": "External prose represented as typed data with digest and provenance.",
                        "properties": {
                          "kind": {
                            "const": "untrusted_text",
                            "default": "untrusted_text",
                            "title": "Kind",
                            "type": "string"
                          },
                          "provenance": {
                            "description": "Source identity for one fenced external text object.",
                            "properties": {
                              "record_id": {
                                "title": "Record Id",
                                "type": "string"
                              },
                              "retrieved_at": {
                                "format": "date-time",
                                "title": "Retrieved At",
                                "type": "string"
                              },
                              "source": {
                                "title": "Source",
                                "type": "string"
                              }
                            },
                            "required": [
                              "source",
                              "record_id",
                              "retrieved_at"
                            ],
                            "title": "UntrustedTextProvenance",
                            "type": "object"
                          },
                          "raw_sha256": {
                            "pattern": "^[0-9a-f]{64}$",
                            "title": "Raw Sha256",
                            "type": "string"
                          },
                          "text": {
                            "title": "Text",
                            "type": "string"
                          }
                        },
                        "required": [
                          "text",
                          "provenance",
                          "raw_sha256"
                        ],
                        "title": "UntrustedText",
                        "type": "object"
                      },
                      "description": {
                        "anyOf": [
                          {
                            "description": "External prose represented as typed data with digest and provenance.",
                            "properties": {
                              "kind": {
                                "const": "untrusted_text",
                                "default": "untrusted_text",
                                "title": "Kind",
                                "type": "string"
                              },
                              "provenance": {
                                "description": "Source identity for one fenced external text object.",
                                "properties": {
                                  "record_id": {
                                    "title": "Record Id",
                                    "type": "string"
                                  },
                                  "retrieved_at": {
                                    "format": "date-time",
                                    "title": "Retrieved At",
                                    "type": "string"
                                  },
                                  "source": {
                                    "title": "Source",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "source",
                                  "record_id",
                                  "retrieved_at"
                                ],
                                "title": "UntrustedTextProvenance",
                                "type": "object"
                              },
                              "raw_sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "title": "Raw Sha256",
                                "type": "string"
                              },
                              "text": {
                                "title": "Text",
                                "type": "string"
                              }
                            },
                            "required": [
                              "text",
                              "provenance",
                              "raw_sha256"
                            ],
                            "title": "UntrustedText",
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null
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
                            "description": "External prose represented as typed data with digest and provenance.",
                            "properties": {
                              "kind": {
                                "const": "untrusted_text",
                                "default": "untrusted_text",
                                "title": "Kind",
                                "type": "string"
                              },
                              "provenance": {
                                "description": "Source identity for one fenced external text object.",
                                "properties": {
                                  "record_id": {
                                    "title": "Record Id",
                                    "type": "string"
                                  },
                                  "retrieved_at": {
                                    "format": "date-time",
                                    "title": "Retrieved At",
                                    "type": "string"
                                  },
                                  "source": {
                                    "title": "Source",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "source",
                                  "record_id",
                                  "retrieved_at"
                                ],
                                "title": "UntrustedTextProvenance",
                                "type": "object"
                              },
                              "raw_sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "title": "Raw Sha256",
                                "type": "string"
                              },
                              "text": {
                                "title": "Text",
                                "type": "string"
                              }
                            },
                            "required": [
                              "text",
                              "provenance",
                              "raw_sha256"
                            ],
                            "title": "UntrustedText",
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null
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
                "path_gloss": {
                  "anyOf": [
                    {
                      "description": "External prose represented as typed data with digest and provenance.",
                      "properties": {
                        "kind": {
                          "const": "untrusted_text",
                          "default": "untrusted_text",
                          "title": "Kind",
                          "type": "string"
                        },
                        "provenance": {
                          "description": "Source identity for one fenced external text object.",
                          "properties": {
                            "record_id": {
                              "title": "Record Id",
                              "type": "string"
                            },
                            "retrieved_at": {
                              "format": "date-time",
                              "title": "Retrieved At",
                              "type": "string"
                            },
                            "source": {
                              "title": "Source",
                              "type": "string"
                            }
                          },
                          "required": [
                            "source",
                            "record_id",
                            "retrieved_at"
                          ],
                          "title": "UntrustedTextProvenance",
                          "type": "object"
                        },
                        "raw_sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "title": "Raw Sha256",
                          "type": "string"
                        },
                        "text": {
                          "title": "Text",
                          "type": "string"
                        }
                      },
                      "required": [
                        "text",
                        "provenance",
                        "raw_sha256"
                      ],
                      "title": "UntrustedText",
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null
                },
                "preliminary_decision_path": {
                  "title": "Preliminary Decision Path",
                  "type": "string"
                },
                "terminal_note": {
                  "anyOf": [
                    {
                      "description": "External prose represented as typed data with digest and provenance.",
                      "properties": {
                        "kind": {
                          "const": "untrusted_text",
                          "default": "untrusted_text",
                          "title": "Kind",
                          "type": "string"
                        },
                        "provenance": {
                          "description": "Source identity for one fenced external text object.",
                          "properties": {
                            "record_id": {
                              "title": "Record Id",
                              "type": "string"
                            },
                            "retrieved_at": {
                              "format": "date-time",
                              "title": "Retrieved At",
                              "type": "string"
                            },
                            "source": {
                              "title": "Source",
                              "type": "string"
                            }
                          },
                          "required": [
                            "source",
                            "record_id",
                            "retrieved_at"
                          ],
                          "title": "UntrustedTextProvenance",
                          "type": "object"
                        },
                        "raw_sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "title": "Raw Sha256",
                          "type": "string"
                        },
                        "text": {
                          "title": "Text",
                          "type": "string"
                        }
                      },
                      "required": [
                        "text",
                        "provenance",
                        "raw_sha256"
                      ],
                      "title": "UntrustedText",
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null
                }
              },
              "required": [
                "preliminary_decision_path",
                "final_strength"
              ],
              "title": "PVS1FlowchartMCP",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
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
        "cnv_info"
      ],
      "type": "object"
    },
    "retryable": {
      "type": "boolean"
    },
    "success": {
      "type": "boolean"
    }
  },
  "required": [
    "success",
    "_meta"
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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "attempted": {
      "title": "Attempted",
      "type": "integer"
    },
    "error_code": {
      "type": "string"
    },
    "failed": {
      "title": "Failed",
      "type": "integer"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "results": {
      "items": {
        "description": "Per-item result for a bulk CNV PVS1 request.",
        "properties": {
          "data": {
            "anyOf": [
              {
                "description": "MCP-presented CNV data.\n\n``pvs1_flowchart`` is required in summary/standard/full modes but\nomitted entirely when ``response_mode='ids_only'`` returns just the\nupstream identifier.",
                "properties": {
                  "cnv_info": {
                    "description": "Typed copy-number variant information exposed through MCP.\n\nOnly ``cnv_id`` is required at the contract level; the other fields\nare dropped when ``response_mode='ids_only'``.",
                    "properties": {
                      "cnv_id": {
                        "title": "Cnv Id",
                        "type": "string"
                      },
                      "cnv_type": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Cnv Type"
                      },
                      "coordinates": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Coordinates"
                      },
                      "gene_symbol": {
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Gene Symbol"
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
                      "cnv_id"
                    ],
                    "title": "CNVInfoMCP",
                    "type": "object"
                  },
                  "disease_mechanisms": {
                    "items": {
                      "description": "Typed disease mechanism row from AutoPVS1.\n\n``disease`` is a scraped free-text disease name (from AutoPVS1's\nClinGen-sourced gene-disease table) \u2014 the same class of surface as\nclingen-link's ``get_gene_validity /assertions/*/disease_name`` \u2014 so it\nships as ``untrusted_text``. ``gene``/``inheritance``/``clinical_validity``\n/``consideration``/``adjusted_strength`` are short controlled-vocabulary\nvalues (HGNC symbol; ClinGen validity/inheritance/PVS1-adjustment\ncategories), not free prose.",
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
                          "description": "External prose represented as typed data with digest and provenance.",
                          "properties": {
                            "kind": {
                              "const": "untrusted_text",
                              "default": "untrusted_text",
                              "title": "Kind",
                              "type": "string"
                            },
                            "provenance": {
                              "description": "Source identity for one fenced external text object.",
                              "properties": {
                                "record_id": {
                                  "title": "Record Id",
                                  "type": "string"
                                },
                                "retrieved_at": {
                                  "format": "date-time",
                                  "title": "Retrieved At",
                                  "type": "string"
                                },
                                "source": {
                                  "title": "Source",
                                  "type": "string"
                                }
                              },
                              "required": [
                                "source",
                                "record_id",
                                "retrieved_at"
                              ],
                              "title": "UntrustedTextProvenance",
                              "type": "object"
                            },
                            "raw_sha256": {
                              "pattern": "^[0-9a-f]{64}$",
                              "title": "Raw Sha256",
                              "type": "string"
                            },
                            "text": {
                              "title": "Text",
                              "type": "string"
                            }
                          },
                          "required": [
                            "text",
                            "provenance",
                            "raw_sha256"
                          ],
                          "title": "UntrustedText",
                          "type": "object"
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
                    "anyOf": [
                      {
                        "description": "Typed PVS1 flowchart decision path and outcome.\n\n``decision_tree`` is the single canonical carrier of every scraped\ncriterion description (``code``) and its hoisted footnote\n(``note_text``). Response-Envelope v1.1 forbids the same upstream\nprose in more than one field (even when both copies are fenced), so\nthere is deliberately no ``notes`` legend dict and no\n``decision_tree_raw`` audit copy \u2014 both re-embedded prose that\n``decision_tree`` already carries. A caller that needs the raw\n``#N -> prose`` legend reads it off ``decision_tree[*].note_id`` +\n``note_text``.\n\n``terminal_note`` is the one-line rationale for the verdict, hoisted\nfrom the leaf step's note_text (or ``notes[preliminary_decision_path]``\nwhen the decision tree is empty). Populated ONLY in ``summary`` mode\n(where ``decision_tree`` is stripped, so it duplicates nothing) for\ncallers that need to explain non-Strong / non-Very-Strong outcomes\nwithout re-fetching the full decision tree. Absent when the upstream\nnote is empty or the verdict is unambiguous (PVS1_Strong /\nPVS1_Very_Strong).\n\n``path_gloss`` is a one-line, deterministic compression of the\ndecision-tree branch the variant traversed plus the terminal strength\n(ASCII ``->`` separated). It embeds the scraped node text, so to avoid\nduplicating ``decision_tree[*].code`` it is emitted ONLY in ``summary``\nmode \u2014 the tier where ``decision_tree`` is absent and the gloss is the\nsole prose carrier. Built only from upstream scraped node text \u2014 no\nhand-authored clinical mappings.\n\n``terminal_note`` and ``path_gloss`` ship as ``untrusted_text`` objects\n(Response-Envelope v1.1), the same as each ``decision_tree`` step's\n``code`` / ``note_text``.",
                        "properties": {
                          "decision_tree": {
                            "items": {
                              "description": "One typed step in the PVS1 decision flowchart.\n\n``code``, ``description``, and ``note_text`` are AutoPVS1's own scraped\nHTML prose (low-trust provenance: autopvs1.bgi.com) and ship as the\nResponse-Envelope v1.1 ``untrusted_text`` object, never a bare string.\n``note_id`` is a short upstream marker (``#1``, ``#2``, ...), not prose.",
                              "properties": {
                                "code": {
                                  "description": "External prose represented as typed data with digest and provenance.",
                                  "properties": {
                                    "kind": {
                                      "const": "untrusted_text",
                                      "default": "untrusted_text",
                                      "title": "Kind",
                                      "type": "string"
                                    },
                                    "provenance": {
                                      "description": "Source identity for one fenced external text object.",
                                      "properties": {
                                        "record_id": {
                                          "title": "Record Id",
                                          "type": "string"
                                        },
                                        "retrieved_at": {
                                          "format": "date-time",
                                          "title": "Retrieved At",
                                          "type": "string"
                                        },
                                        "source": {
                                          "title": "Source",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "source",
                                        "record_id",
                                        "retrieved_at"
                                      ],
                                      "title": "UntrustedTextProvenance",
                                      "type": "object"
                                    },
                                    "raw_sha256": {
                                      "pattern": "^[0-9a-f]{64}$",
                                      "title": "Raw Sha256",
                                      "type": "string"
                                    },
                                    "text": {
                                      "title": "Text",
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "text",
                                    "provenance",
                                    "raw_sha256"
                                  ],
                                  "title": "UntrustedText",
                                  "type": "object"
                                },
                                "description": {
                                  "anyOf": [
                                    {
                                      "description": "External prose represented as typed data with digest and provenance.",
                                      "properties": {
                                        "kind": {
                                          "const": "untrusted_text",
                                          "default": "untrusted_text",
                                          "title": "Kind",
                                          "type": "string"
                                        },
                                        "provenance": {
                                          "description": "Source identity for one fenced external text object.",
                                          "properties": {
                                            "record_id": {
                                              "title": "Record Id",
                                              "type": "string"
                                            },
                                            "retrieved_at": {
                                              "format": "date-time",
                                              "title": "Retrieved At",
                                              "type": "string"
                                            },
                                            "source": {
                                              "title": "Source",
                                              "type": "string"
                                            }
                                          },
                                          "required": [
                                            "source",
                                            "record_id",
                                            "retrieved_at"
                                          ],
                                          "title": "UntrustedTextProvenance",
                                          "type": "object"
                                        },
                                        "raw_sha256": {
                                          "pattern": "^[0-9a-f]{64}$",
                                          "title": "Raw Sha256",
                                          "type": "string"
                                        },
                                        "text": {
                                          "title": "Text",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "text",
                                        "provenance",
                                        "raw_sha256"
                                      ],
                                      "title": "UntrustedText",
                                      "type": "object"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null
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
                                      "description": "External prose represented as typed data with digest and provenance.",
                                      "properties": {
                                        "kind": {
                                          "const": "untrusted_text",
                                          "default": "untrusted_text",
                                          "title": "Kind",
                                          "type": "string"
                                        },
                                        "provenance": {
                                          "description": "Source identity for one fenced external text object.",
                                          "properties": {
                                            "record_id": {
                                              "title": "Record Id",
                                              "type": "string"
                                            },
                                            "retrieved_at": {
                                              "format": "date-time",
                                              "title": "Retrieved At",
                                              "type": "string"
                                            },
                                            "source": {
                                              "title": "Source",
                                              "type": "string"
                                            }
                                          },
                                          "required": [
                                            "source",
                                            "record_id",
                                            "retrieved_at"
                                          ],
                                          "title": "UntrustedTextProvenance",
                                          "type": "object"
                                        },
                                        "raw_sha256": {
                                          "pattern": "^[0-9a-f]{64}$",
                                          "title": "Raw Sha256",
                                          "type": "string"
                                        },
                                        "text": {
                                          "title": "Text",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "text",
                                        "provenance",
                                        "raw_sha256"
                                      ],
                                      "title": "UntrustedText",
                                      "type": "object"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null
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
                          "path_gloss": {
                            "anyOf": [
                              {
                                "description": "External prose represented as typed data with digest and provenance.",
                                "properties": {
                                  "kind": {
                                    "const": "untrusted_text",
                                    "default": "untrusted_text",
                                    "title": "Kind",
                                    "type": "string"
                                  },
                                  "provenance": {
                                    "description": "Source identity for one fenced external text object.",
                                    "properties": {
                                      "record_id": {
                                        "title": "Record Id",
                                        "type": "string"
                                      },
                                      "retrieved_at": {
                                        "format": "date-time",
                                        "title": "Retrieved At",
                                        "type": "string"
                                      },
                                      "source": {
                                        "title": "Source",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "source",
                                      "record_id",
                                      "retrieved_at"
                                    ],
                                    "title": "UntrustedTextProvenance",
                                    "type": "object"
                                  },
                                  "raw_sha256": {
                                    "pattern": "^[0-9a-f]{64}$",
                                    "title": "Raw Sha256",
                                    "type": "string"
                                  },
                                  "text": {
                                    "title": "Text",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "text",
                                  "provenance",
                                  "raw_sha256"
                                ],
                                "title": "UntrustedText",
                                "type": "object"
                              },
                              {
                                "type": "null"
                              }
                            ],
                            "default": null
                          },
                          "preliminary_decision_path": {
                            "title": "Preliminary Decision Path",
                            "type": "string"
                          },
                          "terminal_note": {
                            "anyOf": [
                              {
                                "description": "External prose represented as typed data with digest and provenance.",
                                "properties": {
                                  "kind": {
                                    "const": "untrusted_text",
                                    "default": "untrusted_text",
                                    "title": "Kind",
                                    "type": "string"
                                  },
                                  "provenance": {
                                    "description": "Source identity for one fenced external text object.",
                                    "properties": {
                                      "record_id": {
                                        "title": "Record Id",
                                        "type": "string"
                                      },
                                      "retrieved_at": {
                                        "format": "date-time",
                                        "title": "Retrieved At",
                                        "type": "string"
                                      },
                                      "source": {
                                        "title": "Source",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "source",
                                      "record_id",
                                      "retrieved_at"
                                    ],
                                    "title": "UntrustedTextProvenance",
                                    "type": "object"
                                  },
                                  "raw_sha256": {
                                    "pattern": "^[0-9a-f]{64}$",
                                    "title": "Raw Sha256",
                                    "type": "string"
                                  },
                                  "text": {
                                    "title": "Text",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "text",
                                  "provenance",
                                  "raw_sha256"
                                ],
                                "title": "UntrustedText",
                                "type": "object"
                              },
                              {
                                "type": "null"
                              }
                            ],
                            "default": null
                          }
                        },
                        "required": [
                          "preliminary_decision_path",
                          "final_strength"
                        ],
                        "title": "PVS1FlowchartMCP",
                        "type": "object"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null
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
                  "cnv_info"
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
          "meta": {
            "anyOf": [
              {
                "description": "Per-item cost/cache observability for bulk PVS1 result items.\n\nTop-level ``meta.cache_status`` aggregates the batch (\"mixed\" when\nitems had varying outcomes) \u2014 agents that need to forecast cost on a\nper-item basis read this block. Absent when the item short-circuited\nbefore any upstream call (e.g. invalid input).",
                "properties": {
                  "cache_status": {
                    "anyOf": [
                      {
                        "enum": [
                          "hit",
                          "miss",
                          "coalesced",
                          "bypass"
                        ],
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Cache Status"
                  },
                  "elapsed_ms": {
                    "anyOf": [
                      {
                        "type": "number"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Elapsed Ms"
                  }
                },
                "title": "BulkPerItemMeta",
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "default": null
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
    "retryable": {
      "type": "boolean"
    },
    "skipped": {
      "title": "Skipped",
      "type": "integer"
    },
    "succeeded": {
      "title": "Succeeded",
      "type": "integer"
    },
    "success": {
      "type": "boolean"
    },
    "total": {
      "title": "Total",
      "type": "integer"
    }
  },
  "required": [
    "success",
    "_meta"
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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "result": {
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
        "capabilities_version": {
          "title": "Capabilities Version",
          "type": "string"
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
            "description": "Compact MCP tool summary for first-turn discovery.\n\n``default_response_mode`` is the response_mode the tool emits when\nthe caller omits the parameter. Surfaced so LLM consumers can plan\nbandwidth without parsing the tool description; cheap tools that do\nnot accept response_mode leave it absent.",
            "properties": {
              "default_response_mode": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Default Response Mode"
              },
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
        "capabilities_version",
        "transport",
        "endpoint",
        "research_use_only",
        "tool_summaries",
        "canonical_parameters",
        "compact_workflow",
        "details_resource"
      ],
      "type": "object"
    },
    "retryable": {
      "type": "boolean"
    },
    "success": {
      "type": "boolean"
    }
  },
  "required": [
    "success",
    "_meta"
  ],
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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "result": {
      "description": "Local MCP server health status.\n\n``upstream_reachable`` and ``upstream_status`` are populated only when\nthe caller passes ``check_upstream=true``; otherwise the fields stay\nat their default ``False`` / ``\"not_checked\"`` so the cheap-tool\ncontract (no upstream cost, sub-millisecond) is preserved.",
      "properties": {
        "destructive_tools_enabled": {
          "default": false,
          "title": "Destructive Tools Enabled",
          "type": "boolean"
        },
        "server": {
          "default": "autopvs1-link",
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
        "upstream_reachable": {
          "default": false,
          "title": "Upstream Reachable",
          "type": "boolean"
        },
        "upstream_status": {
          "default": "not_checked",
          "enum": [
            "not_checked",
            "reachable",
            "unreachable"
          ],
          "title": "Upstream Status",
          "type": "string"
        },
        "version": {
          "default": "4.0.5",
          "title": "Version",
          "type": "string"
        }
      },
      "type": "object"
    },
    "retryable": {
      "type": "boolean"
    },
    "success": {
      "type": "boolean"
    }
  },
  "required": [
    "success",
    "_meta"
  ],
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
return ``requires_disambiguation`` with allele-keyed candidates
instead of
silently picking one (mitigates multi-allelic mis-scoring).

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
      "description": "Variant identifier. Canonical SPDI (CHROM-POS-REF-ALT, e.g. X-82763936-A-T) scores in one upstream call. rsID (rs80357906) or HGVS (NM_007294.4:c.5266dup, NP_000050.2:p.Glu1756fs, NC_000017.11:g.43091983C>A) auto-resolves via Ensembl Variant Recoder REST (build-scoped) then scores. Multiple resolver candidates return error.code='requires_disambiguation' with allele-keyed rows in details.candidates \u2014 caller picks one. Recoder offline returns error.code='external_resolver_unavailable' (retryable).",
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
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "result": {
      "description": "MCP-presented variant data.\n\n``pvs1_flowchart`` is required in summary/standard/full modes but\nomitted entirely when ``response_mode='ids_only'`` returns just the\nupstream identifier.",
      "properties": {
        "disease_mechanisms": {
          "items": {
            "description": "Typed disease mechanism row from AutoPVS1.\n\n``disease`` is a scraped free-text disease name (from AutoPVS1's\nClinGen-sourced gene-disease table) \u2014 the same class of surface as\nclingen-link's ``get_gene_validity /assertions/*/disease_name`` \u2014 so it\nships as ``untrusted_text``. ``gene``/``inheritance``/``clinical_validity``\n/``consideration``/``adjusted_strength`` are short controlled-vocabulary\nvalues (HGNC symbol; ClinGen validity/inheritance/PVS1-adjustment\ncategories), not free prose.",
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
                "description": "External prose represented as typed data with digest and provenance.",
                "properties": {
                  "kind": {
                    "const": "untrusted_text",
                    "default": "untrusted_text",
                    "title": "Kind",
                    "type": "string"
                  },
                  "provenance": {
                    "description": "Source identity for one fenced external text object.",
                    "properties": {
                      "record_id": {
                        "title": "Record Id",
                        "type": "string"
                      },
                      "retrieved_at": {
                        "format": "date-time",
                        "title": "Retrieved At",
                        "type": "string"
                      },
                      "source": {
                        "title": "Source",
                        "type": "string"
                      }
                    },
                    "required": [
                      "source",
                      "record_id",
                      "retrieved_at"
                    ],
                    "title": "UntrustedTextProvenance",
                    "type": "object"
                  },
                  "raw_sha256": {
                    "pattern": "^[0-9a-f]{64}$",
                    "title": "Raw Sha256",
                    "type": "string"
                  },
                  "text": {
                    "title": "Text",
                    "type": "string"
                  }
                },
                "required": [
                  "text",
                  "provenance",
                  "raw_sha256"
                ],
                "title": "UntrustedText",
                "type": "object"
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
          "anyOf": [
            {
              "description": "Typed PVS1 flowchart decision path and outcome.\n\n``decision_tree`` is the single canonical carrier of every scraped\ncriterion description (``code``) and its hoisted footnote\n(``note_text``). Response-Envelope v1.1 forbids the same upstream\nprose in more than one field (even when both copies are fenced), so\nthere is deliberately no ``notes`` legend dict and no\n``decision_tree_raw`` audit copy \u2014 both re-embedded prose that\n``decision_tree`` already carries. A caller that needs the raw\n``#N -> prose`` legend reads it off ``decision_tree[*].note_id`` +\n``note_text``.\n\n``terminal_note`` is the one-line rationale for the verdict, hoisted\nfrom the leaf step's note_text (or ``notes[preliminary_decision_path]``\nwhen the decision tree is empty). Populated ONLY in ``summary`` mode\n(where ``decision_tree`` is stripped, so it duplicates nothing) for\ncallers that need to explain non-Strong / non-Very-Strong outcomes\nwithout re-fetching the full decision tree. Absent when the upstream\nnote is empty or the verdict is unambiguous (PVS1_Strong /\nPVS1_Very_Strong).\n\n``path_gloss`` is a one-line, deterministic compression of the\ndecision-tree branch the variant traversed plus the terminal strength\n(ASCII ``->`` separated). It embeds the scraped node text, so to avoid\nduplicating ``decision_tree[*].code`` it is emitted ONLY in ``summary``\nmode \u2014 the tier where ``decision_tree`` is absent and the gloss is the\nsole prose carrier. Built only from upstream scraped node text \u2014 no\nhand-authored clinical mappings.\n\n``terminal_note`` and ``path_gloss`` ship as ``untrusted_text`` objects\n(Response-Envelope v1.1), the same as each ``decision_tree`` step's\n``code`` / ``note_text``.",
              "properties": {
                "decision_tree": {
                  "items": {
                    "description": "One typed step in the PVS1 decision flowchart.\n\n``code``, ``description``, and ``note_text`` are AutoPVS1's own scraped\nHTML prose (low-trust provenance: autopvs1.bgi.com) and ship as the\nResponse-Envelope v1.1 ``untrusted_text`` object, never a bare string.\n``note_id`` is a short upstream marker (``#1``, ``#2``, ...), not prose.",
                    "properties": {
                      "code": {
                        "description": "External prose represented as typed data with digest and provenance.",
                        "properties": {
                          "kind": {
                            "const": "untrusted_text",
                            "default": "untrusted_text",
                            "title": "Kind",
                            "type": "string"
                          },
                          "provenance": {
                            "description": "Source identity for one fenced external text object.",
                            "properties": {
                              "record_id": {
                                "title": "Record Id",
                                "type": "string"
                              },
                              "retrieved_at": {
                                "format": "date-time",
                                "title": "Retrieved At",
                                "type": "string"
                              },
                              "source": {
                                "title": "Source",
                                "type": "string"
                              }
                            },
                            "required": [
                              "source",
                              "record_id",
                              "retrieved_at"
                            ],
                            "title": "UntrustedTextProvenance",
                            "type": "object"
                          },
                          "raw_sha256": {
                            "pattern": "^[0-9a-f]{64}$",
                            "title": "Raw Sha256",
                            "type": "string"
                          },
                          "text": {
                            "title": "Text",
                            "type": "string"
                          }
                        },
                        "required": [
                          "text",
                          "provenance",
                          "raw_sha256"
                        ],
                        "title": "UntrustedText",
                        "type": "object"
                      },
                      "description": {
                        "anyOf": [
                          {
                            "description": "External prose represented as typed data with digest and provenance.",
                            "properties": {
                              "kind": {
                                "const": "untrusted_text",
                                "default": "untrusted_text",
                                "title": "Kind",
                                "type": "string"
                              },
                              "provenance": {
                                "description": "Source identity for one fenced external text object.",
                                "properties": {
                                  "record_id": {
                                    "title": "Record Id",
                                    "type": "string"
                                  },
                                  "retrieved_at": {
                                    "format": "date-time",
                                    "title": "Retrieved At",
                                    "type": "string"
                                  },
                                  "source": {
                                    "title": "Source",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "source",
                                  "record_id",
                                  "retrieved_at"
                                ],
                                "title": "UntrustedTextProvenance",
                                "type": "object"
                              },
                              "raw_sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "title": "Raw Sha256",
                                "type": "string"
                              },
                              "text": {
                                "title": "Text",
                                "type": "string"
                              }
                            },
                            "required": [
                              "text",
                              "provenance",
                              "raw_sha256"
                            ],
                            "title": "UntrustedText",
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null
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
                            "description": "External prose represented as typed data with digest and provenance.",
                            "properties": {
                              "kind": {
                                "const": "untrusted_text",
                                "default": "untrusted_text",
                                "title": "Kind",
                                "type": "string"
                              },
                              "provenance": {
                                "description": "Source identity for one fenced external text object.",
                                "properties": {
                                  "record_id": {
                                    "title": "Record Id",
                                    "type": "string"
                                  },
                                  "retrieved_at": {
                                    "format": "date-time",
                                    "title": "Retrieved At",
                                    "type": "string"
                                  },
                                  "source": {
                                    "title": "Source",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "source",
                                  "record_id",
                                  "retrieved_at"
                                ],
                                "title": "UntrustedTextProvenance",
                                "type": "object"
                              },
                              "raw_sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "title": "Raw Sha256",
                                "type": "string"
                              },
                              "text": {
                                "title": "Text",
                                "type": "string"
                              }
                            },
                            "required": [
                              "text",
                              "provenance",
                              "raw_sha256"
                            ],
                            "title": "UntrustedText",
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null
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
                "path_gloss": {
                  "anyOf": [
                    {
                      "description": "External prose represented as typed data with digest and provenance.",
                      "properties": {
                        "kind": {
                          "const": "untrusted_text",
                          "default": "untrusted_text",
                          "title": "Kind",
                          "type": "string"
                        },
                        "provenance": {
                          "description": "Source identity for one fenced external text object.",
                          "properties": {
                            "record_id": {
                              "title": "Record Id",
                              "type": "string"
                            },
                            "retrieved_at": {
                              "format": "date-time",
                              "title": "Retrieved At",
                              "type": "string"
                            },
                            "source": {
                              "title": "Source",
                              "type": "string"
                            }
                          },
                          "required": [
                            "source",
                            "record_id",
                            "retrieved_at"
                          ],
                          "title": "UntrustedTextProvenance",
                          "type": "object"
                        },
                        "raw_sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "title": "Raw Sha256",
                          "type": "string"
                        },
                        "text": {
                          "title": "Text",
                          "type": "string"
                        }
                      },
                      "required": [
                        "text",
                        "provenance",
                        "raw_sha256"
                      ],
                      "title": "UntrustedText",
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null
                },
                "preliminary_decision_path": {
                  "title": "Preliminary Decision Path",
                  "type": "string"
                },
                "terminal_note": {
                  "anyOf": [
                    {
                      "description": "External prose represented as typed data with digest and provenance.",
                      "properties": {
                        "kind": {
                          "const": "untrusted_text",
                          "default": "untrusted_text",
                          "title": "Kind",
                          "type": "string"
                        },
                        "provenance": {
                          "description": "Source identity for one fenced external text object.",
                          "properties": {
                            "record_id": {
                              "title": "Record Id",
                              "type": "string"
                            },
                            "retrieved_at": {
                              "format": "date-time",
                              "title": "Retrieved At",
                              "type": "string"
                            },
                            "source": {
                              "title": "Source",
                              "type": "string"
                            }
                          },
                          "required": [
                            "source",
                            "record_id",
                            "retrieved_at"
                          ],
                          "title": "UntrustedTextProvenance",
                          "type": "object"
                        },
                        "raw_sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "title": "Raw Sha256",
                          "type": "string"
                        },
                        "text": {
                          "title": "Text",
                          "type": "string"
                        }
                      },
                      "required": [
                        "text",
                        "provenance",
                        "raw_sha256"
                      ],
                      "title": "UntrustedText",
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "default": null
                }
              },
              "required": [
                "preliminary_decision_path",
                "final_strength"
              ],
              "title": "PVS1FlowchartMCP",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
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
          "description": "Typed variant information exposed through MCP.\n\nOnly ``variant_id`` is required at the contract level. ``variant_type``\nand ``gene_symbol`` are populated for summary/standard/full but absent\nwhen ``response_mode='ids_only'`` returns just the upstream identifier.",
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
              "title": "External Links"
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
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Gene Symbol"
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
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "title": "Variant Type"
            }
          },
          "required": [
            "variant_id"
          ],
          "title": "VariantInfoMCP",
          "type": "object"
        }
      },
      "required": [
        "genome_build",
        "variant_info"
      ],
      "type": "object"
    },
    "retryable": {
      "type": "boolean"
    },
    "success": {
      "type": "boolean"
    }
  },
  "required": [
    "success",
    "_meta"
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
(malformed ``items``) use error code ``invalid_bulk_input``.

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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "attempted": {
      "title": "Attempted",
      "type": "integer"
    },
    "error_code": {
      "type": "string"
    },
    "failed": {
      "title": "Failed",
      "type": "integer"
    },
    "message": {
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "results": {
      "items": {
        "description": "Per-item result for a bulk variant PVS1 request.",
        "properties": {
          "data": {
            "anyOf": [
              {
                "description": "MCP-presented variant data.\n\n``pvs1_flowchart`` is required in summary/standard/full modes but\nomitted entirely when ``response_mode='ids_only'`` returns just the\nupstream identifier.",
                "properties": {
                  "disease_mechanisms": {
                    "items": {
                      "description": "Typed disease mechanism row from AutoPVS1.\n\n``disease`` is a scraped free-text disease name (from AutoPVS1's\nClinGen-sourced gene-disease table) \u2014 the same class of surface as\nclingen-link's ``get_gene_validity /assertions/*/disease_name`` \u2014 so it\nships as ``untrusted_text``. ``gene``/``inheritance``/``clinical_validity``\n/``consideration``/``adjusted_strength`` are short controlled-vocabulary\nvalues (HGNC symbol; ClinGen validity/inheritance/PVS1-adjustment\ncategories), not free prose.",
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
                          "description": "External prose represented as typed data with digest and provenance.",
                          "properties": {
                            "kind": {
                              "const": "untrusted_text",
                              "default": "untrusted_text",
                              "title": "Kind",
                              "type": "string"
                            },
                            "provenance": {
                              "description": "Source identity for one fenced external text object.",
                              "properties": {
                                "record_id": {
                                  "title": "Record Id",
                                  "type": "string"
                                },
                                "retrieved_at": {
                                  "format": "date-time",
                                  "title": "Retrieved At",
                                  "type": "string"
                                },
                                "source": {
                                  "title": "Source",
                                  "type": "string"
                                }
                              },
                              "required": [
                                "source",
                                "record_id",
                                "retrieved_at"
                              ],
                              "title": "UntrustedTextProvenance",
                              "type": "object"
                            },
                            "raw_sha256": {
                              "pattern": "^[0-9a-f]{64}$",
                              "title": "Raw Sha256",
                              "type": "string"
                            },
                            "text": {
                              "title": "Text",
                              "type": "string"
                            }
                          },
                          "required": [
                            "text",
                            "provenance",
                            "raw_sha256"
                          ],
                          "title": "UntrustedText",
                          "type": "object"
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
                    "anyOf": [
                      {
                        "description": "Typed PVS1 flowchart decision path and outcome.\n\n``decision_tree`` is the single canonical carrier of every scraped\ncriterion description (``code``) and its hoisted footnote\n(``note_text``). Response-Envelope v1.1 forbids the same upstream\nprose in more than one field (even when both copies are fenced), so\nthere is deliberately no ``notes`` legend dict and no\n``decision_tree_raw`` audit copy \u2014 both re-embedded prose that\n``decision_tree`` already carries. A caller that needs the raw\n``#N -> prose`` legend reads it off ``decision_tree[*].note_id`` +\n``note_text``.\n\n``terminal_note`` is the one-line rationale for the verdict, hoisted\nfrom the leaf step's note_text (or ``notes[preliminary_decision_path]``\nwhen the decision tree is empty). Populated ONLY in ``summary`` mode\n(where ``decision_tree`` is stripped, so it duplicates nothing) for\ncallers that need to explain non-Strong / non-Very-Strong outcomes\nwithout re-fetching the full decision tree. Absent when the upstream\nnote is empty or the verdict is unambiguous (PVS1_Strong /\nPVS1_Very_Strong).\n\n``path_gloss`` is a one-line, deterministic compression of the\ndecision-tree branch the variant traversed plus the terminal strength\n(ASCII ``->`` separated). It embeds the scraped node text, so to avoid\nduplicating ``decision_tree[*].code`` it is emitted ONLY in ``summary``\nmode \u2014 the tier where ``decision_tree`` is absent and the gloss is the\nsole prose carrier. Built only from upstream scraped node text \u2014 no\nhand-authored clinical mappings.\n\n``terminal_note`` and ``path_gloss`` ship as ``untrusted_text`` objects\n(Response-Envelope v1.1), the same as each ``decision_tree`` step's\n``code`` / ``note_text``.",
                        "properties": {
                          "decision_tree": {
                            "items": {
                              "description": "One typed step in the PVS1 decision flowchart.\n\n``code``, ``description``, and ``note_text`` are AutoPVS1's own scraped\nHTML prose (low-trust provenance: autopvs1.bgi.com) and ship as the\nResponse-Envelope v1.1 ``untrusted_text`` object, never a bare string.\n``note_id`` is a short upstream marker (``#1``, ``#2``, ...), not prose.",
                              "properties": {
                                "code": {
                                  "description": "External prose represented as typed data with digest and provenance.",
                                  "properties": {
                                    "kind": {
                                      "const": "untrusted_text",
                                      "default": "untrusted_text",
                                      "title": "Kind",
                                      "type": "string"
                                    },
                                    "provenance": {
                                      "description": "Source identity for one fenced external text object.",
                                      "properties": {
                                        "record_id": {
                                          "title": "Record Id",
                                          "type": "string"
                                        },
                                        "retrieved_at": {
                                          "format": "date-time",
                                          "title": "Retrieved At",
                                          "type": "string"
                                        },
                                        "source": {
                                          "title": "Source",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "source",
                                        "record_id",
                                        "retrieved_at"
                                      ],
                                      "title": "UntrustedTextProvenance",
                                      "type": "object"
                                    },
                                    "raw_sha256": {
                                      "pattern": "^[0-9a-f]{64}$",
                                      "title": "Raw Sha256",
                                      "type": "string"
                                    },
                                    "text": {
                                      "title": "Text",
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "text",
                                    "provenance",
                                    "raw_sha256"
                                  ],
                                  "title": "UntrustedText",
                                  "type": "object"
                                },
                                "description": {
                                  "anyOf": [
                                    {
                                      "description": "External prose represented as typed data with digest and provenance.",
                                      "properties": {
                                        "kind": {
                                          "const": "untrusted_text",
                                          "default": "untrusted_text",
                                          "title": "Kind",
                                          "type": "string"
                                        },
                                        "provenance": {
                                          "description": "Source identity for one fenced external text object.",
                                          "properties": {
                                            "record_id": {
                                              "title": "Record Id",
                                              "type": "string"
                                            },
                                            "retrieved_at": {
                                              "format": "date-time",
                                              "title": "Retrieved At",
                                              "type": "string"
                                            },
                                            "source": {
                                              "title": "Source",
                                              "type": "string"
                                            }
                                          },
                                          "required": [
                                            "source",
                                            "record_id",
                                            "retrieved_at"
                                          ],
                                          "title": "UntrustedTextProvenance",
                                          "type": "object"
                                        },
                                        "raw_sha256": {
                                          "pattern": "^[0-9a-f]{64}$",
                                          "title": "Raw Sha256",
                                          "type": "string"
                                        },
                                        "text": {
                                          "title": "Text",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "text",
                                        "provenance",
                                        "raw_sha256"
                                      ],
                                      "title": "UntrustedText",
                                      "type": "object"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null
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
                                      "description": "External prose represented as typed data with digest and provenance.",
                                      "properties": {
                                        "kind": {
                                          "const": "untrusted_text",
                                          "default": "untrusted_text",
                                          "title": "Kind",
                                          "type": "string"
                                        },
                                        "provenance": {
                                          "description": "Source identity for one fenced external text object.",
                                          "properties": {
                                            "record_id": {
                                              "title": "Record Id",
                                              "type": "string"
                                            },
                                            "retrieved_at": {
                                              "format": "date-time",
                                              "title": "Retrieved At",
                                              "type": "string"
                                            },
                                            "source": {
                                              "title": "Source",
                                              "type": "string"
                                            }
                                          },
                                          "required": [
                                            "source",
                                            "record_id",
                                            "retrieved_at"
                                          ],
                                          "title": "UntrustedTextProvenance",
                                          "type": "object"
                                        },
                                        "raw_sha256": {
                                          "pattern": "^[0-9a-f]{64}$",
                                          "title": "Raw Sha256",
                                          "type": "string"
                                        },
                                        "text": {
                                          "title": "Text",
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "text",
                                        "provenance",
                                        "raw_sha256"
                                      ],
                                      "title": "UntrustedText",
                                      "type": "object"
                                    },
                                    {
                                      "type": "null"
                                    }
                                  ],
                                  "default": null
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
                          "path_gloss": {
                            "anyOf": [
                              {
                                "description": "External prose represented as typed data with digest and provenance.",
                                "properties": {
                                  "kind": {
                                    "const": "untrusted_text",
                                    "default": "untrusted_text",
                                    "title": "Kind",
                                    "type": "string"
                                  },
                                  "provenance": {
                                    "description": "Source identity for one fenced external text object.",
                                    "properties": {
                                      "record_id": {
                                        "title": "Record Id",
                                        "type": "string"
                                      },
                                      "retrieved_at": {
                                        "format": "date-time",
                                        "title": "Retrieved At",
                                        "type": "string"
                                      },
                                      "source": {
                                        "title": "Source",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "source",
                                      "record_id",
                                      "retrieved_at"
                                    ],
                                    "title": "UntrustedTextProvenance",
                                    "type": "object"
                                  },
                                  "raw_sha256": {
                                    "pattern": "^[0-9a-f]{64}$",
                                    "title": "Raw Sha256",
                                    "type": "string"
                                  },
                                  "text": {
                                    "title": "Text",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "text",
                                  "provenance",
                                  "raw_sha256"
                                ],
                                "title": "UntrustedText",
                                "type": "object"
                              },
                              {
                                "type": "null"
                              }
                            ],
                            "default": null
                          },
                          "preliminary_decision_path": {
                            "title": "Preliminary Decision Path",
                            "type": "string"
                          },
                          "terminal_note": {
                            "anyOf": [
                              {
                                "description": "External prose represented as typed data with digest and provenance.",
                                "properties": {
                                  "kind": {
                                    "const": "untrusted_text",
                                    "default": "untrusted_text",
                                    "title": "Kind",
                                    "type": "string"
                                  },
                                  "provenance": {
                                    "description": "Source identity for one fenced external text object.",
                                    "properties": {
                                      "record_id": {
                                        "title": "Record Id",
                                        "type": "string"
                                      },
                                      "retrieved_at": {
                                        "format": "date-time",
                                        "title": "Retrieved At",
                                        "type": "string"
                                      },
                                      "source": {
                                        "title": "Source",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "source",
                                      "record_id",
                                      "retrieved_at"
                                    ],
                                    "title": "UntrustedTextProvenance",
                                    "type": "object"
                                  },
                                  "raw_sha256": {
                                    "pattern": "^[0-9a-f]{64}$",
                                    "title": "Raw Sha256",
                                    "type": "string"
                                  },
                                  "text": {
                                    "title": "Text",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "text",
                                  "provenance",
                                  "raw_sha256"
                                ],
                                "title": "UntrustedText",
                                "type": "object"
                              },
                              {
                                "type": "null"
                              }
                            ],
                            "default": null
                          }
                        },
                        "required": [
                          "preliminary_decision_path",
                          "final_strength"
                        ],
                        "title": "PVS1FlowchartMCP",
                        "type": "object"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null
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
                    "description": "Typed variant information exposed through MCP.\n\nOnly ``variant_id`` is required at the contract level. ``variant_type``\nand ``gene_symbol`` are populated for summary/standard/full but absent\nwhen ``response_mode='ids_only'`` returns just the upstream identifier.",
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
                        "title": "External Links"
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
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Gene Symbol"
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
                        "anyOf": [
                          {
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "default": null,
                        "title": "Variant Type"
                      }
                    },
                    "required": [
                      "variant_id"
                    ],
                    "title": "VariantInfoMCP",
                    "type": "object"
                  }
                },
                "required": [
                  "genome_build",
                  "variant_info"
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
          "meta": {
            "anyOf": [
              {
                "description": "Per-item cost/cache observability for bulk PVS1 result items.\n\nTop-level ``meta.cache_status`` aggregates the batch (\"mixed\" when\nitems had varying outcomes) \u2014 agents that need to forecast cost on a\nper-item basis read this block. Absent when the item short-circuited\nbefore any upstream call (e.g. invalid input).",
                "properties": {
                  "cache_status": {
                    "anyOf": [
                      {
                        "enum": [
                          "hit",
                          "miss",
                          "coalesced",
                          "bypass"
                        ],
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Cache Status"
                  },
                  "elapsed_ms": {
                    "anyOf": [
                      {
                        "type": "number"
                      },
                      {
                        "type": "null"
                      }
                    ],
                    "default": null,
                    "title": "Elapsed Ms"
                  }
                },
                "title": "BulkPerItemMeta",
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "default": null
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
    "retryable": {
      "type": "boolean"
    },
    "skipped": {
      "title": "Skipped",
      "type": "integer"
    },
    "succeeded": {
      "title": "Succeeded",
      "type": "integer"
    },
    "success": {
      "type": "boolean"
    },
    "total": {
      "title": "Total",
      "type": "integer"
    }
  },
  "required": [
    "success",
    "_meta"
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
      "type": "string"
    },
    "response_mode": {
      "default": "ids_only",
      "description": "Response detail level. Default 'ids_only' emits the AutoPVS1 variant_id and url per row \u2014 the leanest shape for hand-off to get_variant_pvs1_data. 'summary' drops the rows entirely (use only with pagination metadata); 'standard' returns rich rows with gene + variant_type; 'full' is identical to 'standard' for search.",
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

#### Output Schema

```json
{
  "properties": {
    "_meta": {
      "description": "Common metadata carried in the ``_meta`` block of every MCP tool envelope.\n\nResponse-Envelope Standard v1 field canon: ``tool``, ``request_id``,\ntiered ``next_commands``, ``capabilities_version``, and provenance\n(``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and\n``capabilities_version`` are populated by :func:`ok_envelope` /\n:func:`error_envelope`; callers never set them directly.\n\n``effective_chars`` is the byte length of the serialized ``data`` field\n(compact JSON). It lets LLM callers calibrate against the advertised\nper-mode ``char_budget`` after the first call instead of guessing.\n\n``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's\nwall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``\n| ``bypass``). Populated by the cache wrapper via the telemetry\nContextVar; both drop from the wire when the tool made no upstream\ncall (e.g. ``get_server_health`` or ``get_server_capabilities``).\n\n``cost_tier`` is a coarse latency hint sourced from\n:data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value\nappears in the detailed capabilities resource so the wire and the\ndiscovery doc stay in lockstep. LLM callers use it to plan call\nsequencing without re-fetching capabilities every turn.\n\n``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap\n(default 1000 ms; tunable via\n``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on\nscrape-tier envelopes since it is meaningless for cheap tools.\n\n``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated\nonly when this call actually drove an upstream request\n(``cache_status in {\"miss\", \"coalesced\"}``) \u2014 those reset the\nrate-limit clock, so the next upstream call is gated until that\ninstant. ``hit`` / ``bypass`` cannot determine the next earliest\ntime (the clock may already have elapsed), so the field stays\nabsent.\n\n``retry_after_ms`` populates only on error envelopes for which the\ncaller can sensibly retry after a delay; on success envelopes it\ndrops from the wire.\n\n``next_actions`` is a per-error-code list of recovery hints\nsourced from\n:data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates\non every error envelope so a failing LLM dispatcher can pick the\nnext move without paying a ToolSearch round-trip to re-discover\nthe surface; absent on success envelopes.\n\n``cached_count`` and ``uncached_count`` populate only on bulk\nsuccess envelopes when items had mixed cache outcomes. In that\ncase ``cache_status='mixed'`` and the counts split items by\nwhether they returned warm (``hit`` + ``coalesced``) or cold\n(``miss`` + ``bypass``). Unanimous batches emit the single\nunderlying status and drop both counts. Cheap and single-tool\nenvelopes never carry these.",
      "properties": {
        "cache_status": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cache Status"
        },
        "cached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cached Count"
        },
        "capabilities_version": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Capabilities Version"
        },
        "cost_tier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cost Tier"
        },
        "effective_chars": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Effective Chars"
        },
        "elapsed_ms": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Elapsed Ms"
        },
        "expected_cold_latency_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expected Cold Latency Ms"
        },
        "next_actions": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Actions"
        },
        "next_call_earliest_at": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Next Call Earliest At"
        },
        "next_commands": {
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
          "title": "Next Commands"
        },
        "rate_limit_floor_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Rate Limit Floor Ms"
        },
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
        "retry_after_ms": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Retry After Ms"
        },
        "server_version": {
          "default": "4.0.5",
          "title": "Server Version",
          "type": "string"
        },
        "tool": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Tool"
        },
        "uncached_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Uncached Count"
        },
        "unsafe_for_clinical_use": {
          "default": true,
          "title": "Unsafe For Clinical Use",
          "type": "boolean"
        },
        "upstream": {
          "anyOf": [
            {
              "description": "Provenance note for HTML-scraped AutoPVS1 outputs.\n\nSurfaced only on scrape-tier envelopes so callers know the data was\nparsed from upstream HTML (not an official API) and that the format is\nnot contractually pinned and may drift silently.",
              "properties": {
                "note": {
                  "default": "Fields are parsed from upstream AutoPVS1 HTML, which has no versioned/contractual format; values may drift silently if the page changes. Cross-check before any interpretation.",
                  "title": "Note",
                  "type": "string"
                },
                "retrieval": {
                  "default": "html-scrape",
                  "title": "Retrieval",
                  "type": "string"
                },
                "source": {
                  "title": "Source",
                  "type": "string"
                }
              },
              "required": [
                "source"
              ],
              "title": "UpstreamProvenance",
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "warnings": {
          "items": {
            "description": "Structured non-fatal warning for LLM callers.\n\n``count`` and ``affected_indices`` are populated only when this warning\naggregates per-item occurrences in a bulk call. Single-tool warnings\nleave them ``None`` and they drop out of the wire payload via\n``exclude_none`` on the per-item meta serialization path.",
            "properties": {
              "affected_indices": {
                "anyOf": [
                  {
                    "items": {
                      "type": "integer"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Affected Indices"
              },
              "code": {
                "title": "Code",
                "type": "string"
              },
              "count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "default": null,
                "title": "Count"
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
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "genome_build": {
      "title": "Genome Build",
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "ordering": {
      "const": "upstream",
      "default": "upstream",
      "title": "Ordering",
      "type": "string"
    },
    "pagination": {
      "description": "Pagination block for ``search_variants``.\n\nCursors are base64url-encoded ``{\"offset\": N}`` tokens. They are\ntransparent by convention: a caller MAY decode one to read the row\noffset, but the encoding is not a stable contract and MAY change to an\nopaque form later, so prefer echoing ``next_cursor`` back verbatim.\n``offset`` is echoed for operator visibility only.\n``total_count_kind`` documents how to interpret ``total_count`` on the\nsurrounding ``SearchMCPData``: ``upstream_page`` means the count is\nonly what the upstream returned for this query (no guarantee of\nexhaustiveness); ``upstream_total`` means the upstream guarantees the\nfull result set was returned.\n\n``previous_cursor`` and ``next_cursor`` carry ``= None`` defaults so\nthe published JSON schema marks them non-required. The wire payload\nstrips null fields (``exclude_none=True``) and the MCP client\nvalidates structured content against that schema \u2014 without the\ndefaults, page 1 (no previous) and the last page (no next) would\nfail validation.",
      "properties": {
        "has_more": {
          "title": "Has More",
          "type": "boolean"
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
          "default": null,
          "title": "Next Cursor"
        },
        "offset": {
          "title": "Offset",
          "type": "integer"
        },
        "previous_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Previous Cursor"
        },
        "total_count_kind": {
          "default": "upstream_page",
          "enum": [
            "upstream_total",
            "upstream_page"
          ],
          "title": "Total Count Kind",
          "type": "string"
        }
      },
      "required": [
        "has_more",
        "offset"
      ],
      "title": "SearchPaginationMCP",
      "type": "object"
    },
    "query": {
      "title": "Query",
      "type": "string"
    },
    "recovery_action": {
      "type": "string"
    },
    "results": {
      "items": {
        "description": "Typed AutoPVS1 search result row.\n\nOnly ``variant_id`` and ``url`` are guaranteed to be present.\n``response_mode='ids_only'`` drops the descriptive fields so callers\nthat only need the identifier and a re-fetch URL pay no extra bytes.",
        "properties": {
          "gene": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "default": null,
            "title": "Gene"
          },
          "genome_build": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "default": null,
            "title": "Genome Build"
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
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "default": null,
            "title": "Variant Type"
          }
        },
        "required": [
          "variant_id",
          "url"
        ],
        "title": "SearchResultMCP",
        "type": "object"
      },
      "title": "Results",
      "type": "array"
    },
    "retryable": {
      "type": "boolean"
    },
    "returned_count": {
      "title": "Returned Count",
      "type": "integer"
    },
    "success": {
      "type": "boolean"
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
    "success",
    "_meta"
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
