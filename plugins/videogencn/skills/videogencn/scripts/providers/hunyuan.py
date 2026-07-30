"""Tencent Hunyuan (混元) video generation provider via TokenHub API.

Auth: Bearer token via HUNYUAN_API_KEY env var.
API docs: https://cloud.tencent.com/document/product/1823/130081
Flow: POST /v1/api/video/submit -> poll POST /v1/api/video/query -> download.

Models:
  Fully supported (t2v/i2v): hy-video-1.5
  Experimental (i2v only, limited param support): yt-video-2.0, yt-video-fx, yt-video-humanactor
"""

import os
import sys
from typing import Optional

from providers.base import (VideoProvider, GenerationRequest,
                            safe_json, safe_request,
                            encode_image_to_data_uri,
                            ConfigError, InputError, APIError)

# Models with full parameter support
FULLY_SUPPORTED = frozenset({"hy-video-1.5"})
# Models that only support i2v mode
I2V_ONLY = frozenset({"yt-video-2.0", "yt-video-fx", "yt-video-humanactor"})


class HunyuanProvider(VideoProvider):
    name = "hunyuan"
    env_var = "HUNYUAN_API_KEY"
    _default_api_base = "https://tokenhub.tencentmaas.com/v1/api/video"

    POLL_DEADLINE = 1800

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.env_var, "")
        if not key:
            raise ConfigError(
                f"{self.env_var} environment variable not set.\n"
                f"Get a key at: https://console.cloud.tencent.com/hunyuan\n"
                f"Set it with: export {self.env_var}='your-api-key'")
        return key

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    @property
    def default_models(self) -> dict[str, str]:
        return {
            "t2v": "hy-video-1.5",
            "i2v": "hy-video-1.5",
        }

    @property
    def supported_modes(self) -> list[str]:
        return ["t2v", "i2v"]

    def check_mode(self, model: str, mode: str) -> None:
        if mode not in ("t2v", "i2v"):
            raise InputError(
                f"Hunyuan only supports t2v and i2v, not '{mode}'.")
        if model in I2V_ONLY and mode != "i2v":
            raise InputError(
                f"model '{model}' only supports i2v mode, not '{mode}'.")

    def validate_params(self, req: GenerationRequest) -> None:
        unsupported = []
        if req.model not in FULLY_SUPPORTED:
            unsupported.extend(["--duration", "--seed"])
        if req.resolution != "1080P":
            unsupported.append("--resolution")
        if req.ratio != "16:9":
            unsupported.append("--ratio")
        if req.audio:
            unsupported.append("--audio")
        if req.camera_motion:
            unsupported.append("--camera-motion")
        if unsupported:
            flags = ", ".join(sorted(set(unsupported)))
            print(f"Warning: Hunyuan ignores these flags: {flags}",
                  file=sys.stderr)

    # ------------------------------------------------------------------
    # Media resolution
    # ------------------------------------------------------------------

    def resolve_media(self, path_or_url: str, model: str = "") -> tuple[str, bool]:
        """TokenHub accepts HTTP(S) URLs. Local files encoded as base64 data URIs."""
        if path_or_url.startswith(("http://", "https://", "data:")):
            return path_or_url, False
        return encode_image_to_data_uri(path_or_url), False

    # ------------------------------------------------------------------
    # Request body builder
    # ------------------------------------------------------------------

    def build_body(self, req: GenerationRequest,
                   image_url: Optional[str], last_url: Optional[str],
                   refs: list[tuple[Optional[str], str]]) -> dict:
        body: dict = {
            "model": req.model,
            "prompt": req.prompt,
        }

        if req.model in FULLY_SUPPORTED:
            body["duration"] = req.duration
            if req.seed is not None:
                body["seed"] = req.seed

        if req.mode == "i2v" and image_url:
            body["image"] = {"url": image_url}

        return body

    # ------------------------------------------------------------------
    # Async lifecycle
    # ------------------------------------------------------------------

    def submit(self, body: dict, oss_used: bool = False) -> str:
        headers = {"Content-Type": "application/json", **self.auth_headers()}
        data = safe_json(
            safe_request("POST", f"{self.api_base}/submit",
                        headers=headers, json=body, label="Hunyuan submit"),
            label="Hunyuan submit")
        task_id = data.get("id")
        if not task_id:
            raise APIError(f"no task id in Hunyuan response: {data}")
        return task_id

    def _poll_request(self, task_id: str):
        """TokenHub uses POST for queries (not GET)."""
        headers = {"Content-Type": "application/json", **self.auth_headers()}
        return safe_request("POST", f"{self.api_base}/query",
                           headers=headers, json={"id": task_id},
                           label="Hunyuan poll")

    def _parse_poll_response(self, rsp) -> tuple[str, Optional[str], str]:
        """TokenHub returns: {status, progress, data: {url}}."""
        data = safe_json(rsp, "Hunyuan poll")
        status = data.get("status", "unknown")

        if status == "completed":
            video_url = data.get("data", {}).get("url", "")
            if video_url:
                return "SUCCEEDED", video_url, ""
            return "FAILED", None, "task completed but no video_url in response"

        if status in ("failed", "cancelled", "error"):
            return "FAILED", None, str(data)

        progress = data.get("progress", "")
        label = f"{status}" + (f" ({progress}%)" if progress else "")
        return label, None, ""

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def list_models_text(self) -> str:
        lines = [
            "Hunyuan 腾讯混元 (t2v/i2v; TokenHub Bearer token via HUNYUAN_API_KEY):",
            "  hy-video-1.5 (t2v/i2v default; 720p; 5-10s; full parameter support)",
            "",
            "Experimental / limited support (i2v only; basic prompt+image only):",
            "  yt-video-2.0 (i2v general; YouTu)",
            "  yt-video-fx (video effects from template)",
            "  yt-video-humanactor (portrait animation/driving)",
            "",
            "Env vars:",
            "  HUNYUAN_API_KEY (required) — https://console.cloud.tencent.com/hunyuan",
            "",
            "Note: --duration and --seed are supported for hy-video-1.5 only.",
            "  --resolution, --ratio, --audio, and --camera-motion are not yet available.",
        ]
        return "\n".join(lines)
