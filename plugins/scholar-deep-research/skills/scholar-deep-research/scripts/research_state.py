#!/usr/bin/env python3
"""research_state.py — central state management for scholar-deep-research.

The state file is the single source of truth. Every other script reads from
and writes to it. Operations are idempotent on the file.

Schema (abbreviated):
{
  "schema_version": 1,
  "question": "...",
  "archetype": "literature_review",
  "phase": 0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "queries": [{"source", "query", "round", "hits", "new", "timestamp"}],
  "papers": {
    "<id>": {
      "id", "doi", "title", "authors", "year", "venue", "abstract",
      "citations", "url", "pdf_url", "source": ["openalex", ...],
      "score", "score_components": {...},
      "selected": false, "depth": "shallow|full",
      "evidence": {"method", "findings", "limitations", "relevance"},
      "discovered_via": "search|citation_chase",
      "tags": [], "first_seen_round": 1
    }
  },
  "selected_ids": [],
  "themes": [{"name", "summary", "paper_ids"}],
  "tensions": [{"topic", "sides": [{"position", "paper_ids"}]}],
  "self_critique": {"findings": [], "resolved": [], "appendix": ""},
  "report_path": null
}

Paper IDs are normalized:
  doi:10.1038/nature12373    (preferred)
  openalex:W2059403765       (fallback)
  arxiv:2301.12345           (preprints without DOI)
  pmid:12345678              (PubMed without DOI)

All commands accept --state PATH (default: research_state.json) and emit
JSON to stdout when reading, or write the state file in place when mutating.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from _common import (
    EXIT_STATE, EXIT_VALIDATION, err, maybe_emit_schema, ok,
    phase1_max_requests_per_source, phase1_max_rounds,
    reject_dry_run_with_idempotency, set_command_meta, with_idempotency,
)
from _locking import StateLockTimeout, locked_rmw

SCHEMA_VERSION = 1

# Whitelist of fields `set` is permitted to write. `papers`, `queries`,
# `self_critique`, `phase`, and everything else must be mutated through the
# dedicated commands so an agent cannot silently wipe the corpus via
# `set --field papers`, or skip a gate via `set --field phase`. Phase changes
# go through `advance`, which runs the G1..G7 gate predicates in `_gates.py`.
SETTABLE_FIELDS = {"archetype", "report_path"}


# ---------- IO ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_REQUIRED_STATE_KEYS = (
    "schema_version", "question", "archetype", "phase",
    "queries", "papers", "selected_ids", "themes", "tensions",
)


def _validate_state_shape(state: Any, path: Path) -> None:
    """Raise `state_schema_mismatch` / `state_corrupt` for malformed state.

    Checked once on every load so downstream code can assume the shape.
    Kept permissive: optional keys (ranking, self_critique, report_path,
    created_at, updated_at) are NOT required — init creates them but
    older states may pre-date a field.
    """
    if not isinstance(state, dict):
        err("state_corrupt",
            f"State file {path} did not parse to an object.",
            retryable=False, exit_code=EXIT_STATE, path=str(path))
    missing = [k for k in _REQUIRED_STATE_KEYS if k not in state]
    if missing:
        err("state_corrupt",
            f"State file {path} is missing required keys: {missing}.",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path), missing=missing)
    if state["schema_version"] != SCHEMA_VERSION:
        err("state_schema_mismatch",
            f"State schema_version {state['schema_version']} is not "
            f"supported (this code expects {SCHEMA_VERSION}). If this "
            f"state was created by a newer version, upgrade the skill; "
            f"if older, re-init after exporting papers.",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path),
            found=state["schema_version"],
            expected=SCHEMA_VERSION)
    if not isinstance(state["papers"], dict):
        err("state_corrupt",
            f"State.papers must be an object (got {type(state['papers']).__name__}).",
            retryable=False, exit_code=EXIT_STATE, path=str(path))
    if not isinstance(state["queries"], list):
        err("state_corrupt",
            f"State.queries must be an array (got {type(state['queries']).__name__}).",
            retryable=False, exit_code=EXIT_STATE, path=str(path))


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        err("state_not_found",
            f"State file not found: {path}. "
            f"Run `research_state.py init --question ...` first.",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path))
    try:
        state = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        err("state_corrupt",
            f"State file {path} is not valid JSON: {e}",
            retryable=False, exit_code=EXIT_STATE,
            path=str(path))
    _validate_state_shape(state, path)
    # Back-fill optional slices added after the state's creation. These are
    # not in `_REQUIRED_STATE_KEYS` and not version-bumped — they default
    # to empty so older state files load without intervention.
    state.setdefault("search_diagnostics", {})
    return state


def _validate_ingest_payload(payload: Any) -> None:
    """Validate a search-ingest payload before it touches state.

    Required keys: `source` (str), `query` (str), `round` (int), `papers`
    (list). Missing or wrong-typed fields raise `invalid_payload` which
    the CLI/library wrapper routes to EXIT_VALIDATION.
    """
    if not isinstance(payload, dict):
        err("invalid_payload",
            "Ingest payload must be a JSON object.",
            retryable=False, exit_code=EXIT_VALIDATION)
    required = {"source": str, "query": str, "round": int, "papers": list}
    missing = [k for k in required if k not in payload]
    if missing:
        err("invalid_payload",
            f"Ingest payload missing required keys: {missing}.",
            retryable=False, exit_code=EXIT_VALIDATION,
            missing=missing)
    for key, typ in required.items():
        if not isinstance(payload[key], typ):
            err("invalid_payload",
                f"Ingest payload field '{key}' must be {typ.__name__}, "
                f"got {type(payload[key]).__name__}.",
                retryable=False, exit_code=EXIT_VALIDATION,
                field=key,
                expected=typ.__name__,
                actual=type(payload[key]).__name__)
    for i, paper in enumerate(payload["papers"]):
        if not isinstance(paper, dict):
            err("invalid_payload",
                f"Ingest payload papers[{i}] must be an object.",
                retryable=False, exit_code=EXIT_VALIDATION,
                index=i)


def _save_state(path: Path, state: dict[str, Any]) -> None:
    """Atomic, unlocked write. Caller is responsible for locking.

    Used by `cmd_init` (where the file is created fresh under --force
    control) and by the mutator passed to `_locked_rmw` after it has
    already acquired the exclusive lock. Do NOT call from outside this
    module or without holding the state lock — use `_locked_rmw` or one
    of the public `apply_*` helpers instead.
    """
    state["updated_at"] = now_iso()
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def _locked_rmw(
    path: Path,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run `mutator` on the state file under an exclusive lock.

    The mutator receives the current state and returns the new state.
    `updated_at` is stamped automatically after the mutator returns.
    If the lock cannot be acquired within `timeout`, emits a structured
    `state_locked` error and exits with EXIT_STATE (retryable).
    """
    def _wrap(state: dict[str, Any]) -> dict[str, Any]:
        new_state = mutator(state)
        new_state["updated_at"] = now_iso()
        return new_state

    try:
        return locked_rmw(path, _wrap, timeout=timeout, loader=load_state)
    except StateLockTimeout as exc:
        err("state_locked", str(exc),
            retryable=True, exit_code=EXIT_STATE, path=str(path))


