# imagencn Model Reference

> Data source: [`models.json`](models.json) · Updated: 2026-08-08

## Quick Reference

| Use Case | Model | Platform |
|----------|-------|----------|
| Default / general | `qwen-image-2.0-pro` | DashScope |
| Photorealistic photos | `wan2.7-image-pro` | DashScope |
| Edit an image | `qwen-image-edit-max` | DashScope |
| Cheap & fast | `z-image-turbo` | DashScope |
| Photo + text combo | `doubao-seedream-5-0-260128` | Volcano Ark |
| Complex Chinese composition | `hy-image-v3.0` | Hunyuan |
| Chinese text in images | `cogview-4` | Zhipu |
| Ultra-cheap volume gen | `step-image-edit-2` | StepFun |
| International / Gemini | `gemini-3-pro-image-preview` | Gemini |
| International / Grok | `grok-imagine-image-quality` | Grok |
| International / OpenAI | `gpt-image-1` | OpenAI |
| International / FLUX | `flux-2-pro-preview` | FLUX |

## Summary

| Platform | Models | Price Range | Max Res | Env Var |
|----------|--------|-------------|---------|---------|
| **DashScope** | 21 | ¥0.02/img–¥0.20/img | 1328×1328 / 2048×2048 / 2K / 4K / 768×2700 / auto (matches input) | `DASHSCOPE_API_KEY` |
| **Volcano Ark** | 3 | ¥0.15/img–¥0.22/img | 3K / 4K | `ARK_API_KEY` |
| **Hunyuan** | 1 | ¥0.20/img–¥0.20/img | 2048×2048 | `HUNYUAN_API_KEY` |
| **Zhipu** | 3 | ¥0.06/img–¥0.08/img | 2048×2048 | `ZHIPUAI_API_KEY` |
| **StepFun** | 2 | ¥0.02/img–¥0.10/img | 1024×1024 | `STEP_API_KEY` |
| **Gemini** | 4 | ~$0.03/img–~$0.13/img | 1K / 2K / 4K | `GEMINI_API_KEY` |
| **Grok** | 3 | $0.07/img–~$0.14/img | 1024×1024 / 4K | `XAI_API_KEY` |
| **OpenAI** | 4 | ~$0.01/img–~$0.21/img | 1024×1024 / 1536×1024 / 3840×2160 | `OPENAI_API_KEY` |
| **FLUX** | 3 | ~$0.03/img–~$0.10/img | 2K | `BFL_API_KEY` |

---

## Alibaba Cloud Bailian — 21 models

API: Native SDK (dashscope) · Endpoint: `https://dashscope.aliyuncs.com/api/v1`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `qwen-image-2.0-pro` ★ | Qwen-Image 2.0 | ¥0.12/img | 2048×2048 | Latest flagship, native 2K, strongest typography and detail |
| `qwen-image-2.0-pro-2026-06-22` | Qwen-Image 2.0 | ¥0.12/img | 2048×2048 | Latest snapshot: generation + editing fusion, improved text |
| `qwen-image-2.0` | Qwen-Image 2.0 | ¥0.10/img | 2048×2048 | Standard 2.0 tier, native 2K |
| `qwen-image-max` | Qwen-Image 2.0 | ¥0.10/img | 2048×2048 | Previous-gen flagship (Dec 2025) |
| `qwen-image-max-2025-12-30` | Qwen-Image 2.0 | ¥0.10/img | 2048×2048 | qwen-image-max snapshot, improved realism |
| `qwen-image-edit-max` | Editing | ¥0.12/img | auto (matches input) | Flagship editing model, strongest instruction following |
| `qwen-image-edit-max-2026-01-16` | Editing | ¥0.12/img | auto (matches input) | Latest editing snapshot |
| `qwen-image-edit-plus` | Editing | ¥0.06/img | auto (matches input) | Fast, lower-cost image editing |
| `qwen-image-plus` | Legacy | ¥0.04/img | 1328×1328 | Distilled accelerated version of qwen-image-max |
| `qwen-image-plus-2026-01-09` | Legacy | ¥0.04/img | 1328×1328 | qwen-image-plus snapshot, fast high-quality |
| `qwen-image` | Legacy | ¥0.04/img | 1328×1328 | Base model |
| `z-image-turbo` | Z-Image | ¥0.02/img | 2048×2048 | Lightweight, fast & low-cost; portraits and product images |
| `wan2.7-image-pro` | Wan Series | ¥0.20/img | 4K | Latest photorealistic, up to 4K, unified T2I + edit + multi-image |
| `wan2.7-image` | Wan Series | ¥0.12/img | 2K | Wan 2.7 standard, up to 2K |
| `wan2.6-t2i` | Wan Series | ¥0.10/img | 2K | Wan 2.6, flexible sizing |
| `wan2.5-t2i-preview` | Wan Series | ¥0.10/img | 768×2700 | High quality art, up to 768×2700 |
| `wan2.2-t2i-flash` | Wan Series | ¥0.06/img | 2K | Speed-optimized |
| `wan2.2-t2i-plus` | Wan Series | ¥0.10/img | 2K | Professional tier |
| `wanx2.1-t2i-turbo` | Wan Series | ¥0.06/img | 2K | Fast execution |
| `wanx2.1-t2i-plus` | Wan Series | ¥0.10/img | 2K | Professional tier |
| `wanx2.0-t2i-turbo` | Wan Series | ¥0.06/img | 2K | Earlier generation |

