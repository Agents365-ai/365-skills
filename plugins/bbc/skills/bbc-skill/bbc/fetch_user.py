"""bbc fetch-user — sequentially fetch comments for all videos of a UP主.

Strict sequential: one video at a time. Never parallel. Failures on an
individual video are recorded to channel-summary.json.errors and the next
video continues.
"""

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bbc import api, fetch, wbi
from bbc.progress import Progress

INTER_VIDEO_SLEEP_MIN = 5.0
INTER_VIDEO_SLEEP_MAX = 10.0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_output_dir(uid: int) -> Path:
    return (Path.cwd() / "bilibili-comments" / f"user-{uid}").resolve()


def _list_all_videos(
    client: api.Client, uid: int, img_key: str, sub_key: str, *, limit: int | None
) -> list[dict]:
    """Paginate through all user videos. Returns list of dicts with bvid/title/play/comment/created."""
    videos: list[dict] = []
    pn = 1
    ps = 30
    while True:
        data = api.list_user_videos(
            client, uid, img_key=img_key, sub_key=sub_key, pn=pn, ps=ps
        )
        vlist = (data.get("data", {}).get("list", {}) or {}).get("vlist") or []
        page_info = (data.get("data", {}).get("page", {})) or {}
        for v in vlist:
            videos.append(
                {
                    "bvid": v.get("bvid"),
                    "aid": v.get("aid"),
                    "title": v.get("title"),
                    "play": v.get("play"),
                    "comment": v.get("comment"),
                    "created": v.get("created"),
                    "description": v.get("description"),
                    "pic": v.get("pic"),
                }
            )
            if limit and len(videos) >= limit:
                return videos
        total = int(page_info.get("count") or 0)
        if not vlist or len(videos) >= total:
            break
        pn += 1
        time.sleep(0.5)
    return videos


def _load_channel_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"completed_bvids": [], "errors": []}


def run_fetch_user(
    *,
    uid: int,
    cookies: dict,
    output: str | None,
    video_limit: int | None,
    max_top: int | None,
    progress: Progress,
    inter_video_sleep_range: tuple[float, float] = (
        INTER_VIDEO_SLEEP_MIN,
        INTER_VIDEO_SLEEP_MAX,
    ),
) -> dict[str, Any]:
    out_dir = Path(output).expanduser().resolve() if output else default_output_dir(uid)
    out_dir.mkdir(parents=True, exist_ok=True)

    state_path = out_dir / ".bbc-channel-state.json"
    state = _load_channel_state(state_path)
    completed = set(state.get("completed_bvids") or [])

    client = api.Client(cookies, min_interval_sec=1.0)

    progress.start(uid=uid, output=str(out_dir))

    # 1. Get owner info + WBI keys
    nav = api.get_nav(client)
    img_key, sub_key = wbi.keys_from_nav(nav)
    progress.progress(phase="nav", img_key_len=len(img_key))

    # 2. List videos
    progress.progress(phase="list_videos", message="fetching video list…")
    videos = _list_all_videos(client, uid, img_key, sub_key, limit=video_limit)
    progress.progress(phase="list_videos", total_videos=len(videos))

    (out_dir / "videos.json").write_text(
        json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3. Sequentially fetch each video (NEVER parallel)
    per_video_results: list[dict] = []
    errors: list[dict] = list(state.get("errors") or [])

    for idx, v in enumerate(videos, start=1):
        bvid = v.get("bvid")
        if not bvid:
            continue
        if bvid in completed:
            progress.progress(
                phase="skip_video",
                idx=idx,
                total=len(videos),
                bvid=bvid,
                reason="already_done",
            )
            continue

        video_out = out_dir / bvid
        progress.progress(
            phase="video_start",
            idx=idx,
            total=len(videos),
            bvid=bvid,
            title=v.get("title"),
            declared_comments=v.get("comment"),
        )

        sub_progress = Progress(
            "fetch-user.video", progress.request_id, enabled=progress.enabled
        )
        try:
            result = fetch.run_fetch(
                target=bvid,
                cookies=cookies,
                output=str(video_out),
                max_top=max_top,
                since_ts=None,
                force=False,
                progress=sub_progress,
            )
            per_video_results.append(
                {
                    "bvid": bvid,
                    "title": v.get("title"),
                    "output_dir": str(video_out),
                    "counts": result.get("counts"),
                    "completeness": result.get("completeness"),
                }
            )
            completed.add(bvid)
            progress.progress(
                phase="video_done",
                idx=idx,
                total=len(videos),
                bvid=bvid,
                counts=result.get("counts"),
            )
        except api.ApiError as e:
            err_rec = {
                "bvid": bvid,
                "title": v.get("title"),
                "code": e.code,
                "message": e.message,
                "retryable": e.retryable,
                "at": _iso_now(),
            }
            errors.append(err_rec)
            progress.warn(f"video {bvid} failed", **err_rec)
        except Exception as e:
            err_rec = {
                "bvid": bvid,
                "title": v.get("title"),
                "code": "internal_error",
                "message": f"{type(e).__name__}: {e}",
                "retryable": False,
                "at": _iso_now(),
            }
            errors.append(err_rec)
            progress.warn(f"video {bvid} crashed", **err_rec)

        # Persist state after every video (resume-safe even if killed)
        state_path.write_text(
            json.dumps(
                {"completed_bvids": sorted(completed), "errors": errors},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # Inter-video cooldown — only if not last; randomised to mimic human
        # cadence and reduce the chance of B站 risk-control banning the session.
        if idx < len(videos):
            sleep_for = random.uniform(*inter_video_sleep_range)
            progress.progress(phase="cooldown", seconds=round(sleep_for, 2))
            time.sleep(sleep_for)

    # 4. Channel-level summary
    summary = {
        "schema_version": "1.0.0",
        "generated_at": _iso_now(),
        "uid": uid,
        "video_count_total": len(videos),
        "video_count_fetched": len(per_video_results),
        "video_count_skipped": len(videos) - len(per_video_results) - len(errors),
        "video_count_failed": len(errors),
        "videos": per_video_results,
        "errors": errors,
    }
    summary_path = out_dir / "channel-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    progress.complete(
        uid=uid, total=len(videos), fetched=len(per_video_results), failed=len(errors)
    )

    return {
        "uid": uid,
        "output_dir": str(out_dir),
        "video_count_total": len(videos),
        "video_count_fetched": len(per_video_results),
        "video_count_failed": len(errors),
        "files": {
            "videos": "videos.json",
            "channel_summary": "channel-summary.json",
        },
    }


def run_dry_run(
    uid: int, output: str | None, video_limit: int | None
) -> dict[str, Any]:
    out_dir = Path(output).expanduser().resolve() if output else default_output_dir(uid)
    return {
        "dry_run": True,
        "would": {
            "uid": uid,
            "output_dir": str(out_dir),
            "video_limit": video_limit,
            "mode": "sequential (one video at a time, never parallel)",
            "endpoints": [
                "GET /x/web-interface/nav (WBI key discovery)",
                "GET /x/space/wbi/arc/search (WBI-signed, paginated)",
                "-- per video --",
                "GET /x/web-interface/view",
                "GET /x/tag/archive/tags",
                "GET /x/v2/reply/main (paginated)",
                "GET /x/v2/reply/reply (per thread with rcount>0)",
            ],
            "rate_limit": f"1.0s between API calls; {INTER_VIDEO_SLEEP_MIN}-{INTER_VIDEO_SLEEP_MAX}s random between videos",
            "note": "fetch-user is resume-safe: already-completed BVIDs are skipped on re-run.",
        },
    }
