"""MiniMax (海螺 AI) video generation provider.

API docs: https://platform.minimax.io/docs
Auth: Bearer token via MINIMAX_API_KEY env var.

Two API generations:
- video-01 (legacy): POST /v1/video_generation -> poll GET /v1/query/video_generation
  -> GET /v1/files/retrieve for the download URL. 6s, 720P.
- MiniMax-H3 (Hailuo 3.0): POST /v2/video_generation -> poll
  GET /v2/query/video_generation/{task_id} -> task.content.url. Content array
  input, 4-15s, 768P/1080P/2K, 24fps with native audio.

Host override via MINIMAX_API_BASE (host only, e.g. https://api.minimaxi.com
for China or https://api.minimax.io for international); v1/v2 paths are
appended automatically.
"""

import os

from providers.base import (
    APIError,
    ConfigError,
    GenerationRequest,
    InputError,
    VideoProvider,
    encode_image_to_data_uri,
    safe_json,
    safe_request,
    validate_media_file,
)

# MiniMax-H3 accepts 768P / 1080P / 2K. Map the CLI resolution enum onto them;
# the 2K tier is only reachable via a direct API call.
H3_RESOLUTION = {
    "360P": "768P",
    "480P": "768P",
    "540P": "768P",
    "720P": "768P",
    "1080P": "1080P",
}


