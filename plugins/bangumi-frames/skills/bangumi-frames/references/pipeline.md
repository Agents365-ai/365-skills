# Pipeline & stages

The whole run is `python3 scripts/bangumi_frames.py <input> [flags]`. Each stage is
idempotent: it is skipped when its output already exists, so re-running only does the
missing work. Clustering / matching always re-runs because the CCIP features are cached.

| Stage | What it does | Key flags |
|---|---|---|
| **input** | Resolves the positional arg: a **local video file** → used directly (download skipped, work-dir id = filename); otherwise a bilibili URL / `BVxxxx` / `epNNN` → resolved to a URL + downloaded | — |
| **download** | `yt-dlp` pulls the video-only stream into `<out>/<id>/video.*` | `--height 2160` (cap; lower e.g. `720` is faster/smaller); `--prefer size` (smallest = HEVC, ~half the bytes) / `bitrate` (sharpest AVC); `--cookies PATH` |
| **extract** | scene-cut keyframes (engine-selectable) + perceptual-hash dedup → `frames/` + `frames.json` (frame→seconds) | `--engine ffmpeg\|pyscenedetect`; `--scene 0.3` (ffmpeg, smaller = more frames); `--pyscene-threshold 27` (pyscenedetect); `--interval N` (ffmpeg: also keep a frame every N s); `--dedup 6` (hamming distance below which consecutive frames are dropped; 0 = keep all); `--skip 80-170,1300-1390` (exclude time ranges, e.g. OP/ED) |
| **clean** *(optional)* | Removes burned-in subtitles + the bilibili corner watermark in place before classify | see below |
| **classify** | Anime person detection: no person → `scenery/`; person(s) → padded crop(s) → `crops/`; writes `detect.json` | `--conf 0.45` (min detection score); `--min-area 0.015` (min box area as fraction of frame — filters tiny background figures) |
| **cluster / match** | CCIP identity embeddings (cached in `features.npy`) → mode 1 `characters/` or mode 2 `matched/` | see `references/modes.md` |

## Keyframe engines (`--engine`)

Both engines feed the **same** perceptual-hash dedup + downstream stages, so they are a
clean A/B — only the frame *selection* differs. Switching engines re-extracts and
invalidates the cached `detect.json` / `features.npy` automatically.

- **`ffmpeg`** (default) — `select='gt(scene,T)'` on ffmpeg's built-in 0–1 `scene` metric
  (`--scene`, default 0.3). Fast, zero extra deps, supports `--interval` fixed-interval
  top-up. The `scene` score is crude on fades/dissolves, so the threshold is finicky.
- **`pyscenedetect`** — PySceneDetect `ContentDetector` (`--pyscene-threshold` on its ~0–100
  scale, default 27); one mid-scene frame is grabbed per detected scene via OpenCV. More
  robust on gradual transitions and typically denser at default settings. Needs
  `pip install scenedetect`. (`--scene` / `--interval` are ffmpeg-only; `--skip` applies to
  both — pyscenedetect drops scenes whose midpoint falls in a skip range.)

For an A/B, run the same video into two `--out` dirs (or the same dir twice — the second
engine re-extracts) and compare `data.frames` / `data.crops` plus the montages. Example
(17 s preview clip): ffmpeg @ `--scene 0.4` → 28 frames / 12 crops; pyscenedetect @ default
27 → 76 frames / 38 crops (denser recall, enough to form a character group the sparser
ffmpeg set missed). The thresholds are on different scales, so tune each engine on its own.

## `--clean` (subtitle / watermark removal)

Runs after extract, before classify, editing `frames/` in place so every downstream crop
is clean. Subtitles are located with **RapidOCR** (robust to low-contrast white-on-light
text that pixel heuristics miss), restricted to a bottom band so dialogue painted into the
scene is left alone; the semi-transparent bilibili logo is invisible to OCR so a fixed
top-right corner box is masked directly; holes are filled by **LaMa** (reconstructs
clothing lines / colour edges instead of the smear `cv2.inpaint` leaves).

- Flags: `--clean` to enable; `--clean-band 0.22` (bottom fraction scanned for subtitles);
  `--clean-conf 0.6` (min OCR confidence); `--clean-no-watermark` (subtitles only, keep logo).
- Idempotent: a `.frames.clean.sig` marker over the (params, frame-set) pair skips frames
  already cleaned; `--redo extract` (or any re-extraction) wipes `frames/` and invalidates it.
- When frames are actually modified, `detect.json` + `features.npy` are deleted so classify
  and the CCIP step re-run on the cleaned frames.
- Needs `pip install rapidocr-onnxruntime simple-lama-inpainting`. LaMa weights (~196 MB)
  download once from GitHub releases; it uses Apple MPS / CUDA when available (~2 s/frame),
  else CPU (~50 s/frame). Note `simple-lama-inpainting` pins pillow to 9.5.0 (no effect on
  the imgutils path in practice).
- Standalone: `python3 scripts/remove_overlay.py <frame-dir-or-image> --out-dir <dir> [--debug]`.

## Feature cache, CPU/CoreML, redo

- **`features.npy`** caches the per-crop 768-dim CCIP features (row order = sorted crop
  filenames). Re-running with a different `--eps` / `--ref-eps` is therefore seconds —
  tune thresholds freely without re-embedding.
- **CCIP must run on CPU.** The model crashes under CoreML (only part of its graph maps;
  the partial path aborts on a signal). The script does `os.environ.pop("ONNX_MODE", None)`
  before clustering/matching, so even with `ONNX_MODE=CoreML` set for fast detection, the
  CCIP step falls back to CPU. Person detection itself is fine on CoreML.
- **`--redo extract`** invalidates `frames.json` + the clean marker + `detect.json` +
  `features.npy` (re-extract everything). **`--redo classify`** invalidates `detect.json` +
  `features.npy` (re-detect + re-embed, keep frames).

## Output contract (agent-native)

The CLI follows the `agent-native-design` conventions, so an agent can drive it without
scraping prose:

- **stdout** is a single JSON envelope — `{"ok": true, "data": {...}, "next": [...],
  "meta": {"schema_version", "tool", "elapsed_ms"}}` on success, `{"ok": false,
  "error": {"code", "message", "retryable"}, "meta": {...}}` on failure. `data` carries the
  run stats (frames/scenery/crops + the mode-specific block — see `modes.md`).
- **stderr** carries the human-readable per-stage progress logs (liveness during the
  minutes-long download/embed), never polluting the stdout envelope.
- **Format auto-detection:** JSON when stdout is not a TTY (an agent/pipe), a compact human
  summary when it is. Override with `--format json|table`.
- **Exit codes:** `0` ok · `1` runtime (download/extract/model failure) · `2` auth ·
  `3` validation (unresolvable input, empty `--ref`, non-positive `--eps`/`--ref-eps`).
- **`--dry-run`** prints the resolved plan (input kind, work dir, mode, output path,
  whether it will download) and exits without downloading or running models — inputs are
  still validated, so it doubles as a cheap pre-flight.
- **`--schema`** prints the envelope/`data` schema + exit-code map and exits.
- Inputs are validated once at the entry point; `--cookies` / `$BILIBILI_COOKIES` is the
  trust boundary for auth (the agent consumes credentials, it does not fetch them).
