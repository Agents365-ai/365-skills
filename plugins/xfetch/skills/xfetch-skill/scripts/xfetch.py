#!/usr/bin/env python3
"""xfetch — fetch public X (Twitter) data with the user's own cookies.

Resilience note: X constantly changes its site, which breaks high-level scraper
libraries. This CLI insulates itself from most of that by talking to X's GraphQL
API directly — it reuses only the *current query IDs and feature flags* that the
twikit package ships (kept fresh with `pip install -U twikit`) and does its own
requests and parsing. It also skips twikit's homepage-scraped anti-bot transaction
ID (frequently broken) and sends a placeholder, which X accepts for read endpoints.

Agent-native contract:
  - stdout carries the data payload only (JSON/JSONL/CSV); pipe or redirect it.
  - stderr carries human status and errors.
  - exit code is the truth signal: 0 = ok, 1 = error, 2 = not authenticated,
    3 = rate limited, 64 = usage error (bad flag or argument).
"""

import argparse
import base64
import csv
import json
import os
import re
import sys
import time

import httpx
from twikit.client.gql import FEATURES, USER_FEATURES, Endpoint

BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
DEFAULT_COOKIES = os.path.expanduser(
    os.environ.get("XFETCH_COOKIES") or "~/.config/xfetch/cookies.json"
)
TIMEOUT = float(os.environ.get("XFETCH_TIMEOUT") or "30")
PROXY = os.environ.get("XFETCH_PROXY")

# Endpoints that current X serves only over POST (GET 404s). The requester also
# falls back GET<->POST on a 404, so this is an optimization, not a hard rule.
POST_ENDPOINTS = {
    Endpoint.SEARCH_TIMELINE,
    Endpoint.FOLLOWERS,
    Endpoint.FOLLOWING,
    Endpoint.HOME_TIMELINE,
    Endpoint.HOME_LATEST_TIMELINE,
}


def err(msg):
    print(msg, file=sys.stderr)


# --- session / auth ----------------------------------------------------------


def load_session(args):
    at = getattr(args, "auth_token", None) or os.environ.get("XFETCH_AUTH_TOKEN")
    ct0 = getattr(args, "ct0", None) or os.environ.get("XFETCH_CT0")
    if at and ct0:
        return at, ct0
    path = getattr(args, "cookies", None) or DEFAULT_COOKIES
    if os.path.exists(path):
        try:
            d = json.load(open(path))
        except Exception:
            d = {}
        if d.get("auth_token") and d.get("ct0"):
            return d["auth_token"], d["ct0"]
    return None, None


def require_session(args):
    at, ct0 = load_session(args)
    if not at or not ct0:
        err("Not authenticated. Set up credentials with one of:")
        err("  xfetch.py auth extract --browser chrome")
        err("  xfetch.py auth set --auth-token <token> --ct0 <token>")
        err("  xfetch.py auth import --file cookies.txt")
        sys.exit(2)
    return at, ct0


def save_session(at, ct0, path):
    path = path or DEFAULT_COOKIES
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"auth_token": at, "ct0": ct0}, open(path, "w"))
    os.chmod(path, 0o600)
    return path


# --- GraphQL layer -----------------------------------------------------------


def _headers(at, ct0):
    return {
        "authorization": f"Bearer {BEARER}",
        "x-csrf-token": ct0,
        "cookie": f"auth_token={at}; ct0={ct0}",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "content-type": "application/json",
        "x-twitter-client-language": "en",
        # X's anti-bot transaction id; a placeholder is accepted for reads.
        "x-client-transaction-id": base64.b64encode(os.urandom(70)).decode(),
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }


