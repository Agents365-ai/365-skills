"""NDJSON progress events on stderr."""

import json
import sys
import time
from typing import Any


class Progress:
    """Emit one-line JSON progress events to stderr.

    Silent if stderr is not a TTY AND BBC_PROGRESS is unset — keeps
    piped/captured runs clean. Force-on with BBC_PROGRESS=1.
    """

    def __init__(self, command: str, request_id: str, *, enabled: bool | None = None):
        self.command = command
        self.request_id = request_id
        if enabled is None:
            import os

            env = os.environ.get("BBC_PROGRESS", "").lower()
            if env in ("1", "true", "yes"):
                enabled = True
            elif env in ("0", "false", "no"):
                enabled = False
            else:
                enabled = sys.stderr.isatty() if hasattr(sys.stderr, "isatty") else False
        self.enabled = enabled
        self._t0 = time.monotonic()

    def _emit(self, event: str, **fields: Any) -> None:
        if not self.enabled:
            return
        payload = {
            "event": event,
            "command": self.command,
            "request_id": self.request_id,
            "elapsed_ms": int((time.monotonic() - self._t0) * 1000),
            **fields,
        }
        try:
            sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stderr.flush()
        except Exception:
            pass

    def start(self, **fields: Any) -> None:
        self._emit("start", **fields)

    def progress(self, **fields: Any) -> None:
        self._emit("progress", **fields)

    def complete(self, **fields: Any) -> None:
        self._emit("complete", **fields)

    def warn(self, message: str, **fields: Any) -> None:
        self._emit("warn", message=message, **fields)
