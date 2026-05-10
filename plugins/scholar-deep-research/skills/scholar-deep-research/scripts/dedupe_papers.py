#!/usr/bin/env python3
"""dedupe_papers.py — collapse duplicate papers in the state file.

Why this exists: searches across OpenAlex, Crossref, PubMed, and arXiv produce
overlapping records. The ingest step already deduplicates by ID, but the same
paper can appear under different IDs (e.g., a DOI from Crossref and an arXiv
ID from arXiv before the journal version was indexed).

Strategy:
  1. Group by normalized DOI when present (canonical).
  2. For records without DOIs, group by normalized title + first-author last name.
  3. Within each group, merge into the record with the most populated DOI/abstract,
     accumulating `source` and preferring richer metadata.

This script is idempotent: running it twice on the same state file produces
the same result.
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
from pathlib import Path
from typing import Any

from _common import maybe_emit_schema, ok, with_idempotency
from research_state import apply_dedupe, load_state, normalize_title

# Threshold for the secondary preprint/published bridge pass. Chosen
# empirically against the two real-world misses found in scholar-deep-
# research's own end-to-end test (CELLxGENE preprint vs published NAR;
# Nicheformer preprint vs Nature Methods): 0.92 catches both pairs
# (which differ only by trailing punctuation and "× vs x" substitution
# in the Unicode title) without collapsing genuinely-distinct papers
# that share an author and topic.
_TITLE_SIMILARITY_THRESHOLD = 0.92


def populated(r: dict[str, Any]) -> int:
    """Score a record by how many canonical metadata fields it has filled.

    Used as the within-cluster sort key when picking the merge representative
    AND as the tiebreaker when bridging two same-work clusters with
    different DOIs (the more-populated record's cluster keeps its identity).
    """
    return sum(1 for f in ("doi", "abstract", "pdf_url", "venue", "year",
                           "citations") if r.get(f))


def first_author_key(p: dict[str, Any]) -> str:
    authors = p.get("authors") or []
    if not authors:
        return ""
    first = authors[0].lower()
    # last token is usually the surname (works for "First Last", less so
    # for "Last, First" but acceptable as a clustering key)
    parts = re.split(r"[,\s]+", first.strip())
    parts = [x for x in parts if x]
    return parts[-1] if parts else ""


def cluster_key(p: dict[str, Any]) -> str:
    """Key for grouping potentially-duplicate records."""
    if p.get("doi"):
        return f"doi:{p['doi'].lower()}"
    nt = normalize_title(p.get("title") or "")
    if not nt:
        return f"id:{p.get('id', '')}"
    return f"t:{nt[:80]}::a:{first_author_key(p)}::y:{p.get('year') or ''}"


def _is_preprint_doi(doi: str | None) -> bool:
    """True for bioRxiv / medRxiv (10.1101/*) and arXiv (10.48550/arxiv*) DOIs.

    Used as the tiebreaker in the bridge pass: when a preprint and a
    published version of the same work both make it into the corpus
    under different DOIs, the published-DOI cluster wins.
    """
    if not doi:
        return False
    d = doi.lower().strip()
    return d.startswith("10.1101/") or d.startswith("10.48550/arxiv")


def _title_similar(t1: str, t2: str) -> bool:
    """Fuzzy title match for bridging same-work-different-DOI clusters.

    Both inputs are already normalized via `normalize_title`. The
    SequenceMatcher ratio captures the "preprint differs from published
    by a few characters" pattern (trailing periods, capitalization in
    the source, '×' vs 'x' Unicode confusion in CELLxGENE-style titles)
    without collapsing genuinely-distinct papers that happen to share
    keywords.
    """
    if not t1 or not t2:
        return False
    return (difflib.SequenceMatcher(None, t1, t2).ratio()
            >= _TITLE_SIMILARITY_THRESHOLD)


def _bridge_preprint_clusters(
    clusters: dict[str, list[dict[str, Any]]],
) -> int:
    """Second-pass merge: collapse same-work clusters that have different DOIs.

    Primary clustering keys on DOI when present, so a paper that appears
    under both its preprint DOI (e.g. 10.1101/2024.04.15.589472) and
    its published DOI (10.1038/s41592-025-02814-z) clusters into two
    separate buckets and falls through dedupe. This pass walks the
    DOI-keyed clusters pairwise and merges when:

      - the representatives share a first-author surname,
      - their normalized titles are >= 0.92 similar,
      - their years differ by at most 2 (or one is missing).

    The preprint-DOI cluster is merged INTO the published-DOI cluster.
    When both (or neither) are preprints, the more-populated record's
    cluster wins. Returns the number of bridges performed for the
    response envelope.

    Cost: O(N^2) over DOI-keyed cluster representatives. For typical
    Phase 1 corpora (~hundreds of clusters) this is sub-second; the
    bridge runs once per dedupe call so amortized cost is negligible.
    Title-keyed clusters are skipped — they already use the
    title-author-year composite key so cross-cluster bridging is
    redundant.
    """
    rep_info: list[dict[str, Any]] = []
    for key, members in clusters.items():
        if not key.startswith("doi:"):
            continue
        rep = max(members, key=populated)
        nt = normalize_title(rep.get("title") or "")
        fa = first_author_key(rep)
        # Require enough title signal to safely bridge — short titles
        # can collide spuriously across papers with the same first
        # author (e.g. "Editorial", "Reply").
        if len(nt) < 20 or not fa:
            continue
        rep_info.append({
            "key": key,
            "nt": nt,
            "fa": fa,
            "year": rep.get("year"),
            "is_preprint": _is_preprint_doi(rep.get("doi")),
            "populated": populated(rep),
        })

    # Union-find over cluster keys. Each pair that satisfies the bridge
    # criteria points the loser key at the winner; root() chases the
    # chain to the final survivor.
    merged_into: dict[str, str] = {}

    def root(k: str) -> str:
        while k in merged_into:
            k = merged_into[k]
        return k

    for i in range(len(rep_info)):
        ai = rep_info[i]
        for j in range(i + 1, len(rep_info)):
            bj = rep_info[j]
            if ai["fa"] != bj["fa"]:
                continue
            if (ai["year"] is not None and bj["year"] is not None
                    and abs(ai["year"] - bj["year"]) > 2):
                continue
            if not _title_similar(ai["nt"], bj["nt"]):
                continue
            ra = root(ai["key"])
            rb = root(bj["key"])
            if ra == rb:
                continue
            # Look up current attributes of the two cluster roots to
            # decide which keeps its identity.
            ra_info = next(r for r in rep_info if r["key"] == ra)
            rb_info = next(r for r in rep_info if r["key"] == rb)
            if ra_info["is_preprint"] and not rb_info["is_preprint"]:
                loser, winner = ra, rb
            elif rb_info["is_preprint"] and not ra_info["is_preprint"]:
                loser, winner = rb, ra
            elif ra_info["populated"] < rb_info["populated"]:
                loser, winner = ra, rb
            else:
                loser, winner = rb, ra
            merged_into[loser] = winner

    bridges = 0
    for loser_key in list(merged_into.keys()):
        winner_key = root(loser_key)
        if (loser_key != winner_key
                and loser_key in clusters and winner_key in clusters):
            clusters[winner_key].extend(clusters[loser_key])
            del clusters[loser_key]
            bridges += 1
    return bridges


def merge(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge a cluster of duplicates into one record."""
    # Sort by score: most DOI > most-populated abstract > highest cite count
    records = sorted(records, key=populated, reverse=True)
    base = dict(records[0])
    for other in records[1:]:
        for s in other.get("source", []):
            if s not in base.setdefault("source", []):
                base["source"].append(s)
        for k in ("doi", "abstract", "pdf_url", "url", "venue",
                  "openalex_id", "arxiv_id", "pmid"):
            if not base.get(k) and other.get(k):
                base[k] = other[k]
        # citation count: max wins
        bc = base.get("citations") or 0
        oc = other.get("citations") or 0
        if oc > bc:
            base["citations"] = oc
        # round info: keep earliest first_seen_round
        if other.get("first_seen_round") and (
            not base.get("first_seen_round")
            or other["first_seen_round"] < base["first_seen_round"]
        ):
            base["first_seen_round"] = other["first_seen_round"]
    return base


def main() -> None:
    p = argparse.ArgumentParser(description="Deduplicate papers in state.")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Print clusters without modifying state")
    p.add_argument("--idempotency-key",
                   help="Retry-safe key. Retried calls with the same key "
                        "return the original result without re-mutating state.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "dedupe_papers")
    args = p.parse_args()

    path = Path(args.state)
    state = load_state(path)
    papers = list(state["papers"].values())

    clusters: dict[str, list[dict[str, Any]]] = {}
    for pap in papers:
        clusters.setdefault(cluster_key(pap), []).append(pap)

    # Second pass: bridge same-work clusters across distinct DOIs (the
    # preprint vs published-version trap).
    bridges_made = _bridge_preprint_clusters(clusters)

    duplicates = {k: v for k, v in clusters.items() if len(v) > 1}
    if args.dry_run:
        ok({
            "dry_run": True,
            "total_papers": len(papers),
            "duplicate_clusters": len(duplicates),
            "preprint_bridges": bridges_made,
            "clusters": [{"key": k, "ids": [r["id"] for r in v]}
                         for k, v in duplicates.items()],
        })
        return

    # Build new papers dict from merged clusters and a {old_id: new_id} remap
    # so we can rewrite ID-bearing collections (selected_ids, themes, tensions)
    # in the same save — leaving them unrewritten would orphan references.
    from research_state import make_paper_id
    new_papers: dict[str, dict[str, Any]] = {}
    id_remap: dict[str, str] = {}
    merged_count = 0
    for cluster in clusters.values():
        merged = merge(cluster) if len(cluster) > 1 else cluster[0]
        if len(cluster) > 1:
            merged_count += 1
        new_id = make_paper_id(merged)
        merged["id"] = new_id
        for member in cluster:
            old_id = member.get("id")
            if old_id and old_id != new_id:
                id_remap[old_id] = new_id
        # If two clusters collapse to the same id (rare), prefer the more populated
        if new_id in new_papers:
            new_papers[new_id] = merge([new_papers[new_id], merged])
        else:
            new_papers[new_id] = merged

    # The swap-and-rewrite of papers/selected_ids/themes/tensions runs under
    # the state lock inside apply_dedupe so a concurrent reader never sees
    # state["papers"] without the matching remap.
    response = {
        "before": len(papers),
        "after": len(new_papers),
        "merged_clusters": merged_count,
        "ids_remapped": len(id_remap),
        "preprint_bridges": bridges_made,
    }

    def compute() -> dict[str, Any]:
        apply_dedupe(path, new_papers, id_remap)
        return response

    with_idempotency(args, compute)


if __name__ == "__main__":
    main()
