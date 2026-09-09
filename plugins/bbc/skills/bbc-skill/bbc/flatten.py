"""Convert raw API replies into flat JSONL rows."""

from datetime import datetime, timezone


def _iso_utc(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except (ValueError, OverflowError, OSError):
        return ""


def _ip_location(reply: dict) -> str:
    raw = (reply.get("reply_control", {}) or {}).get("location") or ""
    member_loc = (reply.get("member", {}) or {}).get("ip_location") or ""
    val = raw or member_loc
    if not val:
        return ""
    # Strip "IP属地：" or "IP属地:" prefix
    for prefix in ("IP属地：", "IP属地:"):
        if val.startswith(prefix):
            return val[len(prefix):].strip()
    return val.strip()


def _members_mentions(content: dict) -> list[dict]:
    members = content.get("members") or []
    out = []
    for m in members:
        if isinstance(m, dict):
            out.append({"mid": m.get("mid"), "uname": m.get("uname") or m.get("name")})
    return out


def _jump_urls(content: dict) -> list[str]:
    jump = content.get("jump_url") or {}
    if isinstance(jump, dict):
        return sorted({str(k) for k in jump.keys()})
    return []


def flatten_reply(reply: dict, *, bvid: str, owner_mid: int | None, top_type: int = 0) -> dict:
    """One API reply dict -> one JSONL row (omits sub-replies; caller flattens those)."""
    member = reply.get("member") or {}
    content = reply.get("content") or {}
    ctime = int(reply.get("ctime") or 0)
    mid = int(member.get("mid") or 0)
    level = ((member.get("level_info") or {}).get("current_level")) or 0
    vip_info = (member.get("vip") or {})
    vip = bool(vip_info.get("vipStatus") or vip_info.get("status"))

    return {
        "rpid": int(reply.get("rpid") or 0),
        "rpid_str": str(reply.get("rpid_str") or reply.get("rpid") or ""),
        "oid": int(reply.get("oid") or 0),
        "bvid": bvid,
        "parent": int(reply.get("parent") or 0),
        "root": int(reply.get("root") or 0),
        "mid": mid,
        "uname": member.get("uname") or "",
        "user_level": int(level),
        "vip": vip,
        "sex": member.get("sex") or "",
        "ctime": ctime,
        "ctime_iso": _iso_utc(ctime),
        "message": content.get("message") or "",
        "like": int(reply.get("like") or 0),
        "rcount": int(reply.get("rcount") or 0),
        "ip_location": _ip_location(reply),
        "is_up_reply": bool(owner_mid and mid == owner_mid),
        "top_type": int(top_type),
        "mentioned_users": _members_mentions(content),
        "jump_urls": _jump_urls(content),
    }
