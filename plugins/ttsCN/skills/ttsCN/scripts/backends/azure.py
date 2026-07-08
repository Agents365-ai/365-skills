"""Azure Cognitive Services TTS backend."""

import os
import time


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using Azure TTS with SSML.

    config keys: key, region, voice, speech_rate
    Returns: total_duration_seconds (float)
    """
    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(
        subscription=config["key"],
        region=config.get("region", "eastasia"),
    )
    voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
    speech_config.SpeechSynthesisVoiceName = voice
    speech_rate = config.get("speech_rate", "+5%")

    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    accumulated_duration = 0.0

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                audio = speechsdk.audio.AudioOutputConfig(filename=part_file)
                synth = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config, audio_config=audio,
                )

                ssml = (
                    f'<speak version="1.0" '
                    f'xmlns="http://www.w3.org/2001/10/synthesis" '
                    f'xmlns:mstts="https://www.w3.org/2001/mstts" '
                    f'xml:lang="zh-CN">'
                    f'<voice name="{voice}">'
                    f'<prosody rate="{speech_rate}">{chunk}</prosody>'
                    f'</voice>'
                    f'</speak>'
                )

                result = synth.speak_ssml_async(ssml).get()
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    chunk_duration = result.audio_duration.total_seconds()
                    accumulated_duration += chunk_duration
                    print(f"  Part {i + 1}/{len(chunks)} done "
                          f"({len(chunk)} chars, {chunk_duration:.1f}s)")
                    break
                else:
                    details = result.cancellation_details.error_details
                    raise RuntimeError(f"Azure synthesis failed: {details}")
            except Exception as e:
                print(f"  Part {i + 1} attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(attempt * 2)
                else:
                    raise RuntimeError(
                        f"Part {i + 1} synthesis failed after 3 attempts"
                    )

    # Write final output
    import subprocess
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