# ---------- ID normalization ----------

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip().lower()
    raw = raw.replace("https://doi.org/", "").replace("http://doi.org/", "")
    raw = raw.replace("doi:", "").strip()
    m = DOI_RE.search(raw)
    return m.group(0) if m else None


def normalize_title(title: str | None) -> str:
    """Aggressive normalization for fuzzy title match.

    Accepts None (some sources, notably Exa, deliberately emit `title=None`
    for crawler-extracted PDFs without an extractable heading) and returns
    the empty string. Without this guard one bad record would kill the
    entire ingest batch via AttributeError in the boundary validator.
    """
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def make_paper_id(paper: dict[str, Any]) -> str:
    """Pick the best canonical ID for a paper record."""
    doi = normalize_doi(paper.get("doi"))
    if doi:
        return f"doi:{doi}"
    if paper.get("openalex_id"):
        return f"openalex:{paper['openalex_id']}"
    if paper.get("arxiv_id"):
        return f"arxiv:{paper['arxiv_id']}"
    if paper.get("pmid"):
        return f"pmid:{paper['pmid']}"
    # last resort: hash of normalized title; `or ""` handles JSON null
    # which would otherwise override the .get default.
    nt = normalize_title(paper.get("title") or "")
    return f"title:{nt[:80]}"


# ---------- commands ----------

