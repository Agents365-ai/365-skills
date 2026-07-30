"""Baidu AI TTS backend — 30+ voices, emotion synthesis, dialects."""

import os
import subprocess


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize via Baidu AipSpeech API.

    config keys: app_id, api_key, secret_key, voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    from aip import AipSpeech

    client = AipSpeech(config["app_id"], config["api_key"], config["secret_key"])
    voice_per = int(config.get("voice", "0"))
    speech_rate = config.get("speech_rate", "+5%")

    # Convert rate string to Baidu spd (0-15, default 5)
    import re as _re
    rate_match = _re.match(r"([+-]?\d+)%", speech_rate)
    spd = 5
    if rate_match:
        pct = int(rate_match.group(1))
        # Map -50%..+50% to 0..15, centered at 5
        spd = max(0, min(15, 5 + int(pct / 10)))

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    audio_format = "wav" if output_format == "wav" else "mp3"

    for i, text in enumerate(chunks):
        ext = "mp3" if audio_format == "mp3" else "wav"
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.{ext}")
        part_files.append(part_file)

        result = client.synthesis(
            text, "zh", 1,
            {
                "vol": 10, "per": voice_per, "spd": spd,
                "pit": 5, "aue": 3 if audio_format == "mp3" else 6,
            }
        )

        if isinstance(result, dict):
            raise RuntimeError(
                f"Baidu TTS error: err_no={result.get('err_no')}, "
                f"err_msg={result.get('err_msg')}"
            )

        with open(part_file, "wb") as f:
            f.write(result)

        # Resample to 48kHz mono WAV for consistency
        wav_file = part_file.replace(f".{ext}", ".wav")
        probe_result = subprocess.run(
            ["ffmpeg", "-y", "-i", part_file,
             "-ar", "48000", "-ac", "1", wav_file],
            capture_output=True,
        )
        if probe_result.returncode == 0 and wav_file != part_file:
            os.replace(wav_file, part_file)

        # If mp3 was converted to wav, track the wav file
        if ext == "mp3" and output_format == "wav":
            # part_file is now .wav (after os.replace), updated
            pass

        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", part_file],
            capture_output=True, text=True,
        )
        chunk_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        accumulated_duration += chunk_duration
        print(f"  Part {i + 1}/{len(chunks)} done "
              f"({len(text)} chars, {chunk_duration:.1f}s)")

    # Write final output
    if len(part_files) == 1:
        if output_format == "mp3":
            # Baidu native mp3, keep as-is if requested
            os.replace(part_files[0], output_file)
        else:
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
