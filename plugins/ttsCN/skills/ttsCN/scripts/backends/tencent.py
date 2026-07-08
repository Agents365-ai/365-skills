"""Tencent Cloud TTS backend — lowest cost, 380+ voices, SSML."""

import os
import base64
import subprocess
import uuid


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via Tencent Cloud TextToVoice API.

    config keys: secret_id, secret_key, region, voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.tts.v20190823 import tts_client, models

    cred = credential.Credential(config["secret_id"], config["secret_key"])
    client = tts_client.TtsClient(cred, config.get("region", "ap-shanghai"))

    voice_type = int(config.get("voice", "101001"))
    speech_rate = config.get("speech_rate", "+5%")

    # Convert rate string ("+5%") to Speed param (-2 to 2, default 0)
    import re as _re
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    speed = 0
    if rate_match:
        pct = int(rate_match.group(1))
        speed = max(-2.0, min(2.0, pct / 50.0))

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, text in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        try:
            req = models.TextToVoiceRequest()
            req.Text = text
            req.SessionId = str(uuid.uuid4())
            req.VoiceType = voice_type
            req.PrimaryLanguage = 1  # Chinese
            req.SampleRate = 16000
            req.Codec = "wav"
            req.Speed = speed
            req.Volume = 5

            resp = client.TextToVoice(req)

            audio_data = base64.b64decode(resp.Audio)
            with open(part_file, "wb") as f:
                f.write(audio_data)

            # Resample to 48kHz mono for consistency
            normalized = part_file + ".norm.wav"
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", part_file,
                 "-ar", "48000", "-ac", "1", normalized],
                capture_output=True,
            )
            if result.returncode == 0:
                os.replace(normalized, part_file)

            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", part_file],
                capture_output=True, text=True,
            )
            chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
            accumulated_duration += chunk_duration
            print(f"  Part {i + 1}/{len(chunks)} done "
                  f"({len(text)} chars, {chunk_duration:.1f}s)")

        except TencentCloudSDKException as e:
            raise RuntimeError(f"Tencent TTS error: {e}")

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
