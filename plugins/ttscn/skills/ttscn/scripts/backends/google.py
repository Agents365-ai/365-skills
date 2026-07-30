"""Google Cloud TTS backend — international, 220+ voices, 40+ languages."""

import base64
import os
import re
import subprocess
import time


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via Google Cloud text:synthesize API, concat into output_file.

    config keys: key, voice, language, speech_rate
    Returns: total_duration_seconds (float)
    """
    import requests

    key = config["key"]
    voice = config.get("voice", "en-US-Neural2-F")
    # Language: explicit config wins, else derive from voice name
    # (e.g. "cmn-CN-Wavenet-A" -> "cmn-CN")
    language = config.get("language") or "-".join(voice.split("-")[:2])
    speech_rate = config.get("speech_rate", "+5%")

    # Convert rate string ("+5%") to API speakingRate (0.25 - 4.0)
    rate_match = re.match(r"([+-]?\d+)%", speech_rate)
    speaking_rate = 1.0 + int(rate_match.group(1)) / 100.0 if rate_match else 1.0
    speaking_rate = max(0.25, min(4.0, speaking_rate))

    url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    headers = {"X-Goog-Api-Key": key, "Content-Type": "application/json"}

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)
        tmp_file = part_file + ".tmp.wav"

        for attempt in range(1, 4):
            try:
                payload = {
                    "input": {"text": chunk},
                    "voice": {
                        "languageCode": language,
                        "name": voice,
                    },
                    "audioConfig": {
                        "audioEncoding": "LINEAR16",
                        "sampleRateHertz": 48000,
                        "speakingRate": speaking_rate,
                    },
                }
                resp = requests.post(url, json=payload, headers=headers,
                                     timeout=120)
                resp.raise_for_status()
                audio_b64 = resp.json().get("audioContent")
                if not audio_b64:
                    raise RuntimeError("Google TTS returned empty audio")

                with open(tmp_file, "wb") as f:
                    f.write(base64.b64decode(audio_b64))
                conv = subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_file,
                     "-ar", "48000", "-ac", "1", part_file],
                    capture_output=True, text=True,
                )
                if conv.returncode != 0:
                    raise RuntimeError(
                        f"ffmpeg convert failed: {conv.stderr[-200:]}"
                    )
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)

                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries",
                     "format=duration", "-of", "csv=p=0", part_file],
                    capture_output=True, text=True,
                )
                chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
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

    return accumulated_duration
