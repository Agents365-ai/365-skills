"""Command parameter schemas — single source of truth for argparse, help, and
`bbc schema` introspection.
"""

from bbc import SCHEMA_VERSION

BV_PATTERN = r"^BV[A-Za-z0-9]{10}$"

EXIT_CODES = {
    "0": "success",
    "1": "runtime or API error",
    "2": "auth error (cookie invalid/missing)",
    "3": "validation error (bad parameter)",
    "4": "network error (timeout / retries exhausted)",
}

ERROR_CODES = {
    "validation_error": {"exit": 3, "retryable": False},
    "auth_required": {"exit": 2, "retryable": True, "retry_after_auth": True},
    "auth_expired": {"exit": 2, "retryable": True, "retry_after_auth": True},
    "not_found": {"exit": 1, "retryable": False},
    "rate_limited": {"exit": 1, "retryable": True},
    "api_error": {"exit": 1, "retryable": False},
    "network_error": {"exit": 4, "retryable": True},
    "internal_error": {"exit": 1, "retryable": False},
}

COMMANDS = {
    "fetch": {
        "since": "1.0.0",
        "tier": "open",
        "summary": "Fetch all comments (top-level + nested + pinned) for a single video.",
        "params": {
            "target": {
                "type": "string",
                "required": True,
                "description": "BV number or full Bilibili video URL.",
                "pattern": BV_PATTERN + " | bilibili URL",
                "positional": True,
            },
            "max": {
                "type": "integer",
                "min": 1,
                "default": None,
                "description": "Max top-level comments to fetch (default: all).",
            },
            "since": {
                "type": "string",
                "format": "date-time or date",
                "default": None,
                "description": "Only fetch comments newer than this timestamp (ISO-8601).",
            },
            "output": {
                "type": "string",
                "default": "./bilibili-comments/<bvid>",
                "description": "Output directory.",
            },
            "cookie_file": {
                "type": "string",
                "default": None,
                "description": "Path to Netscape cookie file (overrides auto-detect).",
            },
            "browser": {
                "type": "string",
                "enum": ["auto", "firefox", "chrome", "edge", "safari"],
                "default": "auto",
                "description": "Which browser to auto-detect cookies from.",
            },
            "format": {
                "type": "string",
                "enum": ["json", "table"],
                "default": "json (non-TTY) / table (TTY)",
                "description": "Stdout format.",
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "Preview request plan without network calls.",
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Ignore existing state; refetch from scratch.",
            },
        },
    },
    "fetch-user": {
        "since": "1.0.0",
        "tier": "open",
        "summary": "Batch fetch comments for all videos of a UP主 by UID.",
        "params": {
            "uid": {
                "type": "integer",
                "required": True,
                "description": "UP主 UID (member id).",
                "positional": True,
            },
            "output": {
                "type": "string",
                "default": "./bilibili-comments/user-<uid>",
                "description": "Output directory.",
            },
            "video_limit": {
                "type": "integer",
                "min": 1,
                "default": None,
                "description": "Limit how many of the UP's recent videos to fetch.",
            },
            "max": {"type": "integer", "min": 1, "default": None, "description": "Per-video top-level cap."},
            "cookie_file": {"type": "string", "default": None, "description": "See fetch."},
            "browser": {"type": "string", "enum": ["auto", "firefox", "chrome", "edge", "safari"], "default": "auto"},
            "format": {"type": "string", "enum": ["json", "table"], "default": "auto"},
            "dry_run": {"type": "boolean", "default": False},
        },
    },
    "summarize": {
        "since": "1.0.0",
        "tier": "open",
        "summary": "Rebuild summary.json from an existing comments.jsonl directory.",
        "params": {
            "directory": {
                "type": "string",
                "required": True,
                "description": "Path to fetch output dir (must contain comments.jsonl).",
                "positional": True,
            },
            "format": {"type": "string", "enum": ["json", "table"], "default": "auto"},
        },
    },
    "cookie-check": {
        "since": "1.0.0",
        "tier": "open",
        "summary": "Validate cookie and print logged-in user info.",
        "params": {
            "cookie_file": {"type": "string", "default": None, "description": "Path to cookie file (optional)."},
            "browser": {"type": "string", "enum": ["auto", "firefox", "chrome", "edge", "safari"], "default": "auto"},
            "format": {"type": "string", "enum": ["json", "table"], "default": "auto"},
        },
    },
    "schema": {
        "since": "1.0.0",
        "tier": "open",
        "summary": "Return JSON schema for a command (or all commands).",
        "params": {
            "command": {
                "type": "string",
                "required": False,
                "description": "Command name; omit to dump all.",
                "positional": True,
            },
        },
    },
}


def describe(command: str | None = None) -> dict:
    if command and command in COMMANDS:
        return {
            "command": command,
            "schema_version": SCHEMA_VERSION,
            **COMMANDS[command],
            "envelope": _envelope_contract(),
            "exit_codes": EXIT_CODES,
            "error_codes": ERROR_CODES,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "commands": {name: spec["summary"] for name, spec in COMMANDS.items()},
        "envelope": _envelope_contract(),
        "exit_codes": EXIT_CODES,
        "error_codes": ERROR_CODES,
    }


def _envelope_contract() -> dict:
    return {
        "success": {"ok": True, "data": "<object>", "meta": {"request_id": "str", "latency_ms": "int", "schema_version": "str"}},
        "failure": {
            "ok": False,
            "error": {"code": "str", "message": "str", "retryable": "bool", "field?": "str", "retry_after_auth?": "bool"},
            "meta": {"request_id": "str", "latency_ms": "int", "schema_version": "str"},
        },
    }
