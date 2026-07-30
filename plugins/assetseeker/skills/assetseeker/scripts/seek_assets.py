#!/usr/bin/env python3
"""Asset Seeker — Search free commercial-use creative assets online.

Queries Pexels, Unsplash, Pixabay, Iconify, Freesound, and Google Fonts
through their public APIs. Iconify works without any API key.

Usage:
    python seek_assets.py sources                    # List sources + key status
    python seek_assets.py search photo "mountain"    # Search photos
    python seek_assets.py search icon "laptop"       # Search icons
    python seek_assets.py search video "city"        # Search video footage
    python seek_assets.py search sfx "whoosh"        # Search sound effects
    python seek_assets.py search font "bold sans"    # Search fonts
    python seek_assets.py download <url> -o out.jpg  # Download asset
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
import re
from typing import Any

# Playwright is optional — only needed for scraper sources (Mixkit etc.)
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    HAS_PLAYWRIGHT = True
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
    HAS_PLAYWRIGHT = False

# For OAuth2 flow (Freesound auth)
import hashlib
import http.server
import secrets
import threading
import webbrowser
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_CONFIG = {
    "pexels": {
        "label": "Pexels",
        "types": ["photo", "video"],
        "base": "https://api.pexels.com",
        "env_key": "PEXELS_API_KEY",
        "free_tier": "200 req/hr, 20k/month",
        "china_access": True,
        "license": "No attribution required",
    },
    "unsplash": {
        "label": "Unsplash",
        "types": ["photo"],
        "base": "https://api.unsplash.com",
        "env_key": "UNSPLASH_ACCESS_KEY",
        "free_tier": "50 req/hr (demo)",
        "china_access": True,
        "license": "Attribution appreciated",
    },
    "pixabay": {
        "label": "Pixabay",
        "types": ["photo", "video"],
        "base": "https://pixabay.com/api",
        "env_key": "PIXABAY_API_KEY",
        "free_tier": "Free",
        "china_access": True,
        "license": "No attribution required",
        "note": "Music has NO API — web download only",
    },
    "iconify": {
        "label": "Iconify",
        "types": ["icon"],
        "base": "https://api.iconify.design",
        "env_key": None,  # No key needed
        "free_tier": "Unlimited, no registration",
        "china_access": True,
        "license": "Varies by icon set (mostly MIT / CC-BY / Apache)",
    },
    "freesound": {
        "label": "Freesound",
        "types": ["sfx", "music"],
        "base": "https://freesound.org/apiv2",
        "env_key": "FREESOUND_API_KEY",  # client_id; FREESOUND_TOKEN is the actual auth token
        "free_tier": "Free with OAuth token",
        "china_access": True,
        "license": "Check per item (mostly CC0 / CC-BY)",
        "oauth": True,  # Uses OAuth2 — check for token, not just key
    },
    "google-fonts": {
        "label": "Google Fonts",
        "types": ["font"],
        "base": "https://www.googleapis.com/webfonts/v1",
        "env_key": "GOOGLE_FONTS_API_KEY",
        "free_tier": "Free (or offline index — no key needed)",
        "china_access": True,
        "license": "OFL (Open Font License)",
        "always_available": True,  # Has local offline index fallback
    },
    "noun-project": {
        "label": "Noun Project",
        "types": ["icon"],
        "base": "https://api.thenounproject.com/v2",
        "env_key": "NOUN_PROJECT_KEY",
        "free_tier": "5,000/month",
        "china_access": True,
        "license": "Per-icon license",
    },
    "mixkit": {
        "label": "Mixkit (Playwright scraper)",
        "types": ["video", "sfx", "music", "template"],
        "base": "https://mixkit.co",
        "env_key": None,
        "free_tier": "Free, no attribution (use --source mixkit)",
        "china_access": True,
        "license": "No attribution required",
        "scraper": True,
        "pip_deps": ["playwright"],
    },
    "undraw": {
        "label": "unDraw (Playwright scraper)",
        "types": ["illustration"],
        "base": "https://undraw.co",
        "env_key": None,
        "free_tier": "Free, no attribution (use --source undraw)",
        "china_access": True,
        "license": "No attribution required",
        "scraper": True,
        "pip_deps": ["playwright"],
    },
    "100font": {
        "label": "100font (Playwright scraper)",
        "types": ["font"],
        "base": "https://www.100font.com",
        "env_key": None,
        "free_tier": "Free, 820+ verified fonts (use --source 100font)",
        "china_access": True,
        "license": "Varies per font (mostly OFL / free commercial)",
        "scraper": True,
        "pip_deps": ["playwright"],
    },
    "storyset": {
        "label": "Storyset (Playwright scraper)",
        "types": ["illustration"],
        "base": "https://storyset.com",
        "env_key": None,
        "free_tier": "Free, editable illustrations (use --source storyset)",
        "china_access": True,
        "license": "Free with attribution (Freepik license)",
        "scraper": True,
        "pip_deps": ["playwright"],
    },
}

# Maps user-facing type -> list of source names in priority order
TYPE_TO_SOURCES: dict[str, list[str]] = {
    "photo": ["pexels", "unsplash", "pixabay"],
    "icon": ["iconify", "noun-project"],
    "illustration": [],
    "video": ["pexels", "pixabay"],
    "sfx": ["freesound"],
    "music": ["freesound"],
    "font": ["google-fonts"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_key(source: str) -> str | None:
    """Get API key for a source from env var, or None."""
    conf = SOURCE_CONFIG.get(source, {})
    env_key = conf.get("env_key")
    if not env_key:
        return None  # source doesn't need one
    return os.environ.get(env_key)


def _api_get(url: str, headers: dict | None = None) -> Any:
    """Make a GET request and return parsed JSON."""
    merged = {"User-Agent": "assetseeker/1.0"}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, headers=merged)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body[:300]}
    except urllib.error.URLError as e:
        return {"error": f"Request failed: {e.reason}"}


def _download_file(url: str, output: str) -> bool:
    """Download a file from url to output path. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "assetseeker/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            Path(output).write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"Download error: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Source-specific search functions
