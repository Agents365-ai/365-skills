"""Shared helpers for every scholar-deep-research script.

Provides:
  - USER_AGENT             polite-pool identifier for HTTP calls
  - EXIT_*                 stable, differentiated exit codes for agents/orchestrators
  - ok() / err()           unified stdout envelope
  - UpstreamError          typed exception for HTTP/API failures
  - make_paper / make_payload / emit   search-script normalization helpers

Envelope contract:
  success → {"ok": true, "data": <any>, ...}
  failure → {"ok": false, "error": {"code": str, "message": str,
                                    "retryable": bool, ...}}

Every script must print exactly one envelope to stdout and exit with one of
the EXIT_* codes. Diagnostics go to stderr. No prose on stdout, ever.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Canonical version string. Bump in lockstep with the `version` field in
# SKILL.md frontmatter so USER_AGENT, telemetry, and skill metadata agree.
VERSION = "0.14.0"

USER_AGENT = (
    f"scholar-deep-research/{VERSION} "
    "(+https://github.com/Agents365-ai/scholar-deep-research; "
    "polite-pool)"
)

# ---------- exit codes ----------
# Stable across versions. Documented in SKILL.md.
EXIT_OK = 0          # success
EXIT_RUNTIME = 1     # runtime / API logic error (e.g. malformed upstream response)
EXIT_UPSTREAM = 2    # upstream / network error (retryable)
EXIT_VALIDATION = 3  # bad input: missing flag, bad value, whitelist violation
EXIT_STATE = 4       # state file missing, corrupt, or schema mismatch


# ---------- Phase 1 budget envelope ----------
# Caps on Phase 1 ingestion to prevent runaway agent loops (e.g. a
# stricter-than-achievable saturation target driving infinite rounds).
# Read at every check, not at module import, so tests and orchestrators
# can override per-process. ENV-only override — agents cannot raise
# their own ceiling (P2 trust boundary).

def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def phase1_max_rounds() -> int:
    """Cap on distinct discovery rounds before Phase 1 refuses further ingest.

    Default 10 — enough for ~5 keyword clusters with one or two follow-up
    refinement rounds without bumping the cap. Was 5 in 0.12.x; bumped
    after a real test run hit the cap on a moderately-broad CS topic
    (LLM-as-a-judge) before saturation. Override with the env var.
    """
    return _env_int("SCHOLAR_PHASE1_MAX_ROUNDS", 10)


def phase1_max_requests_per_source() -> int:
    """Cap on per-source ingest events during Phase 1 (one event = one query call)."""
    return _env_int("SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE", 20)


# ---------- per-source rate limiting ----------
# Some upstream APIs enforce strict per-IP intervals: arXiv (3s), NCBI
# E-utilities (~0.34s without a key, ~0.1s with), DBLP (no formal limit
# but ~1s avoids the SSL EOF flakiness we see on bursts). The skill
# encourages parallel multi-source search, but agents don't always know
# which sources are quota-managed and which aren't — so each search
# script self-serialises against a shared file-lock under
# ${SCHOLAR_CACHE_DIR}/rate/<source>.lock. Effect: N parallel
# search_arxiv.py invocations sharing the same cache dir queue
# automatically and sleep the right gap between requests, even though
# they're separate Python processes. Requires fcntl (Linux/macOS); on
# Windows the lock is best-effort (worst case: a small burst gets
# through, which is what we already had).

_RATE_DIR = "rate"


def _rate_state_path(source: str) -> Path:
    """File the limiter reads/writes the last-call timestamp through.

    Lives in the same idempotency-cache root so users only set one env
    var. One file per source: parallel arxiv calls block each other but
    not parallel openalex calls.
    """
    cache_dir = Path(os.environ.get("SCHOLAR_CACHE_DIR", ".scholar_cache"))
    rate_dir = cache_dir / _RATE_DIR
    rate_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in ("_", "-") else "_"
                   for c in source.lower())
    return rate_dir / f"{safe}.lock"


def enforce_min_interval(source: str, min_seconds: float) -> float:
    """Block until ≥`min_seconds` has elapsed since the last call for `source`.

    Cross-process: the function takes an exclusive flock on a per-source
    sentinel file, reads the last-call timestamp, sleeps the difference
    if needed, writes the new timestamp, and releases. N concurrent
    invocations from N processes will serialise themselves.

    Returns the actual sleep duration in seconds (0 if no wait was needed).
    No-op when min_seconds <= 0. Best-effort on systems without fcntl —
    falls back to timestamp-only coordination, which still sleeps
    correctly when the timestamps don't race.
    """
    if min_seconds <= 0:
        return 0.0
    path = _rate_state_path(source)
    # 'a+' both creates and lets us seek/read. Open in text mode for
    # cross-platform consistency on the timestamp string.
    with open(path, "a+") as f:
        try:
            import fcntl  # type: ignore[import-not-found]
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            # Windows or filesystem without flock — degrade silently.
            pass
        f.seek(0)
        try:
            last = float((f.read() or "0").strip() or "0")
        except ValueError:
            last = 0.0
        now = time.time()
        wait = (last + min_seconds) - now
        if wait > 0:
            time.sleep(wait)
            now = time.time()
        f.seek(0)
        f.truncate()
        f.write(f"{now:.6f}\n")
        return max(0.0, wait)


# ---------- TTY detection ----------

def stdout_is_tty() -> bool:
    """True if stdout is an interactive terminal.

    Scripts use this to pick a human-friendly default (raw text, tables)
    vs. an agent-friendly default (JSON envelope). Orchestrators that
    want the agent format regardless of terminal can pipe stdout, or
    pass an explicit `--format json` / `--output <file>` flag.
    """
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


# ---------- auto-populated envelope metadata ----------
#
# Every ok()/err() envelope carries a `meta` block with:
#   - request_id: uuid-derived, stable for the life of this process. An
#     orchestrator may override via the SCHOLAR_REQUEST_ID env var to
#     correlate envelopes with its own trace.
#   - latency_ms: monotonic wall-clock since module load (process start).
#     Useful for SLO tracking even without external instrumentation.
#   - cli_version: canonical VERSION constant so an agent can detect
#     drift against a cached schema (Principle 6).
#   - schema_version: envelope schema version (not CLI version). Bumped
#     when the envelope shape changes.

_START_MONO = time.monotonic()
_REQUEST_ID = (
    os.environ.get("SCHOLAR_REQUEST_ID")
    or f"req_{uuid.uuid4().hex[:10]}"
)


def _auto_meta() -> dict[str, Any]:
    # Referenced at call time, so the ordering against SCHEMA_VERSION's
    # later definition is fine — Python resolves module globals lazily.
    return {
        "request_id": _REQUEST_ID,
        "latency_ms": int((time.monotonic() - _START_MONO) * 1000),
        "cli_version": VERSION,
        "schema_version": SCHEMA_VERSION,
    }


# ---------- envelope helpers ----------

def ok(data: Any = None, *, meta: dict[str, Any] | None = None,
       **extra: Any) -> None:
    """Print a success envelope to stdout.

    Does not exit. Caller returns normally (implicit exit 0).
    The `meta` block is auto-populated with request_id, latency_ms,
    cli_version, and schema_version; caller-supplied `meta` entries win
    on key conflict so a caller can override any of them if needed.
    """
    merged_meta = _auto_meta()
    if meta is not None:
        merged_meta.update(meta)
    payload: dict[str, Any] = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload["meta"] = merged_meta
    payload.update(extra)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def err(code: str, message: str, *, retryable: bool = False,
        exit_code: int = EXIT_RUNTIME, **ctx: Any) -> None:
    """Print an error envelope to stdout and exit with `exit_code`.

    `code` is a stable snake_case routing key (e.g. "state_not_found",
    "upstream_error"). `message` is the human-readable sentence. `retryable`
    signals whether calling the exact same command again may succeed. Any
    additional kwargs become extra fields on the error object (e.g. `field`,
    `source`, `allowed`). The top-level envelope carries auto-populated
    `meta` for correlation.
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    error.update(ctx)
    json.dump({"ok": False, "error": error, "meta": _auto_meta()},
              sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(exit_code)


class UpstreamError(Exception):
    """HTTP/API failure raised from inside a search function.

    The search script's main() catches this and calls err() so the agent sees
    a structured failure envelope rather than a silent empty result.
    """

    def __init__(self, source: str, message: str, *,
                 retryable: bool = True,
                 exit_code: int = EXIT_UPSTREAM,
                 status: int | None = None) -> None:
        super().__init__(message)
        self.source = source
        self.message = message
        self.retryable = retryable
        self.exit_code = exit_code
        self.status = status


def record_search_failure(state_path: str | None, source: str, message: str,
                          *, status: int | None = None) -> None:
    """Persist an upstream search failure into state.search_diagnostics.

    No-op when --state is absent (agent ran a stand-alone search). When
    state is present, calls research_state.apply_search_failure under the
    state lock so concurrent failures from parallel searches are race-free.

    Best-effort: any error writing to state is silently swallowed (the
    primary failure is already on its way to err()) — we do not want a
    diagnostic write failure to mask the real upstream error.
    """
    if not state_path:
        return
    try:
        from research_state import apply_search_failure
        apply_search_failure(Path(state_path), source, message, status=status)
    except Exception:
        # Diagnostic writes are advisory; never block the real error path.
        pass

# Fields that every normalized paper should have (None if unknown).
PAPER_FIELDS = (
    "doi", "title", "authors", "year", "venue", "abstract",
    "citations", "url", "pdf_url",
    "openalex_id", "arxiv_id", "pmid",
)


def make_paper(**kwargs: Any) -> dict[str, Any]:
    """Build a paper dict with all standard fields, missing → None."""
    p: dict[str, Any] = {f: None for f in PAPER_FIELDS}
    p.update({k: v for k, v in kwargs.items() if v is not None})
    # type discipline
    if p.get("authors") and not isinstance(p["authors"], list):
        p["authors"] = [p["authors"]]
    if p.get("year"):
        try:
            p["year"] = int(p["year"])
        except (TypeError, ValueError):
            p["year"] = None
    if p.get("citations") is not None:
        try:
            p["citations"] = int(p["citations"])
        except (TypeError, ValueError):
            p["citations"] = 0
    return p


def make_payload(source: str, query: str, round_: int,
                 papers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": source,
        "query": query,
        "round": round_,
        "papers": papers,
    }


def resolve_search_round(state_path: str | None, source: str,
                         explicit: int | None) -> int:
    """Decide which round number to label this search call.

    If `--round` was explicitly passed (`explicit is not None`), return
    it unchanged — the agent retains full control. Otherwise inspect
    `state.queries` and return `max(round seen for this source) + 1`,
    or `1` when no prior round exists for that source. Falls back to 1
    when state is absent or unreadable.

    Why this matters: saturation tracking in `research_state.py
    saturation` partitions papers by `last_round = max(queries[source]
    .round)`. If every search call defaults to `round=1`, every paper
    has `first_seen_round=1`, and the saturation `max_new_citations`
    window spans the entire corpus — a single highly-cited paper
    (Geneformer, scGPT) blocks per-source saturation forever. Auto-
    detecting the next round per source closes this trap by default
    while preserving the explicit-override path.
    """
    if explicit is not None:
        return explicit
    if not state_path:
        return 1
    try:
        state = json.loads(Path(state_path).read_text())
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return 1
    rounds = [
        q.get("round", 0)
        for q in (state.get("queries") or [])
        if q.get("source") == source and isinstance(q.get("round"), int)
    ]
    return (max(rounds) + 1) if rounds else 1


def emit(payload: dict[str, Any], output: str | None,
         state: str | None, *, meta: dict[str, Any] | None = None) -> None:
    """Write search payload to --output JSON and/or hand to research_state ingest.

    Always prints exactly one envelope to stdout:
      - with --state: envelope from apply_ingest() (routed through the state lock)
      - with --output only: {"ok": true, "data": {"output": path, "count": N, ...}}
      - with neither: {"ok": true, "data": <payload>}

    `meta` is merged into the envelope's auto-meta (search-cache hit/miss
    flags travel here from `with_search_cache`). Empty `meta` → identical
    envelope to before, so existing scripts' output is unchanged when the
    cache is disabled.
    """
    extra_meta = meta or None
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    if state:
        # Call apply_ingest directly — no subprocess, no shared temp file.
        # Concurrent searches are serialized by the state lock inside
        # apply_ingest, so Phase 1 fanout is race-free.
        # Lazy import avoids a circular dependency at module load.
        from research_state import Phase1BudgetExhausted, apply_ingest
        try:
            summary = apply_ingest(Path(state), payload)
        except Phase1BudgetExhausted as exc:
            env_var = ("SCHOLAR_PHASE1_MAX_ROUNDS"
                       if exc.limit_kind == "max_rounds"
                       else "SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE")
            err("phase1_budget_exhausted", str(exc),
                retryable=False, exit_code=EXIT_VALIDATION,
                limit_kind=exc.limit_kind, limit=exc.limit,
                current=exc.current, source=exc.source,
                next=[
                    f"# Raise the cap and retry: {env_var}={exc.limit * 2}",
                    "# Or: check saturation and consider advancing to phase 2:",
                    "python scripts/research_state.py saturation",
                    "python scripts/research_state.py advance --check-only",
                ])
        ok(summary, meta=extra_meta)
        return

    if output:
        ok({
            "output": str(output),
            "source": payload.get("source"),
            "query": payload.get("query"),
            "round": payload.get("round"),
            "count": len(payload.get("papers", [])),
        }, meta=extra_meta)
        return

    # Neither --output nor --state: dump the whole payload, enveloped.
    ok(payload, meta=extra_meta)


# ---------- search result TTL cache (opt-in) ----------
#
# Distinct from the idempotency cache above: this is a *natural* result cache
# for HTTP search calls, opt-in via SCHOLAR_SEARCH_CACHE=1 with a 24h default
# TTL. Idempotency cache names a specific run and never expires; this cache
# names a query and expires by clock. Different concerns → different storage
# subdirs (`searches/` vs the flat `cache_dir()/`).
#
# The cap is wired into the 4 stdlib search scripts; agents call them
# normally and a cache hit returns the same papers list with a `search_cache:
# hit` marker in the envelope's `meta`. Default OFF — existing scripts behave
# identically until a human/orchestrator opts in.

_SEARCH_CACHE_VERSION = 1


def _search_cache_enabled() -> bool:
    val = os.environ.get("SCHOLAR_SEARCH_CACHE", "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _search_cache_ttl_seconds() -> int:
    hours = _env_int("SCHOLAR_SEARCH_CACHE_TTL_HOURS", 24)
    return max(0, hours) * 3600


def _search_cache_dir() -> Path:
    d = cache_dir() / "searches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _search_cache_key(source: str, query: str, limit: int,
                      filters: dict[str, Any]) -> str:
    """Canonical key: source + normalized query + limit + sorted-filter JSON.

    Whitespace in the query is collapsed and stripped so trivially-different
    inputs share an entry. Filter keys are sorted to make `{a:1,b:2}` and
    `{b:2,a:1}` collide.
    """
    norm_query = " ".join(query.split())
    blob = json.dumps({
        "source": source,
        "query": norm_query,
        "limit": int(limit),
        "filters": filters or {},
    }, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def with_search_cache(*, source: str, query: str, limit: int,
                      filters: dict[str, Any] | None,
                      fetch: Callable[[], list[dict[str, Any]]]
                      ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Wrap a search HTTP call with an opt-in 24h TTL cache.

    Returns `(papers, meta)`. When the cache is disabled (the default), the
    fetch always runs and `meta` is empty — so the envelope is bit-identical
    to the pre-cache behavior. When enabled, `meta` is `{"search_cache":
    "hit"|"miss", "cached_at": ISO}` so the agent can audit the corpus
    provenance.

    Cache failures (corrupt file, IO error) silently fall back to fetch.
    The cache stores the *normalized papers list*, not the full envelope,
    so the caller can still wrap it with a fresh `make_payload`/`emit`.
    """
    filters = dict(filters or {})
    if not _search_cache_enabled():
        return fetch(), {}

    key = _search_cache_key(source, query, limit, filters)
    path = _search_cache_dir() / f"{key}.json"
    ttl = _search_cache_ttl_seconds()

    if path.exists():
        try:
            entry = json.loads(path.read_text())
            cached_at_str = entry.get("cached_at", "")
            cached_at = datetime.fromisoformat(cached_at_str)
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if ttl == 0 or age < ttl:
                return entry["papers"], {
                    "search_cache": "hit",
                    "cached_at": cached_at_str,
                }
        except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError):
            # Any corruption → fall through to fetch + overwrite.
            pass

    papers = fetch()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        path.write_text(json.dumps({
            "version": _SEARCH_CACHE_VERSION,
            "source": source,
            "query": query,
            "limit": int(limit),
            "filters": filters,
            "cached_at": now,
            "papers": papers,
        }, ensure_ascii=False))
    except OSError:
        # Don't fail the search just because we couldn't write the cache.
        pass
    return papers, {"search_cache": "miss"}


def reconstruct_inverted_abstract(idx: dict[str, list[int]] | None) -> str | None:
    """OpenAlex returns abstracts as inverted indexes; reconstruct flat text."""
    if not idx:
        return None
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None


# ---------- schema introspection ----------

SCHEMA_VERSION = 1

# Stable exit-code vocabulary, shared by every script. The schema response
# includes this so agents can route on code without reading SKILL.md.
EXIT_CODE_VOCAB: dict[str, str] = {
    "0": "success",
    "1": "runtime error (e.g. malformed upstream response, missing dependency)",
    "2": "upstream / network error (retryable)",
    "3": "validation error (bad input)",
    "4": "state error (missing, corrupt, or schema mismatch)",
}


def _action_type_name(action: argparse.Action) -> str:
    """Map an argparse action to a JSON-schema-ish type name."""
    if isinstance(action, (argparse._StoreTrueAction,
                           argparse._StoreFalseAction)):
        return "boolean"
    t = action.type
    if t is int:
        return "integer"
    if t is float:
        return "number"
    if t is None or t is str:
        return "string"
    return getattr(t, "__name__", str(t))


def set_command_meta(parser: argparse.ArgumentParser, **meta: Any) -> None:
    """Attach schema metadata to a parser or subparser.

    Supported keys (all optional):
      since:        first version the command appeared in (e.g. "0.4.0")
      deprecated:   True if the command is on the deprecation path
      replaced_by:  name of the command that supersedes this one
      dangerous:    True for destructive commands (init --force, etc.)
      tier:         "read" | "write" | "destructive" (for safety UIs)

    Surfaced in `--schema` output under each subcommand's `meta` field.
    Agents with a cached schema compare `since` / `deprecated` against
    their local copy to detect drift before calling a renamed method.
    """
    parser._schema_meta = dict(meta)  # type: ignore[attr-defined]


def _parser_to_schema(parser: argparse.ArgumentParser,
                      command: str) -> dict[str, Any]:
    """Walk an argparse parser into a JSON-serializable schema.

    Subparsers recurse into `subcommands`. Positional arguments are emitted
    alongside flags — every agent-visible parameter the command accepts.
    """
    params: dict[str, Any] = {}
    subcommands: dict[str, Any] = {}

    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            for subname, subparser in action.choices.items():
                subcommands[subname] = _parser_to_schema(
                    subparser, f"{command} {subname}")
            continue

        dest = action.dest
        entry: dict[str, Any] = {
            "type": _action_type_name(action),
            "required": bool(action.required),
        }
        if action.option_strings:
            entry["flag"] = action.option_strings[0]
        else:
            entry["positional"] = True
        if action.help:
            entry["help"] = action.help
        if action.choices is not None:
            entry["choices"] = list(action.choices)
        if (action.default is not None
                and action.default is not argparse.SUPPRESS):
            try:
                json.dumps(action.default)  # ensure serializable
                entry["default"] = action.default
            except (TypeError, ValueError):
                entry["default"] = str(action.default)
        if action.nargs in ("*", "+") or isinstance(action,
                                                    argparse._AppendAction):
            entry["multiple"] = True
        params[dest] = entry

    out: dict[str, Any] = {
        "command": command,
        "description": parser.description or "",
        "params": params,
    }
    meta = getattr(parser, "_schema_meta", None)
    if meta:
        out["meta"] = meta
    if subcommands:
        out["subcommands"] = subcommands
    return out


def maybe_emit_schema(parser: argparse.ArgumentParser, command: str,
                      argv: list[str] | None = None) -> None:
    """If the caller passed --schema, emit the parser schema and exit 0.

    Call this at the top of every script's main() *before* parser.parse_args().
    The intercept is pre-parse so --schema works even when required flags are
    missing — an agent discovering a command should be able to ask for its
    schema without already knowing what the flags are.
    """
    argv = argv if argv is not None else sys.argv[1:]
    if "--schema" not in argv:
        return
    schema = _parser_to_schema(parser, command)
    schema["exit_codes"] = EXIT_CODE_VOCAB
    schema["envelope_version"] = SCHEMA_VERSION
    schema["cli_version"] = VERSION
    ok(schema)
    sys.exit(0)


# ---------- idempotency cache ----------
#
# The cache is a directory of JSON files, one per idempotency key. A cache
# entry stores `{response, signature, cached_at}`. When an agent retries a
# command with the same `--idempotency-key`, the cached response is returned
# unchanged so repeated calls do not re-spend API budget or re-mutate state.
#
# Cache directory precedence: $SCHOLAR_CACHE_DIR > .scholar_cache/ in cwd.
# There is no TTL — the agent (or a human) flushes stale keys manually. This
# is deliberate: an idempotency key names a *specific run*, not a time window,
# so silent expiry would violate the contract.

CACHE_ENTRY_VERSION = 1


def cache_dir() -> Path:
    """Return the cache directory path, creating it on first use."""
    d = Path(os.environ.get("SCHOLAR_CACHE_DIR", ".scholar_cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_path_for(key: str) -> Path:
    """Map an idempotency key to its cache file path.

    Keys are sanitized to safe filenames: the raw key is hashed and the
    resulting hex prefix is used as the filename. This means arbitrary
    user-supplied key strings (including `/`, whitespace, unicode) are safe.
    """
    safe = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return cache_dir() / f"{safe}.json"


def command_signature(args: argparse.Namespace,
                      *, exclude: tuple[str, ...] = ()) -> str:
    """Hash an argparse.Namespace into a short signature.

    Used to detect idempotency-key collisions: the same key MUST see the
    same (semantically meaningful) arguments. `exclude` names fields that
    do not affect output (e.g. `email` for polite-pool identification).
    The `idempotency_key` field is always excluded.
    """
    ignored = set(exclude) | {"idempotency_key", "dry_run", "schema", "func"}
    fields = {}
    for k, v in vars(args).items():
        if k in ignored or k.startswith("_"):
            continue
        # Skip callables (e.g. argparse's `func` set_defaults): their repr
        # contains the function's memory address and changes every process,
        # which would make every retry look like a signature mismatch.
        if callable(v):
            continue
        fields[k] = v
    blob = json.dumps(fields, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def read_cache(key: str) -> dict[str, Any] | None:
    """Read a cache entry by key, or None if missing/corrupt."""
    path = cache_path_for(key)
    if not path.exists():
        return None
    try:
        entry = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(entry, dict) or "response" not in entry:
        return None
    return entry


def write_cache(key: str, response: dict[str, Any], *,
                signature: str | None = None) -> None:
    """Persist a cache entry for an idempotency key."""
    path = cache_path_for(key)
    entry = {
        "version": CACHE_ENTRY_VERSION,
        "key": key,
        "signature": signature,
        "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "response": response,
    }
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2))


def reject_dry_run_with_idempotency(args: argparse.Namespace) -> None:
    """Emit `idempotency_with_dry_run` / exit 3 if both flags are set.

    Call at the top of any command that has both `--dry-run` and
    `--idempotency-key` flags. Without this check, a command that
    short-circuits on dry-run before reaching `with_idempotency`
    would silently accept the nonsensical combination.
    """
    if getattr(args, "dry_run", False) and getattr(args, "idempotency_key", None):
        err("idempotency_with_dry_run",
            "--idempotency-key cannot be combined with --dry-run: a dry "
            "run does not mutate anything and nothing is cacheable.",
            retryable=False, exit_code=EXIT_VALIDATION,
            key=args.idempotency_key)


def with_idempotency(
    args: argparse.Namespace,
    compute: Callable[[], dict[str, Any]],
    *,
    signature_exclude: tuple[str, ...] = (),
) -> None:
    """Run `compute` under --idempotency-key semantics and emit ok(result).

    Wraps the common cache-check / compute / cache-write dance so every
    mutating command implements idempotency the same way. The caller
    supplies a zero-arg `compute` that returns the result dict; this
    helper handles cache hits, signature mismatches, and the final
    emission.

    `args` must be an argparse Namespace with an `idempotency_key`
    attribute (may be None). A non-None key combined with a truthy
    `dry_run` attribute returns a structured error — dry runs do not
    mutate and therefore cannot sensibly be cached.

    `signature_exclude` names parameters that should not participate in
    the signature hash (e.g. `email` for polite-pool fields that do not
    change the computed result).
    """
    key = getattr(args, "idempotency_key", None)
    dry = getattr(args, "dry_run", False)

    if not key:
        ok(compute())
        return

    if dry:
        err("idempotency_with_dry_run",
            "--idempotency-key cannot be combined with --dry-run: a dry "
            "run does not mutate anything and nothing is cacheable.",
            retryable=False, exit_code=EXIT_VALIDATION,
            key=key)

    sig = command_signature(args, exclude=signature_exclude)
    cached = read_cache(key)
    if cached is not None:
        if cached.get("signature") and cached["signature"] != sig:
            err("idempotency_key_mismatch",
                f"Idempotency key '{key}' was previously used with "
                f"different arguments. Use a new key or flush the cache entry.",
                retryable=False, exit_code=EXIT_VALIDATION,
                key=key,
                cached_signature=cached["signature"],
                current_signature=sig)
        ok(cached["response"], meta={
            "cache_hit": True,
            "idempotency_key": key,
            "cached_at": cached.get("cached_at"),
        })
        return

    result = compute()
    write_cache(key, result, signature=sig)
    ok(result, meta={"cache_hit": False, "idempotency_key": key})
