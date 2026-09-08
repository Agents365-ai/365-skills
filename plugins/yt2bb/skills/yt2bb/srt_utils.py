#!/usr/bin/env python3
"""SRT utilities for yt2bb - merge bilingual subtitles.

Agent-native CLI: all subcommands support --format json for structured output.
Exit codes: 0=success, 1=runtime error, 2=validation/data error.
"""

import argparse
import hashlib
import importlib
import json
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# Exit codes
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_VALIDATION = 2


def _emit(result, fmt="text", text_fn=None):
    """Emit result as JSON or human-readable text."""
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False))
    elif text_fn:
        text_fn(result)


def parse_srt(path):
    """Parse SRT file into list of entry dicts. Warns on skipped malformed blocks."""
    content = (
        sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    )
    entries = []
    skipped = 0
    for block in re.split(r"\n\n+", content.strip()):
        lines = block.strip().split("\n")
        if len(lines) < 2:
            skipped += 1
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1]
        )
        if not m:
            skipped += 1
            continue
        try:
            idx = int(lines[0])
        except ValueError:
            skipped += 1
            continue
        entries.append(
            {
                "index": idx,
                "start": m.group(1),
                "end": m.group(2),
                "text": "\n".join(lines[2:]) if len(lines) > 2 else "",
            }
        )
    if skipped:
        print(
            f"Warning: skipped {skipped} malformed block(s) during parsing",
            file=sys.stderr,
        )
    return entries


def write_srt(entries, path):
    """Write list of entry dicts to SRT file."""
    lines = []
    for i, e in enumerate(entries, 1):
        lines.extend([str(i), f"{e['start']} --> {e['end']}", e["text"], ""])
    output = "\n".join(lines)
    if path == "-":
        print(output)
    else:
        Path(path).write_text(output, encoding="utf-8")


def merge_bilingual(en_entries, zh_entries, pad_missing=False):
    """Merge EN and ZH entries into bilingual format (EN on top, ZH below).

    Raises ValueError on count mismatch unless pad_missing=True.
    """
    en_count, zh_count = len(en_entries), len(zh_entries)
    if en_count != zh_count:
        if not pad_missing:
            raise ValueError(
                f"Subtitle count mismatch: EN={en_count}, ZH={zh_count}. "
                f"Use --pad-missing to pad the shorter list instead of failing."
            )
        print(
            f"Warning: EN={en_count}, ZH={zh_count}. Padding shorter list.",
            file=sys.stderr,
        )
        if en_count > zh_count:
            for i in range(zh_count, en_count):
                zh_entries.append(
                    {
                        "index": i + 1,
                        "start": en_entries[i]["start"],
                        "end": en_entries[i]["end"],
                        "text": "[翻译缺失]",
                    }
                )
        else:
            for i in range(en_count, zh_count):
                en_entries.append(
                    {
                        "index": i + 1,
                        "start": zh_entries[i]["start"],
                        "end": zh_entries[i]["end"],
                        "text": "[Translation missing]",
                    }
                )

    return [
        {
            "index": i,
            "start": en["start"],
            "end": en["end"],
            "text": f"{en['text']}\n{zh['text']}",
        }
        for i, (en, zh) in enumerate(zip(en_entries, zh_entries), 1)
    ]


def time_to_ms(ts):
    """Convert SRT timestamp (HH:MM:SS,mmm) to milliseconds."""
    try:
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
    except (ValueError, AttributeError):
        raise ValueError(f"Malformed SRT timestamp: {ts!r}") from None


def ms_to_time(ms):
    """Convert milliseconds to SRT timestamp."""
    if ms < 0:
        ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_part = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_part:03d}"


def fix_srt(entries, min_duration_ms=500, min_gap_ms=83, max_passes=3):
    """Fix common SRT issues: short durations, overlaps, tiny gaps.

    Runs multiple passes (up to max_passes) to resolve cascading overlaps
    where fixing one entry pushes timing into the next.
    """
    fixed = [e.copy() for e in entries]

    for _ in range(max_passes):
        changed = False
        # Enforce minimum duration
        for e in fixed:
            start_ms = time_to_ms(e["start"])
            end_ms = time_to_ms(e["end"])
            if end_ms - start_ms < min_duration_ms:
                e["end"] = ms_to_time(start_ms + min_duration_ms)
                changed = True

        # Resolve overlaps and enforce minimum gap
        for i in range(1, len(fixed)):
            prev_start = time_to_ms(fixed[i - 1]["start"])
            prev_end = time_to_ms(fixed[i - 1]["end"])
            curr_start = time_to_ms(fixed[i]["start"])
            if prev_end > curr_start - min_gap_ms:
                new_end = curr_start - min_gap_ms
                if new_end >= prev_start + min_duration_ms:
                    fixed[i - 1]["end"] = ms_to_time(new_end)
                else:
                    new_end = prev_start + min_duration_ms
                    fixed[i - 1]["end"] = ms_to_time(new_end)
                    new_start = new_end + min_gap_ms
                    fixed[i]["start"] = ms_to_time(new_start)
                    curr_end_ms = time_to_ms(fixed[i]["end"])
                    if curr_end_ms < new_start + min_duration_ms:
                        fixed[i]["end"] = ms_to_time(new_start + min_duration_ms)
                changed = True

        if not changed:
            break

    return fixed


def validate_srt(entries):
    """Validate SRT entries for timing issues."""
    issues = []
    for e in entries:
        start_ms = time_to_ms(e["start"])
        end_ms = time_to_ms(e["end"])
        duration = end_ms - start_ms

        if duration < 500:
            issues.append(f"#{e['index']}: duration {duration}ms < 500ms")
        if duration > 7000:
            issues.append(f"#{e['index']}: duration {duration}ms > 7000ms")

    for i in range(1, len(entries)):
        prev_end = time_to_ms(entries[i - 1]["end"])
        curr_start = time_to_ms(entries[i]["start"])
        if prev_end > curr_start:
            issues.append(
                f"#{entries[i]['index']}: overlaps previous by {prev_end - curr_start}ms"
            )

    return issues


