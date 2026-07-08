---
name: imagenCN
description: Use when generating images with Alibaba Cloud Bailian API, especially for Chinese text rendering or photorealistic images
author: Agents365-ai
created: 2024-12-01
updated: 2026-07-05
homepage: https://github.com/Agents365-ai/imagenCN
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["DASHSCOPE_API_KEY"]},"primaryEnv":"DASHSCOPE_API_KEY","emoji":"🎨"}}
---

# ImagenCN - Alibaba Cloud Bailian Text-to-Image Skill

## Overview

Generate images using Alibaba Cloud Bailian API. **Default endpoint is China region**.

Supports three platforms across seven model families:
- **Alibaba Cloud Bailian** (DashScope): Qwen-Image 2.0, Qwen-Image Edit, Qwen-Image legacy, Wan Series, Z-Image
- **ByteDance Volcano Ark**: Doubao-Seedream series (OpenAI-compatible REST)
- **Tencent Hunyuan**: Hunyuan Image 3.0 (OpenAI-compatible REST)

**Cross-platform support**: Windows, macOS, Linux

## When to Use This Skill

Automatically activate this skill when:
- User requests image generation with Chinese text or calligraphy
- Need photorealistic images or photography-style visuals
- Creating commercial posters, illustrations, or digital art
- User mentions any of these: Alibaba Cloud / Bailian / Qwen / Wan / DashScope, ByteDance / Volcano Ark / Seedream / Doubao, Tencent / Hunyuan
- Any task where AI-generated image with strong Chinese support would be helpful

## Workflow

1. **Refine the prompt** (critical — never skip).  Users often give short, casual
   descriptions.  Expand them into a detailed, high-quality prompt before calling the
   API.  Add, as appropriate:
   - Subject details (shape, colour, material, expression, pose)
   - Lighting (golden hour, studio, rim light, soft diffused, neon, cinematic)
   - Composition (rule of thirds, shallow depth of field, wide shot, close-up)
   - Style / medium (photorealistic, oil painting, watercolour, 3D render, vector)
   - Mood / atmosphere (serene, dramatic, whimsical, dystopian, elegant)
   - Quality keywords (8K, hyperdetailed, award-winning, professional photography)
   - For Chinese text on images: describe the text content, placement, font style
     (e.g. calligraphy, sans-serif, bold), colour, and size

2. Pick a model based on the request (see Model Selection Guide below). Default to `qwen-image-2.0-pro` if unsure.
3. Pick a size: native 2K for the Qwen-Image 2.0 family, `1K`/`2K`/`4K` for Wan2.7, or an aspect-ratio preset (`16:9`, `1:1`, etc.).
4. Run `scripts/generate_image.py` with the refined prompt and output path.
5. If the output path was implicit, save into the user's current working directory.

## Models

### Qwen-Image 2.0 family - Latest Flagship (MultiModalConversation API)

| Model | Description |
|-------|-------------|
| `qwen-image-2.0-pro` | **Default**. Latest flagship, native 2K, strongest typography and detail |
| `qwen-image-2.0-pro-2026-06-22` | Latest snapshot (Jun 2026): generation + editing fusion, better text rendering and prompt adherence |
| `qwen-image-2.0` | Standard 2.0 tier, native 2K |
| `qwen-image-max` | Previous-gen flagship (Dec 2025) |
| `qwen-image-max-2025-12-30` | qwen-image-max snapshot: improved realism, fewer AI artifacts |

### Qwen-Image Edit family - Image Editing (MultiModalConversation API)

Editing models require an input image via `--image` (local path or URL). Omit `--size` to match the input image dimensions.

| Model | Description |
|-------|-------------|
| `qwen-image-edit-max` | Flagship editing model, strongest instruction following |
| `qwen-image-edit-max-2026-01-16` | Latest max snapshot (Jan 2026) |
| `qwen-image-edit-plus` | Faster, lower-cost editing |

### Qwen-Image legacy (ImageSynthesis API)

