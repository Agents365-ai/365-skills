#!/usr/bin/env python3
"""search_arxiv.py — query the arXiv API.

arXiv is essential for CS/ML/physics preprints and the latest unpublished work.
Returns Atom XML; we parse with stdlib xml.etree.

NOTE: Papers from arXiv are preprints unless cross-listed with a peer-reviewed
venue. The state file tags them with source="arxiv" — downstream consumers
should treat that as a flag to weight evidence accordingly.
"""
from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

import httpx

from _common import (
    USER_AGENT, UpstreamError, emit, enforce_min_interval, err, make_paper,
    make_payload, maybe_emit_schema, record_search_failure,
    resolve_search_round, set_command_meta, with_search_cache,
)

API = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# arXiv enforces a strict ≥3s/request per-IP limit; bursts trigger 429
# plus a sticky cooldown that lasts 60-90s. The per-source file-lock in
# enforce_min_interval queues parallel calls automatically so multiple
# search_arxiv.py invocations don't all hit the wall at once.
_ARXIV_MIN_INTERVAL = 3.0


def search(query: str, limit: int) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(limit, 200),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    enforce_min_interval("arxiv", _ARXIV_MIN_INTERVAL)
    try:
        r = httpx.get(API, params=params,
                      headers={"User-Agent": USER_AGENT}, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise UpstreamError(
            "arxiv", f"{type(e).__name__}: {e}",
            retryable=True, status=status,
        ) from e

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        raise UpstreamError(
            "arxiv", f"malformed Atom response: {e}",
            retryable=True,
        ) from e

    papers = []
    for entry in root.findall("atom:entry", NS):
        papers.append(_normalize(entry))
    return papers


def _normalize(entry: ET.Element) -> dict:
    def text(path: str) -> str | None:
        el = entry.find(path, NS)
        return el.text.strip() if el is not None and el.text else None

    arxiv_url = text("atom:id") or ""
    arxiv_id = arxiv_url.rsplit("/", 1)[-1].split("v")[0] if arxiv_url else None
    title = text("atom:title") or ""
    title = " ".join(title.split())  # collapse newlines
    summary = text("atom:summary") or ""
    summary = " ".join(summary.split())
    published = text("atom:published") or ""
    year = int(published[:4]) if len(published) >= 4 else None

    authors = [
        a.findtext("atom:name", default="", namespaces=NS).strip()
        for a in entry.findall("atom:author", NS)
    ]
    authors = [a for a in authors if a]

    doi = text("arxiv:doi")
    pdf_url = None
    landing = None
    for link in entry.findall("atom:link", NS):
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href")
        elif link.get("rel") == "alternate":
            landing = link.get("href")

    venue = text("arxiv:journal_ref") or "arXiv"

    return make_paper(
        doi=doi,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=summary,
        citations=None,  # arXiv doesn't expose citation counts
        url=landing or arxiv_url,
        pdf_url=pdf_url,
        arxiv_id=arxiv_id,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Search arXiv.")
    set_command_meta(p, since="0.1.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=50)
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
    maybe_emit_schema(p, "search_arxiv")
    args = p.parse_args()

    try:
        papers, cache_meta = with_search_cache(
            source="arxiv",
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
        "arxiv", args.query,
        resolve_search_round(args.state, "arxiv", args.round),
        papers,
    )
    emit(payload, args.output, args.state, meta=cache_meta)


if __name__ == "__main__":
    main()
