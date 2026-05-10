"""state_apply.py — public library API for mutating research_state.

Extracted from `research_state.py` so the larger file can stay focused on
CLI dispatch + low-level helpers. Every script that mutates state imports
from here (or, equivalently, from `research_state` which re-exports these
names for backwards compatibility):

    from research_state import apply_ingest, apply_ranking, ...
    # or, equivalently after this split:
    from state_apply import apply_ingest, apply_ranking, ...

Single-writer invariant: the `apply_*` functions below — together with
`research_state.cmd_init` — are the ONLY supported write paths.
`research_state._save_state` is private and only reachable from inside
the state lock via `_locked_rmw`. Do not bypass.

Each `apply_*` runs under `research_state._locked_rmw`, so concurrent
calls (e.g. parallel Phase 1 search ingests) are serialized.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from _common import phase1_max_requests_per_source, phase1_max_rounds
from research_state import (
    _locked_rmw,
    _validate_ingest_payload,
    make_paper_id,
    now_iso,
)


class Phase1BudgetExhausted(Exception):
    """Raised when an ingest would push Phase 1 past its configured cap.

    Two cap kinds:
      - `max_requests_per_source`: too many ingest events for one source.
      - `max_rounds`: would create a brand-new round above the cap.

    Caps lift automatically once `state["phase"] >= 2`, so Phase 4
    citation chase is not affected. Override defaults via
    SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE / SCHOLAR_PHASE1_MAX_ROUNDS
    env vars (human/orchestrator boundary; agents cannot raise their
    own ceiling).
    """

    def __init__(self, limit_kind: str, limit: int, current: int,
                 source: str | None = None):
        super().__init__(
            f"phase1 budget exhausted: {limit_kind} = {current} (max {limit})"
            + (f" on source '{source}'" if source else "")
        )
        self.limit_kind = limit_kind
        self.limit = limit
        self.current = current
        self.source = source


def _check_phase1_budget(state: dict[str, Any], source: str,
                         new_round: int) -> None:
    """Raise Phase1BudgetExhausted when the next ingest would exceed caps.

    No-op when state has already advanced past Phase 1.
    """
    if (state.get("phase") or 0) >= 2:
        return

    queries = state.get("queries") or []

    src_requests = sum(1 for q in queries if q.get("source") == source)
    cap_per_source = phase1_max_requests_per_source()
    if src_requests >= cap_per_source:
        raise Phase1BudgetExhausted(
            "max_requests_per_source", cap_per_source, src_requests,
            source=source,
        )

    existing_rounds = {q.get("round") for q in queries}
    cap_rounds = phase1_max_rounds()
    if new_round not in existing_rounds and len(existing_rounds) >= cap_rounds:
        raise Phase1BudgetExhausted(
            "max_rounds", cap_rounds, len(existing_rounds),
        )


def apply_ingest(state_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Library API for ingesting a search payload into state.

    Called by the ingest subcommand AND by `_common.emit()` (which used to
    spawn this script as a subprocess and pass a shared temp-file path —
    that race is gone now). Serializes via the exclusive state lock, so
    concurrent Phase 1 searches are safe.

    Returns the ingestion summary dict (to be emitted by the caller).

    Raises `Phase1BudgetExhausted` when the per-source or new-round cap
    would be exceeded; the lock is released without writing (the mutator
    raises before any state mutation). Callers convert to an `err()`
    envelope.
    """
    _validate_ingest_payload(payload)
    source = payload["source"]
    query = payload["query"]
    rnd = payload["round"]
    incoming = payload["papers"]

    summary: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        _check_phase1_budget(state, source, rnd)
        new_count = 0
        merged_count = 0
        for p in incoming:
            pid = make_paper_id(p)
            p["id"] = pid
            p.setdefault("source", [])
            if source not in p["source"]:
                p["source"].append(source)
            p.setdefault("first_seen_round", rnd)
            p.setdefault("selected", False)
            p.setdefault("depth", "shallow")
            p.setdefault("discovered_via", "search")

            if pid in state["papers"]:
                existing = state["papers"][pid]
                for s in p["source"]:
                    if s not in existing.get("source", []):
                        existing.setdefault("source", []).append(s)
                for k in ("doi", "abstract", "pdf_url", "url", "venue", "citations"):
                    if not existing.get(k) and p.get(k):
                        existing[k] = p[k]
                merged_count += 1
            else:
                state["papers"][pid] = p
                new_count += 1

        state["queries"].append({
            "source": source,
            "query": query,
            "round": rnd,
            "hits": len(incoming),
            "new": new_count,
            "merged": merged_count,
            "timestamp": now_iso(),
        })
        summary.update({
            "source": source,
            "query": query,
            "round": rnd,
            "ingested": len(incoming),
            "new": new_count,
            "merged": merged_count,
            "total_papers": len(state["papers"]),
        })
        return state

    _locked_rmw(state_path, mutator)
    return summary