def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists():
        if not args.force:
            err("state_exists",
                f"{path} already exists. Pass --force to overwrite.",
                retryable=False, exit_code=EXIT_VALIDATION,
                path=str(path))
        # --force alone is not enough: overwriting wipes every paper,
        # query, selection, theme, tension, and the self-critique appendix.
        # Require explicit --dangerous acknowledgement so a prompt-injected
        # or confused agent cannot trivially destroy a research session.
        if not args.dangerous:
            existing_counts: dict[str, int] = {}
            try:
                prior = json.loads(path.read_text())
                existing_counts = {
                    "papers": len(prior.get("papers") or {}),
                    "queries": len(prior.get("queries") or []),
                    "selected_ids": len(prior.get("selected_ids") or []),
                    "themes": len(prior.get("themes") or []),
                    "tensions": len(prior.get("tensions") or []),
                }
            except (OSError, json.JSONDecodeError):
                existing_counts = {"unreadable": 1}
            err("confirmation_required",
                f"{path} exists. --force will DESTROY the existing state "
                f"(counts: {existing_counts}). Re-run with --force "
                f"--dangerous to confirm.",
                retryable=False, exit_code=EXIT_VALIDATION,
                path=str(path),
                existing=existing_counts,
                confirm_with="--dangerous")
    state = {
        "schema_version": SCHEMA_VERSION,
        "question": args.question,
        "archetype": args.archetype,
        "phase": 0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "queries": [],
        "papers": {},
        "selected_ids": [],
        "themes": [],
        "tensions": [],
        "self_critique": {"findings": [], "resolved": [], "appendix": ""},
        "search_diagnostics": {},
        "report_path": None,
    }
    # init writes a fresh file; no prior state to RMW. --force controls
    # overwrite races at the human/orchestrator layer, not via the lock.
    path.parent.mkdir(parents=True, exist_ok=True)
    _save_state(path, state)
    ok({"state": str(path), "phase": 0, "schema_version": SCHEMA_VERSION})


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest search results from a JSON file produced by a search script.

    Input shape: {"source": "openalex", "query": "...", "round": 1, "papers": [...]}
    """
    payload = json.loads(Path(args.input).read_text())

    def compute() -> dict[str, Any]:
        return apply_ingest(Path(args.state), payload)

    # `input` is part of the signature (different file → different result).
    # The payload content itself is not included in the signature — the file
    # path is the identity; if the file contents change under a retried key,
    # that is the caller's choice and the result is what it is. This matches
    # what gh / kubectl do with input files under --idempotency-key.
    try:
        with_idempotency(args, compute)
    except Phase1BudgetExhausted as exc:
        env_var = ("SCHOLAR_PHASE1_MAX_ROUNDS"
                   if exc.limit_kind == "max_rounds"
                   else "SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE")
        err("phase1_budget_exhausted", str(exc),
            retryable=False, exit_code=EXIT_VALIDATION,
            limit_kind=exc.limit_kind, limit=exc.limit, current=exc.current,
            source=exc.source,
            next=[
                f"# Raise the cap and retry: {env_var}={exc.limit * 2}",
                "# Or: check saturation and consider advancing to phase 2:",
                "python scripts/research_state.py saturation",
                "python scripts/research_state.py advance --check-only",
            ])


def cmd_select(args: argparse.Namespace) -> None:
    """Mark the top-N papers (by .score) as selected.

    `--include-ids id1 id2 ...` injects canonical papers the agent
    knows are seminal but ranking missed (relevance signal can be
    weak on short, hyphenated multi-word terms; clinical-domain papers
    can outrank foundational LLM-judge work on surface keyword overlap).
    Injected ids count toward `--top` and bump the lowest-scored
    auto-selected paper out so the final selection remains size N.
    Unknown ids return `unknown_paper_ids` (validation error).
    """
    chosen_ids: list[str] = []
    include_ids = list(getattr(args, "include_ids", None) or [])

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        papers = state["papers"]
        if include_ids:
            unknown = [pid for pid in include_ids if pid not in papers]
            if unknown:
                err("unknown_paper_ids",
                    f"--include-ids referenced papers not in state: {unknown}",
                    retryable=False, exit_code=EXIT_VALIDATION,
                    unknown=unknown)
        ranked = sorted(
            papers.values(),
            key=lambda p: p.get("score", 0.0),
            reverse=True,
        )
        ranked_ids = [p["id"] for p in ranked if p.get("id") not in include_ids]
        # injected ids occupy the top slots, then fill the rest by rank
        slots = max(0, args.top - len(include_ids))
        ids = list(include_ids) + ranked_ids[:slots]
        for pid, p in papers.items():
            p["selected"] = pid in ids
        state["selected_ids"] = ids
        if include_ids:
            log = state.setdefault("_selection_overrides", [])
            log.append({
                "when": now_iso(),
                "include_ids": list(include_ids),
                "top": args.top,
            })
        chosen_ids.extend(ids)
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({
        "selected": len(chosen_ids),
        "ids": chosen_ids,
        "manual_includes": include_ids or [],
    })


class SaturationInputError(Exception):
    """Raised by compute_saturation when input state is unusable.

    `code` is the stable error code to surface; `ctx` carries extra
    context fields for the envelope. Callers either route to `err()`
    (cmd_saturation) or treat as "not saturated" (gate_2).
    """

    def __init__(self, code: str, message: str, **ctx: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.ctx = ctx


def compute_saturation(
    state: dict[str, Any],
    *,
    threshold: float | None = None,
    max_citations: int | None = None,
    min_rounds: int | None = None,
    threshold_authors: float | None = None,
    threshold_venues: float | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Pure function: compute saturation per-source and overall.

    Factored out of `cmd_saturation` so gate_2 can reuse the same logic.
    Raises `SaturationInputError` for `no_queries` / `source_not_queried`
    instead of calling `err()`, so callers control the envelope (cmd_
    wraps it; gate_2 catches and treats as not-saturated).

    Three independent novelty axes — papers, authors, venues — must each
    fall under their threshold for a source to count as saturated. The
    paper axis catches "no new hits"; the author/venue axes catch the
    case where a query keeps surfacing different papers from the same
    hub of researchers or the same venue (i.e. broader exploration has
    stalled even though the paper count keeps ticking). When a source
    never reports venues (e.g. arXiv abstracts), that axis evaluates to
    None and is excluded from the AND.

    Env-var overrides (used when the corresponding kwarg is None — i.e.
    neither the CLI flag nor the gate caller forced a value): broad CS
    topics that cross subfields can fail to converge under the default
    20% threshold, so operators can relax it without code changes.

      SCHOLAR_SATURATION_NEW_PCT       (default 20.0)
      SCHOLAR_SATURATION_MAX_CITATIONS (default 100)
      SCHOLAR_SATURATION_MIN_ROUNDS    (default 2)
      SCHOLAR_SATURATION_NEW_AUTHORS_PCT (default 25.0)
      SCHOLAR_SATURATION_NEW_VENUES_PCT  (default 30.0)
    """
    if threshold is None:
        threshold = float(os.environ.get("SCHOLAR_SATURATION_NEW_PCT", 20.0))
    if max_citations is None:
        max_citations = int(os.environ.get("SCHOLAR_SATURATION_MAX_CITATIONS", 100))
    if min_rounds is None:
        min_rounds = int(os.environ.get("SCHOLAR_SATURATION_MIN_ROUNDS", 2))
    if threshold_authors is None:
        threshold_authors = float(
            os.environ.get("SCHOLAR_SATURATION_NEW_AUTHORS_PCT", 25.0))
    if threshold_venues is None:
        threshold_venues = float(
            os.environ.get("SCHOLAR_SATURATION_NEW_VENUES_PCT", 30.0))
    if not state["queries"]:
        raise SaturationInputError(
            "no_queries",
            "No queries recorded yet. Run a search first.",
        )

    by_source: dict[str, list[dict[str, Any]]] = {}
    for q in state["queries"]:
        by_source.setdefault(q["source"], []).append(q)

    if source:
        if source not in by_source:
            raise SaturationInputError(
                "source_not_queried",
                f"Source '{source}' has no queries in state.",
                source=source,
                available=sorted(by_source.keys()),
            )
        by_source = {source: by_source[source]}

    per_source: dict[str, dict[str, Any]] = {}
    for src, queries in by_source.items():
        last = queries[-1]
        last_round = last["round"]
        rounds_run = len(queries)
        hits = last.get("hits", 0) or 0
        new = last.get("new", 0) or 0
        pct_new = (new / hits * 100) if hits else 0.0
        max_cit = 0
        # Single pass: collect prior vs last-round authors/venues for this
        # source. Papers carry first_seen_round; we partition on that.
        prior_authors: set[str] = set()
        last_authors: set[str] = set()
        prior_venues: set[str] = set()
        last_venues: set[str] = set()
        for p in state["papers"].values():
            if src not in (p.get("source") or []):
                continue
            seen_round = p.get("first_seen_round")
            authors = [a for a in (p.get("authors") or []) if a]
            venue = p.get("venue") or None
            if seen_round == last_round:
                last_authors.update(authors)
                if venue:
                    last_venues.add(venue)
                max_cit = max(max_cit, p.get("citations") or 0)
            elif isinstance(seen_round, int) and seen_round < last_round:
                prior_authors.update(authors)
                if venue:
                    prior_venues.add(venue)

        all_authors = prior_authors | last_authors
        new_authors_pct: float | None
        if all_authors:
            new_authors_pct = round(
                len(last_authors - prior_authors) / len(all_authors) * 100, 1
            )
        else:
            new_authors_pct = None

        all_venues = prior_venues | last_venues
        new_venues_pct: float | None
        # Need ≥2 distinct venues for the axis to carry signal. Single-venue
        # sources (preprint servers like bioRxiv where every paper's venue is
        # "bioRxiv") would otherwise compute 0% forever and bias the AND-clause
        # toward false-saturation.
        if len(all_venues) > 1:
            new_venues_pct = round(
                len(last_venues - prior_venues) / len(all_venues) * 100, 1
            )
        else:
            new_venues_pct = None

        saturated = (
            rounds_run >= min_rounds
            and pct_new < threshold
            and max_cit < max_citations
            and (new_authors_pct is None or new_authors_pct < threshold_authors)
            and (new_venues_pct is None or new_venues_pct < threshold_venues)
        )
        per_source[src] = {
            "rounds_run": rounds_run,
            "last_round": last_round,
            "last_query": last.get("query", ""),
            "hits_last_round": hits,
            "new_last_round": new,
            "new_pct": round(pct_new, 1),
            "new_authors_pct": new_authors_pct,
            "new_venues_pct": new_venues_pct,
            "max_new_citations": max_cit,
            "saturated": saturated,
        }

    overall_saturated = bool(per_source) and all(
        ps["saturated"] for ps in per_source.values()
    )
    return {
        "per_source": per_source,
        "overall_saturated": overall_saturated,
        "threshold_pct": threshold,
        "threshold_authors_pct": threshold_authors,
        "threshold_venues_pct": threshold_venues,
        "max_citations_threshold": max_citations,
        "min_rounds": min_rounds,
    }


