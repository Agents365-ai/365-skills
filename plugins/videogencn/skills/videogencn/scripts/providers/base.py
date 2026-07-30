"""Base classes, exceptions, and utilities for video generation providers."""

import base64
import json
import mimetypes
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Output envelope helpers (agent-native)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "2.0.0"

_stdout_is_tty: bool | None = None


def stdout_is_tty() -> bool:
    """Detect whether stdout is a terminal. Cached after first call."""
    global _stdout_is_tty
    if _stdout_is_tty is None:
        _stdout_is_tty = sys.stdout.isatty()
    return _stdout_is_tty


def resolve_format(flag: str | None) -> str:
    """Resolve output format: explicit flag > TTY detection > table default."""
    if flag in ("json", "table"):
        return flag
    return "table" if stdout_is_tty() else "json"


def emit_json(obj: dict) -> None:
    """Write a JSON object to stdout (one line)."""
    json.dump(obj, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def emit_success(data: Any = None, meta: dict | None = None) -> None:
    """Emit a success envelope to stdout."""
    env: dict = {"ok": True}
    if data is not None:
        env["data"] = data
    m: dict = {"schema_version": SCHEMA_VERSION}
    if meta:
        m.update(meta)
    env["meta"] = m
    emit_json(env)


def emit_error(code: str, message: str, retryable: bool = False,
               data: Any = None, meta: dict | None = None) -> None:
    """Emit an error envelope to stdout (structured, machine-readable)."""
    env: dict = {
        "ok": False,
        "error": {"code": code, "message": message, "retryable": retryable},
    }
    if data is not None:
        env["data"] = data
    m: dict = {"schema_version": SCHEMA_VERSION}
    if meta:
        m.update(meta)
    env["meta"] = m
    emit_json(env)


def emit_progress(event: str, **kwargs) -> None:
    """Emit a JSON progress line to stderr (for agent liveness monitoring)."""
    obj = {"event": event}
    obj.update(kwargs)
    json.dump(obj, sys.stderr, ensure_ascii=False, default=str)
    sys.stderr.write("\n")
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class VideoGenError(Exception):
    """Base exception for video generation errors."""
    exit_code: int = 1


class ConfigError(VideoGenError):
    """Missing API keys, invalid environment configuration."""
    exit_code = 2


class InputError(VideoGenError):
    """Invalid user input: bad mode, unsupported model, file not found, etc."""
    exit_code = 2


class APIError(VideoGenError):
    """HTTP-level errors: network failure, non-JSON response, auth failure."""
    exit_code = 3


class TaskFailedError(VideoGenError):
    """Task ended with FAILED / CANCELED status."""
    exit_code = 4


class TaskTimeoutError(VideoGenError):
    """Poll deadline exceeded before task completed."""
    exit_code = 5


# ---------------------------------------------------------------------------
# Generation request
# ---------------------------------------------------------------------------

@dataclass
class GenerationRequest:
    """All parameters for a video generation job. Provider-agnostic."""
    prompt: str
    mode: str
    model: str
    duration: int = 5
    resolution: str = "1080P"
    ratio: str = "16:9"
    size: str | None = None
    negative: str | None = None
    seed: int | None = None
    no_prompt_extend: bool = False
    no_prompt_optimizer: bool = False
    audio: bool = False
    no_audio: bool = False
    camera_motion: str | None = None


# ---------------------------------------------------------------------------
# Size / ratio lookup
# ---------------------------------------------------------------------------

SIZE_TABLE: dict[tuple[str, str], str] = {
    ("360P", "16:9"): "640*360", ("360P", "9:16"): "360*640",
    ("480P", "16:9"): "832*480", ("480P", "9:16"): "480*832",
    ("540P", "16:9"): "960*540", ("540P", "9:16"): "540*960",
    ("720P", "16:9"): "1280*720", ("720P", "9:16"): "720*1280",
    ("1080P", "16:9"): "1920*1080", ("1080P", "9:16"): "1080*1920",
    ("720P", "1:1"): "720*720", ("1080P", "1:1"): "1080*1080",
    ("720P", "3:4"): "540*720", ("1080P", "3:4"): "810*1080",
    ("720P", "4:3"): "960*720", ("1080P", "4:3"): "1440*1080",
}


def pick_size(req: GenerationRequest, default: str = "1920*1080") -> str:
    """Convert resolution + ratio to a W*H string."""
    return req.size or SIZE_TABLE.get((req.resolution, req.ratio), default)


# ---------------------------------------------------------------------------
# Media validation
# ---------------------------------------------------------------------------

MAX_MEDIA_BYTES = 20 * 1024 * 1024  # 20 MB max per image

ALLOWED_MIME_TYPES = frozenset({
    "image/png", "image/jpeg", "image/jpg",
    "image/webp", "image/bmp", "image/tiff",
})

ALLOWED_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
})


