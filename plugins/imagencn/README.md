# imagencn — AI Image Generation with Chinese Text Excellence

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-6C3C97)](https://claude.ai/code)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-orange)](https://openclaw.ai)
[![SkillsMP](https://img.shields.io/badge/SkillsMP-indexed-blue)](https://skillsmp.com)

[中文文档](README_CN.md)

**imagencn — Image Generation, Cloud-Native: one CLI, every image cloud.** The project started with China-friendly clouds and now covers international providers as well.

A Claude Code / OpenClaw skill for AI image generation using Alibaba Cloud Bailian, ByteDance Volcano Ark, Tencent Hunyuan, Zhipu BigModel, StepFun, Google Gemini, Grok (xAI), OpenAI, and Black Forest Labs (FLUX) APIs.

📋 **[Model Reference](https://agents365-ai.github.io/imagenCN/docs/models.html)** — browse all 44 models with pricing, resolution, and feature comparison.

## Pipeline

<img src="assets/workflow.png" width="450" alt="imagencn Workflow">

## Features

- **Alibaba Cloud Bailian (DashScope)**: Qwen-Image 2.0, Edit, Wan Series, Z-Image — 21 models
- **ByteDance Volcano Ark**: Doubao-Seedream series (5.0/4.5/4.0) — 3 models, up to 4K
- **Tencent Hunyuan**: Hunyuan Image 3.0 — flagship, complex Chinese composition
- **Zhipu / BigModel**: CogView-4, GLM-Image — 3 models, native Chinese text in images
- **StepFun / 阶跃星辰**: Step-2X, Step-Image-Edit-2 — 2 models, ultra-cheap volume gen
- **Google Gemini** (international): Gemini 3 Pro Image / 3.1 Flash Image — 4 models, 512/1K/2K/4K plus aspect ratios
- **Grok / xAI** (international): Grok Imagine — 3 models, aspect-ratio + resolution presets up to 4K
- **OpenAI** (international): GPT Image 1/1.5/2 — 4 models, arbitrary sizes up to 4K (gpt-image-2)
- **Black Forest Labs / FLUX** (international): FLUX.2 Pro / Max — 3 models, async API, flexible ratios + seed control
- **Multiple size presets**: 1:1, 16:9, 9:16, 4:3, 3:4, plus 1K/2K/3K/4K
- **Cross-platform**: Windows, macOS, Linux support
- **Multiple API regions**: China (default), Singapore, Virginia (DashScope)

## Installation

### Claude Code Marketplace (recommended)

```bash
/plugin install imagencn@365-skills
```

Or tell your coding agent:
> help me to install <https://github.com/Agents365-ai/365-skills>

### Manual

The skill lives in the Agents365-ai skills monorepo; clone the monorepo and
link or copy the skill directory into your agent's skills path:

```bash
git clone https://github.com/Agents365-ai/365-skills.git

# Global install (Claude Code example; other agents read their own skills path)
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" ~/.claude/skills/imagencn

# Project-specific
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" .claude/skills/imagencn
```

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" skills/imagencn
```

### SkillsMP

Search `imagencn` on [skillsmp.com](https://skillsmp.com) for one-click install.

## Requirements

### System Requirements

- Python 3.8+
- pip

### Install Dependencies

```bash
pip install dashscope requests
```

### API Keys

```bash
# Alibaba Cloud Bailian (DashScope)
export DASHSCOPE_API_KEY="your_api_key"
# Get key: https://bailian.console.aliyun.com/

# ByteDance Volcano Ark (optional)
export ARK_API_KEY="your_api_key"
# Get key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey

# Tencent Hunyuan (optional)
export HUNYUAN_API_KEY="your_api_key"
# Get key: https://console.cloud.tencent.com/tokenhub/apikey

# Zhipu / BigModel (optional)
export ZHIPUAI_API_KEY="your_api_key"
# Get key: https://bigmodel.cn

# StepFun / 阶跃星辰 (optional)
export STEP_API_KEY="your_api_key"
# Get key: https://platform.stepfun.com/interface-key

# Google Gemini (optional, international)
export GEMINI_API_KEY="your_api_key"
# Get key: https://aistudio.google.com/

# Grok / xAI (optional, international)
export XAI_API_KEY="your_api_key"
# Get key: https://console.x.ai/

# OpenAI (optional, international)
export OPENAI_API_KEY="your_api_key"
# Get key: https://platform.openai.com/api-keys
```

### Config File (Optional)

Create `~/.imagencn.json` for personal defaults:

```json
{"platform": "ark", "model": "doubao-seedream-5-0-260128", "size": "2K"}
```

Project-level `.imagencn.json` overrides user-level. CLI args override both.

> **Upgrading from imagenCN (≤1.1.x)?** The skill was renamed to lowercase `imagencn` — rename your config file too: `mv ~/.imagenCN.json ~/.imagencn.json` (and the install dir `~/.claude/skills/imagenCN` → `~/.claude/skills/imagencn`).

### Optional Environment Variables

```bash
# Set default model per platform
export DASHSCOPE_MODEL="wan2.7-image-pro"       # DashScope default
export ARK_MODEL="doubao-seedream-5-0-260128"   # Volcano Ark default
export HUNYUAN_MODEL="hy-image-v3.0"            # Tencent Hunyuan default
export ZHIPUAI_MODEL="cogview-4"                # Zhipu default
export STEP_MODEL="step-2x-large"               # StepFun default
export GEMINI_MODEL="gemini-3-pro-image-preview" # Google Gemini default
export XAI_MODEL="grok-imagine-image-quality"    # Grok / xAI default
export OPENAI_MODEL="gpt-image-1"                # OpenAI default
export BFL_MODEL="flux-2-pro-preview"            # FLUX default

# Set API endpoint (DashScope only, default: cn)
export DASHSCOPE_API_BASE="cn"  # or "sg", "us", or full URL
```

## Quick Start

### Natural Language (Claude Code)

Just tell Claude what you want:

```
Generate an image of a cute orange cat
Create a poster with text "Happy New Year" in Chinese
Make a photorealistic 4K mountain sunset photo using wan2.7-image-pro
Generate a 16:9 landscape wallpaper
```

### Command Line

```bash
# Basic usage (default model: qwen-image-2.0-pro, native 2K)
python scripts/generate_image.py "A cute cat" output.png

# Photorealistic 4K with Wan2.7 (DashScope)
python scripts/generate_image.py --model wan2.7-image-pro --size 4K "Mountain sunset" photo.png

# Volcano Ark (ByteDance) — requires ARK_API_KEY
python scripts/generate_image.py --platform ark "Editorial portrait, Vogue style" portrait.png

# Tencent Hunyuan — requires HUNYUAN_API_KEY
python scripts/generate_image.py --platform hunyuan "Astronaut on the moon, cinematic" scifi.png

# Google Gemini (international) — requires GEMINI_API_KEY
python scripts/generate_image.py --platform gemini "Japanese garden, morning light" garden.png

# Grok / xAI (international) — requires XAI_API_KEY
python scripts/generate_image.py --platform grok --size 16:9 "Cyberpunk city street at night" city.png

# OpenAI (international) — requires OPENAI_API_KEY
python scripts/generate_image.py --platform openai --quality high "Minimalist ceramic teapot product shot" teapot.png

# Black Forest Labs / FLUX (international) — requires BFL_API_KEY
python scripts/generate_image.py --platform bfl --size 16:9 "Volcanic coastline at dusk" coast.png

# Edit an existing image (DashScope, requires --image)
python scripts/generate_image.py --model qwen-image-edit-max --image input.png "Change the background to a beach" edited.png

# With negative prompt (DashScope)
python scripts/generate_image.py --negative "blurry" "High quality portrait" portrait.png

# List all 9 platforms' models
python scripts/generate_image.py --list-models
```

## Models

| Model | Best For |
| ------- | ---------- |
| `qwen-image-2.0-pro` | **Default**, latest flagship, native 2K, strongest typography and detail |
| `qwen-image-2.0-pro-2026-06-22` | Latest snapshot (Jun 2026), generation + editing fusion |
| `qwen-image-2.0` | Standard 2.0 tier, native 2K |
| `qwen-image-max` | Previous-gen flagship |
| `qwen-image-max-2025-12-30` | qwen-image-max snapshot, improved realism |
| `qwen-image-plus` | Distilled accelerated version |
| `qwen-image-plus-2026-01-09` | qwen-image-plus snapshot (Jan 2026) |
| `qwen-image-edit-max` | Flagship image editing (requires `--image`) |
| `qwen-image-edit-max-2026-01-16` | Latest editing snapshot (Jan 2026) |
| `qwen-image-edit-plus` | Fast, lower-cost image editing |
| `qwen-image` | Base model |
| `wan2.7-image-pro` | Latest photorealistic, up to 4K output |
| `wan2.7-image` | Wan 2.7 standard, up to 2K |
| `wan2.6-t2i` | Wan 2.6, flexible sizing |
| `wan2.5-t2i-preview` | High quality art |
| `wan2.2-t2i-flash` | Fast generation |
| `wan2.2-t2i-plus` | Professional tier |
| `wanx2.1-t2i-turbo` | Fast execution |
| `wanx2.1-t2i-plus` | Professional tier |
| `wanx2.0-t2i-turbo` | Earlier generation |
| `z-image-turbo` | Lightweight, fast & low-cost; portraits and product images |
| `doubao-seedream-5-0-260128` | ByteDance latest, up to 3K, PNG/JPEG, best text rendering |
| `doubao-seedream-4-5-251128` | ByteDance Seedream 4.5, up to 4K |
| `doubao-seedream-4-0-250828` | ByteDance Seedream 4.0, budget-friendly 4K |
| `hy-image-v3.0` | Tencent Hunyuan flagship, strong Chinese composition understanding |
| `cogview-4` | Zhipu CogView-4, native Chinese text in images |
| `cogview-4-250304` | CogView-4 fixed snapshot (Mar 2025), reproducible results |
| `glm-image` | Zhipu GLM-Image flagship, up to 2048×2048 |
| `step-2x-large` | StepFun high quality, 0.1 RMB/image |
| `step-image-edit-2` | StepFun ultra-cheap, 0.02 RMB/image, negative prompt support |
| `gemini-3-pro-image-preview` | Google Gemini flagship (international), 512/1K/2K plus aspect ratios |
| `gemini-3-pro-image` | Google Gemini stable flagship, 1K/2K/4K |
| `gemini-3.1-flash-image` | Google Gemini fast generalist (Nano Banana 2), 512/1K/2K/4K |
| `gemini-3.1-flash-lite-image` | Google Gemini fastest/cheapest, 1K only |
| `grok-imagine-image-quality` | Grok high-quality image model, up to 4K |
| `grok-imagine-image` | Grok standard image model |
| `grok-2-image` | Grok legacy JPG model |
| `gpt-image-1` | OpenAI GPT Image 1, 1024/1536 sizes |
| `gpt-image-1-mini` | OpenAI GPT Image 1 Mini, fast & cheap |
| `gpt-image-1.5` | OpenAI GPT Image 1.5, improved quality |
| `gpt-image-2` | OpenAI flagship, arbitrary sizes up to 4K |
| `flux-2-pro-preview` | FLUX.2 Pro latest rolling (international), async API, prompt upsampling |
| `flux-2-pro` | FLUX.2 Pro pinned snapshot, reproducible results |
| `flux-2-max` | FLUX.2 highest quality, search-grounding |

## Size Presets

**Qwen-Image 2.0 (native 2K):**

- `1:1` → 2048×2048 (default)
- `16:9` → 2688×1536
- `9:16` → 1536×2688
- `4:3` → 2304×1728
- `3:4` → 1728×2304
- `1K` → 1024×1024
- `2K` → 2048×2048

**Qwen-Image legacy:**

- `1:1` → 1328×1328
- `16:9` → 1664×928
- `9:16` → 928×1664
- `4:3` → 1472×1104
- `3:4` → 1104×1472

**Z-Image (pixel area 512×512 to 2048×2048):**

- `1:1` → 1024×1024 (default)
- `16:9` → 1280×720
- `9:16` → 720×1280
- `2:3` → 1024×1536
- `3:2` → 1536×1024

**Wan Series (Wan2.7 also accepts `1K`/`2K`/`4K`):**

- `1:1` → 1024×1024
- `1:1-large` → 1280×1280
- `16:9` → 1280×720
- `9:16` → 720×1280
- `4:3` → 1200×900
- `3:4` → 900×1200
- `2:1` → 1440×720

**Volcano Ark (Seedream):**

- `1:1` → 2048×2048
- `16:9` → 2848×1600
- `9:16` → 1600×2848
- `4:3` → 2304×1728
- `3:4` → 1728×2304
- `1K` / `2K` / `3K` / `4K` (model-dependent)

**Tencent Hunyuan (colon-separated):**

- `1:1` → 1024:1024
- `16:9` → 1920:1080
- `9:16` → 1080:1920
- `4:3` → 1600:1200
- `3:4` → 1200:1600
- `3:2` → 1920:1280
- `2:3` → 1280:1920

**Zhipu (CogView-4 / GLM-Image):**

- `1:1` → 1024x1024 (default)
- `16:9` → 1344x768
- `9:16` → 768x1344
- `4:3` → 1152x864
- `3:4` → 864x1152
- `2:1` → 1440x720
- `1:2` → 720x1440

**StepFun (Step-2X):**

- `1:1` → 1024x1024 (default)
- `1:1-small` → 512x512
- `16:9` → 1280x800
- `9:16` → 800x1280

**Google Gemini (named sizes + aspect ratios):**

- `512` / `1K` (default) / `2K` / `4K` → named output size (4K on Pro / 3.1 Flash; Lite is 1K only)
- `1:1`, `16:9`, `9:16`, `4:3`, `3:4` → aspect ratio (no exact pixel sizes)

**Grok / xAI (aspect ratio + resolution):**

- `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `2:1` → sent as `aspect_ratio` (default: 1:1)
- `1K` / `2K` / `4K` → sent as `resolution`

**OpenAI (GPT Image):**

- `1:1` → 1024x1024 (default)
- `16:9` → 1536x1024, `9:16` → 1024x1536
- `4:3` → 1344x1024, `3:4` → 1024x1344
- `1K` → 1024x1024, `2K` → 2048x2048 (gpt-image-2 only), `4K` → 3840x2160 (gpt-image-2 only)

**FLUX (Black Forest Labs):**

- `1:1` → 1024x1024 (default)
- `16:9` → 1344x768, `9:16` → 768x1344
- `4:3` → 1152x864, `3:4` → 864x1152
- `2:1` → 1440x720, `1:2` → 720x1440
- `1K` → 1024x1024, `2K` → 2048x2048 (flexible WxH also accepted)

## API Endpoints

| Region | Alias | URL |
| -------- | ------- | ----- |
| **China** (default) | `cn` | `https://dashscope.aliyuncs.com/api/v1` |
| Singapore | `sg` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| Virginia | `us` | `https://dashscope-us.aliyuncs.com/api/v1` |

## Support

If this project helps you, consider supporting the author:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>WeChat Pay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
      <br>
      <b>Alipay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## License

[CC BY-NC 4.0](LICENSE) — free for non-commercial use. Commercial use requires permission.