# ---------------------------------------------------------------------------


def _search_pexels(args: argparse.Namespace) -> list[dict]:
    """Search Pexels photos or videos."""
    key = _get_key("pexels")
    if not key:
        return [{"error": "PEXELS_API_KEY not set. Get one at https://www.pexels.com/api/"}]

    if args.type == "video":
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(args.keyword)}&per_page={args.max_results}"
    else:
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(args.keyword)}&per_page={args.max_results}"
        if args.orientation:
            url += f"&orientation={args.orientation}"
        if args.color:
            url += f"&color={args.color}"

    # Pexels uses camelCase for orientation; remap if needed
    if args.orientation == "landscape":
        url = url.replace("&orientation=landscape", "&orientation=landscape")
    elif args.orientation == "portrait":
        url = url.replace("&orientation=portrait", "&orientation=portrait")
    elif args.orientation == "square":
        url = url.replace("&orientation=square", "&orientation=square")

    data = _api_get(url, {"Authorization": key})
    if "error" in data:
        return [data]

    items = data.get("photos") or data.get("videos") or []
    results: list[dict] = []
    for item in items:
        if args.type == "video":
            # Pick best-quality video file
            video_files = sorted(item.get("video_files", []), key=lambda f: f.get("width", 0) * f.get("height", 0), reverse=True)
            best = video_files[0] if video_files else {}
            results.append({
                "id": item.get("id"),
                "source": "pexels",
                "type": "video",
                "url": item.get("url", ""),
                "preview": item.get("image", ""),
                "download_url": best.get("link", ""),
                "width": best.get("width"),
                "height": best.get("height"),
                "duration": item.get("duration"),
                "photographer": item.get("user", {}).get("name", ""),
                "photographer_url": item.get("user", {}).get("url", ""),
            })
        else:
            results.append({
                "id": item.get("id"),
                "source": "pexels",
                "type": "photo",
                "url": item.get("url", ""),
                "preview": item.get("src", {}).get("large", ""),
                "download_url": item.get("src", {}).get("original", ""),
                "width": item.get("width"),
                "height": item.get("height"),
                "photographer": item.get("photographer", ""),
                "photographer_url": item.get("photographer_url", ""),
                "alt": item.get("alt", ""),
                "avg_color": item.get("avg_color", ""),
            })
    return results


def _search_unsplash(args: argparse.Namespace) -> list[dict]:
    """Search Unsplash photos."""
    key = _get_key("unsplash")
    if not key:
        return [{"error": "UNSPLASH_ACCESS_KEY not set. Get one at https://unsplash.com/developers"}]

    url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(args.keyword)}&per_page={args.max_results}"
    if args.orientation:
        url += f"&orientation={args.orientation}"

    data = _api_get(url, {"Authorization": f"Client-ID {key}"})
    if "error" in data:
        return [data]

    results: list[dict] = []
    for item in data.get("results", []):
        results.append({
            "id": item.get("id"),
            "source": "unsplash",
            "type": "photo",
            "url": item.get("links", {}).get("html", ""),
            "preview": item.get("urls", {}).get("regular", ""),
            "download_url": item.get("urls", {}).get("full", ""),
            "width": item.get("width"),
            "height": item.get("height"),
            "photographer": item.get("user", {}).get("name", ""),
            "photographer_url": f"https://unsplash.com/@{item.get('user', {}).get('username', '')}",
            "alt": item.get("alt_description") or item.get("description") or "",
            "color": item.get("color", ""),
            "likes": item.get("likes", 0),
        })
    return results


