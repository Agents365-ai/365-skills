#!/usr/bin/env python3
"""
imagencn — Multi-Platform T2I Image Generation Script

Generate images using five Chinese T2I platforms plus Google Gemini:
  - Alibaba Cloud Bailian (DashScope):  Qwen-Image, Wan Series, Z-Image
  - ByteDance Volcano Ark:             Doubao-Seedream series
  - Tencent Hunyuan:                   Hunyuan Image 3.0
  - Zhipu / BigModel:                  CogView-4, GLM-Image
  - StepFun / 阶跃星辰:                 Step-2X, Step-Image-Edit-2
  - Google Gemini (international):     Gemini 3 Pro Image

Usage:
    python generate_image.py "prompt" [output_path]
    python generate_image.py --model wan2.7-image-pro "prompt" output.png
    python generate_image.py --size 2K "prompt" output.png
    python generate_image.py --platform ark "prompt" output.png
    python generate_image.py --format json "prompt" output.png

Environment variables:
    DASHSCOPE_API_KEY (required) - Alibaba Cloud Bailian API Key
    DASHSCOPE_MODEL (optional) - Default model (default: qwen-image-2.0-pro)
    DASHSCOPE_API_BASE (optional) - API endpoint, defaults to China region
    ARK_API_KEY (required for Ark) - Volcano Ark API Key
    HUNYUAN_API_KEY (required for Hunyuan) - Tencent Hunyuan API Key
    ZHIPUAI_API_KEY (required for Zhipu) - Zhipu API Key
    STEP_API_KEY (required for StepFun) - StepFun API Key
    GEMINI_API_KEY (required for Gemini) - Google AI Studio API Key

Exit codes (stable, agent-parseable):
    0 — success
    1 — usage error (bad arguments, unknown model)
    2 — auth / config error (missing or invalid API key)
    3 — API error (upstream failure, rate limit, quota)
    4 — I/O error (cannot write output file, download failed)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from http import HTTPStatus

try:
    import requests
    from dashscope import ImageSynthesis, MultiModalConversation
    from dashscope.aigc.image_generation import ImageGeneration
    import dashscope
except ImportError:
    print("Error: Required packages not installed", file=sys.stderr)
    print("\nInstall with:", file=sys.stderr)
    print("  pip install dashscope requests", file=sys.stderr)
    sys.exit(1)

# Rich output (optional, falls back to plain text)
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    err_console = Console(stderr=True)
    _HAS_RICH = True
except ImportError:
    console = None
    err_console = None
    _HAS_RICH = False

# ── Exit codes (stable, agent-parseable) ──────────────────────────────

EX_USAGE = 1   # bad arguments, unknown model
EX_AUTH  = 2   # missing or invalid API key, config error
EX_API   = 3   # upstream API failure, rate limit, quota
EX_IO    = 4   # file I/O error (write, download)

EXIT_CODE_LABELS = {
    0: "SUCCESS",
    EX_USAGE: "USAGE_ERROR",
    EX_AUTH: "AUTH_ERROR",
    EX_API: "API_ERROR",
    EX_IO: "IO_ERROR",
}

# ── Output format detection ───────────────────────────────────────────

def _detect_format(explicit):
    """Determine output format: 'json' or 'table'.

    Priority: explicit --format flag > TTY detection.
    When stdout is not a terminal, default to JSON (agent-friendly).
    """
    if explicit:
        return explicit
    return "json" if not sys.stdout.isatty() else "table"


def _json_out(data):
    """Emit a JSON document to stdout."""
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


def _emit_error(code, message, retryable=False, **extra):
    """Emit a structured error and exit.

    In JSON mode: {"ok":false,"error":{"code":...,"message":...,"retryable":...}}
    In table mode: human-readable error on stderr.
    """
    if _FMT == "json":
        err_obj = {"code": EXIT_CODE_LABELS.get(code, "UNKNOWN"), "message": message,
                    "retryable": retryable}
        err_obj.update(extra)
        _json_out({"ok": False, "error": err_obj})
    else:
        _err(f"Error: {message}")
    sys.exit(code)


def _emit_success(data, meta=None):
    """Emit a success result.

    In JSON mode: {"ok":true,"data":{...},"meta":{...}}
    In table mode: human-readable summary on stdout.
    """
    m = meta or {}
    if _FMT == "json":
        _json_out({"ok": True, "data": data, "meta": m})
    else:
        for key, val in data.items():
            label = key.replace("_", " ").capitalize()
            print(f"{label}: {val}")


def _emit_dry_run(data):
    """Emit dry-run preview in the current format."""
    if _FMT == "json":
        _json_out({"ok": True, "dry_run": True, "data": data,
                    "meta": {"version": "1.0"}})
    else:
        for key, val in data.items():
            print(f"  {key}: {val}")
        print()
        print("Dry run — no API call made.")


# ── Schema introspection ──────────────────────────────────────────────

def _load_models_json():
    """Load structured model metadata from docs/models.json."""
    script_dir = Path(__file__).parent.resolve()
    candidates = [
        # Repo root: skills/imagencn/scripts/ -> ../../../docs/models.json
        script_dir.parent.parent.parent / "docs" / "models.json",
        # Flat install: scripts/ -> ../docs/models.json
        script_dir.parent / "docs" / "models.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def show_schema(target=None):
    """Progressive schema introspection.

    --schema              → list all platforms (compact)
    --schema platforms    → full platform details
    --schema models       → all models (grouped by platform)
    --schema <model-id>   → single model's full metadata
    """
    data = _load_models_json()
    if data is None:
        _emit_error(EX_USAGE, "Schema data not found: docs/models.json is missing")
        return

    if target is None:
        # Compact top-level listing
        out = {"providers": [], "model_count": 0}
        for p in data["providers"]:
            out["providers"].append({
                "id": p["id"], "name": p["shortName"], "nameCN": p["nameCN"],
                "models": p["modelCount"], "envVar": p["envVar"],
            })
            out["model_count"] += p["modelCount"]
        out["updated"] = data.get("updated", "unknown")
        out["quick_reference"] = data.get("quickReference", [])
        _json_out(out)

    elif target == "platforms":
        _json_out({"providers": data["providers"], "updated": data.get("updated")})

    elif target == "models":
        all_models = []
        for p in data["providers"]:
            for m in p["models"]:
                m["provider"] = p["shortName"]
                m["providerId"] = p["id"]
                m["providerCN"] = p["nameCN"]
                all_models.append(m)
        _json_out({"models": all_models, "total": len(all_models),
                    "updated": data.get("updated")})

    else:
        # Look up a specific model
        for p in data["providers"]:
            for m in p["models"]:
                if m["id"] == target:
                    m["provider"] = p["shortName"]
                    m["providerId"] = p["id"]
                    m["providerCN"] = p["nameCN"]
                    m["envVar"] = p["envVar"]
                    _json_out(m)
                    return
        _emit_error(EX_USAGE, f"Unknown model: {target}",
                     hint="Use --schema models to list all models")


# ── Output helpers ────────────────────────────────────────────────────

def _out(msg, **kwargs):
    """Print to stdout, using rich if available (table mode only)."""
    if _FMT == "json":
        return  # suppress human output in JSON mode
    if _HAS_RICH:
        console.print(msg, **kwargs)
    else:
        print(msg)


def _err(msg):
    """Print to stderr, using rich if available."""
    if _FMT == "json":
        return  # JSON errors are emitted via _emit_error
    if _HAS_RICH:
        err_console.print(msg)
    else:
        print(msg, file=sys.stderr)


# Ensure platform modules are importable from any working directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from providers.base import ImageGenError, APIError  # noqa: E402

# Platform modules (lazy imports — SDK checked inside each generate function)
try:
    from volcano_ark import (  # noqa: E402
        generate_with_ark, ARK_MODELS, ARK_SIZES,
        resolve_ark_size, get_ark_api_key,
    )
except ImportError:
    generate_with_ark = None  # type: ignore[assignment]
    ARK_MODELS = set()
    ARK_SIZES = {}
    resolve_ark_size = None  # type: ignore[assignment]
    get_ark_api_key = None  # type: ignore[assignment]

try:
    from hunyuan import (  # noqa: E402
        generate_with_hunyuan, HUNYUAN_MODELS, HUNYUAN_SIZES,
        resolve_hunyuan_size, get_hunyuan_api_key,
    )
except ImportError:
    generate_with_hunyuan = None  # type: ignore[assignment]
    HUNYUAN_MODELS = set()
    HUNYUAN_SIZES = {}
    resolve_hunyuan_size = None  # type: ignore[assignment]
    get_hunyuan_api_key = None  # type: ignore[assignment]

try:
    from zhipu import (  # noqa: E402
        generate_with_zhipu, ZHIPU_MODELS, ZHIPU_SIZES,
        resolve_zhipu_size, get_zhipu_api_key,
    )
except ImportError:
    generate_with_zhipu = None  # type: ignore[assignment]
    ZHIPU_MODELS = set()
    ZHIPU_SIZES = {}
    resolve_zhipu_size = None  # type: ignore[assignment]
    get_zhipu_api_key = None  # type: ignore[assignment]

try:
    from stepfun import (  # noqa: E402
        generate_with_stepfun, STEPFUN_MODELS, STEPFUN_SIZES,
        resolve_stepfun_size, get_stepfun_api_key,
    )
except ImportError:
    generate_with_stepfun = None  # type: ignore[assignment]
    STEPFUN_MODELS = set()
    STEPFUN_SIZES = {}
    resolve_stepfun_size = None  # type: ignore[assignment]
    get_stepfun_api_key = None  # type: ignore[assignment]

try:
    from gemini import (  # noqa: E402
        generate_with_gemini, save_gemini_image, GEMINI_MODELS, GEMINI_SIZES,
        resolve_gemini_size, get_gemini_api_key,
    )
except ImportError:
    generate_with_gemini = None  # type: ignore[assignment]
    save_gemini_image = None  # type: ignore[assignment]
    GEMINI_MODELS = set()
    GEMINI_SIZES = {}
    resolve_gemini_size = None  # type: ignore[assignment]
    get_gemini_api_key = None  # type: ignore[assignment]


DEFAULT_MODEL = "qwen-image-2.0-pro"
DEFAULT_SIZE = "2048*2048"

# API Endpoints
API_ENDPOINTS = {
    "cn": "https://dashscope.aliyuncs.com/api/v1",
    "sg": "https://dashscope-intl.aliyuncs.com/api/v1",
    "us": "https://dashscope-us.aliyuncs.com/api/v1",
}
DEFAULT_API_BASE = API_ENDPOINTS["cn"]

# Models using ImageSynthesis (legacy Qwen text rendering, prompt parameter)
SYNTHESIS_MODELS = {"qwen-image-plus", "qwen-image-plus-2026-01-09", "qwen-image"}

# Models using ImageGeneration (Wan series, messages format)
GENERATION_MODELS = {
    "wan2.7-image-pro", "wan2.7-image",
    "wan2.6-t2i", "wan2.5-t2i-preview",
    "wan2.2-t2i-flash", "wan2.2-t2i-plus",
    "wanx2.1-t2i-turbo", "wanx2.1-t2i-plus", "wanx2.0-t2i-turbo",
}

# Models using MultiModalConversation (Qwen-Image 2.0 family, native 2K)
MULTIMODAL_MODELS = {
    "qwen-image-2.0-pro", "qwen-image-2.0-pro-2026-06-22",
    "qwen-image-2.0", "qwen-image-max", "qwen-image-max-2025-12-30",
}

# Z-Image models (lightweight, fast) - also use MultiModalConversation
ZIMAGE_MODELS = {"z-image-turbo"}

# Qwen-Image edit models (image editing, require --image) - MultiModalConversation
EDIT_MODELS = {
    "qwen-image-edit-max", "qwen-image-edit-max-2026-01-16",
    "qwen-image-edit-plus",
}

# Size presets for Qwen-Image 2.0 family (native up to 2048x2048)
QWEN2_SIZES = {
    "1:1": "2048*2048",
    "16:9": "2688*1536",
    "9:16": "1536*2688",
    "4:3": "2304*1728",
    "3:4": "1728*2304",
    "1K": "1024*1024",
    "2K": "2048*2048",
}

# Size presets for legacy Qwen-Image / qwen-image-plus
QWEN_SIZES = {
    "1:1": "1328*1328",
    "16:9": "1664*928",
    "9:16": "928*1664",
    "4:3": "1472*1104",
    "3:4": "1104*1472",
}

# Size presets for Z-Image (pixel area must stay within 512x512 to 2048x2048)
ZIMAGE_SIZES = {
    "1:1": "1024*1024",
    "16:9": "1280*720",
    "9:16": "720*1280",
    "2:3": "1024*1536",
    "3:2": "1536*1024",
    "1K": "1024*1024",
}

# Size presets for Wan series. Wan2.7 also accepts shorthand "1K"/"2K"/"4K".
WAN_SIZES = {
    "1:1": "1024*1024",
    "1:1-large": "1280*1280",
    "16:9": "1280*720",
    "9:16": "720*1280",
    "4:3": "1200*900",
    "3:4": "900*1200",
    "2:1": "1440*720",
    "1K": "1K",
    "2K": "2K",
    "4K": "4K",
}


def get_api_key():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        _emit_error(EX_AUTH, "DASHSCOPE_API_KEY environment variable not set",
                     hint="Get a key at https://bailian.console.aliyun.com/")
    return api_key


def get_api_base():
    base = os.environ.get("DASHSCOPE_API_BASE", DEFAULT_API_BASE)
    if base in API_ENDPOINTS:
        return API_ENDPOINTS[base]
    return base


def load_config():
    """Load defaults from config files.

    Priority (highest last): project .imagencn.json > user ~/.imagencn.json.
    Returns a dict with optional keys: platform, model, size.
    """
    config = {}
    # User-level (lower priority, loaded first)
    user_config = Path.home() / ".imagencn.json"
    if user_config.exists():
        try:
            config.update(json.loads(user_config.read_text()))
        except (json.JSONDecodeError, ValueError):
            pass
    # Project-level (higher priority, overrides user)
    project_config = Path(".imagencn.json")
    if project_config.exists():
        try:
            config.update(json.loads(project_config.read_text()))
        except (json.JSONDecodeError, ValueError):
            pass
    return config


def detect_platform(model):
    """Auto-detect platform from model name."""
    if model is None:
        return "dashscope"
    if model in ARK_MODELS:
        return "ark"
    if model in HUNYUAN_MODELS:
        return "hunyuan"
    if model in ZHIPU_MODELS:
        return "zhipu"
    if model in STEPFUN_MODELS:
        return "stepfun"
    if model in GEMINI_MODELS:
        return "gemini"
    return "dashscope"


def get_default_model_for_platform(platform):
    """Return the default model for a given platform."""
    if platform == "ark":
        return os.environ.get("ARK_MODEL", "doubao-seedream-5-0-260128")
    if platform == "hunyuan":
        return os.environ.get("HUNYUAN_MODEL", "hy-image-v3.0")
    if platform == "zhipu":
        return os.environ.get("ZHIPUAI_MODEL", "cogview-4")
    if platform == "stepfun":
        return os.environ.get("STEP_MODEL", "step-2x-large")
    if platform == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-3-pro-image-preview")
    return os.environ.get("DASHSCOPE_MODEL", DEFAULT_MODEL)


def resolve_size(size_input, model, platform=None):
    if platform is None:
        platform = detect_platform(model)

    # Platform-specific size resolution
    if platform == "ark" and resolve_ark_size is not None:
        return resolve_ark_size(size_input, model)
    if platform == "hunyuan" and resolve_hunyuan_size is not None:
        return resolve_hunyuan_size(size_input)
    if platform == "zhipu" and resolve_zhipu_size is not None:
        return resolve_zhipu_size(size_input)
    if platform == "stepfun" and resolve_stepfun_size is not None:
        return resolve_stepfun_size(size_input)
    if platform == "gemini" and resolve_gemini_size is not None:
        return resolve_gemini_size(size_input)

    # DashScope size resolution (unchanged)
    if model in EDIT_MODELS:
        # No default: let the API match the input image dimensions
        if not size_input:
            return None
        return size_input.replace("x", "*")
    if model in MULTIMODAL_MODELS:
        sizes = QWEN2_SIZES
        default = "2048*2048"
    elif model in ZIMAGE_MODELS:
        sizes = ZIMAGE_SIZES
        default = "1024*1024"
    elif model in SYNTHESIS_MODELS:
        sizes = QWEN_SIZES
        default = "1328*1328"
    else:
        sizes = WAN_SIZES
        default = "1024*1024"
    if not size_input:
        return default
    if size_input in sizes:
        return sizes[size_input]
    if "*" in size_input or "x" in size_input:
        resolved = size_input.replace("x", "*")
    else:
        resolved = size_input
    # Validate against per-model limits at the boundary (P5)
    _validate_size(model, resolved)
    return resolved


def make_output_name(platform, model, idempotency_key=None):
    """Generate output filename.

    With idempotency_key: stable filename for reproducible paths.
    Without: platform-model-timestamp.png.
    """
    if idempotency_key:
        safe_key = re.sub(r"[^a-zA-Z0-9._-]", "-", str(idempotency_key))
        safe_key = safe_key.strip("-")[:64]
        safe_model = re.sub(r"[^a-zA-Z0-9._-]", "-", model).strip("-")
        return f"{platform}-{safe_model}-{safe_key}.png"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_model = re.sub(r"[^a-zA-Z0-9._-]", "-", model)
    safe_model = safe_model.strip("-")
    return f"{platform}-{safe_model}-{ts}.png"


def create_output_dir(output_path):
    output_dir = output_path.parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)


def generate_with_synthesis(api_key, model, prompt, size, negative_prompt=None,
                           prompt_extend=True):
    """Generate image using ImageSynthesis (for qwen-image-plus)."""
    params = {
        "api_key": api_key,
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "prompt_extend": prompt_extend,
        "watermark": False,
    }
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    return ImageSynthesis.call(**params)


def generate_with_generation(api_key, model, prompt, size, negative_prompt=None,
                            prompt_extend=True):
    """Generate image using ImageGeneration (for wan2.6-t2i, wan2.7-image, etc)."""
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    params = {
        "api_key": api_key,
        "model": model,
        "messages": messages,
        "n": 1,
        "size": size,
        "prompt_extend": prompt_extend,
        "watermark": False,
    }
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    return ImageGeneration.call(**params)


def generate_with_multimodal(api_key, model, prompt, size, negative_prompt=None, image=None,
                            prompt_extend=True):
    """Generate image using MultiModalConversation (qwen-image-2.0/edit family, z-image)."""
    content = []
    if image:
        content.append({"image": image})
    content.append({"text": prompt})
    messages = [{"role": "user", "content": content}]
    params = {
        "api_key": api_key,
        "model": model,
        "messages": messages,
        "n": 1,
        "prompt_extend": prompt_extend,
        "watermark": False,
    }
    if size:
        params["size"] = size
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    return MultiModalConversation.call(**params)


def extract_image_url(rsp, model):
    """Extract image URL from response based on model type."""
    if model in SYNTHESIS_MODELS:
        if rsp.output and rsp.output.results:
            return rsp.output.results[0].url
    # ImageGeneration and MultiModalConversation share the choices/message format
    if hasattr(rsp, 'output') and rsp.output:
        choices = rsp.output.get('choices', [])
        if choices:
            content = choices[0].get('message', {}).get('content', [])
            for item in content:
                if 'image' in item:
                    return item['image']
    return None


def save_image(url, output_path):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        if _FMT == "json":
            _emit_error(EX_IO, f"Failed to download image: {e}", retryable=True)
        else:
            print(f"Error: Failed to download image: {e}", file=sys.stderr)
        return False


def get_file_size(path):
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def list_models():
    print("Available models:\n")
    print("Qwen-Image 2.0 family (native 2K) [MultiModalConversation API]:")
    for m in sorted(MULTIMODAL_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nQwen-Image edit family (image editing, requires --image) [MultiModalConversation API]:")
    for m in sorted(EDIT_MODELS):
        print(f"  - {m}")
    print("\nZ-Image (lightweight, fast & low-cost) [MultiModalConversation API]:")
    for m in sorted(ZIMAGE_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nQwen-Image legacy (text rendering) [ImageSynthesis API]:")
    for m in sorted(SYNTHESIS_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nWan Series (photorealistic) [ImageGeneration API]:")
    for m in sorted(GENERATION_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nVolcano Ark / ByteDance (Seedream) [OpenAI-compatible API]:")
    for m in sorted(ARK_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nTencent Hunyuan [OpenAI-compatible API]:")
    for m in sorted(HUNYUAN_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nZhipu / BigModel (CogView-4 / GLM-Image) [OpenAI-compatible API]:")
    for m in sorted(ZHIPU_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nStepFun / 阶跃星辰 (Step-2X) [OpenAI-compatible API]:")
    for m in sorted(STEPFUN_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nGoogle Gemini (international) [generateContent API]:")
    for m in sorted(GEMINI_MODELS):
        default = " (default)" if m == DEFAULT_MODEL else ""
        print(f"  - {m}{default}")
    print("\nSize presets:")
    print("  Qwen-Image 2.0:", ", ".join(QWEN2_SIZES.keys()))
    print("  Z-Image:", ", ".join(ZIMAGE_SIZES.keys()))
    print("  Qwen-Image legacy:", ", ".join(QWEN_SIZES.keys()))
    print("  Wan Series:", ", ".join(WAN_SIZES.keys()))
    print("  Volcano Ark:", ", ".join(ARK_SIZES.keys()) if ARK_SIZES else "N/A")
    print("  Tencent Hunyuan:", ", ".join(HUNYUAN_SIZES.keys()) if HUNYUAN_SIZES else "N/A")
    print("  Zhipu:", ", ".join(ZHIPU_SIZES.keys()) if ZHIPU_SIZES else "N/A")
    print("  StepFun:", ", ".join(STEPFUN_SIZES.keys()) if STEPFUN_SIZES else "N/A")
    print("  Google Gemini:", ", ".join(GEMINI_SIZES.keys()) if GEMINI_SIZES else "N/A")
    print("\nAPI endpoints:")
    for region, url in API_ENDPOINTS.items():
        default = " (default)" if region == "cn" else ""
        print(f"  - {region}: {url}{default}")
    print(f"  - Volcano Ark: https://ark.cn-beijing.volces.com/api/v3")
    print(f"  - Tencent Hunyuan: https://tokenhub.tencentmaas.com/v1/images/generations")
    print(f"  - Zhipu: https://api.z.ai/api/paas/v4/images/generations")
    print(f"  - StepFun: https://api.stepfun.com/v1/images/generations")
    print(f"  - Google Gemini: https://generativelanguage.googleapis.com/v1beta/models")


def _validate_size(model, size):
    """Warn if the requested size exceeds known per-model limits.

    In JSON mode, warnings are suppressed (caller should validate first).
    In table mode, warnings go to stderr.
    """
    if not size or _FMT == "json":
        return
    # Ark: Seedream 5.0 does not support 4K
    if model == "doubao-seedream-5-0-260128" and size == "4K":
        _err("[yellow]Warning:[/] Seedream 5.0 max resolution is 3K "
              "(4K requested).  Use --model doubao-seedream-4-5-251128 for 4K."
              if _HAS_RICH else
              "Warning: Seedream 5.0 max is 3K (4K requested). "
              "Use doubao-seedream-4-5-251128 for 4K.")
    # Hunyuan: max 2048 on either side
    if model in HUNYUAN_MODELS and (":" in size):
        parts = size.split(":")
        try:
            w, h = int(parts[0]), int(parts[1])
            if w > 2048 or h > 2048:
                _err("[yellow]Warning:[/] Hunyuan max resolution is 2048px "
                      f"per side (requested {size})."
                      if _HAS_RICH else
                      f"Warning: Hunyuan max is 2048px per side "
                      f"(requested {size}).")
        except (ValueError, IndexError):
            pass
    # Zhipu: 512-2048 px, divisible by 16, total pixels <= 2^21
    if model in ZHIPU_MODELS and ("x" in size):
        try:
            w_str, h_str = size.split("x")
            w, h = int(w_str), int(h_str)
            if w < 512 or w > 2048 or h < 512 or h > 2048:
                _err("[yellow]Warning:[/] Zhipu requires 512-2048 px per side "
                      f"(requested {size})."
                      if _HAS_RICH else
                      f"Warning: Zhipu requires 512-2048 px per side "
                      f"(requested {size}).")
            elif w % 16 != 0 or h % 16 != 0:
                _err("[yellow]Warning:[/] Zhipu requires dimensions divisible "
                      f"by 16 (requested {size})."
                      if _HAS_RICH else
                      f"Warning: Zhipu requires dimensions divisible by 16 "
                      f"(requested {size}).")
            elif w * h > 2_097_152:
                _err("[yellow]Warning:[/] Zhipu total pixels must be <= 2^21 "
                      f"(requested {size} = {w * h} px)."
                      if _HAS_RICH else
                      f"Warning: Zhipu total pixels must be <= 2^21 "
                      f"(requested {size} = {w * h} px).")
        except (ValueError, IndexError):
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate images via DashScope/Ark/Hunyuan/Zhipu/StepFun/Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "A cute cat"
  %(prog)s --model wan2.7-image-pro --size 4K "Mountain landscape photo" ./landscape.png
  %(prog)s --format json --platform ark "Portrait" portrait.png
  %(prog)s --schema           # list all platforms (JSON)
  %(prog)s --schema qwen-image-2.0-pro   # model details (JSON)
        """
    )
    parser.add_argument("prompt", nargs="?", help="Text description of the image")
    parser.add_argument("output", nargs="?", default=None,
                        help="Output file path (default: auto-named)")
    parser.add_argument("--model", "-m", help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--size", "-s", help="Image size as ratio or pixels")
    parser.add_argument("--negative", "-n", help="Negative prompt")
    parser.add_argument("--image", "-i", help="Input image (path or URL) for editing models")
    parser.add_argument("--guidance-scale", type=float, default=None,
                        help="Guidance scale (Volcano Ark only)")
    parser.add_argument("--logo", type=int, choices=[0, 1], default=None,
                        help="Add AI logo: 0=no, 1=yes (Tencent Hunyuan only)")
    parser.add_argument("--no-watermark", action="store_true",
                        help="Disable watermark (Volcano Ark only)")
    parser.add_argument("--platform", "-p",
                        choices=["dashscope", "ark", "hunyuan", "zhipu", "stepfun", "gemini"],
                        help="Target platform (auto-detect from model name by default)")
    parser.add_argument("--revise", type=int, choices=[0, 1], default=None,
                        help="Auto-enhance prompt: 0=off 1=on (Tencent Hunyuan only)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-extend", action="store_true",
                        help="Disable automatic prompt extension (DashScope only)")
    parser.add_argument("--format", choices=["json", "table"],
                        help="Output format (default: auto-detect from TTY)")
    parser.add_argument("--idempotency-key", help="Stable key for reproducible output filename; "
                        "skips generation if output file already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without generating (show what would be called)")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--schema", nargs="?", const=None, default=None,
                        help="Schema introspection: none=platforms, 'models'=all models, "
                             "'<model-id>'=single model details")

    # ── Progressive help (P3): intercept before argparse exits ──
    # --help models → list all models
    # --help <model> → model details via schema
    for i, a in enumerate(sys.argv[1:], start=1):
        if a in ("--help", "-h"):
            if i + 1 < len(sys.argv):
                target = sys.argv[i + 1]
                if target == "models":
                    list_models()
                    sys.exit(0)
                all_model_ids = (SYNTHESIS_MODELS | GENERATION_MODELS | MULTIMODAL_MODELS |
                                 ZIMAGE_MODELS | EDIT_MODELS | ARK_MODELS | HUNYUAN_MODELS |
                                 ZHIPU_MODELS | STEPFUN_MODELS | GEMINI_MODELS)
                if target in all_model_ids:
                    show_schema(target)
                    return
            break

    args = parser.parse_args()

    # ── Global format mode ─────────────────────────────────────────
    global _FMT
    _FMT = _detect_format(args.format)

    # ── Schema introspection (no API call needed) ──────────────────
    if args.schema is not None or (args.schema is None and hasattr(args, 'schema') and
                                    any(a.startswith('--schema') for a in sys.argv[1:])):
        # Re-parse to handle --schema with an argument vs bare --schema
        if args.schema is not None or args.prompt is None:
            target = args.schema  # None for bare --schema, string for --schema <target>
            show_schema(target)
            return

    # ── List models ────────────────────────────────────────────────
    if args.list_models:
        list_models()
        return

    if not args.prompt:
        parser.print_help()
        sys.exit(EX_USAGE)

    # Load config file (CLI args take precedence over config)
    config = load_config()
    config_platform = config.get("platform")
    config_model = config.get("model")
    config_size_arg = config.get("size")

    # Determine platform and model (CLI > config > env > default)
    if args.platform:
        platform = args.platform
        if args.model:
            model = args.model
        else:
            model = config_model or get_default_model_for_platform(platform)
    else:
        model = (args.model or config_model or
                 os.environ.get("DASHSCOPE_MODEL", DEFAULT_MODEL))
        # CLI --model takes precedence over config platform: detect from the
        # model the user explicitly chose, not from a stale config entry.
        if args.model:
            platform = detect_platform(model)
        else:
            platform = config_platform or detect_platform(model)

    all_models = (SYNTHESIS_MODELS | GENERATION_MODELS | MULTIMODAL_MODELS |
                  ZIMAGE_MODELS | EDIT_MODELS | ARK_MODELS | HUNYUAN_MODELS |
                  ZHIPU_MODELS | STEPFUN_MODELS | GEMINI_MODELS)

    # Validate model
    if model not in all_models:
        msg = (f"[yellow]Warning:[/] Unknown model '{model}'. Using platform default"
               if _HAS_RICH else
               f"Warning: Unknown model '{model}'. Using platform default")
        _err(msg)
        model = get_default_model_for_platform(platform)
    elif args.platform or config_platform:
        # If platform is explicit (CLI or config), verify model belongs to it
        effective_platform = args.platform or config_platform
        platform_models = {
            "ark": ARK_MODELS,
            "hunyuan": HUNYUAN_MODELS,
            "zhipu": ZHIPU_MODELS,
            "stepfun": STEPFUN_MODELS,
            "gemini": GEMINI_MODELS,
        }.get(effective_platform)
        if platform_models and model not in platform_models:
            msg = (f"[yellow]Warning:[/] Model '{model}' is not a "
                   f"'{effective_platform}' model. Using platform default"
                   if _HAS_RICH else
                   f"Warning: Model '{model}' is not a "
                   f"'{effective_platform}' model. Using platform default")
            _err(msg)
            model = get_default_model_for_platform(platform)

    size = resolve_size(args.size or config_size_arg, model, platform)

    # Resolve output path (auto-name if not specified)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(make_output_name(platform, model,
                                            idempotency_key=args.idempotency_key))
    create_output_dir(output_path)

    # Idempotency: skip generation if output file already exists
    if args.idempotency_key and output_path.exists() and output_path.stat().st_size > 0:
        file_size = get_file_size(output_path)
        _emit_success({
            "output_path": str(output_path),
            "size_bytes": output_path.stat().st_size,
            "size_human": file_size,
            "model": model,
            "platform": platform,
            "cached": True,
        }, {"version": "1.0", "idempotency": "Returned cached result for key: " + args.idempotency_key})
        return

    # Handle input image (DashScope edit models only)
    input_image = args.image
    if platform == "dashscope" and model in EDIT_MODELS and not input_image:
        _emit_error(EX_USAGE, f"Model '{model}' is an editing model and requires --image")
    if input_image and os.path.exists(input_image):
        input_image = f"file://{Path(input_image).resolve()}"

    # Set API base for DashScope (needed before API calls)
    if platform == "dashscope":
        dashscope.base_http_api_url = get_api_base()

    # Determine display info
    if platform == "ark":
        api_type = "Volcano Ark (OpenAI-compatible)"
        endpoint = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    elif platform == "hunyuan":
        api_type = "Tencent Hunyuan (OpenAI-compatible)"
        endpoint = "https://tokenhub.tencentmaas.com/v1/images/generations"
    elif platform == "zhipu":
        api_type = "Zhipu (OpenAI-compatible)"
        endpoint = "https://api.z.ai/api/paas/v4/images/generations"
    elif platform == "stepfun":
        api_type = "StepFun (OpenAI-compatible)"
        endpoint = "https://api.stepfun.com/v1/images/generations"
    elif platform == "gemini":
        api_type = "Google Gemini (generateContent)"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    elif model in SYNTHESIS_MODELS:
        api_type = "ImageSynthesis"
        endpoint = dashscope.base_http_api_url
    elif model in MULTIMODAL_MODELS or model in ZIMAGE_MODELS or model in EDIT_MODELS:
        api_type = "MultiModalConversation"
        endpoint = dashscope.base_http_api_url
    else:
        api_type = "ImageGeneration"
        endpoint = dashscope.base_http_api_url

    # ── Dry-run output ─────────────────────────────────────────────
    dry_data = {
        "prompt": args.prompt,
        "platform": platform,
        "model": model,
        "api_type": api_type,
        "size": size or "auto",
        "endpoint": endpoint,
        "output": str(output_path),
    }
    if input_image:
        dry_data["input_image"] = args.image

    if args.dry_run:
        _emit_dry_run(dry_data)
        return

    # ── Show preview in table mode ─────────────────────────────────
    if _FMT == "table":
        if _HAS_RICH:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="bold cyan", justify="right")
            table.add_column(style="white")
            for key, val in dry_data.items():
                label = key.replace("_", " ").capitalize()
                table.add_row(label, str(val))
            console.print()
            console.print(table)
            console.print()
        else:
            print("Generating image...")
            for key, val in dry_data.items():
                label = key.replace("_", " ").capitalize()
                print(f"{label}: {val}")
            print()

    # ── Execute generation ─────────────────────────────────────────
    try:
        if platform == "ark":
            if not get_ark_api_key:
                _emit_error(EX_AUTH, "Volcano Ark module not available",
                             hint="Ensure volcano_ark.py is in the scripts directory")
            ark_key = get_ark_api_key()
            image_url = generate_with_ark(
                ark_key, model, args.prompt, size,
                seed=args.seed,
                guidance_scale=args.guidance_scale,
                no_watermark=args.no_watermark,
            )
        elif platform == "hunyuan":
            if not get_hunyuan_api_key:
                _emit_error(EX_AUTH, "Hunyuan module not available")
            hy_key = get_hunyuan_api_key()
            image_url = generate_with_hunyuan(
                hy_key, model, args.prompt, size,
                seed=args.seed,
                revise=args.revise,
                logo=args.logo,
            )
        elif platform == "zhipu":
            if not get_zhipu_api_key:
                _emit_error(EX_AUTH, "Zhipu module not available")
            zp_key = get_zhipu_api_key()
            image_url = generate_with_zhipu(zp_key, model, args.prompt, size,
                                            seed=args.seed)
        elif platform == "stepfun":
            if not get_stepfun_api_key:
                _emit_error(EX_AUTH, "StepFun module not available")
            sf_key = get_stepfun_api_key()
            image_url = generate_with_stepfun(sf_key, model, args.prompt, size,
                                              negative=args.negative)
        elif platform == "gemini":
            if not get_gemini_api_key:
                _emit_error(EX_AUTH, "Gemini module not available")
            gm_key = get_gemini_api_key()
            image_bytes = generate_with_gemini(gm_key, model, args.prompt, size,
                                               seed=args.seed)
        elif model in SYNTHESIS_MODELS:
            api_key = get_api_key()
            rsp = generate_with_synthesis(api_key, model, args.prompt, size,
                                          args.negative,
                                          prompt_extend=not args.no_extend)
        elif model in MULTIMODAL_MODELS or model in ZIMAGE_MODELS or model in EDIT_MODELS:
            api_key = get_api_key()
            rsp = generate_with_multimodal(api_key, model, args.prompt, size,
                                           args.negative,
                                           image=input_image,
                                           prompt_extend=not args.no_extend)
        else:
            api_key = get_api_key()
            rsp = generate_with_generation(api_key, model, args.prompt, size,
                                           args.negative,
                                           prompt_extend=not args.no_extend)
    except ImageGenError as e:
        # ConfigError (missing key) → exit 2 / AUTH_ERROR, not retryable;
        # APIError → exit 3 / API_ERROR, retryable.
        _emit_error(e.exit_code, str(e), retryable=isinstance(e, APIError))
    except Exception as e:
        _emit_error(EX_API, f"API call failed: {e}", retryable=True)

    if platform == "gemini":
        # Gemini returns image bytes directly (no URL to download)
        try:
            save_gemini_image(image_bytes, output_path)
        except Exception as e:
            _emit_error(EX_IO, f"Failed to save image to {output_path}: {e}")
    elif platform in ("ark", "hunyuan", "zhipu", "stepfun"):
        # URL returned directly from generation function
        if not save_image(image_url, output_path):
            _emit_error(EX_IO, f"Failed to save image to {output_path}")
    else:
        # DashScope response handling
        if hasattr(rsp, 'status_code') and rsp.status_code != HTTPStatus.OK:
            msg = f"API returned {rsp.status_code}"
            extra = {"http_status": rsp.status_code}
            if hasattr(rsp, 'code') and rsp.code:
                extra["api_code"] = str(rsp.code)
            if hasattr(rsp, 'message') and rsp.message:
                extra["api_message"] = str(rsp.message)
            _emit_error(EX_API, msg, retryable=True, **extra)

        image_url = extract_image_url(rsp, model)
        if not image_url:
            _emit_error(EX_API, "No image URL in response", retryable=True)

        if not save_image(image_url, output_path):
            _emit_error(EX_IO, f"Failed to save image to {output_path}")

    # ── Success output ─────────────────────────────────────────────
    if output_path.exists() and output_path.stat().st_size > 0:
        file_size = get_file_size(output_path)
        out_data = {
            "output_path": str(output_path),
            "size_bytes": output_path.stat().st_size,
            "size_human": file_size,
            "model": model,
            "platform": platform,
        }
        meta = {"version": "1.0", "idempotency_note":
                "Image generation is not idempotent — each call produces a new image."}
        _emit_success(out_data, meta)
    else:
        _emit_error(EX_IO, f"Failed to save image to {output_path}")


if __name__ == "__main__":
    main()
