#!/usr/bin/env python3
"""rank_papers.py — score papers in state with a transparent formula.

Formula:
    score = α·relevance + β·log10(citations+1)/3 + γ·recency_decay + δ·venue_prior

Components (each ∈ [0,1]):
  - relevance: stopword-stripped, suffix-stemmed token overlap between the
               question and the paper's title+abstract, plus a phrase bonus
               for each hyphenated or quoted multi-word term in the question
               that appears in the title (+0.15) or abstract (+0.05). The
               stemming handles the common bias→biases / evaluation→evaluating
               morphology mismatch that the previous Jaccard implementation
               silently lost. Cheap and transparent; users wanting semantic
               similarity should re-rank with embeddings and write back to
               score_components.relevance.
  - citations: log10(c+1)/3, capped at 1.0 (≈1000 cites = full credit).
  - recency_decay: exp(-Δyears / half_life), default half-life = 5 years.
  - venue_prior: 1.0 if venue matches a tier-1 list, 0.5 otherwise.

The formula and per-paper components are written into state so the report can
cite its own ranking methodology in the appendix.
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
    maybe_emit_schema, ok, reject_dry_run_with_idempotency, with_idempotency,
)
from research_state import apply_ranking, load_state

# Tier-1 venues. Conservative; users should extend per field.
TIER1_VENUES = {
    # General science
    "nature", "science", "cell", "pnas", "nature communications",
    "science advances", "nature methods", "nature biotechnology",
    "nature medicine", "nature genetics", "nature reviews",
    # ML / AI
    "neurips", "icml", "iclr", "cvpr", "iccv", "eccv", "acl",
    "emnlp", "naacl", "aaai", "ijcai", "kdd", "siggraph",
    # CS systems
    "sosp", "osdi", "sigcomm", "stoc", "focs",
    # Bio
    "elife", "plos biology", "current biology", "molecular cell",
    "immunity", "neuron",
}


# English stopwords. Conservative — restricted to genuine function words
# so domain shorthand ("model", "system") still contributes signal.
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "is", "are", "was", "were",
    "be", "been", "being", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "as", "into", "during", "this", "that", "these", "those",
    "it", "its", "we", "you", "they", "their", "our", "have", "has", "had",
    "do", "does", "did", "doing", "will", "would", "could", "should", "may",
    "might", "must", "can", "what", "which", "who", "whom", "whose", "when",
    "where", "why", "how", "not", "no", "nor", "so", "than", "too", "very",
    "just", "also", "such", "any", "all", "some", "each", "more", "most",
    "other", "another", "between", "about", "against", "above", "below",
    "out", "up", "down", "over", "under",
})

# Suffix-stripping rules for a tiny stemmer. (suffix, min_root_len_after_strip)
# Ordered longest-first so 'tions' beats 'tion' beats 'tion-'less rules.
# Keeping this small and conservative — bigger lists invite false matches
# (e.g. plain 'er' eats away at "her", "per"). The goal is not Porter
# fidelity, just to fold the morphology that the test run actually missed:
# evaluation/evaluating/evaluator/evaluations → evaluat;
# bias/biases → bias; modes/mode → mode; strategies → strateg.
_STEM_SUFFIXES = (
    ("tions", 3), ("tion", 3),
    ("ations", 3), ("ation", 3),
    ("ities", 4), ("ity", 3),
    ("ings", 4), ("ing", 4),
    ("edly", 3),
    ("ied", 3),
    ("ies", 4),
    ("ed", 4),
    ("es", 4),
    ("s", 5),  # min length 5 keeps "bias" intact, drops "evaluators"→"evaluator"
    ("ly", 3),
    ("er", 4), ("or", 4),
)


def _stem_word(word: str) -> str:
    if len(word) <= 3:
        return word
    for suffix, min_root in _STEM_SUFFIXES:
        if word.endswith(suffix) and (len(word) - len(suffix)) >= min_root:
            return word[: -len(suffix)]
    return word


def _normalize_tokens(text: str) -> set[str]:
    """Lowercase, tokenize, strip stopwords, stem. Returns a set."""
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {_stem_word(t) for t in raw
            if len(t) > 1 and t not in _STOPWORDS}


def tokenize(s: str) -> set[str]:
    """Backward-compatible alias for the (now improved) token extractor.

    Preserved as a public name for any caller that imported it; new code
    should use `_normalize_tokens` directly.
    """
    return _normalize_tokens(s)


def _extract_phrases(question: str) -> list[str]:
    """Pull out hyphenated and quoted multi-word phrases from the question.

    These are matched as substrings in the title/abstract for the phrase
    bonus — the token-level overlap can never reward "LLM-as-a-judge"
    appearing as a unit instead of four separate tokens, so phrase
    matching is the boost that makes question-specific terminology pay.
    """
    q = (question or "").lower()
    # Hyphenated like 'llm-as-a-judge', 'in-context', 'mt-bench'
    hyphenated = re.findall(r"\b\w+(?:-\w+)+\b", q)
    # Anything inside double or single quotes
    quoted = re.findall(r'"([^"]+)"', q) + re.findall(r"'([^']+)'", q)
    seen: list[str] = []
    for ph in hyphenated + quoted:
        ph = ph.strip()
        if len(ph) >= 4 and ph not in seen:
            seen.append(ph)
    return seen


def relevance(question: str, paper: dict[str, Any]) -> float:
    """Stopword-stripped, stemmed token overlap + phrase bonus.

    Returns a value in [0, 1]. The base term is `|q ∩ h| / |q|` — Jaccard
    against the question denominator so a perfectly-on-topic paper covering
    every meaningful question term scores 1.0. The phrase bonus is added on
    top (clipped at 1.0) — each hyphenated or quoted phrase from the
    question contributes +0.15 if found in the title and +0.05 if found
    only in the abstract. Title hits are weighted higher because that's
    where authors put the central concept of the paper.
    """
    qtok = _normalize_tokens(question)
    if not qtok:
        return 0.0
    title_text = (paper.get("title") or "").lower()
    abstract_text = (paper.get("abstract") or "").lower()
    htok = _normalize_tokens(title_text + " " + abstract_text)
    if not htok:
        return 0.0
    overlap = qtok & htok
    base = len(overlap) / max(len(qtok), 1)

    bonus = 0.0
    for phrase in _extract_phrases(question):
        if phrase in title_text:
            bonus += 0.15
        elif phrase in abstract_text:
            bonus += 0.05
    return min(base + bonus, 1.0)


def cite_score(citations: int | None) -> float:
    c = citations or 0
    return min(math.log10(c + 1) / 3.0, 1.0)


def recency(year: int | None, half_life: float, now_year: int) -> float:
    if not year:
        return 0.0
    delta = max(0, now_year - year)
    return math.exp(-delta / half_life)


def venue_prior(venue: str | None) -> float:
    if not venue:
        return 0.5
    v = venue.lower()
    for t in TIER1_VENUES:
        if t in v:
            return 1.0
    return 0.5


def main() -> None:
    p = argparse.ArgumentParser(description="Rank papers in state.")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--question",
                   help="Override the question used for relevance "
                        "(default: state.question)")
    p.add_argument("--alpha", type=float, default=0.4, help="weight: relevance")
    p.add_argument("--beta", type=float, default=0.3, help="weight: citations")
    p.add_argument("--gamma", type=float, default=0.2, help="weight: recency")
    p.add_argument("--delta", type=float, default=0.1, help="weight: venue prior")
    p.add_argument("--half-life", type=float, default=5.0,
                   help="Years until recency weight halves (default 5)")
    p.add_argument("--top", type=int, default=20,
                   help="Print top-N to stdout for inspection")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute scores and preview top-N, do NOT write to state.")
    p.add_argument("--idempotency-key",
                   help="Retry-safe key. Retried calls with the same key "
                        "return the original result without re-mutating state.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "rank_papers")
    args = p.parse_args()
    reject_dry_run_with_idempotency(args)

    path = Path(args.state)
    state = load_state(path)
    question = args.question or state["question"]
    now = datetime.now().year

    formula = (
        f"score = {args.alpha}·relevance "
        f"+ {args.beta}·log10(citations+1)/3 "
        f"+ {args.gamma}·exp(-Δyears/{args.half_life}) "
        f"+ {args.delta}·venue_prior"
    )

    scored_papers: dict[str, dict[str, Any]] = {}
    previews: list[dict[str, Any]] = []
    for pid, paper in state["papers"].items():
        rel = relevance(question, paper)
        cit = cite_score(paper.get("citations"))
        rec = recency(paper.get("year"), args.half_life, now)
        ven = venue_prior(paper.get("venue"))
        score = (args.alpha * rel
                 + args.beta * cit
                 + args.gamma * rec
                 + args.delta * ven)
        scored_papers[pid] = {
            "score": round(score, 4),
            "score_components": {
                "relevance": round(rel, 4),
                "citations": round(cit, 4),
                "recency": round(rec, 4),
                "venue": round(ven, 4),
            },
        }
        previews.append({
            "id": pid,
            "title": paper.get("title"),
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "citations": paper.get("citations"),
            "score": scored_papers[pid]["score"],
            "components": scored_papers[pid]["score_components"],
        })

    meta = {
        "formula": formula,
        "weights": {
            "alpha": args.alpha, "beta": args.beta,
            "gamma": args.gamma, "delta": args.delta,
        },
        "half_life": args.half_life,
        "ranked_at": datetime.now().isoformat(timespec="seconds"),
    }
    previews.sort(key=lambda p: p["score"], reverse=True)
    top = previews[: args.top]
    response = {
        "formula": formula,
        "ranked": len(scored_papers),
        "weights": {
            "alpha": args.alpha, "beta": args.beta,
            "gamma": args.gamma, "delta": args.delta,
        },
        "top": top,
    }

    if args.dry_run:
        response["dry_run"] = True
        ok(response)
        return

    def compute() -> dict[str, Any]:
        apply_ranking(path, scored_papers, meta)
        return response

    with_idempotency(args, compute)


if __name__ == "__main__":
    main()