| Model | Description |
|-------|-------------|
| `qwen-image-plus` | Distilled accelerated version of qwen-image-max |
| `qwen-image-plus-2026-01-09` | qwen-image-plus snapshot (Jan 2026): faster high-quality generation |
| `qwen-image` | Base model |

### Wan Series - Photorealistic Generation (ImageGeneration API)

| Model | Description |
|-------|-------------|
| `wan2.7-image-pro` | **Latest**. Up to 4K output, unified architecture (T2I + edit + multi-image) |
| `wan2.7-image` | Wan 2.7 standard, up to 2K |
| `wan2.6-t2i` | Wan 2.6, flexible sizing |
| `wan2.5-t2i-preview` | High quality, up to 768x2700 |
| `wan2.2-t2i-flash` | Speed-optimized |
| `wan2.2-t2i-plus` | Professional tier |
| `wanx2.1-t2i-turbo` | Fast execution |
| `wanx2.1-t2i-plus` | Professional tier |
| `wanx2.0-t2i-turbo` | Earlier generation |

### Z-Image - Lightweight & Fast (MultiModalConversation API)

| Model | Description |
|-------|-------------|
| `z-image-turbo` | Fast, low-cost generation; bilingual (CN/EN) text rendering, high-fidelity portraits and product images. Pixel area 512x512 to 2048x2048 |

### Volcano Ark - ByteDance Seedream (OpenAI-compatible API)

| Model | Description |
|-------|-------------|
| `doubao-seedream-5-0-260128` | **Ark default**. Latest, up to 3K, PNG/JPEG output, best text rendering |
| `doubao-seedream-4-5-251128` | Seedream 4.5, up to 4K |
| `doubao-seedream-4-0-250828` | Seedream 4.0, up to 4K, budget-friendly |

### Tencent Hunyuan (OpenAI-compatible API)

| Model | Description |
|-------|-------------|
| `hy-image-v3.0` | **Hunyuan default**. Flagship 3.0, strong composition awareness, handles complex Chinese prompts up to 8K chars |

## Usage

### Basic Usage

```bash
# Default model (qwen-image-2.0-pro, native 2K output)
python ~/.claude/skills/imagenCN/scripts/generate_image.py "A cute cat" output.png

# Photorealistic with Wan model (Wan2.7 supports 4K)
python ~/.claude/skills/imagenCN/scripts/generate_image.py --model wan2.7-image-pro --size 4K "Realistic photo of mountains at sunset" photo.png

# Edit an existing image (requires --image; local path or URL)
python ~/.claude/skills/imagenCN/scripts/generate_image.py --model qwen-image-edit-max --image input.png "Change the background to a beach at sunset" edited.png
```

### Size Options

```bash
# Use ratio preset
python ~/.claude/skills/imagenCN/scripts/generate_image.py --size 16:9 "Wide landscape" landscape.png

# Use exact dimensions
python ~/.claude/skills/imagenCN/scripts/generate_image.py --size 1280*720 "Custom size" custom.png
```

### Size Presets

**Qwen-Image 2.0 (native 2K):**
- `1:1` -> 2048x2048 (default)
- `16:9` -> 2688x1536
- `9:16` -> 1536x2688
- `4:3` -> 2304x1728
- `3:4` -> 1728x2304
- `1K` -> 1024x1024
- `2K` -> 2048x2048

**Qwen-Image legacy:**
- `1:1` -> 1328x1328
- `16:9` -> 1664x928
- `9:16` -> 928x1664
- `4:3` -> 1472x1104
- `3:4` -> 1104x1472

**Z-Image (pixel area 512x512 to 2048x2048):**
- `1:1` -> 1024x1024 (default)
- `16:9` -> 1280x720
- `9:16` -> 720x1280
- `2:3` -> 1024x1536
- `3:2` -> 1536x1024
- `1K` -> 1024x1024

**Wan Series (Wan2.7 also accepts `1K`/`2K`/`4K`):**
- `1:1` -> 1024x1024
- `1:1-large` -> 1280x1280
- `16:9` -> 1280x720
- `9:16` -> 720x1280
- `4:3` -> 1200x900
- `3:4` -> 900x1200
- `2:1` -> 1440x720

