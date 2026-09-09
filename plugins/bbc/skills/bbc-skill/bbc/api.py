"""HTTP client: stdlib-only, cookie auth, rate-limit, retry."""

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Retryable B站 internal codes
RETRYABLE_CODES = {-352, -412, -509}
# Auth-invalid codes
AUTH_BAD_CODES = {-101, -111}
NOT_FOUND_CODES = {-404, 62002, 62004}


class ApiError(Exception):
    def __init__(
        self, code: str, message: str, *, retryable: bool = False, raw: Any = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.raw = raw


class Client:
    def __init__(
        self,
        cookies: dict[str, str],
        *,
        min_interval_sec: float = 1.0,
        referer: str = "https://www.bilibili.com/",
    ):
        self.cookies = cookies
        self.min_interval = min_interval_sec
        self.referer = referer
        self._last_request = 0.0

    def _cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def get_json(
        self,
        url: str,
        *,
        max_retries: int = 3,
        referer: str | None = None,
    ) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Cookie": self._cookie_header(),
                "Referer": referer or self.referer,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        attempt = 0
        backoff = 2.0
        while True:
            attempt += 1
            self._throttle()
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
            # pi-lens-ignore: ast-grep:no-boolean-in-except
            except urllib.error.HTTPError as e:
                if e.code == 412 and attempt <= max_retries:
                    time.sleep(backoff + random.random())
                    backoff *= 2
                    continue
                if 500 <= e.code < 600 and attempt <= max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ApiError(
                    "network_error" if e.code >= 500 else "api_error",
                    f"HTTP {e.code}: {e.reason}",
                    retryable=(e.code == 412 or 500 <= e.code < 600),
                )
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt <= max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ApiError(
                    "network_error", f"{type(e).__name__}: {e}", retryable=True
                )
            except json.JSONDecodeError as e:
                raise ApiError("api_error", f"invalid JSON response: {e}")

            code = data.get("code")
            if code == 0:
                return data
            if code in AUTH_BAD_CODES:
                raise ApiError(
                    "auth_expired", data.get("message") or "cookie rejected", raw=data
                )
            if code in NOT_FOUND_CODES:
                raise ApiError(
                    "not_found", data.get("message") or "resource not found", raw=data
                )
            if code in RETRYABLE_CODES and attempt <= max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            if code in RETRYABLE_CODES:
                raise ApiError(
                    "rate_limited",
                    data.get("message") or "rate limited",
                    retryable=True,
                    raw=data,
                )
            raise ApiError(
                "api_error", f"B站 code={code}: {data.get('message')}", raw=data
            )


# ---- Endpoint helpers ----


def bv_to_view(client: Client, bvid: str) -> dict:
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    return client.get_json(url)["data"]


def get_nav(client: Client) -> dict:
    return client.get_json("https://api.bilibili.com/x/web-interface/nav")["data"]


def get_tags(client: Client, bvid: str) -> list[dict]:
    url = f"https://api.bilibili.com/x/tag/archive/tags?bvid={bvid}"
    try:
        return client.get_json(url).get("data") or []
    except ApiError:
        return []


def get_main_page(
    client: Client, aid: int, next_cursor: int, bvid: str, ps: int = 20
) -> dict:
    url = (
        "https://api.bilibili.com/x/v2/reply/main"
        f"?type=1&oid={aid}&mode=3&next={next_cursor}&ps={ps}"
    )
    return client.get_json(url, referer=f"https://www.bilibili.com/video/{bvid}/")


def get_sub_page(
    client: Client, aid: int, root_rpid: int, pn: int, bvid: str, ps: int = 20
) -> dict:
    url = (
        "https://api.bilibili.com/x/v2/reply/reply"
        f"?type=1&oid={aid}&root={root_rpid}&ps={ps}&pn={pn}"
    )
    return client.get_json(url, referer=f"https://www.bilibili.com/video/{bvid}/")


def list_user_videos(
    client: Client,
    uid: int,
    *,
    img_key: str,
    sub_key: str,
    pn: int = 1,
    ps: int = 30,
) -> dict:
    from bbc import wbi

    params = {
        "mid": uid,
        "pn": pn,
        "ps": ps,
        "order": "pubdate",
        "platform": "web",
        "web_location": "1550101",
    }
    url = wbi.signed_url(
        "https://api.bilibili.com/x/space/wbi/arc/search", params, img_key, sub_key
    )
    return client.get_json(url, referer=f"https://space.bilibili.com/{uid}")
