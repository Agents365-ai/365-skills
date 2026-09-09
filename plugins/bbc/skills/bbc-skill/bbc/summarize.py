"""Build summary.json from a comments.jsonl + video meta."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bbc import SCHEMA_VERSION


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iso_utc(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except (ValueError, OverflowError, OSError):
        return ""


def _preview(text: str, n: int = 80) -> str:
    t = (text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def build_summary(
    *,
    jsonl_path: Path,
    video_meta: dict,
    fetch_range: dict,
    declared_all_count: int | None,
    top_n: int = 20,
) -> dict:
    # stream-read jsonl
    rows: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total = len(rows)
    top_level = sum(1 for r in rows if r.get("parent", 0) == 0 and r.get("top_type", 0) == 0)
    nested = sum(1 for r in rows if r.get("parent", 0) != 0)
    pinned = sum(1 for r in rows if r.get("top_type", 0) != 0)
    unique_users = len({r.get("mid") for r in rows if r.get("mid")})
    up_replies = sum(1 for r in rows if r.get("is_up_reply"))

    ctimes = [r["ctime"] for r in rows if r.get("ctime")]
    earliest = min(ctimes) if ctimes else 0
    latest = max(ctimes) if ctimes else 0

    by_day = Counter()
    for r in rows:
        iso = r.get("ctime_iso")
        if iso and len(iso) >= 10:
            by_day[iso[:10]] += 1
    by_day_list = [{"date": d, "count": c} for d, c in sorted(by_day.items())]

    top_liked = sorted(rows, key=lambda r: r.get("like", 0), reverse=True)[:top_n]
    top_liked_out = [
        {
            "rpid": r.get("rpid"),
            "uname": r.get("uname"),
            "mid": r.get("mid"),
            "like": r.get("like"),
            "parent": r.get("parent"),
            "is_up_reply": r.get("is_up_reply"),
            "ctime_iso": r.get("ctime_iso"),
            "message_preview": _preview(r.get("message", "")),
        }
        for r in top_liked
    ]

    top_replied_pool = [r for r in rows if r.get("parent", 0) == 0]
    top_replied = sorted(top_replied_pool, key=lambda r: r.get("rcount", 0), reverse=True)[:top_n]
    top_replied_out = [
        {
            "rpid": r.get("rpid"),
            "uname": r.get("uname"),
            "rcount": r.get("rcount"),
            "like": r.get("like"),
            "ctime_iso": r.get("ctime_iso"),
            "message_preview": _preview(r.get("message", "")),
        }
        for r in top_replied
    ]

    ip_counter = Counter(r.get("ip_location") or "未知" for r in rows)
    ip_dist = dict(sorted(ip_counter.items(), key=lambda x: x[1], reverse=True))

    completeness = None
    if declared_all_count:
        completeness = round(total / declared_all_count, 4)

    return {
        "schema_version": SCHEMA_VERSION,
        "fetched_at": _iso_now(),
        "fetch_range": fetch_range,
        "video": video_meta,
        "counts": {
            "total": total,
            "top_level": top_level,
            "nested": nested,
            "pinned": pinned,
            "declared_all_count": declared_all_count,
            "completeness": completeness,
            "unique_users": unique_users,
            "up_replies": up_replies,
        },
        "time_distribution": {
            "earliest_iso": _iso_utc(earliest),
            "latest_iso": _iso_utc(latest),
            "by_day": by_day_list,
        },
        "top_liked": top_liked_out,
        "top_replied": top_replied_out,
        "ip_distribution": ip_dist,
    }


def video_meta_from_view(view: dict, tags: list[dict]) -> dict:
    stat = view.get("stat") or {}
    owner = view.get("owner") or {}
    return {
        "bvid": view.get("bvid"),
        "aid": view.get("aid"),
        "cid": view.get("cid"),
        "title": view.get("title"),
        "desc": view.get("desc"),
        "pubdate_iso": _iso_utc(int(view.get("pubdate") or 0)),
        "ctime_iso": _iso_utc(int(view.get("ctime") or 0)),
        "duration_seconds": view.get("duration"),
        "cover_url": view.get("pic"),
        "tname": view.get("tname"),
        "owner": {"mid": owner.get("mid"), "name": owner.get("name"), "face": owner.get("face")},
        "stat": {
            "view": stat.get("view"),
            "like": stat.get("like"),
            "coin": stat.get("coin"),
            "favorite": stat.get("favorite"),
            "reply": stat.get("reply"),
            "danmaku": stat.get("danmaku"),
            "share": stat.get("share"),
            "his_rank": stat.get("his_rank"),
            "now_rank": stat.get("now_rank"),
        },
        "tags": [t.get("tag_name") for t in (tags or []) if t.get("tag_name")],
    }
