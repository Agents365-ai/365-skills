---
name: videogencn
description: Use when generating video clips with Chinese video models — text-to-video (文生视频), image-to-video (图生视频), first/last-frame and reference-to-video across 4 platforms: Bailian (Wan/PixVerse/Kling/Vidu/HappyHorse), Jimeng (doubao-seedance), MiniMax (Hailuo), Hunyuan (hy-video)
author: Agents365-ai
version: 1.0.0
created: 2026-07-05
updated: 2026-07-08
homepage: https://github.com/Agents365-ai/videogenCN
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["DASHSCOPE_API_KEY"]},"primaryEnv":"DASHSCOPE_API_KEY","emoji":"🎬"}}
---

# videogencn - Chinese Video Generation Skill

## Overview

Generate short video clips using Chinese video models across four providers — Alibaba Cloud Bailian (Wan/PixVerse/Kling/Vidu/HappyHorse), Volcengine Ark (Jimeng/即梦), MiniMax (海螺 AI), and Tencent Hunyuan (混元).

Four modes, auto-selected from inputs:

| Mode | Inputs | Default model |
|------|--------|---------------|
| t2v 文生视频 | prompt only | `wan2.7-t2v-2026-04-25` (Bailian) |
| i2v 图生视频 | prompt + `--image` | `wan2.6-i2v-flash` (Bailian) |
| kf2v 首尾帧 | prompt + `--image` + `--last-frame` | `pixverse/pixverse-c1-kf2v` (Bailian) |
| r2v 参考生视频 | prompt + `--ref` (1-7 images) | `pixverse/pixverse-c1-r2v` (Bailian) |

Video generation is **asynchronous**: submit → poll every 10s → download MP4. Result URLs expire after 24h, so the script always downloads immediately.

Local images: Wan/HappyHorse accept base64 data URIs directly; PixVerse/Kling/Vidu auto-upload to DashScope OSS (48h); Jimeng/Hunyuan use base64; MiniMax uploads via its file API.

## When to Use This Skill

- User asks to 生成视频 / 文生视频 / 图生视频 / 首尾帧 / 参考生视频
- User names a Chinese video model: 万相/Wan, 爱诗/PixVerse, 可灵/Kling, Vidu, HappyHorse, 即梦/Jimeng, 海螺/MiniMax, 混元/Hunyuan
- User needs B-roll, animated stills, character-consistent clips, or frame transitions
- User asks about model pricing, features, or wants to compare models → open `docs/models.html`

## Workflow

### Step 0: Prompt Refinement (interactive)

**Run for t2v/i2v unless skipped** (see §0.4). Claude polishes the user's prompt before generation.

#### 0.1 Analyze the raw input

| Dimension | Check |
|-----------|-------|
| **Subject** | Who/what? Appearance, action, expression |
| **Scene** | Where? Background, environment, atmosphere |
| **Lighting** | Time of day? Light quality? (golden hour, neon, soft diffused, backlit) |
| **Camera** | Shot type? (close-up, wide, aerial, tracking). Movement? (push-in, pan, orbit) |
| **Mood/Style** | Emotional tone? Visual style? (cinematic, anime, documentary, surreal) |
| **Motion** | What moves? How? Speed, direction, dynamics |
| **Temporal** | Any sequence? Beginning→middle→end? |

#### 0.2 Generate three refined variants

Present **3 variants** in a table:

```
| # | 风格方向 | 优化后提示词 | 建议参数 |
|---|---------|-------------|---------|
| 1 | [风格名]  | [完整中文提示词] | 5s / 16:9 / 1080P |
| 2 | [风格名]  | [完整中文提示词] | 8s / 16:9 / 1080P |
| 3 | [风格名]  | [完整中文提示词] | 5s / 9:16 / 1080P |
```

- **Variant 1**: 忠于原意 — preserve core idea, add cinematic detail
- **Variant 2**: 创造性发散 — different artistic interpretation
- **Variant 3**: 实用主义 — optimized for vertical short-video

**Prompt writing rules:**
- Write in Chinese; front-load subject + action (first 20 chars matter most)
- Concrete visual nouns ("金色麦田") not abstract concepts ("丰收的感觉")
- Describe motion explicitly ("缓缓推近", "随风飘动")
- Add camera/lighting cues at the end ("电影感镜头", "逆光剪影")
- Keep within 150 characters
- Wan 2.7 multi-shot: `第N个镜头[N-Ns]: 描述` format

