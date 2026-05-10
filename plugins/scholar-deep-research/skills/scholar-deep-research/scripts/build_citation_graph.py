#!/usr/bin/env python3
"""build_citation_graph.py — snowball search via OpenAlex citation links.

Two directions:
  - backward: papers that this paper *cites* (its references)
  - forward:  papers that cite *this* paper (downstream impact)

Reads the top-N selected (or score-ranked) papers from state, queries OpenAlex
for their refs / cited-by, normalizes the new candidates, and ingests them
back into state with discovered_via="citation_chase". Existing papers (matched
on DOI / OpenAlex ID) are skipped.

Re-running this script after changing --seed-top is safe — already-fetched
papers will be re-merged, not duplicated.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

# `httpx` is imported lazily inside network-calling helpers so that
# `--schema` introspection works on machines without httpx installed.

from _common import (
    EXIT_UPSTREAM, EXIT_VALIDATION, USER_AGENT, UpstreamError, command_signature,
    err, make_paper, make_payload, maybe_emit_schema, ok, read_cache,
    set_command_meta, write_cache,
)
from _s2_citations import (
    S2Error, normalize_s2_paper, s2_get_citations, s2_get_references,
    s2_paper_id,
)
from research_state import apply_citation_chase, load_state, make_paper_id

WORKS = "https://api.openalex.org/works"


# Per-seed failure accumulator. Populated by the fetch_* helpers; surfaced
# in the envelope's `seed_failures` field so orchestrators can distinguish
# "no new papers" from "OpenAlex was failing." Reset at the start of main().
SEED_FAILURES: list[dict[str, Any]] = []


def _record_failure(seed_id: str | None, stage: str, exc: Exception) -> None:
    """Append a structured record of a per-seed fetch failure.

    Two backend-specific shapes are flattened into one envelope row:
      - S2Error: carries .code (e.g. "s2_unauthorized"), .status, .retryable.
      - httpx.HTTPError: carries .response.status_code; no machine-routable
        code for now (callers key off `stage`).
    """
    status: int | None = None
    code: str | None = None
    retryable: bool | None = None
    if isinstance(exc, S2Error):
        status = exc.status
        code = exc.code
        retryable = exc.retryable
    else:
        resp = getattr(exc, "response", None)
        if resp is not None:
            status = getattr(resp, "status_code", None)
    SEED_FAILURES.append({
        "seed_id": seed_id,
        "stage": stage,
        "status": status,
        "code": code,
        "retryable": retryable,
        "message": f"{type(exc).__name__}: {exc}",
    })
    sys.stderr.write(f"{stage} error for {seed_id}: {exc}\n")


def fetch_work(oa_id: str, email: str | None) -> dict | None:
    import httpx  # lazy
    headers = {"User-Agent": USER_AGENT}
    params = {}
    if email:
        params["mailto"] = email
        headers["From"] = email
    try:
        r = httpx.get(f"{WORKS}/{oa_id}", params=params,
                      headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        _record_failure(oa_id, "fetch_work", e)
        return None


def fetch_referenced(seed_id: str, oa_ids: list[str],
                     email: str | None) -> list[dict]:
    """Batch-fetch referenced works by OpenAlex IDs (limit 25 per request via filter)."""
    import httpx  # lazy
    out = []
    chunk = 25
    headers = {"User-Agent": USER_AGENT}
    for i in range(0, len(oa_ids), chunk):
        batch = oa_ids[i:i + chunk]
        params: dict[str, Any] = {
            "filter": "openalex_id:" + "|".join(batch),
            "per-page": chunk,
            "select": "id,doi,title,authorships,publication_year,"
                      "primary_location,cited_by_count,abstract_inverted_index",
        }
        if email:
            params["mailto"] = email
        try:
            r = httpx.get(WORKS, params=params, headers=headers, timeout=30.0)
            r.raise_for_status()
            out.extend(r.json().get("results", []))
        except httpx.HTTPError as e:
            _record_failure(seed_id, "fetch_referenced", e)
        time.sleep(0.1)
    return out


def fetch_cited_by(oa_id: str, limit: int, email: str | None) -> list[dict]:
    import httpx  # lazy
    headers = {"User-Agent": USER_AGENT}
    params: dict[str, Any] = {
        "filter": f"cites:{oa_id}",
        "per-page": min(limit, 200),
        "select": "id,doi,title,authorships,publication_year,"
                  "primary_location,cited_by_count,abstract_inverted_index",
    }
    if email:
        params["mailto"] = email
    try:
        r = httpx.get(WORKS, params=params, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json().get("results", [])
    except httpx.HTTPError as e:
        _record_failure(oa_id, "fetch_cited_by", e)
        return []


def normalize(w: dict[str, Any]) -> dict[str, Any]:
    # Reuse the OpenAlex normalizer logic (kept inline to avoid cross-import).
    from search_openalex import _normalize  # local import for clarity
    return _normalize(w)


def _chase_s2(seed: dict[str, Any], direction: str,
              cited_by_limit: int) -> tuple[list[dict[str, Any]], bool]:
    """Run S2 citation chase for one seed. Returns (records, success_flag).

    `success_flag` is True when at least one S2 endpoint returned without
    raising — empty results count as success (the paper exists in S2 but
    has no records in the requested direction). Failures are appended to
    SEED_FAILURES with stage names `s2_references` / `s2_citations`.
    """
    pid = s2_paper_id(seed)
    if pid is None:
        return [], False
    new_records: list[dict[str, Any]] = []
    success = False

    if direction in ("backward", "both"):
        try:
            refs = s2_get_references(pid, max_results=cited_by_limit)
            for r in refs:
                kw = normalize_s2_paper(r)
                if kw.get("title"):
                    new_records.append(make_paper(**kw))
            success = True
        except S2Error as exc:
            _record_failure(seed.get("id"), "s2_references", exc)

    if direction in ("forward", "both"):
        try:
            cits = s2_get_citations(pid, max_results=cited_by_limit)
            for c in cits:
                kw = normalize_s2_paper(c)
                if kw.get("title"):
                    new_records.append(make_paper(**kw))
            success = success or True
        except S2Error as exc:
            _record_failure(seed.get("id"), "s2_citations", exc)

    return new_records, success


def main() -> None:
    p = argparse.ArgumentParser(description="Build citation graph from state.")
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--seed-top", type=int, default=8,
                   help="Number of top-ranked papers to use as seeds")
    p.add_argument("--direction", choices=["forward", "backward", "both"],
                   default="both")
    p.add_argument("--source", choices=["openalex", "s2", "both"],
                   default="both",
                   help="Citation graph backend(s). 'openalex' uses the "
                        "OpenAlex Works API (good general coverage). 's2' "
                        "uses Semantic Scholar (better for CS / arXiv / "
                        "cross-disciplinary). 'both' runs both and merges "
                        "results — re-ingest dedupes by id, so overlap is "
                        "harmless. Default: both. S2 requires DOI / arXiv / "
                        "PMID on each seed; seeds with only an OpenAlex id "
                        "skip the S2 backend. S2 quota is higher with "
                        "S2_API_KEY set.")
    p.add_argument("--depth", type=int, default=1,
                   help="Currently only depth=1 supported")
    p.add_argument("--cited-by-limit", type=int, default=50,
                   help="Max cited-by results per seed")
    p.add_argument("--email",
                   default=os.environ.get("SCHOLAR_MAILTO"),
                   help="Polite pool email (env: SCHOLAR_MAILTO)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview seeds and estimated request count, "
                        "without making any HTTP calls or mutating state")
    p.add_argument("--idempotency-key",
                   help="If set, a retried run with the same key returns "
                        "the cached response without re-hitting OpenAlex or "
                        "re-mutating state. Cache dir: .scholar_cache/ "
                        "(env: SCHOLAR_CACHE_DIR).")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    set_command_meta(p, since="0.10.0", tier="write")
    maybe_emit_schema(p, "build_citation_graph")
    args = p.parse_args()

    # Idempotency short-circuit: cache hit returns immediately, no network,
    # no state mutation. Signature check catches accidental key reuse with
    # different arguments — returns `idempotency_key_mismatch` rather than
    # silently serving stale data.
    if args.idempotency_key and not args.dry_run:
        sig = command_signature(args, exclude=("email",))
        cached = read_cache(args.idempotency_key)
        if cached is not None:
            if cached.get("signature") and cached["signature"] != sig:
                err("idempotency_key_mismatch",
                    f"Idempotency key '{args.idempotency_key}' was "
                    f"previously used with different arguments. Use a new "
                    f"key or flush the cache entry.",
                    retryable=False, exit_code=EXIT_VALIDATION,
                    key=args.idempotency_key,
                    cached_signature=cached["signature"],
                    current_signature=sig)
            ok(cached["response"], meta={
                "cache_hit": True,
                "idempotency_key": args.idempotency_key,
                "cached_at": cached.get("cached_at"),
            })
            return

    path = Path(args.state)
    state = load_state(path)

    # pick seeds: prefer .selected_ids, fall back to top-by-score
    if state.get("selected_ids"):
        seeds = [state["papers"][pid] for pid in state["selected_ids"]
                 if pid in state["papers"]][: args.seed_top]
    else:
        seeds = sorted(state["papers"].values(),
                       key=lambda x: x.get("score", 0),
                       reverse=True)[: args.seed_top]

    if not seeds:
        err("no_seeds",
            "No seed papers. Run rank_papers.py and `research_state.py "
            "select` first.",
            retryable=False, exit_code=EXIT_VALIDATION)

    use_openalex = args.source in ("openalex", "both")
    use_s2 = args.source in ("s2", "both")

    seeds_with_oa = [s for s in seeds if s.get("openalex_id")] if use_openalex else []
    skipped_oa = ([s["id"] for s in seeds if not s.get("openalex_id")]
                  if use_openalex else [])

    seeds_for_s2 = [s for s in seeds if s2_paper_id(s)] if use_s2 else []
    skipped_s2 = ([s["id"] for s in seeds if not s2_paper_id(s)]
                  if use_s2 else [])

    # Hard fail when only S2 was requested and no seed has a resolvable
    # handle — running with no seeds is a no-op, but the caller should
    # see a structured error rather than a silent zero-fetch envelope.
    if args.source == "s2" and not seeds_for_s2:
        err("no_resolvable_seeds",
            "Source='s2' but no selected paper has a DOI / arXiv id / PMID. "
            "Either re-run with --source=openalex or backfill paper handles.",
            retryable=False, exit_code=EXIT_VALIDATION,
            seed_count=len(seeds))

    if args.dry_run:
        backward_req = 2 * len(seeds_with_oa) if args.direction in ("backward", "both") else 0
        forward_req = len(seeds_with_oa) if args.direction in ("forward", "both") else 0
        s2_req_estimate = len(seeds_for_s2) * (
            2 if args.direction == "both" else 1)
        ok({
            "dry_run": True,
            "would_fetch": {
                "source": args.source,
                "seeds": max(len(seeds_with_oa), len(seeds_for_s2)),
                "skipped_seeds_without_openalex_id": skipped_oa,
                "skipped_seeds_without_resolvable_id": skipped_s2,
                "direction": args.direction,
                "cited_by_limit": args.cited_by_limit,
                "estimated_requests": backward_req + forward_req + s2_req_estimate,
                "by_backend": {
                    "openalex": {
                        "seeds": len(seeds_with_oa),
                        "estimated_requests": backward_req + forward_req,
                    },
                    "s2": {
                        "seeds": len(seeds_for_s2),
                        "estimated_requests": s2_req_estimate,
                    },
                },
                "seed_ids": [s["id"] for s in seeds],
                "note": "Estimates assume ~1 metadata + ~1 batch GET per "
                        "OpenAlex seed and 1 GET per S2 endpoint.",
            },
        })
        return

    SEED_FAILURES.clear()
    new_records: list[dict[str, Any]] = []
    seeds_any_success: set[str] = set()
    backends_used: list[str] = []

    if use_openalex:
        backends_used.append("openalex")
        for seed in seeds_with_oa:
            oa_id = seed["openalex_id"]
            seed_success = False
            if args.direction in ("backward", "both"):
                full = fetch_work(oa_id, args.email)
                if full:
                    refs = full.get("referenced_works", [])
                    ref_ids = [r.rsplit("/", 1)[-1] for r in refs if r]
                    if ref_ids:
                        works = fetch_referenced(oa_id, ref_ids, args.email)
                        for w in works:
                            new_records.append(normalize(w))
                    seed_success = True
            if args.direction in ("forward", "both"):
                cited_by = fetch_cited_by(oa_id, args.cited_by_limit, args.email)
                if cited_by or not SEED_FAILURES or SEED_FAILURES[-1]["seed_id"] != oa_id:
                    for w in cited_by:
                        new_records.append(normalize(w))
                    seed_success = seed_success or True
            if seed_success:
                seeds_any_success.add(seed["id"])

    if use_s2:
        backends_used.append("s2")
        for seed in seeds_for_s2:
            records, ok_flag = _chase_s2(
                seed, args.direction, args.cited_by_limit)
            new_records.extend(records)
            if ok_flag:
                seeds_any_success.add(seed["id"])

    # Track distinct seeds that were actually attempted across any backend.
    attempted_seed_ids = {s["id"] for s in seeds_with_oa} | {
        s["id"] for s in seeds_for_s2}
    seeds_attempted = len(attempted_seed_ids)

    wholly_failed = (
        seeds_attempted > 0
        and not seeds_any_success
        and SEED_FAILURES
    )

    if wholly_failed:
        err("upstream_error",
            "All citation-chase seeds failed across requested backends. "
            "Retry with the same --idempotency-key to resume.",
            retryable=True, exit_code=EXIT_UPSTREAM,
            seed_failures=SEED_FAILURES,
            backends_used=backends_used,
            seeds_attempted=seeds_attempted,
            seeds_with_success=0)

    # Merge + query-append runs under the state lock via apply_citation_chase.
    summary = apply_citation_chase(
        path,
        new_records,
        {
            "source": "_".join(backends_used) + "_citation_chase",
            "query": f"seeds={len(seeds)} direction={args.direction} "
                     f"source={args.source}",
        },
    )

    response = {
        "source": args.source,
        "backends_used": backends_used,
        "seeds": len(seeds),
        "seeds_used": seeds_attempted,
        "seeds_with_success": len(seeds_any_success),
        "skipped_seeds_without_openalex_id": skipped_oa,
        "skipped_seeds_without_resolvable_id": skipped_s2,
        "direction": args.direction,
        "fetched": len(new_records),
        "added": summary["added"],
        "merged": summary["merged"],
        "total_papers": summary["total_papers"],
        "partial_failure": bool(SEED_FAILURES),
        "seed_failures": list(SEED_FAILURES),
    }

    if args.idempotency_key:
        sig = command_signature(args, exclude=("email",))
        write_cache(args.idempotency_key, response, signature=sig)
        ok(response, meta={
            "cache_hit": False,
            "idempotency_key": args.idempotency_key,
        })
    else:
        ok(response)


if __name__ == "__main__":
    main()