def _search_pixabay(args: argparse.Namespace) -> list[dict]:
    """Search Pixabay photos or videos."""
    key = _get_key("pixabay")
    if not key:
        return [{"error": "PIXABAY_API_KEY not set. Get one at https://pixabay.com/api/docs/"}]

    if args.type == "video":
        url = f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(args.keyword)}&per_page={args.max_results}"
    else:
        url = f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(args.keyword)}&per_page={args.max_results}"
    if args.orientation:
        url += f"&orientation={args.orientation}"

    data = _api_get(url)
    if "error" in data:
        return [data]

    items = data.get("hits", [])
    results: list[dict] = []
    for item in items:
        if args.type == "video":
            # Pick medium or large quality
            videos = item.get("videos", {})
            best = videos.get("large") or videos.get("medium") or videos.get("small") or {}
            results.append({
                "id": item.get("id"),
                "source": "pixabay",
                "type": "video",
                "url": item.get("pageURL", ""),
                "preview": videos.get("medium", {}).get("thumbnail", ""),
                "download_url": best.get("url", ""),
                "width": best.get("width"),
                "height": best.get("height"),
                "duration": item.get("duration"),
                "user": item.get("user", ""),
                "tags": item.get("tags", ""),
            })
        else:
            results.append({
                "id": item.get("id"),
                "source": "pixabay",
                "type": "photo",
                "url": item.get("pageURL", ""),
                "preview": item.get("webformatURL", ""),
                "download_url": item.get("largeImageURL", ""),
                "width": item.get("imageWidth"),
                "height": item.get("imageHeight"),
                "user": item.get("user", ""),
                "tags": item.get("tags", ""),
                "likes": item.get("likes", 0),
                "downloads": item.get("downloads", 0),
            })
    return results


def _search_iconify(args: argparse.Namespace) -> list[dict]:
    """Search Iconify icons — no API key needed."""
    keyword = args.keyword.strip()
    if len(keyword) < 2:
        return [{"error": "Icon search needs at least 2 characters"}]

    # Iconify search API: /search?query=...&limit=...
    url = f"https://api.iconify.design/search?query={urllib.parse.quote(keyword)}&limit={args.max_results}"
    data = _api_get(url)
    if "error" in data:
        return [data]

    results: list[dict] = []
    for item in data.get("icons", []):
        prefix, _, name = item.partition(":")
        results.append({
            "id": item,
            "source": "iconify",
            "type": "icon",
            "prefix": prefix,
            "name": name,
            "svg_url": f"https://api.iconify.design/{item}.svg",
            "usage_html": f'<span class="iconify" data-icon="{item}"></span>',
            "preview_url": f"https://api.iconify.design/{item}.svg?width=64&height=64",
            "collections": data.get("collections", {}),
        })

    # Attach collection name for each prefix
    collections = data.get("collections", {})
    for r in results:
        col = collections.get(r["prefix"], {})
        r["collection_name"] = col.get("name", r["prefix"])
        r["collection_license"] = col.get("license", {}).get("title", "Unknown")

    return results


def _search_freesound(args: argparse.Namespace) -> list[dict]:
    """Search Freesound for SFX or music."""
    key = _get_key("freesound")
    token = os.environ.get("FREESOUND_TOKEN", "")
    if not key and not token:
        return [{"error": "Set FREESOUND_API_KEY or FREESOUND_TOKEN. Run: seek_assets.py auth freesound"}]

    auth_header = f"Bearer {token}" if token else f"Token {key}"
    url = f"https://freesound.org/apiv2/search/text/?query={urllib.parse.quote(args.keyword)}&page_size={min(args.max_results, 30)}&fields=id,name,url,previews,license,username,duration,download,tags"

    # Filter for music vs sfx
    if args.type == "music":
        url += "&filter=tag:music"
    elif args.type == "sfx":
        url += "&filter=tag:sfx"

    data = _api_get(url, {"Authorization": auth_header})
    if "error" in data:
        return [data]

    results: list[dict] = []
    for item in data.get("results", []):
        previews = item.get("previews", {})
        results.append({
            "id": item.get("id"),
            "source": "freesound",
            "type": args.type,
            "name": item.get("name", ""),
            "url": item.get("url", ""),
            "preview_url": previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3", ""),
            "download_url": item.get("download", ""),
            "duration": item.get("duration"),
            "license": item.get("license", ""),
            "username": item.get("username", ""),
            "tags": item.get("tags", []),
        })
    return results


def _search_google_fonts(args: argparse.Namespace) -> list[dict]:
    """Search Google Fonts — uses local offline index, or API if key is set."""
    key = _get_key("google-fonts")

    if key:
        return _search_google_fonts_api(args, key)

    # Fall back to local offline index (no key needed)
    return _search_google_fonts_local(args)


def _search_google_fonts_api(args: argparse.Namespace, key: str) -> list[dict]:
    """Search via Google Fonts API (needs API key)."""
    url = f"https://www.googleapis.com/webfonts/v1/webfonts?key={key}&sort=popularity"
    data = _api_get(url)
    if "error" in data:
        return [data]

    keyword = args.keyword.lower()
    items = data.get("items", [])
    matched: list[dict] = []
    for f in items:
        family = f.get("family", "").lower()
        category = (f.get("category", "") or "").lower()
        if keyword in family or keyword in category:
            variants = f.get("variants", [])
            matched.append({
                "family": f.get("family"),
                "source": "google-fonts",
                "type": "font",
                "category": f.get("category", ""),
                "variants": variants,
                "variants_count": len(variants),
                "subsets": f.get("subsets", []),
                "version": f.get("version", ""),
                "last_modified": f.get("lastModified", ""),
                "css_link": f"https://fonts.googleapis.com/css2?family={urllib.parse.quote(f.get('family', '').replace(' ', '+'))}",
                "popularity": f.get("popularity", ""),
            })
        if len(matched) >= args.max_results:
            break
    return matched


