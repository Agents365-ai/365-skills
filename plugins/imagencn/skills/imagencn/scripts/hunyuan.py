"""
Tencent Hunyuan Image Generation — OpenAI-compatible REST API.

Env vars:
    HUNYUAN_API_KEY (required) - Tencent Hunyuan API key
    HUNYUAN_MODEL (optional)   - Default model override

Model: hy-image-v3.0 (flagship 3.0, strong composition, complex CN prompts up to 8K chars)
"""

from providers.base import OpenAICompatibleProvider


class HunyuanProvider(OpenAICompatibleProvider):
    name = "Hunyuan"
    env_var = "HUNYUAN_API_KEY"
    env_model_var = "HUNYUAN_MODEL"
    api_base = "https://api.hunyuan.cloud.tencent.com/v1/images/generations"
    default_model = "hy-image-v3.0"

    models = {"hy-image-v3.0"}

    SIZES = {
        "1:1": "1024:1024", "16:9": "1920:1080", "9:16": "1080:1920",
        "4:3": "1600:1200", "3:4": "1200:1600",
    }

    default_size = "1024:1024"

    def resolve_size(self, size_input, model=None):
        """Hunyuan uses colon-separated sizes (1024:1024 not 1024x1024)."""
        if not size_input:
            return self.default_size
        if size_input in self.SIZES:
            return self.SIZES[size_input]
        if "*" in size_input:
            return size_input.replace("*", ":")
        if "x" in size_input:
            return size_input.replace("x", ":")
        return size_input

    @staticmethod
    def tweak_body(body, extra):
        if extra.get("revise") is not None:
            body["revise"] = int(extra["revise"])
        if extra.get("logo") is not None:
            body["logo_add"] = int(extra["logo"])
        return body


# Module-level singleton
_provider = HunyuanProvider()

# Backward-compatible exports
HUNYUAN_MODELS = HunyuanProvider.models
HUNYUAN_SIZES = HunyuanProvider.SIZES


def get_hunyuan_api_key():
    return _provider.get_api_key()


def resolve_hunyuan_size(size_input):
    return _provider.resolve_size(size_input)


def generate_with_hunyuan(api_key, model, prompt, size, seed=None, revise=None, logo=None):
    extra = {}
    if revise is not None:
        extra["revise"] = revise
    if logo is not None:
        extra["logo"] = logo
    return _provider.generate(api_key, model, prompt, size, seed, **extra)


def download_hunyuan_image(image_url, output_path):
    return _provider.download(image_url, output_path)
