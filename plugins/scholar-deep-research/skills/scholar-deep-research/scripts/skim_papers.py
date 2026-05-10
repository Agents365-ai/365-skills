#!/usr/bin/env python3
"""skim_papers.py — assign deep/skim/defer triage tier to each selected paper.

Phase 3 acceleration: not every selected paper deserves a full deep-read agent
dispatch. Score selected papers on cheap deterministic signals (no LLM, no
network), then split them into tiers:

  tier=deep   → top of the score distribution; dispatched in parallel to
                agents for full PDF + evidence extraction (depth=full).
  tier=skim   → next slice; evidence stub auto-derived from the abstract by
                `apply_triage()` (depth=shallow, no agent fan-out).
  tier=defer  → bottom slice (opt-in via deep+skim < 1.0); removed from
                state.selected_ids entirely. Stays in the corpus and may
                still appear via citation chase.

Defaults: --deep-ratio 0.5, --skim-ratio 0.5 (no defer). Tune lower for more
aggressive cost cuts: --deep-ratio 0.3 --skim-ratio 0.5 leaves 20% deferred.

Signals (each component ∈ [0,1]):
  - relevance        : token overlap between question and title+abstract
  - citation_density : citations / years_since_publication, capped at 1.0
  - recency          : exp(-Δyears / half_life)
  - has_pdf          : 1.0 if pdf_url or doi present, 0.5 otherwise
  - abstract_quality : 0 if missing, 0.5 if <200 chars, 1.0 otherwise (folded
                       into relevance multiplicatively so a missing abstract
                       cannot inflate score off title alone)

Score = 0.4·relevance·abstract_quality
      + 0.3·citation_density
      + 0.2·recency
      + 0.1·has_pdf

The triage patch is applied via research_state.apply_triage(), which writes
per-paper {tier, triage_score, triage_components}, refines selected_ids by
removing 'defer' tier, auto-fills evidence-from-abstract for the 'skim' tier,
and sets state.triage_complete=true so gate G3 can pass.
"""
from __future__ import annotations

import argparse
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from _common import (
    EXIT_VALIDATION, err, maybe_emit_schema, reject_dry_run_with_idempotency,
    set_command_meta, with_idempotency,
)
from research_state import apply_triage, load_state


