"""Atlas Cloud TTS backend using the asynchronous Media API."""

import ipaddress
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urlparse


API_BASE = "https://api.atlascloud.ai/api/v1"
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
USER_AGENT = "ttscn-atlas/1.8.0"


def _prediction_data(response):
    data = response.get("data", response)
    if not isinstance(data, dict):
        raise RuntimeError("Atlas Cloud returned invalid prediction data")
    return data


def _output_url(prediction):
    outputs = prediction.get("outputs")
    value = outputs[0] if isinstance(outputs, list) and outputs else None
    if not isinstance(value, str):
        raise RuntimeError("Atlas Cloud prediction completed without audio output")
    parsed = urlparse(value)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        raise RuntimeError("Atlas Cloud returned an unsafe audio URL")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise RuntimeError("Atlas Cloud returned an unsafe audio URL")
    return value


def _request_json(requests, method, url, key, **kwargs):
    headers = {
        "Authorization": "Bearer {}".format(key),
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    try:
        if response.status_code != 200:
            raise RuntimeError(
                "Atlas Cloud API error {}: {}".format(
                    response.status_code, response.text[:300]
                )
            )
        body = response.json()
    finally:
        response.close()
    if not isinstance(body, dict):
        raise RuntimeError("Atlas Cloud returned an invalid JSON response")
    if body.get("code") not in (None, 0, 200):
        raise RuntimeError(
            "Atlas Cloud API error {}: {}".format(
                body.get("code"), body.get("message", "unknown")
            )
        )
    return body


def _download(requests, url, destination):
    response = requests.get(
        url,
        headers={
            "Accept": "audio/*,application/octet-stream",
            "User-Agent": USER_AGENT,
        },
        stream=True,
        timeout=120,
        allow_redirects=False,
    )
    temporary = Path(str(destination) + ".download")
    try:
        if response.status_code != 200:
            raise RuntimeError(
                "Atlas Cloud audio download failed: HTTP {}".format(
                    response.status_code
                )
            )
        final = urlparse(response.url)
        if (
            final.scheme != "https"
            or not final.hostname
            or final.username
            or final.password
        ):
            raise RuntimeError("Atlas Cloud audio download redirected to an unsafe URL")
        declared = response.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > MAX_DOWNLOAD_BYTES:
            raise RuntimeError("Atlas Cloud audio exceeds the 64 MiB download limit")

        total = 0
        with temporary.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError(
                        "Atlas Cloud audio exceeds the 64 MiB download limit"
                    )
                output.write(chunk)
        os.replace(temporary, destination)
    finally:
        response.close()
        temporary.unlink(missing_ok=True)


def _speed(rate):
    match = re.match(r"([+-]?\d+)%", rate or "")
    value = 1.0 + int(match.group(1)) / 100.0 if match else 1.0
    return max(0.7, min(1.5, value))


def synthesize(chunks, config, output_file, output_format="wav"):
    """Synthesize chunks through Atlas Cloud and concatenate them as 48 kHz WAV."""
    import requests

    key = config["key"]
    voice = config.get("voice", "eve")
    language = config.get("language", "auto")
    poll_seconds = float(config.get("poll_seconds", 2.0))
    max_polls = int(config.get("max_polls", 150))
    if poll_seconds < 0 or max_polls < 1:
        raise ValueError(
            "Atlas Cloud poll interval must be non-negative and max polls positive"
        )
    out_dir = os.path.dirname(output_file) or "."
    part_files = []
    temporary_files = set()
    accumulated_duration = 0.0

    try:
        for index, text in enumerate(chunks):
            payload = {
                "model": "xai/tts-v1",
                "text": text,
                "language": language,
                "voice_id": voice,
                "codec": "mp3",
                "sample_rate": 24000,
                "bit_rate": 128000,
                "speed": _speed(config.get("speech_rate", "+5%")),
            }
            submitted = _prediction_data(
                _request_json(
                    requests,
                    "POST",
                    "{}/model/generateAudio".format(API_BASE),
                    key,
                    json=payload,
                )
            )
            prediction_id = submitted.get("id")
            if not isinstance(prediction_id, str) or not prediction_id:
                raise RuntimeError("Atlas Cloud did not return a prediction id")

            prediction = submitted
            for attempt in range(max_polls + 1):
                status = str(prediction.get("status") or "").lower()
                if status in ("completed", "succeeded"):
                    break
                if status in ("failed", "timeout", "cancelled", "canceled"):
                    raise RuntimeError(
                        "Atlas Cloud generation failed: {}".format(
                            prediction.get("error") or status
                        )
                    )
                if attempt == max_polls:
                    raise RuntimeError(
                        "Atlas Cloud generation exceeded the polling limit"
                    )
                time.sleep(poll_seconds)
                prediction = _prediction_data(
                    _request_json(
                        requests,
                        "GET",
                        "{}/model/prediction/{}".format(
                            API_BASE, quote(prediction_id, safe="")
                        ),
                        key,
                    )
                )

            mp3_file = os.path.join(
                out_dir, ".atlas_tts_part_{:04d}.mp3".format(index)
            )
            wav_file = os.path.join(
                out_dir, ".atlas_tts_part_{:04d}.wav".format(index)
            )
            temporary_files.update((mp3_file, wav_file))
            _download(requests, _output_url(prediction), Path(mp3_file))
            converted = subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_file, "-ar", "48000", "-ac", "1", wav_file],
                capture_output=True,
                text=True,
            )
            if converted.returncode != 0:
                raise RuntimeError(
                    "ffmpeg convert failed: {}".format(converted.stderr[-200:])
                )
            os.remove(mp3_file)
            temporary_files.discard(mp3_file)
            part_files.append(wav_file)

            probe = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                    "-of", "csv=p=0", wav_file,
                ],
                capture_output=True,
                text=True,
            )
            duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
            accumulated_duration += duration
            print(
                "  Part {}/{} done ({} chars, {:.1f}s)".format(
                    index + 1, len(chunks), len(text), duration
                )
            )

        if len(part_files) == 1:
            os.replace(part_files[0], output_file)
            temporary_files.discard(part_files[0])
        else:
            concat_file = os.path.join(out_dir, ".atlas_tts_concat.txt")
            concat_output = os.path.join(out_dir, ".atlas_tts_output.wav")
            temporary_files.update((concat_file, concat_output))
            with open(concat_file, "w", encoding="utf-8") as handle:
                for part_file in part_files:
                    handle.write("file '{}'\n".format(os.path.basename(part_file)))
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    concat_file, "-c", "copy", concat_output,
                ],
                capture_output=True,
                text=True,
                cwd=out_dir,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "ffmpeg concat failed: {}".format(result.stderr[-200:])
                )
            os.replace(concat_output, output_file)
            temporary_files.discard(concat_output)
        return accumulated_duration
    finally:
        for path in temporary_files:
            Path(path).unlink(missing_ok=True)
