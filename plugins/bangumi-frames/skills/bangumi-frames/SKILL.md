---
name: bangumi-frames
version: 0.3.0
description: Extract and organize frames from a Bilibili video (bangumi episode, UP upload, or a local file) into scenery shots and per-character image groups, using anime-specific person detection + CCIP character-identity embeddings. Two modes — cluster everyone, or pull out ONE character via a reference folder. Use when the user wants to collect, extract, or organize anime frames/screenshots by character or by scenery from a Bilibili video. Read-only download for personal viewing/analysis; uploads nothing.
license: MIT
homepage: https://github.com/Agents365-ai/bangumi-frames
compatibility: Requires ffmpeg and (for downloads) yt-dlp on PATH; Python 3.9+ with dghs-imgutils (anime person detection + CCIP). The CCIP step runs on CPU — do NOT set ONNX_MODE=CoreML (CCIP crashes there); person detection is fine on CoreML. Anime / 2.5D-render art only — not for live-action. Optional --clean (subtitle/watermark removal) needs rapidocr-onnxruntime + simple-lama-inpainting.
platforms: [macos, linux]
metadata: {"openclaw":{"requires":{"anyBins":["ffmpeg"]},"emoji":"🎬","os":["darwin","linux"],"install":[{"id":"brew-ffmpeg","kind":"brew","formula":"ffmpeg","bins":["ffmpeg"],"label":"Install ffmpeg via Homebrew","os":["darwin"]},{"id":"pip-yt-dlp","kind":"pip","package":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp (download Bilibili streams)"},{"id":"pip-imgutils","kind":"pip","package":"dghs-imgutils","label":"Install anime person detection + CCIP models"}]},"hermes":{"tags":["bilibili","anime","bangumi","frames","character","ccip","screenshot","video"],"category":"media","requires_tools":["ffmpeg","yt-dlp"],"related_skills":[]},"author":"Agents365-ai","version":"0.3.0"}
---

# bangumi-frames — Bilibili Anime Frame & Character Organizer

## Overview

Give a Bilibili video (a bangumi `ep` link, a UP-upload `BV` link/id, or a **local
video file**); it downloads → extracts scene-change keyframes → splits scenery vs
character frames → organizes the character crops. **One pass, two modes:**

- **no `--ref` (cluster mode)** — group every character crop by CCIP identity into
  `characters/char_NN/`.
- **with `--ref DIR` (one-vs-rest mode)** — given ONE character's reference folder,
  pull every crop in the video that matches it into `matched/`, filenames prefixed
  with distance (closest first) so a tight threshold yields a pure set.

Models are **anime-specific** (deepghs anime person detection + CCIP character-identity
embeddings) — they do not work on live-action footage.

## When to use / when NOT to use

- **Use** when the user wants to collect/extract/organize anime frames or screenshots
  from a Bilibili video — by character, by scenery, or to pull out one specific person.
- **Don't use** for live-action video (needs an insightface-class face stack instead),
  or for generic video editing/trimming/transcoding.

## Bundled resources

| Resource | Read it when |
|---|---|
| `references/pipeline.md` | Tuning a stage — download (`--height`/`--prefer`), extract (`--scene`/`--interval`/`--dedup`/`--skip`), `--clean` (OCR+LaMa subtitle/watermark removal), classify (`--conf`/`--min-area`); feature caching; the CPU/CoreML rule; `--redo` |
| `references/modes.md` | Choosing/tuning the two modes — mode 1 cluster (`--eps`/`--min-samples`) vs mode 2 one-vs-rest (`--ref-eps`, the distance-band histogram, the compressed-embedding threshold lore); full output layout |
| `scripts/bangumi_frames.py` | The entry point (all stages + both modes) |
| `scripts/remove_overlay.py` | Standalone subtitle/watermark removal on a frame dir or single image |

## Prerequisites

1. `ffmpeg` on PATH; `yt-dlp` on PATH for downloads (a local-file input skips download).
2. Python 3.9+, `pip install dghs-imgutils` (first run pulls ~300 MB of models from
   HuggingFace, then cached locally).
3. A Bilibili cookie (Netscape `cookies.txt`). Resolution order:
   `--cookies` > `$BILIBILI_COOKIES` > `~/bb_up/bb_cookies/www.bilibili.com_cookies.txt`.
   1080p+ / premium episodes need a cookie with membership; a preview-only download means
   the cookie lacks access to that episode. Local-file input needs no cookie.
4. **Run the CCIP step on CPU** — do not set `ONNX_MODE=CoreML` (CCIP crashes; the script
   pops it before clustering/matching). Person detection is fine on CoreML.
5. (Only for `--clean`) `pip install rapidocr-onnxruntime simple-lama-inpainting`.
6. (Only for `--engine pyscenedetect`) `pip install scenedetect`.

## Usage

```bash
SKILL=skills/bangumi-frames/scripts/bangumi_frames.py

# Mode 1 — cluster everyone into char_NN groups
python3 $SKILL https://www.bilibili.com/video/BV15qVm68E2h --out ~/frames
python3 $SKILL ep1231575 --out ~/frames           # ep / BV id also accepted
python3 $SKILL ~/local.mp4 --out ~/frames          # local file, skips download

# Mode 2 — pull out ONE character (ref folder = ~200 crops of that character)
python3 $SKILL BV15qVm68E2h --ref ~/refs/紫灵 --ref-eps 0.04 --out ~/frames

# Optional: strip burned-in subtitles + watermark before analysis
python3 $SKILL ep1231575 --clean --out ~/frames
```

Stages are idempotent (a stage is skipped when its output already exists; clustering /
matching always re-runs since the CCIP features are cached). For every flag, the per-stage
trade-offs, and the threshold lore, read the two reference files above.

**Agent-native output:** `stdout` is a single JSON envelope (`{"ok", "data", "next", "meta"}`
on success, `{"ok": false, "error"}` on failure — JSON when piped, a human summary on a TTY;
force with `--format`), `stderr` carries human progress logs, and exit codes are stable
(`0` ok · `1` runtime · `2` auth · `3` validation). Use `--dry-run` to preview the plan
without downloading, `--schema` to print the output contract. Details in `references/pipeline.md`.

## Output

```
<out>/<id>/                     # id = BV id / ep id / local filename
├── frames/  frames.json        # keyframes + timestamps
├── scenery/                    # frames with no detected character
├── crops/  features.npy        # character crops + cached CCIP features
├── detect.json                 # frame -> person boxes / crops
├── characters/                 # MODE 1: char_NN/ (+ full_* frames), _unsorted/, _montage.png
├── matched/                    # MODE 2: 0.012_<crop>.jpg (distance-prefixed) + index.json
├── matched_montage.png         # MODE 2 sample montage
└── index.json                  # MODE 1: char group -> {crop, frame, time}
```

After a run, look at `characters/_montage.png` (mode 1) or `matched_montage.png` (mode 2)
first to judge quality, then read `index.json`. See `references/modes.md` for what to
adjust when grouping/matching is off.

## Limits

- Anime / 2.5D-render art only; live-action needs a different (face-recognition) stack.
- CCIP may split one character's different forms (outfit / transform) into separate groups
  — usually fine for "group by visual appearance"; for mode 2, put each form in the ref.
- 1080p+ on Bilibili needs a membership cookie; download is for personal offline analysis
  only and uploads nothing.
