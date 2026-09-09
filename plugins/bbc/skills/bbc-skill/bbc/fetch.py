"""bbc fetch — main comment fetcher."""

import contextlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bbc import api, flatten, summarize
from bbc.progress import Progress

BV_RE = re.compile(r"BV[A-Za-z0-9]{10}")
URL_BV_RE = re.compile(r"/video/(BV[A-Za-z0-9]{10})", re.IGNORECASE)


def parse_target(target: str) -> str | None:
    """Extract a BV number from a BV string or full URL."""
    if not target:
        return None
    target = target.strip()
    m = URL_BV_RE.search(target)
    if m:
        return m.group(1)
    if BV_RE.fullmatch(target):
        return target
    m = BV_RE.search(target)
    if m:
        return m.group(0)
    return None


def parse_since(value: str | None) -> int | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    if value.isdigit():
        return int(value)
    raise ValueError(f"unrecognized --since value: {value}")


def default_output_dir(bvid: str) -> Path:
    return (Path.cwd() / "bilibili-comments" / bvid).resolve()


class FetchState:
    """Tracks resume state across runs (.bbc-state.json)."""

    def __init__(self, out_dir: Path, bvid: str | None = None):
        self.path = out_dir / ".bbc-state.json"
        self.data: dict = {
            "bvid": None,  # ownership: bound explicitly by run_fetch after validation; None = unknown (legacy/new state)
            "next_cursor": 0,
            "top_pages_done": 0,
            "top_done": False,
            "subs_done": [],  # list of rpids completed
            "latest_ctime": 0,
            "declared_all_count": None,
            "version": 1,
        }
        if self.path.exists():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _invalidate(out_dir: Path, jsonl_path: Path) -> None:
    """Remove prior output + resume state so the next fetch starts from scratch."""
    for path in (jsonl_path, out_dir / ".bbc-state.json"):
        if path.exists():
            path.unlink()


def _as_int(value: Any, what: str) -> int:
    """Coerce a Bilibili API / JSONL field to int; envelope-safe error on malformed data."""
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise api.ApiError("validation_error", f"malformed {what}: {value!r}") from e


def _require_bvid(target: str) -> str:
    """Extract a BV id or raise the validation-error envelope ApiError."""
    bvid = parse_target(target)
    if not bvid:
        raise api.ApiError(
            "validation_error", f"cannot extract BV number from: {target!r}"
        )
    return bvid


