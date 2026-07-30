#!/usr/bin/env python3
"""Generate video clips via multiple Chinese video generation providers.

Providers: Alibaba Bailian (Wan/PixVerse/Kling/Vidu/HappyHorse),
           Jimeng (Volcengine Ark), MiniMax (Hailuo), Hunyuan (Tencent).
Modes: text-to-video (t2v), image-to-video (i2v), first+last frame (kf2v),
reference-to-video (r2v). Tasks are async: submit -> poll -> download.

Usage:
  python generate_video.py "prompt" [output.mp4] [options]
  python generate_video.py "prompt" out.mp4 --image first.png              # i2v
  python generate_video.py "prompt" out.mp4 --image a.png --last-frame b.png  # kf2v
  python generate_video.py "@girl dancing" out.mp4 --ref girl=girl.png     # r2v
  python generate_video.py --task-id <id> --provider <name> out.mp4        # resume
  python generate_video.py schema <resource>                               # introspection
  python generate_video.py --list-models
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Allow imports from the providers package next to this script
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

from providers import get_provider, detect_provider, list_providers, register_providers
from providers.base import (
    GenerationRequest, VideoGenError, ConfigError, InputError, APIError,
    TaskFailedError, TaskTimeoutError,
    safe_request, emit_success, emit_error, emit_progress,
    stdout_is_tty, resolve_format, SCHEMA_VERSION,
)
from providers.base import safe_request as _safe_request


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def download_video(url: str, output_path: Path) -> int:
    """Download a video from URL, write to output_path, return byte count."""
    rsp = _safe_request("GET", url, timeout=300, label="Video download")
    if rsp.status_code != 200:
        raise APIError(
            f"video download failed (HTTP {rsp.status_code}): {rsp.text[:300]}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rsp.content)
    return len(rsp.content)


def parse_ref(ref: str) -> tuple[str | None, str]:
    """Parse --ref 'name=path_or_url' or plain 'path_or_url' -> (name, value)."""
    if "=" in ref:
        name, value = ref.split("=", 1)
        if name.isidentifier() and not os.path.exists(ref):
            return name, value
    return None, ref


def detect_mode(args) -> str:
    """Determine generation mode from input arguments."""
    if args.ref:
        return "r2v"
    if args.image and args.last_frame:
        return "kf2v"
    if args.image:
        return "i2v"
    return "t2v"


# --- Idempotency key cache (P2) ---------------------------------------

_IDEMPOTENCY_DIR = Path.home() / ".cache" / "videogen"


def _idempotency_path(key: str) -> Path:
    """Return cache path for an idempotency key."""
    safe = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _IDEMPOTENCY_DIR / f"{safe}.json"


def _check_idempotency(key: str) -> dict | None:
    """Check if this idempotency key was already used. Returns cached record or None."""
    p = _idempotency_path(key)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _store_idempotency(key: str, record: dict) -> None:
    """Store a task record for an idempotency key."""
    _IDEMPOTENCY_DIR.mkdir(parents=True, exist_ok=True)
    _idempotency_path(key).write_text(json.dumps(record, default=str))


def _detect_provider_from_task(task_id: str):
    """Detect provider from task ID format. Returns (provider, is_confident)."""
    if task_id.startswith("cgt-"):
        return get_provider("jimeng"), True
    if task_id.isdigit():
        return get_provider("minimax"), True
    return get_provider("bailian"), False


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

def _load_models_json() -> dict:
    """Load models.json from the docs directory (repo root or skill root)."""
    script_dir = Path(__file__).resolve().parent  # .../skills/videogencn/scripts
    skill_dir = script_dir.parent                  # .../skills/videogencn
    repo_dir = skill_dir.parent.parent             # repo root
    candidates = [
        repo_dir / "docs" / "models.json",
        skill_dir / "docs" / "models.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text())
    return {}


def cmd_schema(args, available):
    """schema <resource.action> — introspection endpoint for agents."""
    data = _load_models_json()
    target = args.schema_target

    # schema providers — list all providers
    if target == "providers" or target == "":
        providers = []
        for p in data.get("providers", []):
            providers.append({
                "id": p["id"],
                "name": p["name"],
                "full_name": p["full_name"],
                "api_key_env": p["api_key_env"],
                "model_count": len(p.get("models", [])),
            })
        emit_success(providers)
        return

    # schema <provider> — list models for a provider
    for p in data.get("providers", []):
        if target == p["id"]:
            models = []
            for m in p["models"]:
                models.append({
                    "name": m["name"],
                    "family": m["family"],
                    "modes": m["modes_en"],
                    "resolution": m["resolution"],
                    "duration": m["duration"],
                    "audio": m.get("audio", False),
                    "camera_control": m.get("camera_control", False),
                    "multi_shot": m.get("multi_shot", False),
                    "default": m.get("default", False),
                    "price": m.get("price", ""),
                    "use_case": m.get("use_case", ""),
                    "experimental": m.get("experimental", False),
                })
            emit_success(models, {"provider": p["id"], "provider_name": p["name"]})
            return

    # Fallback: unknown target
    emit_error("schema_not_found",
               f"Unknown resource '{target}'. Try 'providers' or a provider id: "
               + ", ".join(p["id"] for p in data.get("providers", [])),
               retryable=False)


# ---------------------------------------------------------------------------
# Cost estimation (for --dry-run)
# ---------------------------------------------------------------------------

def _estimate_cost(req: GenerationRequest, provider_name: str) -> dict:
    """Estimate cost from models.json data. Returns {min, max, currency}."""
    data = _load_models_json()
    for p in data.get("providers", []):
        if p["id"] == provider_name:
            for m in p["models"]:
                if m["name"] == req.model or m.get("full_name") == req.model:
                    price = m.get("price", "")
                    # Parse "$0.04–0.08/s" format
                    if "–" in price:
                        parts = price.replace("$", "").replace("/s", "").split("–")
                        try:
                            lo, hi = float(parts[0]), float(parts[1])
                            return {
                                "min": round(lo * req.duration, 3),
                                "max": round(hi * req.duration, 3),
                                "currency": "USD",
                            }
                        except (ValueError, IndexError):
                            pass
                    elif price and price != "—":
                        try:
                            v = float(price.replace("$", "").replace("/s", ""))
                            return {"min": round(v * req.duration, 3),
                                    "max": round(v * req.duration, 3), "currency": "USD"}
                        except ValueError:
                            pass
                    break
            break
    return {"min": None, "max": None, "currency": "USD", "note": "price data unavailable"}


# ---------------------------------------------------------------------------
# Output dispatcher
# ---------------------------------------------------------------------------

def _print_msg(fmt: str, msg: str, **kwargs) -> None:
    """Print a message: table mode → stderr; json mode → skip (use envelope)."""
    if fmt == "json":
        return  # JSON mode suppresses human prose; use emit_progress for status
    print(msg, **kwargs)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _run(args, available, fmt: str, *, parent_parser=None):
    # --- --help-providers -----------------------------------------------
    if getattr(args, 'help_providers', False):
        data = _load_models_json()
        for p in data.get("providers", []):
            if p["id"] not in available:
                continue
            pk = p["id"]
            print(f"=== {p['name']} ({pk}) ===")
            print(f"  {p['full_name']}")
            print(f"  {p['description']}")
            print(f"  API key: {p['api_key_env']} → {p['api_key_url']}")
            print(f"  Region: {p['region']}")
            if p.get("region_note"):
                print(f"  Note: {p['region_note']}")
            print(f"  Models: {len(p.get('models', []))}")
            for m in p.get("models", []):
                star = " ⭐" if m.get("default") else ""
                exp = " ⚠️" if m.get("experimental") else ""
                modes = ", ".join(m.get("modes_en", m.get("modes", [])))
                print(f"    {m['name']}{star}{exp} [{modes}] {m.get('price','')}")
            print()
        return

    # --- --list-models --------------------------------------------------
    if args.list_models:
        names = [args.provider] if args.provider else available
        models_data = {}
        for name in names:
            p = get_provider(name)
            models_data[name] = p.list_models_text()
        if fmt == "json":
            emit_success(models_data)
        else:
            for name, text in models_data.items():
                print(f"=== {name} ===")
                print(text)
                print()
        return

    # --- --task-id resume -----------------------------------------------
    if args.task_id:
        if args.provider:
            provider = get_provider(args.provider)
        else:
            provider, confident = _detect_provider_from_task(args.task_id)
            if not confident:
                msg = (f"cannot auto-detect provider from task ID '{args.task_id}'; "
                       f"defaulting to '{provider.name}'")
                _print_msg(fmt, f"Warning: {msg}", file=sys.stderr)
        _print_msg(fmt, f"Resuming task {args.task_id} via provider: {provider.name}",
                   file=sys.stderr)
        emit_progress("resume", task_id=args.task_id, provider=provider.name)
        start = time.time()
        video_url = provider.poll(args.task_id)
        output_path = Path(args.output)
        _print_msg(fmt, "Downloading video (result URLs expire after 24h)...", file=sys.stderr)
        size = download_video(video_url, output_path)
        elapsed = round(time.time() - start, 1)
        _print_msg(fmt, f"Saved: {output_path} ({size / 1024 / 1024:.1f} MB)", file=sys.stderr)
        emit_success({
            "output_path": str(output_path),
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 1),
        }, {"provider": provider.name, "task_id": args.task_id, "elapsed_s": elapsed})
        return

    # --- Normal generation ----------------------------------------------
    if not args.prompt:
        if parent_parser:
            parent_parser.error("prompt is required (or use --task-id / --list-models / schema)")
        else:
            raise InputError("prompt is required (or use --task-id / --list-models / schema)")
    if args.last_frame and not args.image:
        raise InputError("--last-frame requires --image (the first frame)")

    # Provider selection
    if args.provider:
        provider = get_provider(args.provider)
    else:
        provider = detect_provider(args.model)

    # Mode detection
    mode = detect_mode(args)
    if mode not in provider.supported_modes:
        raise InputError(
            f"provider '{provider.name}' does not support mode '{mode}'. "
            f"Supported: {', '.join(provider.supported_modes)}")

    # Model selection
    model_env = provider.model_env_var
    model = (args.model
             or (os.environ.get(model_env) if model_env else None)
             or provider.default_models[mode])
    provider.check_mode(model, mode)

    # Build GenerationRequest
    req = GenerationRequest(
        prompt=args.prompt,
        mode=mode,
        model=model,
        duration=args.duration,
        resolution=args.resolution,
        ratio=args.ratio,
        size=args.size,
        negative=args.negative,
        seed=args.seed,
        no_prompt_extend=args.no_prompt_extend,
        no_prompt_optimizer=args.no_prompt_optimizer,
        audio=args.audio,
        no_audio=args.no_audio,
        camera_motion=args.camera_motion,
    )
    provider.validate_params(req)

    # --- --dry-run ------------------------------------------------------
    if args.dry_run:
        # Resolve media (for preview only — skip actual upload)
        image_url = last_url = None
        refs_preview = []
        if args.image:
            image_url = args.image if args.image.startswith(("http", "data:")) else f"<local:{args.image}>"
        if args.last_frame:
            last_url = args.last_frame if args.last_frame.startswith(("http", "data:")) else f"<local:{args.last_frame}>"
        for ref in args.ref:
            name, value = parse_ref(ref)
            refs_preview.append([name, value])

        body = provider.build_body(req, image_url, last_url,
                                   [(n, v) for n, v in refs_preview])
        cost = _estimate_cost(req, provider.name)
        emit_success({
            "dry_run": True,
            "would_submit": {
                "provider": provider.name,
                "model": model,
                "mode": mode,
                "body": body,
            },
            "estimated_cost": cost,
        }, {"provider": provider.name, "model": model, "mode": mode})
        return

    # Resolve media (real upload)
    oss_used = False
    image_url = last_url = None
    if args.image:
        image_url, oss = provider.resolve_media(args.image, model)
        oss_used = oss_used or oss
    if args.last_frame:
        last_url, oss = provider.resolve_media(args.last_frame, model)
        oss_used = oss_used or oss
    refs = []
    for ref in args.ref:
        name, value = parse_ref(ref)
        resolved, oss = provider.resolve_media(value, model)
        refs.append((name, resolved))
        oss_used = oss_used or oss

    # Build body, submit, poll
    body = provider.build_body(req, image_url, last_url, refs)
    _print_msg(fmt, f"Model: {model} (provider: {provider.name}, mode: {mode})", file=sys.stderr)
    emit_progress("submit", provider=provider.name, model=model, mode=mode)

    start = time.time()

    # Idempotency: check for cached task before submitting
    idem_key = getattr(args, 'idempotency_key', None)
    cached = _check_idempotency(idem_key) if idem_key else None
    if cached and cached.get("provider") == provider.name:
        task_id = cached["task_id"]
        _print_msg(fmt, f"Idempotency hit: reusing task {task_id}", file=sys.stderr)
        emit_progress("idempotency_hit", task_id=task_id, key=idem_key)
    else:
        task_id = provider.submit(body, oss_used=oss_used)
        _print_msg(fmt, f"Task submitted: {task_id}", file=sys.stderr)
        if idem_key:
            _store_idempotency(idem_key, {
                "task_id": task_id, "provider": provider.name,
                "model": model, "mode": mode, "created": time.time()})

    emit_progress("submitted", task_id=task_id, provider=provider.name)
    video_url = provider.poll(task_id)

    _print_msg(fmt, "Downloading video (result URLs expire after 24h)...", file=sys.stderr)
    emit_progress("download", task_id=task_id)
    output_path = Path(args.output)
    size = download_video(video_url, output_path)
    elapsed = round(time.time() - start, 1)
    _print_msg(fmt, f"Saved: {output_path} ({size / 1024 / 1024:.1f} MB)", file=sys.stderr)

    emit_success({
        "output_path": str(output_path),
        "size_bytes": size,
        "size_mb": round(size / 1024 / 1024, 1),
        "task_id": task_id,
        "video_url": video_url,
    }, {"provider": provider.name, "model": model, "mode": mode, "elapsed_s": elapsed})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    register_providers()
    available = list_providers()

    # Handle schema subcommand before full parsing
    if len(sys.argv) > 1 and sys.argv[1] == "schema":
        schema_target = sys.argv[2] if len(sys.argv) > 2 else "providers"
        register_providers()
        cmd_schema(argparse.Namespace(schema_target=schema_target), available)
        return

    parser = argparse.ArgumentParser(
        description="Generate video via Chinese video models "
                    "(Bailian Wan/PixVerse/Kling/Vidu/HappyHorse, Jimeng, MiniMax, Hunyuan)")
    parser.add_argument("prompt", nargs="?", help="video description")
    parser.add_argument("output", nargs="?", default="./generated-video.mp4",
                        help="output MP4 path (default: ./generated-video.mp4)")
    parser.add_argument("-m", "--model", help="model name (default: auto by mode)")
    parser.add_argument("--provider", choices=available,
                        help=f"provider backend (default: auto-detect; available: {', '.join(available)})")
    parser.add_argument("-i", "--image", help="first-frame image (path or URL) -> i2v")
    parser.add_argument("--last-frame", help="last-frame image (with --image) -> kf2v")
    parser.add_argument("--ref", action="append", default=[],
                        help="reference image 'name=path_or_url' (repeatable) -> r2v")
    parser.add_argument("-d", "--duration", type=int, default=5,
                        help="duration in seconds (default: 5)")
    parser.add_argument("-r", "--resolution", default="1080P",
                        choices=["360P", "480P", "540P", "720P", "1080P"],
                        help="output resolution (default: 1080P)")
    parser.add_argument("--ratio", default="16:9",
                        choices=["16:9", "9:16", "1:1", "3:4", "4:3", "21:9"],
                        help="aspect ratio (default: 16:9)")
    parser.add_argument("-s", "--size", help="exact size 'W*H' for size-based models")
    parser.add_argument("-n", "--negative", help="negative prompt (Wan only)")
    parser.add_argument("--no-prompt-extend", action="store_true",
                        help="disable automatic prompt rewriting (Wan only)")
    parser.add_argument("--no-prompt-optimizer", action="store_true",
                        help="disable built-in prompt optimizer (MiniMax only)")
    parser.add_argument("--audio", action="store_true",
                        help="enable audio on PixVerse/Kling/Vidu/Jimeng")
    parser.add_argument("--no-audio", action="store_true",
                        help="silent output on Wan models that default to audio")
    parser.add_argument("--camera-motion",
                        help="camera motion description (Jimeng Seedance 2.0)")
    parser.add_argument("--seed", type=int, help="random seed for reproducibility")
    parser.add_argument("--idempotency-key",
                        help="[WRITE] client-supplied key; retries reuse cached task")
    parser.add_argument("--task-id", help="[WRITE] resume polling an existing task")
    parser.add_argument("--dry-run", action="store_true",
                        help="[READ] preview request body + cost estimate without submitting")
    parser.add_argument("--format", choices=["json", "table"], default=None,
                        help="output format (default: table in TTY, json otherwise)")
    parser.add_argument("--list-models", action="store_true",
                        help="[READ] list all models and exit")
    parser.add_argument("--help-providers", action="store_true",
                        help="[READ] show provider details and exit")
    args = parser.parse_args()
    fmt = resolve_format(args.format)

    try:
        _run(args, available, fmt, parent_parser=parser)
    except ConfigError as e:
        if fmt == "json":
            emit_error("config_error", str(e), retryable=False)
        else:
            print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except InputError as e:
        if fmt == "json":
            emit_error("input_error", str(e), retryable=False)
        else:
            print(f"Input error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except APIError as e:
        if fmt == "json":
            emit_error("api_error", str(e), retryable=True)
        else:
            print(f"API error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except TaskFailedError as e:
        if fmt == "json":
            emit_error("task_failed", str(e), retryable=False)
        else:
            print(f"Task failed: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except TaskTimeoutError as e:
        if fmt == "json":
            emit_error("task_timeout", str(e), retryable=True)
        else:
            print(f"Timeout: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except VideoGenError as e:
        if fmt == "json":
            emit_error("error", str(e), retryable=False)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
