"""Unit tests for videogencn core logic — provider detection, mode detection,
ref parsing, body construction, and poll status normalization.

These tests use mocked requests so no real API keys or network calls are needed.
Run with: python -m pytest skills/videogencn/tests/ -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Allow imports from the scripts package (sibling to tests/)
_skill_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_skill_root / "scripts"))

from providers import register_providers, get_provider, detect_provider, list_providers
from providers.base import (
    GenerationRequest, pick_size, SIZE_TABLE,
    validate_media_file, InputError,
    ConfigError, APIError, TaskFailedError, TaskTimeoutError, VideoGenError,
)
from generate_video import detect_mode, parse_ref, download_video, _run


# ---------------------------------------------------------------------------
# Fixture: register providers once
# ---------------------------------------------------------------------------

def setup_module():
    register_providers()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_config_error_is_videogenerror(self):
        e = ConfigError("missing key")
        assert isinstance(e, VideoGenError)
        assert e.exit_code == 2

    def test_input_error_is_videogenerror(self):
        e = InputError("bad input")
        assert isinstance(e, VideoGenError)
        assert e.exit_code == 2

    def test_api_error_is_videogenerror(self):
        e = APIError("http fail")
        assert isinstance(e, VideoGenError)
        assert e.exit_code == 3

    def test_task_failed_is_videogenerror(self):
        e = TaskFailedError("task died")
        assert isinstance(e, VideoGenError)
        assert e.exit_code == 4

    def test_task_timeout_is_videogenerror(self):
        e = TaskTimeoutError("too long")
        assert isinstance(e, VideoGenError)
        assert e.exit_code == 5


# ---------------------------------------------------------------------------
# GenerationRequest
# ---------------------------------------------------------------------------

class TestGenerationRequest:
    def test_defaults(self):
        req = GenerationRequest(prompt="test", mode="t2v", model="wan")
        assert req.duration == 5
        assert req.resolution == "1080P"
        assert req.ratio == "16:9"
        assert req.size is None
        assert req.seed is None
        assert req.audio is False

    def test_custom_values(self):
        req = GenerationRequest(
            prompt="hello", mode="i2v", model="custom",
            duration=10, resolution="720P", ratio="9:16",
            seed=42, audio=True, camera_motion="orbit left")
        assert req.prompt == "hello"
        assert req.mode == "i2v"
        assert req.duration == 10
        assert req.resolution == "720P"
        assert req.ratio == "9:16"
        assert req.seed == 42
        assert req.audio is True
        assert req.camera_motion == "orbit left"


# ---------------------------------------------------------------------------
# SIZE_TABLE and pick_size
# ---------------------------------------------------------------------------

class TestPickSize:
    def test_standard_sizes(self):
        req = GenerationRequest(prompt="x", mode="t2v", model="x",
                                resolution="1080P", ratio="16:9")
        assert pick_size(req) == "1920*1080"

        req2 = GenerationRequest(prompt="x", mode="t2v", model="x",
                                 resolution="720P", ratio="9:16")
        assert pick_size(req2) == "720*1280"

    def test_custom_size_overrides_table(self):
        req = GenerationRequest(prompt="x", mode="t2v", model="x",
                                size="640*480", resolution="1080P", ratio="16:9")
        assert pick_size(req) == "640*480"

    def test_new_ratios(self):
        req = GenerationRequest(prompt="x", mode="t2v", model="x",
                                resolution="1080P", ratio="1:1")
        assert pick_size(req) == "1080*1080"


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

class TestModeDetection:
    def test_t2v_default(self):
        class A:
            ref = []; image = None; last_frame = None
        assert detect_mode(A()) == "t2v"

    def test_i2v_with_image(self):
        class A:
            ref = []; image = "img.png"; last_frame = None
        assert detect_mode(A()) == "i2v"

    def test_kf2v_with_both(self):
        class A:
            ref = []; image = "a.png"; last_frame = "b.png"
        assert detect_mode(A()) == "kf2v"

    def test_r2v_with_refs(self):
        class A:
            ref = ["x=img.png"]; image = None; last_frame = None
        assert detect_mode(A()) == "r2v"


# ---------------------------------------------------------------------------
# CLI validation / download helpers
# ---------------------------------------------------------------------------

class TestCliHelpers:
    def test_run_missing_prompt_raises_input_error(self):
        import pytest

        class A:
            list_models = False
            task_id = None
            prompt = None
            last_frame = None

        with pytest.raises(InputError, match="prompt is required"):
            _run(A(), ["bailian"], "table")

    def test_run_last_frame_without_image_raises_input_error(self):
        import pytest

        class A:
            list_models = False
            task_id = None
            prompt = "animate"
            last_frame = "end.png"
            image = None

        with pytest.raises(InputError, match="--last-frame requires --image"):
            _run(A(), ["bailian"], "table")

    def test_download_video_non_200_raises_api_error(self, tmp_path):
        import pytest

        mock_rsp = MagicMock()
        mock_rsp.status_code = 403
        mock_rsp.text = "expired"
        mock_rsp.content = b""

        with patch("generate_video._safe_request", return_value=mock_rsp):
            with pytest.raises(APIError, match="video download failed"):
                download_video("http://x.com/expired.mp4", tmp_path / "out.mp4")


# ---------------------------------------------------------------------------
# Ref parsing
# ---------------------------------------------------------------------------

class TestRefParsing:
    def test_plain_path(self):
        name, value = parse_ref("image.png")
        assert name is None
        assert value == "image.png"

    def test_named_ref(self):
        name, value = parse_ref("hero=hero.png")
        assert name == "hero"
        assert value == "hero.png"

    def test_url_not_parsed_as_named(self):
        # URLs with = in query params should not be parsed as named refs
        name, value = parse_ref("https://example.com/img?size=large")
        assert name is None
        assert value == "https://example.com/img?size=large"


# ---------------------------------------------------------------------------
# Provider registration and detection
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_all_four_registered(self):
        providers = list_providers()
        assert "bailian" in providers
        assert "jimeng" in providers
        assert "minimax" in providers
        assert "hunyuan" in providers

    def test_get_bailian(self):
        p = get_provider("bailian")
        assert p.name == "bailian"

    def test_get_jimeng(self):
        p = get_provider("jimeng")
        assert p.name == "jimeng"

    def test_get_case_insensitive(self):
        p = get_provider("BAILIAN")
        assert p.name == "bailian"

    def test_unknown_provider_raises(self):
        import pytest
        with pytest.raises(KeyError):
            get_provider("nonexistent")

    def test_detect_by_wan_model(self):
        p = detect_provider("wan2.7-t2v-2026-04-25")
        assert p.name == "bailian"

    def test_detect_by_doubao_model(self):
        p = detect_provider("doubao-seedance-2-0-260128")
        assert p.name == "jimeng"

    def test_detect_by_hunyuan_model(self):
        p = detect_provider("hy-video-1.5")
        assert p.name == "hunyuan"

    def test_detect_none_falls_back(self):
        p = detect_provider(None)
        assert p.name == "bailian"


# ---------------------------------------------------------------------------
# Mode / model validation
# ---------------------------------------------------------------------------

class TestModeValidation:
    def test_bailian_supports_all_four(self):
        p = get_provider("bailian")
        assert "t2v" in p.supported_modes
        assert "i2v" in p.supported_modes
        assert "kf2v" in p.supported_modes
        assert "r2v" in p.supported_modes

    def test_jimeng_supports_t2v_i2v(self):
        p = get_provider("jimeng")
        assert p.supported_modes == ["t2v", "i2v"]

    def test_bailian_valid_mode_passes(self):
        p = get_provider("bailian")
        p.check_mode("wan2.7-t2v-2026-04-25", "t2v")  # should not raise

    def test_bailian_wrong_mode_raises(self):
        import pytest
        p = get_provider("bailian")
        with pytest.raises(InputError):
            p.check_mode("wan2.7-t2v-2026-04-25", "r2v")

    def test_hunyuan_i2v_only_model(self):
        import pytest
        p = get_provider("hunyuan")
        with pytest.raises(InputError):
            p.check_mode("yt-video-fx", "t2v")


# ---------------------------------------------------------------------------
# Default models
# ---------------------------------------------------------------------------

class TestDefaultModels:
    def test_bailian_defaults(self):
        p = get_provider("bailian")
        assert p.default_models["t2v"] == "wan2.7-t2v-2026-04-25"
        assert p.default_models["i2v"] == "wan2.6-i2v-flash"

    def test_jimeng_defaults(self):
        p = get_provider("jimeng")
        assert "doubao-seedance" in p.default_models["t2v"]

    def test_minimax_defaults(self):
        p = get_provider("minimax")
        assert p.default_models["t2v"] == "video-01"

    def test_hunyuan_defaults(self):
        p = get_provider("hunyuan")
        assert p.default_models["t2v"] == "hy-video-1.5"


# ---------------------------------------------------------------------------
# Body construction (smoke tests with GenerationRequest)
# ---------------------------------------------------------------------------

class TestBodyConstruction:
    def test_bailian_t2v_body(self):
        p = get_provider("bailian")
        req = GenerationRequest(prompt="a cat", mode="t2v",
                                model="wan2.7-t2v-2026-04-25", duration=5)
        body = p.build_body(req, None, None, [])
        assert body["model"] == "wan2.7-t2v-2026-04-25"
        assert body["input"]["prompt"] == "a cat"
        assert body["parameters"]["duration"] == 5

    def test_bailian_i2v_body(self):
        p = get_provider("bailian")
        req = GenerationRequest(prompt="zoom in", mode="i2v",
                                model="wan2.6-i2v-flash")
        body = p.build_body(req, "http://example.com/img.png", None, [])
        assert body["input"]["img_url"] == "http://example.com/img.png"

    def test_jimeng_t2v_body(self):
        p = get_provider("jimeng")
        req = GenerationRequest(prompt="sunset", mode="t2v",
                                model="doubao-seedance-2-0-260128",
                                duration=10, seed=42, audio=True)
        body = p.build_body(req, None, None, [])
        assert body["duration"] == 10
        assert body["seed"] == 42
        assert body["generate_audio"] is True

    def test_jimeng_camera_motion(self):
        p = get_provider("jimeng")
        req = GenerationRequest(prompt="tracking shot", mode="t2v",
                                model="doubao-seedance-2-0-260128",
                                camera_motion="slow orbit left")
        body = p.build_body(req, None, None, [])
        assert body["camera_motion"] == "slow orbit left"

    def test_minimax_t2v_body(self):
        p = get_provider("minimax")
        req = GenerationRequest(prompt="waves", mode="t2v",
                                model="video-01", duration=6)
        body = p.build_body(req, None, None, [])
        assert body["prompt_optimizer"] is True
        assert body["duration"] == 6

    def test_minimax_no_optimizer(self):
        p = get_provider("minimax")
        req = GenerationRequest(prompt="waves", mode="t2v",
                                model="video-01",
                                no_prompt_optimizer=True)
        body = p.build_body(req, None, None, [])
        assert body["prompt_optimizer"] is False

    def test_hunyuan_t2v_body(self):
        p = get_provider("hunyuan")
        req = GenerationRequest(prompt="field", mode="t2v",
                                model="hy-video-1.5", duration=5, seed=99)
        body = p.build_body(req, None, None, [])
        assert body["duration"] == 5
        assert body["seed"] == 99

    def test_hunyuan_experimental_skips_params(self):
        p = get_provider("hunyuan")
        req = GenerationRequest(prompt="animate", mode="i2v",
                                model="yt-video-humanactor",
                                duration=10, seed=42)
        body = p.build_body(req, "http://x.com/img.png", None, [])
        assert "duration" not in body  # experimental model skips it
        assert "seed" not in body
        assert body["image"]["url"] == "http://x.com/img.png"

    def test_pixverse_r2v_refs(self):
        p = get_provider("bailian")
        req = GenerationRequest(prompt="@hero fights @monster", mode="r2v",
                                model="pixverse/pixverse-c1-r2v")
        body = p.build_body(req, None, None,
                           [("hero", "http://x.com/hero.png"),
                            ("monster", "http://x.com/monster.png")])
        media = body["input"]["media"]
        assert len(media) == 2
        assert media[0]["ref_name"] == "hero"
        assert media[1]["ref_name"] == "monster"


# ---------------------------------------------------------------------------
# Poll status normalization
# ---------------------------------------------------------------------------

class TestPollNormalization:
    def test_bailian_succeeded(self):
        p = get_provider("bailian")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "output": {"task_status": "SUCCEEDED", "video_url": "http://x.com/v.mp4"}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "SUCCEEDED"
        assert url == "http://x.com/v.mp4"

    def test_bailian_failed(self):
        p = get_provider("bailian")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "output": {"task_status": "FAILED", "code": "ERR", "message": "bad"}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "FAILED"
        assert "ERR" in err

    def test_jimeng_succeeded(self):
        p = get_provider("jimeng")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "status": "succeeded", "content": {"video_url": "http://x.com/v.mp4"}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "SUCCEEDED"

    def test_minimax_success(self):
        # The download URL call uses safe_request imported in minimax module
        p = get_provider("minimax")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "status": "Success", "file_id": "f123"}
        with patch.object(p, 'auth_headers', return_value={}):
            with patch('providers.minimax.safe_request') as mock_req:
                mock_dl = MagicMock()
                mock_dl.json.return_value = {"file": {"download_url": "http://x.com/v.mp4"}}
                mock_req.return_value = mock_dl
                status, url, err = p._parse_poll_response(mock_rsp)
                assert status == "SUCCEEDED"
                assert url == "http://x.com/v.mp4"

    def test_minimax_fail_normalized(self):
        p = get_provider("minimax")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "status": "Fail", "base_resp": {"status_code": 500, "status_msg": "error"}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "FAILED"

    def test_hunyuan_completed(self):
        p = get_provider("hunyuan")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "status": "completed", "data": {"url": "http://x.com/v.mp4"}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "SUCCEEDED"

    def test_hunyuan_completed_no_url(self):
        p = get_provider("hunyuan")
        mock_rsp = MagicMock()
        mock_rsp.json.return_value = {
            "status": "completed", "data": {}}
        status, url, err = p._parse_poll_response(mock_rsp)
        assert status == "FAILED"  # completed without URL = failed


# ---------------------------------------------------------------------------
# Media validation
# ---------------------------------------------------------------------------

class TestMediaValidation:
    def test_missing_file_raises(self):
        import pytest
        with pytest.raises(InputError, match="image not found"):
            validate_media_file("/nonexistent/path/image.png")

    def test_bad_extension_raises(self, tmp_path):
        import pytest
        bad = tmp_path / "doc.txt"
        bad.write_text("not an image")
        with pytest.raises(InputError, match="unsupported image format"):
            validate_media_file(str(bad))

    def test_valid_file_passes(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        result = validate_media_file(str(img))
        assert result.name == "photo.png"

    def test_bailian_upload_policy_missing_data_raises_api_error(self, tmp_path, monkeypatch):
        import pytest

        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        mock_rsp = MagicMock()
        mock_rsp.status_code = 401
        mock_rsp.text = '{"code":"InvalidApiKey","message":"bad key"}'
        mock_rsp.json.return_value = {"code": "InvalidApiKey", "message": "bad key"}

        p = get_provider("bailian")
        with patch("providers.bailian.safe_request", return_value=mock_rsp):
            with pytest.raises(APIError, match="Bailian upload policy failed"):
                p._upload_file("pixverse/pixverse-c1-it2v", str(img))
