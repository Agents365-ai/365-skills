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
| `PAPER_FETCH_SCRIPT` | `extract_pdf.py`, `prefetch_pdfs.py` | Path to paper-fetch's `fetch.py`. If unset, auto-discovers across direct-install skill paths (Claude Code, OpenCode, OpenClaw, Hermes, ~/.agents) **and** the plugin marketplace cache (`~/.claude/plugins/cache/*/paper-fetch/*/skills/paper-fetch/scripts/fetch.py`). If nothing resolves, falls back to Unpaywall |
| `SCHOLAR_PHASE1_MAX_ROUNDS` | `research_state.py ingest` and every `search_*.py` that ingests through it | Hard cap on distinct discovery rounds before Phase 1 refuses further ingest with `phase1_budget_exhausted` (envelope carries a `next:` hint with the right knob to bump); default `10`. Lifts automatically once `phase >= 2`. Raise it when a legitimately broad topic needs more rounds |
| `SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE` | same as above | Hard cap on per-source ingest events during Phase 1; default `20`. Same `phase1_budget_exhausted` envelope when exceeded; same auto-lift at phase 2 |
| `SCHOLAR_SATURATION_NEW_PCT` | `research_state.py saturation`, `_gates.gate_2` | New-paper percentage below which a source is considered saturated; default `20.0`. Raise (e.g. to `40` or `50`) for broad CS topics that genuinely keep surfacing new highly-cited work for many rounds — the default G2 gate is otherwise unreachable. Honored by both the standalone command and the gate |
| `SCHOLAR_SATURATION_MAX_CITATIONS` | same as above | Saturation is blocked while a new paper above this citation threshold appears in the latest round; default `100` |
| `SCHOLAR_SATURATION_MIN_ROUNDS` | same as above | Minimum rounds before any source can be called saturated; default `2`. Prevents single-query sources from claiming saturation |
| `SCHOLAR_SATURATION_NEW_AUTHORS_PCT` | same as above | Author-novelty axis threshold; default `25.0` |
| `SCHOLAR_SATURATION_NEW_VENUES_PCT` | same as above | Venue-novelty axis threshold; default `30.0`. Skipped automatically for sources without venue metadata |
| `SCHOLAR_SATURATION_MIN_AXES` | same as above | Number of converged axes required for a source to saturate; default `4` (strict AND of papers / citations / authors / venues). Set to `3` to enable soft-saturation for hot fields where 3 of 4 axes converge cleanly but query reformulation keeps the papers axis high (typical of fast-moving ML literature). When fewer axes are evaluable than `min_axes`, the requirement falls back to "all evaluable axes" so strict mode is never weakened by axis-absence |
| `SCHOLAR_SEARCH_CACHE` | the 4 stdlib search scripts (`search_openalex/arxiv/crossref/pubmed`) | Set to `1` / `true` / `yes` / `on` to enable an opt-in TTL cache of HTTP search results. Default OFF — envelope is bit-identical to the un-cached path until enabled. When enabled, `meta.search_cache` is `"hit"` or `"miss"` for corpus-provenance audits |
| `SCHOLAR_SEARCH_CACHE_TTL_HOURS` | as above, only when `SCHOLAR_SEARCH_CACHE` is on | TTL for cached search results; default `24` (hours). Distinct cache from `SCHOLAR_CACHE_DIR` — search cache lives under `<cache_dir>/searches/` and expires by clock; idempotency cache names a specific run and never expires |
| `SCHOLAR_REQUEST_ID` | every script (envelope `meta.request_id`) | Override the auto-generated `req_<hex>` request id so an orchestrator can correlate envelopes with its own trace. Defaults to a fresh UUID-derived id per process |

## Why env-var, not CLI flag

Per the agent-native-design principle "trust is directional," credentials and host-level config belong in higher-trust boundaries than the agent's own argv. The shell profile, a systemd unit, or the orchestrator's env injection is set by a human; the agent inherits it without being able to mint it. This is also why there is no `login` / `auth` / `token` subcommand — auth is delegated, not invoked.

When a script needs an env var that isn't set, it returns a structured envelope (`code: missing_env_var` or similar) telling the agent which variable to ask the user about — never a silent failure.
