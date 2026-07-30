"""iFlytek Xunfei TTS backend — 500+ voices, MOS 4.8, WebSocket streaming."""

import os
import base64
import hashlib
import hmac
import json
import subprocess
import time
from datetime import datetime
from urllib.parse import urlencode


def _build_auth_url(app_id, api_key, api_secret):
    """Build Xunfei WebSocket auth URL with HMAC-SHA256 signature."""
    host = "ws-api.xfyun.cn"
    url = "wss://tts-api.xfyun.cn/v2/tts"
    now = datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    signature_origin = (
        f"host: {host}\ndate: {date_str}\nGET /v2/tts HTTP/1.1"
    )
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode()

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    params = {
        "authorization": authorization,
        "date": date_str,
        "host": host,
    }
    return url + "?" + urlencode(params)


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via Xunfei WebSocket TTS API.

    config keys: app_id, api_key, api_secret, voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    import websocket

    app_id = config["app_id"]
    api_key = config["api_key"]
    api_secret = config["api_secret"]
    voice_name = config.get("voice", "xiaoyan")
    speech_rate = config.get("speech_rate", "+5%")

    # Convert rate to Xunfei speed (0-100, default 50)
    import re as _re
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    speed = 50
    if rate_match:
        pct = int(rate_match.group(1))
        speed = max(0, min(100, 50 + pct))

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, text in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        audio_data = bytearray()
        ws_error = []

        def on_open(ws):
            params = {
                "common": {"app_id": app_id},
                "business": {
                    "aue": "raw",
                    "auf": "audio/L16;rate=16000",
                    "vcn": voice_name,
                    "speed": speed,
                    "volume": 50,
                    "pitch": 50,
                    "tte": "utf8",
                },
                "data": {
                    "status": 2,
                    "text": base64.b64encode(text.encode("utf-8")).decode(),
                },
            }
            ws.send(json.dumps(params))

        def on_message(ws, message):
            try:
                msg = json.loads(message)
                code = msg.get("code", 0)
                if code != 0:
                    ws_error.append(f"Xunfei error code={code}, message={msg.get('message', '')}")
                    return
                data_field = msg.get("data", {})
                audio_b64 = data_field.get("audio")
                if audio_b64:
                    audio_data.extend(base64.b64decode(audio_b64))
                status = data_field.get("status")
                if status == 2:  # end of synthesis
                    ws.close()
            except Exception as e:
                ws_error.append(str(e))

        def on_error(ws, error):
            ws_error.append(str(error))

        url = _build_auth_url(app_id, api_key, api_secret)
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
        )
        ws.run_forever()

        if ws_error:
            raise RuntimeError(f"Xunfei TTS error: {ws_error[0]}")

        if not audio_data:
            raise RuntimeError("No audio data received from Xunfei")

        # Write PCM raw data as WAV
        import struct
        pcm_data = bytes(audio_data)
        data_size = len(pcm_data)
        wav_header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1, 16000,
            16000 * 2, 2, 16,
            b"data", data_size,
        )
        with open(part_file + ".pcm.wav", "wb") as f:
            f.write(wav_header + pcm_data)

        # Resample to 48kHz
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", part_file + ".pcm.wav",
             "-ar", "48000", "-ac", "1", part_file],
            capture_output=True,
        )
        if os.path.exists(part_file + ".pcm.wav"):
            os.remove(part_file + ".pcm.wav")
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg resample failed: {result.stderr.decode()[:200]}")

        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", part_file],
            capture_output=True, text=True,
        )
        chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        accumulated_duration += chunk_duration
        print(f"  Part {i + 1}/{len(chunks)} done "
              f"({len(text)} chars, {chunk_duration:.1f}s)")

        # Rate limit: Xunfei free tier ~5 QPS
        time.sleep(0.3)

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