def _search_google_fonts_local(args: argparse.Namespace) -> list[dict]:
    """Search from a pre-built local index of 1940 Google Fonts families."""
    # Locate index relative to this script
    script_dir = Path(__file__).resolve().parent
    index_path = script_dir.parent / "references" / "google_fonts_index.json"

    if not index_path.is_file():
        return [{"error": "Font index not found. Set GOOGLE_FONTS_API_KEY for live search."}]

    try:
        fonts = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [{"error": f"Failed to load font index: {e}"}]

    keyword = args.keyword.lower().strip()
    matched: list[dict] = []

    # Score: exact family match > family starts with keyword > word in family > substring > category
    for f in fonts:
        family = f.get("family", "")
        family_lower = family.lower()
        category = (f.get("category", "") or "").lower()
        variants = f.get("variants", [])

        score = 0
        if keyword == family_lower:
            score = 100
        elif family_lower.startswith(keyword):
            score = 80
        elif f" {keyword}" in family_lower or f"{keyword} " in family_lower:
            score = 60
        elif keyword in family_lower:
            score = 40
        elif keyword in category:
            score = 10
        else:
            continue

        matched.append({
            "family": f.get("family"),
            "source": "google-fonts",
            "type": "font",
            "category": f.get("category", ""),
            "variants": variants,
            "variants_count": len(variants),
            "subsets": f.get("subsets", []),
            "designers": f.get("designers", []),
            "last_modified": f.get("lastModified", ""),
            "css_link": f"https://fonts.googleapis.com/css2?family={urllib.parse.quote(f.get('family', '').replace(' ', '+'))}",
            "_score": score,
        })

    # Sort by internal score descending, then take top N
    matched.sort(key=lambda f: f.get("_score", 0), reverse=True)
    # Strip internal scoring field from output
    for m in matched:
        m.pop("_score", None)
    return matched[:args.max_results]


def _search_noun_project(args: argparse.Namespace) -> list[dict]:
    """Search Noun Project icons (requires OAuth1 — simplified to key+secret)."""
    key = os.environ.get("NOUN_PROJECT_KEY")
    secret = os.environ.get("NOUN_PROJECT_SECRET")
    if not key or not secret:
        return [{"error": "NOUN_PROJECT_KEY / NOUN_PROJECT_SECRET not set. Get them at https://thenounproject.com/developers/"}]

    # Noun Project uses OAuth1; do a simple GET with the key as query param for the public API
    url = f"https://api.thenounproject.com/v2/icon?query={urllib.parse.quote(args.keyword)}&limit={min(args.max_results, 20)}"
    # Basic auth via OAuth1 is complex; use the simpler approach with key+secret as query params
    # Many Noun Project API users just use the key/secret via OAuth1 library
    # For simplicity, we'll return a helpful error if not achievable
    return [{
        "error": "Noun Project requires OAuth1 signing. Use Iconify for zero-config icon search instead.",
        "hint": "Iconify has 300k+ icons and works without any API key.",
    }]


def _search_mixkit(args: argparse.Namespace) -> list[dict]:
    """Search Mixkit for video footage via Playwright scraper."""
    if not HAS_PLAYWRIGHT:
        return [{"error": "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"}]

    keyword = args.keyword.strip()
    asset_type = args.type

    # Map asset type to Mixkit URL path
    type_paths = {
        "video": "free-stock-video",
        "sfx": "free-sound-effects",
        "music": "free-stock-music",
        "template": "free-video-templates",
    }
    path = type_paths.get(asset_type, "free-stock-video")
    base_url = f"https://mixkit.co/{path}/"

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(base_url, timeout=20000)
            page.wait_for_timeout(2000)

            # Use the search form (URL param ?s= does not trigger JS search)
            search_input = page.query_selector('input[type="search"], input[placeholder*="search" i], [class*=search] input[type="text"]')
            if search_input:
                search_input.fill(keyword)
                search_input.press("Enter")
                page.wait_for_timeout(4000)
            else:
                # Fallback: try URL-based search
                page.goto(f"{base_url}?s={urllib.parse.quote(keyword)}", timeout=20000)
                page.wait_for_timeout(4000)

            cards = page.query_selector_all(".item-grid__item")
            for card in cards[:args.max_results]:
                try:
                    link_el = card.query_selector(".item-grid-video-player__overlay-link")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""
                    title = (link_el.inner_text() or "").strip()

                    img_el = card.query_selector(".item-grid-video-player img")
                    thumbnail = img_el.get_attribute("src") if img_el else ""

                    # Extract video ID from href: /free-stock-video/slug-12345/
                    m = re.search(r"-(\d+)/?$", href)
                    vid = m.group(1) if m else ""

                    result: dict = {
                        "id": vid,
                        "source": "mixkit",
                        "type": asset_type,
                        "title": title,
                        "url": f"https://mixkit.co{href}" if href.startswith("/") else href,
                        "thumbnail": thumbnail,
                        "license": "No attribution required",
                    }

                    if asset_type == "video" and vid:
                        result["download_url"] = f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4"
                        result["download_urls"] = {
                            "360p": f"https://assets.mixkit.co/videos/{vid}/{vid}-360.mp4",
                            "720p": f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4",
                        }

                    if title:
                        results.append(result)
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        return [{"error": f"Mixkit scraper failed: {e}", "hint": "Try again or use --source pexels for video search"}]

    if not results:
        return [{"error": f"No Mixkit {asset_type} results for '{keyword}'"}]
    return results


