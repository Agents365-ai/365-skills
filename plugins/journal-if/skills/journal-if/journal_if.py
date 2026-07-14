#!/usr/bin/env python3
"""Journal Impact Factor lookup tool.

Sources (in priority order):
1. Local CSV cache (curated dataset, bundled + auto-updated)
2. OpenAlex API fallback (computes approximate 2-year IF from citation counts)
3. Per-query cache for web lookups (avoids repeat API calls)

Run `journal_if --help` for usage and `journal_if schema` for the full machine-readable
command contract. Stdout is stable JSON when not attached to a TTY.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLI_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"

# Exit codes
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_VALIDATION = 2
EXIT_NOT_FOUND = 3

# Rate limiting for OpenAlex (polite default: 10 req/sec)
_OPENALEX_GAP = 0.11

_last_openalex_time = 0.0

CACHE_DIR = Path(__file__).parent / "cache"
DATA_DIR = Path(__file__).parent / "data"
BUNDLED_CSV = DATA_DIR / "journals_if.csv"

# Upstream CSV — a curated dataset maintained in the repo
UPSTREAM_BASE = "https://raw.githubusercontent.com/Agents365-ai/journal-if/main/skills/journal-if/data"
UPSTREAM_FILES = ["journals_if.csv"]

_quiet = False


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _resolve_cache_dir() -> Path:
    env = os.environ.get("JOURNALIF_CACHE_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return CACHE_DIR


def ensure_cache(target_dir: Path | None = None) -> None:
    """Ensure upstream CSV files are present. Downloads from GitHub if missing."""
    dest = target_dir or CACHE_DIR
    dest.mkdir(parents=True, exist_ok=True)
    for fname in UPSTREAM_FILES:
        fpath = dest / fname
        if fpath.exists():
            continue
        url = f"{UPSTREAM_BASE}/{fname}"
        if not _quiet:
            print(f"  Downloading {fname}...", file=sys.stderr)
        try:
            _fetch(url, timeout=30, dest=fpath)
        except (HTTPError, URLError, TimeoutError) as e:
            if not _quiet:
                print(f"  Warning: failed to download {fname}: {e}", file=sys.stderr)


def _csv_rows(path: Path) -> list[dict]:
    """Parse a CSV of journal IF data. Columns: name, impact_factor, year, category, issn."""
    text = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        name = (r.get("name") or r.get("journal") or "").strip()
        if not name or name.startswith("#"):
            continue
        try:
            if_val = float(r.get("impact_factor", r.get("if", "")))
        except (ValueError, TypeError):
            if_val = None
        rows.append({
            "name": name,
            "impact_factor": if_val,
            "year": r.get("year", "").strip() or None,
            "category": r.get("category", "").strip() or None,
            "issn": r.get("issn", "").strip() or None,
        })
    return rows


def load_cache() -> dict[str, dict]:
    """Load journal IF data from bundled CSV + cached CSVs into a lookup dict."""
    index: dict[str, dict] = {}
    paths = [BUNDLED_CSV, CACHE_DIR / "journals_if.csv"]
    seen = set()
    for p in paths:
        if not p.exists():
            continue
        for row in _csv_rows(p):
            key = _normalize(row["name"])
            if key not in seen:
                seen.add(key)
                index[key] = row
    return index


_cache: dict[str, dict] | None = None


def _get_cache() -> dict[str, dict]:
    global _cache
    if _cache is None:
        ensure_cache()
        _cache = load_cache()
    return _cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"^the\s+", "", s)
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)
    # Remove trailing punctuation
    s = s.rstrip(".,;:")
    return s


def _fetch(url: str, timeout: int = 15, dest: Path | None = None) -> str:
    req = Request(url, headers={"User-Agent": f"journal-if/{CLI_VERSION} (mailto:niehu@outlook.com)"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    if dest:
        dest.write_text(data, encoding="utf-8")
    return data


def _fetch_json(url: str, timeout: int = 15) -> Any:
    return json.loads(_fetch(url, timeout))


# ---------------------------------------------------------------------------
# OpenAlex fallback
# ---------------------------------------------------------------------------

def _lookup_openalex(name: str) -> dict | None:
    """Compute approximate 2-year IF from OpenAlex Source API.

    OpenAlex doesn't provide JCR IF directly, but we can compute a 2-year
    citation-based metric from `counts_by_year` and `works_count`. This is an
    approximation and will differ from the official JCR number.

    Returns None on definitive miss, raises UpstreamUnavailable on transient failure.
    """
    global _last_openalex_time
    elapsed = time.time() - _last_openalex_time
    if elapsed < _OPENALEX_GAP:
        time.sleep(_OPENALEX_GAP - elapsed)

    encoded = quote(name)
    url = f"https://api.openalex.org/sources?search={encoded}&per_page=3"
    try:
        _last_openalex_time = time.time()
        data = _fetch_json(url)
    except (HTTPError, URLError, TimeoutError) as e:
        raise UpstreamUnavailable([{"source": "OpenAlex", "error": str(e)}]) from e

    results = data.get("results", [])
    if not results:
        return None

    # Pick the best match: prefer exact display_name match, then first result
    best = None
    nl = name.lower().strip()
    for r in results:
        dn = (r.get("display_name") or "").lower().strip()
        if dn == nl:
            best = r
            break
    if best is None:
        best = results[0]

    # Compute approximate 2-year IF from most recent complete years
    cby = best.get("counts_by_year", [])
    wc = best.get("works_count", 0)

    # Sort by year descending
    cby_sorted = sorted(cby, key=lambda x: x.get("year", 0), reverse=True)
    if len(cby_sorted) >= 2:
        y0_cites = cby_sorted[0].get("cited_by_count", 0)
        y1_cites = cby_sorted[1].get("cited_by_count", 0)
        # Works published in those 2 years
        y0_works = cby_sorted[0].get("works_count", 0)
        y1_works = cby_sorted[1].get("works_count", 0)
        total_works = y0_works + y1_works
        if total_works > 0:
            approx_if = round((y0_cites + y1_cites) / total_works, 3)
        else:
            approx_if = None
        year = cby_sorted[0].get("year")
    else:
        approx_if = None
        year = cby_sorted[0].get("year") if cby_sorted else None

    return {
        "name": best.get("display_name", name),
        "impact_factor": approx_if,
        "year": year,
        "source": "OpenAlex (approximate 2-year IF — not official JCR)",
        "issn": best.get("issn_l"),
        "openalex_id": best.get("id"),
    }


class UpstreamUnavailable(Exception):
    def __init__(self, sources: list[dict]):
        self.sources = sources
        super().__init__("; ".join(f"{s['source']}: {s['error']}" for s in sources))


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def lookup_journal(name: str, allow_web: bool = True) -> dict | None:
    """Look up IF for a journal. Cascade: local cache -> OpenAlex.

    Returns None only when all sources gave a definitive miss.
    Raises UpstreamUnavailable when upstream failed transiently with no cache hit.
    """
    cache = _get_cache()
    key = _normalize(name)
    if key in cache:
        result = dict(cache[key])
        result["source"] = "local cache"
        result["query"] = name
        return result

    # Fuzzy match tier 1: AND-term match (most precise, e.g. "J Biol Chem" → "Journal of Biological Chemistry")
    terms = key.split()
    if len(terms) >= 2:
        best = None
        best_score = float("inf")
        for ck, cv in cache.items():
            if all(t in ck for t in terms):
                score = len(ck)  # prefer shorter name (tighter match)
                if score < best_score:
                    best_score = score
                    best = cv
        if best:
            result = dict(best)
            result["source"] = "local cache (fuzzy)"
            result["query"] = name
            return result

    # Fuzzy match tier 2: substring match (broader fallback)
    candidates = []
    for ck, cv in cache.items():
        if key in ck or ck in key:
            score = len(key) if key in ck else len(ck)
            candidates.append((score, ck, cv))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        _, _, cv = candidates[0]
        result = dict(cv)
        result["source"] = "local cache (fuzzy)"
        result["query"] = name
        return result

    if not allow_web:
        return None

    try:
        oa = _lookup_openalex(name)
    except UpstreamUnavailable:
        raise

    if oa:
        return oa

    return None


def fuzzy_search(query: str) -> list[dict]:
    """Search local cache for matching journals."""
    cache = _get_cache()
    nq = _normalize(query)
    terms = nq.split()
    results = []
    for ck, cv in cache.items():
        if all(t in ck for t in terms):
            r = dict(cv)
            r["source"] = "local cache"
            results.append(r)

    # Exact prefix matches first, then by name length
    results.sort(key=lambda r: (not _normalize(r["name"]).startswith(nq), len(r["name"])))
    return results


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

def batch_lookup(filepath: str) -> dict:
    path = Path(filepath)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    succeeded = []
    failed = []
    for line in lines:
        q = line.strip()
        if not q or q.startswith("#"):
            continue
        try:
            result = lookup_journal(q)
        except UpstreamUnavailable as e:
            failed.append({
                "query": q,
                "error": {
                    "code": "upstream_unavailable",
                    "message": f"Upstream failed for '{q}'",
                    "retryable": True,
                    "sources": e.sources,
                },
            })
            continue
        if result:
            succeeded.append(result)
        else:
            failed.append({
                "query": q,
                "error": {
                    "code": "not_found",
                    "message": f"No IF data found for '{q}'",
                    "retryable": False,
                },
            })
    return {"succeeded": succeeded, "failed": failed}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "cli_version": CLI_VERSION,
    "global_flags": [
        {"name": "--format", "type": "string", "choices": ["json", "table", "human", "auto"],
         "default": "auto", "description": "Output format. 'auto' picks json when stdout is not a TTY."},
        {"name": "--json", "type": "bool", "description": "Alias for --format json."},
        {"name": "--quiet", "type": "bool", "default": False, "description": "Suppress stderr progress."},
        {"name": "--offline", "type": "bool", "default": False, "description": "Local cache only; skip OpenAlex."},
    ],
    "exit_codes": {
        "0": "success (including partial success)",
        "1": "runtime / upstream error",
        "2": "validation / bad input",
        "3": "not found",
    },
    "error_codes": {
        "not_found": {"retryable": False, "exit_code": 3, "description": "No source matched the query"},
        "upstream_unavailable": {"retryable": True, "exit_code": 1, "description": "Upstream API failed transiently"},
        "file_not_found": {"retryable": False, "exit_code": 2, "description": "Input file does not exist"},
        "validation_error": {"retryable": False, "exit_code": 2, "description": "Bad argument or flag combination"},
        "runtime_error": {"retryable": True, "exit_code": 1, "description": "Unexpected internal error"},
    },
    "envelope": {
        "success": '{"ok": true, "data": ..., "meta": {...}}',
        "partial": '{"ok": "partial", "data": {"succeeded": [...], "failed": [...]}, "meta": {...}}',
        "error": '{"ok": false, "error": {"code": "...", "message": "...", "retryable": bool}, "meta": {...}}',
    },
    "commands": {
        "lookup": {
            "summary": "Look up impact factor for a journal",
            "mutates": "read",
            "params": [
                {"name": "query", "positional": True, "nargs": "+", "type": "string",
                 "required": True, "description": "Journal name"},
            ],
        },
        "batch": {
            "summary": "Look up IF for a list of journals (one per line)",
            "mutates": "read",
            "params": [
                {"name": "path", "positional": True, "type": "string", "required": True,
                 "description": "Path to text file, one journal name per line"},
            ],
        },
        "search": {
            "summary": "Fuzzy-search the local cache",
            "mutates": "read",
            "params": [
                {"name": "query", "positional": True, "nargs": "+", "type": "string",
                 "required": True, "description": "Search terms"},
                {"name": "--limit", "type": "integer", "default": 15},
                {"name": "--offset", "type": "integer", "default": 0},
            ],
        },
        "cache": {
            "summary": "Inspect or refresh the local cache",
            "mutates": "destructive",
            "params": [
                {"name": "action", "positional": True, "type": "string", "required": True,
                 "choices": ["status", "update"],
                 "description": "status: inspect cache; update: re-download upstream CSV"},
            ],
        },
        "schema": {
            "summary": "Print the command schema (JSON)",
            "mutates": "read",
            "params": [
                {"name": "target", "positional": True, "type": "string",
                 "required": False, "default": None,
                 "description": "Optional command name; omit to list all"},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------

def _meta(**extra) -> dict:
    m: dict = {"schema_version": SCHEMA_VERSION, "cli_version": CLI_VERSION}
    m.update(extra)
    return m


def envelope_ok(data: Any, **extra) -> dict:
    env: dict = {"ok": True, "data": data}
    env.update(extra)
    env["meta"] = _meta(**env.get("meta", {}))
    return env


def envelope_error(code: str, message: str, retryable: bool = False, **fields) -> dict:
    err = {"code": code, "message": message, "retryable": retryable}
    err.update(fields)
    return {"ok": False, "error": err, "meta": _meta()}


def envelope_partial(succeeded: list, failed: list) -> dict:
    return {
        "ok": "partial" if failed else True,
        "data": {"succeeded": succeeded, "failed": failed},
        "meta": _meta(),
    }


def exit_code_for(env: dict) -> int:
    if env["ok"] in (True, "partial"):
        return EXIT_OK
    err = env.get("error") or {}
    code = err.get("code", "")
    if code == "not_found":
        return EXIT_NOT_FOUND
    if code in ("validation_error", "file_not_found"):
        return EXIT_VALIDATION
    return EXIT_RUNTIME


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _json_dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _format_human_result(data: dict) -> str:
    lines = [
        f"  Journal:       {data.get('name', data.get('query', 'N/A'))}",
        f"  Impact Factor: {data.get('impact_factor', 'N/A')}",
    ]
    if data.get("year"):
        lines.append(f"  IF Year:       {data['year']}")
    if data.get("category"):
        lines.append(f"  Category:      {data['category']}")
    if data.get("issn"):
        lines.append(f"  ISSN:          {data['issn']}")
    if data.get("source"):
        lines.append(f"  Source:        {data['source']}")
    return "\n".join(lines)


def _format_table(rows: list[dict]) -> str:
    if not rows:
        return "No results."
    headers = ["Journal", "IF", "Year", "Category"]
    body = [
        (
            r.get("name", r.get("query", "")),
            str(r.get("impact_factor", "N/A")),
            str(r.get("year", "")),
            r.get("category", ""),
        )
        for r in rows
    ]
    widths = [
        max(len(h), max((len(str(r[i])) for r in body), default=0))
        for i, h in enumerate(headers)
    ]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    hdr = "|" + "|".join(f" {h:<{widths[i]}} " for i, h in enumerate(headers)) + "|"
    lines = [sep, hdr, sep]
    for row in body:
        lines.append("|" + "|".join(f" {str(row[i]):<{widths[i]}} " for i in range(4)) + "|")
    lines.append(sep)
    return "\n".join(lines)


def resolve_format(args: argparse.Namespace) -> str:
    if getattr(args, "json", False):
        return "json"
    fmt = getattr(args, "format", "auto")
    if fmt and fmt != "auto":
        return fmt
    if not sys.stdout.isatty():
        return "json"
    return "human"


def emit(env: dict, fmt: str, command: str) -> None:
    if fmt == "json":
        print(_json_dump(env))
        return

    if env["ok"] is False:
        err = env["error"]
        print(f"Error [{err['code']}]: {err['message']}", file=sys.stderr)
        return

    if env["ok"] == "partial":
        succeeded = env["data"]["succeeded"]
        failed = env["data"]["failed"]
        if succeeded:
            print(_format_table(succeeded))
        print(f"\n{len(failed)} failed:", file=sys.stderr)
        for f in failed:
            print(f"  - {f['query']}: {f['error']['message']}", file=sys.stderr)
        return

    data = env["data"]

    if command in ("lookup",):
        print(_format_human_result(data))
        return

    if command == "search":
        print(_format_table(data))
        return

    if command == "batch":
        print(_format_table(data.get("succeeded", [])))
        return

    if command == "cache":
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"  {k}: {v}")
        return

    if command == "schema":
        print(_json_dump(data))
        return

    print(_json_dump(data))


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _validate_input_file(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return envelope_error("file_not_found", f"file not found: {path}", retryable=False)
    if not p.is_file():
        return envelope_error("validation_error", f"not a regular file: {path}", retryable=False)
    return None


def handle_lookup(args) -> dict:
    query = " ".join(args.query)
    allow_web = not getattr(args, "offline", False)
    t0 = time.time()
    try:
        result = lookup_journal(query, allow_web=allow_web)
    except UpstreamUnavailable as e:
        latency = int((time.time() - t0) * 1000)
        return envelope_error(
            "upstream_unavailable",
            f"Upstream APIs failed for '{query}'; retry later or use --offline for cache-only",
            retryable=True,
            query=query,
            sources=e.sources,
            meta={"latency_ms": latency},
        )
    latency = int((time.time() - t0) * 1000)
    if result is None:
        return envelope_error(
            "not_found",
            f"No impact factor data found for '{query}'",
            retryable=False,
            query=query,
            meta={"latency_ms": latency},
        )
    return envelope_ok(result, meta={"latency_ms": latency})


def handle_search(args) -> dict:
    query = " ".join(args.query)
    if args.limit < 0 or args.offset < 0:
        return envelope_error("validation_error", "--limit and --offset must be >= 0", retryable=False)
    t0 = time.time()
    all_results = fuzzy_search(query)
    latency = int((time.time() - t0) * 1000)
    total = len(all_results)
    start = args.offset
    end = start + args.limit
    page_items = all_results[start:end]
    return envelope_ok(
        page_items,
        meta={"latency_ms": latency},
        page={"offset": start, "limit": args.limit, "returned": len(page_items),
              "total": total, "has_more": end < total, "next_offset": end if end < total else None},
    )


def handle_batch(args) -> dict:
    err = _validate_input_file(args.path)
    if err:
        return err
    result = batch_lookup(args.path)
    return envelope_partial(result["succeeded"], result["failed"])


def handle_cache(args) -> dict:
    global _cache
    action = args.action

    if action == "status":
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        bundled_exists = BUNDLED_CSV.exists()
        cached_files = [f.name for f in CACHE_DIR.iterdir() if f.suffix == ".csv"] if CACHE_DIR.exists() else []
        try:
            idx = load_cache()
            total = len(idx)
        except Exception:
            total = None
        return envelope_ok({
            "cache_dir": str(CACHE_DIR),
            "bundled_csv": str(BUNDLED_CSV),
            "bundled_exists": bundled_exists,
            "cached_files": cached_files,
            "total_journals": total,
        })

    if action == "update":
        _cache = None
        ensure_cache()
        idx = load_cache()
        _cache = idx
        return envelope_ok({
            "action": "update",
            "total_journals": len(idx),
        })

    return envelope_error("validation_error", f"unknown cache action: {action}", retryable=False)


def handle_schema(args) -> dict:
    target = args.target
    if target is None:
        return envelope_ok(SCHEMA)
    cmd = SCHEMA["commands"].get(target)
    if cmd is None:
        return envelope_error(
            "not_found", f"No such command: {target}",
            retryable=False,
            known_commands=sorted(SCHEMA["commands"].keys()),
        )
    return envelope_ok({"command": target, **cmd})


HANDLERS = {
    "lookup": handle_lookup,
    "batch": handle_batch,
    "search": handle_search,
    "cache": handle_cache,
    "schema": handle_schema,
}


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

def _add_param(sp: argparse.ArgumentParser, param: dict) -> None:
    name = param["name"]
    desc = param.get("description", "")
    if param.get("positional"):
        kwargs: dict = {"help": desc}
        if "nargs" in param:
            kwargs["nargs"] = param["nargs"]
        if "choices" in param:
            kwargs["choices"] = param["choices"]
        sp.add_argument(name, **kwargs)
        return
    kwargs = {"help": desc}
    ptype = param.get("type", "string")
    if ptype == "bool":
        kwargs["action"] = "store_true"
    elif ptype == "integer":
        kwargs["type"] = int
        kwargs["default"] = param.get("default")
    else:
        kwargs["default"] = param.get("default")
    if "choices" in param:
        kwargs["choices"] = param["choices"]
    sp.add_argument(name, **kwargs)


def _make_common_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=["json", "table", "human", "auto"],
                        default=argparse.SUPPRESS, help="Output format")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="Alias for --format json")
    common.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS,
                        help="Suppress stderr progress")
    common.add_argument("--offline", action="store_true", default=argparse.SUPPRESS,
                        help="Local cache only; skip OpenAlex API calls")
    return common


def build_parser() -> argparse.ArgumentParser:
    common = _make_common_parser()
    p = argparse.ArgumentParser(
        prog="journal_if",
        parents=[common],
        description="Journal Impact Factor lookup — local cache + OpenAlex fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"journal_if {CLI_VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    for cmd_name, cmd_spec in SCHEMA["commands"].items():
        sp = sub.add_parser(cmd_name, parents=[common], help=cmd_spec["summary"],
                            formatter_class=argparse.RawDescriptionHelpFormatter)
        for param in cmd_spec["params"]:
            _add_param(sp, param)
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    global _quiet
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "format"):
        args.format = "auto"
    if not hasattr(args, "json"):
        args.json = False
    if not hasattr(args, "quiet"):
        args.quiet = False
    if not hasattr(args, "offline"):
        args.offline = False
    _quiet = bool(args.quiet)

    if not args.command:
        parser.print_help(sys.stderr)
        return EXIT_VALIDATION

    fmt = resolve_format(args)
    handler = HANDLERS.get(args.command)
    if handler is None:
        env = envelope_error("validation_error", f"unknown command: {args.command}", retryable=False)
        emit(env, fmt, args.command)
        return EXIT_VALIDATION

    try:
        env = handler(args)
    except Exception as e:
        env = envelope_error("runtime_error", f"unexpected error: {e}", retryable=True)

    emit(env, fmt, args.command)
    return exit_code_for(env)


if __name__ == "__main__":
    sys.exit(main())