def cmd_saturation(args: argparse.Namespace) -> None:
    """Check whether discovery has saturated, evaluated per source.

    A single source is saturated when ALL of:
      - it has been queried at least `--min-rounds` times (default 2), AND
      - its last round's `new` count is < `--threshold`% of its last round's
        `hits`, AND
      - no paper first seen in that last round (and linked to this source)
        has more than `--max-citations` citations, AND
      - the share of brand-new authors in the last round is
        < `--threshold-authors-pct` (default 25), AND
      - the share of brand-new venues in the last round is
        < `--threshold-venues-pct` (default 30).

    The author/venue axes catch "we keep finding papers from the same hub"
    — a case the paper-pct rule alone cannot. A source that never reports
    a given axis (e.g. arXiv with no venue) reports null for that axis
    and the AND-clause skips it.

    `overall_saturated` is True only when every queried source individually
    satisfies the rule.
    """
    state = load_state(Path(args.state))
    try:
        result = compute_saturation(
            state,
            threshold=args.threshold,
            max_citations=args.max_citations,
            min_rounds=args.min_rounds,
            threshold_authors=args.threshold_authors_pct,
            threshold_venues=args.threshold_venues_pct,
            source=args.source,
        )
    except SaturationInputError as exc:
        err(exc.code, exc.message,
            retryable=False, exit_code=EXIT_VALIDATION, **exc.ctx)
    # Enrich per-source entries with end-state diagnostics so the report
    # writer can footnote "PubMed unreachable; corpus may be biased".
    # overall_saturated is left untouched — failure-only sources do not
    # block saturation (they never contributed any data to compare against).
    diagnostics = compute_source_diagnostics(state)
    for src, diag in diagnostics.items():
        existing = result["per_source"].get(src)
        if existing is None:
            # Source had only failures (or only out-of-band paper contributions
            # not paired with a query). Surface as a stub so it appears in
            # the report.
            result["per_source"][src] = {
                "rounds_run": 0,
                "last_round": None,
                "last_query": None,
                "hits_last_round": 0,
                "new_last_round": 0,
                "new_pct": None,
                "new_authors_pct": None,
                "new_venues_pct": None,
                "max_new_citations": 0,
                "saturated": None,
                "requests": diag["requests"],
                "papers_contributed": diag["papers_contributed"],
                "failures": diag["failures"],
                "last_error": diag["last_error"],
            }
        else:
            existing["requests"] = diag["requests"]
            existing["papers_contributed"] = diag["papers_contributed"]
            existing["failures"] = diag["failures"]
            existing["last_error"] = diag["last_error"]
    ok(result)


def cmd_set(args: argparse.Namespace) -> None:
    """Set a whitelisted top-level state field (phase, archetype, report_path).

    Collection fields (`papers`, `queries`, `themes`, `tensions`,
    `self_critique`) are NOT settable through this command — use the dedicated
    subcommands (`ingest`, `theme`, `tension`, `critique`, etc). This prevents
    an agent from silently wiping the corpus via `set --field papers`.
    """
    if args.field not in SETTABLE_FIELDS:
        err("field_not_settable",
            f"Field '{args.field}' is not settable via `set`. "
            f"Use the dedicated subcommand for collection fields.",
            retryable=False, exit_code=EXIT_VALIDATION,
            field=args.field,
            allowed=sorted(SETTABLE_FIELDS))
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state[args.field] = value
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"field": args.field, "value": value})


def cmd_query(args: argparse.Namespace) -> None:
    """Read a slice of state for inspection.

    All read slices return an enveloped response. List slices carry a `count`
    field so the agent does not need a follow-up call to count items.
    """
    state = load_state(Path(args.state))
    if args.what == "summary":
        ok({
            "question": state["question"],
            "archetype": state["archetype"],
            "phase": state["phase"],
            "papers": len(state["papers"]),
            "selected": len(state["selected_ids"]),
            "queries": len(state["queries"]),
            "themes": len(state["themes"]),
            "tensions": len(state["tensions"]),
            "report_path": state.get("report_path"),
        })
        return
    if args.what == "selected":
        items = [state["papers"][pid] for pid in state["selected_ids"]
                 if pid in state["papers"]]
    elif args.what == "papers":
        items = list(state["papers"].values())
    elif args.what == "queries":
        items = state["queries"]
    elif args.what == "themes":
        items = state["themes"]
    elif args.what == "tensions":
        items = state["tensions"]
    elif args.what == "critique":
        ok(state.get("self_critique",
                     {"findings": [], "resolved": [], "appendix": ""}))
        return
    elif args.what == "diagnostics":
        ok(compute_source_diagnostics(state))
        return
    else:
        err("unknown_query",
            f"Unknown query target: {args.what}",
            retryable=False, exit_code=EXIT_VALIDATION,
            what=args.what)
    ok(items, count=len(items), has_more=False)