def _search_undraw(args: argparse.Namespace) -> list[dict]:
    """Search unDraw for SVG illustrations via Playwright scraper."""
    if not HAS_PLAYWRIGHT:
        return [{"error": "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"}]

    keyword = (args.keyword or "").strip().lower()
    accent_color = getattr(args, "color", None)  # optional hex color for recoloring

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://undraw.co/illustrations", timeout=20000)
            page.wait_for_timeout(4000)

            buttons = page.query_selector_all(".appcontainer button")
            for btn in buttons:
                try:
                    svg = btn.query_selector("svg")
                    if not svg:
                        continue
                    w_str = svg.get_attribute("width") or "0"
                    try:
                        if float(w_str) < 100:
                            continue  # skip tiny UI icons
                    except ValueError:
                        continue

                    title = (btn.inner_text() or "").strip()
                    if not title:
                        continue

                    # Filter by keyword
                    if keyword and keyword not in title.lower():
                        continue

                    # Extract full SVG markup
                    svg_html = page.evaluate("el => el.outerHTML", svg)
                    if not svg_html:
                        continue

                    # Recolor if requested: replace the most prominent accent fill
                    if accent_color:
                        # Find all hex colors and replace the first non-gray one
                        base_color = "#6c63ff"  # unDraw default accent
                        alt_colors = re.findall(r"#[0-9a-fA-F]{6}", svg_html)
                        # Use the most frequent non-gray color as the accent
                        from collections import Counter
                        color_counts = Counter(c for c in alt_colors if c.lower() not in ("#ffffff", "#000000", "#090814", "#f2f2f2", "#e6e6e6", "#d6d6e3"))
                        if color_counts:
                            base_color = color_counts.most_common(1)[0][0]
                        svg_html = svg_html.replace(base_color, f"#{accent_color.lstrip('#')}")

                    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

                    results.append({
                        "id": slug,
                        "source": "undraw",
                        "type": "illustration",
                        "title": title,
                        "url": f"https://undraw.co/illustrations",
                        "svg": svg_html,
                        "svg_bytes": len(svg_html),
                        "download_url": f"https://undraw.co/illustrations",  # no direct URL; save SVG locally
                        "color_hint": "Use --color HEX to change the accent color",
                    })

                    if len(results) >= args.max_results:
                        break
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        return [{"error": f"unDraw scraper failed: {e}"}]

    if not results:
        return [{"error": f"No unDraw illustrations matching '{keyword}' (searched 40 total)"}]
    return results


def _search_100font(args: argparse.Namespace) -> list[dict]:
    """Search 100font.com for Chinese free commercial-use fonts via Playwright."""
    if not HAS_PLAYWRIGHT:
        return [{"error": "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"}]

    keyword = args.keyword.strip()
    base_url = "https://www.100font.com"

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Search
            page.goto(base_url, timeout=15000)
            page.wait_for_timeout(2000)
            search_input = page.query_selector('input[placeholder*="字体"]')
            if search_input:
                search_input.fill(keyword)
                search_input.press("Enter")
                page.wait_for_timeout(3000)
            else:
                page.goto(f"{base_url}/search.htm?keyword={urllib.parse.quote(keyword)}", timeout=15000)
                page.wait_for_timeout(3000)

            # Extract thread items from search results
            thread_links = page.query_selector_all('a[href*="thread-"]')
            seen: set[str] = set()
            for link in thread_links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href.startswith("thread-"):
                        continue
                    if href in seen:
                        continue
                    seen.add(href)

                    title = (link.inner_text() or "").strip()
                    if not title or len(title) < 4:
                        continue
                    # Skip FAQ/articles — font listings start with 【
                    if not title.startswith("【"):
                        continue

                    # Extract tags from title (e.g., "简体 繁体 宋体 时尚 OFL")
                    tags = re.findall(r"[一-鿿\w]+", title.split("】")[-1]) if "】" in title else []

                    results.append({
                        "id": href.replace("thread-", "").replace(".htm", ""),
                        "source": "100font",
                        "type": "font",
                        "family": title.split("】")[0].lstrip("【") if "】" in title else title,
                        "title": title,
                        "url": f"{base_url}/{href}",
                        "tags": tags[:8],
                        "license_hint": "OFL" if "OFL" in title else "Check thread page",
                    })

                    if len(results) >= args.max_results:
                        break
                except Exception:
                    continue

            # If user wants detailed download info, visit the first result's page
            if results and getattr(args, "detail", False):
                for r in results[:3]:  # Only fetch detail for top 3
                    try:
                        page.goto(r["url"], timeout=10000)
                        page.wait_for_timeout(1500)
                        all_links = page.query_selector_all("a")
                        for l in all_links:
                            href = l.get_attribute("href") or ""
                            for host in ["pan.quark.cn", "pan.baidu.com", "lanzou", "aliyundrive", "123pan"]:
                                if host in href:
                                    r.setdefault("download_urls", []).append(href)
                        # Get license info
                        body = (page.inner_text("body") or "")[:2000]
                        lic_match = re.search(r"(SIL Open Font License[\s\S]{0,100})", body)
                        if lic_match:
                            r["license"] = lic_match.group(1).strip()[:120]
                    except Exception:
                        continue
                # Go back to results list for consistency
                # (results page no longer valid after navigation, but we already have data)

            browser.close()
    except Exception as e:
        return [{"error": f"100font scraper failed: {e}"}]

    if not results:
        return [{"error": f"No 100font fonts matching '{keyword}'"}]
    return results


