"""
Zhipu (BigModel) Image Generation — OpenAI-compatible REST API.

Env vars:
    ZHIPUAI_API_KEY (required) - Zhipu API key
    ZHIPUAI_MODEL (optional)   - Default model override

Models: cogview-4 (default), cogview-4-250304, glm-image
"""

from providers.base import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    name = "Zhipu"
    env_var = "ZHIPUAI_API_KEY"
    env_model_var = "ZHIPUAI_MODEL"
    api_base = "https://api.z.ai/api/paas/v4/images/generations"
    default_model = "cogview-4"

    models = {"cogview-4", "cogview-4-250304", "glm-image"}

    SIZES = {
        "1:1": "1024x1024", "9:16": "768x1344", "3:4": "864x1152",
        "16:9": "1344x768", "4:3": "1152x864", "2:1": "1440x720",
        "1:2": "720x1440",
    }

    default_size = "1024x1024"


# Module-level singleton
_provider = ZhipuProvider()

# Backward-compatible exports
ZHIPU_MODELS = ZhipuProvider.models
ZHIPU_SIZES = ZhipuProvider.SIZES


def get_zhipu_api_key():
    return _provider.get_api_key()


def resolve_zhipu_size(size_input):
    return _provider.resolve_size(size_input)


def generate_with_zhipu(api_key, model, prompt, size, seed=None):
    return _provider.generate(api_key, model, prompt, size, seed)


def download_zhipu_image(image_url, output_path):
    return _provider.download(image_url, output_path)