---

## ByteDance Volcano Ark — 3 models

API: OpenAI-compatible REST · Endpoint: `https://ark.cn-beijing.volces.com/api/v3/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `doubao-seedream-5-0-260128` ★ | Seedream | ¥0.22/img | 3K | Latest flagship, up to 3K, PNG/JPEG, best text rendering |
| `doubao-seedream-4-5-251128` | Seedream | ¥0.22/img | 4K | Seedream 4.5, up to 4K |
| `doubao-seedream-4-0-250828` | Seedream | ¥0.15/img | 4K | Seedream 4.0, budget-friendly 4K |

---

## Tencent Hunyuan — 1 model

API: OpenAI-compatible REST · Endpoint: `https://tokenhub.tencentmaas.com/v1/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `hy-image-v3.0` ★ | Hunyuan | ¥0.20/img | 2048×2048 | Flagship, strong composition awareness, handles 8K-char Chinese prompts |

---

## Zhipu / BigModel — 3 models

API: OpenAI-compatible REST · Endpoint: `https://api.z.ai/api/paas/v4/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `cogview-4` ★ | CogView | ¥0.06/img | 2048×2048 | Stable alias for latest CogView-4, native Chinese text rendering |
| `cogview-4-250304` | CogView | ¥0.06/img | 2048×2048 | Fixed snapshot, reproducible results |
| `glm-image` | GLM | ¥0.08/img | 2048×2048 | GLM-Image flagship, hybrid autoregressive/diffusion, up to 2048×2048 |

---

## StepFun — 2 models

API: OpenAI-compatible REST · Endpoint: `https://api.stepfun.com/v1/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `step-2x-large` ★ | Step-2X | ¥0.10/img | 1024×1024 | High quality, 0.1 RMB/image, up to 1024×1024 |
| `step-image-edit-2` | Step-Edit | ¥0.02/img | 1024×1024 | Ultra-cheap, 0.02 RMB/image, supports negative prompts, 8 inference steps |

---

## Google Gemini — 4 models

API: REST (generateContent) · Endpoint: `https://generativelanguage.googleapis.com/v1beta/models`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `gemini-3-pro-image-preview` ★ | Gemini | ~$0.13/img | 2K | Google flagship image model, 512/1K/2K named sizes plus aspect-ratio presets |
| `gemini-3-pro-image` | Gemini | ~$0.13/img | 4K | Stable flagship image model (Nano Banana Pro), 1K/2K/4K |
| `gemini-3.1-flash-image` | Gemini | ~$0.07/img | 4K | Nano Banana 2: fast generalist workhorse, 512/1K/2K/4K, strong text rendering |
| `gemini-3.1-flash-lite-image` | Gemini | ~$0.03/img | 1K | Nano Banana 2 Lite: fastest and cheapest, 1K only |

---

## Grok (xAI) — 3 models

API: REST (OpenAI-compatible) · Endpoint: `https://api.x.ai/v1/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `grok-imagine-image-quality` ★ | Grok Imagine | ~$0.14/img | 4K | High-quality Grok image model, aspect-ratio and resolution presets |
| `grok-imagine-image` | Grok Imagine | ~$0.11/img | 4K | Standard Grok image model (alias grok-imagine-image-2026-03-02) |
| `grok-2-image` | Grok Imagine | $0.07/img | 1024×1024 | Legacy JPG image model, no size control |

---

## OpenAI — 4 models

API: REST (Images API) · Endpoint: `https://api.openai.com/v1/images/generations`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `gpt-image-1` ★ | GPT Image | ~$0.04/img | 1536×1024 | Multimodal image model; 1024x1024/1536x1024/1024x1536 only |
| `gpt-image-1-mini` | GPT Image | ~$0.01/img | 1024×1024 | Fast and cheap GPT image variant |
| `gpt-image-1.5` | GPT Image | ~$0.05/img | 1536×1024 | Improved GPT image generation quality |
| `gpt-image-2` | GPT Image | ~$0.21/img | 3840×2160 | Latest flagship; arbitrary WxH sizes (edges divisible by 16) up to 4K |

---

## Black Forest Labs — 3 models

API: Async REST (polling) · Endpoint: `https://api.bfl.ai/v1`

| Model | Category | Price | Max Res | Notes |
|-------|----------|-------|---------|-------|
| `flux-2-pro-preview` ★ | FLUX.2 | ~$0.03/img | 2K | Latest rolling FLUX.2 Pro, recommended default; prompt upsampling built in |
| `flux-2-pro` | FLUX.2 | ~$0.03/img | 2K | Fixed snapshot of FLUX.2 Pro for reproducible workflows |
| `flux-2-max` | FLUX.2 | ~$0.10/img | 2K | Highest quality FLUX.2 with search-grounding for real-time information |

---

## How to Update

Edit [`docs/models.json`](models.json), then re-sync `models.html` (DATA block)
and regenerate this file from the JSON source.
