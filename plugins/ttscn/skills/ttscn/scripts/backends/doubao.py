"""ByteDance Volcano Ark Doubao TTS backend.

Two transports, selected by config:
- v1 (legacy): POST https://openspeech.bytedance.com/api/v1/tts with
  appid/token/cluster in the body — used when VOLCENGINE_API_KEY is unset.
- v3 (recommended): POST https://openspeech.bytedance.com/api/v3/tts/unidirectional
  with X-Api-Key + X-Api-Resource-Id headers and NO appid. Required for the
  Doubao TTS 2.0 voices (seed-tts-2.0 resource, e.g. zh_female_vv_uranus_bigtts).
"""

import os
import json
import time
import uuid
import base64
import subprocess
import re


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


def _parse_v3_words(sentence, base_offset):
    """Parse a v3 sentence event into boundary dicts.

    Words carry {"word", "startTime", "endTime"} in seconds, relative to the
    chunk/session; base_offset makes them absolute in the final file.
    """
    out = []
    for w in (sentence or {}).get("words") or []:
        try:
            start = float(w["startTime"])
            end = float(w["endTime"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"text": w.get("word", ""),
                    "offset": base_offset + start,
                    "duration": end - start})
    return out


def _normalize_part(part_file):
    """Normalize a raw part to 48kHz mono WAV in place."""
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


def _probe_duration(part_file):
    """Return the WAV duration in seconds via ffprobe."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration", "-of", "csv=p=0", part_file],
        capture_output=True, text=True,
    )
    return float(probe.stdout.strip()) if probe.stdout.strip() else 0.0


def _assemble_output(part_files, output_file):
    """Concatenate part files into output_file and clean up the parts."""
    if len(part_files) == 1:
        os.replace(part_files[0], output_file)
        return
    out_dir = os.path.dirname(output_file) or "."
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


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using Volcengine Doubao TTS HTTP API.

    v1 config keys: appid, token, cluster, voice, endpoint, speech_rate
    v3 config keys: api_key, resource_id, voice, endpoint, speech_rate
    Returns: (total_duration_seconds, word_boundaries) — boundaries from the
    with_timestamp frontend payload; empty list if the voice returns none.
    """
    if config.get("api_key"):
        return _synthesize_v3(chunks, config, output_file)
    import requests

    appid = config["appid"]
    token = config["token"]
    cluster = config.get("cluster", "volcano_tts")
    voice = config.get("voice", "BV001_streaming")
    endpoint = config.get(
        "endpoint", "https://openspeech.bytedance.com/api/v1/tts"
    )
    speech_rate = config.get("speech_rate", "+5%")

    rate_match = re.match(r"([+-]?\d+)%", speech_rate)
    speed_ratio = 1.0 + int(rate_match.group(1)) / 100.0 if rate_match else 1.0
    speed_ratio = max(0.2, min(3.0, speed_ratio))

    uid = os.environ.get("VOLCENGINE_UID", "ttscn")
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

                _normalize_part(part_file)
                chunk_duration = _probe_duration(part_file)
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

    _assemble_output(part_files, output_file)
    return accumulated_duration, word_boundaries


def _synthesize_v3(chunks, config, output_file):
    """Synthesize via the v3 unidirectional HTTP API.

    API-key auth (X-Api-Key + X-Api-Resource-Id), no appid. Word boundaries
    come from the streamed sentence events (original-text based on 2.0 voices).
    """
    import requests

    api_key = config["api_key"]
    resource_id = config.get("resource_id", "seed-tts-2.0")
    voice = config.get("voice", "BV001_streaming")
    if voice == "BV001_streaming" and config.get("voice_source") == "default":
        # BV001_streaming is a v1-only voice; pick a 2.0 voice instead.
        voice = "zh_female_vv_uranus_bigtts"
    endpoint = config.get(
        "endpoint",
        "https://openspeech.bytedance.com/api/v3/tts/unidirectional",
    )

    speech_rate = config.get("speech_rate", "+5%")
    rate_match = re.match(r"([+-]?\d+)%", speech_rate)
    speed_ratio = 1.0 + int(rate_match.group(1)) / 100.0 if rate_match else 1.0
    speed_ratio = max(0.5, min(2.0, speed_ratio))
    speech_rate_v3 = int(round((speed_ratio - 1.0) * 100))

    uid = os.environ.get("VOLCENGINE_UID", "ttscn")
    timeout_sec = int(os.environ.get("VOLCENGINE_TIMEOUT_SEC", "60"))
    sample_rate = int(os.environ.get("VOLCENGINE_SAMPLE_RATE", "48000"))
    # 2.0 resources return original-text subtitles; 1.0 returns TN-based ones.
    enable_subtitle = "2.0" in resource_id

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    word_boundaries = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                headers = {
                    "X-Api-Key": api_key,
                    "X-Api-Resource-Id": resource_id,
                    "X-Api-Request-Id": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                }
                payload = {
                    "user": {"uid": uid},
                    "req_params": {
                        "text": chunk,
                        "speaker": voice,
                        "audio_params": {
                            "format": "pcm",
                            "sample_rate": sample_rate,
                            "speech_rate": speech_rate_v3,
                            "enable_subtitle": enable_subtitle,
                            "enable_timestamp": not enable_subtitle,
                        },
                    },
                }

                resp = requests.post(
                    endpoint, headers=headers, json=payload,
                    timeout=timeout_sec, stream=True,
                )
                resp.raise_for_status()

                audio_bytes = b""
                chunk_boundaries = []
                for raw_line in resp.iter_lines(decode_unicode=True):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        continue
                    code = msg.get("code", 0)
                    if code not in (0, 20000000):
                        raise RuntimeError(
                            f"Doubao v3 API error code={code}, "
                            f"message={msg.get('message')}"
                        )
                    if msg.get("data"):
                        audio_bytes += base64.b64decode(msg["data"])
                    if msg.get("sentence"):
                        chunk_boundaries.extend(_parse_v3_words(
                            msg["sentence"], accumulated_duration))

                if not audio_bytes:
                    raise RuntimeError("Doubao v3 returned empty audio")
                with open(part_file, "wb") as f:
                    f.write(audio_bytes)

                _normalize_part(part_file)
                chunk_duration = _probe_duration(part_file)
                word_boundaries.extend(chunk_boundaries)
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

    _assemble_output(part_files, output_file)
    return accumulated_duration, word_boundaries
