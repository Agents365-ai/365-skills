"""
Volcano Ark (ByteDance) Image Generation Module

Uses the OpenAI-compatible REST API to call Doubao-Seedream models.

Env vars:
    ARK_API_KEY (required) - Volcano Ark API key
    ARK_MODEL (optional)   - Default model override

Models:
    doubao-seedream-5-0-260128  Seedream 5.0  (latest, 2K/3K, PNG/JPEG)
    doubao-seedream-4-5-251128  Seedream 4.5  (2K/4K)
    doubao-seedream-4-0-250828  Seedream 4.0  (1K/2K/4K)

API endpoint: https://ark.cn-beijing.volces.com/api/v3/images/generations
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    requests = None  # handled lazily in generate_with_ark

ARK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

ARK_MODELS = {
    "doubao-seedream-5-0-260128",
    "doubao-seedream-4-5-251128",
    "doubao-seedream-4-0-250828",
}

ARK_SIZES = {
    "1:1": "2048x2048",
    "16:9": "2848x1600",
    "9:16": "1600x2848",
    "4:3": "2304x1728",
    "3:4": "1728x2304",
    "3:2": "2496x1664",
    "2:3": "1664x2496",
    "1K": "1K",
    "2K": "2K",
    "3K": "3K",
    "4K": "4K",
}


def get_ark_api_key():
    """Read ARK_API_KEY from environment; exit with help if missing."""
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("Error: ARK_API_KEY environment variable not set", file=sys.stderr)
        print("\nTo set it:", file=sys.stderr)
        print("  export ARK_API_KEY='your-api-key'", file=sys.stderr)
        print("\nGet API key at:", file=sys.stderr)
        print("  https://console.volcengine.com/ark/region:ark+cn-beijing/apikey", file=sys.stderr)
        sys.exit(1)
    return api_key


def resolve_ark_size(size_input, model=None):
    """Resolve a size preset or custom dimension string for Volcano Ark.

    Ark accepts preset strings ("1K", "2K", "3K", "4K") or custom
    pixel dimensions in the format "WxH" (e.g. "2048x2048").
    """
    if not size_input:
        return "2048x2048"
    if size_input in ARK_SIZES:
        return ARK_SIZES[size_input]
    # Normalise: both '*' and 'x' are acceptable separators; Ark uses 'x'
    if "*" in size_input or "x" in size_input:
        return size_input.replace("*", "x")
    # Return as-is (preset string like "2K")
    return size_input


def generate_with_ark(api_key, model, prompt, size, seed=None,
                      guidance_scale=None, no_watermark=False):
    """Generate an image via Volcano Ark REST API and return the image URL."""
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
        "response_format": "url",
        "watermark": not no_watermark,
    }
    if seed is not None:
        body["seed"] = seed
    if guidance_scale is not None:
        body["guidance_scale"] = guidance_scale

    try:
        response = requests.post(ARK_API_BASE, headers=headers, json=body,
                                 timeout=120)
    except requests.exceptions.RequestException as e:
        print(f"Error: Ark API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        _format_ark_error(response)
        sys.exit(1)

    data = response.json()
    try:
        return data["data"][0]["url"]
    except (KeyError, IndexError, TypeError):
        _format_ark_error(response)
        sys.exit(1)


def _format_ark_error(response):
    """Print a human-readable error from an Ark API response."""
    try:
        err = response.json().get("error", {})
        code = err.get("code", "")
        msg = err.get("message", response.text)
        if code == "ModelNotOpen":
            print(f"Error: Model not activated. Open it in the Ark Console",
                  file=sys.stderr)
            print(f"  Details: {msg}", file=sys.stderr)
        else:
            print(f"Error: Ark API returned {response.status_code} "
                  f"({code}): {msg}", file=sys.stderr)
    except (json.JSONDecodeError, ValueError, AttributeError):
        print(f"Error: Ark API returned {response.status_code}",
              file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
