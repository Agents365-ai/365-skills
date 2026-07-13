"""Voice cloning for ttsCN — create/list/delete cloned voices.

Phase 1 platforms (pure-API, lowest friction):
  minimax    — upload local file (or URL) -> clone. Paid: ~$1.5/voice on the
               global site, ~9.9 RMB charged on first synthesis on the China
               site. A new clone is temporary: it must be used in a real
               synthesis call (previews don't count) within 7 days (global
               site) / 48 h (China site) of creation or MiniMax deletes it;
               after that first use it is kept permanently.
  cosyvoice  — DashScope voice enrollment. Enrollment is free (synthesis
               billed normally) but the reference audio MUST be a public
               http(s) URL; voices expire after 1 year of no synthesis use.

Cloned voices are stored under "cloned_voices" in ~/.ttsCN.json so they can
be referenced by name: `tts.py "text" out.wav --platform minimax --voice myvoice`.

Compliance: both platforms contractually require that you clone only your own
voice or one you have the rights-holder's explicit consent for.

Usage:
    tts.py clone create --platform minimax   --audio my.wav --name myvoice [--yes]
    tts.py clone create --platform cosyvoice --audio https://.../my.wav --name myvoice
    tts.py clone list
    tts.py clone delete --name myvoice [--remote]
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output import (  # noqa: E402
    emit_success, emit_error,
    EXIT_VALIDATION, EXIT_AUTH, EXIT_BACKEND,
)

CLONE_PLATFORMS = ("minimax", "cosyvoice")
USER_CONFIG = os.path.expanduser("~/.ttsCN.json")
MINIMAX_BASE = os.environ.get("MINIMAX_API_BASE", "https://api.minimax.io/v1")


# ── Named-voice store (~/.ttsCN.json "cloned_voices") ───────────────────────

def _load_config():
    try:
        with open(USER_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_voices(voices):
    config = _load_config()
    config["cloned_voices"] = voices
    with open(USER_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_voices():
    return _load_config().get("cloned_voices", {})


def resolve_cloned_voice(backend, voice):
    """If `voice` names a stored clone for `backend`, return its record.

    Called from tts.py voice resolution. Returns the record dict
    ({voice_id, target_model, ...}) or None.
    """
    rec = load_voices().get(voice)
    if rec and rec.get("platform") == backend:
        return rec
    return None


# ── MiniMax ─────────────────────────────────────────────────────────────────

def _minimax_voice_id(name):
    """Derive an API-legal voice_id: 8-256 chars, starts with a letter,
    [A-Za-z0-9_-], must not end in - or _."""
    base = re.sub(r"[^A-Za-z0-9_-]", "", name) or "voice"
    if not base[0].isalpha():
        base = "v" + base
    vid = f"{base}_{uuid.uuid4().hex[:8]}"
    return vid[:256]


def minimax_create(audio, name, voice_id=None):
    """Upload reference audio and create a MiniMax clone. Returns record."""
    import requests

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit(emit_error(
            "auth_missing_env", "MINIMAX_API_KEY not set",
            backend="minimax", exit_code=EXIT_AUTH))
    headers = {"Authorization": f"Bearer {api_key}"}

    # Reference audio: local file preferred; URLs are downloaded first.
    if re.match(r"https?://", audio):
        resp = requests.get(audio, timeout=120)
        resp.raise_for_status()
        content = resp.content
        filename = os.path.basename(audio.split("?")[0]) or "sample.wav"
    else:
        if not os.path.isfile(audio):
            raise SystemExit(emit_error(
                "input_not_found", f"Audio file not found: {audio}",
                field="audio", exit_code=EXIT_VALIDATION))
        with open(audio, "rb") as f:
            content = f.read()
        filename = os.path.basename(audio)

    print("  Uploading reference audio ...", file=sys.stderr)
    r = requests.post(f"{MINIMAX_BASE}/files/upload", headers=headers,
                      data={"purpose": "voice_clone"},
                      files={"file": (filename, content)}, timeout=300)
    if r.status_code != 200:
        raise SystemExit(emit_error(
            "backend_error", f"MiniMax upload failed {r.status_code}: {r.text[:300]}",
            backend="minimax", retryable=True, exit_code=EXIT_BACKEND))
    body = r.json()
    file_id = (body.get("file") or {}).get("file_id")
    if not file_id:
        raise SystemExit(emit_error(
            "backend_error", f"MiniMax upload returned no file_id: {json.dumps(body)[:300]}",
            backend="minimax", exit_code=EXIT_BACKEND))

    vid = voice_id or _minimax_voice_id(name)
    print(f"  Creating clone '{vid}' ...", file=sys.stderr)
    r = requests.post(f"{MINIMAX_BASE}/voice_clone",
                      headers={**headers, "Content-Type": "application/json"},
                      json={"file_id": file_id, "voice_id": vid}, timeout=300)
    if r.status_code != 200:
        raise SystemExit(emit_error(
            "backend_error", f"MiniMax voice_clone failed {r.status_code}: {r.text[:300]}",
            backend="minimax", retryable=True, exit_code=EXIT_BACKEND))
    body = r.json()
    status = (body.get("base_resp") or {}).get("status_code", 0)
    if status != 0:
        raise SystemExit(emit_error(
            "backend_error",
            f"MiniMax voice_clone error {status}: "
            f"{(body.get('base_resp') or {}).get('status_msg', 'unknown')}",
            backend="minimax", exit_code=EXIT_BACKEND))

    return {
        "platform": "minimax", "voice_id": vid,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": audio,
        "note": "temporary until first real synthesis — deleted if not used "
                "within 7 days (global site) / 48h (China site) of creation",
    }


# ── CosyVoice (DashScope enrollment) ────────────────────────────────────────

def _cosyvoice_prefix(name):
    """Enrollment prefix: lowercase letters + digits, <10 chars."""
    return (re.sub(r"[^a-z0-9]", "", name.lower()) or "voice")[:9]


def cosyvoice_create(audio, name, target_model):
    """Enroll a CosyVoice clone from a public audio URL. Returns record."""
    if not os.environ.get("DASHSCOPE_API_KEY"):
        raise SystemExit(emit_error(
            "auth_missing_env", "DASHSCOPE_API_KEY not set",
            backend="cosyvoice", exit_code=EXIT_AUTH))
    if not re.match(r"https?://", audio):
        raise SystemExit(emit_error(
            "validation_failed",
            "CosyVoice enrollment requires a PUBLIC http(s) URL for --audio "
            "(DashScope does not accept local files; host the sample, e.g. on "
            "OSS, and pass its URL). 10-20s WAV/MP3/M4A, >=16kHz, <=10MB.",
            field="audio", exit_code=EXIT_VALIDATION))
    try:
        from dashscope.audio.tts_v2 import VoiceEnrollmentService
    except ImportError:
        raise SystemExit(emit_error(
            "tool_missing", "'dashscope' not installed. Run: pip install dashscope",
            backend="cosyvoice", exit_code=EXIT_VALIDATION))

    print(f"  Enrolling voice (target_model={target_model}) ...", file=sys.stderr)
    service = VoiceEnrollmentService()
    try:
        voice_id = service.create_voice(
            target_model=target_model,
            prefix=_cosyvoice_prefix(name),
            url=audio,
        )
    except Exception as e:
        raise SystemExit(emit_error(
            "backend_error", f"DashScope enrollment failed: {e}",
            backend="cosyvoice", retryable=True, exit_code=EXIT_BACKEND))

    return {
        "platform": "cosyvoice", "voice_id": voice_id,
        "target_model": target_model,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": audio,
        "note": "expires after 1 year without synthesis use; enrollment free",
    }


def cosyvoice_delete_remote(voice_id):
    from dashscope.audio.tts_v2 import VoiceEnrollmentService
    VoiceEnrollmentService().delete_voice(voice_id)


# ── CLI ─────────────────────────────────────────────────────────────────────

def build_clone_parser():
    p = argparse.ArgumentParser(
        prog="tts.py clone",
        description="Create and manage cloned voices (minimax / cosyvoice). "
                    "Clone only your own voice or one you are authorized to use.")
    sub = p.add_subparsers(dest="action", required=True, metavar="<action>")

    sp = sub.add_parser("create", help="Clone a voice from reference audio")
    sp.add_argument("--platform", required=True, choices=CLONE_PLATFORMS)
    sp.add_argument("--audio", required=True,
                    help="Reference audio: local file or URL for minimax; "
                         "public URL only for cosyvoice (10-20s recommended)")
    sp.add_argument("--name", required=True,
                    help="Local name to store the voice under (use as --voice later)")
    sp.add_argument("--voice-id", dest="voice_id",
                    help="minimax only: explicit voice_id (8-256 chars, starts "
                         "with a letter; default: derived from --name)")
    sp.add_argument("--target-model", dest="target_model",
                    help="cosyvoice only: enrollment model, must match the model "
                         "used at synthesis (default: $COSYVOICE_MODEL or cosyvoice-v3-flash)")
    sp.add_argument("--yes", "--no-input", action="store_true", dest="yes",
                    help="Confirm paid clone creation (required for minimax)")
    sp.add_argument("--format", choices=("json", "text"), default=None)

    sp = sub.add_parser("list", help="List locally stored cloned voices")
    sp.add_argument("--platform", choices=CLONE_PLATFORMS)
    sp.add_argument("--format", choices=("json", "text"), default=None)

    sp = sub.add_parser("delete", help="Remove a stored voice (local by default)")
    sp.add_argument("--name", required=True)
    sp.add_argument("--remote", action="store_true",
                    help="Also delete on the platform (cosyvoice only)")
    sp.add_argument("--format", choices=("json", "text"), default=None)

    return p


def handle_clone(argv):
    """Entry point for `tts.py clone ...`. Always exits."""
    started_at = time.time()
    args = build_clone_parser().parse_args(argv)
    voices = load_voices()

    if args.action == "create":
        if args.name in voices:
            emit_error("validation_failed",
                       f"Name '{args.name}' already exists "
                       f"(voice_id {voices[args.name].get('voice_id')}). "
                       "Delete it first or pick another name.",
                       field="name", exit_code=EXIT_VALIDATION, started_at=started_at)
        if args.platform == "minimax":
            if not args.yes:
                emit_error("confirmation_required",
                           "MiniMax voice cloning is PAID (~$1.5/voice on the "
                           "global site; ~9.9 RMB on first use on the China site). "
                           "A new clone is temporary — use it in a real synthesis "
                           "within 7 days (global) / 48h (China site) or it is "
                           "deleted. Re-run with --yes to confirm.",
                           exit_code=EXIT_VALIDATION, started_at=started_at)
            record = minimax_create(args.audio, args.name, args.voice_id)
        else:
            target_model = (args.target_model
                            or os.environ.get("COSYVOICE_MODEL", "cosyvoice-v3-flash"))
            record = cosyvoice_create(args.audio, args.name, target_model)

        voices[args.name] = record
        _save_voices(voices)
        print(f"  ✓ Cloned voice stored as '{args.name}' -> {record['voice_id']}",
              file=sys.stderr)
        print(f"  Use it: tts.py \"text\" out.wav --platform {args.platform} "
              f"--voice {args.name}", file=sys.stderr)
        emit_success({"name": args.name, **record}, started_at=started_at)

    if args.action == "list":
        items = {n: r for n, r in voices.items()
                 if not args.platform or r.get("platform") == args.platform}
        for n, r in items.items():
            print(f"  {n:<20} {r.get('platform', '?'):<10} {r.get('voice_id', '?')}"
                  f"  ({r.get('created', '?')})", file=sys.stderr)
        emit_success({"voices": items, "count": len(items)}, started_at=started_at)

    if args.action == "delete":
        rec = voices.get(args.name)
        if not rec:
            emit_error("validation_failed", f"No stored voice named '{args.name}'",
                       field="name", exit_code=EXIT_VALIDATION, started_at=started_at)
        remote_deleted = False
        if args.remote:
            if rec.get("platform") == "cosyvoice":
                try:
                    cosyvoice_delete_remote(rec["voice_id"])
                    remote_deleted = True
                except Exception as e:
                    emit_error("backend_error",
                               f"Remote delete failed (local record kept): {e}",
                               backend="cosyvoice", retryable=True,
                               exit_code=EXIT_BACKEND, started_at=started_at)
            else:
                print("  MiniMax remote delete is not implemented in this CLI — "
                      "never-used clones expire on their own (7 days global / "
                      "48h China site); removing local record only.",
                      file=sys.stderr)
        del voices[args.name]
        _save_voices(voices)
        emit_success({"deleted": args.name, "remote_deleted": remote_deleted,
                      "voice_id": rec.get("voice_id")}, started_at=started_at)
