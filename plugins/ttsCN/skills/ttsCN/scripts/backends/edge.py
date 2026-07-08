"""Microsoft Edge TTS backend — free, no API key needed, works in China."""

import os
import subprocess
import time


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using Edge TTS, concat chunks into a single output file.

    config keys: voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    import asyncio
    import edge_tts

    voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
    speech_rate = config.get("speech_rate", "+5%")
    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    async def run():
        nonlocal accumulated_duration
        for i, chunk in enumerate(chunks):
            part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
            part_files.append(part_file)
            mp3_file = part_file.replace(".wav", ".mp3")

            for attempt in range(1, 4):
                try:
                    audio_data = bytearray()
                    communicate = edge_tts.Communicate(
                        chunk, voice=voice, rate=speech_rate
                    )
                    async for event in communicate.stream():
                        if event["type"] == "audio":
                            audio_data.extend(event["data"])

                    if not audio_data:
                        raise RuntimeError("No audio data received")

                    with open(mp3_file, "wb") as f:
                        f.write(bytes(audio_data))
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", mp3_file,
                         "-ar", "48000", "-ac", "1", part_file],
                        capture_output=True,
                    )
                    if os.path.exists(mp3_file):
                        os.remove(mp3_file)

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

    asyncio.run(run())

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
