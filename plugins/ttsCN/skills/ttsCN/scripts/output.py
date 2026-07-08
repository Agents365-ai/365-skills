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

# Auto-detect output mode
_PREFERENCES_KEY = "TTS_FORMAT"


def _stdout_is_tty():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def use_json(args):
    """Determine whether to emit JSON on stdout.

    Precedence:
      1. --format json  (explicit CLI flag)
      2. TTS_FORMAT=json env var
      3. stdout is NOT a TTY → default to JSON
      4. stdout IS a TTY → default to human text
    """
    if hasattr(args, "format") and args.format == "json":
        return True
    if os.environ.get(_PREFERENCES_KEY) == "json":
        return True
    return not _stdout_is_tty()


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# Imported lazily to avoid circular dependency
_VERSION = None


def _get_version():
    global _VERSION
    if _VERSION is None:
        try:
            # Read from providers.json
            _ROOT = os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))
            _path = os.path.join(_ROOT, "data", "providers.json")
            with open(_path) as f:
                _VERSION = json.load(f).get("updated", "0.0.0")
        except Exception:
            _VERSION = "0.0.0"
    return _VERSION


def envelope(ok, data=None, error=None, meta=None, started_at=None):
    """Build the standard JSON envelope.

    Success: {"ok":true, "data":{...}, "meta":{"version":"...","ms":123}}
    Error:   {"ok":false, "error":{"code":"...","message":"...","retryable":bool,...}, "meta":{...}}
    """
    if meta is None:
        meta = {}
    meta.setdefault("version", _get_version())
    meta.setdefault("timestamp", _now_iso())
    if started_at is not None:
        meta["ms"] = round((time.time() - started_at) * 1000)

    payload = {"ok": ok, "meta": meta}
    if ok:
        payload["data"] = data if data is not None else {}
    else:
        payload["error"] = error if error is not None else {}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def success(data=None, started_at=None, **extra_meta):
    """Build success envelope."""
    return envelope(True, data=data, started_at=started_at, meta=extra_meta)


def error(code, message, retryable=False, field=None, backend=None,
          started_at=None, **extra):
    """Build error envelope.

    Args:
        code: Stable machine-readable code, e.g. "auth_missing_env"
        message: Human-readable description
        retryable: Whether the agent should retry
        field: Which input field/parameter caused the error (optional)
        backend: Which backend was in use (optional)
        extra: Additional context fields
    """
    err = {"code": code, "message": message, "retryable": retryable}
    if field:
        err["field"] = field
    if backend:
        err["backend"] = backend
    err.update(extra)
    return envelope(False, error=err, started_at=started_at)


def emit_success(data=None, started_at=None, **extra):
    """Print success envelope to stdout and exit 0."""
    print(success(data, started_at=started_at, **extra))
    sys.exit(0)


def emit_error(code, message, retryable=False, field=None, backend=None,
               started_at=None, exit_code=1, **extra):
    """Print error to stderr for humans AND error envelope to stdout for agents.

    Also exits with the appropriate distinct exit code.
    """
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


# Exit code mapping
EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_VALIDATION = 2
EXIT_AUTH = 3
EXIT_BACKEND = 4


def exit_for_error_code(code):
    """Map error code string to exit code integer."""
    if code in ("auth_missing_env", "auth_invalid"):
        return EXIT_AUTH
    if code in ("validation_failed", "input_not_found", "input_empty"):
        return EXIT_VALIDATION
    if code in ("backend_error", "backend_timeout", "backend_rate_limited"):
        return EXIT_BACKEND
    return EXIT_INTERNAL