def cmd_status(args: argparse.Namespace) -> None:
    """Compact "where am I, what's next" summary.

    Returns a flat dict so agents can call this once at the top of a
    session to learn the phase + counts + the next gate's pending
    checks without chaining `query summary` + `saturation` +
    `advance --check-only`. Read-only; never mutates state.

    The `next_gate` block carries the result of evaluating the gate
    for `current_phase + 1` against current state. `next_commands`
    surfaces the same hint list that a failed `advance` would produce,
    so an agent can read this envelope and act without a second call.
    """
    from _gates import GATES, next_hints_for

    state = load_state(Path(args.state))

    papers = state.get("papers") or {}
    selected_ids = state.get("selected_ids") or []
    selected = [papers[pid] for pid in selected_ids if pid in papers]

    by_tier: dict[str, int] = {}
    by_depth: dict[str, int] = {}
    for p in selected:
        tier = p.get("tier") or "untriaged"
        by_tier[tier] = by_tier.get(tier, 0) + 1
        depth = p.get("depth") or "missing"
        by_depth[depth] = by_depth.get(depth, 0) + 1

    queries = state.get("queries") or []
    by_source: dict[str, int] = {}
    for q in queries:
        s = q.get("source") or "unknown"
        by_source[s] = by_source.get(s, 0) + 1

    crit = state.get("self_critique") or {}

    current = state.get("phase", 0)
    target = current + 1
    next_gate_info: dict[str, Any] | None = None
    next_hint_cmds: list[str] = []
    if target in GATES:
        gate_fn = GATES[target]
        try:
            if target == 2:
                result = gate_fn(
                    state, compute_saturation=compute_saturation)
            else:
                result = gate_fn(state)
            failing = [c.name for c in result.checks if not c.ok]
            next_gate_info = {
                "target": target,
                "met": result.met,
                "failing_checks": failing,
            }
            if not result.met:
                next_hint_cmds = next_hints_for(result.checks, args.state)
        except Exception:
            # Partial state can make gate compute raise (e.g. saturation
            # before any query). Status must never throw — leave the
            # block None so callers can still see the rest of the
            # snapshot.
            pass

    ok({
        "phase": current,
        "archetype": state.get("archetype"),
        "question": state.get("question"),
        "papers": {
            "total": len(papers),
            "selected": len(selected_ids),
            "by_tier": by_tier,
            "by_depth": by_depth,
        },
        "queries": {
            "total": len(queries),
            "by_source": by_source,
        },
        "synthesis": {
            "themes": len(state.get("themes") or []),
            "tensions": len(state.get("tensions") or []),
        },
        "critique": {
            "findings": len(crit.get("findings") or []),
            "resolved": len(crit.get("resolved") or []),
            "appendix_populated": bool(crit.get("appendix")),
        },
        "report_path": state.get("report_path"),
        "next_gate": next_gate_info,
        "next_commands": next_hint_cmds,
    })


def cmd_evidence(args: argparse.Namespace) -> None:
    """Attach evidence (extracted reading) to a paper.

    Two mutually-exclusive input modes:

      - **structured**: `--method "..." --findings "a" "b" --limitations "..."
        --relevance "..."`. The original path; works fine for short single
        invocations.

      - **JSON**: `--from-json <path>` or `--from-json -` (stdin). Payload
        shape: `{"method": str, "findings": [str], "limitations": str,
        "relevance": str, "depth": "full"|"shallow"}`. Built for parallel
        agents that compose evidence in Python — skipping the multi-quote
        shell escape dance is the entire reason this path exists. The
        Phase 3 sub-agent fan-out hits ~10x the JSON path each session.

    Mixing the two modes is rejected (`inconsistent_input`) so the
    precedence rule cannot become a silent footgun.
    """
    if args.from_json is not None:
        passed_structured = any(getattr(args, f) is not None for f in
                                ("method", "findings", "limitations",
                                 "relevance"))
        if passed_structured:
            err("inconsistent_input",
                "--from-json is mutually exclusive with --method / "
                "--findings / --limitations / --relevance. Pick one mode.",
                retryable=False, exit_code=EXIT_VALIDATION)
        try:
            if args.from_json == "-":
                raw = sys.stdin.read()
            else:
                raw = Path(args.from_json).read_text()
        except (FileNotFoundError, OSError) as e:
            err("from_json_unreadable",
                f"--from-json source '{args.from_json}' could not be read: {e}",
                retryable=False, exit_code=EXIT_VALIDATION,
                source=args.from_json)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            err("invalid_json",
                f"--from-json payload is not valid JSON: {e}",
                retryable=False, exit_code=EXIT_VALIDATION,
                source=args.from_json)
        if not isinstance(payload, dict):
            err("invalid_json",
                "--from-json payload must be a JSON object, not "
                f"{type(payload).__name__}.",
                retryable=False, exit_code=EXIT_VALIDATION,
                source=args.from_json)
        method = payload.get("method")
        # JSON's depth wins over the argparse default; if absent, fall
        # back to the explicit --depth flag (which itself defaults to
        # "full" via argparse).
        depth = payload.get("depth", args.depth)
        findings = payload.get("findings") or []
        limitations = payload.get("limitations") or ""
        relevance = payload.get("relevance") or ""
    else:
        if not args.method:
            err("missing_field",
                "--method is required (or use --from-json to supply via JSON).",
                retryable=False, exit_code=EXIT_VALIDATION,
                field="method")
        method = args.method
        depth = args.depth
        findings = args.findings or []
        limitations = args.limitations or ""
        relevance = args.relevance or ""

    if not isinstance(method, str) or not method.strip():
        err("missing_field",
            "evidence.method must be a non-empty string.",
            retryable=False, exit_code=EXIT_VALIDATION, field="method")
    if not isinstance(findings, list) or not all(
            isinstance(f, str) for f in findings):
        err("invalid_field",
            "evidence.findings must be a list of strings.",
            retryable=False, exit_code=EXIT_VALIDATION, field="findings")
    if depth not in ("full", "shallow"):
        err("invalid_field",
            f"evidence.depth must be 'full' or 'shallow', not {depth!r}.",
            retryable=False, exit_code=EXIT_VALIDATION, field="depth",
            allowed=["full", "shallow"])

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        if args.id not in state["papers"]:
            err("unknown_paper_id",
                f"No paper in state with id '{args.id}'.",
                retryable=False, exit_code=EXIT_VALIDATION,
                id=args.id)
        paper = state["papers"][args.id]
        paper["evidence"] = {
            "method": method,
            "findings": findings,
            "limitations": limitations,
            "relevance": relevance,
        }
        paper["depth"] = depth
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"id": args.id, "depth": depth})


def cmd_theme(args: argparse.Namespace) -> None:
    total = [0]

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["themes"].append({
            "name": args.name,
            "summary": args.summary or "",
            "paper_ids": args.paper_ids or [],
        })
        total[0] = len(state["themes"])
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"theme": args.name, "total_themes": total[0]})


