#!/usr/bin/env python3
"""list_sources.py — emit the federated search source registry.

Reads each `search_*.py` module's `SOURCE_META` constant and returns one
envelope listing every available academic / web source plus its
capabilities (domain, index type, freshness lag, auth requirement, …).

Use this when an orchestrator needs to decide which sources to query —
e.g. "I have a question about recent CS preprints, which sources should
I hit?" — without grepping each script's docstring. The schema lives in
`_search_meta.py`; validation errors per source are surfaced under
`validation_warnings` so one misconfigured source doesn't break the
whole listing.

Usage:
  python scripts/list_sources.py                 # full envelope
  python scripts/list_sources.py --domain academic
  python scripts/list_sources.py --auth none     # sources usable without keys
  python scripts/list_sources.py --schema        # introspect
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from _common import (
    EXIT_RUNTIME, err, maybe_emit_schema, ok, set_command_meta,
)
from _search_meta import validate_source_meta


def _discover_sources() -> tuple[list[dict], list[str]]:
    """Walk `search_*.py` siblings and pull SOURCE_META from each.

    Returns `(sources, warnings)`. A source missing SOURCE_META or
    failing validation lands in `warnings` and is NOT added to
    `sources` — better to surface a broken source than silently fall
    back to a partial picture.
    """
    here = Path(__file__).resolve().parent
    # Make sure we can `import search_<name>` from this directory.
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    sources: list[dict] = []
    warnings: list[str] = []
    for f in sorted(here.glob("search_*.py")):
        mod_name = f.stem
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            warnings.append(f"{mod_name}: import failed ({type(e).__name__}: {e})")
            continue
        meta = getattr(mod, "SOURCE_META", None)
        if meta is None:
            warnings.append(f"{mod_name}: no SOURCE_META exposed")
            continue
        validation_errs = validate_source_meta(meta)
        if validation_errs:
            warnings.append(f"{mod_name}: " + "; ".join(validation_errs))
            continue
        sources.append(meta)
    return sources, warnings


def _filter(sources: list[dict], *,
            domain: str | None,
            index_type: str | None,
            auth: str | None,
            needs_relevance_filter: bool | None) -> list[dict]:
    """Apply --domain / --index-type / --auth / --needs-relevance-filter."""
    out = sources
    if domain:
        out = [s for s in out if s["domain"] == domain]
    if index_type:
        out = [s for s in out if s["index_type"] == index_type]
    if auth:
        out = [s for s in out if s["auth"] == auth]
    if needs_relevance_filter is not None:
        out = [s for s in out
               if s["needs_relevance_filter"] == needs_relevance_filter]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--domain",
                   help="Filter by domain (academic, preprint, medical, "
                        "bio_preprint, cs_academic, general).")
    p.add_argument("--index-type",
                   help="Filter by index type (metadata_aggregator, "
                        "preprint_server, subject_aggregator, web_search).")
    p.add_argument("--auth",
                   help="Filter by auth requirement (none, "
                        "polite_email_optional, ncbi_key_optional, "
                        "api_key_required).")
    p.add_argument("--needs-relevance-filter",
                   choices=("true", "false"),
                   help="Only sources whose results need (or don't need) "
                        "post-filtering.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit.")
    set_command_meta(p, since="0.15.0", tier="read")
    maybe_emit_schema(p, "list_sources")
    args = p.parse_args()

    sources, warnings = _discover_sources()
    if not sources:
        err("no_sources_discovered",
            "No search_*.py modules exposed a valid SOURCE_META. "
            "See warnings for per-module reasons.",
            retryable=False, exit_code=EXIT_RUNTIME,
            warnings=warnings)

    nrf: bool | None = None
    if args.needs_relevance_filter == "true":
        nrf = True
    elif args.needs_relevance_filter == "false":
        nrf = False

    filtered = _filter(
        sources,
        domain=args.domain,
        index_type=args.index_type,
        auth=args.auth,
        needs_relevance_filter=nrf,
    )

    ok({
        "sources": filtered,
        "count": len(filtered),
        "total_available": len(sources),
        "validation_warnings": warnings,
    })


if __name__ == "__main__":
    main()
