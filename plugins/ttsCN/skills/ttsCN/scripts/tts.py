#!/usr/bin/env python3
"""
ttsCN — Multi-Platform Chinese TTS Script

Generate speech audio from text using 8 China-friendly TTS backends:
  - Microsoft Edge TTS:  Free, no API key (default)
  - ByteDance Doubao:    Premium Chinese voices, 1 RMB/10K chars
  - Alibaba CosyVoice:   Fast streaming DashScope TTS
  - Microsoft Azure:     Enterprise-grade SSML, eastasia region
  - Tencent Cloud TTS:   Lowest cost (0.75 RMB/10K chars), 380+ voices
  - Baidu AI TTS:        Flexible pricing, 30+ voices, emotion + dialects
  - MiniMax TTS:         Best quality (speech-2.8-hd), 300+ voices, cloning
  - iFlytek Xunfei:      500+ voices, MOS 4.8, education/automotive

Usage:
    python tts.py "你好世界" output.wav
    python tts.py --platform doubao "你好世界" output.wav
    python tts.py --voice zh-CN-YunxiNeural --rate +10% "text" output.mp3
    python tts.py --input script.txt output.wav
    python tts.py --dry-run "这是一段测试文本"

Environment variables:
    TTS_BACKEND (optional) — Default backend
    TTS_VOICE (optional) — Default voice
    TTS_RATE (optional) — Speech rate, e.g. "+5%"
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Ensure backends are importable from any working directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backends import (
    BACKENDS, VOICES, VOICE_DESCRIPTIONS,
    init_backend, get_synthesize_func, get_max_chars,
    resolve_backend, resolve_voice, resolve_speech_rate,
    BackendError, MissingPackageError, MissingEnvVarError,
)

DEFAULT_BACKEND = "edge"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+5%"


def chunk_text(text, max_chars):
    """Split text into TTS-friendly chunks at sentence boundaries.

    Splits on Chinese/English sentence punctuation (。！？.!?).
    Sentences longer than max_chars are hard-split on soft punctuation
    (，, ;：), then by minimum viable fragments. No chunk exceeds max_chars.
    """
    SOFT_PUNCT = "，,;：:、 "
    END_PUNCT = ("。", ".", "!", "?", "！", "？")

    def hard_split(sentence, limit):
        if len(sentence) <= limit:
            return [sentence]
        budget = limit - 1
        lookback = max(8, limit // 4)
        pieces = []
        buf = ""
        for ch in sentence:
            buf += ch
            if len(buf) >= budget:
                cut = -1
                for j in range(len(buf) - 1, max(-1, len(buf) - lookback - 1), -1):
                    if buf[j] in SOFT_PUNCT:
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

    # Normalize Chinese semicolons as sentence boundaries
    normalized = text.replace("；", "。")
    raw = re.split(r"(?<=[。.!?！？])\s*", normalized)
    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        sentences.extend(hard_split(s, max_chars))

    chunks = []
    current = ""
    for s in sentences:
        suffix = ""
        if not s.endswith(tuple(END_PUNCT) + tuple(SOFT_PUNCT.replace(" ", ""))):
            suffix = "。"
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


def list_backends():
    """Print available backends with full capability details."""
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
            print(f"      Clone:         ✅ yes — {info['clone_detail']}")
        else:
            print(f"      Clone:         ❌ no")
        envs = ", ".join(info["env"]) if info["env"] else "none required"
        print(f"      Env vars:      {envs}")
        print()

    print("Voice presets:\n")
    for backend, voice_list in VOICES.items():
        print(f"  [{backend}]")
        for v in voice_list[:8]:  # show first 8
            desc = VOICE_DESCRIPTIONS.get(v, "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {v}{desc_str}")
        if len(voice_list) > 8:
            print(f"    ... and {len(voice_list) - 8} more")
        print()

    print("Config files:")
    print("  Project: ./.ttsCN.json")
    print("  User:    ~/.ttsCN.json")
    print("  Format:  {\"backend\": \"edge\", \"voice\": \"zh-CN-XiaoxiaoNeural\", \"rate\": \"+5%\"}")
    print()
    print("Env vars (precedence over config files):")
    print("  TTS_BACKEND, TTS_VOICE, TTS_RATE")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-platform Chinese TTS text-to-speech synthesis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "你好世界" output.wav
  %(prog)s --voice zh-CN-YunxiNeural "欢迎收听" welcome.wav
  %(prog)s --platform doubao "今天天气真好" weather.wav
  %(prog)s --rate +15% "快速播报" fast.wav
  %(prog)s --input script.txt output.wav
  %(prog)s --format mp3 "你好" hello.mp3
  %(prog)s --dry-run "这是一段测试文本"
  %(prog)s --list
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
    parser.add_argument("--rate", "-r", help="Speech rate, e.g. '+5%', '-10%'")

    # Output format
    parser.add_argument("--format", "-f", choices=["wav", "mp3"], default="wav",
                        help="Output audio format (default: wav)")

    # Info / preview
    parser.add_argument("--list", action="store_true", help="List backends and voices")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview: show config, chunk count, estimated duration")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voices for all backends")

    args = parser.parse_args()

    if args.list or args.list_voices:
        list_backends()
        return

    # --- Resolve text input ---
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        sys.exit(1)

    if not text:
        print("Error: Empty text input", file=sys.stderr)
        sys.exit(1)

    # --- Resolve backend ---
    if args.platform:
        backend, backend_src = args.platform, "cli"
    else:
        backend, backend_src = resolve_backend()

    # --- Resolve voice ---
    if args.voice:
        voice, voice_src = args.voice, "cli"
    else:
        voice, voice_src = resolve_voice(backend)

    # --- Resolve rate ---
    if args.rate:
        rate, rate_src = args.rate, "cli"
    else:
        rate, rate_src = resolve_speech_rate()

    # --- Resolve output ---
    if args.output:
        output_file = args.output
    else:
        # Auto-name: ttsCN-<backend>-<timestamp>.wav
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = f"ttsCN-{backend}-{ts}.{args.format}"

    # Ensure output has correct extension for format
    if args.format == "mp3" and not output_file.endswith(".mp3"):
        output_file = output_file.rsplit(".", 1)[0] + ".mp3" if "." in output_file else output_file + ".mp3"
    elif args.format == "wav" and not output_file.endswith(".wav"):
        output_file = output_file.rsplit(".", 1)[0] + ".wav" if "." in output_file else output_file + ".wav"

    # --- Display config ---
    print(f"Backend:  {backend} [from {backend_src}]")
    print(f"Voice:    {voice} [from {voice_src}]")
    if VOICE_DESCRIPTIONS.get(voice):
        print(f"          {VOICE_DESCRIPTIONS[voice]}")
    print(f"Rate:     {rate} [from {rate_src}]")
    print(f"Format:   {args.format}")
    print(f"Output:   {output_file}")
    print(f"Text:     {len(text)} characters")
    print()

    max_chars = get_max_chars(backend)

    # --- Dry run (no backend init needed) ---
    if args.dry_run:
        chunks = chunk_text(text, max_chars)
        cn_chars = len(re.findall(r"[一-鿿]", text))
        en_words = len(re.findall(r"[A-Za-z]+", text))
        est_duration = cn_chars / 4.0 + en_words / 3.0
        rate_match = re.match(r"([+-]?\d+)%", rate)
        if rate_match:
            est_duration /= 1.0 + int(rate_match.group(1)) / 100.0

        print("--- Dry Run ---")
        print(f"  Chinese chars:  {cn_chars}")
        print(f"  English words:  {en_words}")
        print(f"  Total chars:    {len(text)}")
        print(f"  Chunks:         {len(chunks)} (max {max_chars} chars/chunk)")
        print(f"  Est. duration:  {est_duration:.0f}s ({est_duration / 60:.1f} min)")
        print(f"  SSML:           {'yes' if BACKENDS[backend]['supports_ssml'] else 'no'}")
        print(f"  API call:       not made")
        return

    # --- Init backend (validates packages + env vars) ---
    try:
        config = init_backend(backend)
    except BackendError as e:
        print(f"Error: {e}", file=sys.stderr)
        if isinstance(e, MissingPackageError) and e.install_cmd:
            print(f"  Fix: {e.install_cmd}", file=sys.stderr)
        if isinstance(e, MissingEnvVarError) and e.var:
            print(f"  Set: export {e.var}=<your_key>", file=sys.stderr)
        sys.exit(1)

    config["voice"] = voice
    config["speech_rate"] = rate

    # --- Synthesize ---
    chunks = chunk_text(text, max_chars)
    print(f"Split into {len(chunks)} chunk(s) (max {max_chars} chars/chunk)\n")

    synthesize = get_synthesize_func(backend)
    started_at = time.time()
    try:
        duration = synthesize(chunks, config, output_file, output_format=args.format)
    except Exception as e:
        print(f"\nError: Synthesis failed: {e}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - started_at
    file_size = Path(output_file).stat().st_size
    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB"

    print(f"\nDone!")
    print(f"  Output:   {output_file} ({size_str})")
    print(f"  Duration: {duration:.1f}s ({duration / 60:.1f} min)")
    print(f"  Time:     {elapsed:.1f}s wall clock")


if __name__ == "__main__":
    main()
