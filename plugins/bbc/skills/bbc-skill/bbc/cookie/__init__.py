"""Cookie auto-detect orchestrator.

Priority:
1. Explicit cookie file (arg or $BBC_COOKIE_FILE)
2. $BBC_SESSDATA env (direct value)
3. Cached config ~/.config/bbc-skill/cookie.json
4. Auto-detect browsers (by OS)

Returns a dict of {name: value} or raises CookieNotFound.
"""

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from . import chrome_macos, firefox, netscape


class CookieNotFound(Exception):
    pass


CONFIG_PATH = Path.home() / ".config/bbc-skill/cookie.json"


def _from_env_sessdata() -> dict[str, str] | None:
    val = os.environ.get("BBC_SESSDATA", "").strip()
    if val:
        return {"SESSDATA": val}
    return None


def _from_config_file() -> dict[str, str] | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("SESSDATA"):
            return {k: v for k, v in data.items() if isinstance(v, str)}
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _auto_detect(browser_hint: str = "auto") -> tuple[dict[str, str] | None, str | None]:
    """Returns (cookies, source_label)."""
    candidates: list[tuple[str, Callable[[], dict[str, str] | None]]] = []

    if browser_hint in ("auto", "firefox"):
        candidates.append(("firefox", firefox.extract))
    if browser_hint in ("auto", "chrome"):
        if sys.platform == "darwin":
            candidates.append(("chrome (macOS)", lambda: chrome_macos.extract("chrome")))
    if browser_hint in ("auto", "edge"):
        if sys.platform == "darwin":
            candidates.append(("edge (macOS)", lambda: chrome_macos.extract("edge")))

    for label, fn in candidates:
        try:
            cookies = fn()
        except Exception:
            cookies = None
        if cookies and cookies.get("SESSDATA"):
            return cookies, label
    return None, None


def load(
    *,
    cookie_file: str | None = None,
    browser: str = "auto",
) -> tuple[dict[str, str], str]:
    """Load cookies. Returns (cookies, source).

    Raises CookieNotFound if none found.
    """
    # 1. Explicit cookie file
    if cookie_file:
        path = Path(cookie_file).expanduser()
        if not path.exists():
            raise CookieNotFound(f"cookie file not found: {path}")
        cookies = netscape.parse(path)
        if not cookies.get("SESSDATA"):
            raise CookieNotFound(f"no SESSDATA in cookie file: {path}")
        return cookies, f"file:{path}"

    # 2. $BBC_COOKIE_FILE
    env_file = os.environ.get("BBC_COOKIE_FILE", "").strip()
    if env_file:
        path = Path(env_file).expanduser()
        if path.exists():
            cookies = netscape.parse(path)
            if cookies.get("SESSDATA"):
                return cookies, f"env:BBC_COOKIE_FILE={path}"

    # 3. $BBC_SESSDATA direct
    env_cookies = _from_env_sessdata()
    if env_cookies:
        return env_cookies, "env:BBC_SESSDATA"

    # 4. Cached config file
    cached = _from_config_file()
    if cached:
        return cached, f"config:{CONFIG_PATH}"

    # 5. Auto-detect browser
    cookies, source = _auto_detect(browser)
    if cookies:
        return cookies, f"browser:{source}"

    raise CookieNotFound(
        "No cookie found. Provide --cookie-file, set $BBC_SESSDATA, "
        "or log into bilibili.com in Chrome/Firefox/Edge (supported) and retry."
    )


def save_to_config(cookies: dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