def run_fetch(
    *,
    target: str,
    cookies: dict,
    output: str | None,
    max_top: int | None,
    since_ts: int | None,
    force: bool,
    progress: Progress,
) -> dict[str, Any]:
    bvid = _require_bvid(target)

    out_dir = (
        Path(output).expanduser().resolve() if output else default_output_dir(bvid)
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)

    jsonl_path = out_dir / "comments.jsonl"
    summary_path = out_dir / "summary.json"

    state = FetchState(out_dir)

    # --force, or state that belongs to another video (or ownership unverifiable)
    # -> old data invalidated, refetch from scratch
    if force or state.data.get("bvid") != bvid:
        _invalidate(out_dir, jsonl_path)
        state = FetchState(out_dir)
    state.data["bvid"] = bvid

    progress.start(bvid=bvid, output=str(out_dir))

    client = api.Client(
        cookies, min_interval_sec=1.0, referer=f"https://www.bilibili.com/video/{bvid}/"
    )

    # 1. Video meta
    view = api.bv_to_view(client, bvid)
    aid = _as_int(view["aid"], "aid")
    owner_mid = _as_int((view.get("owner") or {}).get("mid") or 0, "owner.mid")
    title = view.get("title") or ""
    progress.progress(phase="meta", title=title, aid=aid)
    (out_dir / "raw" / "view.json").write_text(
        json.dumps(view, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    tags = api.get_tags(client, bvid)
    (out_dir / "raw" / "tags.json").write_text(
        json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Open JSONL append mode; if resuming we trust existing lines
    appended_ids: set[int] = set()
    if jsonl_path.exists() and not force:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rpid = json.loads(line).get("rpid")
                    if rpid:
                        appended_ids.add(int(rpid))
                except json.JSONDecodeError:
                    continue

    jsonl_file = jsonl_path.open("a", encoding="utf-8")

    def write_row(row: dict) -> None:
        rpid = row.get("rpid")
        if not rpid or rpid in appended_ids:
            return
        appended_ids.add(rpid)
        jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 2. Top-level loop (+ first-page pinned)
    top_level_replies: list[dict] = []
    pinned_count = 0
    next_cursor = 0 if force else state.data.get("next_cursor", 0)
    page = 0 if force else state.data.get("top_pages_done", 0)
    declared_all = state.data.get("declared_all_count")

    if not state.data.get("top_done"):
        while True:
            page += 1
            data = api.get_main_page(client, aid, next_cursor, bvid)
            d = data.get("data") or {}
            cur = d.get("cursor") or {}
            if declared_all is None:
                declared_all = cur.get("all_count")
                state.data["declared_all_count"] = declared_all

            replies = d.get("replies") or []

            # pinned only on first page
            if page == 1:
                for pr in d.get("top_replies") or []:
                    row = flatten.flatten_reply(
                        pr, bvid=bvid, owner_mid=owner_mid, top_type=2
                    )
                    if row.get("mid") == owner_mid:
                        row["top_type"] = 1  # UP置顶
                    write_row(row)
                    top_level_replies.append(pr)
                    pinned_count += 1
                upper = (d.get("upper") or {}).get("top") or None
                if isinstance(upper, dict):
                    row = flatten.flatten_reply(
                        upper, bvid=bvid, owner_mid=owner_mid, top_type=1
                    )
                    write_row(row)
                    top_level_replies.append(upper)
                    pinned_count += 1

            # save raw
            (out_dir / "raw" / f"main-page-{page:03d}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            progress.progress(
                phase="top_level",
                page=page,
                done=len(replies),
                cumulative=len(appended_ids),
                declared_total=declared_all,
            )

            should_stop = False
            for r in replies:
                ctime = _as_int(r.get("ctime") or 0, "ctime")
                if since_ts and ctime < since_ts:
                    should_stop = True
                    continue
                row = flatten.flatten_reply(
                    r, bvid=bvid, owner_mid=owner_mid, top_type=0
                )
                write_row(row)
                top_level_replies.append(r)
                if ctime > state.data["latest_ctime"]:
                    state.data["latest_ctime"] = ctime

            if (
                max_top
                and len([r for r in top_level_replies if r.get("parent", 0) == 0])
                >= max_top
            ):
                should_stop = True

            if cur.get("is_end") or not replies or should_stop:
                break
            next_cursor = cur.get("next")
            if not next_cursor:
                break

            state.data["next_cursor"] = next_cursor
            state.data["top_pages_done"] = page
            state.save()

        state.data["top_done"] = True
        state.data["top_pages_done"] = page
        state.save()

    # 3. Nested replies — iterate top-level entries with rcount > 0
    done_subs = set(state.data.get("subs_done") or [])
    subs_count = 0
    subs_threads = 0

    # Flush appended top-level rows so the re-read sees everything.
    jsonl_file.flush()

    thread_candidates = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                row.get("parent", 0) == 0
                and _as_int(row.get("rcount") or 0, "rcount") > 0
            ):
                thread_candidates.append(
                    (_as_int(row["rpid"], "rpid"), _as_int(row["rcount"], "rcount"))
                )

    for rpid, rcount in thread_candidates:
        if rpid in done_subs:
            continue
        subs_threads += 1
        pn = 1
        while True:
            sd = api.get_sub_page(client, aid, rpid, pn, bvid)
            subs = (sd.get("data") or {}).get("replies") or []
            (out_dir / "raw" / f"reply-{rpid}-p{pn:03d}.json").write_text(
                json.dumps(sd, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for sr in subs:
                if since_ts and _as_int(sr.get("ctime") or 0, "ctime") < since_ts:
                    continue
                row = flatten.flatten_reply(
                    sr, bvid=bvid, owner_mid=owner_mid, top_type=0
                )
                write_row(row)
                subs_count += 1
            progress.progress(
                phase="nested",
                root_rpid=rpid,
                page=pn,
                got=len(subs),
                cumulative_subs=subs_count,
            )
            if len(subs) < 20:
                break
            pn += 1
            # shorter throttle for sub pages
            time.sleep(0.5)
        done_subs.add(rpid)
        state.data["subs_done"] = sorted(done_subs)
        state.save()

    jsonl_file.close()

    # 4. Summary
    video_meta = summarize.video_meta_from_view(view, tags)
    fetch_range = {
        "mode": "full" if not (max_top or since_ts) else "partial",
        "max": max_top,
        "since": since_ts,
        "resumed": False,
    }
    summary = summarize.build_summary(
        jsonl_path=jsonl_path,
        video_meta=video_meta,
        fetch_range=fetch_range,
        declared_all_count=declared_all,
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    progress.complete(counts=summary["counts"])

    return {
        "bvid": bvid,
        "aid": aid,
        "title": title,
        "output_dir": str(out_dir),
        "files": {
            "comments": str(jsonl_path.relative_to(out_dir.parent))
            if out_dir.parent in jsonl_path.parents
            else "comments.jsonl",
            "summary": "summary.json",
            "raw_dir": "raw/",
        },
        "counts": summary["counts"],
        "completeness": summary["counts"].get("completeness"),
    }


def run_dry_run(target: str, output: str | None) -> dict[str, Any]:
    bvid = _require_bvid(target)
    out_dir = (
        Path(output).expanduser().resolve() if output else default_output_dir(bvid)
    )
    return {
        "dry_run": True,
        "would": {
            "bvid": bvid,
            "output_dir": str(out_dir),
            "endpoints": [
                "GET /x/web-interface/view",
                "GET /x/tag/archive/tags",
                "GET /x/v2/reply/main (paginated, ~20 per page)",
                "GET /x/v2/reply/reply (per thread with rcount>0, paginated)",
            ],
            "rate_limit": "1.0s between top-level requests, 0.5s between sub-replies",
            "note": "Exact request count depends on total comments and nested threads. Use 'bbc fetch <BV>' to execute.",
        },
    }