# ---------------------------------------------------------------------------
# Netflix-spec lint
# ---------------------------------------------------------------------------

# CJK Unified Ideographs + Extension A. A line containing any of these is
# treated as a Chinese line for CPS and per-line length checks.
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html_tags(text):
    """Strip HTML-style tags like <i>, <b> from subtitle text."""
    return _HTML_TAG_RE.sub("", text)


def _is_cjk_line(line):
    """True if the line contains any CJK Unified Ideographs."""
    return bool(_CJK_RE.search(line))


def _visible_length(line):
    """Visible character count for Netflix line-length checks.

    CJK full-width chars and Latin chars both count as 1. HTML tags are
    stripped so `<i>hi</i>` counts as 2, not 9. Trailing whitespace is
    ignored.
    """
    return len(_strip_html_tags(line).rstrip())


def lint_srt(
    entries,
    *,
    min_duration_ms=833,
    max_duration_ms=7000,
    min_gap_ms=83,
    max_cps_en=17.0,
    max_cps_zh=9.0,
    max_chars_en=42,
    max_chars_zh=16,
    max_lines=2,
):
    """Lint SRT entries against the Netflix Timed Text Style Guide.

    Checks hard readability rules (duration, CPS, line count) as errors
    and soft typography rules (per-line length, inter-cue gap) as
    warnings. Returns a list of issue dicts sorted by cue index; each
    issue has ``index``, ``code``, ``severity`` ('error' or 'warning'),
    and ``message`` fields.

    Netflix defaults (all overridable):
      * duration: 833 ms <= cue <= 7000 ms
      * reading speed: <= 17 CPS English, <= 9 CPS Simplified Chinese
      * lines: <= 2 per cue
      * line length: <= 42 chars English, <= 16 full-width chars Chinese
      * inter-cue gap: >= 2 frames @ 24 fps (83 ms)
    """
    issues = []
    for e in entries:
        idx = e["index"]
        start_ms = time_to_ms(e["start"])
        end_ms = time_to_ms(e["end"])
        duration_ms = end_ms - start_ms
        duration_s = duration_ms / 1000 if duration_ms > 0 else 0

        if duration_ms < min_duration_ms:
            issues.append(
                {
                    "index": idx,
                    "code": "duration_too_short",
                    "severity": "error",
                    "message": f"#{idx}: duration {duration_ms}ms < {min_duration_ms}ms (Netflix min)",
                }
            )
        if duration_ms > max_duration_ms:
            issues.append(
                {
                    "index": idx,
                    "code": "duration_too_long",
                    "severity": "error",
                    "message": f"#{idx}: duration {duration_ms}ms > {max_duration_ms}ms (Netflix max)",
                }
            )

        text = _strip_html_tags(e["text"]).strip()
        if not text:
            continue

        lines = [ln for ln in text.split("\n") if ln.strip()]
        if len(lines) > max_lines:
            issues.append(
                {
                    "index": idx,
                    "code": "too_many_lines",
                    "severity": "error",
                    "message": f"#{idx}: {len(lines)} lines > {max_lines} (Netflix max per cue)",
                }
            )

        for line in lines:
            visible = _visible_length(line)
            if visible == 0:
                continue
            if _is_cjk_line(line):
                if visible > max_chars_zh:
                    issues.append(
                        {
                            "index": idx,
                            "code": "line_too_long_zh",
                            "severity": "warning",
                            "message": (
                                f"#{idx}: ZH line {visible} chars > {max_chars_zh} "
                                f"(Netflix SC max)"
                            ),
                        }
                    )
                if duration_s > 0:
                    cps = visible / duration_s
                    if cps > max_cps_zh:
                        issues.append(
                            {
                                "index": idx,
                                "code": "cps_zh_too_fast",
                                "severity": "error",
                                "message": (
                                    f"#{idx}: ZH reading speed {cps:.1f} CPS "
                                    f"> {max_cps_zh} (Netflix SC max)"
                                ),
                            }
                        )
            else:
                if visible > max_chars_en:
                    issues.append(
                        {
                            "index": idx,
                            "code": "line_too_long_en",
                            "severity": "warning",
                            "message": (
                                f"#{idx}: EN line {visible} chars > {max_chars_en} "
                                f"(Netflix max)"
                            ),
                        }
                    )
                if duration_s > 0:
                    cps = visible / duration_s
                    if cps > max_cps_en:
                        issues.append(
                            {
                                "index": idx,
                                "code": "cps_en_too_fast",
                                "severity": "error",
                                "message": (
                                    f"#{idx}: EN reading speed {cps:.1f} CPS "
                                    f"> {max_cps_en} (Netflix max)"
                                ),
                            }
                        )

    for i in range(1, len(entries)):
        prev_end = time_to_ms(entries[i - 1]["end"])
        curr_start = time_to_ms(entries[i]["start"])
        if prev_end <= curr_start:
            gap = curr_start - prev_end
            if gap < min_gap_ms:
                issues.append(
                    {
                        "index": entries[i]["index"],
                        "code": "gap_too_small",
                        "severity": "warning",
                        "message": (
                            f"#{entries[i]['index']}: gap {gap}ms < {min_gap_ms}ms "
                            f"(Netflix min 2 frames @ 24fps)"
                        ),
                    }
                )

    return issues


def _transliterate(text):
    """Transliterate via unidecode when installed; otherwise return text unchanged."""
    try:
        return importlib.import_module("unidecode").unidecode(text)
    except (ImportError, AttributeError):
        return text


