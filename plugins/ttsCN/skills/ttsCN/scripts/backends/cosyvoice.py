"""Alibaba DashScope CosyVoice TTS backend."""

import os
import time


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using CosyVoice (DashScope) streaming TTS.

    config keys: model, voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    import re as _re
    import struct
    import json as _json
    from dashscope.audio.tts_v2 import (
        SpeechSynthesizer, ResultCallback, AudioFormat,
    )

    speech_rate = config.get("speech_rate", "+5%")
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    cosy_rate = 1.0 + int(rate_match.group(1)) / 100.0 if rate_match else 1.0
    cosy_rate = max(0.5, min(2.0, cosy_rate))

    model = os.environ.get("COSYVOICE_MODEL", "cosyvoice-v3-flash")
    voice = config.get("voice", "longxiaochun_v3")
    sample_rate = 48000

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                audio_buf = bytearray()

                class Callback(ResultCallback):
                    def on_data(self, data):
                        audio_buf.extend(data)

                    def on_error(self, message):
                        raise RuntimeError(f"CosyVoice error: {message}")

                synth = SpeechSynthesizer(
                    model=model,
                    voice=voice,
                    format=AudioFormat.PCM_48000HZ_MONO_16BIT,
                    speech_rate=cosy_rate,
                    callback=Callback(),
                )
                synth.streaming_call(chunk)
                synth.streaming_complete()

                if not audio_buf:
                    raise RuntimeError("No audio data received")

                # Write PCM as WAV
                pcm_data = bytes(audio_buf)
                data_size = len(pcm_data)
                wav_header = struct.pack(
                    "<4sI4s4sIHHIIHH4sI",
                    b"RIFF", 36 + data_size, b"WAVE",
                    b"fmt ", 16, 1, 1, sample_rate,
                    sample_rate * 2, 2, 16,
                    b"data", data_size,
                )
                with open(part_file, "wb") as f:
                    f.write(wav_header + pcm_data)

                chunk_duration = data_size / (sample_rate * 2)
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
        import subprocess
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
