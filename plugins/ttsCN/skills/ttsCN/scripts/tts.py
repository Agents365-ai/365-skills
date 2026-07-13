#!/usr/bin/env python3
"""
ttsCN — Multi-Platform Chinese TTS Script (agent-native v1.1.0)

Generate speech audio from text using 8 China-friendly TTS backends.

Usage:
    tts.py "你好世界" output.wav
    tts.py --idempotency-key my-job-42 "你好" out.wav
    tts.py --format json --list
    tts.py --list --fields name,cost,supports_clone
    tts.py schema backends
    tts.py schema backends.doubao
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backends import (
    BACKENDS, VOICES, VOICE_DESCRIPTIONS, TAGS,
    init_backend, get_synthesize_func, get_max_chars,
    resolve_backend, resolve_voice, resolve_speech_rate,
    BackendError, MissingPackageError, MissingEnvVarError,
    UnknownBackendError,
)
from output import (
    use_json, envelope, success, error, emit_success, emit_error,
    EXIT_OK, EXIT_INTERNAL, EXIT_VALIDATION, EXIT_AUTH, EXIT_BACKEND,
    exit_for_error_code, SCHEMA_VERSION, VERSION,
)
import idempotency

DEFAULT_BACKEND = "edge"

# Compact fields for default JSON list (keep agent token cost low)
_COMPACT_FIELDS = [
    "id", "name", "provider", "cost", "cost_per_10k",
    "voices_count", "max_chars", "max_duration_display",
    "supports_ssml", "supports_clone", "tags",
]

# ── Text chunking ─────────────────────────────────────────────────────────

_SOFT_PUNCT = "，,;：:、 "
_END_PUNCT = ("。", ".", "!", "?", "！", "？")
_PROSODIC_END = _END_PUNCT + tuple(_SOFT_PUNCT.replace(" ", ""))


def _hard_split(sentence, max_chars):
    if len(sentence) <= max_chars:
        return [sentence]
    budget = max_chars - 1
    lookback = max(8, max_chars // 4)
    pieces = []
    buf = ""
    for ch in sentence:
        buf += ch
        if len(buf) >= budget:
            cut = -1
            for j in range(len(buf) - 1, max(-1, len(buf) - lookback - 1), -1):
                if buf[j] in _SOFT_PUNCT:
                    cut = j
                    break
            if cut >= 0:
                pieces.append(buf[:cut + 1])
                buf = buf[cut + 1:]
            else:
                pieces.append(buf + "，")
                buf = ""
    if buf:
        pieces.append(buf)
    return pieces


def chunk_text(text, max_chars):
    normalized = text.replace("；", "。")
    raw = re.split(r"(?<=[。.!?！？])\s*", normalized)
    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        sentences.extend(_hard_split(s, max_chars))
    chunks = []
    current = ""
    for s in sentences:
        suffix = "" if s.endswith(_PROSODIC_END) else "。"
        addition = s + suffix
        if len(current) + len(addition) <= max_chars:
            current += addition
        else:
            if current:
                chunks.append(current)
            current = addition
    if current:
        chunks.append(current)
    return chunks


# ── Formatting ────────────────────────────────────────────────────────────

def _resolve_voice_name(backend, voice_id):
    desc = VOICE_DESCRIPTIONS.get(voice_id, voice_id)
    return desc


def _backend_json(name, compact=False):
    """Build JSON-safe backend summary."""
    info = BACKENDS[name]
    full = {
        "id": name,
        "name": info.get("name", name),
        "provider": info.get("provider", ""),
        "cost": info.get("cost", ""),
        "cost_per_10k": info.get("cost_per_10k", ""),
        "max_chars": info["max_chars"],
        "max_duration_sec": info["max_duration_sec"],
        "max_duration_display": info.get("max_duration_display", ""),
        "voices_count": info.get("voices_count", ""),
        "supports_ssml": info["supports_ssml"],
        "supports_clone": info.get("supports_clone", False),
        "clone_detail": info.get("clone_detail", ""),
        "supports_emotion": info.get("supports_emotion", ""),
        "supports_dialects": info.get("supports_dialects", ""),
        "languages": info.get("languages", ""),
        "streaming": info.get("streaming", ""),
        "setup_label": info.get("setup_label", ""),
        "tags": info.get("tags", []),
        "env_vars": info["env"],
        "pip_install": info.get("import", ("", "", ""))[2] if isinstance(info.get("import"), tuple) else "",
        "get_key_url": info.get("get_key_url", ""),
        "voices": [
            {"id": v, "description": VOICE_DESCRIPTIONS.get(v, "")}
            for v in VOICES.get(name, [])
        ],
    }
    if compact:
        return {k: v for k, v in full.items() if k in _COMPACT_FIELDS}
    return full


def _list_json(args_fields=None, full=False):
    """Build list output dict (for JSON envelope)."""
    compact = not full  # compact by default
    all_backends = []
    for name in BACKENDS:
        bj = _backend_json(name, compact=compact)
        if args_fields:
            fset = set(args_fields.split(","))
            bj = {k: v for k, v in bj.items() if k in fset}
        all_backends.append(bj)
    result = {"backends": all_backends, "tags": TAGS}
    if not full:
        result["note"] = "Compact mode — use --full for all fields"
    return result


def _list_text(args_fields=None):
    """Print human-readable backend list (for TTY)."""
    print("Available TTS backends:\n")
    for name, info in BACKENDS.items():
        tag = " (default)" if name == DEFAULT_BACKEND else ""
        print(f"  {name}{tag}")
        print(f"      {info['description']}")
        print(f"      Voices:        {info['voices_count']}")
        print(f"      Max chars:     {info['max_chars']} / chunk")
        print(f"      Max duration:  ~{info['max_duration_sec']}s / chunk")
        print(f"      SSML:          {'✅ yes' if info['supports_ssml'] else '❌ no'}")
        if info.get('supports_clone'):
            print(f"      Clone:         ✅ yes — {info.get('clone_detail','')}")
        else:
            print(f"      Clone:         ❌ no")
        envs = ", ".join(info["env"]) if info["env"] else "none required"
        print(f"      Env vars:      {envs}")
        print()

    print("Voice presets:\n")
    for backend, voice_list in VOICES.items():
        print(f"  [{backend}]")
        for v in voice_list[:6]:
            desc = VOICE_DESCRIPTIONS.get(v, "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {v}{desc_str}")
        if len(voice_list) > 6:
            print(f"    ... and {len(voice_list) - 6} more")
        print()

    print("Config files:")
    print("  Project: ./.ttsCN.json")
    print("  User:    ~/.ttsCN.json")
    print()
    print("Env vars (precedence over config files):")
    print("  TTS_BACKEND, TTS_VOICE, TTS_RATE")


# ── Schema subcommand ─────────────────────────────────────────────────────

def _handle_schema(args):
    path = args.path
    full = getattr(args, "full", False)

    if not path or path == "backends":
        data = _list_json(full=full)
        if hasattr(args, "fields") and args.fields:
            fset = set(args.fields.split(","))
            data["backends"] = [
                {k: v for k, v in b.items() if k in fset}
                for b in data["backends"]
            ]
        emit_success(data)

    if path.startswith("backends."):
        bid = path.split(".", 1)[1]
        if bid not in BACKENDS:
            emit_error("validation_failed", f"Unknown backend: {bid}",
                       field="path", retryable=False, exit_code=EXIT_VALIDATION)
        data = _backend_json(bid, compact=not full)
        if hasattr(args, "fields") and args.fields:
            fset = set(args.fields.split(","))
            data = {k: v for k, v in data.items() if k in fset}
        emit_success(data)

    if path == "voices":
        data = {}
        for name in BACKENDS:
            data[name] = [
                {"id": v, "description": VOICE_DESCRIPTIONS.get(v, "")}
                for v in VOICES.get(name, [])
            ]
        emit_success(data)

    if path == "tags":
        emit_success({"tags": TAGS})

    if path == "version":
        emit_success({"version": VERSION, "schema_version": SCHEMA_VERSION,
                       "providers_updated": _get_providers_updated()})

    emit_error("validation_failed",
               "Unknown schema path: {}. Use: backends, backends.<id>, voices, tags, version".format(path),
               field="path", retryable=False, exit_code=EXIT_VALIDATION)


def _ensure_mp3(output_file, started_at):
    """Transcode output_file to MP3 in place if it isn't MP3 already."""
    import subprocess
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=format_name",
         "-of", "csv=p=0", output_file],
        capture_output=True, text=True,
    )
    if "mp3" in probe.stdout:
        return
    tmp_file = output_file + ".transcode.mp3"
    conv = subprocess.run(
        ["ffmpeg", "-y", "-i", output_file,
         "-codec:a", "libmp3lame", "-qscale:a", "2", tmp_file],
        capture_output=True, text=True,
    )
    if conv.returncode != 0:
        emit_error("backend_error",
                   "MP3 transcode failed: {}".format(conv.stderr[-200:]),
                   retryable=False, exit_code=EXIT_BACKEND,
                   started_at=started_at)
    os.replace(tmp_file, output_file)