def gql(at, ct0, endpoint, variables, features=FEATURES, extra_params=None):
    qid = endpoint.split("/graphql/")[1].split("/")[0]

    def _do(method):
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, proxy=PROXY) as cl:
            if method == "GET":
                params = {
                    "variables": json.dumps(variables, separators=(",", ":")),
                    "features": json.dumps(features, separators=(",", ":")),
                }
                if extra_params:
                    for k, v in extra_params.items():
                        params[k] = json.dumps(v, separators=(",", ":"))
                return cl.get(endpoint, params=params, headers=_headers(at, ct0))
            body = {"variables": variables, "features": features, "queryId": qid}
            if extra_params:
                body.update(extra_params)
            return cl.post(endpoint, json=body, headers=_headers(at, ct0))

    prefer = "POST" if endpoint in POST_ENDPOINTS else "GET"
    r = _do(prefer)
    if r.status_code == 404:
        r = _do("POST" if prefer == "GET" else "GET")
    if r.status_code in (401, 403):
        err(
            f"X rejected the request (HTTP {r.status_code}) — cookies are likely "
            f"expired or invalid. Re-authenticate."
        )
        sys.exit(2)
    if r.status_code == 429:
        reset = r.headers.get("x-rate-limit-reset")
        err("Rate limited by X (HTTP 429). Wait for the window to reset, then resume.")
        if reset:
            err(f"rate_limit_reset={reset}")
        sys.exit(3)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if isinstance(data, dict) and data.get("errors") and not data.get("data"):
        msgs = "; ".join(e.get("message", "?") for e in data["errors"])
        raise RuntimeError(
            f"GraphQL error: {msgs} (X may have changed; try: pip install -U twikit)"
        )
    return data


# --- parsers -----------------------------------------------------------------


def parse_user(result):
    if not result or result.get("__typename") == "UserUnavailable":
        return None
    lg = result.get("legacy") or {}
    url = lg.get("url")
    url_entities = ((lg.get("entities") or {}).get("url") or {}).get("urls") or []
    if url_entities:
        url = url_entities[0].get("expanded_url") or url
    return {
        "id": result.get("rest_id") or lg.get("id_str"),
        "screen_name": lg.get("screen_name"),
        "name": lg.get("name"),
        "description": lg.get("description"),
        "location": lg.get("location"),
        "url": url,
        "created_at": lg.get("created_at"),
        "followers_count": lg.get("followers_count"),
        "following_count": lg.get("friends_count"),
        "statuses_count": lg.get("statuses_count"),
        "favourites_count": lg.get("favourites_count"),
        "media_count": lg.get("media_count"),
        "listed_count": lg.get("listed_count"),
        "verified": lg.get("verified"),
        "is_blue_verified": result.get("is_blue_verified"),
        "protected": lg.get("protected"),
        "profile_image_url": lg.get("profile_image_url_https"),
        "profile_banner_url": lg.get("profile_banner_url"),
    }


def parse_tweet(result):
    if not result:
        return None
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet") or {}
    lg = result.get("legacy") or {}
    tid = lg.get("id_str") or result.get("rest_id")
    if not tid:
        return None
    author = ((result.get("core") or {}).get("user_results") or {}).get("result") or {}
    alg = author.get("legacy") or {}
    sn = alg.get("screen_name")
    note = ((result.get("note_tweet") or {}).get("note_tweet_results") or {}).get(
        "result"
    ) or {}
    ent = lg.get("entities") or {}
    media_src = (lg.get("extended_entities") or ent or {}).get("media") or []
    return {
        "id": tid,
        "url": f"https://x.com/{sn}/status/{tid}" if sn and tid else None,
        "created_at": lg.get("created_at"),
        "text": note.get("text") or lg.get("full_text"),
        "lang": lg.get("lang"),
        "favorite_count": lg.get("favorite_count"),
        "retweet_count": lg.get("retweet_count"),
        "reply_count": lg.get("reply_count"),
        "quote_count": lg.get("quote_count"),
        "bookmark_count": lg.get("bookmark_count"),
        "view_count": (result.get("views") or {}).get("count"),
        "is_quote_status": lg.get("is_quote_status"),
        "possibly_sensitive": lg.get("possibly_sensitive"),
        "in_reply_to": lg.get("in_reply_to_screen_name"),
        "conversation_id": lg.get("conversation_id_str"),
        "hashtags": [h.get("text") for h in (ent.get("hashtags") or [])],
        "urls": [u.get("expanded_url") for u in (ent.get("urls") or [])],
        "media": [
            {
                "type": m.get("type"),
                "url": m.get("media_url_https") or m.get("media_url"),
            }
            for m in media_src
        ],
        "quote_id": (
            (result.get("quoted_status_result") or {}).get("result") or {}
        ).get("rest_id"),
        "retweeted_id": (
            (lg.get("retweeted_status_result") or {}).get("result") or {}
        ).get("rest_id"),
        "author": {
            "id": author.get("rest_id"),
            "screen_name": sn,
            "name": alg.get("name"),
        }
        if author
        else None,
    }


