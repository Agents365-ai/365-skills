"""
Volcano Ark (ByteDance) Image Generation — OpenAI-compatible REST API.

Env vars:
    ARK_API_KEY (required) - Volcano Ark API key
    ARK_MODEL (optional)   - Default model override

Models: doubao-seedream-5-0-260128 (default), 4.5, 4.0
"""

from providers.base import OpenAICompatibleProvider


class ArkProvider(OpenAICompatibleProvider):
    name = "Ark"
    env_var = "ARK_API_KEY"
    env_model_var = "ARK_MODEL"
    api_base = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    default_model = "doubao-seedream-5-0-260128"

    models = {
        "doubao-seedream-5-0-260128",
        "doubao-seedream-4-5-251128",
        "doubao-seedream-4-0-250828",
    }

    SIZES = {
        "1:1": "2048x2048", "16:9": "2848x1600", "9:16": "1600x2848",
        "4:3": "2304x1728", "3:4": "1728x2304", "3:2": "2496x1664",
        "2:3": "1664x2496",
        "1K": "1K", "2K": "2K", "3K": "3K", "4K": "4K",
    }

    default_size = "2048x2048"

    @staticmethod
    def tweak_body(body, extra):
        if extra.get("guidance_scale") is not None:
            body["guidance_scale"] = extra["guidance_scale"]
        body["watermark"] = extra.get("watermark", True)
        return body

    @staticmethod
    def format_error(rsp):
        import json
        try:
            err = rsp.json().get("error", {})
            code = err.get("code", "")
            msg = err.get("message", rsp.text)
            if code == "ModelNotOpen":
                return (f"Model not activated. Open it in the Ark Console. "
                        f"Details: {msg}")
            return f"HTTP {rsp.status_code} ({code}): {msg}"
        except (json.JSONDecodeError, ValueError):
            return f"HTTP {rsp.status_code}: {rsp.text[:300]}"


# Module-level singleton
_provider = ArkProvider()

# Backward-compatible exports
ARK_MODELS = ArkProvider.models
ARK_SIZES = ArkProvider.SIZES


def get_ark_api_key():
    return _provider.get_api_key()


def resolve_ark_size(size_input, model=None):
    return _provider.resolve_size(size_input, model)


def generate_with_ark(api_key, model, prompt, size, seed=None,
                      guidance_scale=None, no_watermark=False):
    extra = {}
    if guidance_scale is not None:
        extra["guidance_scale"] = guidance_scale
    if no_watermark:
        extra["watermark"] = False
    return _provider.generate(api_key, model, prompt, size, seed, **extra)


def download_ark_image(image_url, output_path):
    return _provider.download(image_url, output_path)