def _get_providers_updated():
    try:
        import json
        # data/ sits at the skill root, one level above scripts/
        _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _path = os.path.join(_ROOT, "data", "providers.json")
        with open(_path) as f:
            return json.load(f).get("updated", "unknown")
    except Exception:
        return "unknown"


# ── CLI ───────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Multi-platform Chinese TTS text-to-speech synthesis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "你好世界" output.wav
  %(prog)s --idempotency-key job-42 "你好" out.wav
  %(prog)s --platform doubao "你好" weather.wav
  %(prog)s --voice zh-CN-YunxiNeural --rate +10%% "text" out.wav
  %(prog)s --input script.txt output.wav
  %(prog)s --format json --list
  %(prog)s --list --full --fields name,cost,supports_clone
  %(prog)s --dry-run "预览文本"
  %(prog)s schema backends
  %(prog)s schema backends.doubao
  %(prog)s clone create --platform minimax --audio my.wav --name myvoice --yes
  %(prog)s "正文" out.wav --platform minimax --voice myvoice
        """,
    )

    # Input
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("text", nargs="?", help="Text to synthesize (inline)")
    input_group.add_argument("--input", "-i", help="Read text from file")

    parser.add_argument("output", nargs="?", default=None, help="Output audio file path")

    # Backend & voice
    parser.add_argument("--platform", "-p", choices=list(BACKENDS.keys()),
                        help="TTS backend (default: edge)")
    parser.add_argument("--voice", "-v", help="Voice name")
    parser.add_argument("--rate", "-r", help="Speech rate, e.g. '+5%%', '-10%%'")

    # Output format
    parser.add_argument("--format", "-f", choices=["wav", "mp3", "json"], default=None,
                        help="Output format: wav, mp3 (audio), or json (envelope)")

    # Idempotency
    parser.add_argument("--idempotency-key",
                        help="Idempotency key — retried calls with same key return cached result")

    # Agent compatibility (no-ops — ttsCN never prompts interactively)
    parser.add_argument("--yes", "--no-input", action="store_true", dest="no_input",
                        help="Skip confirmation prompts (no-op, accepted for agent compatibility)")

    # Info / preview
    parser.add_argument("--list", action="store_true", help="List backends and voices")
    parser.add_argument("--fields", help="Filter --list output: comma-separated field names (json only)")
    parser.add_argument("--full", action="store_true",
                        help="Show all fields in --list/schema JSON (default: compact)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview synthesis without API call")

    return parser


def _resolve_format(args):
    if args.format:
        return args.format
    if os.environ.get("TTS_FORMAT"):
        return os.environ["TTS_FORMAT"]
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return "json"
    return None


def _resolve_backend_config(args):
    if args.platform:
        backend, backend_src = args.platform, "cli"
    else:
        backend, backend_src = resolve_backend()
    if args.voice:
        voice, voice_src = args.voice, "cli"
    else:
        voice, voice_src = resolve_voice(backend)
    if args.rate:
        rate, rate_src = args.rate, "cli"
    else:
        rate, rate_src = resolve_speech_rate()

    # Named cloned voice? Substitute the platform voice_id (see clone.py).
    from clone import resolve_cloned_voice
    cloned = resolve_cloned_voice(backend, voice)
    if cloned:
        voice, voice_src = cloned["voice_id"], "cloned:" + voice
        if backend == "cosyvoice" and cloned.get("target_model"):
            # Synthesis model must match the enrollment target_model.
            os.environ["COSYVOICE_MODEL"] = cloned["target_model"]
    return backend, backend_src, voice, voice_src, rate, rate_src


def _resolve_output(args, backend, fmt):
    if args.output:
        return args.output
    if fmt in ("wav", "mp3"):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "ttsCN-{}-{}.{}".format(backend, ts, fmt)
    return None


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "clone":
        from clone import handle_clone
        handle_clone(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "schema":
        sp = argparse.ArgumentParser(description="Query provider registry as JSON")
        sp.add_argument("path", nargs="?", default="backends",
                        help="Resource: backends, backends.<id>, voices, tags, version")
        sp.add_argument("--fields", help="Comma-separated field filter")
        sp.add_argument("--full", action="store_true", help="Show all fields (default: compact)")
        _handle_schema(sp.parse_args(sys.argv[2:]))
        return

    parser = build_parser()
    args = parser.parse_args()
    started_at = time.time()

    json_mode = (output_fmt == "json") if (output_fmt := _resolve_format(args)) else False
    try:
        return _run(args, started_at, json_mode)
    finally:
        pass


def _run(args, started_at, json_mode=False):
    output_fmt = _resolve_format(args)
    if json_mode is False:
        json_mode = (output_fmt == "json")
    _diag = sys.stderr if json_mode else sys.stdout

    # ── --list ────────────────────────────────────────────────────────────
    if args.list:
        if json_mode:
            data = _list_json(args.fields, full=args.full)
            emit_success(data, started_at=started_at)
        else:
            _list_text(args.fields)
        return

    # ── Resolve text input ────────────────────────────────────────────────
    if args.input:
        if not os.path.exists(args.input):
            emit_error("input_not_found",
                       "Input file not found: {}".format(args.input),
                       field="input", retryable=False,
                       exit_code=EXIT_VALIDATION, started_at=started_at)
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        if json_mode:
            emit_error("input_empty", "No text provided for synthesis",
                       field="text", retryable=False,
                       exit_code=EXIT_VALIDATION, started_at=started_at)
        else:
            build_parser().print_help()
            sys.exit(EXIT_VALIDATION)

    if not text:
        emit_error("input_empty", "Empty text input",
                   field="text", retryable=False,
                   exit_code=EXIT_VALIDATION, started_at=started_at)

    # ── Idempotency check ────────────────────────────────────────────────
    idem_key = getattr(args, "idempotency_key", None)
    if idem_key:
        hit, cached = idempotency.lookup(idem_key)
        if hit and cached:
            print("idempotency hit: {} — returning cached result".format(idem_key[:20]),
                  file=_diag)
            if json_mode:
                emit_success(cached, started_at=started_at)
            else:
                r = cached
                print("\nDone! (cached)")
                print("  Output:   {}".format(r.get("output_file", "")))
                print("  Duration: {:.1f}s".format(r.get("duration_seconds", 0)))
            return

    # ── Resolve backend/voice/rate ────────────────────────────────────────
    backend, backend_src, voice, voice_src, rate, rate_src = \
        _resolve_backend_config(args)

    if output_fmt is None:
        output_fmt = "wav"
    if output_fmt not in ("wav", "mp3"):
        output_fmt = "wav"

    output_file = _resolve_output(args, backend, output_fmt)

    if output_file:
        if output_fmt == "mp3" and not output_file.endswith(".mp3"):
            output_file = output_file.rsplit(".", 1)[0] + ".mp3" if "." in output_file else output_file + ".mp3"
        elif output_fmt == "wav" and not output_file.endswith(".wav"):
            output_file = output_file.rsplit(".", 1)[0] + ".wav" if "." in output_file else output_file + ".wav"

    # ── Display config ────────────────────────────────────────────────────
    print("Backend:  {} [from {}]".format(backend, backend_src), file=_diag)
    print("Voice:    {} [from {}]".format(voice, voice_src), file=_diag)
    desc = _resolve_voice_name(backend, voice)
    if desc and desc != voice:
        print("          {}".format(desc), file=_diag)
    print("Rate:     {} [from {}]".format(rate, rate_src), file=_diag)
    print("Format:   {}".format(output_fmt), file=_diag)
    print("Output:   {}".format(output_file), file=_diag)
    print("Text:     {} characters".format(len(text)), file=_diag)
    if idem_key:
        print("Idem key: {}...".format(idem_key[:30]), file=_diag)
    print(file=_diag)

    max_chars = get_max_chars(backend)

    # ── Dry run ───────────────────────────────────────────────────────────
    if args.dry_run:
        chunks = chunk_text(text, max_chars)
        cn = len(re.findall(r"[一-鿿]", text))
        en = len(re.findall(r"[A-Za-z]+", text))
        est_duration = cn / 4.0 + en / 3.0
        rate_match = re.match(r"([+-]?\d+)%", rate)
        if rate_match:
            est_duration /= 1.0 + int(rate_match.group(1)) / 100.0

        dry_run_data = {
            "backend": backend,
            "voice": voice,
            "voice_description": _resolve_voice_name(backend, voice),
            "speech_rate": rate,
            "max_chars_per_chunk": max_chars,
            "total_chars": len(text),
            "cn_chars": cn,
            "en_words": en,
            "chunks_count": len(chunks),
            "estimated_duration_seconds": round(est_duration, 1),
            "estimated_duration_minutes": round(est_duration / 60, 1),
            "supports_ssml": BACKENDS[backend]["supports_ssml"],
        }

        if json_mode:
            emit_success(dry_run_data, started_at=started_at)
        else:
            print("--- Dry Run ---", file=_diag)
            print("  Chinese chars:  {}".format(cn), file=_diag)
            print("  English words:  {}".format(en), file=_diag)
            print("  Total chars:    {}".format(len(text)), file=_diag)
            print("  Chunks:         {} (max {} chars/chunk)".format(len(chunks), max_chars), file=_diag)
            print("  Est. duration:  {:.0f}s ({:.1f} min)".format(est_duration, est_duration / 60), file=_diag)
            print("  SSML:           {}".format("yes" if BACKENDS[backend]["supports_ssml"] else "no"), file=_diag)
            print("  API call:       not made", file=_diag)
        return

    # ── Init backend ──────────────────────────────────────────────────────
    try:
        config = init_backend(backend)
    except MissingPackageError as e:
        emit_error("tool_missing", str(e),
                   retryable=False, backend=backend,
                   extra={"install_cmd": e.install_cmd},
                   exit_code=EXIT_VALIDATION, started_at=started_at)
    except MissingEnvVarError as e:
        emit_error("auth_missing_env", str(e),
                   retryable=False, field=e.var, backend=backend,
                   exit_code=EXIT_AUTH, started_at=started_at)
    except BackendError as e:
        emit_error("internal_error", str(e),
                   retryable=False, backend=backend,
                   exit_code=EXIT_INTERNAL, started_at=started_at)

    config["voice"] = voice
    config["speech_rate"] = rate

    # ── Synthesize ────────────────────────────────────────────────────────
    chunks = chunk_text(text, max_chars)
    print("Split into {} chunk(s) (max {} chars/chunk)\n".format(len(chunks), max_chars),
          file=_diag)

    synthesize = get_synthesize_func(backend)
    try:
        duration = synthesize(chunks, config, output_file, output_format=output_fmt)
    except Exception as e:
        emit_error("backend_error", "Synthesis failed: {}".format(e),
                   retryable=True, backend=backend,
                   exit_code=EXIT_BACKEND, started_at=started_at)

    # Most backends emit WAV regardless of output_fmt — transcode centrally
    if output_fmt == "mp3":
        _ensure_mp3(output_file, started_at)

    file_size = Path(output_file).stat().st_size
    elapsed = time.time() - started_at

    result = {
        "backend": backend,
        "voice": voice,
        "speech_rate": rate,
        "output_file": output_file,
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 1),
        "duration_seconds": round(duration, 1),
        "duration_minutes": round(duration / 60, 1),
        "wall_clock_seconds": round(elapsed, 1),
        "chunks": len(chunks),
        "total_chars": len(text),
    }

    # Store result under idempotency key for future retries
    if idem_key:
        idempotency.store(idem_key, result)

    if json_mode:
        emit_success(result, started_at=started_at)
    else:
        size_str = "{:.1f} KB".format(file_size / 1024) if file_size < 1024 * 1024 else "{:.1f} MB".format(file_size / 1024 / 1024)
        print("\nDone!")
        print("  Output:   {} ({})".format(output_file, size_str))
        print("  Duration: {:.1f}s ({:.1f} min)".format(duration, duration / 60))
        print("  Time:     {:.1f}s wall clock".format(elapsed))


if __name__ == "__main__":
    main()
