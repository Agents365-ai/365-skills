"""
Tencent Hunyuan Image Generation Module

Uses the TokenHub OpenAI-compatible REST API to call
Hunyuan Image models.

Env vars:
    HUNYUAN_API_KEY (required) - Tencent Hunyuan API key (Bearer token)
    HUNYUAN_MODEL (optional)   - Default model override

Models:
    hy-image-v3.0  Hunyuan Image 3.0 (flagship, strongest composition)

API endpoint: https://tokenhub.tencentmaas.com/v1/images/generations
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    requests = None  # handled lazily in generate_with_hunyuan

HUNYUAN_API_BASE = "https://tokenhub.tencentmaas.com/v1/images/generations"

HUNYUAN_MODELS = {
    "hy-image-v3.0",
}

# Hunyuan uses COLON-separated sizes ("1024:1024"), unlike DashScope's "*".
HUNYUAN_SIZES = {
    "1:1": "1024:1024",
    "16:9": "1920:1080",
    "9:16": "1080:1920",
    "4:3": "1600:1200",
    "3:4": "1200:1600",
}


def get_hunyuan_api_key():
    """Read HUNYUAN_API_KEY from environment; exit with help if missing."""
    api_key = os.environ.get("HUNYUAN_API_KEY")
    if not api_key:
        print("Error: HUNYUAN_API_KEY environment variable not set", file=sys.stderr)
        print("\nTo set it:", file=sys.stderr)
        print("  export HUNYUAN_API_KEY='your-api-key'", file=sys.stderr)
        print("\nGet API key at:", file=sys.stderr)
        print("  https://console.cloud.tencent.com/tokenhub/apikey", file=sys.stderr)
        sys.exit(1)
    return api_key


def resolve_hunyuan_size(size_input):
    """Resolve a size preset or custom dimension string for Tencent Hunyuan.

    Hunyuan uses colon-separated sizes ("1024:1024").  This function
    normalises all common input formats (ratio preset, "*", "x") to the
    colon format the Hunyuan API expects.
    """
    if not size_input:
        return "1024:1024"
    if size_input in HUNYUAN_SIZES:
        return HUNYUAN_SIZES[size_input]
    # Normalise: both '*' and 'x' separators -> ':'
    if "*" in size_input:
        return size_input.replace("*", ":")
    if "x" in size_input:
        return size_input.replace("x", ":")
    # Already colon-separated or a raw value — pass through
    return size_input


def generate_with_hunyuan(api_key, model, prompt, size, seed=None,
                          revise=None, logo_add=None):
    """Generate an image via Tencent Hunyuan (TokenHub) and return the URL."""
    if requests is None:
        print("Error: 'requests' package not installed", file=sys.stderr)
        print("\nInstall with:  pip install requests", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    if seed is not None:
        body["seed"] = seed
    if revise is not None:
        body["revise"] = revise
    if logo_add is not None:
        body["logo_add"] = logo_add

    try:
        response = requests.post(HUNYUAN_API_BASE, headers=headers, json=body,
                                 timeout=120)
    except requests.exceptions.RequestException as e:
        print(f"Error: Hunyuan API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        _format_hunyuan_error(response)
        sys.exit(1)

    data = response.json()
    try:
        return data["data"][0]["url"]
    except (KeyError, IndexError, TypeError):
        _format_hunyuan_error(response)
        sys.exit(1)


def _format_hunyuan_error(response):
    """Print a human-readable error from a Hunyuan API response."""
    try:
        err = response.json()
        msg = err.get("error", {}).get("message", "") or response.text
        print(f"Error: Hunyuan API returned {response.status_code}: {msg}",
              file=sys.stderr)
    except (json.JSONDecodeError, ValueError, AttributeError):
        print(f"Error: Hunyuan API returned {response.status_code}",
              file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
