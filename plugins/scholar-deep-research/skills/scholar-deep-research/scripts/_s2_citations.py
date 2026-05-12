"""_s2_citations.py — minimal Semantic Scholar citation/reference client.

Used by `build_citation_graph.py` as a second backend alongside OpenAlex.
Coverage of S2's citation graph differs from OpenAlex (better for CS,
cross-disciplinary, and recent arXiv-anchored work), so dual-source
chase finds papers neither alone would surface.

Scope is intentionally narrow:
  - `s2_get_citations(paper_id)` — papers that cite this one
  - `s2_get_references(paper_id)` — papers this one cites
  - `normalize_s2_paper(record)` — make_paper-shaped dict

Auth: `S2_API_KEY` env var (matches semanticscholar-skill convention).
Without a key the public quota is ~1 req/s; we sleep accordingly.

Test hook: when `SCHOLAR_S2_TEST_FAKE` points at a JSON file, the two
fetch helpers read canned responses from it instead of hitting the
network. The hook keeps the smoke suite offline.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Lazy httpx import so --schema introspection works without httpx.

GRAPH = "https://api.semanticscholar.org/graph/v1"
_FIELDS = "title,year,citationCount,authors,venue,externalIds,abstract"
# Public S2 quota is ~1 req/s. Authenticated quotas are higher but we
# still pace conservatively — a citation chase fans out across N seeds,
# bursting all at once is the fastest way to earn 429s.
_MIN_GAP_S = 1.1


# Module-level pacing — shared across calls in one process.
_last_request_time = 0.0


def _read_test_fake() -> dict[str, Any] | None:
    """If SCHOLAR_S2_TEST_FAKE is set, return the canned response map."""
    fake_path = os.environ.get("SCHOLAR_S2_TEST_FAKE")
    if not fake_path:
        return None
    try:
        return json.loads(Path(fake_path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"SCHOLAR_S2_TEST_FAKE set but unreadable: {exc}\n")
        return None


class S2Error(Exception):
    """S2 fetch failed. `code` is a snake_case category, `status` is
    the HTTP status if any, `retryable` flags whether a retry might help."""

    def __init__(self, code: str, message: str, *,
                 status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


def _request_paginated(path: str, *, max_results: int) -> list[dict[str, Any]]:
    import httpx
    global _last_request_time

    api_key = os.environ.get("S2_API_KEY") or ""
    headers = {"x-api-key": api_key} if api_key else {}
    url = f"{GRAPH}{path}"
    out: list[dict[str, Any]] = []
    offset = 0
    page = min(100, max_results)

    while len(out) < max_results:
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_GAP_S:
            time.sleep(_MIN_GAP_S - elapsed)
        _last_request_time = time.time()

        params = {"fields": _FIELDS, "limit": page, "offset": offset}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=30.0)
        except httpx.HTTPError as exc:
            raise S2Error("s2_network_error",
                          f"{type(exc).__name__}: {exc}",
                          retryable=True) from exc

        if r.status_code in (401, 403):
            raise S2Error("s2_unauthorized",
                          "S2 rejected the request "
                          f"({r.status_code}). Set S2_API_KEY for higher "
                          "quota; without one, public access is rate-limited "
                          "and may be denied for some endpoints.",
                          status=r.status_code, retryable=False)
        if r.status_code == 404:
            # Paper unknown to S2 — not a hard error, just empty result.
            return []
        if r.status_code == 429 or r.status_code >= 500:
            raise S2Error("s2_rate_limited" if r.status_code == 429
                          else "s2_upstream_error",
                          f"S2 returned {r.status_code}",
                          status=r.status_code, retryable=True)
        if r.status_code >= 400:
            raise S2Error("s2_client_error",
                          f"S2 returned {r.status_code}: {r.text[:200]}",
                          status=r.status_code, retryable=False)

        body = r.json()
        # S2 occasionally returns {"data": null, ...} — `get(...,[])` returns
        # None in that case (key present, value None), so guard with `or []`.
        out.extend(body.get("data") or [])
        if "next" not in body:
            break
        offset = body["next"]
        if offset >= max_results:
            break

    return out[:max_results]


def s2_paper_id(seed: dict[str, Any]) -> str | None:
    """S2-acceptable paper id for a seed.

    S2 takes `DOI:<doi>`, `ARXIV:<id>`, `PMID:<id>`, plus its native
    paperId. We prefer DOI (most universally resolvable). Returns None
    when the seed has no S2-resolvable handle, in which case S2 chase
    skips this seed.
    """
    doi = seed.get("doi")
    if doi:
        return f"DOI:{doi}"
    arxiv_id = seed.get("arxiv_id")
    if arxiv_id:
        return f"ARXIV:{arxiv_id}"
    pmid = seed.get("pmid")
    if pmid:
        return f"PMID:{pmid}"
    return None


def s2_get_citations(paper_id: str, max_results: int = 100) -> list[dict[str, Any]]:
    """Papers that cite `paper_id`. Each row has a `citingPaper` envelope."""
    fake = _read_test_fake()
    if fake is not None:
        return fake.get("citations", {}).get(paper_id, [])
    rows = _request_paginated(
        f"/paper/{paper_id}/citations", max_results=max_results)
    # Each row: {"citingPaper": {...}, "isInfluential": bool, ...}
    return [r["citingPaper"] for r in rows if r.get("citingPaper")]


def s2_get_references(paper_id: str, max_results: int = 100) -> list[dict[str, Any]]:
    """Papers that `paper_id` cites. Each row has a `citedPaper` envelope."""
    fake = _read_test_fake()
    if fake is not None:
        return fake.get("references", {}).get(paper_id, [])
    rows = _request_paginated(
        f"/paper/{paper_id}/references", max_results=max_results)
    return [r["citedPaper"] for r in rows if r.get("citedPaper")]


def normalize_s2_paper(s2: dict[str, Any]) -> dict[str, Any]:
    """Convert an S2 paper dict to make_paper-shaped fields (kwargs).

    The caller wraps the result via `make_paper(**kwargs)` so type
    discipline (year as int, authors as list, etc.) lands in one place.
    """
    ext = s2.get("externalIds") or {}
    doi = ext.get("DOI")
    arxiv_id = ext.get("ArXiv")
    pmid = ext.get("PubMed")
    authors = [a.get("name") for a in (s2.get("authors") or [])
               if a and a.get("name")]
    venue = s2.get("venue") or None
    return {
        "doi": doi,
        "title": s2.get("title"),
        "authors": authors or None,
        "year": s2.get("year"),
        "venue": venue,
        "abstract": s2.get("abstract"),
        "citations": s2.get("citationCount"),
        "arxiv_id": arxiv_id,
        "pmid": pmid,
    }