def _find_instructions(data):
    if isinstance(data, dict):
        if isinstance(data.get("instructions"), list):
            return data["instructions"]
        for v in data.values():
            r = _find_instructions(v)
            if r is not None:
                return r
    elif isinstance(data, list):
        for v in data:
            r = _find_instructions(v)
            if r is not None:
                return r
    return None


def _is_cursor(content):
    if (
        content.get("entryType") == "TimelineTimelineCursor"
        or content.get("__typename") == "TimelineTimelineCursor"
    ):
        return content.get("cursorType"), content.get("value")
    return None, None


def extract_timeline(data, kind):
    """Return (items, bottom_cursor). kind is 'tweet' or 'user'.
    Injected/promoted entries and cross-kind modules (e.g. who-to-follow) are skipped."""
    key = "tweet_results" if kind == "tweet" else "user_results"
    parse = parse_tweet if kind == "tweet" else parse_user
    items, cursor = [], None

    def handle(ic):
        if not ic or ic.get("promotedMetadata"):
            return
        p = parse((ic.get(key) or {}).get("result"))
        if p and p.get("id"):
            items.append(p)

    for ins in _find_instructions(data) or []:
        entries = ins.get("entries")
        if entries is None and ins.get("entry"):
            entries = [ins["entry"]]
        for e in entries or []:
            eid = e.get("entryId", "")
            if eid.startswith("promoted-"):
                continue
            content = e.get("content") or {}
            ctype, cval = _is_cursor(content)
            if ctype:
                if ctype == "Bottom":
                    cursor = cval
                continue
            if (
                content.get("entryType") == "TimelineTimelineModule"
                or "items" in content
            ):
                for it in content.get("items") or []:
                    handle((it.get("item") or {}).get("itemContent"))
                continue
            handle(content.get("itemContent"))
    return items, cursor


# --- output ------------------------------------------------------------------


def _sql_ident(c):
    # SQLite identifier allowlist: word chars only so quoting cannot be escaped
    return '"' + re.sub(r"\W", "_", c) + '"'


def _flat(v):
    return (
        json.dumps(v, ensure_ascii=False, default=str)
        if isinstance(v, (list, dict))
        else v
    )


def emit(data, args):
    fmt = args.format
    if fmt == "json":
        json.dump(
            data,
            sys.stdout,
            ensure_ascii=False,
            indent=None if args.plain else 2,
            default=str,
        )
        sys.stdout.write("\n")
        return
    rows = [
        r for r in (data if isinstance(data, list) else [data]) if isinstance(r, dict)
    ]
    if fmt == "jsonl":
        for r in rows:
            sys.stdout.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        return
    if fmt == "csv":
        if not rows:
            return
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        w = csv.DictWriter(sys.stdout, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _flat(v) for k, v in r.items()})
        return
    if fmt == "sqlite":
        import sqlite3

        if not args.db:
            err("Error: --db <path> is required for --format sqlite")
            sys.exit(1)
        if not rows:
            err("No rows to write")
            return
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        table = (
            "tweets"
            if "retweet_count" in cols
            else "users"
            if "followers_count" in cols
            else "records"
        )
        con = sqlite3.connect(args.db)
        defs = ",".join(
            f"{_sql_ident(c)} TEXT PRIMARY KEY"
            if c == "id"
            else f"{_sql_ident(c)} TEXT"
            for c in cols
        )
        create_sql = f"CREATE TABLE IF NOT EXISTS {table} ({defs})"
        insert_sql = "INSERT OR REPLACE INTO {} ({}) VALUES ({})".format(
            table,
            ",".join(_sql_ident(c) for c in cols),
            ",".join("?" for _ in cols),
        )
        # pi-lens-ignore: python-sql-injection
        con.execute(create_sql)  # nosemgrep
        # pi-lens-ignore: python-sql-injection
        con.executemany(insert_sql, [[_flat(r.get(c)) for c in cols] for r in rows])
        con.commit()
        con.close()
        err(f"✓ Inserted {len(rows)} rows into {table} ({args.db})")
        return


