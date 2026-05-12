#!/usr/bin/env python3
"""search_pubmed.py — query PubMed via NCBI E-utilities.

Two-step protocol:
  1. esearch.fcgi → list of PMIDs matching the query
  2. esummary.fcgi → metadata for those PMIDs

Abstracts are NOT returned by search — esummary doesn't include them, and
attempting to parse efetch's loosely-structured text response here produced
too many false splits. Abstracts are pulled per-paper during Phase 3
(deep-read) via extract_pdf.py or a targeted efetch call.

API key: optional but recommended (env: NCBI_API_KEY) for higher rate limits.
"""
from __future__ import annotations

import argparse
import os
from typing import Any

# `httpx` is imported lazily inside network-calling helpers so that
# `--schema` introspection works on machines without httpx installed.

from _common import (
    USER_AGENT, UpstreamError, emit, enforce_min_interval, err, make_paper,
    make_payload, maybe_emit_schema, record_search_failure,
    resolve_search_round, set_command_meta, with_search_cache,
)

SOURCE_META = {
    "name": "pubmed",
    "domain": "medical",
    "index_type": "subject_aggregator",
    "covers": ["papers"],
    "lookup_by": ["pmid", "doi", "title"],
    "freshness_lag_days": 1,
    "rate_limit_qps_polite": 3.0,
    "auth": "ncbi_key_optional",
    "needs_relevance_filter": False,
    "language_scope": ["en"],
}

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# NCBI E-utilities: 3 requests/s without an API key, 10 req/s with one.
# Each search() makes two HTTP calls (esearch + esummary), so the per-call
# minimum interval is half the per-second budget to keep both under the cap.
_PUBMED_MIN_INTERVAL_NO_KEY = 0.34   # ~3 req/s
_PUBMED_MIN_INTERVAL_WITH_KEY = 0.10  # ~10 req/s


def search(query: str, limit: int, api_key: str | None,
           year_from: int | None, year_to: int | None) -> list[dict]:
    import httpx  # lazy: keeps --schema working on httpx-less machines

    term = query
    if year_from or year_to:
        a = year_from or 1900
        b = year_to or 3000
        term = f"({query}) AND ({a}:{b}[dp])"

    es_params: dict[str, Any] = {
        "db": "pubmed",
        "term": term,
        "retmax": min(limit, 200),
        "retmode": "json",
        "sort": "relevance",
    }
    if api_key:
        es_params["api_key"] = api_key
    headers = {"User-Agent": USER_AGENT}
    min_interval = (_PUBMED_MIN_INTERVAL_WITH_KEY if api_key
                    else _PUBMED_MIN_INTERVAL_NO_KEY)

    enforce_min_interval("pubmed", min_interval)
    try:
        r = httpx.get(ESEARCH, params=es_params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise UpstreamError(
            "pubmed", f"esearch: {type(e).__name__}: {e}",
            retryable=True, status=status,
        ) from e
    pmids = r.json().get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    sum_params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if api_key:
        sum_params["api_key"] = api_key
    enforce_min_interval("pubmed", min_interval)
    try:
        r = httpx.get(ESUMMARY, params=sum_params, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise UpstreamError(
            "pubmed", f"esummary: {type(e).__name__}: {e}",
            retryable=True, status=status,
        ) from e
    result = r.json().get("result", {})

    papers = []
    for pmid in pmids:
        rec = result.get(pmid)
        if not rec:
            continue
        papers.append(_normalize(rec, pmid, abstract=None))
    return papers


def _normalize(rec: dict[str, Any], pmid: str,
               abstract: str | None = None) -> dict[str, Any]:
    authors = [a.get("name") for a in rec.get("authors", []) if a.get("name")]
    year = None
    pubdate = rec.get("pubdate") or ""
    if pubdate[:4].isdigit():
        year = int(pubdate[:4])

    doi = None
    for aid in rec.get("articleids", []):
        if aid.get("idtype") == "doi":
            doi = aid.get("value")
            break

    return make_paper(
        doi=doi,
        title=rec.get("title"),
        authors=authors,
        year=year,
        venue=rec.get("fulljournalname") or rec.get("source"),
        abstract=abstract,
        citations=None,  # PubMed doesn't expose citation counts
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        pdf_url=None,
        pmid=pmid,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search PubMed.")
    set_command_meta(p, since="0.1.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--api-key",
                   default=os.environ.get("NCBI_API_KEY"),
                   help="NCBI API key (env: NCBI_API_KEY)")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--round", type=int, default=None,
                   help="Search round (used by saturation tracking). "
                        "Default: auto-detect from --state — if the source "
                        "has prior queries, use max(round)+1; otherwise 1.")
    p.add_argument("--output")
    p.add_argument("--state",
                   default=os.environ.get("SCHOLAR_STATE_PATH"),
                   help="Ingest results into this state file "
                        "(env: SCHOLAR_STATE_PATH)")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "search_pubmed")
    args = p.parse_args()

    try:
        papers, cache_meta = with_search_cache(
            source="pubmed",
            query=args.query,
            limit=args.limit,
            filters={"year_from": args.year_from, "year_to": args.year_to},
            fetch=lambda: search(args.query, args.limit, args.api_key,
                                 args.year_from, args.year_to),
        )
    except UpstreamError as e:
        record_search_failure(args.state, e.source, e.message, status=e.status)
        err("upstream_error", e.message,
            retryable=e.retryable, exit_code=e.exit_code,
            source=e.source, status=e.status)
    payload = make_payload(
        "pubmed", args.query,
        resolve_search_round(args.state, "pubmed", args.round),
        papers,
    )
    emit(payload, args.output, args.state, meta=cache_meta)


if __name__ == "__main__":
    main()
