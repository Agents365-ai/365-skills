"""TTS backend registry for ttsCN — loaded from data/providers.json."""

import json
import os

# ── Path to the central data file ──────────────────────────────────────────
_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_PROVIDERS_JSON = os.path.join(_DATA_DIR, "providers.json")


def _load_providers():
    """Load provider data from providers.json."""
    if not os.path.exists(_PROVIDERS_JSON):
        raise FileNotFoundError(f"providers.json not found at {_PROVIDERS_JSON}")
    with open(_PROVIDERS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


_PROVIDERS = _load_providers()


def _build_backends():
    """Convert providers.json entries into the runtime BACKENDS dict."""
    backends = {}
    for p in _PROVIDERS["backends"]:
        bid = p["id"]
        # Build a one-line description from available fields
        if "description" in p:
            desc = p["description"]
        else:
            desc = f"{p['name']} ({p['provider']}) — {p['cost']}, {p['voices_count']} voices"
        backends[bid] = {
            "module": "." + bid,
            "env": p["env_vars"],
            "import": (p["pip_package"], p["pip_package"], p["pip_install"]),
            "max_chars": p["max_chars"],
            "max_duration_sec": p["max_duration_sec"],
            "voices_count": p["voices_count"],
            "supports_ssml": p["supports_ssml"],
            "supports_clone": p["supports_clone"],
            "clone_detail": p.get("clone_detail", ""),
            "description": desc,
            "name": p["name"],
            "provider": p["provider"],
            "cost": p["cost"],
            "cost_per_10k": p["cost_per_10k"],
            "max_duration_display": p["max_duration_display"],
            "supports_emotion": p["supports_emotion"],
            "supports_dialects": p["supports_dialects"],
            "languages": p["languages"],
            "streaming": p["streaming"],
            "setup_label": p["setup_label"],
            "get_key_url": p["get_key_url"],
            "tags": p["tags"],
        }
    return backends


def _build_voices():
    """Build VOICES and VOICE_DESCRIPTIONS from providers.json.
    First occurrence of a voice ID wins (don't overwrite descriptions)."""
    voices = {}
    descriptions = {}
    for p in _PROVIDERS["backends"]:
        vlist = []
        for v in p["voices"]:
            vlist.append(v["id"])
            if v["id"] not in descriptions:
                if v.get("style") and v.get("best_for"):
                    descriptions[v["id"]] = f"{v['style']} — {v['best_for']} ({p['name']})"
                elif v.get("style"):
                    descriptions[v["id"]] = f"{v['style']} ({p['name']})"
        voices[p["id"]] = vlist
    return voices, descriptions


BACKENDS = _build_backends()
VOICES, VOICE_DESCRIPTIONS = _build_voices()
TAGS = _PROVIDERS.get("tags", {})


# ── Error classes ──────────────────────────────────────────────────────────
class BackendError(Exception):
    code = "internal_error"
    exit_code = 1
    retryable = False

class UnknownBackendError(BackendError):
    code = "validation_failed"
    exit_code = 2

class MissingPackageError(BackendError):
    code = "tool_missing"
    exit_code = 1
    def __init__(self, message, package=None, install_cmd=None):
        super().__init__(message)
        self.package = package
        self.install_cmd = install_cmd

class MissingEnvVarError(BackendError):
    code = "auth_missing_env"
    exit_code = 3
    retryable = False
    def __init__(self, message, var=None):
        super().__init__(message)
        self.var = var


# ── Resolution functions ───────────────────────────────────────────────────
def resolve_backend():
    env = os.environ.get("TTS_BACKEND")
    if env:
        return env, "env"
    pref = _load_pref("backend")
    if pref:
        return pref, "config"
    return "edge", "default"


def resolve_voice(backend):
    env = os.environ.get("TTS_VOICE")
    if env:
        return env, "env"
    pref = _load_pref("voice")
    if pref:
        return pref, "config"
    defaults = {
        "edge": "zh-CN-XiaoxiaoNeural", "azure": "zh-CN-XiaoxiaoNeural",
        "cosyvoice": "longxiaochun_v3", "doubao": "BV001_streaming",
        "tencent": "101001", "baidu": "0",
        "minimax": "female-shaonv", "xunfei": "xiaoyan",
    }
    return defaults.get(backend, "zh-CN-XiaoxiaoNeural"), "default"


def resolve_speech_rate():
    env = os.environ.get("TTS_RATE")
    if env:
        return env, "env"
    pref = _load_pref("rate")
    if pref:
        return pref, "config"
    return "+5%", "default"


def _load_pref(key):
    for config_path in [
        os.path.join(os.getcwd(), ".ttsCN.json"),
        os.path.expanduser("~/.ttsCN.json"),
    ]:
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    obj = json.load(f)
                if key in obj:
                    return obj[key]
            except (json.JSONDecodeError, OSError):
                pass
    return None


# ── Backend init ───────────────────────────────────────────────────────────
def init_backend(name):
    if name not in BACKENDS:
        raise UnknownBackendError(
            f"Unknown backend '{name}'. Available: {', '.join(BACKENDS.keys())}"
        )
    info = BACKENDS[name]
    mod_name, pkg_name, install_cmd = info["import"]
    try:
        __import__(mod_name)
    except ImportError as e:
        raise MissingPackageError(
            f"'{pkg_name}' not installed. Run: {install_cmd}",
            package=pkg_name, install_cmd=install_cmd,
        ) from e
    for var in info["env"]:
        if not os.environ.get(var):
            raise MissingEnvVarError(f"{var} not set", var=var)
    return _build_config(name)


def _build_config(name):
    config = {}
    voice, voice_src = resolve_voice(name)
    config["voice"] = voice
    config["voice_source"] = voice_src

    if name == "azure":
        config["key"] = os.environ["AZURE_SPEECH_KEY"]
        config["region"] = os.environ.get("AZURE_SPEECH_REGION", "eastasia")
    elif name == "doubao":
        config["appid"] = os.environ["VOLCENGINE_APPID"]
        config["token"] = os.environ["VOLCENGINE_ACCESS_TOKEN"]
        config["cluster"] = os.environ.get("VOLCENGINE_CLUSTER", "volcano_tts")
        config["endpoint"] = os.environ.get(
            "VOLCENGINE_TTS_ENDPOINT", "https://openspeech.bytedance.com/api/v1/tts")
    elif name == "cosyvoice":
        config["model"] = os.environ.get("COSYVOICE_MODEL", "cosyvoice-v3-flash")
    elif name == "tencent":
        config["secret_id"] = os.environ["TENCENT_SECRET_ID"]
        config["secret_key"] = os.environ["TENCENT_SECRET_KEY"]
        config["region"] = os.environ.get("TENCENT_TTS_REGION", "ap-shanghai")
    elif name == "baidu":
        config["app_id"] = os.environ["BAIDU_APP_ID"]
        config["api_key"] = os.environ["BAIDU_API_KEY"]
        config["secret_key"] = os.environ["BAIDU_SECRET_KEY"]
    elif name == "minimax":
        config["api_key"] = os.environ["MINIMAX_API_KEY"]
        config["model"] = os.environ.get("MINIMAX_MODEL", "speech-2.6-hd")
        config["group_id"] = os.environ.get("MINIMAX_GROUP_ID", "")
    elif name == "xunfei":
        config["app_id"] = os.environ["XUNFEI_APP_ID"]
        config["api_key"] = os.environ["XUNFEI_API_KEY"]
        config["api_secret"] = os.environ["XUNFEI_API_SECRET"]
    return config


def get_synthesize_func(name):
    from importlib import import_module
    mod = import_module(BACKENDS[name]["module"], package="ttsCN.scripts.backends")
    return mod.synthesize


def get_max_chars(name):
    return BACKENDS[name]["max_chars"]


def supports_ssml(name):
    return BACKENDS[name]["supports_ssml"]