def cmd_tension(args: argparse.Namespace) -> None:
    try:
        sides = json.loads(args.sides)
    except json.JSONDecodeError as e:
        err("invalid_json",
            f"--sides is not valid JSON: {e}",
            retryable=False, exit_code=EXIT_VALIDATION,
            field="sides")
    total = [0]

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        state["tensions"].append({
            "topic": args.topic,
            "sides": sides,
        })
        total[0] = len(state["tensions"])
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"topic": args.topic, "total_tensions": total[0]})


def cmd_advance(args: argparse.Namespace) -> None:
    """Advance the phase by one, iff the gate for the target phase is met.

    Replaces the former `set --field phase <N>` path, which let hosts skip
    gates. The target is always `current + 1`; `--to` is accepted only for
    forward compatibility (must equal current + 1) and to make intent
    explicit in logs. `--check-only` runs the gate without writing.
    """
    # Import lazily so `--schema` works on machines where `_gates.py` is
    # still absent (shouldn't happen, but harmless).
    from _gates import GATES, next_hints_for

    state = load_state(Path(args.state))
    current = state.get("phase", 0)
    target = args.to if args.to is not None else current + 1

    # Phase 7 (Report) is terminal — there is no G8. Return a positive
    # envelope so agents that loop on `advance` until "ok" don't see this
    # as an error and so the human reading the envelope gets a clear
    # "you're done" signal instead of `unknown_gate`.
    max_phase = max(GATES.keys())
    if current >= max_phase and (args.to is None or args.to == current):
        ok({
            "advanced": False,
            "from": current,
            "to": current,
            "at_terminal_phase": True,
            "message": (
                f"Phase {current} is the terminal phase. Render is the final "
                "step — run `python scripts/render_report.py --state <state>` "
                "to produce the report (and `--lint` once you've filled the "
                "AGENT prose slots)."
            ),
        })
        return

    if target <= current:
        err("phase_not_advancing",
            f"Cannot advance to phase {target} from current phase {current}. "
            f"Target must be current+1. Use `init --force` to reset.",
            retryable=False, exit_code=EXIT_VALIDATION,
            current=current, requested=target)
    if target - current > 1:
        err("phase_skip_forbidden",
            f"Cannot skip gates: target phase {target} is more than one "
            f"step past current phase {current}. Advance one gate at a time.",
            retryable=False, exit_code=EXIT_VALIDATION,
            current=current, requested=target)
    if target not in GATES:
        err("unknown_gate",
            f"No gate defined for target phase {target}. "
            f"Valid targets: {sorted(GATES.keys())}.",
            retryable=False, exit_code=EXIT_VALIDATION,
            requested=target, valid=sorted(GATES.keys()))

    # gate_2 needs compute_saturation; others don't — pass it as kwarg when
    # the gate's signature expects it.
    gate_fn = GATES[target]
    if target == 2:
        result = gate_fn(state, compute_saturation=compute_saturation)
    else:
        result = gate_fn(state)

    if not result.met:
        failures = [c.name for c in result.checks if not c.ok]
        next_cmds = next_hints_for(result.checks, args.state)
        err("gate_not_met",
            f"Gate G{target} for phase {current} → {target} is not met. "
            f"Failing checks: {failures}.",
            retryable=False, exit_code=EXIT_VALIDATION,
            gate=result.to_dict(),
            current=current, target=target,
            next=next_cmds)

    if args.check_only:
        ok({"check_only": True, "gate": result.to_dict(),
            "current": current, "target": target, "met": True})
        return

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        # Re-check current phase under the lock to avoid TOCTOU: another
        # process could have advanced while we were computing the gate.
        if state.get("phase", 0) != current:
            err("phase_raced",
                f"Phase changed under the lock (was {current}, now "
                f"{state.get('phase')}). Re-run advance.",
                retryable=True, exit_code=EXIT_STATE,
                current_actual=state.get("phase"), expected=current)
        state["phase"] = target
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"advanced": True, "from": current, "to": target,
        "gate": result.to_dict()})


def cmd_rank(args: argparse.Namespace) -> None:
    """Apply a ranking patch produced by rank_papers.py.

    Patch shape: {"scored_papers": {pid: {score, score_components}}, "meta": {...}}.
    This subcommand is for replay/audit — normal use is via rank_papers.py,
    which calls apply_ranking() directly.
    """
    reject_dry_run_with_idempotency(args)
    patch = json.loads(Path(args.patch).read_text())
    if args.dry_run:
        ok({
            "dry_run": True,
            "would_apply": {
                "scored_papers": len(patch.get("scored_papers") or {}),
                "meta": patch.get("meta") or {},
            },
        })
        return

    def compute() -> dict[str, Any]:
        return apply_ranking(
            Path(args.state),
            patch.get("scored_papers") or {},
            patch.get("meta") or {},
        )

    with_idempotency(args, compute)


def cmd_dedupe(args: argparse.Namespace) -> None:
    """Apply a dedupe patch produced by dedupe_papers.py.

    Patch shape: {"new_papers": {pid: paper}, "id_remap": {old_id: new_id}}.
    """
    reject_dry_run_with_idempotency(args)
    patch = json.loads(Path(args.patch).read_text())
    if args.dry_run:
        ok({
            "dry_run": True,
            "would_apply": {
                "new_papers": len(patch.get("new_papers") or {}),
                "ids_remapped": len(patch.get("id_remap") or {}),
            },
        })
        return

    def compute() -> dict[str, Any]:
        return apply_dedupe(
            Path(args.state),
            patch.get("new_papers") or {},
            patch.get("id_remap") or {},
        )

    with_idempotency(args, compute)


def cmd_citation_chase(args: argparse.Namespace) -> None:
    """Apply a citation-chase patch produced by build_citation_graph.py.

    Patch shape: {"new_records": [...], "query_entry": {source, query, ...}}.
    """
    reject_dry_run_with_idempotency(args)
    patch = json.loads(Path(args.patch).read_text())
    if args.dry_run:
        ok({
            "dry_run": True,
            "would_apply": {
                "new_records": len(patch.get("new_records") or []),
                "query_entry": patch.get("query_entry") or {},
            },
        })
        return

    def compute() -> dict[str, Any]:
        return apply_citation_chase(
            Path(args.state),
            patch.get("new_records") or [],
            patch.get("query_entry") or {},
        )

    with_idempotency(args, compute)


