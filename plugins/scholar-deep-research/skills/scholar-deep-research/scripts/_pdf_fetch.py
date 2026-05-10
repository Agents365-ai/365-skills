"""Shared PDF fetching helpers.

Two callers depend on this module:

  - `extract_pdf.py` — single-paper, fail-fast. On error, it calls `err()`
    once and exits.
  - `prefetch_pdfs.py` — batch, fail-soft. On error for one paper, it
    records the failure on that paper and continues with the rest.

The two failure styles are reconciled by raising a typed `FetchError`
from this module. `extract_pdf.py` catches and translates to `err()`;
`prefetch_pdfs.py` catches and writes a structured failure record into
state. No `err()` calls live inside this module, so the same code path
serves both audiences.

Resolution order (mirrors the original behavior in extract_pdf.py):
  1. paper-fetch skill (Agents365-ai/paper-fetch) — 5-source OA chain
     (Unpaywall → arXiv → bioRxiv/medRxiv → PubMed Central → Semantic
     Scholar → Sci-Hub fallback). Discovered via PAPER_FETCH_SCRIPT env
     var or known platform install paths.
  2. Direct Unpaywall API — single-source fallback when paper-fetch is
     not installed. Configurable per call via `fallback_unpaywall=False`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class FetchError(Exception):
    """Typed PDF-fetch failure carrying envelope-ready context.

    Caller is responsible for translating to `err()` (single-paper
    scripts) or accumulating into state (batch scripts). All
    err()-friendly fields are available as attributes.
    """

    def __init__(self, code: str, message: str, *,
                 retryable: bool = False, **ctx: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.ctx = ctx


# ---------- paper-fetch discovery ----------

_FETCH_SCRIPT_REL = "scripts/fetch.py"

# All known skill install paths across platforms.
# Order: Claude Code → OpenCode (config + dotfile) → OpenClaw → Hermes →
# agents convention.
_CONVENTION_PATHS = [
    Path.home() / ".claude" / "skills" / "paper-fetch" / _FETCH_SCRIPT_REL,
    Path.home() / ".config" / "opencode" / "skills" / "paper-fetch" / _FETCH_SCRIPT_REL,
    Path.home() / ".opencode" / "skills" / "paper-fetch" / _FETCH_SCRIPT_REL,
    Path.home() / ".openclaw" / "skills" / "paper-fetch" / _FETCH_SCRIPT_REL,
    Path.home() / ".hermes" / "skills" / "research" / "paper-fetch" / _FETCH_SCRIPT_REL,
    Path.home() / ".agents" / "skills" / "paper-fetch" / _FETCH_SCRIPT_REL,
]


def find_paper_fetch_script() -> Path | None:
    """Locate paper-fetch's fetch.py.

    Discovery chain:
      1. PAPER_FETCH_SCRIPT env var (explicit override)
      2. Known skill install paths across platforms

    Returns None if neither resolves to an existing file.
    """
    env = os.environ.get("PAPER_FETCH_SCRIPT")
    if env:
        p = Path(env)
        if p.is_file():
            return p
        # Soft warning for the override-set-but-bad case; still try
        # convention paths so the run isn't blocked by a stale env var.
        print(f"[warn] PAPER_FETCH_SCRIPT={env} not found, "
              f"trying convention paths", file=sys.stderr)
    for path in _CONVENTION_PATHS:
        if path.is_file():
            return path
    return None


# ---------- single-DOI fetch ----------

def _fetch_via_paper_fetch(doi: str, fetch_script: Path,
                           out_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Resolve DOI via paper-fetch skill (subprocess).

    `out_dir` is created if missing and passed through as `--out` so
    paper-fetch writes the PDF where the caller wants it. Returns
    `(pdf_path, fetch_meta)`. Raises `FetchError` on any failure.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(fetch_script), doi,
         "--format", "json", "--out", str(out_dir)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        detail = result.stdout.strip() or result.stderr.strip()
        raise FetchError(
            "paper_fetch_failed",
            f"paper-fetch exited {result.returncode} for {doi}: {detail}",
            retryable=result.returncode in (2, 4),
            doi=doi,
        )

    try:
        envelope = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        raise FetchError(
            "paper_fetch_bad_response",
            f"paper-fetch returned non-JSON for {doi}",
            retryable=False, doi=doi,
        )

    if not envelope.get("ok"):
        e = envelope.get("error", {})
        raise FetchError(
            "paper_fetch_error",
            e.get("message", f"paper-fetch failed for {doi}"),
            retryable=bool(e.get("retryable", False)),
            doi=doi,
            upstream_code=e.get("code"),
        )

    data = envelope.get("data", {})
    local_path = data.get("local_path") or data.get("path")
    if not local_path or not Path(local_path).is_file():
        # paper-fetch sometimes reports success without a `local_path`
        # in the envelope but writes the PDF into `--out` anyway. Glob
        # the dir as a backstop before giving up.
        pdfs = list(out_dir.glob("*.pdf"))
        if pdfs:
            local_path = str(pdfs[0])
        else:
            raise FetchError(
                "paper_fetch_no_pdf",
                f"paper-fetch succeeded but no PDF found for {doi}",
                retryable=False, doi=doi,
            )

    fetch_meta = {
        "doi": doi,
        "source": data.get("source", "paper-fetch"),
        "title": data.get("title"),
        "authors": data.get("authors"),
        "year": data.get("year"),
        "pdf_url": data.get("pdf_url") or data.get("url"),
    }
    return Path(local_path), fetch_meta


def _fetch_via_unpaywall(doi: str, out_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Fallback: resolve DOI via Unpaywall API directly.

    Writes the PDF into `out_dir`. Raises `FetchError` on any failure.
    """
    import httpx

    out_dir.mkdir(parents=True, exist_ok=True)
    email = os.environ.get("SCHOLAR_MAILTO", "scholar-deep-research@example.com")
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"

    try:
        r = httpx.get(api_url, follow_redirects=True, timeout=30.0,
                      headers={"User-Agent": "scholar-deep-research/0.1"})
        r.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise FetchError(
            "unpaywall_request_failed",
            f"Unpaywall API failed for {doi}: {type(e).__name__}: {e}",
            retryable=True, doi=doi, status=status,
        )

    data = r.json()
    best_oa = data.get("best_oa_location") or {}
    pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")

    if not pdf_url:
        raise FetchError(
            "no_open_access_pdf",
            f"No open-access PDF found for DOI {doi} via Unpaywall",
            retryable=False, doi=doi, is_oa=data.get("is_oa", False),
        )

    try:
        r2 = httpx.get(pdf_url, follow_redirects=True, timeout=60.0,
                       headers={"User-Agent": "scholar-deep-research/0.1"})
        r2.raise_for_status()
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise FetchError(
            "pdf_download_failed",
            f"Failed to download PDF from {pdf_url}: {type(e).__name__}: {e}",
            retryable=True, doi=doi, pdf_url=pdf_url, status=status,
        )

    # Stable filename within out_dir so concurrent fetchers can use a
    # per-paper out_dir without colliding on tempfile suffixes.
    pdf_path = out_dir / "unpaywall.pdf"
    pdf_path.write_bytes(r2.content)

    fetch_meta = {
        "doi": doi,
        "source": "unpaywall_fallback",
        "title": data.get("title"),
        "authors": [a.get("family", "") + ", " + a.get("given", "")
                    for a in (data.get("z_authors") or []) if a.get("family")],
        "year": data.get("year"),
        "pdf_url": pdf_url,
    }
    return pdf_path, fetch_meta