#### 0.3 User feedback loop

| User says | Action |
|-----------|--------|
| "用第N个" / "N" | Use variant N as-is |
| "更诗意" / "更浪漫" | Regenerate with poetic tone |
| "更简洁" | Strip to essentials |
| "加动态元素" | Add more motion/action |
| "改为夜景" / "下雪" / etc | Apply scene change to all variants |
| "混合1和3" | Combine subject of 1 with style of 3 |
| "直接用" / "不改了" | Skip refinement |
| Custom feedback | Apply and regenerate |

Iterate until the user explicitly approves ("好", "可以", "用这个", "生成吧").

#### 0.4 Skip conditions

Skip refinement when user says "直接生成" / "不用优化" / "skip", the prompt is already detailed (>80 chars), or mode is kf2v/r2v.

### Step 1: Decide mode, provider, and model

- **Mode**: auto-detected from inputs (t2v / i2v / kf2v / r2v)
- **Provider**: `--provider {bailian,jimeng,minimax,hunyuan}` or auto-detect from model name
- **Model**: `--model` flag, or provider default for the mode
- **Parameters**: duration, resolution, ratio from variant suggestion or user override

### Step 2: Confirm and generate

Show the final command and confirm with the user. Run the script; it blocks until the task finishes and saves the MP4.

### Step 3: Deliver

Report output path, file size, and generation time. Save to cwd if no path given.

**Cost note**: video APIs bill per second of output. Confirm with user for long/many clips.

## Providers

### Alibaba Bailian 百炼

One API key (`DASHSCOPE_API_KEY`) covers 5 model families. Third-party models (PixVerse/Kling/Vidu/HappyHorse) are **cn region only**. Models: Wan (t2v/i2v, up to 15s), PixVerse (all 4 modes, 1-15s), Kling (t2v/i2v/kf2v + r2v on omni), Vidu (q3: 1-16s with audio; q2: 1-10s), HappyHorse (t2v/i2v, 3-15s).

### Volcengine Ark (Jimeng 即梦)

`ARK_API_KEY` via `https://ark.cn-beijing.volces.com/api/v3`. Seedance 2.0: t2v/i2v up to 15s/2K, with audio, lip-sync, and camera motion. Ratios: 16:9, 9:16, 1:1, 21:9.

### MiniMax 海螺 AI

`MINIMAX_API_KEY` via `https://api.minimax.chat`. video-01: t2v/i2v, 6s at 720P. Prompt optimizer on by default (`--no-prompt-optimizer` to disable).

### Tencent Hunyuan 混元

`HUNYUAN_API_KEY` via TokenHub. hy-video-1.5: t2v/i2v (5-10s, 720P, supports `--duration`/`--seed`). Experimental i2v-only: yt-video-2.0, yt-video-fx, yt-video-humanactor. Flags `--resolution`, `--ratio`, `--audio`, `--camera-motion` are not yet supported.

## Model Selection Guide

| Use case | Model | Provider |
|----------|-------|----------|
| Best quality t2v, multi-shot | `wan2.7-t2v-2026-04-25` | Bailian |
| Fast action / combat | `pixverse/pixverse-c1-t2v` | Bailian |
| Smart storyboard + audio | `kling/kling-v3-video-generation` | Bailian |
| Long clips up to 16s + audio | `vidu/viduq3-pro_text2video` | Bailian |
| Douyin/XHS short-video | `doubao-seedance-2-0-260128` | Jimeng |
| Smooth motion, natural physics | `video-01` | MiniMax |
| Animate an image (default) | `wan2.6-i2v-flash` | Bailian |
| Transition between two frames | `pixverse/pixverse-c1-kf2v` | Bailian |
| Character/subject consistency | `pixverse/pixverse-c1-r2v` | Bailian |
| Cheap drafts | `wanx2.1-t2v-turbo`, `happyhorse-1.0-t2v` | Bailian |
| Chinese t2v/i2v on Tencent | `hy-video-1.5` | Hunyuan |
| Portrait animation (experimental) | `yt-video-humanactor` | Hunyuan |

Run `python scripts/generate_video.py --list-models` for the full model catalog.

### Model Comparison Page

When the user wants to compare models, browse pricing, filter by features, or pick a model:

**Open `docs/models.html` in the browser.** It's a self-contained static page — no server needed. Use `open` (macOS) or `xdg-open` (Linux):

```bash
open docs/models.html
```

