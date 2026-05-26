#!/usr/bin/env python3
"""Fetch legal open-access PDFs by DOI.

Resolution order: Unpaywall -> Semantic Scholar openAccessPdf ->
arXiv -> PMC OA -> bioRxiv/medRxiv.

Exit codes:
  0  success (all DOIs resolved and downloaded / dry-run previewed)
  1  unresolved — one or more DOIs had no OA copy; no transport failure
  2  reserved for auth errors (currently unused; Unpaywall gracefully degrades)
  3  validation error (bad arguments, missing input)
  4  transport error — network / download / IO failure (retryable class)

If UNPAYWALL_EMAIL is not set, the Unpaywall source is skipped
and the remaining 4 sources are still tried.

Machine contract:
  stdout — one JSON object per invocation (or NDJSON with --stream)
  stderr — NDJSON progress events when --format json; prose when --format text

Contract-changing version of this file. The schema_version below is what the
`schema` subcommand reports and what appears in every response's `meta` slot;
agents that cache schema should compare against it to detect drift.
"""
from __future__ import annotations

import argparse
import html.parser
import ipaddress
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

CLI_VERSION = "0.14.0"
SCHEMA_VERSION = "1.10.0"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMAIL = os.environ.get("UNPAYWALL_EMAIL", "").strip()
# UA for API calls (Unpaywall requires contact email in the UA per their ToS).
UA = f"paper-fetch/{CLI_VERSION} (mailto:{EMAIL or 'anonymous'})"
# UA for PDF downloads — some publishers (e.g., iiarjournals.org) return
# HTTP 403 for non-browser User-Agents even on OA PDFs. Uses a generic
# modern browser identifier; the per-request Accept header still declares
# we want a PDF, and the host allowlist still restricts where we fetch.
DOWNLOAD_UA = (
    f"Mozilla/5.0 (compatible; paper-fetch/{CLI_VERSION}; "
    f"+https://github.com/obra/paper-fetch) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB

# Canonical DOI shape — kept here so build_schema() and runtime validation
# share one source of truth. Schema-side this is exposed as the regex below
# without the surrounding anchors.
DOI_PATTERN = r"^10\..+/.+$"
_DOI_RE = re.compile(DOI_PATTERN)

EXIT_SUCCESS = 0
EXIT_UNRESOLVED = 1
EXIT_AUTH = 2  # reserved
EXIT_VALIDATION = 3
EXIT_TRANSPORT = 4

# Per-error retry backoff hints surfaced to agents. Only set on retryable=True
# codes. Values are recommendations, not guarantees: an orchestrator that
# ignores them and retries sooner will at worst re-hit the same failure.
RETRY_AFTER_HOURS = {
    "not_found": 168,              # OA availability changes on embargo / preprint timescale
    "download_network_error": 1,   # transient network / upstream hiccup
    "download_size_exceeded": 24,  # publisher posted a >50 MB PDF; revisit in a day
    "download_io_error": 1,        # local disk full / permission blip
}

# ---------------------------------------------------------------------------
# Institutional mode
# ---------------------------------------------------------------------------

# Rate limit (institutional mode only — public OA sources are unmetered by
# their operators and do not need client-side pacing).
INSTITUTIONAL_RATE_PER_SEC = 1.0

# ---------------------------------------------------------------------------
# Sci-Hub fallback
# ---------------------------------------------------------------------------

# Default mirror list (snapshot from https://www.sci-hub.pub/ on 2026-04-26).
# Operator can override with PAPER_FETCH_SCIHUB_MIRRORS=sci-hub.ru,sci-hub.st,...
# When all configured mirrors miss, we re-scan SCIHUB_DISCOVERY_URL once per
# process for a fresh list.
SCIHUB_DEFAULT_MIRRORS = (
    "sci-hub.ru",
    "sci-hub.st",
    "sci-hub.su",
    "sci-hub.box",
    "sci-hub.red",
    "sci-hub.al",
    "sci-hub.mk",
    "sci-hub.ee",
)
SCIHUB_DISCOVERY_URL = "https://www.sci-hub.pub/"

# Mobile Safari UA for Sci-Hub HTML page fetches. Mobile clients tend to
# get a simpler page layout less likely to trigger CAPTCHA. Technique
# borrowed from ethanwillis/zotero-scihub.
SCIHUB_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Mobile/15E148 Safari/604.1"
)

# Polite per-host pacing for Sci-Hub mirror requests. Public OA APIs are
# unmetered; Sci-Hub mirrors throttle and CAPTCHA aggressively, so we pace
# Sci-Hub fetches independently of institutional mode.
SCIHUB_RATE_PER_SEC = 1.0
_last_scihub_request_monotonic: float = 0.0

# Hostnames blocked in every mode. Covers two threat classes:
#   - loopback aliases that resolve to 127.0.0.1 / ::1 but pass the IP literal
#     check (the ip literal check only fires when the URL host IS an IP)
#   - cloud metadata endpoints that can leak IAM credentials if an SSRF
#     target pivoted into fetching from them
# This does not defend against DNS rebinding — a hostname pointing at a
# public IP at validation time but a private IP at connection time slips
# through. Mitigating that requires pin-after-resolve and is out of scope
# for v0.8.0.
_BLOCKED_HOSTS = {
    # Loopback aliases
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    # Cloud metadata
    "metadata.google.internal",
    "metadata.aws.internal",
    "metadata",  # some cloud SDKs resolve bare 'metadata'
}


def _is_institutional() -> bool:
    """True iff the operator has opted the process into institutional mode."""
    return bool(os.environ.get("PAPER_FETCH_INSTITUTIONAL"))


def _auth_mode() -> str:
    return "institutional" if _is_institutional() else "public"


# ---------------------------------------------------------------------------
# CloakBrowser fallback (operator-controlled, off by default)
# ---------------------------------------------------------------------------

# When PAPER_FETCH_CLOAK is set, a download blocked by Cloudflare (HTTP 403/429
# or an HTML interstitial served in place of the PDF) is retried through
# CloakBrowser — a stealth Chromium that can pass the JS challenge. fetch.py
# shells out to the companion `cloak_pdf.py` via a cloakbrowser-importable
# Python, so this file keeps its stdlib-only footprint. Bytes returned by the
# helper are re-validated through the same %PDF + size checks as any other
# download; the agent cannot opt in (env var is an operator action).

# URLs that were ultimately downloaded via CloakBrowser, so the result envelope
# can flag `via: cloak` for orchestrator visibility.
_CLOAK_DOWNLOADS: set[str] = set()


def _is_cloak_enabled() -> bool:
    """True iff the operator opted into the CloakBrowser fallback."""
    return bool(os.environ.get("PAPER_FETCH_CLOAK"))


def _resolve_cloak_python() -> str | None:
    """Locate a Python interpreter that can import cloakbrowser.

    Order: CLOAKBROWSER_PYTHON env → ~/github/CloakBrowser/.venv/bin/python →
    the current interpreter. Mirrors cloakFetch's cloak_fetch.sh resolution.
    Returns None when no candidate can import cloakbrowser.
    """
    candidates = [
        os.environ.get("CLOAKBROWSER_PYTHON", "").strip(),
        str(Path.home() / "github" / "CloakBrowser" / ".venv" / "bin" / "python"),
        sys.executable,
    ]
    for c in candidates:
        if not c:
            continue
        if not (os.path.isfile(c) or shutil.which(c)):
            continue
        try:
            r = subprocess.run(
                [c, "-c", "import cloakbrowser"],
                capture_output=True,
                timeout=30,
            )
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def _cloak_fetch_pdf(url: str, *, timeout: int) -> bytes | None:
    """Fetch PDF bytes through CloakBrowser. Returns bytes, or None on failure.

    Shells out to the companion cloak_pdf.py via a cloakbrowser-importable
    Python. Fails closed: a missing dependency or any error returns None so the
    caller falls through to the next source.
    """
    py = _resolve_cloak_python()
    if not py:
        _progress("download_cloak_skip", url=url, reason="no_cloakbrowser_python")
        return None
    helper = Path(__file__).with_name("cloak_pdf.py")
    if not helper.exists():
        _progress("download_cloak_skip", url=url, reason="helper_missing")
        return None
    _progress("download_cloak_try", url=url)
    try:
        # Browser launch + challenge solve is slow; give it headroom over the
        # per-request timeout.
        r = subprocess.run(
            [py, str(helper), url, str(timeout)],
            capture_output=True,
            timeout=timeout + 90,
        )
    except Exception as e:
        _progress("download_cloak_error", url=url, error=str(e))
        return None
    if r.returncode != 0 or not r.stdout:
        tail = r.stderr.decode("utf-8", "replace")[-200:] if r.stderr else ""
        _progress("download_cloak_error", url=url, reason="helper_failed", stderr=tail)
        return None
    return r.stdout


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Universal URL safety check — applied in every mode.

    Returns (ok, reason). Blocks SSRF vectors regardless of whether the
    hostname would pass the allowlist check:
      - non-http(s) schemes (file://, ftp://, gopher://, etc.)
      - non-80/443 ports
      - IP literals in private / loopback / link-local / reserved space
      - known cloud metadata hostnames
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "malformed_url"
    if parsed.scheme not in ("http", "https"):
        return False, "scheme_not_allowed"
    if parsed.port is not None and parsed.port not in (80, 443):
        return False, "port_not_allowed"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "empty_host"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "private_ip"
    except ValueError:
        pass  # hostname is a name, not a literal — fine
    if host in _BLOCKED_HOSTS:
        return False, "blocked_host"
    return True, ""


# Simple per-process token bucket. Single-threaded, so no locking needed.
_last_request_monotonic: float = 0.0


def _rate_limit_gate() -> None:
    """Enforce INSTITUTIONAL_RATE_PER_SEC pacing. No-op in public mode.

    Runs before every outbound HTTP request in institutional mode so
    that a single process cannot inadvertently hammer a publisher's
    servers beyond the configured rate.
    """
    global _last_request_monotonic
    if not _is_institutional():
        return
    min_interval = 1.0 / INSTITUTIONAL_RATE_PER_SEC
    now = time.monotonic()
    wait = _last_request_monotonic + min_interval - now
    if wait > 0:
        time.sleep(wait)
        now = time.monotonic()
    _last_request_monotonic = now


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

# Global output state (set by main()).
_format = "json"
_pretty = False
_stream = False
_request_id = ""
_started_monotonic = 0.0


def _now_ms() -> int:
    return int((time.monotonic() - _started_monotonic) * 1000)


def _log_text(msg: str) -> None:
    """Human-readable diagnostic → stderr only (used in text mode)."""
    print(msg, file=sys.stderr)


def _progress(event: str, **fields) -> None:
    """Progress event on stderr.

    JSON mode emits NDJSON so orchestrators can parse stderr for liveness.
    Text mode emits prose for humans.
    """
    if _format == "json":
        payload = {"event": event, "request_id": _request_id, "elapsed_ms": _now_ms(), **fields}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)
        return

    # Text mode — render a short human line.
    if event == "session":
        # Agent-only diagnostic; silent in human mode.
        return
    if event == "start":
        _log_text(f"==> {fields.get('doi', '?')}")
    elif event == "source_skip":
        _log_text(f"  [{fields.get('source', '?')}] skipped ({fields.get('reason', '?')})")
    elif event == "source_try":
        _log_text(f"  [{fields.get('source', '?')}] trying…")
    elif event == "source_hit":
        _log_text(f"  [{fields.get('source', '?')}] {fields.get('pdf_url', '?')}")
    elif event == "source_miss":
        _log_text(f"  [{fields.get('source', '?')}] no PDF")
    elif event == "download_error":
        reason = fields.get("reason", "?")
        status = fields.get("http_status")
        detail = fields.get("error")
        if status:
            _log_text(f"  download failed: {reason} (HTTP {status})")
        elif detail:
            _log_text(f"  download failed: {reason} ({detail})")
        else:
            _log_text(f"  download failed: {reason}")
    elif event == "download_ok":
        _log_text(f"  saved → {fields.get('file', '?')}")
    elif event == "download_skip":
        _log_text(f"  [skip-existing] {fields.get('file', '?')}")
    elif event == "dry_run":
        _log_text(f"  [dry-run] [{fields.get('source', '?')}] {fields.get('pdf_url', '?')} → {fields.get('file', '?')}")
    elif event == "not_found":
        _log_text(f"  no OA PDF found for {fields.get('doi', '?')}")
    else:
        # fall back
        _log_text(f"  [{event}] {fields}")


