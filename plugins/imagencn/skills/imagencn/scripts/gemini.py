"""
Google Gemini Image Generation — generateContent REST API (international).

Env vars:
    GEMINI_API_KEY (required) - Google AI Studio API key
    GEMINI_MODEL (optional)   - Default model override

Model: gemini-3-pro-image-preview (default).

Unlike the OpenAI-compatible providers, Gemini returns base64 inline image
data instead of a URL, so generate_with_gemini() returns decoded image bytes
and save_gemini_image() writes them to disk (no download step).
"""

import base64
import os

from providers.base import (
    OpenAICompatibleProvider, ConfigError, APIError, safe_request, safe_json,
)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_DEFAULT_MODEL = "gemini-3-pro-image-preview"
GEMINI_DEFAULT_SIZE = "1K"

GEMINI_MODELS = {"gemini-3-pro-image-preview"}

# Named sizes ("512"/"1K"/"2K") map to imageConfig.image_size; ratio presets
# map to imageConfig.aspect_ratio. Gemini has no exact pixel-size parameter.
GEMINI_SIZES = {
    "512": "512", "1K": "1K", "2K": "2K",
    "1:1": "1:1", "16:9": "16:9", "9:16": "9:16",
    "4:3": "4:3", "3:4": "3:4",
}


def get_gemini_api_key():
    """Read GEMINI_API_KEY from environment. Raises ConfigError if missing."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ConfigError(
            "GEMINI_API_KEY environment variable not set.\n"
            "Set it with: export GEMINI_API_KEY='your-api-key'\n"
            "Get a free key at: https://aistudio.google.com/")
    return key


def resolve_gemini_size(size_input):
    """Resolve a size preset to a Gemini named size or aspect ratio."""
    if not size_input:
        return GEMINI_DEFAULT_SIZE
    # Unknown values pass through; the API reports unsupported ones.
    return GEMINI_SIZES.get(size_input, size_input)


def generate_with_gemini(api_key, model, prompt, size, seed=None):
    """POST :generateContent → return decoded image bytes.

    Raises APIError on upstream failure or when no image is returned.
    """
    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    generation_config = {"responseModalities": ["IMAGE", "TEXT"]}
    if size:
        if ":" in size:
            generation_config["imageConfig"] = {"aspect_ratio": size}
        else:
            generation_config["imageConfig"] = {"image_size": size}
    if seed is not None:
        generation_config["seed"] = seed
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    rsp = safe_request("POST", url, headers=headers, json_data=body,
                       label="Gemini generate")
    if rsp.status_code != 200:
        # Gemini errors use the same {"error": {"code", "message"}} shape.
        raise APIError(OpenAICompatibleProvider.format_error(rsp))

    data = safe_json(rsp, "Gemini generate")
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise APIError(
        "Gemini returned no image data (prompt may have been blocked)")


def save_gemini_image(image_bytes, output_path):
    """Write decoded image bytes to output_path. Returns byte count."""
    path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return len(image_bytes)