def slugify(title):
    """Convert title to URL-safe slug, preserving CJK and other Unicode scripts.

    Uses unidecode for transliteration when available; otherwise keeps
    Unicode letters/digits so that CJK titles produce readable slugs
    instead of opaque hashes.
    """
    title = _transliterate(title)
    normalized = unicodedata.normalize("NFKC", title)
    # Allow Unicode word characters (letters + digits) — covers CJK, Cyrillic, etc.
    slug = re.sub(r"[^\w]+", "-", normalized.lower(), flags=re.UNICODE).strip("-")
    # Remove lone underscores left by \w matching _
    slug = slug.replace("_", "-")
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        slug = "video-" + hashlib.sha256(title.encode()).hexdigest()[:8]
    return slug


# ---------------------------------------------------------------------------
# Whisper environment detection
# ---------------------------------------------------------------------------


def _run_quiet(cmd):
    """Run a command and return stdout, or None on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _detect_memory_gb():
    """Detect total system memory in GB."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = _run_quiet(["sysctl", "-n", "hw.memsize"])
            return int(out) / (1024**3) if out else None
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (1024**2)
            return None
        elif system == "Windows":
            out = _run_quiet(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"]
            )
            if out:
                for line in out.splitlines():
                    if "TotalPhysicalMemory" in line:
                        return int(line.split("=")[1]) / (1024**3)
            return None
    except (ValueError, OSError):
        return None


def _detect_gpu():
    """Detect GPU info. Returns dict with 'type', 'name', 'vram_gb'."""
    system = platform.system()
    machine = platform.machine()

    out = _run_quiet(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
    )
    if out:
        parts = out.splitlines()[0].split(", ")
        name = parts[0].strip()
        try:
            vram_mb = int(parts[1].strip()) if len(parts) > 1 else 0
            return {"type": "cuda", "name": name, "vram_gb": round(vram_mb / 1024, 1)}
        except ValueError:
            return {"type": "cuda", "name": name, "vram_gb": None}

    if system == "Darwin" and machine == "arm64":
        chip = (
            _run_quiet(["sysctl", "-n", "machdep.cpu.brand_string"]) or "Apple Silicon"
        )
        mem = _detect_memory_gb()
        return {"type": "mps", "name": chip, "vram_gb": round(mem, 1) if mem else None}

    return {"type": "cpu", "name": "CPU only", "vram_gb": None}


def _detect_whisper_backends():
    """Check which whisper CLI backends are installed."""
    backends = {}
    for name, cmd in [
        ("openai-whisper", "whisper"),
        ("mlx-whisper", "mlx_whisper"),
        ("whisper-ctranslate2", "whisper-ctranslate2"),
    ]:
        backends[name] = shutil.which(cmd) is not None
    return backends


_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
_MODEL_SIZE_GB = {
    "tiny": 0.07,
    "base": 0.14,
    "small": 0.5,
    "medium": 1.5,
    "large-v3": 3.0,
}


def _detect_whisper_models():
    """Detect locally cached whisper models across all backends.

    Returns dict mapping model name to list of backends that have it cached.
    """
    home = Path.home()
    cached = {m: [] for m in _WHISPER_MODELS}

    # openai-whisper: ~/.cache/whisper/{model}.pt
    ow_cache = home / ".cache" / "whisper"
    if ow_cache.is_dir():
        for m in _WHISPER_MODELS:
            # openai-whisper uses "large-v3.pt" or "large-v3.en.pt"
            if (ow_cache / f"{m}.pt").exists():
                cached[m].append("openai-whisper")

    # mlx-whisper: ~/.cache/huggingface/hub/models--mlx-community--whisper-{model}-mlx/
    hf_cache = home / ".cache" / "huggingface" / "hub"
    if hf_cache.is_dir():
        for m in _WHISPER_MODELS:
            slug = m.replace("-", "-")  # large-v3 stays large-v3
            mlx_dir = hf_cache / f"models--mlx-community--whisper-{slug}-mlx"
            if mlx_dir.is_dir():
                cached[m].append("mlx-whisper")
            # whisper-ctranslate2 / faster-whisper: Systran--faster-whisper-{model}
            ct2_dir = hf_cache / f"models--Systran--faster-whisper-{slug}"
            if ct2_dir.is_dir():
                cached[m].append("whisper-ctranslate2")

    return cached


