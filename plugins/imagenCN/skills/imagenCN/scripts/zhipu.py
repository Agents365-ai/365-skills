"""
Zhipu (BigModel) Image Generation Module

Uses the OpenAI-compatible REST API to call CogView-4 and GLM-Image models.

Env vars:
    ZHIPUAI_API_KEY (required) - Zhipu API key
    ZHIPUAI_MODEL (optional)   - Default model override

Models:
    cogview-4           CogView-4 stable alias (recommended, 0.06 RMB/image)
    cogview-4-250304    CogView-4 fixed snapshot (Mar 2025)
    glm-image           GLM-Image flagship (up to 2048x2048)

API endpoint: https://api.z.ai/api/paas/v4/images/generations
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    requests = None  # handled lazily in generate_with_zhipu

ZHIPU_API_BASE = "https://api.z.ai/api/paas/v4/images/generations"

ZHIPU_MODELS = {
    "cogview-4",
    "cogview-4-250304",
    "glm-image",
}

ZHIPU_SIZES = {
    "1:1": "1024x1024",
    "9:16": "768x1344",
    "3:4": "864x1152",
    "16:9": "1344x768",
    "4:3": "1152x864",
    "2:1": "1440x720",
    "1:2": "720x1440",
}


def get_zhipu_api_key():
    """Read ZHIPUAI_API_KEY from environment; exit with help if missing."""
    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        print("Error: ZHIPUAI_API_KEY environment variable not set", file=sys.stderr)
        print("\nTo set it:", file=sys.stderr)
        print("  export ZHIPUAI_API_KEY='your-api-key'", file=sys.stderr)
        print("\nGet API key at:  https://bigmodel.cn", file=sys.stderr)
        sys.exit(1)
    return api_key


def resolve_zhipu_size(size_input):
    """Resolve a size preset or custom dimension string for Zhipu.

    Zhipu accepts "WxH" pixel strings.  Custom sizes must be in
    512-2048 px, divisible by 16, with total pixels ≤ 2^21.
    """
    if not size_input:
        return "1024x1024"
    if size_input in ZHIPU_SIZES:
        return ZHIPU_SIZES[size_input]
    if "*" in size_input:
        return size_input.replace("*", "x")
    return size_input


def generate_with_zhipu(api_key, model, prompt, size):
    """Generate an image via Zhipu REST API and return the image URL."""
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

    try:
        response = requests.post(ZHIPU_API_BASE, headers=headers, json=body,
                                 timeout=120)
    except requests.exceptions.RequestException as e:
        print(f"Error: Zhipu API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        _format_zhipu_error(response)
        sys.exit(1)

    data = response.json()
    try:
        return data["data"][0]["url"]
    except (KeyError, IndexError, TypeError):
        _format_zhipu_error(response)
        sys.exit(1)


def _format_zhipu_error(response):
    """Print a human-readable error from a Zhipu API response."""
    try:
        err = response.json()
        msg = err.get("error", {}).get("message", "") or response.text
        print(f"Error: Zhipu API returned {response.status_code}: {msg}",
              file=sys.stderr)
    except (json.JSONDecodeError, ValueError, AttributeError):
        print(f"Error: Zhipu API returned {response.status_code}",
              file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
