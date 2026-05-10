#!/usr/bin/env python3
"""prefetch_pdfs.py — pull PDFs for selected papers ahead of Phase 3.

Phase 3 deep-read fan-out is most expensive when each agent has to
discover, download, and store its own PDF inside its own context. This
script does that work upfront, in a single host-side process with
controlled concurrency, so each agent can read a local file path it
finds in `state.papers[<id>].pdf_path`.

Behavior:
  - Iterates `state.selected_ids`, keeping papers whose `tier` is in
    `--tier` (default: ['deep']) and whose `doi` is present. Other
    papers are recorded with `pdf_status` describing why they were
    skipped (`no_doi`, `wrong_tier`).
  - Papers that already have a working `pdf_path` on disk are kept
    untouched; re-runs are cheap.
  - Remaining papers are dispatched through a ThreadPoolExecutor with
    `--concurrency` workers. Each task calls `fetch_pdf()` from
    `_pdf_fetch.py`, which routes through paper-fetch when available
    and falls back to Unpaywall otherwise.
  - All per-paper records are written back via
    `research_state.apply_pdf_paths()` under the exclusive state lock.
    Concurrent prefetch + ingest + triage are race-free.

Failure handling:
  Per-paper failures are recorded on the paper as
  `pdf_status='failed'` with `pdf_failure_code` / `pdf_failure_reason`.
  The script does not exit non-zero just because one paper failed; it
  exits non-zero only on script-level errors (state file missing,
  invalid args). Phase 3 agents see the failure record and can either
  attempt their own download or write `evidence_unavailable`.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from _common import (
    EXIT_VALIDATION, err, maybe_emit_schema, ok,
    reject_dry_run_with_idempotency, set_command_meta, with_idempotency,
)
from _pdf_fetch import FetchError, fetch_pdf, find_paper_fetch_script
from research_state import apply_pdf_paths, load_state


VALID_TIERS = {"deep", "skim", "defer"}


def _safe_subdir(paper_id: str) -> str:
    """Hash the paper id into a filename-safe subdirectory.

    DOI-based ids contain '/' and ':' which we don't want in the
    cache layout. Hashing also keeps subdir names short and stable
    across re-runs.
    """
    return hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:24]


def _existing_pdf_ok(paper: dict[str, Any]) -> bool:
    """True if this paper already has a usable cached PDF.

    Returns True only when both `pdf_path` is set AND the file exists
    on disk, so a deleted cache directory doesn't leave stale state.
    """
    p = paper.get("pdf_path")
    return bool(p) and Path(p).is_file()


def _scan_dropped_pdf(out_root: Path, paper_id: str) -> Path | None:
    """Detect a user-dropped PDF in the per-paper cache subdir.

    When prefetch can't auto-fetch (paywall) or has nothing to fetch
    (no DOI), the user can manually drop a PDF into
    `${out_root}/<safe_subdir>/`. On the next prefetch run, this scan
    picks the file up so the paper is classified as cached without
    re-attempting fetch.
    """
    subdir = out_root / _safe_subdir(paper_id)
    if not subdir.is_dir():
        return None
    pdfs = sorted(subdir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def _build_manifest_entry(paper: dict[str, Any], out_root: Path) -> dict[str, Any]:
    """Produce a manifest row describing where to drop a hand-fetched PDF."""
    from urllib.parse import quote_plus
    pid = paper["id"]
    drop_at = out_root / _safe_subdir(pid) / "manual.pdf"
    doi = paper.get("doi")
    title = paper.get("title") or ""
    alt_urls: list[str] = []
    if doi:
        alt_urls.append(f"https://doi.org/{doi}")
    if title:
        alt_urls.append(
            f"https://scholar.google.com/scholar?q={quote_plus(title)}")
    return {
        "id": pid,
        "doi": doi,
        "title": title,
        "authors": (paper.get("authors") or [])[:2],
        "year": paper.get("year"),
        "drop_at": str(drop_at),
        "current_status": paper.get("pdf_status") or "pending",
        "failure_code": paper.get("pdf_failure_code"),
        "alt_urls": alt_urls,
    }


def _emit_manifest(
    state: dict[str, Any],
    tiers: list[str],
    out_root: Path,
) -> list[dict[str, Any]]:
    """Read-only: list papers in --tier scope that need manual download.

    Excludes papers that are already cached (via state.pdf_path or via
    a user-dropped file in the cache subdir from a prior round).
    """
    selected = state.get("selected_ids") or []
    papers = state.get("papers") or {}
    tier_set = set(tiers)
    needs: list[dict[str, Any]] = []
    for pid in selected:
        paper = papers.get(pid)
        if not paper:
            continue
        tier = paper.get("tier")
        if tier and tier not in tier_set:
            continue
        if _existing_pdf_ok(paper):
            continue
        if _scan_dropped_pdf(out_root, pid):
            continue
        needs.append(_build_manifest_entry(paper, out_root))
    return needs


def _fetch_one(
    paper_id: str,
    doi: str,
    out_root: Path,
    fetch_script: Path | None,
    fallback_unpaywall: bool,
) -> dict[str, Any]:
    """Fetch a single paper. Returns a record (never raises)."""
    out_dir = out_root / _safe_subdir(paper_id)
    try:
        pdf_path, fetch_meta = fetch_pdf(
            doi,
            out_dir=out_dir,
            fetch_script=fetch_script,
            fallback_unpaywall=fallback_unpaywall,
        )
    except FetchError as exc:
        return {
            "id": paper_id,
            "pdf_status": "failed",
            "pdf_failure_code": exc.code,
            "pdf_failure_reason": exc.message,
            "pdf_failure_retryable": exc.retryable,
        }

    try:
        size = pdf_path.stat().st_size
    except OSError:
        size = None

    return {
        "id": paper_id,
        "pdf_status": "ok",
        "pdf_path": str(pdf_path),
        "pdf_source": fetch_meta.get("source"),
        "pdf_bytes": size,
        "pdf_url": fetch_meta.get("pdf_url"),
        "pdf_fetched_at": datetime.now().isoformat(timespec="seconds"),
    }


def _classify_papers(
    state: dict[str, Any],
    tiers: list[str],
    out_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Partition selected papers into (to_fetch, skipped_records).

    Returns:
        to_fetch: list of {id, doi} dicts to dispatch through the pool.
        skipped_records: {id -> record} for papers we won't fetch but
            still want to update on (no_doi, wrong_tier, already_cached).

    Cached classification covers two routes: state.pdf_path pointing at
    a real file, OR a user-dropped *.pdf inside the per-paper cache
    subdir (the second route is what makes the --emit-manifest →
    user downloads → re-run loop work without manual state edits).
    """
    selected = state.get("selected_ids") or []
    papers = state.get("papers") or {}
    to_fetch: list[dict[str, Any]] = []
    skipped: dict[str, dict[str, Any]] = {}
    tier_set = set(tiers)
    for pid in selected:
        paper = papers.get(pid)
        if not paper:
            continue
        tier = paper.get("tier")
        if tier and tier not in tier_set:
            # Untouched — don't even rewrite the record.
            continue
        if _existing_pdf_ok(paper):
            skipped[pid] = {
                "id": pid,
                "pdf_status": "cached",
                "pdf_path": paper.get("pdf_path"),
                "pdf_source": paper.get("pdf_source"),
                "pdf_bytes": paper.get("pdf_bytes"),
            }
            continue
        dropped = _scan_dropped_pdf(out_root, pid)
        if dropped is not None:
            skipped[pid] = {
                "id": pid,
                "pdf_status": "cached",
                "pdf_path": str(dropped),
                "pdf_source": "user_provided",
                "pdf_bytes": dropped.stat().st_size,
            }
            continue
        doi = paper.get("doi")
        if not doi:
            skipped[pid] = {
                "id": pid,
                "pdf_status": "no_doi",
                "pdf_failure_code": "no_doi",
                "pdf_failure_reason":
                    "Paper has no DOI; prefetch_pdfs only handles DOI-based "
                    "resolution. Hand-fetch and set pdf_path manually if needed.",
                "pdf_failure_retryable": False,
            }
            continue
        to_fetch.append({"id": pid, "doi": doi})
    return to_fetch, skipped