def _dump_json(obj: dict) -> str:
    if _pretty:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False)


def _emit(obj: dict) -> None:
    """Final result → stdout as JSON or human-readable text."""
    if _format == "json":
        print(_dump_json(obj))
    else:
        _emit_text(obj)


def _emit_ndjson(obj: dict) -> None:
    """Per-item streaming line on stdout (--stream mode)."""
    print(_dump_json(obj), flush=True)


def _emit_text(obj: dict) -> None:
    """Render a result envelope as human-readable text on stdout."""
    ok = obj.get("ok")
    if ok is False:
        err = obj.get("error", {})
        print(f"error: [{err.get('code', '?')}] {err.get('message', '?')}")
        return

    data = obj.get("data", {})
    results = data.get("results", [data] if "doi" in data else [])
    for r in results:
        if r.get("skipped"):
            status = "skipped"
        elif r.get("dry_run"):
            status = "dry-run"
        elif r.get("success"):
            status = "saved"
        else:
            status = "failed"
        src = r.get("source") or "?"
        doi = r.get("doi", "?")
        target = r.get("file") or r.get("pdf_url") or "?"
        print(f"[{src}] {doi} → {target}  ({status})")
    summary = data.get("summary")
    if summary:
        print(f"\n{summary['succeeded']}/{summary['total']} succeeded  ({summary.get('failed', 0)} failed)")
    nxt = data.get("next") or []
    if nxt:
        print("\nnext:")
        for hint in nxt:
            print(f"  {hint}")


def _meta(extra: dict | None = None) -> dict:
    m = {
        "request_id": _request_id,
        "latency_ms": _now_ms(),
        "schema_version": SCHEMA_VERSION,
        "cli_version": CLI_VERSION,
        "auth_mode": _auth_mode(),
    }
    if extra:
        m.update(extra)
    return m


def _envelope_ok(data: dict, *, ok=True, meta_extra: dict | None = None) -> dict:
    return {"ok": ok, "data": data, "meta": _meta(meta_extra)}


def _envelope_err(code: str, message: str, *, retryable: bool = False, **ctx) -> dict:
    e = {"code": code, "message": message, "retryable": retryable}
    e.update(ctx)
    return {"ok": False, "error": e, "meta": _meta()}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, *, accept: str = "application/json", timeout: int, user_agent: str | None = None) -> bytes:
    _rate_limit_gate()
    req = urllib.request.Request(url, headers={"User-Agent": user_agent or UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url: str, *, timeout: int):
    return json.loads(_get(url, timeout=timeout).decode("utf-8"))


def _scihub_rate_gate() -> None:
    """1 req/s pacing for Sci-Hub fetches, applied in every auth mode."""
    global _last_scihub_request_monotonic
    min_interval = 1.0 / SCIHUB_RATE_PER_SEC
    now = time.monotonic()
    wait = _last_scihub_request_monotonic + min_interval - now
    if wait > 0:
        time.sleep(wait)
        now = time.monotonic()
    _last_scihub_request_monotonic = now


def _is_allowed_host(url: str) -> bool:
    """Gatekeeper for any outbound PDF fetch.

    Only SSRF defense applies — private IPs, non-http(s) schemes, non-80/443
    ports, and cloud metadata hostnames are rejected. Everything else is
    allowed: the skill trusts URLs returned by the OA APIs it already called
    (Unpaywall, Semantic Scholar, bioRxiv, PMC), and the %PDF magic-byte +
    50 MB size checks in `_download` catch tampered responses.
    """
    ok, _reason = _is_safe_url(url)
    return ok


def _download(url: str, dest: Path, *, timeout: int) -> str | None:
    """Download a PDF. Returns None on success, or an error slug on failure."""
    if not _is_allowed_host(url):
        _progress("download_error", reason="host_not_allowed", url=url)
        return "host_not_allowed"

    def _finalize(data: bytes) -> str | None:
        """Validate (%PDF magic + size cap) and write. Shared by both the
        urllib path and the CloakBrowser fallback so safety checks live in one
        place regardless of how the bytes were obtained."""
        if len(data) > MAX_PDF_SIZE:
            _progress("download_error", reason="size_exceeded", bytes=len(data), limit=MAX_PDF_SIZE)
            return "size_exceeded"
        if not data[:5].startswith(b"%PDF"):
            _progress("download_error", reason="not_a_pdf")
            return "not_a_pdf"
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        except OSError as e:
            _progress("download_error", reason="io_error", error=str(e))
            return "io_error"
        return None

    def _try_cloak() -> bool:
        """Retry this URL through CloakBrowser. Returns True iff a valid PDF was
        fetched and written. No-op (False) when the operator hasn't opted in."""
        if not _is_cloak_enabled():
            return False
        data = _cloak_fetch_pdf(url, timeout=timeout)
        if not data or _finalize(data) is not None:
            return False
        _CLOAK_DOWNLOADS.add(url)
        _progress("download_cloak_ok", url=url, bytes=len(data))
        return True

    _rate_limit_gate()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DOWNLOAD_UA,
            "Accept": "application/pdf,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(MAX_PDF_SIZE + 1)
    except Exception as e:
        # Surface HTTP status when present (urllib.error.HTTPError carries .code).
        # Lets agents distinguish a 403 publisher block (try a VPN / different
        # source) from a generic timeout (just retry).
        http_status = getattr(e, "code", None)
        # Cloudflare answers non-browser clients with 403/429. If the operator
        # opted into the CloakBrowser fallback, retry through it before failing.
        if isinstance(http_status, int) and http_status in (403, 429) and _try_cloak():
            return None
        fields: dict = {"reason": "network_error", "error": str(e)}
        if isinstance(http_status, int):
            fields["http_status"] = http_status
        _progress("download_error", **fields)
        return "network_error"
    if len(data) > MAX_PDF_SIZE:
        _progress("download_error", reason="size_exceeded", bytes=len(data), limit=MAX_PDF_SIZE)
        return "size_exceeded"
    # A 200 whose body is not a PDF is often a Cloudflare "Just a moment..."
    # interstitial served in place of the file — worth a CloakBrowser retry.
    if not data[:5].startswith(b"%PDF"):
        if _try_cloak():
            return None
        _progress("download_error", reason="not_a_pdf")
        return "not_a_pdf"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    except OSError as e:
        _progress("download_error", reason="io_error", error=str(e))
        return "io_error"
    return None


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------


def _slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:n]


_JOURNAL_STOPWORDS = {"the", "of", "and", "for", "in", "on", "a", "an", "to", "&"}


def _journal_abbrev(name: str | None, max_len: int = 20) -> str:
    """ISO-style initials for 3+ words (PNAS, JACS, NEJM); CamelCase otherwise."""
    if not name:
        return ""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w and w.lower() not in _JOURNAL_STOPWORDS]
    if not words:
        return ""
    if len(words) >= 3:
        return "".join(w[0].upper() for w in words)[:max_len]
    return "".join(w[:1].upper() + w[1:] for w in words)[:max_len]


def _filename(meta: dict) -> str:
    author = _slug((meta.get("author") or "unknown").split()[-1], 20)
    year = str(meta.get("year") or "nd")
    journal = _journal_abbrev(meta.get("journal"))
    title = _slug(meta.get("title") or "paper", 40)
    parts = [author, year]
    if journal:
        parts.append(journal)
    parts.append(title)
    return "_".join(parts) + ".pdf"


# ---------------------------------------------------------------------------
# Source resolvers
# ---------------------------------------------------------------------------


def try_unpaywall(doi: str, *, timeout: int) -> tuple[str | None, dict]:
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
    try:
        d = _get_json(url, timeout=timeout)
    except Exception as e:
        _progress("source_miss", source="unpaywall", reason=str(e))
        return None, {}
    meta = {
        "title": d.get("title"),
        "year": d.get("year"),
        "author": (d.get("z_authors") or [{}])[0].get("family") if d.get("z_authors") else None,
        "journal": d.get("journal_name"),
    }
    loc = d.get("best_oa_location") or {}
    return loc.get("url_for_pdf"), meta


def try_semantic_scholar(doi: str, *, timeout: int) -> tuple[str | None, dict, dict]:
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}"
        "?fields=title,year,authors,openAccessPdf,externalIds,venue"
    )
    try:
        d = _get_json(url, timeout=timeout)
    except Exception as e:
        _progress("source_miss", source="semantic_scholar", reason=str(e))
        return None, {}, {}
    meta = {
        "title": d.get("title"),
        "year": d.get("year"),
        "author": (d.get("authors") or [{}])[0].get("name"),
        "journal": d.get("venue") or None,
    }
    pdf = (d.get("openAccessPdf") or {}).get("url")
    return pdf, meta, d.get("externalIds") or {}


