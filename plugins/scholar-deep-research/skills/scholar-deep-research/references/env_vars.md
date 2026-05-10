# Environment variables

Trust-boundary configuration. These are set once by the human or orchestrator — never by the agent. CLI flags override env vars where both are present.

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SCHOLAR_STATE_PATH` | every script that takes `--state` | Default path to `research_state.json` |
| `SCHOLAR_MAILTO` | `search_openalex.py`, `search_crossref.py`, `build_citation_graph.py` | Polite-pool email for OpenAlex / Crossref — higher rate limits |
| `NCBI_API_KEY` | `search_pubmed.py` | NCBI E-utilities API key — higher rate limits |
| `EXA_API_KEY` | `search_exa.py` | Exa API key — required to enable the open-web search provider |
| `S2_API_KEY` | `build_citation_graph.py --source s2\|both` | Semantic Scholar API key — raises the public ~1 req/s quota. Optional; without it the S2 backend still works at the lower quota |
| `SCHOLAR_CACHE_DIR` | `build_citation_graph.py` (any command that takes `--idempotency-key`) | Cache directory for idempotent-retry responses; default `.scholar_cache/` in cwd |
| `PAPER_FETCH_SCRIPT` | `extract_pdf.py` | Path to paper-fetch's `fetch.py`. If unset, auto-discovers across all known skill install paths (Claude Code, OpenCode, OpenClaw, Hermes, ~/.agents). If not found, falls back to Unpaywall |
| `SCHOLAR_PHASE1_MAX_ROUNDS` | `research_state.py ingest` and every `search_*.py` that ingests through it | Hard cap on distinct discovery rounds before Phase 1 refuses further ingest with `phase1_budget_exhausted`; default `5`. Lifts automatically once `phase >= 2`. Raise it when a legitimately broad topic needs more rounds |
| `SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE` | same as above | Hard cap on per-source ingest events during Phase 1; default `20`. Same `phase1_budget_exhausted` envelope when exceeded; same auto-lift at phase 2 |
| `SCHOLAR_SEARCH_CACHE` | the 4 stdlib search scripts (`search_openalex/arxiv/crossref/pubmed`) | Set to `1` / `true` / `yes` / `on` to enable an opt-in TTL cache of HTTP search results. Default OFF — envelope is bit-identical to the un-cached path until enabled. When enabled, `meta.search_cache` is `"hit"` or `"miss"` for corpus-provenance audits |
| `SCHOLAR_SEARCH_CACHE_TTL_HOURS` | as above, only when `SCHOLAR_SEARCH_CACHE` is on | TTL for cached search results; default `24` (hours). Distinct cache from `SCHOLAR_CACHE_DIR` — search cache lives under `<cache_dir>/searches/` and expires by clock; idempotency cache names a specific run and never expires |
| `SCHOLAR_REQUEST_ID` | every script (envelope `meta.request_id`) | Override the auto-generated `req_<hex>` request id so an orchestrator can correlate envelopes with its own trace. Defaults to a fresh UUID-derived id per process |

## Why env-var, not CLI flag

Per the agent-native-design principle "trust is directional," credentials and host-level config belong in higher-trust boundaries than the agent's own argv. The shell profile, a systemd unit, or the orchestrator's env injection is set by a human; the agent inherits it without being able to mint it. This is also why there is no `login` / `auth` / `token` subcommand — auth is delegated, not invoked.

When a script needs an env var that isn't set, it returns a structured envelope (`code: missing_env_var` or similar) telling the agent which variable to ask the user about — never a silent failure.