def apply_search_failure(state_path: Path, source: str, message: str,
                         *, status: int | None = None) -> dict[str, Any]:
    """Record a failed upstream search call into search_diagnostics.

    Called by the 4 stdlib search scripts (openalex/arxiv/pubmed/crossref)
    from their `except UpstreamError` block, so the report-writer in
    Phase 7 can footnote which sources were unreachable. Successes are
    not separately persisted — they are implicit in `state.queries` and
    `state.papers[*].source`.

    Increments `failures` and overwrites `last_error` with the most
    recent message + status + ISO timestamp. Returns the updated entry.
    """
    entry: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        diagnostics = state.setdefault("search_diagnostics", {})
        existing = diagnostics.setdefault(source, {"failures": 0, "last_error": None})
        existing["failures"] = int(existing.get("failures", 0)) + 1
        existing["last_error"] = {
            "message": message,
            "status": status,
            "timestamp": now_iso(),
        }
        entry.update(existing)
        return state

    _locked_rmw(state_path, mutator)
    return entry


def compute_source_diagnostics(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-source roll-up: requests, papers_contributed, failures, last_error.

    Pure function over the state dict — read by both `cmd_query` and
    `cmd_saturation` so they share one source of truth. A source appears
    in the output if it has *any* signal (a successful query, a paper
    tagged with the source, or a recorded failure).
    """
    sources: set[str] = set()
    requests_by_source: dict[str, int] = {}
    for q in state.get("queries") or []:
        src = q.get("source")
        if not src:
            continue
        sources.add(src)
        requests_by_source[src] = requests_by_source.get(src, 0) + 1

    papers_by_source: dict[str, int] = {}
    for p in (state.get("papers") or {}).values():
        for src in (p.get("source") or []):
            sources.add(src)
            papers_by_source[src] = papers_by_source.get(src, 0) + 1

    diagnostics = state.get("search_diagnostics") or {}
    for src in diagnostics.keys():
        sources.add(src)

    out: dict[str, dict[str, Any]] = {}
    for src in sorted(sources):
        diag = diagnostics.get(src) or {}
        out[src] = {
            "requests": requests_by_source.get(src, 0),
            "papers_contributed": papers_by_source.get(src, 0),
            "failures": int(diag.get("failures") or 0),
            "last_error": diag.get("last_error"),
        }
    return out


def apply_ranking(
    state_path: Path,
    scored_papers: dict[str, dict[str, Any]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Apply ranking scores + components to state.

    `scored_papers` maps `paper_id -> {"score": float, "score_components": {...}}`.
    `meta` is the ranking metadata dict (formula, weights, half_life, ranked_at).
    Returns a summary dict with `ranked` count and formula.
    """
    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        for pid, scoring in scored_papers.items():
            if pid in state["papers"]:
                state["papers"][pid]["score"] = scoring["score"]
                state["papers"][pid]["score_components"] = scoring["score_components"]
        state["ranking"] = meta
        return state

    _locked_rmw(state_path, mutator)
    return {"ranked": len(scored_papers), "formula": meta.get("formula")}


def apply_dedupe(
    state_path: Path,
    new_papers: dict[str, dict[str, Any]],
    id_remap: dict[str, str],
) -> dict[str, Any]:
    """Replace state.papers with `new_papers` and rewrite ID-bearing collections.

    The rewrite uses `id_remap: {old_id -> new_id}`. References to IDs that
    no longer exist in `new_papers` are dropped. Runs inside the lock so the
    swap and the rewrite are atomic — a concurrent reader sees either the
    pre-dedupe or the post-dedupe state, never a mix.
    """
    def remap(pid: str) -> str:
        return id_remap.get(pid, pid)

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["papers"] = new_papers
        if state.get("selected_ids"):
            seen: set[str] = set()
            rewritten: list[str] = []
            for pid in state["selected_ids"]:
                new_pid = remap(pid)
                if new_pid in new_papers and new_pid not in seen:
                    rewritten.append(new_pid)
                    seen.add(new_pid)
            state["selected_ids"] = rewritten
        for theme in state.get("themes", []):
            if "paper_ids" in theme:
                theme["paper_ids"] = sorted({
                    remap(pid) for pid in theme["paper_ids"]
                    if remap(pid) in new_papers
                })
        for tension in state.get("tensions", []):
            for side in tension.get("sides", []):
                if "paper_ids" in side:
                    side["paper_ids"] = sorted({
                        remap(pid) for pid in side["paper_ids"]
                        if remap(pid) in new_papers
                    })
        return state

    _locked_rmw(state_path, mutator)
    return {"after": len(new_papers), "ids_remapped": len(id_remap)}


def apply_triage(
    state_path: Path,
    triage_records: dict[str, dict[str, Any]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Apply Phase-3 triage results to state.

    `triage_records` maps `paper_id -> {tier, triage_score, triage_components}`
    where `tier ∈ {"deep", "skim", "defer"}`. The mutator:

      - writes per-paper {tier, triage_score, triage_components}
      - removes 'defer' papers from `state.selected_ids` (they stay in
        `state.papers` for citation-chase reachability)
      - auto-fills an abstract-derived evidence stub for 'skim' papers
        with depth='shallow', so G4's `depth_marks_valid` check passes
        without an agent fan-out
      - leaves 'deep' papers untouched (depth still 'shallow' from ingest;
        agents flip them to depth='full' via `evidence` after deep-read)
      - sets `state.triage_complete = True` and stores the triage `meta`

    Returns a summary dict with per-tier counts and the new selected_ids size.
    """
    summary: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        counts = {"deep": 0, "skim": 0, "defer": 0}
        for pid, rec in triage_records.items():
            paper = state["papers"].get(pid)
            if not paper:
                continue
            tier = rec.get("tier")
            if tier not in counts:
                continue
            paper["tier"] = tier
            paper["triage_score"] = rec.get("triage_score")
            paper["triage_components"] = rec.get("triage_components")
            counts[tier] += 1

            if tier == "skim":
                # Auto-derived evidence from abstract; depth=shallow so
                # G4's depth_marks_valid passes without agent fan-out.
                # If the paper already has agent-written evidence (e.g.
                # re-running triage after a manual deep-read), preserve it.
                if not paper.get("evidence"):
                    abstract = paper.get("abstract") or ""
                    paper["evidence"] = {
                        "method": "abstract-only triage (skim tier)",
                        "findings": [abstract[:500]] if abstract else [],
                        "limitations": "Skim tier — evidence derived from "
                                       "abstract only; not a deep read.",
                        "relevance": "Auto-filled by skim_papers.py; agent "
                                     "did not deep-read.",
                    }
                paper["depth"] = "shallow"

        # Refine selected_ids: drop defer tier.
        kept: list[str] = []
        for pid in state.get("selected_ids") or []:
            paper = state["papers"].get(pid)
            if paper and paper.get("tier") == "defer":
                paper["selected"] = False
                continue
            kept.append(pid)
        state["selected_ids"] = kept

        state["triage_complete"] = True
        state["triage_meta"] = meta
        summary.update({
            "counts": counts,
            "selected_ids_after": len(kept),
            "deferred_removed": (
                len(triage_records) - counts["deep"] - counts["skim"]
            ),
        })
        return state

    _locked_rmw(state_path, mutator)
    return summary


def apply_pdf_paths(
    state_path: Path,
    pdf_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Apply prefetch_pdfs.py results to state.

    `pdf_records` maps `paper_id -> { pdf_status, pdf_path?, pdf_source?,
    pdf_bytes?, pdf_url?, pdf_fetched_at?, pdf_failure_code?,
    pdf_failure_reason?, pdf_failure_retryable? }`. The mutator copies
    these onto `state.papers[<id>]` for each known paper and skips
    silently for unknown ids (a paper deleted between prefetch dispatch
    and write-back is not an error).

    Returns a summary with per-status counts and the count of unknown
    ids that were skipped.
    """
    # Stable allow-list so an attacker-shaped record cannot smuggle
    # unrelated keys onto a paper through this entry point.
    _ALLOWED_KEYS = {
        "pdf_status", "pdf_path", "pdf_source", "pdf_bytes", "pdf_url",
        "pdf_fetched_at", "pdf_failure_code", "pdf_failure_reason",
        "pdf_failure_retryable",
    }
    summary: dict[str, Any] = {"applied": 0, "unknown": 0, "by_status": {}}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        for pid, rec in pdf_records.items():
            paper = state["papers"].get(pid)
            if not paper:
                summary["unknown"] += 1
                continue
            for k, v in rec.items():
                if k == "id":
                    continue
                if k not in _ALLOWED_KEYS:
                    continue
                paper[k] = v
            summary["applied"] += 1
            status = rec.get("pdf_status") or "unknown"
            summary["by_status"][status] = (
                summary["by_status"].get(status, 0) + 1
            )
        return state

    _locked_rmw(state_path, mutator)
    return summary


def apply_citation_chase(
    state_path: Path,
    new_records: list[dict[str, Any]],
    query_entry: dict[str, Any],
) -> dict[str, Any]:
    """Merge `new_records` into state.papers and append a chase query entry.

    `query_entry` is a partial record: `source`, `query` (description), and
    optionally `round` must be provided. `hits`, `new`, `merged`, and
    `timestamp` are computed here.
    """
    summary: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        added = 0
        merged = 0
        for rec in new_records:
            pid = make_paper_id(rec)
            rec["id"] = pid
            rec.setdefault("source", ["openalex"])
            rec.setdefault(
                "first_seen_round",
                state["queries"][-1]["round"] if state["queries"] else 1,
            )
            rec["discovered_via"] = "citation_chase"
            rec.setdefault("selected", False)
            rec.setdefault("depth", "shallow")
            if pid in state["papers"]:
                existing = state["papers"][pid]
                for k in ("doi", "abstract", "pdf_url", "url", "venue"):
                    if not existing.get(k) and rec.get(k):
                        existing[k] = rec[k]
                merged += 1
            else:
                state["papers"][pid] = rec
                added += 1

        final_query = dict(query_entry)
        if "round" not in final_query:
            final_query["round"] = (
                state["queries"][-1]["round"] + 1
                if state["queries"] else 1
            )
        final_query["hits"] = len(new_records)
        final_query["new"] = added
        final_query["merged"] = merged
        final_query["timestamp"] = now_iso()
        state["queries"].append(final_query)

        summary.update({
            "added": added,
            "merged": merged,
            "total_papers": len(state["papers"]),
            "round": final_query["round"],
        })
        return state

    _locked_rmw(state_path, mutator)
    return summary