def _search_storyset(args: argparse.Namespace) -> list[dict]:
    """Search Storyset for editable illustrations via Playwright."""
    if not HAS_PLAYWRIGHT:
        return [{"error": "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"}]

    keyword = args.keyword.strip()
    search_url = f"https://storyset.com/search?q={urllib.parse.quote(keyword)}"

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(search_url, timeout=20000)
            page.wait_for_timeout(4000)

            links = page.query_selector_all('a[href*="/illustration/"]')
            seen_names: set[str] = set()
            for link in links:
                href = link.get_attribute("href") or ""
                parts = href.strip("/").split("/")
                if len(parts) < 2:
                    continue
                name, style = parts[-2], parts[-1]

                # Deduplicate — each illustration has 5 style variants, keep first
                if name in seen_names:
                    continue
                seen_names.add(name)

                title = name.replace("-", " ").title()

                # Find thumbnail image
                img = link.query_selector("img")
                thumbnail = img.get_attribute("src") if img else ""

                # Storyset style URLs
                styles = ["rafiki", "bro", "amico", "pana", "cuate"]
                style_urls = {
                    s: f"https://storyset.com/illustration/{name}/{s}"
                    for s in styles
                }

                results.append({
                    "id": name,
                    "source": "storyset",
                    "type": "illustration",
                    "title": title,
                    "url": f"https://storyset.com{href}",
                    "thumbnail": thumbnail,
                    "styles": style_urls,
                    "license": "Free with attribution (Freepik license)",
                })

                if len(results) >= args.max_results:
                    break

            browser.close()
    except Exception as e:
        return [{"error": f"Storyset scraper failed: {e}"}]

    if not results:
        return [{"error": f"No Storyset illustrations matching '{keyword}'"}]
    return results


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

SEARCHERS = {
    "pexels": _search_pexels,
    "unsplash": _search_unsplash,
    "pixabay": _search_pixabay,
    "iconify": _search_iconify,
    "freesound": _search_freesound,
    "google-fonts": _search_google_fonts,
    "noun-project": _search_noun_project,
    "mixkit": _search_mixkit,
    "undraw": _search_undraw,
    "100font": _search_100font,
    "storyset": _search_storyset,
}


def _available_sources(asset_type: str) -> list[str]:
    """Return configured sources for the given type, filtering by API key availability.
    Always includes sources that don't need a key (Iconify).
    """
    candidates = TYPE_TO_SOURCES.get(asset_type, [])
    available: list[str] = []
    for src in candidates:
        conf = SOURCE_CONFIG.get(src, {})
        if conf.get("always_available") or conf.get("env_key") is None:
            # Local fallback or no key needed — always available
            available.append(src)
        elif conf.get("oauth"):
            # OAuth2 source — need either the key or the token
            env = conf.get("env_key", "")
            if env and (_get_key(src) or os.environ.get("FREESOUND_TOKEN")):
                available.append(src)
        elif _get_key(src):
            available.append(src)
    return available