class MiniMaxProvider(VideoProvider):
    name = "minimax"
    env_var = "MINIMAX_API_KEY"
    _default_api_base = "https://api.minimax.chat"

    POLL_DEADLINE = 1200

    def __init__(self) -> None:
        # Set by build_body(); routes polling to the v2 endpoint for H3 tasks.
        self._h3 = False

    @property
    def api_base(self) -> str:
        return os.environ.get("MINIMAX_API_BASE", self._default_api_base)

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.env_var, "")
        if not key:
            raise ConfigError(
                f"{self.env_var} environment variable not set.\n"
                f"Get a key at: https://platform.minimax.io\n"
                f"Set it with: export {self.env_var}='your-api-key'"
            )
        return key

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    @property
    def default_models(self) -> dict[str, str]:
        return {
            "t2v": "MiniMax-H3",
            "i2v": "MiniMax-H3",
        }

    @property
    def supported_modes(self) -> list[str]:
        return ["t2v", "i2v"]

    def check_mode(self, model: str, mode: str) -> None:
        if mode not in ("t2v", "i2v"):
            raise InputError(f"MiniMax only supports t2v and i2v, not '{mode}'.")

    def validate_params(self, req: GenerationRequest) -> None:
        import sys

        if req.model.startswith("MiniMax-H3"):
            if not 4 <= req.duration <= 15:
                print(
                    f"Warning: MiniMax-H3 supports 4-15s; requested "
                    f"{req.duration}s may fail.",
                    file=sys.stderr,
                )
            return
        if req.duration > 6:
            print(
                f"Warning: MiniMax video-01 supports up to 6s; "
                f"requested {req.duration}s may fail.",
                file=sys.stderr,
            )
        if req.resolution != "1080P":
            print(
                f"Warning: MiniMax video-01 outputs at 720P; "
                f"--resolution {req.resolution} is ignored.",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    # Media resolution
    # ------------------------------------------------------------------

    def resolve_media(self, path_or_url: str, model: str = "") -> tuple[str, bool]:
        """MiniMax accepts HTTP(S) URLs directly. Local files are uploaded
        (video-01) or inlined as data URIs (H3, which takes URLs only)."""
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url, False
        validate_media_file(path_or_url)
        if model.startswith("MiniMax-H3"):
            return encode_image_to_data_uri(path_or_url), False
        file_id = self._upload_file(path_or_url)
        return file_id, False

    def _upload_file(self, path: str) -> str:
        """Upload a local file via MiniMax's file upload API. Returns file_id."""
        fname = os.path.basename(path)
        try:
            fh = open(path, "rb")
        except OSError as e:
            raise InputError(f"cannot read {path}: {e}")
        with fh:
            rsp = safe_request(
                "POST",
                f"{self.api_base}/v1/files/upload",
                headers=self.auth_headers(),
                files={"file": (fname, fh)},
                data={"purpose": "video_generation"},
                label="MiniMax file upload",
            )
        data = safe_json(rsp, "MiniMax file upload")
        file_id = data.get("file", {}).get("file_id")
        if not file_id:
            raise APIError(f"MiniMax file upload failed: {data}")
        print(f"Uploaded {path} -> MiniMax (file_id: {file_id})")
        return file_id

    # ------------------------------------------------------------------
    # Request body builder
    # ------------------------------------------------------------------

    def build_body(
        self,
        req: GenerationRequest,
        image_url: str | None,
        last_url: str | None,
        refs: list[tuple[str | None, str]],
    ) -> dict:
        self._h3 = req.model.startswith("MiniMax-H3")
        if self._h3:
            body: dict = {
                "model": req.model,
                "content": [{"type": "text", "text": req.prompt}],
                "resolution": H3_RESOLUTION.get(req.resolution, "1080P"),
                "duration": req.duration,
                "ratio": req.ratio,
            }
            if req.mode == "i2v" and image_url:
                body["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                        "role": "first_frame",
                    }
                )
            return body

        body = {
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
        version = "v2" if self._h3 else "v1"
        data = safe_json(
            safe_request(
                "POST",
                f"{self.api_base}/{version}/video_generation",
                headers=headers,
                json=body,
                label="MiniMax submit",
            ),
            label="MiniMax submit",
        )
        task_id = data.get("task_id")
        if not task_id:
            raise APIError(f"no task_id in MiniMax response: {data}")
        return task_id

    def _poll_request(self, task_id: str):
        headers = self.auth_headers()
        if self._h3:
            return safe_request(
                "GET",
                f"{self.api_base}/v2/query/video_generation/{task_id}",
                headers=headers,
                label="MiniMax poll",
            )
        # ponytail: --task-id resume carries no API-version hint; fall back to
        # the v2 endpoint on a client error so H3 tasks can still be resumed.
        rsp = safe_request(
            "GET",
            f"{self.api_base}/v1/query/video_generation",
            params={"task_id": task_id},
            headers=headers,
            label="MiniMax poll",
        )
        if rsp.status_code in (400, 404, 405):
            rsp = safe_request(
                "GET",
                f"{self.api_base}/v2/query/video_generation/{task_id}",
                headers=headers,
                label="MiniMax poll",
            )
        return rsp

    def _parse_poll_response(self, rsp) -> tuple[str, str | None, str]:
        data = safe_json(rsp, "MiniMax poll")
        task = data.get("task")
        if task is not None:  # v2 (H3): nested {task: {status, content}}
            status = task.get("status", "UNKNOWN")
            if status == "succeeded":
                return "SUCCEEDED", task.get("content", {}).get("url", ""), ""
            if status in ("failed", "cancelled"):
                return "FAILED", None, f"status={status} {task.get('error', '')}"
            if status in ("queued", "running"):
                return "processing", None, ""
            return "UNKNOWN", None, f"status={status}"
        status = data.get("status", "UNKNOWN")
        if status == "Success":
            file_id = data.get("file_id", "")
            if file_id:
                dl_data = safe_json(
                    safe_request(
                        "GET",
                        f"{self.api_base}/v1/files/retrieve",
                        params={"file_id": file_id},
                        headers=self.auth_headers(),
                        label="MiniMax download URL",
                    ),
                    label="MiniMax download URL",
                )
                video_url = dl_data.get("file", {}).get("download_url", "")
                return "SUCCEEDED", video_url, ""
            return "SUCCEEDED", None, "no file_id"
        if status in ("Fail", "Failed", "Error", "Timeout", "Cancelled"):
            err = data.get("base_resp", {})
            return (
                "FAILED",
                None,
                f"{err.get('status_code', '')} {err.get('status_msg', '')}",
            )
        if status in ("Processing", "Queueing"):
            return "processing", None, ""
        err = data.get("base_resp", {})
        return (
            "UNKNOWN",
            None,
            f"status={status} {err.get('status_code', '')} {err.get('status_msg', '')}",
        )

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def list_models_text(self) -> str:
        lines = [
            "MiniMax 海螺 AI (t2v/i2v; Bearer token auth via MINIMAX_API_KEY):",
            "  MiniMax-H3 (t2v/i2v default; Hailuo 3.0, 4-15s, 768P/1080P, audio)",
            "  video-01 (legacy t2v/i2v; 6s, 720P)",
            "",
            "Env vars:",
            f"  {self.env_var} (required) — https://platform.minimax.io",
            "  MINIMAX_API_BASE (optional) — host only, e.g. "
            "https://api.minimaxi.com (CN) or https://api.minimax.io (intl)",
        ]
        return "\n".join(lines)
