#!/usr/bin/env python3
"""search_biorxiv.py — query bioRxiv (and medRxiv) preprints via Europe PMC.

bioRxiv's native API is interval-based (date range / DOI lookup) and offers no
keyword search. Europe PMC (https://www.ebi.ac.uk/europepmc/) indexes bioRxiv
and medRxiv preprints with full keyword search, so we use it as the search
gateway and post-filter the results to the CSHL DOI prefix `10.1101/` (which
covers both bioRxiv and medRxiv — same publisher).

Why this matters: bioRxiv catches life-sci preprints before they appear in
PubMed (typical lag: weeks to months) and outside arXiv's CS/physics scope.
For systematic reviews on emerging topics, missing the preprint server means
missing the leading edge.

Public API: no key required. Polite use only — identifies via User-Agent.
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Any

# httpx imported lazily inside `search` so `--schema` works without it.

from _common import (
    USER_AGENT, UpstreamError, emit, err, make_paper, make_payload,
    maybe_emit_schema, record_search_failure, resolve_search_round,
    set_command_meta, with_search_cache,
)

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
BIORXIV_PREFIX = "10.1101/"

# Europe PMC accepts PUBYEAR ranges via the PUB_YEAR field with operators.


def search(query: str, limit: int,
           year_from: int | None, year_to: int | None) -> list[dict[str, Any]]:
    import httpx

    # Compose the Europe PMC query: keyword + preprint source + optional year.
    # SRC:PPR restricts to preprints across all servers; we then post-filter
    # by DOI prefix to keep only bioRxiv/medRxiv.
    pieces = [f"({query})", "SRC:PPR"]
    if year_from and year_to:
        pieces.append(f"PUB_YEAR:[{year_from} TO {year_to}]")
    elif year_from:
        pieces.append(f"PUB_YEAR:[{year_from} TO 2999]")
    elif year_to:
        pieces.append(f"PUB_YEAR:[1900 TO {year_to}]")
    full_query = " AND ".join(pieces)

    params = {
        "query": full_query,
        "format": "json",
        "resultType": "core",  # gives abstracts; lite omits them
        "pageSize": min(limit * 3, 1000),  # over-fetch since we'll prefix-filter
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        r = httpx.get(API, params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise UpstreamError(
            "biorxiv",
            f"{type(e).__name__}: {e}",
            retryable=True,
            status=status,
        ) from e

    data = r.json()
    raw_hits = ((data.get("resultList") or {}).get("result")) or []
    hits = _filter_to_biorxiv(raw_hits)
    return [_normalize(h) for h in hits[:limit]]


def _filter_to_biorxiv(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only hits whose DOI is under the CSHL `10.1101/` prefix."""
    out = []
    for h in hits:
        doi = h.get("doi")
        if isinstance(doi, str) and doi.startswith(BIORXIV_PREFIX):
            out.append(h)
    return out


_AUTHOR_TRAIL_PUNCT = re.compile(r"[.;,\s]+$")


def _parse_author_string(author_string: str | None) -> list[str]:
    """Split EPMC's `authorString` ("Smith J, Jones K, et al.") into a list.

    Strips trailing punctuation per author, drops 'et al' markers.
    """
    if not author_string:
        return []
    out: list[str] = []
    for raw in author_string.split(","):
        name = _AUTHOR_TRAIL_PUNCT.sub("", raw.strip())
        if not name:
            continue
        if name.lower() in {"et al", "et al."}:
            continue
        out.append(name)
    return out


def _year_from_hit(hit: dict[str, Any]) -> int | None:
    """Prefer `pubYear`; fall back to first 4 chars of `firstPublicationDate`."""
    raw = hit.get("pubYear")
    if not raw:
        date = hit.get("firstPublicationDate") or ""
        raw = date[:4] if len(date) >= 4 else None
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _coerce_int(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _pick_urls(hit: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (landing_url, pdf_url) from EPMC's fullTextUrlList."""
    block = hit.get("fullTextUrlList") or {}
    items = block.get("fullTextUrl") or []
    landing: str | None = None
    pdf: str | None = None
    for it in items:
        url = it.get("url")
        if not url:
            continue
        if url.lower().endswith(".pdf") and pdf is None:
            pdf = url
        elif landing is None:
            landing = url
    if landing is None and hit.get("doi"):
        landing = f"https://doi.org/{hit['doi']}"
    return landing, pdf


def _normalize(hit: dict[str, Any]) -> dict[str, Any]:
    landing, pdf = _pick_urls(hit)
    return make_paper(
        doi=hit.get("doi"),
        title=hit.get("title"),
        authors=_parse_author_string(hit.get("authorString")),
        year=_year_from_hit(hit),
        venue=hit.get("journalTitle") or "bioRxiv",
        abstract=hit.get("abstractText"),
        citations=_coerce_int(hit.get("citedByCount")),
        url=landing,
        pdf_url=pdf,
        pmid=hit.get("pmid") or None,
    )


def main() -> None:
    p = argparse.ArgumentParser(
        description="Search bioRxiv/medRxiv preprints via Europe PMC.")
    set_command_meta(p, since="0.10.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
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
    maybe_emit_schema(p, "search_biorxiv")
    args = p.parse_args()

    try:
        papers, cache_meta = with_search_cache(
            source="biorxiv",
            query=args.query,
            limit=args.limit,
            filters={"year_from": args.year_from, "year_to": args.year_to},
            fetch=lambda: search(args.query, args.limit,
                                 args.year_from, args.year_to),
        )
    except UpstreamError as e:
        record_search_failure(args.state, e.source, e.message, status=e.status)
        err("upstream_error", e.message,
            retryable=e.retryable, exit_code=e.exit_code,
            source=e.source, status=e.status)
    payload = make_payload(
        "biorxiv", args.query,
        resolve_search_round(args.state, "biorxiv", args.round),
        papers,
    )
    emit(payload, args.output, args.state, meta=cache_meta)


if __name__ == "__main__":
    main()
