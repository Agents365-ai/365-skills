"""Shared base for OpenAI-compatible image generation providers.

All four non-Bailian platforms (Ark, Hunyuan, Zhipu, StepFun) use the same
REST API pattern: POST /images/generations → parse image URL → GET download.
This module eliminates ~200 lines of duplicated HTTP/auth/size logic.
"""

import json
import os
import sys
from http import HTTPStatus
from typing import Optional, Callable

try:
    import requests
except ImportError:
    requests = None  # handled lazily


# ── Exceptions ──────────────────────────────────────────────────────────

class ImageGenError(Exception):
    """Base exception for image generation errors."""
    exit_code: int = 1


class ConfigError(ImageGenError):
    """Missing API key or invalid config."""
    exit_code = 2


class APIError(ImageGenError):
    """Upstream API failure."""
    exit_code = 3


class IOError_(ImageGenError):
    """File I/O or download failure."""
    exit_code = 4


# ── Shared HTTP helpers ─────────────────────────────────────────────────

def safe_request(method, url, headers, json_data=None, timeout=120,
                 label="API") -> requests.Response:
    """Wrap requests with timeout and clean error handling."""
    if requests is None:
        raise ConfigError("'requests' package not installed. Run: pip install requests")
    try:
        rsp = requests.request(method, url, headers=headers, json=json_data,
                               timeout=timeout)
        return rsp
    except requests.Timeout:
        raise APIError(f"{label} request timed out after {timeout}s")
    except requests.ConnectionError as e:
        raise APIError(f"{label} connection failed: {e}")
    except requests.RequestException as e:
        raise APIError(f"{label} request failed: {e}")


def safe_json(rsp, label="API") -> dict:
    """Parse response as JSON. Raises APIError on non-JSON."""
    try:
        return rsp.json()
    except (json.JSONDecodeError, ValueError):
        raise APIError(
            f"{label} returned non-JSON (HTTP {rsp.status_code}): "
            f"{rsp.text[:300]}")


# ── OpenAI-compatible provider base ─────────────────────────────────────

class OpenAICompatibleProvider:
    """Base for providers using OpenAI-compatible /images/generations endpoint.

    Subclasses set class-level config, then inherit generate() + download().
    """

    # Subclass must set:
    name: str = ""
    env_var: str = ""           # e.g. "ARK_API_KEY"
    env_model_var: str = ""     # e.g. "ARK_MODEL"
    api_base: str = ""          # e.g. "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    default_model: str = ""
    models: set[str] = set()
    default_size: str = "1024x1024"

    # Size table: ratio string → pixel dimensions (subclass may override)
    SIZES: dict[str, str] = {}

    # Auth header prefix (default: Bearer)
    auth_prefix: str = "Bearer"

    # Post-processing on request body before POST (hook for subclass overrides)
    @staticmethod
    def tweak_body(body: dict, args) -> dict:
        """Hook: modify the request body before POST. Return modified body."""
        return body

    # Error formatting (hook for subclass overrides)
    @staticmethod
    def format_error(rsp) -> str:
        """Hook: return a human-readable error string from a failed response."""
        try:
            err = rsp.json().get("error", {})
            code = err.get("code", "")
            msg = err.get("message", rsp.text)
            return f"HTTP {rsp.status_code} ({code}): {msg}"
        except (json.JSONDecodeError, ValueError):
            return f"HTTP {rsp.status_code}: {rsp.text[:300]}"

    # ── Public API ──────────────────────────────────────────────────────

    def get_api_key(self) -> str:
        """Read API key from environment. Raises ConfigError if missing."""
        key = os.environ.get(self.env_var)
        if not key:
            raise ConfigError(
                f"{self.env_var} environment variable not set.\n"
                f"Set it with: export {self.env_var}='your-api-key'")
        return key

    def get_default_model(self) -> str | None:
        """Read default model from env var, or use class default."""
        if self.env_model_var:
            return os.environ.get(self.env_model_var) or self.default_model
        return self.default_model

    def resolve_size(self, size_input: str | None, model: str | None = None) -> str:
        """Resolve a size string to pixel dimensions.

        Supports: ratio presets ("16:9"), named presets ("2K"), exact "WxH"/"W*H".
        """
        if not size_input:
            return self.default_size
        if size_input in self.SIZES:
            return self.SIZES[size_input]
        if "*" in size_input or "x" in size_input:
            return size_input.replace("*", "x")
        return size_input  # pass through named presets like "2K"

    def generate(self, api_key: str, model: str, prompt: str, size: str,
                 seed: int | None = None, **extra) -> str:
        """POST /images/generations → return image URL. Raises APIError on failure."""
        headers = {
            "Authorization": f"{self.auth_prefix} {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
        }
        if seed is not None:
            body["seed"] = seed

        # Let subclasses tweak body
        body = self.tweak_body(body, extra)

        rsp = safe_request("POST", self.api_base, headers=headers, json_data=body,
                          label=f"{self.name} generate")
        if rsp.status_code != 200:
            raise APIError(self.format_error(rsp))

        data = safe_json(rsp, f"{self.name} generate")
        try:
            return data["data"][0]["url"]
        except (KeyError, IndexError, TypeError):
            raise APIError(self.format_error(rsp))

    def download(self, image_url: str, output_path: str) -> int:
        """Download an image from URL to output_path. Returns byte count."""
        rsp = safe_request("GET", image_url, headers={},
                          timeout=300, label=f"{self.name} download")
        if rsp.status_code != 200:
            raise APIError(
                f"{self.name} download failed (HTTP {rsp.status_code})")
        path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(rsp.content)
        return len(rsp.content)
