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

Environment:
  PAPER_FETCH_CLOAK_HEADED  If set, launch a headed (visible) browser instead
                            of headless. Some Cloudflare challenges (e.g.
                            science.org) defeat headless mode and only clear in
                            a real window. Needs a display, so it is opt-in.
"""

import base64
import os
import sys
import time
from urllib.parse import urlparse

# JS run inside the cleared page to fetch the PDF through the browser's own
# network stack (full TLS/fingerprint + cookie jar). This passes Cloudflare
# where an out-of-page APIRequestContext request is re-challenged. Returns the
# body base64-encoded so binary survives the JS string boundary.
_FETCH_JS = """async (u) => {
    const r = await fetch(u, {credentials: 'include'});
    const bytes = new Uint8Array(await r.arrayBuffer());
    let bin = '';
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return {status: r.status, b64: btoa(bin)};
}"""


def _err(msg: str) -> None:
    print(f"[cloak] {msg}", file=sys.stderr)


def main() -> int:
    if not (2 <= len(sys.argv) <= 3):
        _err("usage: cloak_pdf.py <url> [timeout_seconds]")
        return 1

    url = sys.argv[1]
    timeout_s = int(sys.argv[2]) if len(sys.argv) == 3 else 60
    timeout_ms = timeout_s * 1000
    headless = not os.environ.get("PAPER_FETCH_CLOAK_HEADED")

    try:
        from cloakbrowser import launch
    except ImportError as e:
        _err(f"cloakbrowser import failed: {e}")
        _err("install via: pip install cloakbrowser")
        return 1

    browser = None
    try:
        _err(f"launching {'headless' if headless else 'headed'} stealth browser")
        browser = launch(headless=headless)
        ctx = browser.new_context(accept_downloads=False)
        page = ctx.new_page()

        # Visit the origin first so CloakBrowser can solve any Cloudflare JS
        # challenge and set the cf_clearance cookie for the domain. The cookie
        # then carries over to the in-page fetch below (same context).
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        _err(f"clearing challenge at {origin}")
        try:
            page.goto(origin, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as e:
            _err(f"origin navigation warning: {e}")

        # Poll until the Cloudflare interstitial clears. The challenge shows
        # "Just a moment..." and then a transitional "Loading <url>" title
        # before the real page title appears — treat both as not-ready.
        deadline = time.time() + min(timeout_s, 40)
        while time.time() < deadline:
            title = page.title() or ""
            if title and "Just a moment" not in title and not title.startswith("Loading"):
                break
            time.sleep(1)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        time.sleep(1)  # settle late-loading JS / redirects
        _err(f"page title: {(page.title() or '')[:60]!r}")

        # Fetch from inside the cleared page so the request carries the browser's
        # real fingerprint and cf_clearance cookie. Retry once if a late
        # navigation tears down the execution context mid-evaluate.
        _err(f"fetching {url}")
        res = None
        for attempt in range(2):
            try:
                res = page.evaluate(_FETCH_JS, url)
                break
            except Exception as e:
                _err(f"evaluate attempt {attempt + 1} failed: {e}")
                time.sleep(2)
        if not res:
            return 1
        status = res.get("status")
        if status != 200 or not res.get("b64"):
            _err(f"in-page fetch returned HTTP {status}")
            return 1
        body = base64.b64decode(res["b64"])
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