# --- pagination --------------------------------------------------------------


def paginate(
    args, at, ct0, endpoint, variables, kind, features=FEATURES, extra_params=None
):
    seen, out = set(), []
    cursor = getattr(args, "cursor", None)
    max_pages = int(args.max_pages) if getattr(args, "max_pages", None) else None
    want_all = getattr(args, "all", False)
    pages = 0
    next_cursor = None
    try:
        while True:
            v = dict(variables)
            if cursor:
                v["cursor"] = cursor
            data = gql(
                at, ct0, endpoint, v, features=features, extra_params=extra_params
            )
            items, next_cursor = extract_timeline(data, kind)
            fresh = [it for it in items if it["id"] not in seen]
            for it in fresh:
                seen.add(it["id"])
            out.extend(fresh)
            pages += 1
            if not next_cursor or not fresh:
                next_cursor = None
                break
            if not want_all and not max_pages:
                break
            if max_pages and pages >= max_pages:
                break
            cursor = next_cursor
            time.sleep(float(args.delay))
    except BaseException:
        # On failure/interrupt, emit the failed page's cursor so the pull can resume.
        if cursor:
            err(f"next_cursor={cursor}")
        raise
    if next_cursor:
        err(f"next_cursor={next_cursor}")
    return out


def extract_tweet_id(s):
    s = s.strip()
    if s.isdigit():
        return s
    m = re.search(r"(?:status|article)/(\d+)", s)
    if m:
        return m.group(1)
    raise ValueError(f"Invalid tweet URL or ID: {s}")


def resolve_user(at, ct0, handle):
    h = handle.lstrip("@")
    if h.isdigit():
        data = gql(
            at,
            ct0,
            Endpoint.USER_BY_REST_ID,
            {"userId": h, "withSafetyModeUserFields": True},
            features=USER_FEATURES,
        )
    else:
        data = gql(
            at,
            ct0,
            Endpoint.USER_BY_SCREEN_NAME,
            {"screen_name": h, "withSafetyModeUserFields": False},
            features=USER_FEATURES,
            extra_params={"fieldToggles": {"withAuxiliaryUserLabels": False}},
        )
    res = ((data.get("data") or {}).get("user") or {}).get("result")
    if not res:
        raise RuntimeError(f"User not found: {handle}")
    return res


# --- commands ----------------------------------------------------------------


def cmd_auth_set(args):
    if not args.auth_token or not args.ct0:
        err("auth set needs --auth-token and --ct0")
        sys.exit(2)
    err(f"✓ Saved cookies to {save_session(args.auth_token, args.ct0, args.cookies)}")


def cmd_auth_import(args):
    raw = open(args.file, encoding="utf-8", errors="replace").read()
    jar = {}
    try:
        obj = json.loads(raw)
        items = obj if isinstance(obj, list) else obj.get("cookies", [])
        for c in items:
            if isinstance(c, dict) and c.get("name"):
                jar[c["name"]] = c.get("value")
    # pi-lens-ignore: ast-grep:no-boolean-in-except
    except json.JSONDecodeError:
        for line in raw.splitlines():
            s = line.strip()
            if not s or (s.startswith("#") and not s.startswith("#HttpOnly_")):
                continue
            parts = s.replace("#HttpOnly_", "").split("\t")
            if len(parts) < 7:
                parts = s.split()
            if len(parts) >= 7:
                jar[parts[5]] = parts[6]
    if not jar.get("auth_token") or not jar.get("ct0"):
        err(f"Could not find both auth_token and ct0 in {args.file}")
        sys.exit(2)
    err(
        f"✓ Imported cookies from {args.file}; saved to "
        f"{save_session(jar['auth_token'], jar['ct0'], args.cookies)}"
    )


