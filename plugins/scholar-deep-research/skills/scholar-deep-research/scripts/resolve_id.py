#!/usr/bin/env python3
"""resolve_id.py — figure out what kind of paper ID an agent has in hand.

Agents often receive a paper reference as a bare string ("10.1145/...",
"W2059403765", "arxiv:2301.12345", or a URL) without knowing which lookup
script can use it. Calling `query --field papers --where doi:...` with the
wrong canonical form leads to retry loops.

This is the read-only resolver: hand it a string, get back the canonical
form, the detected kind, the search scripts that can fetch metadata for it,
and a transparent record of what normalization was applied.

No state, no network, no cache. Pure detection + canonicalization.
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from _common import maybe_emit_schema, ok, set_command_meta
from research_state import normalize_doi

# OpenAlex Work IDs are "W" + digits.
_OPENALEX_RE = re.compile(r"^W\d+$", re.IGNORECASE)

# arXiv new-style IDs: YYMM.NNNNN with optional vN suffix.
_ARXIV_NEW_RE = re.compile(
    r"^(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)$", re.IGNORECASE
)
# arXiv old-style: math/0211159 or hep-th/9901001 or similar.
_ARXIV_OLD_RE = re.compile(
    r"^(?:arxiv:)?([a-z-]+(?:\.[A-Z]{2})?/\d{7})$"
)
# arXiv URL form (abs or pdf).
_ARXIV_URL_RE = re.compile(
    r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/"
    r"([\w\-/.]+?)(?:v\d+)?(?:\.pdf)?/?$",
    re.IGNORECASE,
)

# PMID: pure digits (1–9). The optional pmid: prefix is the canonical form.
_PMID_RE = re.compile(r"^(?:pmid:)?(\d{1,9})$", re.IGNORECASE)

# Source map by detected kind. These are the search scripts that accept the
# given ID directly. Not exhaustive — agents can always cross-walk via DOI.
_SOURCES_BY_KIND: dict[str, list[str]] = {
    "doi": ["openalex", "crossref", "pubmed"],
    "openalex": ["openalex"],
    "arxiv": ["arxiv"],
    "pmid": ["pubmed"],
}


def resolve_id(raw: str) -> dict[str, Any]:
    """Detect the kind of `raw`, canonicalize it, and report sources.

    Always returns the same dict shape, even on unknown input — so callers
    can branch on `detected_kind == "unknown"` without try/except.
    """
    original = raw
    notes: list[str] = []
    raw = (raw or "").strip()
    if raw != original:
        notes.append("stripped surrounding whitespace")

    if not raw:
        return _result(original, None, "unknown", notes + ["input was empty"])

    # --- DOI (catches URL, prefixed, bare). The most permissive matcher
    # runs first because DOIs can contain slashes that look like other IDs.
    doi = normalize_doi(raw)
    if doi:
        if "doi.org" in original.lower():
            notes.append("extracted DOI from doi.org URL")
        elif original.lower().startswith("doi:"):
            notes.append("stripped doi: prefix")
        if any(c.isupper() for c in raw):
            notes.append("lowercased DOI")
        sources = list(_SOURCES_BY_KIND["doi"])
        # Prefix-based hints — these specific DOI prefixes are first-party
        # for additional sources beyond the generic three.
        if doi.startswith("10.1101/"):
            sources.append("biorxiv")
            notes.append("CSHL prefix → bioRxiv/medRxiv first-party source")
        if doi.startswith("10.48550/arxiv."):
            sources.append("arxiv")
            notes.append("arXiv DOI prefix → arxiv first-party source")
        return _result(original, f"doi:{doi}", "doi", notes,
                       sources=sources)

    # --- arXiv URL
    if (m := _ARXIV_URL_RE.match(raw)):
        return _result(original, f"arxiv:{m.group(1)}", "arxiv",
                       notes + ["extracted arXiv ID from URL"])

    # --- arXiv new-style (YYMM.NNNNN)
    if (m := _ARXIV_NEW_RE.match(raw)):
        if raw.lower().startswith("arxiv:"):
            notes.append("stripped arxiv: prefix")
        return _result(original, f"arxiv:{m.group(1)}", "arxiv", notes)

    # --- arXiv old-style (subject/NNNNNNN)
    if (m := _ARXIV_OLD_RE.match(raw)):
        if raw.lower().startswith("arxiv:"):
            notes.append("stripped arxiv: prefix")
        return _result(original, f"arxiv:{m.group(1)}", "arxiv", notes)

    # --- OpenAlex Work ID
    if _OPENALEX_RE.match(raw):
        canonical = raw.upper()
        if raw != canonical:
            notes.append("uppercased W prefix")
        return _result(original, f"openalex:{canonical}", "openalex", notes)

    # --- PMID (digits, optionally pmid: prefix). Last among the matchers
    # because it's the loosest pattern (would shadow nothing important here).
    if (m := _PMID_RE.match(raw)):
        if raw.lower().startswith("pmid:"):
            notes.append("stripped pmid: prefix")
        return _result(original, f"pmid:{m.group(1)}", "pmid", notes)

    return _result(
        original, None, "unknown",
        notes + ["input does not match DOI, OpenAlex W-ID, arXiv, or PMID"],
    )


def _result(raw: str, canonical: str | None, kind: str,
            notes: list[str], *,
            sources: list[str] | None = None) -> dict[str, Any]:
    return {
        "input": raw,
        "canonical_id": canonical,
        "detected_kind": kind,
        "available_sources": sources if sources is not None
        else _SOURCES_BY_KIND.get(kind, []),
        "normalization_notes": notes,
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Resolve a paper identifier to its canonical form, detect its "
            "kind (doi/openalex/arxiv/pmid), and report which search "
            "scripts can fetch metadata for it. Read-only, no network."
        )
    )
    set_command_meta(p, since="0.10.0", tier="read")
    p.add_argument("id", help="Paper identifier in any common form "
                              "(DOI, DOI URL, OpenAlex W-ID, arXiv ID, "
                              "arXiv URL, or PMID).")
    maybe_emit_schema(p, "resolve_id")
    args = p.parse_args()
    ok(resolve_id(args.id))


if __name__ == "__main__":
    main()