def cmd_triage(args: argparse.Namespace) -> None:
    """Apply a triage patch produced by skim_papers.py.

    Patch shape: {"triage_records": {pid: {tier, triage_score, triage_components}},
                  "meta": {...}}.
    Normal usage is via skim_papers.py, which calls apply_triage() directly.
    This subcommand is for replay/audit when a patch has been saved.
    """
    reject_dry_run_with_idempotency(args)
    patch = json.loads(Path(args.patch).read_text())
    if args.dry_run:
        recs = patch.get("triage_records") or {}
        ok({
            "dry_run": True,
            "would_apply": {
                "triage_records": len(recs),
                "meta": patch.get("meta") or {},
            },
        })
        return

    def compute() -> dict[str, Any]:
        return apply_triage(
            Path(args.state),
            patch.get("triage_records") or {},
            patch.get("meta") or {},
        )

    with_idempotency(args, compute)


def cmd_prefetch(args: argparse.Namespace) -> None:
    """Apply a prefetch_pdfs patch produced by prefetch_pdfs.py.

    Patch shape: {"pdf_records": {pid: {pdf_status, pdf_path?, ...}}}.
    Normal usage is via prefetch_pdfs.py, which calls apply_pdf_paths()
    directly. This subcommand exists for replay/audit when a patch has
    been saved out-of-band.
    """
    reject_dry_run_with_idempotency(args)
    patch = json.loads(Path(args.patch).read_text())
    if args.dry_run:
        recs = patch.get("pdf_records") or {}
        ok({
            "dry_run": True,
            "would_apply": {"pdf_records": len(recs)},
        })
        return

    def compute() -> dict[str, Any]:
        return apply_pdf_paths(
            Path(args.state),
            patch.get("pdf_records") or {},
        )

    with_idempotency(args, compute)


