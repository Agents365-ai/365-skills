# CLI contract

Every script in `scripts/` follows the same agent-native contract. This is the long-form reference; agents typically discover it by running scripts and reading the JSON envelope, but it's documented here for humans, new contributors, and anyone debugging an unexpected response shape.

## Stdout is JSON-only

Every script prints **exactly one** JSON envelope to stdout and exits with a code from the stable vocabulary below. No prose is ever mixed into stdout — diagnostics and progress logs go to stderr.

### Success envelope

```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "request_id": "...",
    "latency_ms": 123,
    "cli_version": "<X.Y.Z, matches scripts/_common.py:VERSION>",
    "schema_version": 1
  }
}
```

### Failure envelope

```json
{
  "ok": false,
  "error": {
    "code": "snake_case_routing_key",
    "message": "human sentence",
    "retryable": true,
    "...extra context fields...": "..."
  },
  "meta": { ... }
}
```

`code` is the routing key — a stable, snake_case identifier the agent can match against. `message` is the human-friendly sentence. `retryable` tells the agent whether a re-run might succeed without intervention.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | runtime error (e.g. malformed upstream response, missing dependency) |
| `2` | upstream / network error (retryable) |
| `3` | validation error (bad input) |
| `4` | state error (missing, corrupt, or schema mismatch) |

## Schema introspection

Every script supports `--schema`, which prints its full parameter schema (types, defaults, choices, required flags, subcommands where applicable) as JSON and exits 0. **An agent discovering an unfamiliar script should run `--schema` before `--help`** — it is machine-parseable and covers everything `--help` does.

```bash
python scripts/search_openalex.py --schema
python scripts/research_state.py --schema   # includes every subcommand
```

The top-level schema response carries `cli_version` so an agent caching a schema can detect drift. Per-subcommand schemas carry `meta.{since, tier, dangerous_if}` so agents can detect new commands and graduated-safety paired-flag requirements.

## Export bibliography exception

`export_bibtex.py` without `--output` writes raw BibTeX/RIS/CSL text to stdout for pipe compatibility:

```bash
python scripts/export_bibtex.py --state research_state.json --format bibtex > refs.bib
```

This is the one place where stdout is not the JSON envelope — it's the deliberate TTY/pipe affordance for human users and shell pipelines. Agents that need a structured response should always pass `--output <path>`; that path returns `{"ok": true, "data": {"output": "...", "format": "bibtex", "count": N}}` like every other script.

## Idempotency on mutating commands

Every mutating command accepts `--idempotency-key <k>`. The first successful run writes `{response, signature}` to `${SCHOLAR_CACHE_DIR:-.scholar_cache}/<sha256>.json`. A retry with the same key replays the cached response. The same key with *different* semantic arguments returns `idempotency_key_mismatch` rather than silently serving stale data. Combining `--idempotency-key` with `--dry-run` is rejected at the boundary — a dry run doesn't mutate, so caching it is meaningless.
