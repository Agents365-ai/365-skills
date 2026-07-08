# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

All code, comments, and documentation must be in English.

## Git Commits

Do NOT add "Co-Authored-By: Claude" to commit messages.

## What This Is

A Claude Code skill for AI image generation using three Chinese T2I platforms:
- Alibaba Cloud Bailian (阿里云百炼) — DashScope API
- ByteDance Volcano Ark (火山方舟) — Seedream models
- Tencent Hunyuan (腾讯混元) — Hunyuan Image 3.0

## Models

- **Qwen-Image (通义千问)**: Best for Chinese/English text rendering on images (DashScope)
- **Wan Series (通义万相)**: Best for photorealistic images and photography (DashScope)
- **Z-Image**: Lightweight, fast & low-cost (DashScope)
- **Seedream (豆包)**: Photo + text combo, up to 4K (Volcano Ark)
- **Hunyuan Image (混元生图)**: Complex Chinese composition, 8K-char prompts (Tencent Hunyuan)

## Key Command

```bash
# Basic usage
python scripts/generate_image.py "prompt" output.png

# With model and size (DashScope)
python scripts/generate_image.py --model wan2.7-image-pro --size 16:9 "prompt" output.png

# Volcano Ark (ByteDance) — requires ARK_API_KEY
python scripts/generate_image.py --platform ark "prompt" output.png

# Tencent Hunyuan — requires HUNYUAN_API_KEY
python scripts/generate_image.py --platform hunyuan "prompt" output.png

# List models (all 3 platforms)
python scripts/generate_image.py --list-models
```

## Environment Variables

```bash
export DASHSCOPE_API_KEY="your_api_key"   # Required (DashScope)
export DASHSCOPE_MODEL="qwen-image-plus"  # Optional default model (DashScope)
export DASHSCOPE_API_BASE="cn"            # Optional: cn, sg, us (DashScope)

export ARK_API_KEY="your_api_key"         # Required (Volcano Ark)
export ARK_MODEL="doubao-seedream-5-0-260128"  # Optional default model (Ark)

export HUNYUAN_API_KEY="your_api_key"     # Required (Tencent Hunyuan)
export HUNYUAN_MODEL="hy-image-v3.0"      # Optional default model (Hunyuan)
```

## Project Structure

```
imagenCN/
├── SKILL.md              # Main documentation
├── scripts/
│   └── generate_image.py # Image generation script
└── CLAUDE.md             # This file
```
