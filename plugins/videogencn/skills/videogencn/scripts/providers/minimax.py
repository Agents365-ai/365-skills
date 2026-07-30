"""MiniMax (海螺 AI) video generation provider.

API docs: https://platform.minimax.io/docs
Auth: Bearer token via MINIMAX_API_KEY env var.
Flow: POST /video_generation -> poll GET /query/video_generation
      -> GET /files/retrieve for download URL.
"""

import os
from typing import Optional

from providers.base import (VideoProvider, GenerationRequest,
                            safe_json, safe_request, validate_media_file,
                            ConfigError, InputError, APIError)


class MiniMaxProvider(VideoProvider):
    name = "minimax"
    env_var = "MINIMAX_API_KEY"
    _default_api_base = "https://api.minimax.chat/v1"

    POLL_DEADLINE = 1200

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.env_var, "")
        if not key:
            raise ConfigError(
                f"{self.env_var} environment variable not set.\n"
                f"Get a key at: https://platform.minimax.io\n"
                f"Set it with: export {self.env_var}='your-api-key'")
        return key

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    @property
    def default_models(self) -> dict[str, str]:
        return {
            "t2v": "video-01",
            "i2v": "video-01",
        }

    @property
    def supported_modes(self) -> list[str]:
        return ["t2v", "i2v"]

    def check_mode(self, model: str, mode: str) -> None:
        if mode not in ("t2v", "i2v"):
            raise InputError(
                f"MiniMax only supports t2v and i2v, not '{mode}'.")

    def validate_params(self, req: GenerationRequest) -> None:
        import sys
        if req.duration > 6:
            print(f"Warning: MiniMax video-01 supports up to 6s; "
                  f"requested {req.duration}s may fail.", file=sys.stderr)
        if req.resolution != "1080P":
            print(f"Warning: MiniMax video-01 outputs at 720P; "
                  f"--resolution {req.resolution} is ignored.", file=sys.stderr)

    # ------------------------------------------------------------------
    # Media resolution
    # ------------------------------------------------------------------

    def resolve_media(self, path_or_url: str, model: str = "") -> tuple[str, bool]:
        """MiniMax accepts HTTP(S) URLs directly. Local files are uploaded."""
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url, False
        validate_media_file(path_or_url)
        file_id = self._upload_file(path_or_url)
        return file_id, False

    def _upload_file(self, path: str) -> str:
        """Upload a local file via MiniMax's file upload API. Returns file_id."""
        fname = os.path.basename(path)
        with open(path, "rb") as f:
            rsp = safe_request("POST", f"{self.api_base}/files/upload",
                              headers=self.auth_headers(),
                              files={"file": (fname, f)},
                              data={"purpose": "video_generation"},
                              label="MiniMax file upload")
        data = safe_json(rsp, "MiniMax file upload")
        file_id = data.get("file", {}).get("file_id")
        if not file_id:
            raise APIError(f"MiniMax file upload failed: {data}")
        print(f"Uploaded {path} -> MiniMax (file_id: {file_id})")
        return file_id

    # ------------------------------------------------------------------
    # Request body builder
    # ------------------------------------------------------------------

    def build_body(self, req: GenerationRequest,
                   image_url: Optional[str], last_url: Optional[str],
                   refs: list[tuple[Optional[str], str]]) -> dict:
        body: dict = {
            "model": req.model,
            "prompt": req.prompt,
            "duration": req.duration,
            "prompt_optimizer": not req.no_prompt_optimizer,
        }

        if req.mode == "i2v" and image_url:
            if image_url.startswith(("http://", "https://")):
                body["first_frame_image"] = image_url
            else:
                body["first_frame_image"] = f"file_id:{image_url}"

        return body

    # ------------------------------------------------------------------
    # Async lifecycle
    # ------------------------------------------------------------------

    def submit(self, body: dict, oss_used: bool = False) -> str:
        headers = {"Content-Type": "application/json", **self.auth_headers()}
        data = safe_json(
            safe_request("POST", f"{self.api_base}/video_generation",
                        headers=headers, json=body, label="MiniMax submit"),
            label="MiniMax submit")
        task_id = data.get("task_id")
        if not task_id:
            raise APIError(f"no task_id in MiniMax response: {data}")
        return task_id

    def _poll_request(self, task_id: str):
        headers = self.auth_headers()
        return safe_request("GET",
            f"{self.api_base}/query/video_generation",
            params={"task_id": task_id},
            headers=headers, label="MiniMax poll")

    def _parse_poll_response(self, rsp) -> tuple[str, Optional[str], str]:
        data = safe_json(rsp, "MiniMax poll")
        status = data.get("status", "UNKNOWN")
        if status == "Success":
            file_id = data.get("file_id", "")
            if file_id:
                dl_data = safe_json(
                    safe_request("GET", f"{self.api_base}/files/retrieve",
                                params={"file_id": file_id},
                                headers=self.auth_headers(),
                                label="MiniMax download URL"),
                    label="MiniMax download URL")
                video_url = dl_data.get("file", {}).get("download_url", "")
                return "SUCCEEDED", video_url, ""
            return "SUCCEEDED", None, "no file_id"
        if status in ("Fail", "Failed", "Error", "Timeout", "Cancelled"):
            err = data.get("base_resp", {})
            return "FAILED", None, f"{err.get('status_code', '')} {err.get('status_msg', '')}"
        if status in ("Processing", "Queueing"):
            return "processing", None, ""
        err = data.get("base_resp", {})
        return "UNKNOWN", None, f"status={status} {err.get('status_code', '')} {err.get('status_msg', '')}"

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def list_models_text(self) -> str:
        lines = [
            "MiniMax 海螺 AI (t2v/i2v; Bearer token auth via MINIMAX_API_KEY):",
            "  video-01 (t2v/i2v default; 6s, 720P)",
            "",
            "Env vars:",
            f"  {self.env_var} (required) — https://platform.minimax.io",
        ]
        return "\n".join(lines)