def cmd_auth_extract(args):
    try:
        import browser_cookie3 as bc3
    except ImportError:
        err("Browser extraction needs browser_cookie3: pip install browser_cookie3")
        sys.exit(1)
    fn = getattr(bc3, args.browser, None)
    if fn is None:
        err(f"Unsupported browser: {args.browser}")
        sys.exit(2)
    found, problems = {}, []
    for domain in ("x.com", "twitter.com"):
        try:
            for c in fn(domain_name=domain):
                if c.name in ("auth_token", "ct0") and c.value:
                    found.setdefault(c.name, c.value)
        except Exception as e:
            problems.append(f"{domain}: {e}")
    if not found.get("auth_token") or not found.get("ct0"):
        err(
            f"Could not find auth_token/ct0 in {args.browser} — is it logged into x.com?"
        )
        for p in problems:
            err(f"  ({p})")
        sys.exit(2)
    err(
        f"✓ Extracted from {args.browser}; saved to "
        f"{save_session(found['auth_token'], found['ct0'], args.cookies)}"
    )


def cmd_auth_login(args):
    import asyncio

    import twikit

    user = args.username or os.environ.get("X_USERNAME")
    pw = args.password or os.environ.get("X_PASSWORD")
    if not user or not pw:
        err("login needs --username and --password (or X_USERNAME / X_PASSWORD)")
        sys.exit(2)

    async def _login():
        c = twikit.Client(language="en-US", proxy=PROXY)
        await c.login(
            auth_info_1=user,
            auth_info_2=(args.email or os.environ.get("X_EMAIL")),
            password=pw,
            totp_secret=(args.totp or os.environ.get("X_TOTP_SECRET")),
        )
        return c.get_cookies()

    ck = asyncio.run(_login())
    if not ck.get("auth_token") or not ck.get("ct0"):
        err("Login did not return the expected cookies")
        sys.exit(1)
    err(
        f"✓ Logged in as @{user.lstrip('@')}; saved to "
        f"{save_session(ck['auth_token'], ck['ct0'], args.cookies)}"
    )


def cmd_auth_check(args):
    at, ct0 = load_session(args)
    if not at or not ct0:
        emit({"authenticated": False}, args)
        err("✗ Not authenticated")
        sys.exit(2)
    # Verify by reading the home timeline, which requires a valid login.
    try:
        data = gql(
            at,
            ct0,
            Endpoint.HOME_TIMELINE,
            {
                "count": 1,
                "includePromotedContent": False,
                "latestControlAvailable": True,
                "requestContext": "launch",
                "seenTweetIds": [],
            },
        )
    except SystemExit:
        raise  # 401/403 already reported by gql() with exit 2
    except Exception as e:
        emit({"authenticated": False, "error": str(e)}, args)
        err(f"✗ Credentials present but rejected by X: {e}")
        sys.exit(2)
    if (data.get("data") or {}).get("home"):
        emit({"authenticated": True}, args)
        err("✓ Authenticated (cookies valid)")
        return
    emit({"authenticated": False}, args)
    err("✗ Not authenticated")
    sys.exit(2)


def cmd_auth_clear(args):
    path = args.cookies or DEFAULT_COOKIES
    if os.path.exists(path):
        os.remove(path)
        err(f"✓ Cleared {path}")
    else:
        err("Nothing to clear")


def cmd_user(args):
    at, ct0 = require_session(args)
    emit(parse_user(resolve_user(at, ct0, args.handle)), args)


def cmd_tweets(args):
    at, ct0 = require_session(args)
    uid = resolve_user(at, ct0, args.handle)["rest_id"]
    endpoint = (
        Endpoint.USER_MEDIA
        if args.media
        else Endpoint.USER_TWEETS_AND_REPLIES
        if args.replies
        else Endpoint.USER_TWEETS
    )
    variables = {
        "userId": uid,
        "count": int(args.count),
        "includePromotedContent": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True,
        "withV2Timeline": True,
    }
    emit(paginate(args, at, ct0, endpoint, variables, "tweet"), args)


def cmd_likes(args):
    at, ct0 = require_session(args)
    uid = resolve_user(at, ct0, args.handle)["rest_id"]
    variables = {
        "userId": uid,
        "count": int(args.count),
        "includePromotedContent": False,
        "withVoice": True,
        "withV2Timeline": True,
    }
    emit(paginate(args, at, ct0, Endpoint.USER_LIKES, variables, "tweet"), args)


