# CLAUDE.md

@AGENTS.md

Claude Code entrypoint only:

- Use `AGENTS.md` for shared repository instructions.
- Keep Claude-specific additions here short and tool-specific.
- Prefer `make ci-local` before final handoff. It runs `lint-loc`, which
  enforces the 600-LOC per-file budget (see AGENTS.md "File Size Discipline").
- When planning an edit that would push an `autopvs1_link/` module past
  ~500 lines, propose a split first rather than growing the file.
- When a split is required, prefer cohesive sub-modules and keep public facades
  stable so call sites do not churn.
