"""ByteDance Volcano Ark Doubao TTS backend."""

import os
import json
import time
import uuid
import base64
import subprocess


def _parse_frontend_words(frontend_json, base_offset):
    """Parse addition.frontend (a JSON-encoded string) into boundary dicts.

    The words array carries {"word", "start_time", "end_time"} in seconds,
    relative to the chunk; base_offset makes them absolute in the final file.
    Timestamps already reflect speed_ratio (applied server-side).
    """
    if not frontend_json:
        return []
    try:
        words = json.loads(frontend_json).get("words") or []
        return [{"text": w["word"],
                 "offset": base_offset + float(w["start_time"]),
                 "duration": float(w["end_time"]) - float(w["start_time"])}
                for w in words]
    except (ValueError, KeyError, TypeError):
        return []


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using Volcengine Doubao TTS HTTP API.

    config keys: appid, token, cluster, voice, endpoint, speech_rate
    Returns: (total_duration_seconds, word_boundaries) — boundaries from the
    with_timestamp frontend payload; empty list if the voice returns none.
    """
    import requests

    appid = config["appid"]
    token = config["token"]
    cluster = config.get("cluster", "volcano_tts")
    voice = config.get("voice", "BV001_streaming")
    endpoint = config.get(
        "endpoint", "https://openspeech.bytedance.com/api/v1/tts"
    )
    speech_rate = config.get("speech_rate", "+5%")

    import re as _re
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    speed_ratio = 1.0 + int(rate_match.group(1)) / 100.0 if rate_match else 1.0
    speed_ratio = max(0.2, min(3.0, speed_ratio))

    uid = os.environ.get("VOLCENGINE_UID", "ttsCN")
    timeout_sec = int(os.environ.get("VOLCENGINE_TIMEOUT_SEC", "60"))
    sample_rate = int(os.environ.get("VOLCENGINE_SAMPLE_RATE", "48000"))

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    word_boundaries = []
    accumulated_duration = 0.0

    headers = {
        "Authorization": f"Bearer; {token}",
        "Content-Type": "application/json",
    }

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                req_id = str(uuid.uuid4())
                payload = {
                    "app": {"appid": appid, "token": token, "cluster": cluster},
                    "user": {"uid": uid},
                    "audio": {
                        "voice_type": voice,
                        "encoding": "wav",
                        "rate": sample_rate,
                        "speed_ratio": speed_ratio,
                        "volume_ratio": 1.0,
                        "pitch_ratio": 1.0,
                    },
                    "request": {
                        "reqid": req_id,
                        "text": chunk,
                        "text_type": "plain",
                        "operation": "query",
                        "with_timestamp": 1,
                    },
                }

                resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout_sec)
                resp.raise_for_status()
                data = resp.json()

                code = data.get("code")
                if code != 3000:
                    raise RuntimeError(
                        f"Doubao API error code={code}, message={data.get('message')}"
                    )

                audio_b64 = data.get("data")
                if not audio_b64:
                    raise RuntimeError("Doubao API returned empty audio data")
                audio_bytes = base64.b64decode(audio_b64)
                with open(part_file, "wb") as f:
                    f.write(audio_bytes)

                # Normalize to 48kHz mono WAV
                normalized = part_file + ".norm.wav"
                norm_result = subprocess.run(
                    ["ffmpeg", "-y", "-i", part_file,
                     "-ar", "48000", "-ac", "1", normalized],
                    capture_output=True,
                )
                if norm_result.returncode != 0:
                    raise RuntimeError(
                        f"ffmpeg normalization failed: "
                        f"{norm_result.stderr.decode()[:200]}"
                    )
                os.replace(normalized, part_file)

                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries",
                     "format=duration", "-of", "csv=p=0", part_file],
                    capture_output=True, text=True,
                )
                chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
                word_boundaries.extend(_parse_frontend_words(
                    (data.get("addition") or {}).get("frontend"),
                    accumulated_duration))
                accumulated_duration += chunk_duration
                print(f"  Part {i + 1}/{len(chunks)} done "
                      f"({len(chunk)} chars, {chunk_duration:.1f}s)")
                break
            except Exception as e:
                print(f"  Part {i + 1} attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(attempt * 2)
                else:
                    raise RuntimeError(
                        f"Part {i + 1} synthesis failed after 3 attempts"
                    )

    # Write final output
    if len(part_files) == 1:
        os.replace(part_files[0], output_file)
    else:
        concat_list = os.path.join(out_dir, ".tts_concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for pf in part_files:
                f.write(f"file '{os.path.basename(pf)}'\n")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", output_file],
            capture_output=True, text=True, cwd=out_dir,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:200]}")
        os.remove(concat_list)
        for pf in part_files:
            if os.path.exists(pf):
                os.remove(pf)

    return accumulated_duration, word_boundaries
