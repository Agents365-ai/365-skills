"""
StepFun (阶跃星辰) Image Generation Module

Uses the OpenAI-compatible REST API to call Step-2X and Step-Image-Edit-2.

Env vars:
    STEP_API_KEY (required) - StepFun API key
    STEP_MODEL (optional)   - Default model override

Models:
    step-2x-large        Step-2X Large (0.1 RMB/image, high quality)
    step-image-edit-2    Step Image Edit 2 (0.02 RMB/image, fast, supports
                          negative prompts and text_mode)

API endpoint: https://api.stepfun.com/v1/images/generations
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    requests = None  # handled lazily in generate_with_stepfun

STEPFUN_API_BASE = "https://api.stepfun.com/v1/images/generations"

STEPFUN_MODELS = {
    "step-2x-large",
    "step-image-edit-2",
}

STEPFUN_SIZES = {
    "1:1": "1024x1024",
    "1:1-small": "512x512",
    "16:9": "1280x800",
    "9:16": "800x1280",
}


def get_stepfun_api_key():
    """Read STEP_API_KEY from environment; exit with help if missing."""
    api_key = os.environ.get("STEP_API_KEY")
    if not api_key:
        print("Error: STEP_API_KEY environment variable not set", file=sys.stderr)
        print("\nTo set it:", file=sys.stderr)
        print("  export STEP_API_KEY='your-api-key'", file=sys.stderr)
        print("\nGet API key at:  https://platform.stepfun.com/interface-key", file=sys.stderr)
        sys.exit(1)
    return api_key


def resolve_stepfun_size(size_input):
    """Resolve a size preset or custom dimension string for StepFun.

    StepFun accepts "WxH" pixel strings.  step-2x-large supports
    256x256 to 1024x1024; step-image-edit-2 uses height-first format.
    """
    if not size_input:
        return "1024x1024"
    if size_input in STEPFUN_SIZES:
        return STEPFUN_SIZES[size_input]
    if "*" in size_input:
        return size_input.replace("*", "x")
    return size_input


def generate_with_stepfun(api_key, model, prompt, size, negative_prompt=None):
    """Generate an image via StepFun REST API and return the image URL."""
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
        "n": 1,
    }
    if negative_prompt and model == "step-image-edit-2":
        body["negative_prompt"] = negative_prompt

    try:
        response = requests.post(STEPFUN_API_BASE, headers=headers, json=body,
                                 timeout=120)
    except requests.exceptions.RequestException as e:
        print(f"Error: StepFun API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        _format_stepfun_error(response)
        sys.exit(1)

    data = response.json()
    try:
        return data["data"][0]["url"]
    except (KeyError, IndexError, TypeError):
        _format_stepfun_error(response)
        sys.exit(1)


def _format_stepfun_error(response):
    """Print a human-readable error from a StepFun API response."""
    try:
        err = response.json()
        msg = err.get("error", {}).get("message", "") or response.text
        print(f"Error: StepFun API returned {response.status_code}: {msg}",
              file=sys.stderr)
    except (json.JSONDecodeError, ValueError, AttributeError):
        print(f"Error: StepFun API returned {response.status_code}",
              file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