def _source_status() -> dict[str, dict]:
    """Return status of all sources."""
    status: dict[str, dict] = {}
    for name, conf in SOURCE_CONFIG.items():
        env = conf.get("env_key")
        always_avail = conf.get("always_available") or (env is None and not conf.get("scraper"))
        if always_avail:
            has = True
        elif conf.get("scraper"):
            has = "scraper"  # Playwright-based, always usable when Playwright installed
        elif env:
            has = bool(os.environ.get(env))
        else:
            has = False
        status[name] = {
            "label": conf["label"],
            "types": conf["types"],
            "has_api_key": has,
            "free_tier": conf.get("free_tier", ""),
            "china_access": conf.get("china_access", True),
            "license": conf.get("license", ""),
            "note": conf.get("note", ""),
            "env_var": env,
        }
    return status


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_sources(args: argparse.Namespace) -> None:
    """List sources and their API key status."""
    status = _source_status()
    if args.type:
        status = {k: v for k, v in status.items() if args.type in v["types"]}

    if args.format == "text":
        print(f"{'Source':<18} {'Types':<22} {'Key?':<6} {'Free Tier':<28} {'China':<6}")
        print("-" * 82)
        for name, s in status.items():
            types = ",".join(s["types"])
            key = "✓" if s["has_api_key"] else ("N/A" if s["env_var"] is None else "✗")
            china = "✓" if s["china_access"] else "⚠️"
            print(f"{name:<18} {types:<22} {key:<6} {s['free_tier']:<28} {china:<6}")
        print(f"\n{len(status)} sources listed")
    else:
        print(json.dumps(status, ensure_ascii=False, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    """Search assets across configured sources."""
    asset_type = args.type

    if asset_type not in TYPE_TO_SOURCES:
        valid = ", ".join(TYPE_TO_SOURCES.keys())
        print(json.dumps({"error": f"Unknown type: {asset_type}", "valid_types": valid.split(", ")}, ensure_ascii=False))
        sys.exit(1)

    # Determine which sources to use
    if args.source:
        sources = [args.source]
    else:
        sources = _available_sources(asset_type)

    if not sources:
        print(json.dumps({
            "error": f"No API keys configured for {asset_type} sources.",
            "hint": "Set at least PEXELS_API_KEY (https://www.pexels.com/api/). Iconify works for icons without any key.",
            "available_sources": _source_status(),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    all_results: dict[str, list[dict]] = {}
    total = 0

    for src in sources:
        searcher = SEARCHERS.get(src)
        if not searcher:
            continue
        try:
            results = searcher(args)
        except Exception as e:
            results = [{"error": f"{src}: {e}"}]
        all_results[src] = results
        total += len(results) if not any("error" in r for r in results) else 0

    output: dict[str, Any] = {
        "keyword": args.keyword,
        "type": asset_type,
        "total_results": total,
        "sources_queried": sources,
    }

    if args.format == "text":
        _print_search_text(args.keyword, asset_type, all_results)
    else:
        for src, results in all_results.items():
            conf = SOURCE_CONFIG.get(src, {})
            output[src] = {
                "label": conf.get("label", src),
                "count": len(results),
                "license": conf.get("license", ""),
                "results": results,
            }
        print(json.dumps(output, ensure_ascii=False, indent=2))


def _print_search_text(keyword: str, asset_type: str, all_results: dict[str, list[dict]]) -> None:
    """Human-readable search output."""
    print(f"Search: {asset_type} \"{keyword}\"\n")
    for src, results in all_results.items():
        conf = SOURCE_CONFIG.get(src, {})
        label = conf.get("label", src)
        has_err = any("error" in r for r in results)
        if has_err:
            for r in results:
                if "error" in r:
                    print(f"[{label}] ⚠️  {r['error']}")
                    if "hint" in r:
                        print(f"       → {r['hint']}")
            print()
            continue

        print(f"─── {label} ({len(results)} results) | License: {conf.get('license', 'N/A')} ───")
        for i, r in enumerate(results, 1):
            if asset_type == "photo":
                print(f"  {i}. {r.get('alt', r.get('tags', 'Photo'))[:60]}")
                print(f"     {r.get('width')}×{r.get('height')} | {r.get('photographer') or r.get('user', '')}")
                print(f"     Preview: {r.get('preview', '')[:100]}")
                print(f"     Download: {r.get('download_url', '')[:100]}")
            elif asset_type == "video":
                dur = r.get("duration", 0) or 0
                title = r.get("title") or r.get("alt", "")
                res = f"{r.get('width')}×{r.get('height')}" if r.get("width") else ""
                dur_str = f" | {dur:.0f}s" if dur else ""
                author = f" | by {r.get('photographer') or r.get('user', '')}" if r.get("photographer") or r.get("user") else ""
                print(f"  {i}. {title[:60]}")
                print(f"     {r.get('url', '')[:80]}")
                if res or dur:
                    print(f"     {res}{dur_str}{author}")
                # Show multi-quality download options
                dl_urls = r.get("download_urls", {})
                if dl_urls:
                    for quality, url in dl_urls.items():
                        print(f"     [{quality}] {url[:100]}")
                else:
                    print(f"     Download: {r.get('download_url', '')[:100]}")
            elif asset_type == "icon":
                print(f"  {i}. {r.get('id', '')} [{r.get('collection_name', '')}]")
                print(f"     SVG: {r.get('svg_url', '')}")
                print(f"     License: {r.get('collection_license', '')}")
            elif asset_type in ("sfx", "music"):
                dur = r.get("duration", 0)
                print(f"  {i}. {r.get('name', '')[:60]} ({dur:.1f}s)")
                print(f"     License: {r.get('license', '')} | by {r.get('username', '')}")
                print(f"     Preview: {r.get('preview_url', '')[:100]}")
            elif asset_type == "font":
                # Google Fonts format
                if r.get("category"):
                    print(f"  {i}. {r.get('family', '')} ({r.get('category', '')})")
                    print(f"     Variants: {', '.join(r.get('variants', []))}")
                    print(f"     CSS: {r.get('css_link', '')}")
                # 100font format
                else:
                    title = r.get('title', '') or r.get('family', '')
                    tags = ', '.join(r.get('tags', []))
                    print(f"  {i}. {title}")
                    if tags:
                        print(f"     Tags: {tags}")
                    print(f"     Page: {r.get('url', '')}")
                    dl_urls = r.get('download_urls', [])
                    if dl_urls:
                        for du in dl_urls:
                            print(f"     Download: {du}")
            elif asset_type == "illustration":
                title = r.get('title', '')
                source = r.get('source', '')
                print(f"  {i}. {title}")
                if r.get("svg_bytes"):
                    print(f"     SVG: {r.get('svg_bytes', 0)} bytes | {r.get('color_hint', '')}")
                if r.get("styles"):
                    styles = ', '.join(r["styles"].keys())
                    print(f"     Styles: {styles} | License: {r.get('license', '')}")
                print(f"     URL: {r.get('url', '')}")
        print()


def cmd_auth(args: argparse.Namespace) -> None:
    """Run OAuth2 flow for a source (currently supports Freesound)."""
    if args.source != "freesound":
        print(json.dumps({"error": f"OAuth not supported for '{args.source}'. Only 'freesound'."}))
        sys.exit(1)

    client_id = os.environ.get("FREESOUND_API_KEY", "")
    if not client_id:
        print(json.dumps({"error": "Set FREESOUND_API_KEY (your Freesound client_id) first."}))
        sys.exit(1)

    state = secrets.token_urlsafe(16)

    auth_url = (
        f"https://freesound.org/apiv2/oauth2/authorize/?"
        f"client_id={urllib.parse.quote(client_id)}"
        f"&response_type=code"
        f"&state={state}"
    )

    print(f"Opening browser for Freesound authorization...", file=sys.stderr)
    webbrowser.open(auth_url)

    print("\nAfter authorizing, Freesound will redirect you. Check the browser URL bar.", file=sys.stderr)
    print('Look for "code=" in the URL and copy the value after it.', file=sys.stderr)
    code = input("\nPaste authorization code: ").strip()
    if not code:
        print(json.dumps({"error": "No code provided."}))
        sys.exit(1)

    # Exchange code for access token
    token_url = "https://freesound.org/apiv2/oauth2/access_token/"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
    }).encode("utf-8")
    req = urllib.request.Request(token_url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"error": f"Token exchange failed: HTTP {e.code}", "detail": body[:300]}))
        sys.exit(1)

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)

    if access_token:
        print(json.dumps({
            "status": "ok",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "hint": f"Set: export FREESOUND_TOKEN={access_token}",
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "No access_token in response", "raw": token_data}))


