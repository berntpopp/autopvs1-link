# MCP Evaluation Checklist

Use this checklist after MCP contract changes. Outputs are research-use
AutoPVS1 data, not clinical decision support.

- `get_variant_pvs1_data` with `{"genome_build":"hg19","variant_id":"X-82763936-A-T"}` returns `ok: true`, `data.pvs1_flowchart.final_strength: "Strong"`, `meta.research_use_only: true`, and cache metadata remains available through `autopvs1-link://cache/statistics`.
- `get_variant_pvs1_data` with `{"genome_build":"hg19","variant_id":"17-41276045-ACT-A"}` returns `ok: true`, `data.pvs1_flowchart.final_strength: "VeryStrong"`, and `data.variant_info.pli_score_display` is present when `pli_score` is present.
- `get_variant_pvs1_data` with `{"genome_build":"hg38","variant_id":"NOT-A-VARIANT"}` returns `ok: false`, `error.code: "invalid_variant_id"`, and no raw HTML, MDN URL, or traceback.
- `get_cnv_pvs1_data` with `{"genome_build":"hg19","cnv_id":"17:15000000-20000000:DEL"}` returns `ok: false`, `error.code: "invalid_cnv_id"`, and a suggestion to use `17-15000000-20000000-DEL`.
- `get_cnv_pvs1_data` with `{"genome_build":"hg19","cnv_id":"17-15000000-20000000-DEL"}` returns `ok: true` when the service adapter returns CNV data.
- `search_variants` with `{"query":"BRCA1 c.5266dupC","genome_build":"hg38"}` returns `ok: true`, `data.results: []`, and guidance in warnings or suggestions when upstream returns no results.
- `search_variants` with `{"query":"   "}` returns `ok: false` and `error.code: "invalid_search_query"`.
- `clear_cache` with `{}` returns `ok: false` and `error.code: "destructive_disabled"` unless `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true` is set.