def check_whisper():
    """Detect platform/GPU/memory and recommend whisper backend + model.

    Returns a structured dict with platform info, installed backends,
    cached models, and recommendation.
    """
    system = platform.system()
    machine = platform.machine()
    is_apple_silicon = system == "Darwin" and machine == "arm64"
    mem_gb = _detect_memory_gb()
    gpu = _detect_gpu()
    backends = _detect_whisper_backends()

    # Model recommendation based on available memory.
    # Treat unknown memory as unknown, not as 0 GB.
    avail_gb = gpu["vram_gb"] if gpu["vram_gb"] is not None else mem_gb
    if avail_gb is not None and avail_gb >= 10:
        rec_model = "large-v3"
        model_reason = f"{avail_gb:.0f} GB available"
    elif avail_gb is not None and avail_gb >= 5:
        rec_model = "medium"
        model_reason = f"{avail_gb:.0f} GB available (large-v3 needs ~10 GB)"
    elif avail_gb is None:
        rec_model = "medium" if is_apple_silicon or gpu["type"] == "cuda" else "tiny"
        model_reason = "Memory unknown; using a safe default for this platform"
    else:
        rec_model = "tiny"
        model_reason = f"{avail_gb:.0f} GB available (medium needs ~5 GB)"

    # Backend recommendation
    if is_apple_silicon:
        rec_backend = "mlx-whisper"
        rec_reason = "Apple Silicon native (MLX), fastest on this platform"
        install_cmd = "pip install mlx-whisper"
        model_flag = f"mlx-community/whisper-{rec_model}-mlx"
        example = (
            f'mlx_whisper "${{slug}}/${{slug}}.mp4" '
            f"--model {model_flag} "
            f'--language "$src_lang" '
            f'--output-format srt --output-dir "${{slug}}"'
        )
    elif gpu["type"] == "cuda":
        rec_backend = "whisper-ctranslate2"
        rec_reason = (
            f"CTranslate2 + CUDA ({gpu['name']}), ~4x faster than openai-whisper"
        )
        install_cmd = "pip install whisper-ctranslate2"
        model_flag = rec_model
        example = (
            f'whisper-ctranslate2 "${{slug}}/${{slug}}.mp4" '
            f"--model {model_flag} "
            f'--language "$src_lang" '
            f'--output_format srt --output_dir "${{slug}}"'
        )
    else:
        rec_backend = "whisper-ctranslate2"
        rec_reason = "CTranslate2, ~4x faster than openai-whisper on CPU"
        install_cmd = "pip install whisper-ctranslate2"
        model_flag = rec_model
        example = (
            f'whisper-ctranslate2 "${{slug}}/${{slug}}.mp4" '
            f"--model {model_flag} "
            f'--language "$src_lang" '
            f'--output_format srt --output_dir "${{slug}}"'
        )

    # Detect cached models
    models = _detect_whisper_models()

    # Check if recommended model is cached for recommended backend
    rec_model_cached = rec_backend in models.get(rec_model, [])
    rec_model_size = _MODEL_SIZE_GB.get(rec_model, 0)

    # Find best already-cached model (largest that fits in memory)
    best_cached = None
    for m in reversed(_WHISPER_MODELS):  # large-v3 first
        if models[m]:  # cached by any backend
            best_cached = m
            break

    # Fallback command
    fallback = None
    rec_installed = backends.get(rec_backend, False)
    if not rec_installed and backends.get("openai-whisper"):
        fallback = (
            f'whisper "${{slug}}/${{slug}}.mp4" --model {rec_model} '
            f'--language "$src_lang" --output_format srt --output_dir "${{slug}}"'
        )

    os_label = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(
        system, system
    )

    return {
        "ok": True,
        "command": "check-whisper",
        "platform": {
            "os": os_label,
            "arch": machine,
            "apple_silicon": is_apple_silicon,
            "memory_gb": round(mem_gb, 1) if mem_gb else None,
        },
        "gpu": gpu,
        "backends": backends,
        "models": {m: cached for m, cached in models.items() if cached},
        "recommendation": {
            "backend": rec_backend,
            "reason": rec_reason,
            "model": rec_model,
            "model_reason": model_reason,
            "model_cached": rec_model_cached,
            "model_download_gb": rec_model_size if not rec_model_cached else 0,
            "installed": rec_installed,
            "install": install_cmd if not rec_installed else None,
            "command": example,
        },
        "best_cached_model": best_cached,
        "fallback": fallback,
    }


def _print_check_whisper_text(result):
    """Human-readable output for check-whisper."""
    p = result["platform"]
    gpu = result["gpu"]
    rec = result["recommendation"]

    arch_note = " (Apple Silicon)" if p["apple_silicon"] else ""
    print("=== yt2bb Whisper Environment Check ===\n")
    print(f"Platform:  {p['os']} {p['arch']}{arch_note}")
    if p["memory_gb"]:
        print(f"Memory:    {p['memory_gb']:.0f} GB")
    else:
        print("Memory:    unknown")
    vram_note = f" ({gpu['vram_gb']:.0f} GB VRAM)" if gpu["type"] == "cuda" else ""
    print(f"GPU:       {gpu['name']}{vram_note}")
    print()

    print("Installed backends:")
    for name, installed in result["backends"].items():
        mark = "+" if installed else "-"
        print(f"  [{mark}] {name}")
    print()

    print("Cached models:")
    models = result.get("models", {})
    if models:
        for m, cached_by in models.items():
            size = _MODEL_SIZE_GB.get(m, 0)
            print(f"  [+] {m} ({size:.1f} GB) — via {', '.join(cached_by)}")
    else:
        print("  (none)")
    print()

    download_note = ""
    if rec["model_download_gb"] > 0:
        download_note = f" — needs ~{rec['model_download_gb']:.1f} GB download"
    print("Recommended:")
    print(f"  Backend:  {rec['backend']} — {rec['reason']}")
    print(f"  Model:    {rec['model']} ({rec['model_reason']}){download_note}")
    if rec["install"]:
        print(f"  Install:  {rec['install']}")
    print()
    print("Command:")
    print(f"  {rec['command']}")

    best_cached = result.get("best_cached_model")
    if best_cached and best_cached != rec["model"] and rec["model_download_gb"] > 0:
        print()
        print(f"Tip: {best_cached} is already cached and can be used immediately.")

    if result["fallback"]:
        print()
        print(
            "Note: openai-whisper is already installed. You can use it as a fallback:"
        )
        print(f"  {result['fallback']}")


# ---------------------------------------------------------------------------
# ASS subtitle generation
# ---------------------------------------------------------------------------


def _srt_time_to_ass(ts):
    """Convert SRT timestamp (HH:MM:SS,mmm) to ASS format (H:MM:SS.cc)."""
    try:
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        cs = int(ms) // 10
        return f"{int(h)}:{m}:{s}.{cs:02d}"
    except (ValueError, AttributeError):
        raise ValueError(f"Malformed SRT timestamp: {ts!r}") from None


def _ass_escape(text):
    """Escape characters that have special meaning in ASS dialogue text."""
    return text.replace("{", r"\{").replace("}", r"\}")


# Reflow: split a cue into complete-phrase lines (see the Netflix SC / rule 10
# "each line is a whole sentence or short phrase" convention).
_ZH_SENT_ENDERS = "。！？…"
_ZH_CLAUSE_SEP = "，、；："
_EN_SENT_ENDERS = ".?!"
_EN_CLAUSE_SEP = ",;:"


def _split_at(text, seps):
    """Split text into units, keeping each separator attached to its preceding unit."""
    units = []
    cur = []
    for ch in text:
        cur.append(ch)
        if ch in seps:
            units.append("".join(cur))
            cur = []
    if cur:
        units.append("".join(cur))
    return units


