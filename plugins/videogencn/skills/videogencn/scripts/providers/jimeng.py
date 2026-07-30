"""Jimeng (即梦) video generation provider via Volcengine Ark API.

Auth: Bearer token via ARK_API_KEY env var.
API docs: https://www.volcengine.com/docs/82379 (Ark Content Generation)
Flow: POST /api/v3/contents/generations/tasks -> poll GET .../tasks/{id} -> download.
"""

import os
from typing import Optional

from providers.base import (VideoProvider, GenerationRequest,
                            safe_json, safe_request,
                            encode_image_to_data_uri,
                            ConfigError, InputError, APIError)


class JimengProvider(VideoProvider):
    name = "jimeng"
    env_var = "ARK_API_KEY"
    _default_api_base = "https://ark.cn-beijing.volces.com/api/v3"

    POLL_DEADLINE = 1800

    @property
    def api_key(self) -> str:
        for var in ("ARK_API_KEY", "VOLCENGINE_ACCESS_KEY"):
            key = os.environ.get(var, "")
            if key:
                return key
        raise ConfigError(
            "ARK_API_KEY environment variable not set.\n"
            "Set it with: export ARK_API_KEY='your-api-key'\n"
            "Get a key at: https://console.volcengine.com/ark/")

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    @property
    def default_models(self) -> dict[str, str]:
        return {
            "t2v": "doubao-seedance-2-0-260128",
            "i2v": "doubao-seedance-2-0-260128",
        }

    @property
    def supported_modes(self) -> list[str]:
        return ["t2v", "i2v"]

    def check_mode(self, model: str, mode: str) -> None:
        if mode not in ("t2v", "i2v"):
            raise InputError(
                f"Jimeng only supports t2v and i2v, not '{mode}'.")

    # ------------------------------------------------------------------
    # Media resolution
    # ------------------------------------------------------------------

    def resolve_media(self, path_or_url: str, model: str = "") -> tuple[str, bool]:
        """Jimeng Ark API accepts HTTP(S) URLs or base64 data URIs for images."""
        if path_or_url.startswith(("http://", "https://", "data:")):
            return path_or_url, False
        return encode_image_to_data_uri(path_or_url), False

    # ------------------------------------------------------------------
    # Request body builder
    # ------------------------------------------------------------------

    def build_body(self, req: GenerationRequest,
                   image_url: Optional[str], last_url: Optional[str],
                   refs: list[tuple[Optional[str], str]]) -> dict:
        content: list[dict] = []
        if req.mode == "i2v" and image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": "first_frame",
            })
        content.append({"type": "text", "text": req.prompt})

        ratio = "adaptive" if (req.mode == "i2v" and image_url) else req.ratio

        body: dict = {
            "model": req.model,
            "content": content,
            "duration": req.duration,
            "resolution": req.resolution.lower().rstrip("p") + "p",
            "ratio": ratio,
            "watermark": False,
        }

        if req.seed is not None:
            body["seed"] = req.seed
        if req.audio:
            body["generate_audio"] = True
        if req.camera_motion:
            body["camera_motion"] = req.camera_motion

        return body

    # ------------------------------------------------------------------
    # Async lifecycle
    # ------------------------------------------------------------------

    def submit(self, body: dict, oss_used: bool = False) -> str:
        headers = {"Content-Type": "application/json", **self.auth_headers()}
        data = safe_json(
            safe_request("POST", f"{self.api_base}/contents/generations/tasks",
                        headers=headers, json=body, label="Jimeng submit"),
            label="Jimeng submit")
        task_id = data.get("id")
        if not task_id:
            raise APIError(f"no task id in Jimeng response: {data}")
        return task_id

    def _poll_request(self, task_id: str):
        headers = self.auth_headers()
        return safe_request("GET",
            f"{self.api_base}/contents/generations/tasks/{task_id}",
            headers=headers, label="Jimeng poll")

    def _parse_poll_response(self, rsp) -> tuple[str, Optional[str], str]:
        """Ark API returns: {id, status, content: {video_url}, ...}"""
        data = safe_json(rsp, "Jimeng poll")
        status = data.get("status", "unknown")
        if status == "succeeded":
            video_url = data.get("content", {}).get("video_url", "")
            return "SUCCEEDED", video_url, ""
        if status in ("failed", "expired", "cancelled"):
            err = data.get("error", {}).get("message", str(data))
            return "FAILED", None, err
        return status, None, ""

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def list_models_text(self) -> str:
        lines = [
            "Jimeng 即梦 / Seedance (t2v/i2v; Volcengine Ark Bearer token auth):",
            "  doubao-seedance-2-0-260128 (t2v/i2v default; up to 15s, 2K, audio)",
            "  doubao-seedance-2-0-fast-260128 (fast variant)",
            "  doubao-seedance-1-5-pro-251215 (1.5 Pro; audio, smart duration)",
            "  doubao-seedance-1-0-pro (1.0 standard)",
            "",
            "Env vars:",
            "  ARK_API_KEY (required) — https://console.volcengine.com/ark/",
            "",
            "Features: t2v/i2v, native audio, up to 15s, 1080p/2K, lip-sync, camera control",
        ]
        return "\n".join(lines)
