# research_state.json schema

The state file is the single source of truth for a research run. Every script reads and writes it through `research_state.py` subcommands or the matching `apply_*` library functions in that module — no script touches the JSON directly. The shape is versioned via `schema_version`; loading a state file from an unsupported version returns `state_schema_mismatch` (exit 4) rather than silently coercing.

Run `python scripts/research_state.py --schema` for the machine-readable version with every subcommand expanded.

## Abbreviated shape

```json
{
  "schema_version": 1,
  "question": "...",
  "archetype": "literature_review",
  "phase": 3,
  "created_at": "...",
  "updated_at": "...",
  "queries": [
    {"source": "openalex", "query": "...", "hits": 42, "new": 30, "round": 1}
  ],
  "papers": {
    "doi:10.1038/nature12373": {
      "id": "doi:10.1038/nature12373",
      "title": "...",
      "authors": ["..."],
      "year": 2013,
      "venue": "Nature",
      "citations": 523,
      "abstract": "...",
      "source": ["openalex", "crossref"],
      "score": 0.81,
      "score_components": {
        "relevance": 0.9,
        "citations": 0.8,
        "recency": 0.6,
        "venue": 1.0
      },
      "selected": true,
      "depth": "full",
      "tier": "deep",
      "triage_score": 0.74,
      "triage_components": {
        "relevance": 0.8,
        "citation_density": 0.6,
        "recency": 0.9,
        "has_pdf": 1.0,
        "abstract_quality": 1.0
      },
      "evidence": {
        "method": "...",
        "findings": ["..."],
        "limitations": "..."
      },
      "discovered_via": "search"
    }
  },
  "triage_complete": true,
  "triage_meta": {
    "weights": {},
    "deep_ratio": 0.5,
    "skim_ratio": 0.5,
    "triaged_at": "..."
  },
  "themes": [{"name": "...", "paper_ids": ["..."]}],
  "tensions": [
    {"topic": "...", "sides": [{"position": "...", "paper_ids": ["..."]}]}
  ],
  "self_critique": {"findings": [], "resolved": [], "appendix": "..."},
  "report_path": "reports/slug_20260411.md"
}
```

## ID normalization

Paper IDs are normalized in priority order: `doi:...` → `openalex:W...` → `arxiv:...` → `pmid:...`. `dedupe_papers.py` depends on this ordering, and merging logic prefers the higher-priority ID when the same paper is discovered through multiple sources.

## What's settable directly

Only `archetype` and `report_path` are settable via `research_state.py set --field ...`. `phase` is **not** settable — it advances only through `research_state.py advance`, which runs the gate predicates in `_gates.py`. Every collection field (`papers`, `queries`, `themes`, `tensions`, `self_critique`) is mutable only through its dedicated subcommand. Widening the `SETTABLE_FIELDS` whitelist is a security decision — don't do it casually.
