#!/usr/bin/env python3
"""search_openalex.py — query the OpenAlex API.

OpenAlex is the primary discovery source for scholar-deep-research:
  - Free, no key required
  - 240M+ scholarly works
  - Cites/cited-by counts
  - DOI and PDF URLs where available

Polite pool: pass --email to identify yourself for higher rate limits.
"""
from __future__ import annotations

import argparse
import os
from typing import Any

# `httpx` is imported lazily inside network-calling helpers so that
# `--schema` introspection works on machines without httpx installed.

from _common import (
    USER_AGENT, UpstreamError, make_paper, make_payload, emit, err,
    maybe_emit_schema, reconstruct_inverted_abstract, record_search_failure,
    resolve_search_round, set_command_meta, with_search_cache,
)

SOURCE_META = {
    "name": "openalex",
    "domain": "academic",
    "index_type": "metadata_aggregator",
    "covers": ["papers", "authors", "venues", "institutions"],
    "lookup_by": ["doi", "openalex_id", "title"],
    "freshness_lag_days": 7,
    "rate_limit_qps_polite": 10.0,
    "auth": "polite_email_optional",
    "needs_relevance_filter": False,
    "language_scope": ["en"],
}

API = "https://api.openalex.org/works"


def search(query: str, limit: int, email: str | None,
           year_from: int | None, year_to: int | None) -> list[dict[str, Any]]:
    import httpx  # lazy: keeps --schema working on httpx-less machines

    params: dict[str, Any] = {
        "search": query,
        "per-page": min(limit, 200),
        "select": ",".join([
            "id", "doi", "title", "authorships", "publication_year",
            "primary_location", "cited_by_count",
            "abstract_inverted_index", "open_access",
        ]),
    }
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if email:
        params["mailto"] = email

    headers = {"User-Agent": USER_AGENT}
    if email:
        headers["From"] = email

    papers: list[dict[str, Any]] = []
    cursor = "*"
    fetched = 0
    while fetched < limit:
        params["cursor"] = cursor
        params["per-page"] = min(limit - fetched, 200)
        try:
            r = httpx.get(API, params=params, headers=headers, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise UpstreamError(
                "openalex",
                f"{type(e).__name__}: {e}",
                retryable=True,
                status=status,
            ) from e
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for w in results:
            papers.append(_normalize(w))
            fetched += 1
            if fetched >= limit:
                break
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
    return papers


def _normalize(w: dict[str, Any]) -> dict[str, Any]:
    oa_id = (w.get("id") or "").rsplit("/", 1)[-1] or None
    doi = w.get("doi")
    if doi and isinstance(doi, str):
        doi = doi.replace("https://doi.org/", "")
    authors = [
        a.get("author", {}).get("display_name")
        for a in w.get("authorships", []) if a.get("author")
    ]
    venue = None
    primary = w.get("primary_location") or {}
    src = primary.get("source") or {}
    venue = src.get("display_name")

    pdf_url = None
    if primary.get("pdf_url"):
        pdf_url = primary["pdf_url"]
    elif w.get("open_access", {}).get("oa_url"):
        pdf_url = w["open_access"]["oa_url"]

    landing = primary.get("landing_page_url")
    return make_paper(
        doi=doi,
        title=w.get("title"),
        authors=[a for a in authors if a],
        year=w.get("publication_year"),
        venue=venue,
        abstract=reconstruct_inverted_abstract(w.get("abstract_inverted_index")),
        citations=w.get("cited_by_count", 0),
        url=landing or (f"https://doi.org/{doi}" if doi else None),
        pdf_url=pdf_url,
        openalex_id=oa_id,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search OpenAlex.")
    set_command_meta(p, since="0.1.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--email",
                   default=os.environ.get("SCHOLAR_MAILTO"),
                   help="Polite pool email (env: SCHOLAR_MAILTO)")
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
    maybe_emit_schema(p, "search_openalex")
    args = p.parse_args()

    try:
        papers, cache_meta = with_search_cache(
            source="openalex",
            query=args.query,
            limit=args.limit,
            filters={"year_from": args.year_from, "year_to": args.year_to},
            fetch=lambda: search(args.query, args.limit, args.email,
                                 args.year_from, args.year_to),
        )
    except UpstreamError as e:
        record_search_failure(args.state, e.source, e.message, status=e.status)
        err("upstream_error", e.message,
            retryable=e.retryable, exit_code=e.exit_code,
            source=e.source, status=e.status)
    payload = make_payload(
        "openalex", args.query,
        resolve_search_round(args.state, "openalex", args.round),
        papers,
    )
    emit(payload, args.output, args.state, meta=cache_meta)


if __name__ == "__main__":
    main()
