"""argparse dispatcher for bbc."""

import argparse
import json
import sys
from pathlib import Path

from bbc import (
    __version__,
    api,
    cookie,
    envelope,
    fetch,
    fetch_user,
    progress,
    schema,
    summarize,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bbc",
        description="Fetch Bilibili video comments for UP主 self-analysis.",
    )
    p.add_argument("--version", action="version", version=f"bbc {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # fetch
    f = sub.add_parser("fetch", help="Fetch all comments for one video (BV or URL)")
    f.add_argument("target", help="BV number or Bilibili video URL")
    f.add_argument(
        "--max", dest="max_top", type=int, default=None, help="Max top-level comments"
    )
    f.add_argument(
        "--since", dest="since", default=None, help="ISO date/time; fetch newer only"
    )
    f.add_argument("--output", "-o", default=None, help="Output directory")
    f.add_argument("--cookie-file", default=None, help="Netscape cookie file")
    f.add_argument(
        "--browser",
        default="auto",
        choices=["auto", "firefox", "chrome", "edge", "safari"],
    )
    f.add_argument("--format", dest="fmt", default=None, choices=["json", "table"])
    f.add_argument("--dry-run", action="store_true")
    f.add_argument("--force", action="store_true")

    fu = sub.add_parser("fetch-user", help="Batch fetch all videos of a UP主 by UID")
    fu.add_argument("uid", type=int)
    fu.add_argument("--output", "-o", default=None)
    fu.add_argument("--video-limit", type=int, default=None)
    fu.add_argument("--max", dest="max_top", type=int, default=None)
    fu.add_argument("--cookie-file", default=None)
    fu.add_argument(
        "--browser",
        default="auto",
        choices=["auto", "firefox", "chrome", "edge", "safari"],
    )
    fu.add_argument("--format", dest="fmt", default=None, choices=["json", "table"])
    fu.add_argument("--dry-run", action="store_true")

    # summarize
    s = sub.add_parser(
        "summarize", help="Rebuild summary.json from existing comments.jsonl"
    )
    s.add_argument("directory")
    s.add_argument("--format", dest="fmt", default=None, choices=["json", "table"])

    # cookie-check
    cc = sub.add_parser("cookie-check", help="Validate cookie and print logged-in user")
    cc.add_argument("--cookie-file", default=None)
    cc.add_argument(
        "--browser",
        default="auto",
        choices=["auto", "firefox", "chrome", "edge", "safari"],
    )
    cc.add_argument("--format", dest="fmt", default=None, choices=["json", "table"])

    # schema
    sc = sub.add_parser("schema", help="Return JSON schema for a command (or all)")
    sc.add_argument("cmd", nargs="?", default=None)
    sc.add_argument("--format", dest="fmt", default=None, choices=["json", "table"])

    return p


def _resolve_cookies(args) -> tuple[dict, str]:
    return cookie.load(
        cookie_file=getattr(args, "cookie_file", None),
        browser=getattr(args, "browser", "auto"),
    )


def _cmd_schema(args) -> dict:
    return envelope.success(
        schema.describe(args.cmd),
        request_id=envelope.new_request_id(),
        elapsed_ms=0,
    )


def _cmd_cookie_check(args) -> dict:
    req_id = envelope.new_request_id()
    clock = envelope.Clock()
    try:
        cookies, source = _resolve_cookies(args)
    except cookie.CookieNotFound as e:
        return envelope.failure(
            "auth_required",
            str(e),
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=True,
        )
    client = api.Client(cookies)
    try:
        nav = api.get_nav(client)
    except api.ApiError as e:
        return envelope.failure(
            e.code,
            e.message,
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=e.retryable,
        )
    is_login = bool(nav.get("isLogin"))
    if not is_login:
        return envelope.failure(
            "auth_expired",
            "cookie does not represent a logged-in session",
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=True,
        )
    return envelope.success(
        {
            "mid": nav.get("mid"),
            "uname": nav.get("uname"),
            "vip": bool(nav.get("vipStatus") or 0),
            "level": (nav.get("level_info") or {}).get("current_level"),
            "source": source,
            "cookie_names": sorted(cookies.keys()),
        },
        request_id=req_id,
        elapsed_ms=clock.ms(),
    )


def _cmd_fetch(args) -> dict:
    req_id = envelope.new_request_id()
    clock = envelope.Clock()

    # dry-run: no cookie load required (just validate target)
    if args.dry_run:
        try:
            data = fetch.run_dry_run(args.target, args.output)
        except api.ApiError as e:
            return envelope.failure(
                e.code,
                e.message,
                request_id=req_id,
                elapsed_ms=clock.ms(),
                retryable=e.retryable,
            )
        return envelope.success(
            data,
            request_id=req_id,
            elapsed_ms=clock.ms(),
            extra_top={"dry_run": True},
        )

    try:
        cookies, source = _resolve_cookies(args)
    except cookie.CookieNotFound as e:
        return envelope.failure(
            "auth_required",
            str(e),
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=True,
        )

    try:
        since_ts = fetch.parse_since(args.since)
    except ValueError as e:
        return envelope.failure(
            "validation_error",
            str(e),
            request_id=req_id,
            elapsed_ms=clock.ms(),
            field="since",
        )

    prog = progress.Progress("fetch", req_id)
    try:
        data = fetch.run_fetch(
            target=args.target,
            cookies=cookies,
            output=args.output,
            max_top=args.max_top,
            since_ts=since_ts,
            force=args.force,
            progress=prog,
        )
    except api.ApiError as e:
        return envelope.failure(
            e.code,
            e.message,
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=e.retryable,
        )
    except Exception as e:
        return envelope.failure(
            "internal_error",
            f"{type(e).__name__}: {e}",
            request_id=req_id,
            elapsed_ms=clock.ms(),
        )
    data["cookie_source"] = source
    return envelope.success(data, request_id=req_id, elapsed_ms=clock.ms())


def _cmd_fetch_user(args) -> dict:
    req_id = envelope.new_request_id()
    clock = envelope.Clock()

    if args.dry_run:
        data = fetch_user.run_dry_run(args.uid, args.output, args.video_limit)
        return envelope.success(
            data,
            request_id=req_id,
            elapsed_ms=clock.ms(),
            extra_top={"dry_run": True},
        )

    try:
        cookies, source = _resolve_cookies(args)
    except cookie.CookieNotFound as e:
        return envelope.failure(
            "auth_required",
            str(e),
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=True,
        )

    prog = progress.Progress("fetch-user", req_id)
    try:
        data = fetch_user.run_fetch_user(
            uid=args.uid,
            cookies=cookies,
            output=args.output,
            video_limit=args.video_limit,
            max_top=args.max_top,
            progress=prog,
        )
    except api.ApiError as e:
        return envelope.failure(
            e.code,
            e.message,
            request_id=req_id,
            elapsed_ms=clock.ms(),
            retryable=e.retryable,
        )
    except Exception as e:
        return envelope.failure(
            "internal_error",
            f"{type(e).__name__}: {e}",
            request_id=req_id,
            elapsed_ms=clock.ms(),
        )
    data["cookie_source"] = source
    return envelope.success(data, request_id=req_id, elapsed_ms=clock.ms())


def _cmd_summarize(args) -> dict:
    req_id = envelope.new_request_id()
    clock = envelope.Clock()
    d = Path(args.directory).expanduser().resolve()
    jsonl = d / "comments.jsonl"
    if not jsonl.exists():
        return envelope.failure(
            "validation_error",
            f"no comments.jsonl in {d}",
            request_id=req_id,
            elapsed_ms=clock.ms(),
            field="directory",
        )
    raw_view = d / "raw" / "view.json"
    raw_tags = d / "raw" / "tags.json"
    try:
        view = (
            json.loads(raw_view.read_text(encoding="utf-8"))
            if raw_view.exists()
            else {}
        )
        tags = (
            json.loads(raw_tags.read_text(encoding="utf-8"))
            if raw_tags.exists()
            else []
        )
    except (OSError, json.JSONDecodeError) as e:
        return envelope.failure(
            "validation_error",
            f"malformed raw metadata in {d}/raw: {e}",
            request_id=req_id,
            elapsed_ms=clock.ms(),
            field="directory",
        )
    video_meta = summarize.video_meta_from_view(view, tags)
    summary = summarize.build_summary(
        jsonl_path=jsonl,
        video_meta=video_meta,
        fetch_range={"mode": "resumed", "max": None, "since": None, "resumed": True},
        declared_all_count=None,
    )
    out = d / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return envelope.success(
        {"summary_path": str(out), "counts": summary["counts"]},
        request_id=req_id,
        elapsed_ms=clock.ms(),
    )


DISPATCH = {
    "schema": _cmd_schema,
    "cookie-check": _cmd_cookie_check,
    "fetch": _cmd_fetch,
    "fetch-user": _cmd_fetch_user,
    "summarize": _cmd_summarize,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handler = DISPATCH.get(args.command)
    if handler is None:
        env = envelope.failure(
            "validation_error",
            f"unknown command: {args.command}",
            request_id=envelope.new_request_id(),
            elapsed_ms=0,
        )
    else:
        env = handler(args)

    fmt = envelope.effective_format(getattr(args, "fmt", None))
    envelope.emit(env, fmt)
    return envelope.exit_for(env)


if __name__ == "__main__":
    sys.exit(main())