**Volcano Ark (Seedream):**
- `1:1` -> 2048x2048
- `16:9` -> 2848x1600
- `9:16` -> 1600x2848
- `4:3` -> 2304x1728
- `3:4` -> 1728x2304
- `3:2` -> 2496x1664
- `2:3` -> 1664x2496
- `1K` / `2K` / `3K` / `4K` (model-dependent max resolution)

**Tencent Hunyuan (colon-separated format):**
- `1:1` -> 1024:1024
- `16:9` -> 1920:1080
- `9:16` -> 1080:1920
- `4:3` -> 1600:1200
- `3:4` -> 1200:1600

### Advanced Options

```bash
# With negative prompt
python ~/.claude/skills/imagenCN/scripts/generate_image.py --negative "blurry, low quality" "High quality portrait" portrait.png

# List all models
python ~/.claude/skills/imagenCN/scripts/generate_image.py --list-models
```

## Requirements

```bash
pip install dashscope requests

# Optional: for coloured output and styled tables
pip install rich
```

## Environment Variables

```bash
# Alibaba Cloud Bailian (DashScope)
export DASHSCOPE_API_KEY="your_api_key"        # Required
export DASHSCOPE_MODEL="wan2.7-image-pro"       # Optional default model
export DASHSCOPE_API_BASE="cn"                  # Optional: cn, sg, us

# ByteDance Volcano Ark
export ARK_API_KEY="your_api_key"               # Required for Ark
export ARK_MODEL="doubao-seedream-5-0-260128"   # Optional default model

# Tencent Hunyuan (TokenHub)
export HUNYUAN_API_KEY="your_api_key"           # Required for Hunyuan
export HUNYUAN_MODEL="hy-image-v3.0"            # Optional default model
```

Get API Keys:
- DashScope: https://bailian.console.aliyun.com/
- Volcano Ark: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
- Tencent Hunyuan: https://console.cloud.tencent.com/tokenhub/apikey

## Config File (Optional)

Create `~/.imagenCN.json` for personal defaults, or `.imagenCN.json` in a project
directory for per-project overrides.  API keys stay in environment variables for
security.

```json
{
  "platform": "ark",
  "model": "doubao-seedream-5-0-260128",
  "size": "2K"
}
```

All keys are optional.  Priority (highest first):
1. CLI arguments (`--platform`, `--model`, `--size`)
2. Project config (`.imagenCN.json` in current directory)
3. User config (`~/.imagenCN.json`)
4. Environment variables (`DASHSCOPE_MODEL`, `ARK_MODEL`, `HUNYUAN_MODEL`)
5. Built-in defaults

## API Endpoints

| Region | Alias | URL |
|--------|-------|-----|
| **China** (default) | `cn` | `https://dashscope.aliyuncs.com/api/v1` |
| Singapore | `sg` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| Virginia | `us` | `https://dashscope-us.aliyuncs.com/api/v1` |

```bash
# Switch to Singapore endpoint
export DASHSCOPE_API_BASE="sg"

# Or use full URL
export DASHSCOPE_API_BASE="https://dashscope-intl.aliyuncs.com/api/v1"
```

## Model Selection Guide

### Quick Pick — You Only Need Six

| What you want | Model | Platform |
|---------------|-------|----------|
| **Default / general** (posters, text, daily use) | `qwen-image-2.0-pro` | DashScope |
| **Photorealistic** (portraits, landscapes, products) | `wan2.7-image-pro` | DashScope |
| **Edit an image** (swap backgrounds, restyle) | `qwen-image-edit-max` | DashScope |
| **Cheap & fast** (quick drafts, high volume) | `z-image-turbo` | DashScope |
| **Best text + photography combo** | `doubao-seedream-5-0-260128` | Volcano Ark |
| **Complex Chinese composition** | `hy-image-v3.0` | Tencent Hunyuan |

All other models are legacy/snapshot variants. You don't need them unless you have a specific reason.

### Full Reference

