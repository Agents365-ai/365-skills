"""
OpenAI Image Generation — GPT Image models via REST API.

Env vars:
    OPENAI_API_KEY (required) - OpenAI API key
    OPENAI_MODEL (optional)   - Default model override

Models: gpt-image-1 (default), gpt-image-1-mini, gpt-image-1.5, gpt-image-2

GPT image models always return base64-encoded image data (the "url" response
format is not supported), so generate_with_openai() returns decoded bytes and
save_openai_image() writes them to disk (no download step).

Size note: gpt-image-1 accepts only 1024x1024 / 1536x1024 / 1024x1536;
2K/4K presets work on gpt-image-2 (arbitrary WxH, both edges divisible by 16).
"""

import base64
import os

from providers.base import (
    APIError,
    ConfigError,
    OpenAICompatibleProvider,
    safe_json,
    safe_request,
    save_image_bytes,
)

OPENAI_API_BASE = "https://api.openai.com/v1/images/generations"
OPENAI_DEFAULT_MODEL = "gpt-image-1"
OPENAI_DEFAULT_SIZE = "1024x1024"

OPENAI_MODELS = {"gpt-image-1", "gpt-image-1-mini", "gpt-image-1.5", "gpt-image-2"}

OPENAI_SIZES = {
    "1:1": "1024x1024",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
    "4:3": "1344x1024",
    "3:4": "1024x1344",
    "1K": "1024x1024",
    "2K": "2048x2048",
    "4K": "3840x2160",
}


def get_openai_api_key():
    """Read OPENAI_API_KEY from environment. Raises ConfigError if missing."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ConfigError(
            "OPENAI_API_KEY environment variable not set.\n"
            "Set it with: export OPENAI_API_KEY='your-api-key'\n"
            "Get a key at: https://platform.openai.com/api-keys"
        )
    return key


def resolve_openai_size(size_input):
    """Resolve a size preset to pixel dimensions (WxH, not W*H)."""
    if not size_input:
        return OPENAI_DEFAULT_SIZE
    return OPENAI_SIZES.get(size_input, size_input.replace("*", "x"))


def generate_with_openai(api_key, model, prompt, size, quality=None):
    """POST /images/generations → return decoded image bytes.

    Raises APIError on upstream failure or when no image is returned.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "output_format": "png",
    }
    if quality:
        body["quality"] = quality

    rsp = safe_request(
        "POST",
        OPENAI_API_BASE,
        headers=headers,
        json_data=body,
        label="OpenAI generate",
    )
    if rsp.status_code != 200:
        raise APIError(OpenAICompatibleProvider.format_error(rsp))

    data = safe_json(rsp, "OpenAI generate")
    try:
        b64 = data["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError) as e:
        raise APIError(OpenAICompatibleProvider.format_error(rsp)) from e
    return base64.b64decode(b64)


def save_openai_image(image_bytes, output_path):
    """Write decoded image bytes to output_path. Returns byte count."""
    return save_image_bytes(image_bytes, output_path)