def _hard_wrap(text, max_chars, is_zh):
    """Break an indivisible over-long unit into <= max_chars lines.

    Chinese is cut at the character boundary (no spaces); English prefers word
    boundaries so a word is never sliced in half unless it alone exceeds the limit.
    """
    if is_zh:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    lines = []
    cur = ""
    for word in text.split(" "):
        candidate = (cur + " " + word).strip() if cur else word
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text[:max_chars]]


def _reflow_text(text, max_chars, is_zh):
    """Split a cue into complete-phrase lines, each <= max_chars.

    Breaks only at sentence / clause / word boundaries so a displayed line never
    ends mid-phrase (never a truncated fragment); hard-wraps only a genuinely
    indivisible over-long unit. Reinforces rule 10 (whole-sentence display).
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    enders = _ZH_SENT_ENDERS if is_zh else _EN_SENT_ENDERS
    inner = _ZH_CLAUSE_SEP if is_zh else _EN_CLAUSE_SEP

    # 1. break into sentence units (each keeps its ender)
    units = _split_at(text, enders)
    # 2. further break any over-long sentence at clause / word boundaries
    atomic = []
    for u in units:
        if len(u) > max_chars:
            atomic.extend(_split_at(u, inner))
        else:
            atomic.append(u)
    # 3. hard-wrap any unit that is still over the limit
    final = []
    for u in atomic:
        if len(u) > max_chars:
            final.extend(_hard_wrap(u, max_chars, is_zh))
        else:
            final.append(u)
    # 4. greedily pack into <= max_chars lines
    lines = []
    cur = ""
    for u in final:
        if not cur:
            cur = u
        elif len(cur + u) <= max_chars:
            cur += u
        else:
            lines.append(cur)
            cur = u
    if cur:
        lines.append(cur)
    return lines


def _detect_font():
    """Return the best available CJK subtitle font for this OS."""
    system = platform.system()
    if system == "Darwin":
        return "PingFang SC"
    if system == "Windows":
        return "Microsoft YaHei"
    # Linux: pick the first installed CJK font via fontconfig
    for candidate in (
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
    ):
        if _run_quiet(["fc-list", ":", "family=" + candidate]) is not None:
            return candidate
    return "Noto Sans CJK SC"


# ASS color format: &HAABBGGRR  (alpha=00 is fully opaque, FF is fully
# transparent). For BorderStyle=3 (opaque box), libass uses OutlineColour
# as the box fill — so the semi-transparent gray lives in `outline_color`,
# not `back_color`.
_PRESET_CLEAN = {
    "name": "Professional Clean",
    "box": True,
    "top_margin": 105,
    "bottom_margin": 55,
    "styles": {
        "EN": {
            "fontsize": 44,
            "primary": "&H0000EFFF",  # yellow text
            "secondary": "&H000000FF",
            "outline_color": "&H96C8C8C8",  # semi-transparent light gray box fill
            "back_color": "&H80000000",  # soft black drop shadow
            "border_style": 3,
            "outline": 6,  # box padding around the text
            "shadow": 0,
        },
        "ZH": {
            "fontsize": 56,
            "primary": "&H0000D4FF",  # golden yellow
            "secondary": "&H000000FF",
            "outline_color": "&H96C8C8C8",
            "back_color": "&H80000000",
            "border_style": 3,
            "outline": 6,
            "shadow": 0,
        },
    },
    "en_tag": "",
    "zh_tag": "",
}

_PRESET_NETFLIX = {
    "name": "Netflix Clean",
    # Modeled on Netflix's Timed Text Style Guide: pure white text,
    # thin black outline, soft drop shadow, no background box, slightly
    # inset from the bottom edge so the block sits in the safe area.
    "box": False,
    "top_margin": 145,
    "bottom_margin": 72,
    "styles": {
        "EN": {
            "fontsize": 52,
            "primary": "&H00FFFFFF",  # pure white
            "secondary": "&H000000FF",
            "outline_color": "&H00000000",  # black outline
            "back_color": "&H80000000",  # soft black drop shadow
            "border_style": 1,  # outline + shadow (no box)
            "outline": 3,
            "shadow": 2,
        },
        "ZH": {
            "fontsize": 58,
            "primary": "&H00FFFFFF",
            "secondary": "&H000000FF",
            "outline_color": "&H00000000",
            "back_color": "&H80000000",
            "border_style": 1,
            "outline": 3,
            "shadow": 2,
        },
    },
    "en_tag": "",
    "zh_tag": "",
}

_PRESET_GLOW = {
    "name": "Vibrant Glow",
    "box": False,
    "top_margin": 105,
    "bottom_margin": 55,
    "styles": {
        "EN": {
            "fontsize": 44,
            "primary": "&H00FFFFFF",
            "secondary": "&H000000FF",
            "outline_color": "&H000080FF",
            "back_color": "&H00000000",
            "border_style": 1,
            "outline": 5,
            "shadow": 0,
        },
        "ZH": {
            "fontsize": 56,
            "primary": "&H0000FFFF",
            "secondary": "&H000000FF",
            "outline_color": "&H00003080",
            "back_color": "&H00000000",
            "border_style": 1,
            "outline": 5,
            "shadow": 0,
        },
    },
    "en_tag": r"{\blur5}",
    "zh_tag": r"{\blur5}",
}

ASS_PRESETS = {
    "clean": _PRESET_CLEAN,
    "netflix": _PRESET_NETFLIX,
    "glow": _PRESET_GLOW,
}

_ASS_STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding"
)


def _scaled_ass_metric(value, scale, minimum=1):
    """Scale ASS metrics by resolution while keeping values usable on smaller videos."""
    try:
        return max(minimum, int(round(float(value) * float(scale))))
    except (TypeError, ValueError):
        return minimum


def _build_preset_style_lines(preset, font, top_lang, resolution, safe_area=0.06):
    """Build ASS style lines for a preset with resolution-aware sizing.

    ``safe_area`` is the fraction of frame height reserved at the bottom (e.g.
    0.06 keeps subtitles clear of platform UI / progress bars). The bottom-anchored
    language's margin is floored at that safe zone.
    """
    _, height = resolution
    scale = height / 1080
    try:
        safe_px = int(round(height * safe_area))
    except (TypeError, ValueError):
        safe_px = 0
    top_margin = _scaled_ass_metric(preset["top_margin"], scale, minimum=24)
    bottom_margin = max(
        _scaled_ass_metric(preset["bottom_margin"], scale, minimum=18),
        safe_px,
    )
    lang_margins = {
        "EN": top_margin if top_lang == "en" else bottom_margin,
        "ZH": top_margin if top_lang == "zh" else bottom_margin,
    }

    # Style field order (ASS v4+):
    #   Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,
    #   BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing,
    #   Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR,
    #   MarginV, Encoding
    style_lines = []
    for lang in ("EN", "ZH"):
        style = preset["styles"][lang]
        style_lines.append(
            "Style: {lang},{font},{fontsize},{primary},{secondary},{outline_color},"
            "{back_color},-1,0,0,0,100,100,0,0,{border_style},{outline},{shadow},"
            "2,15,15,{margin_v},1".format(
                lang=lang,
                font=font,
                fontsize=_scaled_ass_metric(style["fontsize"], scale, minimum=18),
                primary=style["primary"],
                secondary=style["secondary"],
                outline_color=style["outline_color"],
                back_color=style["back_color"],
                border_style=style["border_style"],
                outline=_scaled_ass_metric(style["outline"], scale, minimum=1),
                shadow=_scaled_ass_metric(style["shadow"], scale, minimum=0),
                margin_v=lang_margins[lang],
            )
        )
    return style_lines


def _parse_ass_styles(path):
    """Extract style lines and override tags from an external ASS file."""
    content = Path(path).read_text(encoding="utf-8")
    style_lines = []
    style_names = set()
    in_styles = False
    en_tag, zh_tag = "", ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[V4+ Styles]") or stripped.startswith("[V4 Styles]"):
            in_styles = True
            continue
        if stripped.startswith("[") and in_styles:
            in_styles = False
        if in_styles and stripped.startswith("Style:"):
            style_lines.append(stripped)
            parts = stripped.split(":", 1)[1].split(",", 1)
            if parts:
                style_names.add(parts[0].strip())
        if stripped.startswith("; en_tag="):
            en_tag = stripped.split("=", 1)[1].strip()
        if stripped.startswith("; zh_tag="):
            zh_tag = stripped.split("=", 1)[1].strip()
    if not style_lines:
        raise ValueError(f"No Style lines found in {path}")
    missing = {"EN", "ZH"} - style_names
    if missing:
        raise ValueError(
            f"Style file {path} must define styles named EN and ZH; missing: {', '.join(sorted(missing))}"
        )
    return style_lines, en_tag, zh_tag


def to_ass(
    entries,
    preset="clean",
    font=None,
    resolution=(1920, 1080),
    top_lang="zh",
    style_file=None,
    reflow=False,
    fade_ms=150,
    safe_area=0.06,
):
    """Convert bilingual SRT entries to a styled ASS file.

    Each bilingual entry (EN\\nZH text) is split into two separate ASS
    Dialogue lines with independent styles, enabling per-line color and
    glow effects not possible with SRT force_style.

    Optional cinematic enhancements:
      * ``reflow``    -- split each cue into complete-sentence lines (rule 10)
      * ``fade_ms``   -- fade in/out duration in ms (0 disables; ASS uses cs)
      * ``safe_area`` -- fraction of frame height kept clear at the bottom
      * ``font=None`` -- auto-pick the best installed CJK font for the OS
    """
    w, h = resolution
    if font is None:
        font = _detect_font()

    if style_file:
        style_lines, en_tag, zh_tag = _parse_ass_styles(style_file)
        title = f"yt2bb bilingual — custom ({Path(style_file).stem})"
    else:
        p = ASS_PRESETS[preset]
        en_tag, zh_tag = p["en_tag"], p["zh_tag"]
        title = f"yt2bb bilingual — {p['name']}"
        style_lines = _build_preset_style_lines(
            p, font, top_lang, resolution, safe_area
        )

    fade_cs = max(0, fade_ms // 10)
    fad_tag = f"{{\\fad({fade_cs},{fade_cs})}}" if fade_cs > 0 else ""

    header = "\n".join(
        [
            "[Script Info]",
            f"Title: {title}",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            f"PlayResX: {w}",
            f"PlayResY: {h}",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            _ASS_STYLE_FORMAT,
            "\n".join(style_lines),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )

    dialogue_lines = []
    for e in entries:
        start = _srt_time_to_ass(e["start"])
        end = _srt_time_to_ass(e["end"])
        parts = e["text"].rsplit("\n", 1)
        raw_en = parts[0] if parts else ""
        raw_zh = parts[1] if len(parts) > 1 else ""
        if reflow and raw_en:
            raw_en = "\\N".join(_reflow_text(raw_en, 42, False))
        if reflow and raw_zh:
            raw_zh = "\\N".join(_reflow_text(raw_zh, 16, True))
        en_text = _ass_escape(raw_en)
        zh_text = _ass_escape(raw_zh)
        if en_text:
            dialogue_lines.append(
                f"Dialogue: 0,{start},{end},EN,,0,0,0,,{fad_tag}{en_tag}{en_text}"
            )
        if zh_text:
            dialogue_lines.append(
                f"Dialogue: 0,{start},{end},ZH,,0,0,0,,{fad_tag}{zh_tag}{zh_text}"
            )

    return header + "\n" + "\n".join(dialogue_lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="srt_utils.py",
        description="SRT utilities for yt2bb. Use --format json for agent-friendly output.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 2.6.2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Shared --format flag
    fmt_parent = argparse.ArgumentParser(add_help=False)
    fmt_parent.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format: text (human) or json (agent)",
    )

    p_merge = sub.add_parser(
        "merge", parents=[fmt_parent], help="Merge EN and ZH SRT into bilingual SRT"
    )
    p_merge.add_argument("en_srt")
    p_merge.add_argument("zh_srt")
    p_merge.add_argument("output_srt")
    p_merge.add_argument(
        "--pad-missing",
        action="store_true",
        help="Pad shorter list instead of failing on count mismatch",
    )
    p_merge.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and report what would happen without writing",
    )

    p_validate = sub.add_parser(
        "validate", parents=[fmt_parent], help="Validate SRT timing"
    )
    p_validate.add_argument("input_srt")

    p_lint = sub.add_parser(
        "lint",
        parents=[fmt_parent],
        help="Lint SRT against Netflix Timed Text Style Guide",
    )
    p_lint.add_argument("input_srt")
    p_lint.add_argument(
        "--max-cps-en",
        type=float,
        default=17.0,
        help="Max English chars/sec (default: 17)",
    )
    p_lint.add_argument(
        "--max-cps-zh",
        type=float,
        default=9.0,
        help="Max Chinese chars/sec (default: 9)",
    )
    p_lint.add_argument(
        "--min-duration-ms",
        type=int,
        default=833,
        help="Min cue duration in ms (default: 833 = 5/6 s)",
    )
    p_lint.add_argument(
        "--max-duration-ms",
        type=int,
        default=7000,
        help="Max cue duration in ms (default: 7000)",
    )
    p_lint.add_argument(
        "--min-gap-ms",
        type=int,
        default=83,
        help="Min gap between cues in ms (default: 83 = 2 frames @ 24fps)",
    )
    p_lint.add_argument(
        "--max-chars-en",
        type=int,
        default=42,
        help="Max English chars per line (default: 42)",
    )
    p_lint.add_argument(
        "--max-chars-zh",
        type=int,
        default=16,
        help="Max Chinese full-width chars per line (default: 16)",
    )

    p_fix = sub.add_parser("fix", parents=[fmt_parent], help="Fix SRT timing issues")
    p_fix.add_argument("input_srt")
    p_fix.add_argument("output_srt")

    p_slug = sub.add_parser(
        "slugify", parents=[fmt_parent], help="Convert title to URL-safe slug"
    )
    p_slug.add_argument("title", nargs="+")

    p_ass = sub.add_parser(
        "to_ass",
        parents=[fmt_parent],
        help="Convert bilingual SRT to styled ASS (supports glow)",
    )
    p_ass.add_argument("input_srt")
    p_ass.add_argument("output_ass")
    p_ass.add_argument(
        "--preset",
        choices=["clean", "netflix", "glow"],
        default="clean",
        help="Subtitle style preset (default: clean)",
    )
    p_ass.add_argument(
        "--font",
        default=None,
        help="Font family name; auto-picked if omitted (best installed CJK font)",
    )
    p_ass.add_argument(
        "--res", default="1920x1080", help="Video resolution WxH (default: 1920x1080)"
    )
    p_ass.add_argument(
        "--top",
        choices=["zh", "en"],
        default="zh",
        help="Which language on top (default: zh)",
    )
    p_ass.add_argument(
        "--style-file",
        default=None,
        help="External .ass file with custom [V4+ Styles] (overrides --preset/--font/--top)",
    )
    p_ass.add_argument(
        "--reflow",
        action="store_true",
        help="Split each cue into complete-sentence lines (rule 10)",
    )
    p_ass.add_argument(
        "--fade",
        type=int,
        default=150,
        help="Fade in/out duration in ms (0 disables; default: 150)",
    )
    p_ass.add_argument(
        "--safe-area",
        type=float,
        default=0.06,
        help="Fraction of frame height kept clear at the bottom (default: 0.06)",
    )
    p_ass.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and report what would happen without writing",
    )

    sub.add_parser(
        "check-whisper",
        parents=[fmt_parent],
        help="Detect platform/GPU and recommend whisper backend + model",
    )

    args = parser.parse_args()
    fmt = args.output_format

    # --- merge ---
    if args.cmd == "merge":
        try:
            en_entries = parse_srt(args.en_srt)
            zh_entries = parse_srt(args.zh_srt)
        except OSError as e:
            _emit(
                {
                    "ok": False,
                    "command": "merge",
                    "error": {
                        "code": "io_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        if args.dry_run:
            match = len(en_entries) == len(zh_entries)
            _emit(
                {
                    "ok": True,
                    "command": "merge",
                    "dry_run": True,
                    "en_entries": len(en_entries),
                    "zh_entries": len(zh_entries),
                    "counts_match": match,
                    "output": args.output_srt,
                },
                fmt,
                lambda r: print(
                    f"Dry run: EN={r['en_entries']}, ZH={r['zh_entries']}, "
                    f"match={'yes' if r['counts_match'] else 'NO'} -> {r['output']}"
                ),
            )
            sys.exit(EXIT_OK)
        try:
            merged = merge_bilingual(
                en_entries, zh_entries, pad_missing=args.pad_missing
            )
        except ValueError as e:
            _emit(
                {
                    "ok": False,
                    "command": "merge",
                    "error": {
                        "code": "count_mismatch",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_VALIDATION)
        write_srt(merged, args.output_srt)
        _emit(
            {
                "ok": True,
                "command": "merge",
                "entries": len(merged),
                "output": args.output_srt,
            },
            fmt,
            lambda r: print(f"Merged {r['entries']} entries -> {r['output']}"),
        )

    # --- validate ---
    elif args.cmd == "validate":
        try:
            entries = parse_srt(args.input_srt)
        except OSError as e:
            _emit(
                {
                    "ok": False,
                    "command": "validate",
                    "error": {
                        "code": "io_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        issues = validate_srt(entries)
        if issues:
            _emit(
                {
                    "ok": False,
                    "command": "validate",
                    "file": args.input_srt,
                    "entries": len(entries),
                    "issue_count": len(issues),
                    "issues": issues,
                },
                fmt,
                lambda r: (
                    print(f"Found {r['issue_count']} issues in {r['file']}:"),
                    [print(f"  {i}") for i in r["issues"]],
                ),
            )
            sys.exit(EXIT_VALIDATION)
        else:
            _emit(
                {
                    "ok": True,
                    "command": "validate",
                    "file": args.input_srt,
                    "entries": len(entries),
                    "issue_count": 0,
                    "issues": [],
                },
                fmt,
                lambda r: print(f"OK: {r['entries']} entries, no issues found"),
            )

    # --- lint (Netflix spec) ---
    elif args.cmd == "lint":
        try:
            entries = parse_srt(args.input_srt)
        except OSError as e:
            _emit(
                {
                    "ok": False,
                    "command": "lint",
                    "error": {
                        "code": "io_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        issues = lint_srt(
            entries,
            min_duration_ms=args.min_duration_ms,
            max_duration_ms=args.max_duration_ms,
            min_gap_ms=args.min_gap_ms,
            max_cps_en=args.max_cps_en,
            max_cps_zh=args.max_cps_zh,
            max_chars_en=args.max_chars_en,
            max_chars_zh=args.max_chars_zh,
        )
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i for i in issues if i["severity"] == "warning"]
        result = {
            "ok": len(errors) == 0,
            "command": "lint",
            "file": args.input_srt,
            "entries": len(entries),
            "thresholds": {
                "min_duration_ms": args.min_duration_ms,
                "max_duration_ms": args.max_duration_ms,
                "min_gap_ms": args.min_gap_ms,
                "max_cps_en": args.max_cps_en,
                "max_cps_zh": args.max_cps_zh,
                "max_chars_en": args.max_chars_en,
                "max_chars_zh": args.max_chars_zh,
            },
            "error_count": len(errors),
            "warning_count": len(warnings),
            "issues": issues,
        }

        def _print_lint(r):
            if r["error_count"] == 0 and r["warning_count"] == 0:
                print(f"OK: {r['entries']} entries, no Netflix-spec issues")
                return
            print(
                f"{r['file']}: {r['error_count']} error(s), "
                f"{r['warning_count']} warning(s) across {r['entries']} entries"
            )
            for issue in r["issues"]:
                tag = "ERROR" if issue["severity"] == "error" else "WARN "
                print(f"  [{tag}] {issue['message']}")

        _emit(result, fmt, _print_lint)
        if errors:
            sys.exit(EXIT_VALIDATION)

    # --- fix ---
    elif args.cmd == "fix":
        try:
            entries = parse_srt(args.input_srt)
        except OSError as e:
            _emit(
                {
                    "ok": False,
                    "command": "fix",
                    "error": {
                        "code": "io_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        before = len(validate_srt(entries))
        fixed = fix_srt(entries)
        write_srt(fixed, args.output_srt)
        after = len(validate_srt(fixed))
        _emit(
            {
                "ok": True,
                "command": "fix",
                "entries": len(fixed),
                "output": args.output_srt,
                "issues_before": before,
                "issues_after": after,
            },
            fmt,
            lambda r: print(
                f"Fixed {r['entries']} entries -> {r['output']} "
                f"(issues: {r['issues_before']} -> {r['issues_after']})"
            ),
        )

    # --- slugify ---
    elif args.cmd == "slugify":
        title = " ".join(args.title)
        slug = slugify(title)
        _emit(
            {"ok": True, "command": "slugify", "title": title, "slug": slug},
            fmt,
            lambda r: print(r["slug"]),
        )

    # --- check-whisper ---
    elif args.cmd == "check-whisper":
        result = check_whisper()
        _emit(result, fmt, _print_check_whisper_text)

    # --- to_ass ---
    elif args.cmd == "to_ass":
        try:
            w, h = map(int, args.res.lower().split("x"))
        except ValueError:
            _emit(
                {
                    "ok": False,
                    "command": "to_ass",
                    "error": {
                        "code": "bad_resolution",
                        "message": f"--res must be WxH, got '{args.res}'",
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_VALIDATION)
        try:
            entries = parse_srt(args.input_srt)
            if args.style_file:
                _parse_ass_styles(args.style_file)  # validate early
        except (OSError, ValueError) as e:
            _emit(
                {
                    "ok": False,
                    "command": "to_ass",
                    "error": {
                        "code": "runtime_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        preset_name = (
            args.preset
            if not args.style_file
            else f"custom ({Path(args.style_file).stem})"
        )
        if args.dry_run:
            _emit(
                {
                    "ok": True,
                    "command": "to_ass",
                    "dry_run": True,
                    "entries": len(entries),
                    "preset": preset_name,
                    "top_lang": args.top,
                    "resolution": f"{w}x{h}",
                    "output": args.output_ass,
                },
                fmt,
                lambda r: print(
                    f"Dry run: [{r['preset']}] {r['entries']} entries, "
                    f"{r['resolution']}, top={r['top_lang']} -> {r['output']}"
                ),
            )
            sys.exit(EXIT_OK)
        try:
            ass_content = to_ass(
                entries,
                preset=args.preset,
                font=args.font,
                resolution=(w, h),
                top_lang=args.top,
                style_file=args.style_file,
                reflow=args.reflow,
                fade_ms=args.fade,
                safe_area=args.safe_area,
            )
        except (OSError, ValueError) as e:
            _emit(
                {
                    "ok": False,
                    "command": "to_ass",
                    "error": {
                        "code": "runtime_error",
                        "message": str(e),
                        "retryable": False,
                    },
                },
                fmt,
                lambda r: print(f"Error: {r['error']['message']}", file=sys.stderr),
            )
            sys.exit(EXIT_RUNTIME)
        Path(args.output_ass).write_text(ass_content, encoding="utf-8")
        _emit(
            {
                "ok": True,
                "command": "to_ass",
                "entries": len(entries),
                "output": args.output_ass,
                "preset": preset_name,
                "top_lang": args.top,
            },
            fmt,
            lambda r: print(f"[{r['preset']}] {r['entries']} entries -> {r['output']}"),
        )