def cmd_tweet(args):
    at, ct0 = require_session(args)
    tid = extract_tweet_id(args.url_or_id)
    data = gql(
        at,
        ct0,
        Endpoint.TWEET_RESULT_BY_REST_ID,
        {
            "tweetId": tid,
            "withCommunity": False,
            "includePromotedContent": False,
            "withVoice": False,
        },
        extra_params={
            "fieldToggles": {
                "withArticleRichContentState": True,
                "withArticlePlainText": False,
                "withGrokAnalyze": False,
            }
        },
    )
    emit(
        parse_tweet(((data.get("data") or {}).get("tweetResult") or {}).get("result")),
        args,
    )


def cmd_thread(args):
    at, ct0 = require_session(args)
    focal = extract_tweet_id(args.url_or_id)
    variables = {
        "focalTweetId": focal,
        "with_rux_injections": False,
        "includePromotedContent": True,
        "withCommunity": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withBirdwatchNotes": True,
        "withVoice": True,
        "withV2Timeline": True,
    }
    extra = {"fieldToggles": {"withAuxiliaryUserLabels": False}}
    tweets = paginate(
        args, at, ct0, Endpoint.TWEET_DETAIL, variables, "tweet", extra_params=extra
    )
    root = [t for t in tweets if t["id"] == focal]
    replies = [t for t in tweets if t["id"] != focal]
    emit(root + replies, args)


def cmd_search(args):
    at, ct0 = require_session(args)
    product = {"top": "Top", "latest": "Latest", "media": "Media"}.get(
        args.type.lower(), "Top"
    )
    variables = {
        "rawQuery": args.query,
        "count": int(args.count),
        "querySource": "typed_query",
        "product": product,
    }
    emit(paginate(args, at, ct0, Endpoint.SEARCH_TIMELINE, variables, "tweet"), args)


def cmd_followers(args):
    at, ct0 = require_session(args)
    uid = resolve_user(at, ct0, args.handle)["rest_id"]
    variables = {
        "userId": uid,
        "count": int(args.count),
        "includePromotedContent": False,
    }
    emit(paginate(args, at, ct0, Endpoint.FOLLOWERS, variables, "user"), args)


def cmd_following(args):
    at, ct0 = require_session(args)
    uid = resolve_user(at, ct0, args.handle)["rest_id"]
    variables = {
        "userId": uid,
        "count": int(args.count),
        "includePromotedContent": False,
    }
    emit(paginate(args, at, ct0, Endpoint.FOLLOWING, variables, "user"), args)


def cmd_home(args):
    at, ct0 = require_session(args)
    endpoint = (
        Endpoint.HOME_LATEST_TIMELINE if args.following else Endpoint.HOME_TIMELINE
    )
    variables = {
        "count": int(args.count),
        "includePromotedContent": True,
        "latestControlAvailable": True,
        "requestContext": "launch",
        "withCommunity": True,
        "seenTweetIds": [],
    }
    emit(paginate(args, at, ct0, endpoint, variables, "tweet"), args)


def cmd_bookmarks(args):
    at, ct0 = require_session(args)
    variables = {"count": int(args.count), "includePromotedContent": True}
    features = dict(FEATURES)
    features["graphql_timeline_v2_bookmark_timeline"] = True
    emit(
        paginate(
            args, at, ct0, Endpoint.BOOKMARKS, variables, "tweet", features=features
        ),
        args,
    )


# --- CLI ---------------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    """Exit 64 on usage errors so exit 2 stays reserved for 'not authenticated'."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


