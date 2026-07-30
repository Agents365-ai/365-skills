"""Azure Cognitive Services TTS backend."""

import os
import re
import time
from xml.sax.saxutils import escape

from markers import render_markers
from phonemes import apply_phonemes


def build_ssml_fragment(chunk, phoneme_dict):
    """Render phonemes and expressiveness markers into an SSML fragment.

    apply_phonemes inserts <phoneme> tags, render_markers turns [PAUSE:x]
    into <break/> (and strips sound tags), then the surrounding text is
    XML-escaped while the generated tags are preserved via placeholders —
    same ordering the video-podcast-maker azure path uses.
    """
    frag = apply_phonemes(chunk, phoneme_dict or {})
    frag = render_markers(frag, "ssml")
    tags = []

    def _save(m):
        tags.append(m.group(0))
        return "\x00{}\x00".format(len(tags) - 1)

    frag = escape(re.sub(r"<[^>]+>", _save, frag))
    for i, tag in enumerate(tags):
        frag = frag.replace("\x00{}\x00".format(i), tag)
    return frag


def _style_wrap(block):
    """Wrap in mstts:express-as when env TTS_STYLE is set (e.g. "gentle").

    Empty/unset keeps plain neural prosody — some voices (Multilingual
    variants) produce vocoder artifacts under express-as.
    """
    style = os.environ.get("TTS_STYLE", "")
    return (f'<mstts:express-as style="{style}">{block}</mstts:express-as>'
            if style else block)


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize using Azure TTS with SSML and word boundary tracking.

    config keys: key, region, voice, speech_rate, phoneme_dict
    Returns: (total_duration_seconds, word_boundaries) where each boundary
    is {"text", "offset", "duration"} in seconds, absolute in the final file.
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
    word_boundaries = []
    accumulated_duration = 0.0
    phoneme_dict = config.get("phoneme_dict") or {}

    for i, chunk in enumerate(chunks):
        part_file = os.path.join(out_dir, f".tts_part_{i:04d}.wav")
        part_files.append(part_file)

        for attempt in range(1, 4):
            try:
                audio = speechsdk.audio.AudioOutputConfig(filename=part_file)
                synth = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config, audio_config=audio,
                )

                # Collect per attempt; merged only on success so a failed
                # attempt can't leave duplicate boundaries behind.
                attempt_words = []
                chunk_start = accumulated_duration  # snapshot for closure

                def word_boundary_cb(evt, _start=chunk_start):
                    # Punctuation boundaries carry no spoken text — skip them.
                    if getattr(evt, "boundary_type", None) == \
                            speechsdk.SpeechSynthesisBoundaryType.Punctuation:
                        return
                    attempt_words.append({
                        "text": evt.text,
                        # audio_offset is in 100-ns ticks
                        "offset": _start + evt.audio_offset / 10_000_000,
                        "duration": evt.duration.total_seconds(),
                    })
                synth.synthesis_word_boundary.connect(word_boundary_cb)

                fragment = build_ssml_fragment(chunk, phoneme_dict)
                inner = _style_wrap(
                    f'<prosody rate="{speech_rate}">{fragment}</prosody>')
                ssml = (
                    f'<speak version="1.0" '
                    f'xmlns="http://www.w3.org/2001/10/synthesis" '
                    f'xmlns:mstts="https://www.w3.org/2001/mstts" '
                    f'xml:lang="zh-CN">'
                    f'<voice name="{voice}">'
                    f'{inner}'
                    f'</voice>'
                    f'</speak>'
                )

                result = synth.speak_ssml_async(ssml).get()
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    chunk_duration = result.audio_duration.total_seconds()
                    accumulated_duration += chunk_duration
                    word_boundaries.extend(attempt_words)
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

    return accumulated_duration, word_boundaries