def cmd_download(args: argparse.Namespace) -> None:
    """Download a single asset from a URL."""
    url = args.url
    output = args.output
    if not output:
        # Infer from URL
        output = url.split("/")[-1].split("?")[0] or "download"

    print(f"Downloading {url} → {output} …", file=sys.stderr)
    ok = _download_file(url, output)
    if ok:
        size = Path(output).stat().st_size
        print(json.dumps({"status": "ok", "file": output, "size_bytes": size}, ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "file": output, "message": "Download failed"}, ensure_ascii=False))
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Asset Seeker — Search free commercial-use creative assets online",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  seek_assets.py sources
  seek_assets.py search photo "mountain sunset"
  seek_assets.py search icon "laptop" --format text
  seek_assets.py search video "city traffic" --source pexels
  seek_assets.py search sfx "whoosh" --max 5
  seek_assets.py search font "bold sans"
  seek_assets.py download https://example.com/photo.jpg -o bg.jpg
        """,
    )

    sub = parser.add_subparsers(dest="command")

    # sources
    p_src = sub.add_parser("sources", help="List sources and API key status")
    p_src.add_argument("--type", help="Filter by asset type (photo, icon, video, sfx, font)")
    p_src.add_argument("--format", choices=["json", "text"], default="text")
    p_src.set_defaults(func=cmd_sources)

    # search
    p_search = sub.add_parser("search", help="Search for assets")
    p_search.add_argument("type", help=f"Asset type: {', '.join(TYPE_TO_SOURCES.keys())}")
    p_search.add_argument("keyword", help="Search keyword")
    p_search.add_argument("--max", type=int, dest="max_results", default=10, help="Max results per source (default: 10)")
    p_search.add_argument("--source", help="Specific source to query (e.g., pexels, iconify)")
    p_search.add_argument("--orientation", choices=["landscape", "portrait", "square"], help="Photo/video orientation filter")
    p_search.add_argument("--color", help="Photo color filter (Pexels/Pixabay only)")
    p_search.add_argument("--format", choices=["json", "text"], default="json")
    p_search.set_defaults(func=cmd_search)

    # auth
    p_auth = sub.add_parser("auth", help="Run OAuth2 flow for a source")
    p_auth.add_argument("source", help="Source name (e.g., freesound)")
    p_auth.set_defaults(func=cmd_auth)

    # download
    p_dl = sub.add_parser("download", help="Download a single asset")
    p_dl.add_argument("url", help="Asset URL")
    p_dl.add_argument("-o", "--output", help="Output file path")
    p_dl.set_defaults(func=cmd_download)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
