"""
Grok (xAI) Image Generation — OpenAI-compatible REST API.

Env vars:
    XAI_API_KEY (required) - xAI API key
    XAI_MODEL (optional)   - Default model override

Models: grok-imagine-image-quality (default), grok-imagine-image, grok-2-image

The xAI API has no pixel-exact size parameter; sizes are sent as
aspect_ratio ("16:9") or resolution ("2k") instead.
"""

from providers.base import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    name = "Grok"
    env_var = "XAI_API_KEY"
    env_model_var = "XAI_MODEL"
    api_base = "https://api.x.ai/v1/images/generations"
    default_model = "grok-imagine-image-quality"

    models = {"grok-imagine-image", "grok-imagine-image-quality", "grok-2-image"}

    SIZES = {
        "1:1": "1:1",
        "16:9": "16:9",
        "9:16": "9:16",
        "4:3": "4:3",
        "3:4": "3:4",
        "2:1": "2:1",
        "1K": "1k",
        "2K": "2k",
        "4K": "4k",
    }

    default_size = ""

    @staticmethod
    def tweak_body(body, extra):
        # xAI has no "size" param; route to aspect_ratio or resolution instead.
        size = body.pop("size", None)
        if size:
            if ":" in size:
                body["aspect_ratio"] = size
            else:
                body["resolution"] = size.lower()
        return body


# Module-level singleton
_provider = GrokProvider()

# Backward-compatible exports
GROK_MODELS = GrokProvider.models
GROK_SIZES = GrokProvider.SIZES


def get_grok_api_key():
    return _provider.get_api_key()


def resolve_grok_size(size_input):
    return _provider.resolve_size(size_input)


def generate_with_grok(api_key, model, prompt, size, seed=None):
    return _provider.generate(api_key, model, prompt, size, seed)


def download_grok_image(image_url, output_path):
    return _provider.download(image_url, output_path)
