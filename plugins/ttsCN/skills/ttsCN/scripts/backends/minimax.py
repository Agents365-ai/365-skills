"""MiniMax TTS backend — best quality, 300+ voices, voice cloning."""

import os
import json
import subprocess


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via MiniMax T2A v2 API.

    config keys: api_key, model, voice, group_id, speech_rate
    Returns: total_duration_seconds (float)
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

    url = "https://api.minimax.io/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
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

        # Check if response is JSON (error) or binary (audio)
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            err_data = resp.json()
            raise RuntimeError(
                f"MiniMax API error: {err_data.get('base_resp', {}).get('status_msg', 'unknown')}"
            )

        with open(part_file, "wb") as f:
            f.write(resp.content)

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

    return accumulated_duration
