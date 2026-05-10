#!/usr/bin/env python3
"""search_exa.py — query the Exa web search API.

Exa is a neural/semantic web search API. Unlike the scholarly APIs already
federated here (OpenAlex, arXiv, Crossref, PubMed), Exa indexes the open web
and reaches material those sources miss: institutional PDFs, conference
mirrors, lab websites, technical blogs, preprints parked outside arXiv, and
government or NGO reports.

Defaults to `category="research paper"` so discovery stays aligned with the
scholar-deep-research workflow; pass `--category` to broaden (e.g. `news`
for citation-criticism chases, `""` for unfiltered web).

Abstract content is populated by cascading:
    summary (if available) → text excerpt → joined highlights → None

Citation counts are not available from Exa (set to 0); downstream ranking
in `rank_papers.py` will weight Exa results on relevance/recency rather
than prior citations.

API key: required (env: EXA_API_KEY). Signup at https://exa.ai/.
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Any

# `exa_py` is imported lazily inside network-calling helpers so that
# `--schema` introspection works on machines without exa-py installed.

from _common import (
    EXIT_RUNTIME, USER_AGENT, UpstreamError, emit, err, make_paper,
    make_payload, maybe_emit_schema, resolve_search_round, set_command_meta,
)

INTEGRATION_ID = "scholar-deep-research"


class _DependencyMissing(Exception):
    """Raised when an optional runtime dependency is not installed.

    Routed by main() to a dedicated `dependency_missing` envelope so an
    agent can distinguish "transient API failure, retry later" from "the
    human needs to pip install something".
    """

    def __init__(self, dependency: str, message: str) -> None:
        super().__init__(message)
        self.dependency = dependency
        self.message = message

# Matches a DOI anywhere in a URL path. Conservative on the tail — allows
# alphanumerics, dots, dashes, underscores, slashes, parens. Trims trailing
# punctuation that commonly ends a URL but isn't part of the DOI.
_DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
_DOI_TRAIL = re.compile(r"[).,;:]+$")


def _doi_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = _DOI_RE.search(url)
    if not m:
        return None
    return _DOI_TRAIL.sub("", m.group(1))


def _year_from_published(published: str | None) -> int | None:
    if not published or not isinstance(published, str) or len(published) < 4:
        return None
    try:
        return int(published[:4])
    except ValueError:
        return None


def _extract_snippet(result: Any) -> str | None:
    """Pick the best abstract-equivalent content from an Exa result.

    Exa returns any combination of `summary`, `text`, and `highlights`
    depending on which content modes were requested and what the crawler
    found. Cascade in preference order and fall back to None.
    """
    summary = getattr(result, "summary", None)
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    text = getattr(result, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    highlights = getattr(result, "highlights", None)
    if isinstance(highlights, list) and highlights:
        joined = " … ".join(h.strip() for h in highlights if isinstance(h, str) and h.strip())
        if joined:
            return joined

    return None


def _str_or_none(v: Any) -> str | None:
    """Coerce empty / whitespace-only strings to None.

    Exa sometimes returns `title=""` (and occasionally `url=""`) on PDF-only
    results where the crawler did not extract a heading. Without this coercion
    those would propagate as empty strings into the state file and silently
    corrupt dedupe (two empty titles compare equal under similarity) and rank
    (empty title scores against a missing-data heuristic, not zero).
    """
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _authors_list(result: Any) -> list[str]:
    """Exa returns either `author` (str) or `authors` (list). Normalize."""
    authors = getattr(result, "authors", None)
    if isinstance(authors, list):
        return [a for a in authors if isinstance(a, str) and a.strip()]
    author = getattr(result, "author", None)
    if isinstance(author, str) and author.strip():
        # Split on common separators without being too aggressive — a single
        # author string "Jane Doe" stays as one entry.
        parts = [p.strip() for p in re.split(r"\s*(?:,| and | & )\s*", author) if p.strip()]
        return parts or [author.strip()]
    return []


def _normalize(result: Any) -> dict[str, Any]:
    url = _str_or_none(getattr(result, "url", None))
    title = _str_or_none(getattr(result, "title", None))
    doi = _doi_from_url(url)
    published = getattr(result, "published_date", None) or getattr(result, "publishedDate", None)
    return make_paper(
        doi=doi,
        title=title,
        authors=_authors_list(result),
        year=_year_from_published(published),
        venue=None,
        abstract=_extract_snippet(result),
        citations=0,
        url=url,
        pdf_url=url if url and url.lower().endswith(".pdf") else None,
    )


def search(
    query: str,
    limit: int,
    api_key: str,
    *,
    search_type: str,
    category: str | None,
    year_from: int | None,
    year_to: int | None,
    include_domains: list[str] | None,
    exclude_domains: list[str] | None,
    include_text: list[str] | None,
    exclude_text: list[str] | None,
) -> list[dict[str, Any]]:
    # Lazy import keeps --schema working on machines without exa-py installed.
    try:
        from exa_py import Exa
    except ImportError as e:
        raise _DependencyMissing(
            "exa-py",
            f"exa-py is not installed: {e}. Install with `pip install exa-py`.",
        ) from e

    client = Exa(api_key=api_key, user_agent=USER_AGENT)
    # Attribution header — how Exa identifies API calls coming from this skill.
    client.headers["x-exa-integration"] = INTEGRATION_ID

    kwargs: dict[str, Any] = {
        "query": query,
        "num_results": min(max(limit, 1), 100),
        "type": search_type,
        "text": {"max_characters": 1500},
        "highlights": {"num_sentences": 3, "highlights_per_url": 3},
    }
    if category:
        kwargs["category"] = category
    if year_from:
        kwargs["start_published_date"] = f"{year_from}-01-01"
    if year_to:
        kwargs["end_published_date"] = f"{year_to}-12-31"
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains
    if include_text:
        kwargs["include_text"] = include_text
    if exclude_text:
        kwargs["exclude_text"] = exclude_text

    try:
        response = client.search_and_contents(**kwargs)
    except Exception as e:  # exa-py raises ValueError / httpx errors / ApiError
        status = getattr(getattr(e, "response", None), "status_code", None)
        retryable = status is None or status >= 500 or status == 429
        raise UpstreamError(
            "exa",
            f"{type(e).__name__}: {e}",
            retryable=retryable,
            status=status,
        ) from e

    results = getattr(response, "results", None) or []
    return [_normalize(r) for r in results]


def _split_csv(values: list[str] | None) -> list[str] | None:
    """Allow --include-domain to be passed repeatedly or comma-separated."""
    if not values:
        return None
    out: list[str] = []
    for v in values:
        out.extend(part.strip() for part in v.split(",") if part.strip())
    return out or None


def main() -> None:
    p = argparse.ArgumentParser(description="Search the web via Exa.")
    set_command_meta(p, since="0.6.0", tier="read")
    p.add_argument("--query", required=True)
    p.add_argument(
        "--limit", type=int, default=50,
        help="Number of results (default: 50, max: 100 per call — Exa cap)",
    )
    p.add_argument(
        "--type",
        dest="search_type",
        default="auto",
        choices=["auto", "neural", "fast"],
        help="Exa search type (default: auto)",
    )
    p.add_argument(
        "--category",
        default="research paper",
        help="Exa category filter (default: 'research paper'). "
             "Pass empty string to disable.",
    )
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument(
        "--include-domain",
        action="append",
        help="Restrict to these domains. Repeatable or comma-separated.",
    )
    p.add_argument(
        "--exclude-domain",
        action="append",
        help="Exclude these domains. Repeatable or comma-separated.",
    )
    p.add_argument(
        "--include-text",
        action="append",
        help="Require these substrings in results. Repeatable.",
    )
    p.add_argument(
        "--exclude-text",
        action="append",
        help="Forbid these substrings in results. Repeatable.",
    )
    p.add_argument("--round", type=int, default=None,
                   help="Search round (used by saturation tracking). "
                        "Default: auto-detect from --state — if the source "
                        "has prior queries, use max(round)+1; otherwise 1.")
    p.add_argument("--output", help="Write payload JSON to this path")
    p.add_argument("--state",
                   default=os.environ.get("SCHOLAR_STATE_PATH"),
                   help="Ingest results into this state file "
                        "(env: SCHOLAR_STATE_PATH)")
    p.add_argument("--api-key",
                   default=os.environ.get("EXA_API_KEY"),
                   help="Exa API key (env: EXA_API_KEY)")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    maybe_emit_schema(p, "search_exa")
    args = p.parse_args()

    if not args.api_key:
        err(
            "missing_api_key",
            "EXA_API_KEY is not set. Export it or pass --api-key. "
            "Get one at https://exa.ai/.",
            retryable=False,
            exit_code=3,
        )

    category = args.category.strip() if args.category else None

    try:
        papers = search(
            args.query,
            args.limit,
            args.api_key,
            search_type=args.search_type,
            category=category or None,
            year_from=args.year_from,
            year_to=args.year_to,
            include_domains=_split_csv(args.include_domain),
            exclude_domains=_split_csv(args.exclude_domain),
            include_text=_split_csv(args.include_text),
            exclude_text=_split_csv(args.exclude_text),
        )
    except _DependencyMissing as e:
        err("dependency_missing", e.message,
            retryable=False, exit_code=EXIT_RUNTIME, dependency=e.dependency)
    except UpstreamError as e:
        err("upstream_error", e.message,
            retryable=e.retryable, exit_code=e.exit_code,
            source=e.source, status=e.status)
    payload = make_payload(
        "exa", args.query,
        resolve_search_round(args.state, "exa", args.round),
        papers,
    )
    emit(payload, args.output, args.state)


if __name__ == "__main__":
    main()