def fetch_pdf(
    doi: str,
    *,
    out_dir: Path | None = None,
    fetch_script: Path | None = None,
    fallback_unpaywall: bool = True,
) -> tuple[Path, dict[str, Any]]:
    """Resolve a DOI to a local PDF. Returns `(pdf_path, fetch_meta)`.

    Args:
        doi: The DOI to resolve (with or without doi: prefix).
        out_dir: Where to write the PDF. If None, a temporary directory
            is created (caller's responsibility to clean up). For
            batch/cache use, pass a stable per-paper directory so the
            file location is deterministic and reusable.
        fetch_script: Pre-resolved path to paper-fetch's fetch.py. If
            None, auto-discover. Pass explicitly to avoid the lookup
            cost in tight loops.
        fallback_unpaywall: When paper-fetch is unavailable or fails
            with `paper_fetch_no_pdf`, try Unpaywall directly. Set
            False to fail fast on paper-fetch errors.

    Raises:
        FetchError on any unrecoverable failure. The exception carries
        a snake_case `code`, a human `message`, a `retryable` flag, and
        envelope-ready context in `ctx`.
    """
    if out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix="scholar_fetch_"))

    if fetch_script is None:
        fetch_script = find_paper_fetch_script()

    if fetch_script is not None:
        try:
            return _fetch_via_paper_fetch(doi, fetch_script, out_dir)
        except FetchError as e:
            # Only fall back when the upstream truly produced nothing —
            # not when it produced a structured "no OA available" answer.
            # If `paper_fetch_error` carries an upstream code that means
            # "the paper exists but is paywalled," Unpaywall would just
            # repeat the same answer. Conservative trigger: only retry
            # via Unpaywall on `paper_fetch_no_pdf` and `paper_fetch_bad_response`.
            if not fallback_unpaywall:
                raise
            if e.code not in ("paper_fetch_no_pdf", "paper_fetch_bad_response"):
                raise

    return _fetch_via_unpaywall(doi, out_dir)
