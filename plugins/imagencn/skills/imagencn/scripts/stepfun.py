"""
StepFun (阶跃星辰) Image Generation — OpenAI-compatible REST API.

Env vars:
    STEP_API_KEY (required) - StepFun API key
    STEP_MODEL (optional)   - Default model override

Models: step-2x-large (default), step-image-edit-2
"""

from providers.base import OpenAICompatibleProvider


class StepFunProvider(OpenAICompatibleProvider):
    name = "StepFun"
    env_var = "STEP_API_KEY"
    env_model_var = "STEP_MODEL"
    api_base = "https://api.stepfun.com/v1/images/generations"
    default_model = "step-2x-large"

    models = {"step-2x-large", "step-image-edit-2"}

    SIZES = {
        "1:1": "1024x1024", "1:1-small": "512x512",
        "16:9": "1280x800", "9:16": "800x1280",
    }

    default_size = "1024x1024"

    @staticmethod
    def tweak_body(body, extra):
        if extra.get("negative_prompt"):
            body["negative_prompt"] = extra["negative_prompt"]
        return body


# Module-level singleton
_provider = StepFunProvider()

# Backward-compatible exports
STEPFUN_MODELS = StepFunProvider.models
STEPFUN_SIZES = StepFunProvider.SIZES


def get_stepfun_api_key():
    return _provider.get_api_key()


def resolve_stepfun_size(size_input):
    return _provider.resolve_size(size_input)


def generate_with_stepfun(api_key, model, prompt, size, seed=None, negative=None):
    extra = {}
    if negative:
        extra["negative_prompt"] = negative
    return _provider.generate(api_key, model, prompt, size, seed, **extra)


def download_stepfun_image(image_url, output_path):
    return _provider.download(image_url, output_path)