def cmd_critique(args: argparse.Namespace) -> None:
    final_crit: dict[str, Any] = {}

    def mutator(state: dict[str, Any]) -> dict[str, Any]:
        crit = state.setdefault("self_critique",
                                {"findings": [], "resolved": [], "appendix": ""})
        if args.finding:
            crit["findings"].append(args.finding)
        if args.resolve:
            crit["resolved"].append(args.resolve)
        if args.appendix:
            crit["appendix"] = args.appendix
        final_crit.update(crit)
        return state

    _locked_rmw(Path(args.state), mutator)
    ok({"critique": final_crit})


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research_state.py",
        description="Central state file management for scholar-deep-research.",
    )
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="Path to the state file "
             "(env: SCHOLAR_STATE_PATH, default: research_state.json)",
    )
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Create a new state file")
    s.add_argument("--question", required=True)
    s.add_argument("--archetype", default="literature_review",
                   choices=["literature_review", "systematic_review",
                            "scoping_review", "comparative_analysis",
                            "grant_background"])
    s.add_argument("--force", action="store_true",
                   help="Overwrite an existing state file. DESTRUCTIVE. "
                        "Must be paired with --dangerous.")
    s.add_argument("--dangerous", action="store_true",
                   help="Explicit acknowledgement required alongside --force. "
                        "Without it, --force returns a confirmation_required "
                        "envelope listing what would be destroyed.")
    set_command_meta(s, since="0.1.0", tier="write",
                     dangerous_if="force + dangerous")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("ingest", help="Ingest search results from a JSON file")
    s.add_argument("--input", required=True)
    s.add_argument("--idempotency-key",
                   help="Retry-safe key. Retried calls with the same key "
                        "return the original result. Mismatched args with "
                        "the same key returns idempotency_key_mismatch.")
    set_command_meta(s, since="0.1.0", tier="write")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("select", help="Mark top-N (by score) as selected")
    s.add_argument("--top", type=int, default=20)
    s.add_argument(
        "--include-ids", nargs="*", default=None,
        help="Paper ids to inject into the selection regardless of rank "
             "(e.g. canonical papers the relevance signal missed). Each "
             "injected id occupies one of the --top slots; the lowest-rank "
             "auto-selections drop. Unknown ids return validation error.",
    )
    set_command_meta(s, since="0.13.0", tier="write")
    s.set_defaults(func=cmd_select)

    s = sub.add_parser("saturation",
                       help="Check whether discovery saturated (per source)")
    # Defaults are None so compute_saturation falls through to env-var
    # overrides (SCHOLAR_SATURATION_*) and then its own defaults. Pass an
    # explicit flag to force a value above any env-var override.
    s.add_argument("--threshold", type=float, default=None,
                   help="New-paper percentage below which a source is "
                        "considered saturated (default 20; "
                        "env: SCHOLAR_SATURATION_NEW_PCT). Raise for "
                        "broad CS topics where the default never converges.")
    s.add_argument("--max-citations", type=int, default=None,
                   help="If a new paper has more citations than this, the "
                        "source is NOT saturated (default 100; "
                        "env: SCHOLAR_SATURATION_MAX_CITATIONS).")
    s.add_argument("--min-rounds", type=int, default=None,
                   help="Minimum rounds before a source can be called "
                        "saturated. Prevents declaring saturation on a "
                        "single-query source (default 2; "
                        "env: SCHOLAR_SATURATION_MIN_ROUNDS).")
    s.add_argument("--threshold-authors-pct", type=float, default=None,
                   help="Brand-new-author share below which the author "
                        "axis is considered saturated (default 25; "
                        "env: SCHOLAR_SATURATION_NEW_AUTHORS_PCT). "
                        "Looser than --threshold because authors recur "
                        "more naturally than papers.")
    s.add_argument("--threshold-venues-pct", type=float, default=None,
                   help="Brand-new-venue share below which the venue "
                        "axis is considered saturated (default 30; "
                        "env: SCHOLAR_SATURATION_NEW_VENUES_PCT). "
                        "Sources without venue metadata report null and "
                        "skip this axis.")
    s.add_argument("--source",
                   help="Check a single source only (default: all sources)")
    s.set_defaults(func=cmd_saturation)

    s = sub.add_parser(
        "set",
        help=f"Set a whitelisted top-level field ({sorted(SETTABLE_FIELDS)})",
    )
    s.add_argument("--field", required=True)
    s.add_argument("--value", required=True)
    s.set_defaults(func=cmd_set)

    s = sub.add_parser(
        "advance",
        help="Advance phase by one if the target gate (G1..G7) passes.",
    )
    s.add_argument("--to", type=int,
                   help="Explicit target phase (must be current+1). "
                        "Omit to advance by one.")
    s.add_argument("--check-only", action="store_true",
                   help="Run the gate, emit the result, do NOT write.")
    set_command_meta(s, since="0.4.0", tier="write")
    s.set_defaults(func=cmd_advance)

    s = sub.add_parser("query", help="Read a slice of state")
    s.add_argument("what", choices=["summary", "selected", "papers", "queries",
                                    "themes", "tensions", "critique",
                                    "diagnostics"])
    s.set_defaults(func=cmd_query)

    s = sub.add_parser(
        "status",
        help='Compact "where am I, what\'s next" snapshot (read-only)')
    set_command_meta(s, since="0.10.0", tier="read")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("evidence", help="Attach evidence to a paper")
    s.add_argument("--id", required=True)
    s.add_argument("--method",
                   help="Required unless --from-json is given.")
    s.add_argument("--findings", nargs="*")
    s.add_argument("--limitations")
    s.add_argument("--relevance")
    s.add_argument("--depth", choices=["full", "shallow"], default="full")
    s.add_argument(
        "--from-json",
        help="Read {method,findings,limitations,relevance[,depth]} from "
             "this JSON file. Use '-' for stdin. Mutually exclusive with "
             "--method/--findings/--limitations/--relevance.")
    set_command_meta(s, since="0.10.0", tier="write")
    s.set_defaults(func=cmd_evidence)

    # Replay/audit subcommands: apply a pre-computed patch from a JSON file.
    # Normal usage is via rank_papers.py / dedupe_papers.py / build_citation_graph.py,
    # which call the apply_* functions directly. These exist so a failed
    # mutation can be replayed from the patch file without re-running the
    # (sometimes network-bound) compute step.
    s = sub.add_parser("rank", help="Apply a ranking patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.add_argument("--dry-run", action="store_true",
                   help="Report patch size without mutating state.")
    s.add_argument("--idempotency-key",
                   help="Retry-safe key (see ingest --idempotency-key).")
    set_command_meta(s, since="0.4.0", tier="write")
    s.set_defaults(func=cmd_rank)

    s = sub.add_parser("dedupe", help="Apply a dedupe patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.add_argument("--dry-run", action="store_true",
                   help="Report patch size without mutating state.")
    s.add_argument("--idempotency-key",
                   help="Retry-safe key (see ingest --idempotency-key).")
    set_command_meta(s, since="0.4.0", tier="write")
    s.set_defaults(func=cmd_dedupe)

    s = sub.add_parser("citation-chase", help="Apply a citation-chase patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.add_argument("--dry-run", action="store_true",
                   help="Report patch size without mutating state.")
    s.add_argument("--idempotency-key",
                   help="Retry-safe key (see ingest --idempotency-key).")
    set_command_meta(s, since="0.4.0", tier="write")
    s.set_defaults(func=cmd_citation_chase)

    s = sub.add_parser("triage", help="Apply a Phase-3 triage patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.add_argument("--dry-run", action="store_true",
                   help="Report patch size without mutating state.")
    s.add_argument("--idempotency-key",
                   help="Retry-safe key (see ingest --idempotency-key).")
    set_command_meta(s, since="0.7.0", tier="write")
    s.set_defaults(func=cmd_triage)

    s = sub.add_parser("prefetch", help="Apply a PDF-prefetch patch JSON")
    s.add_argument("--patch", required=True, help="Patch JSON file path")
    s.add_argument("--dry-run", action="store_true",
                   help="Report patch size without mutating state.")
    s.add_argument("--idempotency-key",
                   help="Retry-safe key (see ingest --idempotency-key).")
    set_command_meta(s, since="0.8.0", tier="write")
    s.set_defaults(func=cmd_prefetch)

    s = sub.add_parser("theme", help="Add a theme")
    s.add_argument("--name", required=True)
    s.add_argument("--summary")
    s.add_argument("--paper-ids", nargs="*")
    s.set_defaults(func=cmd_theme)

    s = sub.add_parser("tension", help="Add a tension")
    s.add_argument("--topic", required=True)
    s.add_argument("--sides", required=True,
                   help='JSON array: [{"position": "...", "paper_ids": ["..."]}]')
    s.set_defaults(func=cmd_tension)

    s = sub.add_parser("critique", help="Append a self-critique finding/appendix")
    s.add_argument("--finding")
    s.add_argument("--resolve")
    s.add_argument("--appendix")
    s.set_defaults(func=cmd_critique)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    maybe_emit_schema(parser, "research_state", argv)
    args = parser.parse_args(argv)
    args.func(args)


# ---------- library API re-exports ----------
#
# The mutating apply_* helpers now live in `state_apply.py` to keep this
# module focused on CLI dispatch + low-level helpers. Re-exporting here
# preserves the public import surface every caller already uses:
#
#     from research_state import apply_ingest, apply_ranking, ...
#
# Two delicate bits make the circular import resolve cleanly:
#
# 1. This `from state_apply import ...` sits at the bottom of the file,
#    AFTER every helper state_apply needs (`_locked_rmw`,
#    `_validate_ingest_payload`, `make_paper_id`, `now_iso`) is defined.
#
# 2. When `python research_state.py` is invoked directly, the module is
#    registered in `sys.modules` as `__main__`, not `research_state`. So
#    state_apply's `from research_state import _locked_rmw` would re-load
#    the file and recurse forever. The line below aliases the running
#    module under the name `research_state` so state_apply finds the
#    already-loaded (partially initialized) module instead.
import sys as _sys  # noqa: E402
_sys.modules.setdefault("research_state", _sys.modules[__name__])

from state_apply import (  # noqa: E402, F401  (re-export — names look unused locally)
    Phase1BudgetExhausted,
    apply_citation_chase,
    apply_dedupe,
    apply_ingest,
    apply_pdf_paths,
    apply_ranking,
    apply_search_failure,
    apply_triage,
    compute_source_diagnostics,
)


if __name__ == "__main__":
    main()
