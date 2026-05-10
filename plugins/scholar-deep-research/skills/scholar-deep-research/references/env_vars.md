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
| `SCHOLAR_SKIP_UPDATE_CHECK` | `check_update.py` | Set to any non-empty value to pin the current version and skip Phase 0 Step 0's auto-update |

## Why env-var, not CLI flag

Per the agent-native-design principle "trust is directional," credentials and host-level config belong in higher-trust boundaries than the agent's own argv. The shell profile, a systemd unit, or the orchestrator's env injection is set by a human; the agent inherits it without being able to mint it. This is also why there is no `login` / `auth` / `token` subcommand — auth is delegated, not invoked.

When a script needs an env var that isn't set, it returns a structured envelope (`code: missing_env_var` or similar) telling the agent which variable to ask the user about — never a silent failure.
