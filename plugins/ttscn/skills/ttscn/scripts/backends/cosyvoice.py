"""Alibaba DashScope CosyVoice TTS backend."""

import json
import os
import time


def _extract_words(event, words_by_index):
    """Fold a websocket event into {sentence_index: words}; last event wins.

    With word_timestamp_enabled, result-generated events carry
    payload.output.sentence.words — a progressively growing array, so the
    final event per sentence index holds the complete word list.
    """
    try:
        obj = json.loads(event) if isinstance(event, str) else event
        sent = (obj.get("payload", {}).get("output") or {}).get("sentence") or {}
        words = sent.get("words")
        if words:
            words_by_index[sent.get("index", 0)] = words
    except (ValueError, TypeError, AttributeError):
        pass


def _to_boundaries(words_by_index, base_offset):
    """Flatten per-sentence word arrays into boundary dicts (seconds).

    Words carry {"text", "begin_time", "end_time"} in milliseconds,
    absolute within the invocation's stream; base_offset makes them
    absolute in the final file. Older models (cosyvoice-v1) ignore the
    request flag and simply yield no words.
    """
    out = []
    try:
        for idx in sorted(words_by_index):
            for w in words_by_index[idx]:
                out.append({
                    "text": w["text"],
                    "offset": base_offset + float(w["begin_time"]) / 1000.0,
                    "duration": (float(w["end_time"])
                                 - float(w["begin_time"])) / 1000.0,
                })
    except (KeyError, TypeError, ValueError):
        return []
    return out


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using CosyVoice (DashScope) streaming TTS.

    config keys: model, voice, speech_rate
    Returns: (total_duration_seconds, word_boundaries) — boundaries from
    word_timestamp_enabled events; empty list on models without support.
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
    word_boundaries = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                audio_buf = bytearray()
                words_by_index = {}

                class Callback(ResultCallback):
                    def on_data(self, data):
                        audio_buf.extend(data)

                    def on_event(self, message):
                        _extract_words(message, words_by_index)

                    def on_error(self, message):
                        raise RuntimeError(f"CosyVoice error: {message}")

                synth = SpeechSynthesizer(
                    model=model,
                    voice=voice,
                    format=AudioFormat.PCM_48000HZ_MONO_16BIT,
                    speech_rate=cosy_rate,
                    callback=Callback(),
                    additional_params={"word_timestamp_enabled": True},
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
                word_boundaries.extend(
                    _to_boundaries(words_by_index, accumulated_duration))
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

    return accumulated_duration, word_boundaries
