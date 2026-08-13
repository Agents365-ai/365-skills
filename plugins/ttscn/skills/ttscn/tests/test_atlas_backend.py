"""Offline contract tests for the Atlas Cloud TTS backend."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from backends import BACKENDS, _build_config, atlas, resolve_voice  # noqa: E402


class FakeResponse:
    def __init__(self, *, body=None, content=b"", url="https://cdn.example/audio.mp3"):
        self.status_code = 200
        self._body = body
        self._content = content
        self.url = url
        self.headers = {"Content-Length": str(len(content))}
        self.text = ""
        self.closed = False

    def json(self):
        return self._body

    def iter_content(self, chunk_size):
        del chunk_size
        yield self._content

    def close(self):
        self.closed = True


def test_speed_is_clamped_to_model_range():
    assert atlas._speed("-90%") == 0.7
    assert atlas._speed("+25%") == 1.25
    assert atlas._speed("+200%") == 1.5


def test_registry_and_defaults(monkeypatch):
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
    assert BACKENDS["atlas"]["env"] == ["ATLASCLOUD_API_KEY"]
    assert resolve_voice("atlas") == ("eve", "default")
    assert _build_config("atlas") == {
        "voice": "eve",
        "voice_source": "default",
        "key": "test-key",
        "language": "auto",
        "poll_seconds": 2.0,
        "max_polls": 150,
    }


@pytest.mark.parametrize(
    "value",
    [
        "http://cdn.example/audio.mp3",
        "https://user:password@cdn.example/audio.mp3",
        "https://127.0.0.1/audio.mp3",
        "https://metadata.local/audio.mp3",
        "not-a-url",
    ],
)
def test_output_url_rejects_unsafe_values(value):
    with pytest.raises(RuntimeError, match="unsafe audio URL"):
        atlas._output_url({"outputs": [value]})


def test_synthesize_submits_once_per_chunk_and_downloads_without_credentials(
    monkeypatch, tmp_path
):
    import requests

    api_calls = []
    download_calls = []
    responses = []

    def fake_request(method, url, headers, timeout, **kwargs):
        api_calls.append((method, url, headers, timeout, kwargs))
        if method == "POST":
            response = FakeResponse(
                body={"data": {"id": "prediction-1", "status": "starting"}}
            )
        else:
            response = FakeResponse(
                body={
                    "data": {
                        "id": "prediction-1",
                        "status": "completed",
                        "outputs": ["https://cdn.example/audio.mp3"],
                    }
                }
            )
        responses.append(response)
        return response

    def fake_get(url, headers, stream, timeout, allow_redirects):
        download_calls.append((url, headers, stream, timeout, allow_redirects))
        response = FakeResponse(content=b"fake-mp3")
        responses.append(response)
        return response

    def fake_run(args, **kwargs):
        del kwargs
        if args[0] == "ffmpeg":
            Path(args[-1]).write_bytes(b"fake-wav")
            return SimpleNamespace(returncode=0, stderr="", stdout="")
        if args[0] == "ffprobe":
            return SimpleNamespace(returncode=0, stderr="", stdout="1.25\n")
        raise AssertionError("unexpected command: {}".format(args))

    monkeypatch.setattr(requests, "request", fake_request)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(atlas.subprocess, "run", fake_run)
    monkeypatch.setattr(atlas.time, "sleep", lambda _seconds: None)

    output = tmp_path / "atlas.wav"
    duration = atlas.synthesize(
        ["你好，Atlas Cloud。", "第二个分块。"],
        {
            "key": "test-key",
            "voice": "eve",
            "language": "auto",
            "speech_rate": "+5%",
            "poll_seconds": 0,
            "max_polls": 2,
        },
        str(output),
    )

    assert duration == 2.5
    assert output.read_bytes() == b"fake-wav"
    assert [call[0] for call in api_calls] == ["POST", "GET", "POST", "GET"]
    assert api_calls[0][4]["json"]["model"] == "xai/tts-v1"
    assert all(call[2]["Authorization"] == "Bearer test-key" for call in api_calls)
    assert len(download_calls) == 2
    assert all("Authorization" not in call[1] for call in download_calls)
    assert all(call[4] is False for call in download_calls)
    assert all(response.closed for response in responses)
    assert not list(tmp_path.glob(".atlas_tts_*"))