The page supports filtering by provider, mode (文生/图生/首尾帧/参考生), and features (audio/camera/multi-shot), with pricing and capability comparison across all 22 models.

## Usage

```bash
# Text-to-Video (Bailian default)
python scripts/generate_video.py "一只柴犬在樱花树下奔跑,花瓣随风飘落,电影感镜头" shiba.mp4 \
  --duration 5 --resolution 1080P --ratio 16:9

# Image-to-Video
python scripts/generate_video.py "镜头缓缓推近,人物微笑" out.mp4 --image portrait.png

# First+Last Frame (kf2v)
python scripts/generate_video.py "花苞缓缓绽放成盛开的牡丹" bloom.mp4 \
  --image bud.png --last-frame bloom.png

# Reference-to-Video (r2v)
python scripts/generate_video.py "@girl 在 @cafe 里弹吉他" out.mp4 \
  --ref girl=girl.png --ref cafe=cafe.jpg

# Other providers
python scripts/generate_video.py "城市日落延时摄影" sunset.mp4 --provider jimeng --duration 10
python scripts/generate_video.py "海浪拍打礁石" ocean.mp4 --provider minimax --duration 6
python scripts/generate_video.py "金黄色的麦田在秋风中起伏" field.mp4 --provider hunyuan --duration 5

# Dry-run: preview request + cost estimate without submitting
python scripts/generate_video.py "一只柴犬在樱花树下奔跑" --dry-run

# Schema introspection (for agents)
python scripts/generate_video.py schema providers   # list all providers
python scripts/generate_video.py schema bailian     # list bailian models with capabilities

# JSON output (auto-detected when stdout is not a TTY; force with --format)
python scripts/generate_video.py --list-models --format json
python scripts/generate_video.py "海边的日落" out.mp4 --format json --provider jimeng

# Resume a task
python scripts/generate_video.py --task-id <task-id> out.mp4

# List all models
python scripts/generate_video.py --list-models
```

## Options

| Flag | Meaning | Default |
|------|---------|---------|
| `--provider` | `bailian` / `jimeng` / `minimax` / `hunyuan` | auto-detect |
| `-m/--model` | model name | auto by mode |
| `-i/--image` | first-frame image (path/URL) → i2v | — |
| `--last-frame` | last-frame image → kf2v (requires `-i`) | — |
| `--ref` | reference image `name=path_or_url`, repeatable → r2v | — |
| `-d/--duration` | seconds | 5 |
| `-r/--resolution` | 360P/480P/540P/720P/1080P | 1080P |
| `--ratio` | 16:9 / 9:16 / 1:1 / 3:4 / 4:3 / 21:9 | 16:9 |
| `-s/--size` | exact `W*H` for size-based models | from resolution+ratio |
| `-n/--negative` | negative prompt (Wan only) | — |
| `--no-prompt-extend` | disable prompt rewriting (Wan only) | extend on |
| `--no-prompt-optimizer` | disable built-in prompt optimizer (MiniMax only) | optimizer on |
| `--audio` | enable audio on PixVerse/Kling/Vidu/Jimeng | off |
| `--no-audio` | silent output on Wan audio models | audio on |
| `--camera-motion` | camera motion (Jimeng Seedance 2.0 only) | — |
| `--seed` | reproducibility | random |
| `--task-id` | resume polling an existing task | — |
| `--dry-run` | preview request body + cost estimate, no submit | — |
| `--format` | `json` or `table` (default: table in TTY, json otherwise) | auto |
| `--list-models` | list models and exit | — |
| `schema <resource>` | introspection: `providers` or a provider id | — |

## Requirements

```bash
pip install requests
```

## Environment Variables

| Variable | Required | Provider | Purpose |
|----------|----------|----------|---------|
| `DASHSCOPE_API_KEY` | yes (Bailian) | Bailian | https://bailian.console.aliyun.com/ |
| `DASHSCOPE_API_BASE` | no | Bailian | `cn` (default) / `sg` / `us` |
| `DASHSCOPE_VIDEO_MODEL` | no | Bailian | default model override |
| `ARK_API_KEY` | yes (Jimeng) | Jimeng | https://console.volcengine.com/ark/ |
| `MINIMAX_API_KEY` | yes (MiniMax) | MiniMax | https://platform.minimax.io |
| `HUNYUAN_API_KEY` | yes (Hunyuan) | Hunyuan | https://console.cloud.tencent.com/hunyuan |

Third-party Bailian models are **cn region only**.
