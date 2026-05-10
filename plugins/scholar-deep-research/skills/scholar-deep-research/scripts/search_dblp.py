#!/usr/bin/env python3
"""search_dblp.py — query the DBLP computer-science bibliography.

DBLP is the gold standard for CS bibliographies: comprehensive coverage of
conference proceedings (NeurIPS, ICML, CVPR, ACL, ...) and CS journals,
authoritative author disambiguation, stable record keys.

What DBLP does NOT provide:
  - abstracts (it's a metadata catalog, not a content provider)
  - citation counts (use OpenAlex/Crossref for those)

So DBLP is a *complement* to OpenAlex/arXiv for CS reviews — it catches papers
the others miss (especially older proceedings) and provides cleaner author/
venue strings, but you'll need OpenAlex or Crossref to pull abstracts and
citation context.

Public API: https://dblp.org/search/publ/api?q=<query>&format=json — no key,
polite use only. Author identifies via User-Agent.
"""
from __future__ import annotations

import argparse
import os
from typing import Any

# httpx imported lazily inside `search` so `--schema` works without it.

from _common import (
    USER_AGENT, UpstreamError, emit, err, make_paper, make_payload,
    maybe_emit_schema, record_search_failure, resolve_search_round,
    set_command_meta, with_search_cache,
)

API = "https://dblp.org/search/publ/api"


def search(query: str, limit: int) -> list[dict[str, Any]]:
    import httpx

    params = {
        "q": query,
        "format": "json",
        "h": min(limit, 1000),  # DBLP caps page size at 1000
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        r = httpx.get(API, params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise UpstreamError(
            "dblp",
            f"{type(e).__name__}: {e}",
            retryable=True,
            status=status,
        ) from e

    data = r.json()
    hits_block = (data.get("result") or {}).get("hits") or {}
    hits = hits_block.get("hit") or []
    if isinstance(hits, dict):
        # When result count == 1, DBLP returns a single dict, not a 1-list.
        hits = [hits]

    papers: list[dict[str, Any]] = []
    for h in hits[:limit]:
        info = h.get("info") or {}
        papers.append(_normalize(info))
    return papers


def _normalize(info: dict[str, Any]) -> dict[str, Any]:
    """Convert one DBLP `info` block into the shared paper shape."""
    # Authors: `authors.author` is dict (single) or list (multi).
    raw_authors = ((info.get("authors") or {}).get("author")) or []
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    authors = [a.get("text") for a in raw_authors if a.get("text")]

    # Venue: usually a string, occasionally a list (cross-listed entries).
    venue = info.get("venue")
    if isinstance(venue, list):
        venue = ", ".join(str(v) for v in venue if v) or None

    # Year: arrives as a string; coerce defensively.
    year_raw = info.get("year")
    try:
        year = int(year_raw) if year_raw else None
    except (TypeError, ValueError):
        year = None

    # `ee` is the electronic-edition link (often a DOI URL or publisher URL).
    # It can be a string or a list; pick the first usable value.
    ee = info.get("ee")
    if isinstance(ee, list):
        ee = ee[0] if ee else None

    # If no `ee` link, fall back to the canonical DBLP record URL via `key`.
    key = info.get("key")
    url = ee or (f"https://dblp.org/rec/{key}.html" if key else None)

    return make_paper(
        doi=info.get("doi"),
        title=info.get("title"),
        authors=authors,
        year=year,
        venue=venue,
        abstract=None,           # DBLP doesn't carry abstracts
        citations=None,          # nor citation counts
        url=url,
        pdf_url=None,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search DBLP (CS bibliography).")
    set_command_meta(p, since="0.10.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--round", type=int, default=None,
                   help="Search round (used by saturation tracking). "
                        "Default: auto-detect from --state — if the source "
                        "has prior queries, use max(round)+1; otherwise 1.")
    p.add_argument("--output", help="Write payload JSON to this path")
    p.add_argument("--state",
                   default=os.environ.get("SCHOLAR_STATE_PATH"),
                   help="Ingest results into this state file "
                        "(env: SCHOLAR_STATE_PATH)")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "search_dblp")
    args = p.parse_args()

    try:
        papers, cache_meta = with_search_cache(
            source="dblp",
            query=args.query,
            limit=args.limit,
            filters={},
            fetch=lambda: search(args.query, args.limit),
        )
    except UpstreamError as e:
        record_search_failure(args.state, e.source, e.message, status=e.status)
        err("upstream_error", e.message,
            retryable=e.retryable, exit_code=e.exit_code,
            source=e.source, status=e.status)
    payload = make_payload(
        "dblp", args.query,
        resolve_search_round(args.state, "dblp", args.round),
        papers,
    )
    emit(payload, args.output, args.state, meta=cache_meta)


if __name__ == "__main__":
    main()