def validate_media_file(path: str) -> Path:
    """Validate a local image file exists, has an allowed extension, and is
    within the size limit. Returns the resolved Path.

    Raises InputError on any validation failure.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise InputError(f"image not found: {path}")

    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InputError(
            f"unsupported image format '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    file_size = p.stat().st_size
    if file_size > MAX_MEDIA_BYTES:
        raise InputError(
            f"image too large ({file_size / 1024 / 1024:.1f} MB). "
            f"Max: {MAX_MEDIA_BYTES / 1024 / 1024:.0f} MB")

    return p


def encode_image_to_data_uri(path: str) -> str:
    """Read a local image file and return a base64 data URI string.

    Validates the file first, then encodes it. Used by providers that accept
    inline base64 images (Wan, HappyHorse, Jimeng, Hunyuan).

    Raises InputError if the file is invalid.
    """
    p = validate_media_file(path)
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    if mime not in ALLOWED_MIME_TYPES:
        mime = "image/png"  # fallback for unrecognized types
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


# ---------------------------------------------------------------------------
# Shared HTTP helpers (raise APIError on failure)
# ---------------------------------------------------------------------------

def safe_json(rsp, label: str = "API") -> dict:
    """Parse response as JSON. Raises APIError on non-JSON responses."""
    try:
        return rsp.json()
    except ValueError:
        content_type = rsp.headers.get("content-type", "unknown")
        body_preview = rsp.text[:500]
        raise APIError(
            f"{label} returned non-JSON response "
            f"(status {rsp.status_code}, content-type: {content_type})\n"
            f"Response preview: {body_preview}")


def safe_request(method: str, url: str, label: str = "API", **kwargs) -> requests.Response:
    """Wrap requests.request with timeout and clean error handling.

    Raises APIError on network failures. Never includes auth headers in messages.
    """
    kwargs.setdefault("timeout", 60)
    try:
        return requests.request(method, url, **kwargs)
    except requests.Timeout:
        raise APIError(f"{label} request timed out after {kwargs['timeout']}s: {url}")
    except requests.ConnectionError as e:
        raise APIError(f"{label} connection failed: {e}")
    except requests.RequestException as e:
        raise APIError(f"{label} request failed: {e}")


# ---------------------------------------------------------------------------
# Terminal status sets for the poll loop
# ---------------------------------------------------------------------------

SUCCESS_STATUSES = frozenset({"SUCCEEDED"})
FAILURE_STATUSES = frozenset({"FAILED", "CANCELED", "UNKNOWN"})


# ---------------------------------------------------------------------------
# Base provider class
# ---------------------------------------------------------------------------

class VideoProvider:
    """Base class for video generation backends.

    Subclasses must implement:
      - name, env_var (class attrs)
      - api_key property
      - api_base property (or _default_api_base)
      - auth_headers()
      - default_models
      - supported_modes
      - check_mode(model, mode)       — raises InputError
      - validate_params(request)      — warns or raises
      - build_body(request, image_url, last_url, refs)
      - submit(body, oss_used)        — raises APIError
      - _poll_request(task_id)
      - _parse_poll_response(rsp)
      - resolve_media(path_or_url, model) — raises InputError
      - list_models_text()
    """

    name: str = "base"
    env_var: str = ""
    model_env_var: str | None = None
    _default_api_base: str = ""

    POLL_INTERVAL: int = 10
    POLL_DEADLINE: int = 1800  # 30 minutes max

    @property
    def api_key(self) -> str:
        raise NotImplementedError(f"{self.name}: api_key property not implemented")

    @property
    def api_base(self) -> str:
        return self._default_api_base

    def auth_headers(self) -> dict:
        raise NotImplementedError(f"{self.name}: auth_headers() not implemented")

    @property
    def default_models(self) -> dict[str, str]:
        raise NotImplementedError(f"{self.name}: default_models not implemented")

    @property
    def supported_modes(self) -> list[str]:
        raise NotImplementedError(f"{self.name}: supported_modes not implemented")

    def check_mode(self, model: str, mode: str) -> None:
        raise NotImplementedError(f"{self.name}: check_mode() not implemented")

    def validate_params(self, req: GenerationRequest) -> None:
        """Validate CLI parameters before submission. Override for provider limits."""
        pass

    def build_body(self, req: GenerationRequest,
                   image_url: Optional[str], last_url: Optional[str],
                   refs: list[tuple[Optional[str], str]]) -> dict:
        raise NotImplementedError(f"{self.name}: build_body() not implemented")

    def submit(self, body: dict, oss_used: bool = False) -> str:
        raise NotImplementedError(f"{self.name}: submit() not implemented")

    # ------------------------------------------------------------------
    # Poll loop (shared; subclasses implement _poll_request + _parse_poll_response)
    # ------------------------------------------------------------------

    def poll(self, task_id: str) -> Optional[str]:
        """Poll until completion or deadline. Returns video_url.

        Raises TaskFailedError if the task ends in a failure state.
        Raises TaskTimeoutError if the deadline is exceeded.
        Raises APIError on HTTP-level poll failures.
        """
        deadline = time.time() + self.POLL_DEADLINE
        while True:
            rsp = self._poll_request(task_id)
            if rsp.status_code != 200:
                body_preview = rsp.text[:300]
                raise APIError(
                    f"poll request failed (HTTP {rsp.status_code}): {body_preview}")
            status, video_url, err_msg = self._parse_poll_response(rsp)
            if status in SUCCESS_STATUSES:
                if not video_url:
                    raise APIError("task succeeded but no video_url in response")
                return video_url
            if status in FAILURE_STATUSES:
                raise TaskFailedError(
                    f"task {task_id} ended with status {status}: {err_msg}")
            if time.time() > deadline:
                raise TaskTimeoutError(
                    f"task {task_id} still {status} after "
                    f"{self.POLL_DEADLINE // 60} minutes. "
                    f"Resume later with: --task-id {task_id}")
            emit_progress("poll", status=status,
                         wait_s=self.POLL_INTERVAL, task_id=task_id)
            time.sleep(self.POLL_INTERVAL)

    def _poll_request(self, task_id: str):
        raise NotImplementedError(f"{self.name}: _poll_request() not implemented")

    def _parse_poll_response(self, rsp) -> tuple[str, Optional[str], str]:
        """Parse poll response -> (status, video_url_or_None, error_message).

        Status MUST be normalized to: SUCCEEDED, FAILED, CANCELED, UNKNOWN,
        or a descriptive intermediate status (e.g. "queued", "processing").
        """
        raise NotImplementedError(f"{self.name}: _parse_poll_response() not implemented")

    def resolve_media(self, path_or_url: str, model: str = "") -> tuple[str, bool]:
        """Turn a path/URL into something the API accepts.

        Returns (resolved_value, needs_extra_header).
        Raises InputError if the file is missing or invalid.
        """
        raise NotImplementedError(f"{self.name}: resolve_media() not implemented")

    def list_models_text(self) -> str:
        raise NotImplementedError(f"{self.name}: list_models_text() not implemented")