def main() -> None:
    p = argparse.ArgumentParser(
        description="Prefetch PDFs for Phase 3 deep-tier papers ahead of "
                    "agent fan-out.",
    )
    p.add_argument(
        "--state",
        default=os.environ.get("SCHOLAR_STATE_PATH", "research_state.json"),
        help="State file path (env: SCHOLAR_STATE_PATH)",
    )
    p.add_argument("--tier", nargs="+", default=["deep"],
                   choices=sorted(VALID_TIERS),
                   help="Which tiers to prefetch (default: deep)")
    p.add_argument("--concurrency", type=int, default=4,
                   help="Number of parallel fetches (default 4). Be polite "
                        "to publisher servers; rarely worth raising above 8.")
    p.add_argument(
        "--out-dir",
        default=os.environ.get(
            "SCHOLAR_CACHE_DIR", ".scholar_cache",
        ) + "/pdfs",
        help="Cache directory for downloaded PDFs (default: "
             "${SCHOLAR_CACHE_DIR:-.scholar_cache}/pdfs)",
    )
    p.add_argument("--no-fallback-unpaywall", dest="fallback_unpaywall",
                   action="store_false",
                   help="Disable Unpaywall fallback when paper-fetch fails. "
                        "Default: fallback enabled.")
    p.add_argument("--dry-run", action="store_true",
                   help="List papers that would be fetched; do NOT download "
                        "or write to state.")
    p.add_argument("--emit-manifest", action="store_true",
                   help="Read-only: list papers in --tier scope that lack a "
                        "PDF (failed, no_doi, or never attempted) with the "
                        "exact path to drop a manually-fetched copy at. "
                        "User can then re-run prefetch_pdfs.py and the dropped "
                        "files will be auto-absorbed as pdf_source=user_provided. "
                        "Mutually exclusive with --dry-run / --idempotency-key.")
    p.add_argument("--idempotency-key",
                   help="Retry-safe key. Retried calls with the same key "
                        "return the original result without re-fetching.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    set_command_meta(p, since="0.8.0", tier="write")
    maybe_emit_schema(p, "prefetch_pdfs")
    args = p.parse_args()
    reject_dry_run_with_idempotency(args)

    if args.emit_manifest and (args.dry_run or args.idempotency_key):
        err("inconsistent_input",
            "--emit-manifest is read-only and mutually exclusive with "
            "--dry-run / --idempotency-key.",
            retryable=False, exit_code=EXIT_VALIDATION)

    if args.concurrency < 1:
        err("invalid_concurrency",
            f"--concurrency must be >= 1, got {args.concurrency}",
            retryable=False, exit_code=EXIT_VALIDATION,
            concurrency=args.concurrency)

    path = Path(args.state)
    state = load_state(path)
    out_root = Path(args.out_dir)

    if args.emit_manifest:
        needs = _emit_manifest(state, args.tier, out_root)
        ok({
            "tier": args.tier,
            "out_dir": str(out_root),
            "needs_user_download": needs,
            "count": len(needs),
            "next_steps": [
                "Drop each PDF at its drop_at path "
                "(any *.pdf filename in that subdir works).",
                "Re-run prefetch_pdfs.py — dropped files are absorbed "
                "as pdf_source=user_provided without re-fetch.",
            ],
        })
        return

    to_fetch, skipped = _classify_papers(state, args.tier, out_root)

    if args.dry_run:
        ok({
            "dry_run": True,
            "tier": args.tier,
            "out_dir": str(out_root),
            "would_fetch": len(to_fetch),
            "would_fetch_ids": [p["id"] for p in to_fetch],
            "skipped": {
                "count": len(skipped),
                "by_status": _count_by_status(skipped.values()),
            },
        })
        return

    fetch_script = find_paper_fetch_script()
    fetch_script_used = str(fetch_script) if fetch_script else None

    def compute() -> dict[str, Any]:
        records: dict[str, dict[str, Any]] = dict(skipped)
        if to_fetch:
            out_root.mkdir(parents=True, exist_ok=True)
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                futures = {
                    pool.submit(
                        _fetch_one, item["id"], item["doi"],
                        out_root, fetch_script,
                        args.fallback_unpaywall,
                    ): item["id"]
                    for item in to_fetch
                }
                for fut in as_completed(futures):
                    rec = fut.result()
                    records[rec["id"]] = rec

        summary = apply_pdf_paths(path, records)
        return {
            "tier": args.tier,
            "out_dir": str(out_root),
            "attempted": len(to_fetch),
            "skipped": len(skipped),
            "by_status": _count_by_status(records.values()),
            "fetch_script": fetch_script_used,
            "fallback_unpaywall": args.fallback_unpaywall,
            "summary": summary,
        }

    with_idempotency(args, compute, signature_exclude=("concurrency",))


def _count_by_status(records) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        s = r.get("pdf_status") or "unknown"
        counts[s] = counts.get(s, 0) + 1
    return counts


if __name__ == "__main__":
    main()
