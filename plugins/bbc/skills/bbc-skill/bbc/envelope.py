"""JSON envelope, exit codes, TTY detection."""

import json
import os
import sys
import time
import uuid
from typing import Any

from bbc import SCHEMA_VERSION

# Exit codes — see references/agent-contract.md
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_AUTH = 2
EXIT_VALIDATION = 3
EXIT_NETWORK = 4

ERROR_CODE_TO_EXIT = {
    "validation_error": EXIT_VALIDATION,
    "auth_required": EXIT_AUTH,
    "auth_expired": EXIT_AUTH,
    "not_found": EXIT_RUNTIME,
    "rate_limited": EXIT_RUNTIME,
    "api_error": EXIT_RUNTIME,
    "network_error": EXIT_NETWORK,
    "internal_error": EXIT_RUNTIME,
}


def stdout_is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def effective_format(explicit: str | None) -> str:
    if explicit in ("json", "table"):
        return explicit
    return "table" if stdout_is_tty() else "json"


def new_request_id() -> str:
    return "req_" + uuid.uuid4().hex[:12]


class Clock:
    def __init__(self) -> None:
        self.start = time.monotonic()

    def ms(self) -> int:
        return int((time.monotonic() - self.start) * 1000)


def success(
    data: Any,
    *,
    request_id: str,
    elapsed_ms: int,
    extra_meta: dict | None = None,
    extra_top: dict | None = None,
) -> dict:
    env = {
        "ok": True,
        "data": data,
        "meta": {
            "request_id": request_id,
            "latency_ms": elapsed_ms,
            "schema_version": SCHEMA_VERSION,
            **(extra_meta or {}),
        },
    }
    if extra_top:
        env.update(extra_top)
    return env


def failure(
    code: str,
    message: str,
    *,
    request_id: str,
    elapsed_ms: int,
    retryable: bool = False,
    field: str | None = None,
    extra: dict | None = None,
) -> dict:
    err: dict = {"code": code, "message": message, "retryable": retryable}
    if field:
        err["field"] = field
    if code == "auth_expired":
        err["retry_after_auth"] = True
    if extra:
        err.update(extra)
    return {
        "ok": False,
        "error": err,
        "meta": {
            "request_id": request_id,
            "latency_ms": elapsed_ms,
            "schema_version": SCHEMA_VERSION,
        },
    }


def emit_json(env: dict) -> None:
    """Emit envelope to stdout as JSON (single line + trailing newline)."""
    json.dump(env, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def emit_table(env: dict) -> None:
    """Human-readable rendering (very simple)."""
    if env.get("ok") == True or env.get("ok") == "partial":
        _print_table_success(env)
    else:
        err = env.get("error", {})
        sys.stdout.write(
            f"\x1b[31mERROR\x1b[0m [{err.get('code')}] {err.get('message')}\n"
            if _colors_ok()
            else f"ERROR [{err.get('code')}] {err.get('message')}\n"
        )
        if err.get("retryable"):
            sys.stdout.write("  (retryable)\n")
    sys.stdout.flush()


def _print_table_success(env: dict) -> None:
    data = env.get("data")
    if isinstance(data, dict):
        # Flatten one level
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                sys.stdout.write(f"{k}:\n")
                sys.stdout.write(
                    "  "
                    + json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\n  ")
                    + "\n"
                )
            else:
                sys.stdout.write(f"{k}: {v}\n")
    else:
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _colors_ok() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return stdout_is_tty()


def emit(env: dict, fmt: str) -> None:
    if fmt == "table":
        emit_table(env)
    else:
        emit_json(env)


def exit_for(env: dict) -> int:
    if env.get("ok") == True:
        return EXIT_OK
    if env.get("ok") == "partial":
        return EXIT_OK
    code = env.get("error", {}).get("code", "internal_error")
    return ERROR_CODE_TO_EXIT.get(code, EXIT_RUNTIME)
