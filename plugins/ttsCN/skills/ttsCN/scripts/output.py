"""Agent-native JSON output envelope for ttsCN.

Stdout contract:
    Always valid JSON when --format=json or when stdout is not a TTY.
    Human-readable prose on stderr; machine-readable JSON on stdout.

Exit codes:
    0 — Success
    1 — Internal / runtime error
    2 — Invalid input / validation error
    3 — Auth / missing credentials
    4 — Backend API error (rate-limit, timeout, upstream failure)
"""

import json
import os
import sys
import time

SCHEMA_VERSION = "1.1.0"  # semver — bump on envelope/contract changes

# Fields deprecated in current version. Agents should migrate before removed_in.
# {"old_field": {"replaced_by":"new_field", "removed_in":"1.2.0"}}
DEPRECATED_FIELDS = {}

_PREFERENCES_KEY = "TTS_FORMAT"


def _stdout_is_tty():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def use_json(args):
    if hasattr(args, "format") and args.format == "json":
        return True
    if os.environ.get(_PREFERENCES_KEY) == "json":
        return True
    return not _stdout_is_tty()


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


VERSION = "1.3.2"  # tool version — single source of truth, imported by tts.py


def _get_version():
    return VERSION


def envelope(ok, data=None, error=None, meta=None, started_at=None):
    """Build standard JSON envelope.

    Success: {"ok":true, "data":{...}, "meta":{"version":"...","schema_version":"1.1.0","timestamp":"...","ms":123}}
    Error:   {"ok":false, "error":{"code":"...","message":"...","retryable":bool,...}, "meta":{...}}
    """
    if meta is None:
        meta = {}
    meta.setdefault("version", _get_version())
    meta.setdefault("schema_version", SCHEMA_VERSION)
    meta.setdefault("timestamp", _now_iso())
    if started_at is not None:
        meta["ms"] = round((time.time() - started_at) * 1000)
    if DEPRECATED_FIELDS:
        meta["deprecated_fields"] = DEPRECATED_FIELDS

    payload = {"ok": ok, "meta": meta}
    if ok:
        payload["data"] = data if data is not None else {}
    else:
        payload["error"] = error if error is not None else {}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def success(data=None, started_at=None, **extra_meta):
    return envelope(True, data=data, started_at=started_at, meta=extra_meta)


def error(code, message, retryable=False, field=None, backend=None,
          started_at=None, **extra):
    err = {"code": code, "message": message, "retryable": retryable}
    if field:
        err["field"] = field
    if backend:
        err["backend"] = backend
    err.update(extra)
    return envelope(False, error=err, started_at=started_at)


def emit_success(data=None, started_at=None, **extra):
    print(success(data, started_at=started_at, **extra))
    sys.exit(0)


def emit_error(code, message, retryable=False, field=None, backend=None,
               started_at=None, exit_code=1, **extra):
    # Human-readable on stderr
    print(f"Error [{code}]: {message}", file=sys.stderr)
    if field:
        print(f"  Field: {field}", file=sys.stderr)
    if backend:
        print(f"  Backend: {backend}", file=sys.stderr)
    # Machine-readable on stdout
    err = {"code": code, "message": message, "retryable": retryable}
    if field:
        err["field"] = field
    if backend:
        err["backend"] = backend
    err.update(extra)
    print(envelope(False, error=err, started_at=started_at))
    sys.exit(exit_code)


EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_VALIDATION = 2
EXIT_AUTH = 3
EXIT_BACKEND = 4


def exit_for_error_code(code):
    if code in ("auth_missing_env", "auth_invalid"):
        return EXIT_AUTH
    if code in ("validation_failed", "input_not_found", "input_empty",
                "tool_missing"):
        return EXIT_VALIDATION
    if code in ("backend_error", "backend_timeout", "backend_rate_limited"):
        return EXIT_BACKEND
    return EXIT_INTERNAL