| Use Case | Recommended Model |
|----------|-------------------|
| General high-quality (default) | `qwen-image-2.0-pro` |
| Chinese text/calligraphy | `qwen-image-2.0-pro` |
| English text on images | `qwen-image-2.0-pro` |
| Posters with typography | `qwen-image-2.0-pro` |
| Photorealistic photos (4K) | `wan2.7-image-pro` |
| Photorealistic photos (2K) | `wan2.7-image` |
| Portrait photography | `wan2.7-image-pro` |
| Image editing (best quality) | `qwen-image-edit-max` |
| Image editing (fast, low-cost) | `qwen-image-edit-plus` |
| Fast, low-cost generation | `z-image-turbo` |
| High-fidelity portraits / product shots (fast) | `z-image-turbo` |
| Fast photorealistic (Wan) | `wan2.2-t2i-flash` |
| Lower-cost text rendering | `qwen-image-plus` |
| ByteDance best quality | `doubao-seedream-5-0-260128` |
| Budget-friendly 4K (ByteDance) | `doubao-seedream-4-0-250828` |
| Complex Chinese prompts (Tencent) | `hy-image-v3.0` |

## Platform Quick Comparison

| Feature | DashScope (Bailian) | Volcano Ark | Tencent Hunyuan |
|---------|---------------------|-------------|-----------------|
| Best for | Text rendering, model variety | Photo + text combo | Complex Chinese composition |
| Max resolution | 4K (Wan2.7) | 4K (Seedream 4.0/4.5) | 2K |
| SDK required | `dashscope` | None (REST) | None (REST) |
| Pricing | Varies per model | ~0.22 RMB/image | ~0.20 RMB/image |
| Env var | `DASHSCOPE_API_KEY` | `ARK_API_KEY` | `HUNYUAN_API_KEY` |

## Comparison with Imagen (Gemini)

| Feature | ImagenCN (Bailian) | Imagen (Gemini) |
|---------|-------------------|-----------------|
| Chinese text rendering | Excellent | Good |
| English text rendering | Excellent | Good |
| Photorealistic images | Excellent | Good |
| Speed | Medium | Fast |
| Model variety | 15+ models | 3 models |
| Max resolution | 4K (Wan2.7-Pro) | 2K |

## Examples

### Volcano Ark (ByteDance)
```bash
# Default Ark model (Seedream 5.0)
ARK_API_KEY="xxx" python scripts/generate_image.py \
  --platform ark \
  "A vibrant close-up editorial portrait, Vogue magazine cover style" \
  portrait.png

# With 4K output
ARK_API_KEY="xxx" python scripts/generate_image.py \
  --platform ark --model doubao-seedream-4-5-251128 --size 4K \
  "Breathtaking mountain sunset, golden hour, professional photography" \
  landscape.png
```

### Tencent Hunyuan
```bash
# Default Hunyuan model (Image 3.0)
HUNYUAN_API_KEY="xxx" python scripts/generate_image.py \
  --platform hunyuan \
  "An astronaut riding a horse on the moon, cinematic lighting, 8K detail" \
  scifi.png

# With prompt auto-enhance disabled
HUNYUAN_API_KEY="xxx" python scripts/generate_image.py \
  --platform hunyuan --revise 0 \
  "A cute orange cat napping in sunlight, oil painting style" \
  cat.png
```

### Chinese New Year Poster (DashScope)
```bash
python ~/.claude/skills/imagenCN/scripts/generate_image.py \
  "A beautiful Chinese New Year poster with red background, golden text, fireworks and firecrackers" \
  new_year_poster.png
```

### Photorealistic Landscape (4K)
```bash
python ~/.claude/skills/imagenCN/scripts/generate_image.py \
  --model wan2.7-image-pro \
  --size 4K \
  "Breathtaking sunset over mountain range, golden hour, professional photography" \
  landscape.png
```

### Product Shot
```bash
python ~/.claude/skills/imagenCN/scripts/generate_image.py \
  --model wan2.7-image \
  --size 2K \
  "Professional product photography of a coffee cup on marble surface, studio lighting" \
  product.png
```
