---
name: autopvs1-scraper-change
description: Use when modifying AutoPVS1 HTML fetching, parsing, URL construction, or fixture-backed scraper behavior.
---

# AutoPVS1 Scraper Change

Follow `AGENTS.md` first.

## Workflow

1. Inspect `autopvs1_link/api/autopvs1_client.py` and any split parser, URL, or
   validation modules.
2. Keep the default upstream rate-limit delay at 1.0 seconds unless the user
   explicitly approves a change.
3. Treat the upstream as HTML, not a stable API. Parser changes require an HTML
   fixture under `tests/fixtures/`.
4. Prefer BeautifulSoup selectors and structured parsing helpers over ad hoc
   string slicing.
5. Validate genome builds and variant/CNV identifiers before constructing
   upstream URLs.
6. Run parser/client fixture tests, then `make ci-local`.