def build_parser():
    g = Parser(add_help=False)
    g.add_argument("--cookies", help=f"cookies file (default {DEFAULT_COOKIES})")
    g.add_argument("--auth-token", dest="auth_token", help="auth_token cookie")
    g.add_argument("--ct0", help="ct0 cookie")
    g.add_argument("--proxy", help="proxy URL, e.g. http://user:pass@host:port")
    g.add_argument(
        "--format", choices=["json", "jsonl", "csv", "sqlite"], default="json"
    )
    g.add_argument("--db", help="SQLite path (with --format sqlite)")
    g.add_argument("--plain", action="store_true", help="compact JSON (no indent)")

    p = Parser(add_help=False)
    p.add_argument("-n", "--count", type=int, default=20, help="results per page")
    p.add_argument("--all", action="store_true", help="fetch every page")
    p.add_argument(
        "--max-pages", dest="max_pages", type=int, help="cap number of pages"
    )
    p.add_argument("--cursor", help="start from a pagination cursor")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between pages")

    ap = Parser(
        prog="xfetch.py",
        description="Fetch public X (Twitter) data with your own cookies.",
    )
    ap.add_argument("-v", "--version", action="version", version="xfetch-skill 0.3")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("auth", parents=[g], help="authentication")
    asub = sp.add_subparsers(dest="authcmd", required=True)
    asub.add_parser("check", parents=[g]).set_defaults(func=cmd_auth_check)
    asub.add_parser("set", parents=[g]).set_defaults(func=cmd_auth_set)
    ai = asub.add_parser(
        "import", parents=[g], help="import a cookies.txt / JSON export"
    )
    ai.add_argument("--file", required=True)
    ai.set_defaults(func=cmd_auth_import)
    ae = asub.add_parser(
        "extract", parents=[g], help="read cookies from a logged-in browser"
    )
    ae.add_argument(
        "--browser",
        default="chrome",
        choices=[
            "chrome",
            "chromium",
            "firefox",
            "safari",
            "edge",
            "brave",
            "arc",
            "opera",
            "vivaldi",
            "librewolf",
        ],
    )
    ae.set_defaults(func=cmd_auth_extract)
    al = asub.add_parser(
        "login", parents=[g], help="username/password login (via twikit)"
    )
    al.add_argument("--username")
    al.add_argument("--password")
    al.add_argument("--email")
    al.add_argument("--totp")
    al.set_defaults(func=cmd_auth_login)
    asub.add_parser("clear", parents=[g]).set_defaults(func=cmd_auth_clear)

    x = sub.add_parser("user", parents=[g], help="user profile")
    x.add_argument("handle")
    x.set_defaults(func=cmd_user)

    x = sub.add_parser("tweets", parents=[g, p], help="a user's tweets")
    x.add_argument("handle")
    x.add_argument("--replies", action="store_true")
    x.add_argument("--media", action="store_true")
    x.set_defaults(func=cmd_tweets)

    x = sub.add_parser("likes", parents=[g, p], help="a user's liked tweets")
    x.add_argument("handle")
    x.set_defaults(func=cmd_likes)

    x = sub.add_parser("tweet", parents=[g], help="single tweet by URL or ID")
    x.add_argument("url_or_id")
    x.set_defaults(func=cmd_tweet)

    x = sub.add_parser("thread", parents=[g, p], help="a tweet and its replies")
    x.add_argument("url_or_id")
    x.set_defaults(func=cmd_thread)

    x = sub.add_parser("search", parents=[g, p], help="search tweets")
    x.add_argument("query")
    x.add_argument(
        "--type",
        default="top",
        type=str.lower,
        choices=["top", "latest", "media"],
        help="top | latest | media",
    )
    x.set_defaults(func=cmd_search)

    x = sub.add_parser("followers", parents=[g, p], help="a user's followers")
    x.add_argument("handle")
    x.set_defaults(func=cmd_followers)

    x = sub.add_parser("following", parents=[g, p], help="who a user follows")
    x.add_argument("handle")
    x.set_defaults(func=cmd_following)

    x = sub.add_parser("home", parents=[g, p], help="your home timeline")
    x.add_argument("--following", action="store_true", help="chronological (Following)")
    x.set_defaults(func=cmd_home)

    sub.add_parser("bookmarks", parents=[g, p], help="your bookmarks").set_defaults(
        func=cmd_bookmarks
    )
    return ap


def main():
    args = build_parser().parse_args()
    global PROXY
    if getattr(args, "proxy", None):
        PROXY = args.proxy
    try:
        args.func(args)
    # pi-lens-ignore: unreachable-except
    except SystemExit:
        raise
    except KeyboardInterrupt:
        err("Interrupted")
        sys.exit(130)
    except Exception as e:
        err(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
