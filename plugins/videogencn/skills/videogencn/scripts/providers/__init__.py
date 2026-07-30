"""Provider registry for video generation backends."""

_providers: dict[str, "VideoProvider"] = {}


def register_providers():
    """Register all built-in providers. Called once at startup."""
    from providers.bailian import BailianProvider
    from providers.hunyuan import HunyuanProvider
    from providers.jimeng import JimengProvider
    from providers.minimax import MiniMaxProvider

    for p in [BailianProvider(), HunyuanProvider(), JimengProvider(), MiniMaxProvider()]:
        _providers[p.name] = p


def get_provider(name: str) -> "VideoProvider":
    """Return a provider by name. Raises KeyError if not found."""
    if not _providers:
        register_providers()
    name = name.lower()
    if name not in _providers:
        raise KeyError(f"Unknown provider '{name}'. Available: {', '.join(_providers)}")
    return _providers[name]


def detect_provider(model: str | None) -> "VideoProvider":
    """Auto-detect provider from model name prefix. Falls back to bailian."""
    if not _providers:
        register_providers()
    if not model:
        return _providers["bailian"]
    m = model.lower()
    if m.startswith(("wan", "pixverse/", "kling/", "vidu/", "happyhorse")):
        return _providers["bailian"]
    if m.startswith(("jimeng", "doubao")):
        return _providers.get("jimeng", _providers["bailian"])
    if m.startswith(("minimax", "hailuo", "video-")):
        return _providers.get("minimax", _providers["bailian"])
    if m.startswith(("hy-video", "hunyuan", "yt-video")):
        return _providers.get("hunyuan", _providers["bailian"])
    return _providers["bailian"]


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    if not _providers:
        register_providers()
    return sorted(_providers.keys())
