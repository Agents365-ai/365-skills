"""
Black Forest Labs (FLUX) Image Generation — asynchronous REST API.

Env vars:
    BFL_API_KEY (required) - Black Forest Labs API key
    BFL_MODEL (optional)   - Default model override

Models: flux-2-pro-preview (default, rolling), flux-2-pro (pinned snapshot),
flux-2-max (highest quality, search-grounding).

FLUX.2 uses an asynchronous pattern: POST /v1/<model> returns an id and a
polling_url; poll the polling_url until status is "Ready", then download
result.sample (a signed URL valid for 10 minutes).

Note: FLUX 3 image generation is not yet publicly available (early access
only, no public API endpoint as of 2026-08).
"""

import os
import time

from providers.base import (
    APIError,
    ConfigError,
    safe_json,
    safe_request,
)

BFL_API_BASE = "https://api.bfl.ai/v1"
BFL_DEFAULT_MODEL = "flux-2-pro-preview"
BFL_DEFAULT_SIZE = "1024x1024"

BFL_MODELS = {"flux-2-pro-preview", "flux-2-pro", "flux-2-max"}

# Ratio presets map to pixel dimensions; 1K/2K are named sizes.
BFL_SIZES = {
    "1:1": "1024x1024",
    "16:9": "1344x768",
    "9:16": "768x1344",
    "4:3": "1152x864",
    "3:4": "864x1152",
    "2:1": "1440x720",
    "1:2": "720x1440",
    "1K": "1024x1024",
    "2K": "2048x2048",
}

# Non-terminal statuses to keep polling
_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 120

_TERMINAL_ERROR_STATUSES = {
    "Error",
    "Task not found",
    "Request Moderated",
    "Content Moderated",
}


def get_bfl_api_key():
    """Read BFL_API_KEY from environment. Raises ConfigError if missing."""
    key = os.environ.get("BFL_API_KEY")
    if not key:
        raise ConfigError(
            "BFL_API_KEY environment variable not set.\n"
            "Set it with: export BFL_API_KEY='your-api-key'\n"
            "Get a key at: https://api.bfl.ai/"
        )
    return key


def resolve_bfl_size(size_input):
    """Resolve a size preset to pixel dimensions (WxH)."""
    if not size_input:
        return BFL_DEFAULT_SIZE
    if size_input in BFL_SIZES:
        return BFL_SIZES[size_input]
    return size_input.replace("*", "x")


def _poll_result(polling_url, api_key):
    """Poll the BFL polling_url until Ready. Returns the result dict.

    Raises APIError on moderated/error statuses or timeout.
    """
    headers = {"x-key": api_key}
    start = time.time()
    while True:
        rsp = safe_request(
            "GET", polling_url, headers=headers, timeout=30, label="FLUX poll"
        )
        if rsp.status_code != 200:
            raise APIError(
                f"FLUX poll failed (HTTP {rsp.status_code}): {rsp.text[:300]}"
            )
        data = safe_json(rsp, "FLUX poll")
        status = data.get("status", "")
        if status == "Ready":
            return data.get("result") or {}
        if status in _TERMINAL_ERROR_STATUSES:
            raise APIError(f"FLUX generation failed: {status}")
        if time.time() - start > _POLL_TIMEOUT:
            raise APIError(f"FLUX generation timed out after {_POLL_TIMEOUT}s")
        time.sleep(_POLL_INTERVAL)


def generate_with_bfl(api_key, model, prompt, size, seed=None):
    """POST /v1/<model> → poll → return image URL.

    Raises APIError on upstream failure, moderation, or timeout.
    """
    try:
        width, _, height = resolve_bfl_size(size).partition("x")
        width, height = int(width), int(height)
    except ValueError:
        raise APIError(
            f"invalid size for FLUX: '{size}' (expected WxH pixels, e.g. 1024x1024)"
        ) from None
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
    }
    if seed is not None:
        body["seed"] = seed

    headers = {
        "x-key": api_key,
        "Content-Type": "application/json",
    }
    rsp = safe_request(
        "POST",
        f"{BFL_API_BASE}/{model}",
        headers=headers,
        json_data=body,
        timeout=30,
        label="FLUX generate",
    )
    if rsp.status_code != 200:
        raise APIError(
            f"FLUX generate failed (HTTP {rsp.status_code}): {rsp.text[:300]}"
        )

    data = safe_json(rsp, "FLUX generate")
    polling_url = data.get("polling_url")
    if not polling_url:
        raise APIError("FLUX returned no polling_url")

    result = _poll_result(polling_url, api_key)
    sample = result.get("sample")
    if not sample:
        raise APIError("FLUX returned no image URL in result")
    return sample
