"""MiniMax TTS backend — best quality, 300+ voices, voice cloning."""

import os
import json
import re
import subprocess

# Parenthesized ASCII runs in the sent text are engine syntax on minimax —
# pinyin annotations 字(zi4) and sound tags (chuckle) — and come back as
# their own timestamped_words entries (one per phonetic symbol). They are
# not script text; drop them from the boundary stream.
_ENGINE_TOKEN = re.compile(r"^\([0-9a-zü]+\)$")


def _parse_subtitles(entries, base_offset):
    """Extract word-level boundaries from subtitle-file entries (seconds).

    The downloaded file is an array of sentence blocks; with
    subtitle_type=word each block carries timestamped_words with
    {"word", "time_begin", "time_end"} in milliseconds, relative to the
    chunk (punctuation included, with real timings). base_offset makes
    them absolute in the final file. Blocks without word data are skipped
    — coarse ~50-char sentence blocks would be worse than the consumer's
    per-char estimation fallback.
    """
    try:
        return [{"text": w["word"],
                 "offset": base_offset + float(w["time_begin"]) / 1000.0,
                 "duration": (float(w["time_end"]) - float(w["time_begin"])) / 1000.0}
                for s in entries
                for w in (s.get("timestamped_words") or [])
                if not _ENGINE_TOKEN.match(w["word"])]
    except (KeyError, TypeError, ValueError, AttributeError):
        return []


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via MiniMax T2A v2 API.

    config keys: api_key, model, voice, group_id, speech_rate
    Returns: (total_duration_seconds, word_boundaries) — boundaries come from
    the subtitle_file download (word granularity); empty list on any subtitle
    failure so synthesis itself never breaks over timing metadata.
    """
    import requests

    api_key = config["api_key"]
    model = config.get("model", "speech-2.6-hd")
    voice_id = config.get("voice", "female-shaonv")
    group_id = config.get("group_id", "")
    speech_rate = config.get("speech_rate", "+5%")

    # Convert rate string to speed (0.5 - 2.0, default 1.0)
    import re as _re
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    speed = 1.0
    if rate_match:
        pct = int(rate_match.group(1))
        speed = max(0.5, min(2.0, 1.0 + pct / 100.0))

    # Global site by default; China-site users set MINIMAX_API_BASE
    # (e.g. https://api.minimaxi.com/v1) — same env var clone.py honors.
    api_base = os.environ.get("MINIMAX_API_BASE", "https://api.minimax.io/v1")
    url = f"{api_base.rstrip('/')}/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    word_boundaries = []
    accumulated_duration = 0.0

    for i, text in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.mp3")
        part_files.append(part_file)

        payload = json.dumps({
            "model": model,
            "text": text,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "format": "mp3",
                "sample_rate": 32000,
                "bitrate": 128000,
                "channel": 1,
            },
            "language_boost": "Chinese",
            "subtitle_enable": True,
            "subtitle_type": "word",
        })
        if group_id:
            payload_dict = json.loads(payload)
            payload_dict["group_id"] = group_id
            payload = json.dumps(payload_dict)

        resp = requests.post(url, headers=headers, data=payload, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(
                f"MiniMax API error {resp.status_code}: {resp.text[:300]}"
            )

        # t2a_v2 returns JSON with hex-encoded audio in data.audio;
        # binary body is only kept as a fallback for non-JSON responses.
        subtitle_url = None
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            body = resp.json()
            base_resp = body.get("base_resp") or {}
            if base_resp.get("status_code", -1) != 0:
                raise RuntimeError(
                    f"MiniMax API error {base_resp.get('status_code')}: "
                    f"{base_resp.get('status_msg', 'unknown')}"
                )
            audio_hex = (body.get("data") or {}).get("audio")
            if not audio_hex:
                raise RuntimeError("MiniMax API returned no audio data")
            audio_bytes = bytes.fromhex(audio_hex)
            subtitle_url = (body.get("data") or {}).get("subtitle_file")
        else:
            audio_bytes = resp.content

        with open(part_file, "wb") as f:
            f.write(audio_bytes)

        # Convert to 48kHz mono WAV
        wav_file = part_file.replace(".mp3", ".wav")
        conv_result = subprocess.run(
            ["ffmpeg", "-y", "-i", part_file,
             "-ar", "48000", "-ac", "1", wav_file],
            capture_output=True,
        )
        if conv_result.returncode == 0:
            part_files[i] = wav_file
            if os.path.exists(part_file):
                os.remove(part_file)
        else:
            wav_file = part_file  # keep mp3

        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", wav_file],
            capture_output=True, text=True,
        )
        chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        if subtitle_url:
            # Best-effort: the URL expires after 24h and word-level subtitle
            # payloads are not guaranteed on every model — never fail the run.
            try:
                sub = requests.get(subtitle_url, timeout=30)
                word_boundaries.extend(
                    _parse_subtitles(sub.json(), accumulated_duration))
            except Exception:
                pass
        accumulated_duration += chunk_duration
        print(f"  Part {i + 1}/{len(chunks)} done "
              f"({len(text)} chars, {chunk_duration:.1f}s)")

    # Write final output
    wav_part_files = [f for f in part_files if os.path.exists(f)]
    if len(wav_part_files) == 1:
        os.replace(wav_part_files[0], output_file)
    else:
        concat_list = os.path.join(out_dir, ".tts_concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for pf in wav_part_files:
                f.write(f"file '{os.path.basename(pf)}'\n")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", output_file],
            capture_output=True, text=True, cwd=out_dir,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:200]}")
        os.remove(concat_list)
        for pf in wav_part_files:
            if os.path.exists(pf):
                os.remove(pf)

    return accumulated_duration, word_boundaries