def tokenize(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def relevance(question: str, paper: dict[str, Any]) -> float:
    qtok = tokenize(question)
    if not qtok:
        return 0.0
    haystack = " ".join([paper.get("title") or "", paper.get("abstract") or ""])
    htok = tokenize(haystack)
    if not htok:
        return 0.0
    return len(qtok & htok) / max(len(qtok), 1)


def abstract_quality(paper: dict[str, Any]) -> float:
    abstract = paper.get("abstract") or ""
    n = len(abstract)
    if n == 0:
        return 0.0
    if n < 200:
        return 0.5
    return 1.0


def citation_density(citations: int | None, year: int | None,
                     now_year: int) -> float:
    """citations per year since publication, capped at 1.0 (≈20/yr full credit)."""
    c = citations or 0
    if not year:
        return 0.0
    delta = max(1, now_year - year + 1)  # +1 so brand-new papers don't blow up
    per_year = c / delta
    return min(per_year / 20.0, 1.0)


def recency(year: int | None, half_life: float, now_year: int) -> float:
    if not year:
        return 0.0
    delta = max(0, now_year - year)
    return math.exp(-delta / half_life)


def has_pdf_signal(paper: dict[str, Any]) -> float:
    if paper.get("pdf_url") or paper.get("doi"):
        return 1.0
    return 0.5


def score_paper(paper: dict[str, Any], question: str,
                half_life: float, now_year: int) -> dict[str, Any]:
    rel = relevance(question, paper)
    aq = abstract_quality(paper)
    cd = citation_density(paper.get("citations"), paper.get("year"), now_year)
    rec = recency(paper.get("year"), half_life, now_year)
    pdf = has_pdf_signal(paper)
    score = 0.4 * rel * aq + 0.3 * cd + 0.2 * rec + 0.1 * pdf
    return {
        "score": round(score, 4),
        "components": {
            "relevance": round(rel, 4),
            "abstract_quality": round(aq, 4),
            "citation_density": round(cd, 4),
            "recency": round(rec, 4),
            "has_pdf": round(pdf, 4),
        },
    }


def assign_tiers(scored: list[tuple[str, dict[str, Any]]],
                 deep_ratio: float, skim_ratio: float) -> dict[str, str]:
    """Sort by score desc and slice into tiers by ratio.

    Returns {paper_id -> tier}. Any paper not in deep+skim falls to 'defer'.
    """
    n = len(scored)
    if n == 0:
        return {}
    ordered = sorted(scored, key=lambda kv: kv[1]["score"], reverse=True)
    deep_n = round(n * deep_ratio)
    skim_n = round(n * skim_ratio)
    # Clamp: deep+skim cannot exceed N
    if deep_n + skim_n > n:
        skim_n = max(0, n - deep_n)
    tiers: dict[str, str] = {}
    for i, (pid, _) in enumerate(ordered):
        if i < deep_n:
            tiers[pid] = "deep"
        elif i < deep_n + skim_n:
            tiers[pid] = "skim"
        else:
            tiers[pid] = "defer"
    return tiers


def main() -> None:
    p = argparse.ArgumentParser(
        description="Triage selected papers into deep/skim/defer tiers for "
                    "Phase 3 deep-read fan-out.",
    )
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--question",
                   help="Override the question used for relevance "
                        "(default: state.question)")
    p.add_argument("--deep-ratio", type=float, default=0.5,
                   help="Fraction of selected papers that go to the deep tier "
                        "(default 0.5). Top of score distribution.")
    p.add_argument("--skim-ratio", type=float, default=0.5,
                   help="Fraction that go to the skim tier (default 0.5). "
                        "Mid slice; abstract-derived evidence stub auto-filled.")
    p.add_argument("--half-life", type=float, default=5.0,
                   help="Recency decay half-life in years (default 5)")
    p.add_argument("--dry-run", action="store_true",
                   help="Score and preview tiers; do NOT write to state.")
    p.add_argument("--idempotency-key",
                   help="Retry-safe key. Retried calls with the same key "
                        "return the original result without re-mutating state.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    set_command_meta(p, since="0.7.0", tier="write")
    maybe_emit_schema(p, "skim_papers")
    args = p.parse_args()
    reject_dry_run_with_idempotency(args)

    if args.deep_ratio < 0 or args.skim_ratio < 0:
        err("invalid_ratio",
            "Ratios must be non-negative.",
            retryable=False, exit_code=EXIT_VALIDATION,
            deep_ratio=args.deep_ratio, skim_ratio=args.skim_ratio)
    if args.deep_ratio + args.skim_ratio > 1.0 + 1e-9:
        err("invalid_ratio",
            f"deep_ratio + skim_ratio = {args.deep_ratio + args.skim_ratio} "
            f"must be ≤ 1.0. The remainder goes to the defer tier.",
            retryable=False, exit_code=EXIT_VALIDATION,
            deep_ratio=args.deep_ratio, skim_ratio=args.skim_ratio)

    path = Path(args.state)
    state = load_state(path)
    question = args.question or state.get("question") or ""
    selected = state.get("selected_ids") or []
    if not selected:
        err("no_selection",
            "state.selected_ids is empty. Run `research_state.py select` "
            "after `rank_papers.py` first.",
            retryable=False, exit_code=EXIT_VALIDATION)

    now = datetime.now().year
    scored: dict[str, dict[str, Any]] = {}
    for pid in selected:
        paper = state["papers"].get(pid)
        if not paper:
            continue
        scored[pid] = score_paper(paper, question, args.half_life, now)

    tiers = assign_tiers(list(scored.items()),
                         deep_ratio=args.deep_ratio,
                         skim_ratio=args.skim_ratio)
    triage_records: dict[str, dict[str, Any]] = {}
    for pid, scoring in scored.items():
        triage_records[pid] = {
            "tier": tiers[pid],
            "triage_score": scoring["score"],
            "triage_components": scoring["components"],
        }

    counts = {"deep": 0, "skim": 0, "defer": 0}
    for pid, rec in triage_records.items():
        counts[rec["tier"]] += 1

    preview_top = sorted(
        triage_records.items(),
        key=lambda kv: kv[1]["triage_score"],
        reverse=True,
    )
    deep_titles = [
        {
            "id": pid,
            "tier": rec["tier"],
            "score": rec["triage_score"],
            "title": (state["papers"].get(pid) or {}).get("title"),
        }
        for pid, rec in preview_top
        if rec["tier"] == "deep"
    ]

    meta = {
        "weights": {
            "relevance": 0.4, "citation_density": 0.3,
            "recency": 0.2, "has_pdf": 0.1,
        },
        "half_life": args.half_life,
        "deep_ratio": args.deep_ratio,
        "skim_ratio": args.skim_ratio,
        "triaged_at": datetime.now().isoformat(timespec="seconds"),
    }

    response = {
        "triaged": len(triage_records),
        "counts": counts,
        "deep_tier_preview": deep_titles,
        "weights": meta["weights"],
    }

    if args.dry_run:
        response["dry_run"] = True
        from _common import ok
        ok(response)
        return

    def compute() -> dict[str, Any]:
        apply_triage(path, triage_records, meta)
        return response

    with_idempotency(args, compute)


if __name__ == "__main__":
    main()
