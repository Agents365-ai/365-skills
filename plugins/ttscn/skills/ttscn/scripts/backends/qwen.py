"""Alibaba Qwen3-TTS backend (DashScope) — reuses DASHSCOPE_API_KEY."""

import os
import subprocess
import time


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via qwen3-tts-flash, concat into output_file.

    config keys: model, voice, language_type, instructions
    Uses dashscope.MultiModalConversation (non-streaming): the response's
    output.audio.url points at the full audio file (valid 24h), which we
    download. No word timestamps on this path, so word_boundaries are
    always empty. The HTTP mode has no rate parameter — speech_rate is
    ignored; use qwen3-tts-instruct-flash + QWEN_TTS_INSTRUCTIONS for
    prosody control instead.
    Returns: total_duration_seconds (float)
    """
    import dashscope
    import requests
    from dashscope.api_entities.dashscope_response import (
        MultiModalConversationResponse,
    )

    model = config.get("model", "qwen3-tts-flash")
    voice = config.get("voice", "Cherry")
    language_type = config.get("language_type") or None  # omit = Auto
    instructions = config.get("instructions") or None  # instruct models only

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)
        tmp_file = part_file + ".tmp"

        for attempt in range(1, 4):
            try:
                call_kwargs: dict = {
                    "model": model,
                    "text": chunk,
                    "voice": voice,
                    "stream": False,
                }
                if language_type:
                    call_kwargs["language_type"] = language_type
                if instructions:
                    call_kwargs["instructions"] = instructions
                resp = dashscope.MultiModalConversation.call(**call_kwargs)
                if not isinstance(resp, MultiModalConversationResponse):
                    raise RuntimeError("Qwen-TTS returned a stream unexpectedly")
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Qwen-TTS error {resp.status_code}: {str(resp)[:300]}"
                    )
                audio_url = None
                if isinstance(resp.output, dict):
                    audio = resp.output.get("audio") or {}
                    if isinstance(audio, dict):
                        audio_url = audio.get("url")
                if not audio_url:
                    raise RuntimeError("Qwen-TTS returned no audio URL")
                audio_resp = requests.get(audio_url, timeout=120)
                audio_resp.raise_for_status()
                if not audio_resp.content:
                    raise RuntimeError("Qwen-TTS returned empty audio")

                with open(tmp_file, "wb") as f:
                    f.write(audio_resp.content)
                conv = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        tmp_file,
                        "-ar",
                        "48000",
                        "-ac",
                        "1",
                        part_file,
                    ],
                    capture_output=True,
                    text=True,
                )
                if conv.returncode != 0:
                    raise RuntimeError(f"ffmpeg convert failed: {conv.stderr[-200:]}")
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)

                probe = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "quiet",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "csv=p=0",
                        part_file,
                    ],
                    capture_output=True,
                    text=True,
                )
                chunk_duration = (
                    float(probe.stdout.strip()) if probe.stdout.strip() else 0
                )
                accumulated_duration += chunk_duration
                print(
                    f"  Part {i + 1}/{len(chunks)} done "
                    f"({len(chunk)} chars, {chunk_duration:.1f}s)"
                )
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
        # pi-lens-ignore: ast-grep:unchecked-throwing-call-python
        with open(concat_list, "w", encoding="utf-8") as f:
            for pf in part_files:
                f.write(f"file '{os.path.basename(pf)}'\n")
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                output_file,
            ],
            capture_output=True,
            text=True,
            cwd=out_dir,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:200]}")
        # pi-lens-ignore: ast-grep:unchecked-throwing-call-python
        os.remove(concat_list)
        for pf in part_files:
            if os.path.exists(pf):
                # pi-lens-ignore: ast-grep:unchecked-throwing-call-python
                os.remove(pf)

    return accumulated_duration