def try_arxiv(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def try_arxiv_metadata(arxiv_id: str, *, timeout: int) -> dict:
    """Fetch title / year / first-author from arXiv's Atom API.

    Used when neither Unpaywall nor S2 returned metadata — typical for
    arXiv-only papers reached via the synthesized 10.48550/arXiv.<id> DOI
    form, which S2's by-DOI endpoint does not index. Without this, the
    deterministic filename falls back to encoding the DOI literal.

    Best-effort: returns an empty dict on any failure (offline, malformed
    response, paper not found).
    """
    bare = re.sub(r"v\d+$", "", arxiv_id)
    try:
        body = _get(
            f"http://export.arxiv.org/api/query?id_list={bare}",
            accept="application/atom+xml",
            timeout=timeout,
        )
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(body)
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        published = entry.findtext("atom:published", default="", namespaces=ns) or ""
        year = int(published[:4]) if published[:4].isdigit() else None
        author = entry.findtext("atom:author/atom:name", default=None, namespaces=ns)
        return {"title": title or None, "year": year, "author": author}
    except Exception:
        return {}


def try_pmc(pmcid: str) -> str:
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"


def try_europe_pmc(pmcid: str) -> str:
    """Europe PMC's render endpoint — mirror of PMC without PoW challenge.

    For articles flagged as hasPDF=Y in Europe PMC's catalog, this returns
    the paper's PDF directly. Useful as a fallback when NCBI PMC returns
    its cloudpmc-viewer JavaScript proof-of-work page.
    """
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    return f"https://europepmc.org/articles/{pmcid}?pdf=render"


_PMCID_URL_RE = re.compile(r"/pmc/articles/(PMC\d+)", re.IGNORECASE)


def _pmcid_from_url(url: str | None) -> str | None:
    """Extract a PMCID from a URL like https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123/...

    S2's openAccessPdf.url often points to a PMC article without also
    populating externalIds.PubMedCentral; parsing the URL recovers the id
    so we can still build Europe PMC / PMC fallback candidates.
    """
    if not url:
        return None
    m = _PMCID_URL_RE.search(url)
    return m.group(1).upper() if m else None


def try_biorxiv(doi: str, *, timeout: int) -> str | None:
    if not doi.startswith("10.1101/"):
        return None
    for server in ("biorxiv", "medrxiv"):
        try:
            d = _get_json(f"https://api.biorxiv.org/details/{server}/{doi}", timeout=timeout)
            coll = d.get("collection") or []
            if coll:
                latest = coll[-1]
                return f"https://www.{server}.org/content/10.1101/{latest['doi'].split('/')[-1]}v{latest.get('version', 1)}.full.pdf"
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Title → DOI resolvers (Crossref + Semantic Scholar fallback)
# ---------------------------------------------------------------------------

# Minimum title length we'll send to a resolver. Anything shorter is almost
# certainly a typo or one-word query that will return noise.
_MIN_TITLE_LEN = 6

# Heuristic confidence thresholds for Crossref's relevance score. The score
# is unitless and scales with title length, so these are calibrated to be
# permissive — anything obviously sloppy still produces a low_confidence
# flag rather than silently picking the wrong paper.
TITLE_SCORE_MIN = 40.0   # absolute floor; below this the top is suspect
TITLE_GAP_MIN = 3.0      # gap from top to runner-up; below this the top is ambiguous


def try_crossref_title(title: str, *, timeout: int) -> tuple[str | None, dict, list[dict]]:
    """Resolve a paper title to a DOI via Crossref.

    Crossref's relevance score is unitless and scales with title length, so we
    don't gate on an absolute threshold — we hand the top match plus the
    top 3 candidates back to the caller so an agent can sanity-check.

    Returns ``(top_doi, top_meta, candidates)``:
      - ``top_doi``: best-match DOI, or ``None`` if Crossref returned no items
      - ``top_meta``: ``{title, year, author, journal, score}`` for the top hit
      - ``candidates``: list of up to 3 candidate dicts in score order
    """
    q = title.strip()
    if len(q) < _MIN_TITLE_LEN:
        return None, {}, []
    # query.title outranks query.bibliographic for this use case: the input is
    # explicitly a paper title, and bibliographic mode also weights authors/year
    # equally — empirically that demoted the canonical AlphaFold paper below
    # secondary "Faculty Opinions recommendation of ..." entries that share
    # all the user's title tokens.
    params = {
        "query.title": q,
        "rows": "3",
        "select": "DOI,title,score,author,issued,container-title",
    }
    # Crossref's polite pool gives priority to requests that identify the
    # caller via mailto. We already pass UA but also include mailto when the
    # operator set UNPAYWALL_EMAIL, since the same address is theirs.
    if EMAIL:
        params["mailto"] = EMAIL
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    try:
        data = _get_json(url, timeout=timeout)
    except Exception as e:
        _progress("title_resolve_failed", reason=str(e))
        return None, {}, []

    items = ((data.get("message") or {}).get("items")) or []
    if not items:
        return None, {}, []

    candidates: list[dict] = []
    for it in items[:3]:
        title_list = it.get("title") or []
        author_list = it.get("author") or []
        first_author = ""
        if author_list:
            a0 = author_list[0]
            first_author = a0.get("family") or a0.get("name") or ""
        issued = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = issued[0] if issued and issued[0] else None
        cont = it.get("container-title") or []
        candidates.append({
            "doi": it.get("DOI"),
            "title": title_list[0] if title_list else None,
            "year": year,
            "author": first_author or None,
            "journal": cont[0] if cont else None,
            "score": it.get("score"),
        })

    top = candidates[0]
    top_meta = {k: v for k, v in top.items() if k != "doi"}
    return top.get("doi"), top_meta, candidates


def try_semantic_scholar_match(title: str, *, timeout: int) -> tuple[str | None, dict]:
    """Resolve a title to a DOI via Semantic Scholar's ``/paper/search/match``.

    S2's match endpoint returns at most one paper — its closest title in the
    corpus. Better than the relevance endpoint for our use case because we
    want exactness, not breadth. Critically, S2's corpus includes arXiv-only
    papers that never get a Crossref DOI; for those we synthesize the
    canonical arXiv DOI ``10.48550/arXiv.{id}`` so the downstream fetch
    chain treats the result uniformly.

    Returns ``(doi, meta)``. ``meta`` carries ``title``, ``year``, ``author``,
    ``journal``, ``paper_id``, and ``external_ids`` for caller transparency.
    """
    q = title.strip()
    if len(q) < _MIN_TITLE_LEN:
        return None, {}
    params = {
        "query": q,
        "fields": "title,authors,year,venue,externalIds",
    }
    url = "https://api.semanticscholar.org/graph/v1/paper/search/match?" + urllib.parse.urlencode(params)
    try:
        d = _get_json(url, timeout=timeout)
    except Exception as e:
        # 404 (no match) is the expected miss path here — the helper logs
        # the same way for any failure since the caller treats them as miss.
        _progress("title_resolver_miss", resolver="semantic_scholar", reason=str(e))
        return None, {}

    items = d.get("data") or []
    if not items:
        return None, {}
    top = items[0]
    ext = top.get("externalIds") or {}
    doi = ext.get("DOI")
    if not doi and ext.get("ArXiv"):
        # arXiv assigns DataCite DOIs as 10.48550/arXiv.<id> (since 2022;
        # for older preprints the DOI may not be registered, but the fetch
        # chain's arXiv source resolver doesn't need a registered DOI —
        # it builds the PDF URL from the arXiv id itself once S2 / Unpaywall
        # surface it via externalIds during the download phase).
        doi = f"10.48550/arXiv.{ext['ArXiv']}"
    if not doi:
        return None, {}
    authors = top.get("authors") or []
    return doi, {
        "doi": doi,
        "title": top.get("title"),
        "year": top.get("year"),
        "author": authors[0].get("name") if authors else None,
        "journal": top.get("venue") or None,
        "paper_id": top.get("paperId"),
        "external_ids": ext,
    }


# ---------------------------------------------------------------------------
# Publisher-direct fallback (institutional mode only)
# ---------------------------------------------------------------------------
# When the five OA sources all miss and the operator has opted into
# institutional mode, construct a publisher-side PDF URL by DOI prefix.
# The caller's IP / subscription cookies / EZproxy determine whether the
# publisher actually serves the PDF; unauthorized responses (401/403 or an
# HTML login page) fail the %PDF magic-byte check and the envelope surfaces
# download_not_a_pdf. SSRF + 50 MB + 1 req/s rate limit still apply.

_PUBLISHER_DIRECT_TEMPLATES: dict[str, tuple[str, str]] = {
    # DOI prefix -> (publisher label, URL template).
    # {doi} = full DOI; {suffix} = part after the prefix.
    "10.1038/": ("nature", "https://www.nature.com/articles/{suffix}.pdf"),
    "10.1126/": ("science", "https://www.science.org/doi/pdf/{doi}"),
    "10.1002/": ("wiley", "https://onlinelibrary.wiley.com/doi/pdf/{doi}"),
    "10.1007/": ("springer", "https://link.springer.com/content/pdf/{doi}.pdf"),
    "10.1021/": ("acs", "https://pubs.acs.org/doi/pdf/{doi}"),
    "10.1073/": ("pnas", "https://www.pnas.org/doi/pdf/{doi}"),
    "10.1056/": ("nejm", "https://www.nejm.org/doi/pdf/{doi}"),
    "10.1177/": ("sage", "https://journals.sagepub.com/doi/pdf/{doi}"),
    "10.1080/": ("tandf", "https://www.tandfonline.com/doi/pdf/{doi}"),
    # 10.1016/ (Elsevier / Cell Press) needs PII lookup — handled separately below.
    # 10.3390/ (MDPI) needs slug lookup — handled separately below; the
    # canonical www.mdpi.com PDF URL is gated by Akamai and 403s many
    # data-center / non-Western IPs even on OA papers, so we route via the
    # pub.mdpi-res.com CDN instead (see _mdpi_pdf_candidates).
}


# MDPI uses a short journal abbreviation in its DOI suffix (e.g. "app" for
# Applied Sciences) but a longer slug in the CDN URL (e.g. "applsci"). For
# many journals these are identical — ijms, molecules, sensors, cells,
# nutrients, cancers, foods, plants, etc. — and the fallback below covers
# them. Only journals whose slug differs from the short need to live here.
# Source: MDPI's own pub.mdpi-res.com URL convention, verified against
# representative DOIs from each listed journal.
_MDPI_SHORT_TO_SLUG: dict[str, str] = {
    "app": "applsci",
    "su": "sustainability",
    "ma": "materials",
    "en": "energies",
    "ani": "animals",
    "polym": "polymers",
    "antiox": "antioxidants",
    "math": "mathematics",
    "sym": "symmetry",
    "nano": "nanomaterials",
    "met": "metals",
    "catal": "catalysts",
    "cryst": "crystals",
    "atmos": "atmosphere",
    "info": "information",
    "md": "marinedrugs",
    "fi": "futureinternet",
    "f": "forests",
    "w": "water",
    "v": "viruses",
    "d": "diversity",
}

# DOI suffix shape for MDPI: <alpha-short><yy><iss><art>. Year and issue
# are 2 digits each; article fills the rest (1+ digits, padded to 5 in URL).
_MDPI_DOI_SUFFIX_RE = re.compile(r"^([a-z]+)(\d{2})(\d{2})(\d+)$")


def _mdpi_pdf_candidates(doi: str) -> list[str]:
    """CDN URL candidates for an MDPI DOI (10.3390/...).

    Returns 1-2 candidate URLs on pub.mdpi-res.com. Empty list if the DOI
    suffix doesn't match the expected MDPI shape (rare; older DOIs).

    Two URLs are returned when the short prefix has a known mapping AND
    differs from the short itself, so the download loop can fall back to
    the short-as-slug guess if the mapping is wrong or stale.
    """
    if not doi.startswith("10.3390/"):
        return []
    suffix = doi[len("10.3390/"):]
    m = _MDPI_DOI_SUFFIX_RE.match(suffix)
    if not m:
        return []
    short, vol, _iss, art = m.groups()
    art5 = art.zfill(5)
    slugs: list[str] = []
    mapped = _MDPI_SHORT_TO_SLUG.get(short)
    if mapped:
        slugs.append(mapped)
    if short not in slugs:
        slugs.append(short)
    return [
        f"https://pub.mdpi-res.com/{s}/{s}-{vol}-{art5}/article_deploy/{s}-{vol}-{art5}.pdf"
        for s in slugs
    ]


def _try_publisher_direct(doi: str, *, timeout: int) -> list[tuple[str, str]]:
    """Construct publisher-side direct PDF URL candidates by DOI prefix.

    Returns a list of (url, publisher_label) tuples in priority order, or
    an empty list if no template matches. Multiple candidates are returned
    when the publisher has more than one viable host (e.g. MDPI with both
    a mapped slug and a fallback slug). The actual HTTP fetch will reveal
    authorization failures via 401/403 or HTML responses.
    """
    if doi.startswith("10.1016/"):
        # Elsevier: resolve DOI -> PII via Crossref, then build sciencedirect URL.
        try:
            data = _get_json(f"https://api.crossref.org/works/{doi}", timeout=timeout)
        except Exception:
            return []
        ids = (data.get("message") or {}).get("alternative-id") or []
        pii = next(
            (i for i in ids if isinstance(i, str) and i.startswith("S") and len(i) >= 16),
            None,
        )
        if not pii:
            return []
        return [(f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft", "elsevier")]

    if doi.startswith("10.3390/"):
        return [(url, "mdpi") for url in _mdpi_pdf_candidates(doi)]

    for prefix, (label, tmpl) in _PUBLISHER_DIRECT_TEMPLATES.items():
        if doi.startswith(prefix):
            suffix = doi[len(prefix):]
            return [(tmpl.format(doi=doi, suffix=suffix), label)]

    return []


# ---------------------------------------------------------------------------
# Sci-Hub resolver
# ---------------------------------------------------------------------------

_SCIHUB_DISCOVERY_RE = re.compile(
    r'href=["\']https?://(?:www\.)?(sci-hub\.[a-z0-9.-]+)/?["\']',
    re.IGNORECASE,
)
# Phrases that signal the paper is genuinely not in Sci-Hub's corpus
# (vs. CAPTCHA / mirror outage). Lets us short-circuit instead of cycling
# through every mirror.
_SCIHUB_NOT_IN_CORPUS_PATTERNS = (
    re.compile(r"please\s+try\s+to\s+search\s+again\s+using\s+doi", re.IGNORECASE),
    re.compile(r"статья\s+не\s+найдена\s+в\s+базе", re.IGNORECASE),
    re.compile(r"article\s+not\s+found\s+in\s+(?:the\s+)?database", re.IGNORECASE),
)

# Lazily populated; reset only on process restart.
_scihub_discovered_cache: list[str] | None = None


def _is_scihub_enabled() -> bool:
    """True unless operator opted out via PAPER_FETCH_NO_SCIHUB=1."""
    return not os.environ.get("PAPER_FETCH_NO_SCIHUB")


def _scihub_mirrors() -> list[str]:
    """Mirror list for Sci-Hub, in priority order.

    PAPER_FETCH_SCIHUB_MIRRORS (comma-sep) overrides the built-in defaults.
    Discovery (re-scanning SCIHUB_DISCOVERY_URL) is invoked separately by
    `try_scihub` after the configured list is exhausted.
    """
    override = os.environ.get("PAPER_FETCH_SCIHUB_MIRRORS", "").strip()
    if override:
        return _parse_mirror_overrides(override)
    return list(SCIHUB_DEFAULT_MIRRORS)


def _parse_mirror_overrides(raw: str) -> list[str]:
    """Parse comma-separated mirror overrides into bare hostnames.

    Accepts forms like ``sci-hub.ru``, ``https://sci-hub.ru``, or
    ``sci-hub.ru/path/`` and returns just the hostname. Empty / unsafe
    entries (non-http(s) schemes, IP literals in private space, blocked
    hosts) are dropped — without this, a typo in the env var could route
    traffic at an attacker-controlled host.
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw_entry in raw.split(","):
        entry = raw_entry.strip().rstrip("/")
        if not entry:
            continue
        # Add a scheme so urlparse splits hostname correctly for bare
        # ``sci-hub.ru`` inputs (urlparse treats them as path-only).
        candidate = entry if "://" in entry else "https://" + entry
        try:
            parsed = urllib.parse.urlparse(candidate)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        host = (parsed.hostname or "").lower()
        if not host or host in seen:
            continue
        # Reuse the universal SSRF guard so an override of e.g.
        # ``localhost`` or a private IP literal is dropped.
        ok, _ = _is_safe_url(f"https://{host}/")
        if not ok:
            continue
        seen.add(host)
        out.append(host)
    return out


def _scihub_is_not_in_corpus(html: str) -> bool:
    """True if the HTML matches a known 'paper not in database' message.

    Lets the resolver skip the remaining mirrors when continuing is pointless
    (every mirror serves the same shared corpus). Distinct from CAPTCHA, which
    looks like an empty or challenge page — for that we still rotate mirrors.
    """
    return any(p.search(html) for p in _SCIHUB_NOT_IN_CORPUS_PATTERNS)


class _ScihubEmbedFinder(html.parser.HTMLParser):
    """Collect <iframe>/<embed> tags from Sci-Hub paper pages.

    Order-independent attribute capture — unlike the prior regex, an
    ``<iframe src="..." id="pdf">`` is treated identically to
    ``<iframe id="pdf" src="...">``. Records all candidates so the caller
    can prefer ``id="pdf"`` and fall back to any ``.pdf`` src.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # list of (id_attr_lower, src_attr) tuples, in document order.
        self.candidates: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._maybe_record(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        # Self-closing variant (<embed ... />) — still want to capture.
        self._maybe_record(tag, attrs)

    def _maybe_record(self, tag: str, attrs: list) -> None:
        if tag.lower() not in ("iframe", "embed"):
            return
        attr_map = {(k or "").lower(): (v or "") for k, v in attrs}
        src = attr_map.get("src", "").strip()
        if not src:
            return
        self.candidates.append((attr_map.get("id", "").lower(), src))


def _scihub_normalize_pdf_url(url: str, mirror_host: str | None) -> str | None:
    """Normalize a candidate src into an absolute https URL.

    Returns None if the URL is path-relative without a mirror context to
    anchor it against — the caller will fall back to another mirror.
    """
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        if not mirror_host:
            return None
        return f"https://{mirror_host}{url}"
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def _scihub_extract_iframe(html_text: str, mirror_host: str | None = None) -> str | None:
    """Extract the embedded PDF URL from a Sci-Hub paper page.

    Sci-Hub returns an HTML page with an <iframe src="...pdf"> (or sometimes
    an <embed src="...pdf">) pointing at the actual PDF on a CDN. Returns
    the absolute https:// URL, or None if no embed found (CAPTCHA, missing
    paper, or layout change). When `mirror_host` is provided, path-relative
    URLs (e.g. `/downloads/abc.pdf`) are resolved against it.
    """
    finder = _ScihubEmbedFinder()
    try:
        finder.feed(html_text)
    except Exception:
        # Malformed markup — bail to None so the caller rotates mirrors.
        return None

    # Prefer tags carrying id="pdf" regardless of attribute order in the source.
    # Within each tier, prefer entries whose src contains ".pdf".
    pdf_id = [(i, s) for i, s in finder.candidates if i == "pdf"]
    other = [(i, s) for i, s in finder.candidates if i != "pdf"]

    for tier in (pdf_id, other):
        # First pass within tier — strict ".pdf" hint.
        for _, src in tier:
            if ".pdf" not in src.lower():
                continue
            normalized = _scihub_normalize_pdf_url(src.strip(), mirror_host)
            if normalized:
                return normalized
        # Second pass within the id="pdf" tier — Sci-Hub sometimes serves
        # an obfuscated CDN URL without the ``.pdf`` extension. Trust the
        # explicit id anchor over filename hints.
        if tier is pdf_id:
            for _, src in tier:
                normalized = _scihub_normalize_pdf_url(src.strip(), mirror_host)
                if normalized:
                    return normalized
    return None


def _scihub_discover_mirrors(*, timeout: int) -> list[str]:
    """Scrape SCIHUB_DISCOVERY_URL for current mirror list. Cached per process."""
    global _scihub_discovered_cache
    if _scihub_discovered_cache is not None:
        return _scihub_discovered_cache
    try:
        html = _get(SCIHUB_DISCOVERY_URL, accept="text/html", timeout=timeout).decode("utf-8", "replace")
    except Exception as e:
        _progress("scihub_discover_failed", reason=str(e))
        _scihub_discovered_cache = []
        return []
    found: list[str] = []
    seen: set[str] = set()
    for m in _SCIHUB_DISCOVERY_RE.finditer(html):
        host = m.group(1).lower()
        if host in seen:
            continue
        seen.add(host)
        found.append(host)
    _scihub_discovered_cache = found
    if found:
        _progress("scihub_discover_ok", mirrors=found)
    return found


def try_scihub(doi: str, *, timeout: int) -> tuple[str, str] | None:
    """Resolve a DOI to a PDF URL via Sci-Hub mirrors.

    Tries the configured mirror list in order; on exhaustion, performs a
    one-shot discovery scan of SCIHUB_DISCOVERY_URL and tries any new
    mirrors. Returns `(pdf_url, mirror_host)` on hit so the caller can
    surface which mirror succeeded; returns None if every mirror missed.

    Short-circuits when a mirror explicitly reports the paper is not in
    Sci-Hub's database — every mirror shares one corpus, so cycling further
    just wastes round trips.
    """
    tried: set[str] = set()
    mirrors = _scihub_mirrors()

    def _try_one(host: str) -> tuple[str | None, str]:
        """Returns (pdf_url, status). status is 'pdf' | 'no_pdf' | 'not_in_corpus' | 'error'."""
        url = f"https://{host}/{doi}"
        if not _is_allowed_host(url):
            return None, "error"
        _scihub_rate_gate()
        try:
            html = _get(
                url,
                accept="text/html,application/xhtml+xml",
                timeout=timeout,
                user_agent=SCIHUB_UA,
            ).decode("utf-8", "replace")
        except Exception:
            return None, "error"
        pdf = _scihub_extract_iframe(html, mirror_host=host)
        if pdf:
            return pdf, "pdf"
        if _scihub_is_not_in_corpus(html):
            return None, "not_in_corpus"
        return None, "no_pdf"

    def _walk(hosts: list[str]) -> tuple[tuple[str, str] | None, bool]:
        """Returns ((pdf_url, mirror) | None, gave_up). gave_up=True on confirmed not-in-corpus."""
        for host in hosts:
            if host in tried:
                continue
            tried.add(host)
            pdf, status = _try_one(host)
            if pdf:
                return (pdf, host), False
            if status == "not_in_corpus":
                _progress("source_miss", source="scihub", reason="not_in_corpus", mirror=host)
                return None, True
        return None, False

    hit, gave_up = _walk(mirrors)
    if hit or gave_up:
        return hit

    fresh = _scihub_discover_mirrors(timeout=timeout)
    hit, _ = _walk(fresh)
    return hit


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------


def _download_failure(
    doi: str,
    meta: dict,
    sources_tried: list[str],
    errors: list[dict],
    *,
    candidates: list[tuple[str, str]] | None = None,
) -> dict:
    """Build a per-item download failure result. `errors` must be non-empty."""
    last = errors[-1]
    retryable = last["reason"] in ("network_error", "size_exceeded", "io_error")
    code = f"download_{last['reason']}"
    err_obj = {
        "code": code,
        "message": (
            f"All {len(errors)} candidate(s) failed; last error from {last['source']}: {last['reason']}"
            if len(errors) > 1
            else f"Download failed from {last['source']}: {last['reason']}"
        ),
        "retryable": retryable,
    }
    if retryable and code in RETRY_AFTER_HOURS:
        err_obj["retry_after_hours"] = RETRY_AFTER_HOURS[code]
    out = {
        "doi": doi,
        "success": False,
        "source": last["source"],
        "pdf_url": last["url"],
        "file": None,
        "meta": meta or {},
        "sources_tried": sources_tried,
        "download_attempts": errors,
        "error": err_obj,
    }
    if candidates:
        out["candidates"] = [{"source": s, "url": u} for s, u in candidates]
    return out


def fetch(
    doi: str,
    out_dir: Path,
    *,
    dry_run: bool,
    overwrite: bool,
    timeout: int,
) -> dict:
    """Resolve and optionally download a single DOI.

    Returns a structured per-item result (not an envelope). Guaranteed keys:
      doi, success, source, pdf_url, file, meta, sources_tried, error?
    """
    doi = doi.strip()
    # str.removeprefix is Python 3.9+; README advertises 3.8+.
    for _prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi.org/", "dx.doi.org/", "doi:"):
        if doi.startswith(_prefix):
            doi = doi[len(_prefix):]
            break
    # Reject anything that doesn't match the documented DOI pattern before
    # we start hitting external APIs. Saves a round-trip on typos and keeps
    # the runtime contract aligned with the schema's `params.doi.pattern`.
    if not _DOI_RE.match(doi):
        return {
            "doi": doi,
            "success": False,
            "source": None,
            "pdf_url": None,
            "file": None,
            "meta": {},
            "sources_tried": [],
            "error": {
                "code": "validation_error",
                "message": f"Not a valid DOI: {doi!r} (expected pattern {DOI_PATTERN})",
                "retryable": False,
            },
        }
    _progress("start", doi=doi)

    sources_tried: list[str] = []
    meta: dict = {}
    download_errors: list[dict] = []

    # Fatal download errors that abort the fallback loop. Only host-independent
    # local failures qualify (e.g., disk write failed). ``size_exceeded`` is per-URL,
    # so a bloated copy from one source should not prevent trying a smaller copy from another.
    FATAL_DL_ERRORS = ("io_error",)

    def _merge_meta(extra: dict) -> list[str]:
        added: list[str] = []
        for k, v in (extra or {}).items():
            if v and not meta.get(k):
                meta[k] = v
                added.append(k)
        return added

    # --- Semantic Scholar is queried lazily (cached). Provides metadata,
    # its own PDF URL, and externalIds (PMCID, arXiv id) used to construct
    # additional candidates. Only called when needed so that a successful
    # Unpaywall hit with complete metadata short-circuits the flow. ---
    _s2_cache: dict | None = None

    def _get_s2() -> tuple[str | None, dict, dict]:
        nonlocal _s2_cache
        if _s2_cache is not None:
            return _s2_cache["pdf"], _s2_cache["meta"], _s2_cache["ext"]
        if "semantic_scholar" not in sources_tried:
            sources_tried.append("semantic_scholar")
        _progress("source_try", doi=doi, source="semantic_scholar")
        pdf, s2_meta, ext = try_semantic_scholar(doi, timeout=timeout)
        _s2_cache = {"pdf": pdf, "meta": s2_meta, "ext": ext}
        return pdf, s2_meta, ext

    # --- Unpaywall first (often the quickest OA link) ---
    up_url: str | None = None
    if EMAIL:
        _progress("source_try", doi=doi, source="unpaywall")
        sources_tried.append("unpaywall")
        up_url, up_meta = try_unpaywall(doi, timeout=timeout)
        _merge_meta(up_meta)
        if up_url:
            _progress("source_hit", doi=doi, source="unpaywall", pdf_url=up_url)
            # Enrich metadata from S2 if Unpaywall didn't give us author/title
            # (prevents unknown_<year>_paper.pdf filenames).
            if not meta.get("author") or not meta.get("title"):
                _, s2_meta, _ = _get_s2()
                added = _merge_meta(s2_meta)
                if added:
                    _progress("source_enrich", doi=doi, source="semantic_scholar", fields=added)
                elif not s2_meta:
                    _progress("source_enrich_failed", doi=doi, source="semantic_scholar", reason="s2_unavailable")
        else:
            _progress("source_miss", doi=doi, source="unpaywall")
    else:
        _progress("source_skip", doi=doi, source="unpaywall", reason="UNPAYWALL_EMAIL not set")

    # --- Compute destination filename from merged meta ---
    fname = _filename(meta or {"title": doi})
    dest = out_dir / fname

    # Per-source diagnostics (mirror that succeeded, publisher label, etc.)
    # surfaced in the result envelope under `source_detail`. Keyed by source label.
    source_details: dict[str, dict] = {}

    def _success(src: str, url: str, extra: dict | None = None) -> dict:
        out = {
            "doi": doi,
            "success": True,
            "source": src,
            "pdf_url": url,
            "file": str(dest),
            "meta": meta or {},
            "sources_tried": sources_tried,
        }
        if src in source_details:
            out["source_detail"] = source_details[src]
        if url in _CLOAK_DOWNLOADS:
            out["via"] = "cloak"
        if extra:
            out.update(extra)
        return out

    # --- Try Unpaywall's PDF first (if we have one) ---
    if up_url:
        if dry_run:
            _progress("dry_run", doi=doi, source="unpaywall", pdf_url=up_url, file=str(dest))
            return _success("unpaywall", up_url, {"dry_run": True})
        if dest.exists() and not overwrite:
            _progress("download_skip", doi=doi, file=str(dest))
            return _success("unpaywall", up_url, {"skipped": True, "skip_reason": "file_exists"})
        dl_err = _download(up_url, dest, timeout=timeout)
        if dl_err is None:
            _progress("download_ok", doi=doi, file=str(dest), source="unpaywall")
            return _success("unpaywall", up_url)
        download_errors.append({"source": "unpaywall", "url": up_url, "reason": dl_err})
        if dl_err in FATAL_DL_ERRORS:
            return _download_failure(doi, meta, sources_tried, download_errors)
        # Non-fatal download failure — fall through to additional sources as fallback.

    # --- Force S2 lookup (for fallback PDF URL + externalIds) ---
    s2_pdf, s2_meta, ext = _get_s2()
    _merge_meta(s2_meta)

    # If the Unpaywall path ran the file-exists check and skipped, we already returned above.
    # For the remaining sources, check destination once more in case enrichment changed the name.
    fname = _filename(meta or {"title": doi})
    dest = out_dir / fname

    # --- Build fallback candidate list (deduped by URL) ---
    # Any URL already attempted via Unpaywall is skipped — no point retrying
    # the exact same URL from a different source label.
    attempted_urls: set[str] = {e["url"] for e in download_errors}
    candidates: list[tuple[str, str]] = []

    def _add(src: str, url: str) -> None:
        if url in attempted_urls:
            return
        if any(u == url for _, u in candidates):
            return
        attempted_urls.add(url)
        candidates.append((src, url))

    if s2_pdf:
        _progress("source_hit", doi=doi, source="semantic_scholar", pdf_url=s2_pdf)
        _add("semantic_scholar", s2_pdf)
    elif not up_url:
        _progress("source_miss", doi=doi, source="semantic_scholar")

    # Synthesized arXiv DOIs (10.48550/arXiv.<id>) encode the arxiv id directly.
    # S2 doesn't index by this DOI form, so a S2-by-DOI lookup returns 404 and
    # externalIds stays empty — recover the id from the DOI literal so the
    # arxiv source still gets tried.
    if not ext.get("ArXiv") and doi.lower().startswith("10.48550/arxiv."):
        ext["ArXiv"] = doi[len("10.48550/arxiv."):]
        # Backfill metadata from arXiv's API only when our other sources
        # missed — keeps the filename meaningful (Vaswani_2017_… instead of
        # unknown_nd_10_48550_arXiv_…) without burning a round-trip when
        # Unpaywall or S2 already gave us a title.
        if not meta.get("title"):
            ax_meta = try_arxiv_metadata(ext["ArXiv"], timeout=timeout)
            if ax_meta:
                added = _merge_meta(ax_meta)
                if added:
                    _progress("source_enrich", doi=doi, source="arxiv", fields=added)
                    fname = _filename(meta or {"title": doi})
                    dest = out_dir / fname
            else:
                _progress("source_enrich_failed", doi=doi, source="arxiv")

    if ext.get("ArXiv"):
        sources_tried.append("arxiv")
        arxiv_url = try_arxiv(ext["ArXiv"])
        _progress("source_hit", doi=doi, source="arxiv", pdf_url=arxiv_url)
        _add("arxiv", arxiv_url)

    # Recover PMCID from any PMC-style URL we've seen (S2 openAccessPdf often
    # points to a PMC landing page without populating externalIds.PubMedCentral).
    if not ext.get("PubMedCentral"):
        for url_src in (up_url, s2_pdf):
            pmcid_from_url = _pmcid_from_url(url_src)
            if pmcid_from_url:
                ext["PubMedCentral"] = pmcid_from_url
                break

    if ext.get("PubMedCentral"):
        # Europe PMC tried first — bypasses NCBI PMC's cloudpmc-viewer JS challenge.
        sources_tried.append("europe_pmc")
        epmc_url = try_europe_pmc(ext["PubMedCentral"])
        _progress("source_hit", doi=doi, source="europe_pmc", pdf_url=epmc_url)
        _add("europe_pmc", epmc_url)
        sources_tried.append("pmc")
        pmc_url = try_pmc(ext["PubMedCentral"])
        _progress("source_hit", doi=doi, source="pmc", pdf_url=pmc_url)
        _add("pmc", pmc_url)

    if doi.startswith("10.1101/"):
        _progress("source_try", doi=doi, source="biorxiv")
        sources_tried.append("biorxiv")
        bx_url = try_biorxiv(doi, timeout=timeout)
        if bx_url:
            _progress("source_hit", doi=doi, source="biorxiv", pdf_url=bx_url)
            _add("biorxiv", bx_url)
        else:
            _progress("source_miss", doi=doi, source="biorxiv")

    # --- Publisher-direct fallback (institutional mode only) ---
    # Runs only when the operator has opted into institutional mode. The
    # caller's IP / cookies / EZproxy are what actually authorize the fetch.
    if _is_institutional():
        _progress("source_try", doi=doi, source="publisher_direct")
        pub_candidates = _try_publisher_direct(doi, timeout=timeout)
        if pub_candidates:
            sources_tried.append("publisher_direct")
            for pub_url, pub_label in pub_candidates:
                _progress("source_hit", doi=doi, source="publisher_direct", pdf_url=pub_url, publisher=pub_label)
                _add("publisher_direct", pub_url)
        else:
            _progress("source_miss", doi=doi, source="publisher_direct", reason="no_template_for_doi_prefix")

    # --- Sci-Hub fallback (last resort) ---
    # Mirror list comes from PAPER_FETCH_SCIHUB_MIRRORS or the built-in defaults;
    # exhaustion triggers a one-shot scan of SCIHUB_DISCOVERY_URL for fresh mirrors.
    # Disabled with PAPER_FETCH_NO_SCIHUB=1.
    def _try_scihub_resolve() -> str | None:
        if not _is_scihub_enabled():
            return None
        if "scihub" in sources_tried:
            return None
        _progress("source_try", doi=doi, source="scihub")
        sources_tried.append("scihub")
        sh_hit = try_scihub(doi, timeout=timeout)
        if not sh_hit:
            _progress("source_miss", doi=doi, source="scihub")
            return None
        sh_url, sh_mirror = sh_hit
        source_details["scihub"] = {"mirror": sh_mirror}
        _progress("source_hit", doi=doi, source="scihub", pdf_url=sh_url, mirror=sh_mirror)
        return sh_url

    # First Sci-Hub pass: runs when no OA candidates resolved at all (regardless
    # of whether Unpaywall produced a non-fatal download error). The download
    # loop below treats Sci-Hub like any other candidate.
    if not candidates:
        sh_url = _try_scihub_resolve()
        if sh_url:
            _add("scihub", sh_url)

    # --- Exhausted all sources with no candidates and no prior attempts → not_found ---
    if not candidates and not download_errors:
        _progress("not_found", doi=doi)
        err = {
            "code": "not_found",
            "message": "No open-access PDF found",
            "retryable": True,
            "retry_after_hours": RETRY_AFTER_HOURS["not_found"],
            "reason": "OA availability changes over time; retry after embargo lifts or preprint appears",
        }
        # In public mode, suggest institutional access as a next avenue.
        # Silent in institutional mode — if they're already opted in and the
        # paper still wasn't found, the subscription doesn't cover it.
        if not _is_institutional():
            err["suggest_institutional"] = True
            err["hint"] = (
                "If your institution has a subscription to this paper, "
                "set PAPER_FETCH_INSTITUTIONAL=1 and run from on-campus or VPN."
            )
        return {
            "doi": doi,
            "success": False,
            "source": None,
            "pdf_url": None,
            "file": None,
            "meta": meta or {},
            "sources_tried": sources_tried,
            "error": err,
        }

    # --- Dry-run preview of first fallback candidate (only reached when Unpaywall didn't hit) ---
    if dry_run and candidates:
        src0, url0 = candidates[0]
        _progress("dry_run", doi=doi, source=src0, pdf_url=url0, file=str(dest))
        return _success(src0, url0, {"dry_run": True, "candidates": [{"source": s, "url": u} for s, u in candidates]})

    # --- File-exists skip on first candidate (non-Unpaywall path) ---
    if candidates and dest.exists() and not overwrite:
        src0, url0 = candidates[0]
        _progress("download_skip", doi=doi, file=str(dest))
        return _success(src0, url0, {"skipped": True, "skip_reason": "file_exists"})

    # --- Fallback download loop ---
    fatal_seen = False
    for cand_src, cand_url in candidates:
        dl_err = _download(cand_url, dest, timeout=timeout)
        if dl_err is None:
            _progress("download_ok", doi=doi, file=str(dest), source=cand_src)
            return _success(cand_src, cand_url, {"candidates": [{"source": s, "url": u} for s, u in candidates]})
        download_errors.append({"source": cand_src, "url": cand_url, "reason": dl_err})
        if dl_err in FATAL_DL_ERRORS:
            fatal_seen = True
            break

    # Second Sci-Hub pass: every OA candidate produced a URL but none of them
    # could actually be downloaded (e.g. CAPTCHA, broken link, blocked host).
    # Try Sci-Hub now if it hasn't already been attempted, and if no fatal
    # local error (io_error) terminated the loop.
    if not fatal_seen and "scihub" not in sources_tried:
        sh_url = _try_scihub_resolve()
        if sh_url and sh_url not in attempted_urls:
            attempted_urls.add(sh_url)
            candidates.append(("scihub", sh_url))
            dl_err = _download(sh_url, dest, timeout=timeout)
            if dl_err is None:
                _progress("download_ok", doi=doi, file=str(dest), source="scihub")
                return _success("scihub", sh_url, {"candidates": [{"source": s, "url": u} for s, u in candidates]})
            download_errors.append({"source": "scihub", "url": sh_url, "reason": dl_err})

    return _download_failure(doi, meta, sources_tried, download_errors, candidates=candidates)


# ---------------------------------------------------------------------------
# Idempotency sidecar
# ---------------------------------------------------------------------------


def _idem_path(out_dir: Path, key: str) -> Path:
    safe = _slug(key, 80) or "default"
    return out_dir / ".paper-fetch-idem" / f"{safe}.json"


def _idem_load(out_dir: Path, key: str) -> dict | None:
    p = _idem_path(out_dir, key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _idem_store(out_dir: Path, key: str, envelope: dict) -> None:
    p = _idem_path(out_dir, key)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # best-effort only


# ---------------------------------------------------------------------------
# Schema subcommand
# ---------------------------------------------------------------------------


def build_schema() -> dict:
    return {
        "command": "paper-fetch",
        "cli_version": CLI_VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": "Fetch PDFs by DOI via Unpaywall, Semantic Scholar, arXiv, Europe PMC, PMC, and bioRxiv/medRxiv. In institutional mode (PAPER_FETCH_INSTITUTIONAL=1), also attempts a publisher-direct fetch (publisher_direct source) using the caller's own subscription IP / cookies / EZproxy. As a last resort, falls back to Sci-Hub mirrors (scihub source); disable with PAPER_FETCH_NO_SCIHUB=1. On download failure (host_not_allowed, not_a_pdf, network_error), automatically falls back to the next candidate source.",
        "subcommands": {
            "schema": "Print this schema as JSON and exit (no network).",
        },
        "params": {
            "doi": {
                "type": "string",
                "required": False,
                "description": "DOI to fetch (positional). Use '-' to read DOIs line-by-line from stdin.",
                "pattern": DOI_PATTERN,
                "example": "10.1038/s41586-020-2649-2",
            },
            "title": {
                "type": "string",
                "required": False,
                "description": "Paper title; resolved to a DOI via Crossref before download. Mutually exclusive with positional DOI / --batch. The resolved DOI, top match, and up to 3 candidates are surfaced under meta.title_resolution.",
                "example": "Highly accurate protein structure prediction with AlphaFold",
            },
            "batch": {
                "type": "path",
                "required": False,
                "description": "File with one DOI per line for bulk download. Use '-' to read from stdin.",
            },
            "out": {
                "type": "path",
                "required": False,
                "default": "pdfs",
                "description": "Output directory.",
            },
            "dry_run": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Resolve sources without downloading; preview the PDF URL and destination path.",
            },
            "format": {
                "type": "enum",
                "values": ["json", "text"],
                "required": False,
                "default": "auto (json when stdout not a TTY, text otherwise)",
                "description": "Output format. json for agents, text for humans.",
            },
            "pretty": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Pretty-print JSON output with 2-space indentation.",
            },
            "stream": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Emit one NDJSON result per line on stdout as each DOI resolves, then a final summary line.",
            },
            "overwrite": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Re-download PDFs even when the destination file already exists.",
            },
            "idempotency_key": {
                "type": "string",
                "required": False,
                "description": "Stable key for safe retries. Re-running with the same key returns the original envelope from a sidecar in <out>/.paper-fetch-idem/.",
            },
            "timeout": {
                "type": "integer",
                "required": False,
                "default": DEFAULT_TIMEOUT,
                "description": "HTTP timeout in seconds per request.",
            },
        },
        "exit_codes": {
            "0": "success (all DOIs resolved / previewed)",
            "1": "unresolved (some DOIs had no OA copy; no transport failure)",
            "2": "reserved for auth errors (currently unused)",
            "3": "validation error (bad arguments, missing input)",
            "4": "transport error (network / download / IO failure; retryable class)",
        },
        "error_codes": {
            "validation_error": {"retryable": False, "message": "Bad arguments or empty input"},
            "not_found": {"retryable": True, "retry_after_hours": RETRY_AFTER_HOURS["not_found"], "message": "No OA PDF found anywhere; OA availability changes over time"},
            "title_resolve_failed": {"retryable": False, "message": "Crossref returned no items for the given title; provide a DOI directly or refine the title"},
            "download_network_error": {"retryable": True, "retry_after_hours": RETRY_AFTER_HOURS["download_network_error"], "message": "Network failure during download"},
            "download_not_a_pdf": {"retryable": False, "message": "Response was not a PDF (HTML landing page)"},
            "download_host_not_allowed": {"retryable": False, "message": "PDF URL failed SSRF safety check (private IP, non-http(s) scheme, non-80/443 port, or blocked metadata host)"},
            "download_size_exceeded": {"retryable": True, "retry_after_hours": RETRY_AFTER_HOURS["download_size_exceeded"], "message": f"Response exceeded {MAX_PDF_SIZE // (1024*1024)} MB limit"},
            "download_io_error": {"retryable": True, "retry_after_hours": RETRY_AFTER_HOURS["download_io_error"], "message": "Local filesystem write failed"},
            "internal_error": {"retryable": False, "message": "Unexpected error"},
        },
        "envelope": {
            "success": {"ok": True, "data": {"results": [], "summary": {}, "next": []}, "meta": {}},
            "partial": {"ok": "partial", "data": {"results": [], "summary": {}, "next": []}, "meta": {}},
            "failure": {"ok": False, "error": {"code": "", "message": "", "retryable": False}, "meta": {}},
        },
        "result_fields": {
            "source_detail": "Optional per-source diagnostics (e.g. {'mirror': 'sci-hub.ru'} when source='scihub'). Present only when the resolving source has additional context worth surfacing for orchestrator routing.",
            "via": "Optional. Set to 'cloak' when the PDF was fetched through the CloakBrowser fallback (a Cloudflare-blocked URL retried via stealth Chromium). Absent for ordinary downloads. Requires PAPER_FETCH_CLOAK.",
        },
        "deprecations": [],
        "meta_fields": {
            "request_id": "Unique per-invocation id; correlates stderr progress events with the stdout envelope.",
            "latency_ms": "Wall-clock time from process start to this emit.",
            "schema_version": "Version of this schema contract; bumped on any additive or breaking change.",
            "cli_version": "Version of the paper-fetch binary that produced the envelope.",
            "auth_mode": "Either 'public' (OA sources, no client rate limit) or 'institutional' (user opted in via PAPER_FETCH_INSTITUTIONAL=1; 1 req/s rate limit to protect the operator's IP from publisher-side throttling).",
            "sources_tried": "Union of sources consulted across all DOIs in this run.",
            "title_resolution": "Present only when --title was used. Includes: query, resolver (the resolver whose match was used: 'crossref' or 'semantic_scholar'), resolvers_tried (ordered list of every resolver consulted), resolved_doi, resolved_title, match_score (Crossref relevance score; absent for S2 matches), candidates (top-3 from the winning resolver), low_confidence (true if the chosen DOI failed the score/gap heuristics), low_confidence_reason ('score_below_threshold' / 'ambiguous_runner_up' / 'no_match'), fallback_reason (why Crossref's match was rejected when S2 was used), and crossref_candidates (top-3 Crossref hits when the S2 fallback won, for cross-resolver inspection). Agents should sanity-check the top match — especially when low_confidence is true.",
        },
        "env": {
            "UNPAYWALL_EMAIL": "Optional. Contact email for Unpaywall API. If unset, Unpaywall is skipped.",
            "PAPER_FETCH_INSTITUTIONAL": "Optional. Set to any value to opt into institutional mode: activates a 1 req/s rate limiter and enables the publisher-direct fallback. Intended for callers whose IP / cookies / EZproxy already grant subscription access. SSRF defense applies in every mode.",
            "PAPER_FETCH_NO_SCIHUB": "Optional. Set to any value to disable the Sci-Hub fallback (enabled by default).",
            "PAPER_FETCH_SCIHUB_MIRRORS": "Optional. Comma-separated list of Sci-Hub mirror hostnames to try, in priority order, overriding the built-in defaults (e.g. 'sci-hub.ru,sci-hub.st,sci-hub.su').",
            "PAPER_FETCH_CLOAK": "Optional. Set to any value to enable the CloakBrowser fallback: when a download is blocked by Cloudflare (HTTP 403/429 or a non-PDF interstitial), the URL is retried through a stealth Chromium that can pass the JS challenge. Off by default; requires the cloak_pdf.py companion and a cloakbrowser-importable Python (see CLOAKBROWSER_PYTHON). Bytes are re-validated through the same %PDF + 50 MB checks. Operator action only — the agent cannot opt in.",
            "CLOAKBROWSER_PYTHON": "Optional. Path to a Python interpreter that can import cloakbrowser, used by the PAPER_FETCH_CLOAK fallback. If unset, falls back to ~/github/CloakBrowser/.venv/bin/python then the current interpreter.",
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EPILOG = """\
exit codes:
  0  all DOIs resolved successfully
  1  unresolved (some DOIs had no OA copy; no transport failure)
  3  validation error (bad arguments)
  4  transport error (network / download / IO failure; retryable class)

subcommands:
  schema                 print the machine-readable CLI schema and exit (no network)

stdin:
  paper-fetch -          read a single DOI from stdin
  paper-fetch --batch -  read DOIs line-by-line from stdin

output:
  stdout emits one JSON object per invocation (NDJSON with --stream).
  stderr emits NDJSON progress events when --format json, prose when --format text.
  stdout format auto-detects TTY: json when piped/captured, text in a terminal.

examples:
  %(prog)s 10.1038/s41586-020-2649-2
  %(prog)s 10.1038/s41586-020-2649-2 --dry-run
  %(prog)s --batch dois.txt --out ./papers --format text
  echo 10.1038/s41586-020-2649-2 | %(prog)s --batch -
  %(prog)s schema
"""


def _load_dois_from_args(args) -> list[str] | dict:
    """Parse DOI input from args. Returns list of DOIs or an error envelope dict.

    Title resolution (``--title``) is handled separately by ``_resolve_title``
    in main(); this loader sees only the resolved DOI by then.
    """
    inputs = [bool(args.batch), bool(args.doi), bool(getattr(args, "title", None))]
    if sum(inputs) > 1:
        return _envelope_err(
            "validation_error",
            "Pass exactly one of: positional DOI, --batch FILE, or --title TITLE.",
        )
    if args.batch:
        if args.batch == "-":
            text = sys.stdin.read()
            dois = [l.strip() for l in text.splitlines() if l.strip()]
        else:
            batch_path = Path(args.batch)
            if not batch_path.exists():
                return _envelope_err(
                    "validation_error",
                    f"Batch file not found: {args.batch}",
                    field="batch",
                )
            dois = [l.strip() for l in batch_path.read_text().splitlines() if l.strip()]
    elif args.doi == "-":
        text = sys.stdin.read()
        dois = [l.strip() for l in text.splitlines() if l.strip()]
    elif args.doi:
        dois = [args.doi]
    else:
        return _envelope_err("validation_error", "Provide a DOI, --title, or --batch file")

    if not dois:
        return _envelope_err("validation_error", "No DOIs found in input")
    return dois


def _classify_low_confidence(score: float | None, gap: float | None) -> str | None:
    """Identify why a Crossref top match should be treated as low-confidence.

    Returns a single short reason string, or None if both heuristics pass.
    Order matters: ``score_below_threshold`` is the more diagnostic signal,
    so report that first when both fire.
    """
    if score is not None and score < TITLE_SCORE_MIN:
        return "score_below_threshold"
    if gap is not None and gap < TITLE_GAP_MIN:
        return "ambiguous_runner_up"
    return None


def _resolve_title(title: str, *, timeout: int) -> tuple[str | None, dict]:
    """Resolve a title to a DOI via Crossref → Semantic Scholar fallback chain.

    Always populates a ``resolution_meta`` dict (at least ``query`` and
    ``resolvers_tried``) so callers can surface it in the envelope's meta slot.
    """
    _progress("title_resolve_try", query=title)
    resolvers_tried: list[str] = []

    # Pass 1 — Crossref. Confident hit short-circuits the chain.
    resolvers_tried.append("crossref")
    cr_doi, cr_top, cr_candidates = try_crossref_title(title, timeout=timeout)
    cr_score = cr_top.get("score") if cr_top else None
    cr_gap: float | None = None
    if len(cr_candidates) >= 2:
        s0 = cr_candidates[0].get("score")
        s1 = cr_candidates[1].get("score")
        if isinstance(s0, (int, float)) and isinstance(s1, (int, float)):
            cr_gap = float(s0) - float(s1)
    cr_low_reason = _classify_low_confidence(cr_score, cr_gap) if cr_doi else "no_match"

    if cr_doi and cr_low_reason is None:
        _progress(
            "title_resolve_hit",
            query=title,
            resolver="crossref",
            doi=cr_doi,
            title=cr_top.get("title"),
            score=cr_score,
        )
        return cr_doi, {
            "query": title,
            "resolver": "crossref",
            "resolvers_tried": resolvers_tried,
            "resolved_doi": cr_doi,
            "resolved_title": cr_top.get("title"),
            "match_score": cr_score,
            "candidates": cr_candidates,
            "low_confidence": False,
        }

    # Pass 2 — Semantic Scholar match endpoint. Covers arXiv-only papers
    # (no Crossref DOI) and rescues low-confidence Crossref matches.
    _progress(
        "title_resolver_try",
        query=title,
        resolver="semantic_scholar",
        reason="crossref_" + cr_low_reason if cr_low_reason else "crossref_no_match",
    )
    resolvers_tried.append("semantic_scholar")
    s2_doi, s2_meta = try_semantic_scholar_match(title, timeout=timeout)
    if s2_doi:
        _progress(
            "title_resolve_hit",
            query=title,
            resolver="semantic_scholar",
            doi=s2_doi,
            title=s2_meta.get("title"),
        )
        out: dict = {
            "query": title,
            "resolver": "semantic_scholar",
            "resolvers_tried": resolvers_tried,
            "resolved_doi": s2_doi,
            "resolved_title": s2_meta.get("title"),
            "candidates": [s2_meta],
            "low_confidence": False,
            "fallback_reason": cr_low_reason,
        }
        # Preserve the Crossref candidate list so an agent can compare what
        # each resolver thought was the top hit (helps when the two disagree).
        if cr_candidates:
            out["crossref_candidates"] = cr_candidates
        return s2_doi, out

    # Pass 3 — every resolver missed. If Crossref had *any* candidate, return
    # it with a low_confidence flag so the agent can either (a) proceed with
    # caution or (b) bail out via the dry-run preview.
    if cr_doi:
        _progress(
            "title_resolve_hit",
            query=title,
            resolver="crossref",
            doi=cr_doi,
            title=cr_top.get("title"),
            score=cr_score,
            low_confidence=True,
            reason=cr_low_reason,
        )
        return cr_doi, {
            "query": title,
            "resolver": "crossref",
            "resolvers_tried": resolvers_tried,
            "resolved_doi": cr_doi,
            "resolved_title": cr_top.get("title"),
            "match_score": cr_score,
            "candidates": cr_candidates,
            "low_confidence": True,
            "low_confidence_reason": cr_low_reason,
        }

    _progress("title_resolve_miss", query=title, resolvers_tried=resolvers_tried)
    return None, {
        "query": title,
        "resolvers_tried": resolvers_tried,
        "candidates": [],
    }


def _default_format() -> str:
    try:
        return "json" if not sys.stdout.isatty() else "text"
    except Exception:
        return "json"


def _decide_exit(results: list[dict]) -> int:
    """Pick the most descriptive exit code from per-item outcomes."""
    any_validation = False
    any_transport = False
    any_unresolved = False
    any_failure = False
    for r in results:
        if r.get("success"):
            continue
        any_failure = True
        err = r.get("error") or {}
        code = err.get("code", "")
        if code == "validation_error":
            any_validation = True
        elif code == "not_found":
            any_unresolved = True
        elif code.startswith("download_"):
            any_transport = True
        else:
            any_unresolved = True
    if not any_failure:
        return EXIT_SUCCESS
    # Validation errors win over transport/unresolved: a malformed DOI is a
    # caller bug, not a transient network issue.
    if any_validation and not (any_transport or any_unresolved):
        return EXIT_VALIDATION
    if any_transport:
        return EXIT_TRANSPORT
    return EXIT_UNRESOLVED


def _next_hints(results: list[dict], args) -> list[str]:
    """Suggest follow-up commands for the failed subset.

    Hints are intended for an agent or human to copy-paste and run, so all
    user-controlled values (DOIs, --out path) are shell-quoted to prevent
    a maliciously crafted DOI from injecting commands.
    """
    failed = [r["doi"] for r in results if not r.get("success")]
    if not failed:
        return []
    out = shlex.quote(args.out)
    if len(failed) == 1:
        cmd = f"paper-fetch {shlex.quote(failed[0])} --out {out}"
        if args.dry_run:
            cmd += " --dry-run"
        return [cmd]
    # Multiple failures — feed them via stdin so each DOI is delimited by a
    # real newline rather than interpolated into the shell command.
    payload = shlex.quote("\n".join(failed) + "\n")
    cmd = f"printf %s {payload} | paper-fetch --batch - --out {out}"
    if args.dry_run:
        cmd += " --dry-run"
    return [cmd]


def main():
    global _format, _pretty, _stream, _request_id, _started_monotonic

    _started_monotonic = time.monotonic()
    _request_id = f"req_{uuid.uuid4().hex[:12]}"

    # Schema subcommand — handle before the main parser so we don't require a DOI.
    if len(sys.argv) >= 2 and sys.argv[1] == "schema":
        # Honor --pretty / --format if they follow.
        rest = sys.argv[2:]
        _pretty = "--pretty" in rest
        if "--format" in rest:
            i = rest.index("--format")
            if i + 1 < len(rest) and rest[i + 1] in ("json", "text"):
                _format = rest[i + 1]
            else:
                _format = _default_format()
        else:
            _format = _default_format()
        schema = build_schema()
        _emit(_envelope_ok(schema))
        sys.exit(EXIT_SUCCESS)

    ap = argparse.ArgumentParser(
        prog="paper-fetch",
        description="Fetch legal open-access PDFs by DOI via Unpaywall, Semantic Scholar, arXiv, PMC, and bioRxiv/medRxiv.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("doi", nargs="?", help="DOI to fetch (e.g. 10.1038/s41586-020-2649-2). Use '-' to read from stdin.")
    ap.add_argument("--title", metavar="TITLE", help="paper title; resolved to a DOI via Crossref before download. Mutually exclusive with positional DOI / --batch.")
    ap.add_argument("--batch", metavar="FILE", help="file with one DOI per line for bulk download. Use '-' to read from stdin.")
    ap.add_argument("--out", default="pdfs", metavar="DIR", help="output directory (default: pdfs)")
    ap.add_argument("--dry-run", action="store_true", help="resolve sources without downloading; preview the PDF URL and filename")
    ap.add_argument(
        "--format",
        choices=["json", "text"],
        default=None,
        dest="fmt",
        help="output format. json for agents, text for humans. Default: json when stdout is not a TTY, text otherwise.",
    )
    ap.add_argument("--pretty", action="store_true", help="pretty-print JSON output (2-space indent)")
    ap.add_argument("--stream", action="store_true", help="emit one NDJSON result per line on stdout as each DOI resolves (batch mode)")
    ap.add_argument("--overwrite", action="store_true", help="re-download even if the destination file already exists")
    ap.add_argument("--idempotency-key", metavar="KEY", default=None, help="safe-retry key; re-running with the same key replays the original envelope from <out>/.paper-fetch-idem/")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="SECONDS", help=f"HTTP timeout in seconds per request (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--version", action="version", version=f"paper-fetch {CLI_VERSION} (schema {SCHEMA_VERSION})")
    args = ap.parse_args()

    _format = args.fmt or _default_format()
    _pretty = args.pretty
    _stream = args.stream

    # One-time session header — lets agents detect schema drift on the very
    # first stderr line, before any per-DOI work or network I/O.
    _progress("session", cli_version=CLI_VERSION, schema_version=SCHEMA_VERSION)

    if not EMAIL:
        _progress("source_skip", source="unpaywall", reason="UNPAYWALL_EMAIL not set (top-level notice)")

    out_dir = Path(args.out)

    # Title resolution — runs before DOI loading so the rest of the pipeline
    # treats the resolved DOI as if it had been passed directly.
    title_resolution: dict | None = None
    if args.title:
        # Reject simultaneous title + DOI / --batch up front rather than later.
        if args.doi or args.batch:
            _emit(_envelope_err(
                "validation_error",
                "--title cannot be combined with a positional DOI or --batch.",
            ))
            sys.exit(EXIT_VALIDATION)
        resolved_doi, title_resolution = _resolve_title(args.title, timeout=args.timeout)
        if not resolved_doi:
            _emit(_envelope_err(
                "title_resolve_failed",
                f"Crossref returned no items for title: {args.title!r}",
                retryable=False,
                title_resolution=title_resolution,
            ))
            sys.exit(EXIT_UNRESOLVED)
        # Inject the resolved DOI as the positional argument so downstream
        # logic (DOI validation, fetch loop, idempotency replay) is identical.
        # Clear args.title so the mutual-exclusion guard in _load_dois_from_args
        # doesn't trip on the (now consumed) title.
        args.doi = resolved_doi
        args.title = None

    loaded = _load_dois_from_args(args)
    if isinstance(loaded, dict):
        _emit(loaded)
        sys.exit(EXIT_VALIDATION)
    dois: list[str] = loaded

    # Idempotency replay — before any network I/O.
    if args.idempotency_key:
        cached = _idem_load(out_dir, args.idempotency_key)
        if cached is not None:
            # Re-stamp meta so the replayed envelope still reports current latency / request id.
            cached_meta = cached.get("meta", {}) or {}
            cached_meta.update({
                "request_id": _request_id,
                "latency_ms": _now_ms(),
                "replayed_from_idempotency_key": args.idempotency_key,
            })
            cached["meta"] = cached_meta
            _emit(cached)
            # Exit code mirrors the cached envelope's outcome.
            if cached.get("ok") is True:
                sys.exit(EXIT_SUCCESS)
            if cached.get("ok") == "partial":
                sys.exit(_decide_exit(cached.get("data", {}).get("results", [])))
            sys.exit(EXIT_VALIDATION if cached.get("error", {}).get("code") == "validation_error" else EXIT_UNRESOLVED)

    results: list[dict] = []
    for d in dois:
        r = fetch(
            d,
            out_dir,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            timeout=args.timeout,
        )
        results.append(r)
        if _stream and _format == "json":
            _emit_ndjson({"ok": bool(r.get("success")), "data": r, "meta": _meta()})

    succeeded = sum(1 for r in results if r.get("success"))
    total = len(results)
    failed = total - succeeded

    if succeeded == total:
        ok_flag: bool | str = True
    elif succeeded == 0:
        ok_flag = False
    else:
        ok_flag = "partial"

    data = {
        "results": results,
        "summary": {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
        },
        "next": _next_hints(results, args),
    }

    sources_tried_union = sorted({s for r in results for s in r.get("sources_tried", [])})
    meta_extra = {"sources_tried": sources_tried_union}
    if not EMAIL:
        meta_extra["unpaywall_skipped"] = True
    if title_resolution is not None:
        meta_extra["title_resolution"] = title_resolution

    if ok_flag is False:
        # Total failure of a single-DOI call — downgrade to an error envelope
        # when the single result has an error with a code, so agents see
        # {ok:false, error:{...}} for the simple case.
        if total == 1 and results[0].get("error"):
            err = results[0]["error"]
            envelope = _envelope_err(
                err.get("code", "internal_error"),
                err.get("message", "failed"),
                retryable=err.get("retryable", False),
                **{k: v for k, v in err.items() if k not in ("code", "message", "retryable")},
                doi=results[0]["doi"],
                sources_tried=results[0].get("sources_tried", []),
            )
            envelope["meta"].update(meta_extra)
        else:
            envelope = _envelope_ok(data, ok=False, meta_extra=meta_extra)
    else:
        envelope = _envelope_ok(data, ok=ok_flag, meta_extra=meta_extra)

    # Stream mode already emitted per-item lines; final envelope still goes out as a summary.
    if _stream and _format == "json":
        print(_dump_json({"summary": data["summary"], "meta": envelope["meta"], "next": data["next"], "ok": ok_flag}), flush=True)
    else:
        _emit(envelope)

    # Store idempotency sidecar on completion (even for partial — replay returns same shape).
    if args.idempotency_key:
        _idem_store(out_dir, args.idempotency_key, envelope)

    sys.exit(_decide_exit(results))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        _emit(_envelope_err("internal_error", str(e)))
        sys.exit(EXIT_TRANSPORT)
