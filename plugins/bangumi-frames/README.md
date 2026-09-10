# bangumi-frames — Bilibili Anime Frame & Character Organizer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
**English** · [中文](README_CN.md)

A skill that turns a **Bilibili video** (a bangumi episode, a UP upload, or a local file)
into organized **per-character image groups** and **scenery shots**. It downloads the
video, extracts scene-change keyframes, splits frames into scenery vs character crops with
anime-specific person detection, and then either **clusters everyone** or **pulls out one
specific character** using CCIP character-identity embeddings. Works with **Claude Code**
and any agent compatible with the [Agent Skills](https://agentskills.io) format.

> Read-only download for personal offline viewing/analysis — it uploads nothing. Anime /
> 2.5D-render art only (not live-action).

## What it does

- Takes a **Bilibili episode / video link** (or a local video file) and pulls out its best frames.
- **Recognizes the anime characters** in each frame, kept separate from the scenery shots.
- **Sort everyone** — groups every character automatically, one folder per person.
- **Pick specific characters** — give it sample pictures of someone and it pulls every shot
  that character shows up in. Point it at a folder of per-character subfolders to pull several
  named characters in one pass, each into its own folder.
- Can **erase burned-in subtitles and the corner watermark** first, if you want clean images.

## 📦 Install

```bash
# required
brew install ffmpeg            # or your platform's ffmpeg
pip install yt-dlp dghs-imgutils

# optional, only for --clean (subtitle/watermark removal)
pip install rapidocr-onnxruntime simple-lama-inpainting
```

First run downloads ~300 MB of anime detection + CCIP models from HuggingFace (cached after).
A Bilibili cookie (`cookies.txt`) is needed to download non-preview / 1080p+ episodes;
resolution order is `--cookies` > `$BILIBILI_COOKIES` > `~/bb_up/bb_cookies/www.bilibili.com_cookies.txt`.

> **Run on CPU for the CCIP step** — do not set `ONNX_MODE=CoreML` (CCIP crashes there; the
> script pops it automatically before clustering/matching). Person detection is fine on CoreML.

## 🚀 Usage

```bash
SKILL=skills/bangumi-frames/scripts/bangumi_frames.py

# Mode 1 — cluster everyone into char_NN groups
python3 $SKILL https://www.bilibili.com/video/BV15qVm68E2h --out ~/frames
python3 $SKILL ep1231575 --out ~/frames            # ep / BV id also accepted
python3 $SKILL ~/local.mp4 --out ~/frames           # local file, skips download

# Mode 2 — pull out ONE character (ref folder = ~200 crops of that character)
python3 $SKILL BV15qVm68E2h --ref ~/refs/紫灵 --ref-eps 0.04 --out ~/frames

# Mode 2, several characters at once — ref folder of per-character subfolders
#   ~/refs/凡人/{韩立,紫灵,南宫婉}/*.jpg  ->  matched/{韩立,紫灵,南宫婉}/
python3 $SKILL BV15qVm68E2h --ref ~/refs/凡人 --ref-eps 0.04 --out ~/frames

# Optional: strip burned-in subtitles + watermark before analysis
python3 $SKILL ep1231575 --clean --out ~/frames
```

## 🗂️ Output

```
<out>/<id>/                     # id = BV id / ep id / local filename
├── frames/  frames.json        # keyframes + timestamps
├── scenery/                    # frames with no detected character
├── crops/  features.npy        # character crops + cached CCIP features
├── detect.json                 # frame -> person boxes / crops
├── characters/                 # MODE 1: char_NN_crop/ + char_NN_full/ (paired), _unsorted/, _montage.png
├── matched/                    # MODE 2: 0.012_<crop>.jpg (distance-prefixed) + index.json
│                               #   (multi-character: matched/<name>/ per subfolder)
├── matched_montage.png         # MODE 2 sample montage (single-character)
└── index.json                  # MODE 1: char group -> {crop, frame, time}
```

Look at `characters/_montage.png` (mode 1) or `matched_montage.png` (mode 2) first to judge
quality, then read `index.json`.

## ⚙️ How it works

`input → download → extract → (clean) → classify → cluster | match`

Each stage is idempotent (skipped when its output exists); clustering/matching always re-runs
off the cached features. Full per-stage flags, the CPU/CoreML rule, and the threshold lore are
in the skill's reference docs:

- [`skills/bangumi-frames/references/pipeline.md`](skills/bangumi-frames/references/pipeline.md) — stages, flags, `--clean`, caching, `--redo`
- [`skills/bangumi-frames/references/modes.md`](skills/bangumi-frames/references/modes.md) — mode 1 vs mode 2, thresholds, distance bands

## 📁 Layout

```
skills/bangumi-frames/      # the skill (SKILL.md + scripts/ + references/)
```

Part of the [Agents365-ai/365-skills](https://github.com/Agents365-ai/365-skills) skills monorepo;
regression tests and CI workflows live in the standalone history, not in the plugin.

## 📝 License

[MIT](LICENSE) © Agents365-ai
