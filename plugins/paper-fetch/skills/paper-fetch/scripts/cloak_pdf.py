#!/usr/bin/env python3
"""Fetch a (possibly Cloudflare-gated) PDF via CloakBrowser; write bytes to stdout.

Usage: cloak_pdf.py <url> [timeout_seconds]

Stdout: raw PDF bytes (binary).
Stderr: progress / error messages (safe to /dev/null).
Exit:   0 on success (bytes written), 1 on any failure.

This is an OPTIONAL companion to fetch.py. fetch.py shells out to it only when
PAPER_FETCH_CLOAK is set and a normal download was blocked by Cloudflare. It
requires the `cloakbrowser` package (https://github.com/CloakHQ/CloakBrowser)
to be importable in the interpreter that runs it — point CLOAKBROWSER_PYTHON at
that interpreter's venv. fetch.py itself stays stdlib-only and never imports
this module; it re-validates the returned bytes through its own %PDF + size
checks, so this helper does no validation beyond fetching.
"""

import sys
import time
from urllib.parse import urlparse


def _err(msg: str) -> None:
    print(f"[cloak] {msg}", file=sys.stderr)


def main() -> int:
    if not (2 <= len(sys.argv) <= 3):
        _err("usage: cloak_pdf.py <url> [timeout_seconds]")
        return 1

    url = sys.argv[1]
    timeout_s = int(sys.argv[2]) if len(sys.argv) == 3 else 60
    timeout_ms = timeout_s * 1000

    try:
        from cloakbrowser import launch
    except ImportError as e:
        _err(f"cloakbrowser import failed: {e}")
        _err("install via: pip install cloakbrowser")
        return 1

    browser = None
    try:
        _err("launching headless stealth browser")
        browser = launch(headless=True)
        ctx = browser.new_context(accept_downloads=False)
        page = ctx.new_page()

        # Visit the origin first so CloakBrowser can solve any Cloudflare JS
        # challenge and set the cf_clearance cookie for the domain. The cookie
        # then carries over to the APIRequestContext fetch below (same jar).
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        _err(f"clearing challenge at {origin}")
        try:
            page.goto(origin, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as e:
            _err(f"origin navigation warning: {e}")

        # Poll for the Cloudflare interstitial to clear ("Just a moment...").
        deadline = time.time() + min(timeout_s, 30)
        while time.time() < deadline:
            title = page.title() or ""
            if title and "Just a moment" not in title:
                break
            time.sleep(1)

        # Fetch the PDF via the browser context's HTTP client — it shares the
        # cookie jar (including cf_clearance) but does not render, so binary
        # bodies come back intact rather than triggering the PDF viewer.
        _err(f"fetching {url}")
        resp = ctx.request.get(
            url,
            headers={"Accept": "application/pdf,*/*;q=0.8"},
            timeout=timeout_ms,
        )
        if not resp.ok:
            _err(f"context request returned HTTP {resp.status}")
            return 1
        body = resp.body()
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()
        _err(f"done, {len(body)} bytes")
        return 0
    except Exception as e:
        _err(f"failed: {e}")
        return 1
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
