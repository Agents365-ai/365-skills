---
name: ttsCN
description: Multi-platform Chinese TTS text-to-speech via Edge/Doubao/CosyVoice/Azure/Tencent/Baidu/MiniMax/Xunfei — 8 backends, all work in China
author: Agents365-ai
created: 2026-07-08
updated: 2026-07-08
homepage: https://github.com/Agents365-ai/ttsCN
metadata: {"openclaw":{"requires":{"bins":["python3","ffmpeg"]},"emoji":"🔊"}}
---

# ttsCN — Multi-Platform Chinese TTS Skill

## Overview

Generate natural Chinese speech audio from text. **8 backends, all work in China**.

| # | Backend | Cost | Key strength |
|---|---------|------|-------------|
| 1 | **Edge TTS** (default) | Free | No API key, works everywhere |
| 2 | **Doubao** (ByteDance) | ~1 RMB/10K | Best Chinese naturalness (9/10) |
| 3 | **CosyVoice** (Alibaba) | ~0.2 RMB/1K | Fast streaming, flexible |
| 4 | **Azure** (Microsoft) | ~1 USD/M chars | Enterprise SSML, eastasia |
| 5 | **Tencent Cloud** | **0.75 RMB/10K** | Lowest cost, 380+ voices |
| 6 | **Baidu AI** | Flexible | 30+ voices, emotion + dialects |
| 7 | **MiniMax** | ~$0.10/1K | Best quality, 300+ voices, cloning |
| 8 | **iFlytek Xunfei** | ~2 RMB/10K | MOS 4.8, 500+ voices, pro grade |

**Cross-platform**: Windows, macOS, Linux

## When to Use This Skill

Automatically activate this skill when:
- User wants to convert Chinese text to speech audio
- Generating voice narration or voiceover for videos
- Creating audiobook or podcast audio from text
- User asks to compare TTS providers, choose a TTS backend, or see what voices are available
- User asks about TTS pricing, features, or which provider supports cloning/SSML/dialects
- User mentions any of: TTS, text-to-speech, 语音合成, 文字转语音, Edge TTS, Doubao TTS, CosyVoice, 火山引擎, 阿里云语音, Azure TTS, 腾讯云TTS, 百度语音, MiniMax, 讯飞语音
- Any task where Chinese text-to-speech would be helpful

## Provider Comparison Page

**When the user wants to browse, compare, or choose a TTS provider, ALWAYS open the
local HTML comparison page in their browser FIRST** — it's a visual, filterable table
that is much faster to scan than reading text output.

```bash
# Open the comparison page
open ~/.claude/skills/ttsCN/docs/providers.html
```

The comparison page includes:
- **Filterable table** — filter by free, SSML, voice cloning, streaming, dialects, multilingual
- **Per-provider detail panels** — cost, max chars/duration, clone method, emotion, languages
- **Voice cards** — recommended voices with style descriptions and best-use labels
- **API key links** — direct links to each provider's console for key acquisition

This page is auto-generated from `data/providers.json`. Run `python scripts/build_docs.py`
to regenerate it after editing the JSON.

**After opening the page**, ask the user which backend and voice they'd like to use,
then proceed to Step 2.

## Workflow

### Step 0 — Show the comparison page (when comparing/choosing)

If the user is browsing, comparing providers, or unsure which backend to use:

```bash
open ~/.claude/skills/ttsCN/docs/providers.html
```

This opens a filterable visual comparison in their browser. Let them explore,
then ask which backend + voice they want.

### Step 1 — Understand the request

Clarify what the user needs:
- **Text**: inline text or a file? Short or long-form?
- **Voice style**: male/female, young/mature, warm/energetic? (see Voice Guide)
- **Speed**: normal, faster (+10-20%), slower (-10-20%)?
- **Format**: WAV (lossless) or MP3 (compressed)?

### Step 2 — Pick a backend & voice

Choose based on the use case (see Backend Selection Guide). Default to **Edge TTS**
with `zh-CN-XiaoxiaoNeural` (female, warm, standard) if unsure. Mention your choice.

### Step 3 — Synthesize

Run `scripts/tts.py` with the text and chosen options.

### Step 4 — Report

Confirm: output path, file size, audio duration.

## Backend Selection Guide

### Quick Pick

| Use case | Backend | Voice | Why |
|----------|---------|-------|-----|
| **Default / general** | edge | zh-CN-XiaoxiaoNeural | Free, no setup |
| **Short video / Douyin** | doubao | BV001_streaming | Native short-video style |
| **Audiobook / long-form** | cosyvoice | longxiaochun_v3 | Fast synthesis, natural |
| **Enterprise / SSML** | azure | zh-CN-XiaoxiaoNeural | Rich prosody control |
| **Bulk / lowest cost** | tencent | 101001 | 0.75 RMB/10K chars |
| **Emotion / dialects** | baidu | 3 or 4 | Emotion synthesis, Cantonese |
| **Best quality / cloning** | minimax | female-shaonv | speech-2.8-hd, voice design |
| **Education / pro** | xunfei | xiaoyan | MOS 4.8, 500+ voices |
| **Male narration** | edge | zh-CN-YunxiNeural | Energetic male voice |
| **Documentary** | azure | zh-CN-YunyangNeural | Deep, professional male |
| **Children's content** | edge | zh-CN-XiaomengNeural | Bright, youthful female |
| **Cost-sensitive** | edge | zh-CN-XiaoxiaoNeural | Completely free |

### Full Capability Comparison

| Capability | Edge | Doubao | CosyVoice | Azure | Tencent | Baidu | MiniMax | Xunfei |
|------------|------|--------|-----------|-------|---------|-------|---------|--------|
| **Cost (per 10K chars)** | Free | ~1元 | ~2元 | ~$1/M chars | **0.75元** | 灵活 | ~$1 | ~2元 |
| **Built-in voices** | 20+ | 8 | 7 | 20+ | 380+ | 30+ | 300+ | 500+ |
| **Max chars / chunk** | 2000 | 280 | 400 | 2000 | 150 | 500 | **3000** | 200 |
| **Max duration / chunk** | ~10 min | ~1 min | ~2 min | ~10 min | ~30 s | ~2 min | ~5 min | ~1 min |
| **SSML** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Voice cloning** | ❌ | ✅ | ❌ | ✅ (gated) | ✅ | ✅ | ✅ | ✅ |
| **Clone method** | — | seed-icl-2.0, 5s audio | — | Custom Neural Voice, 300+句 | 一句话(5-15s) / 基础版(10-20min) | 大模型复刻, 任意音频 | 5-20s, 零样本, 99%相似 | 一句话(≈3s), 500万+已创建 |
| **Clone cost** | — | 150元/音色/年 | — | 企业定制报价 | API调用费 | 按次预付费 | ~$0.50/次 | 平台配额 |
| **Emotion** | Via SSML | Limited | Via style | Via SSML | Via SSML | ✅ Native 8种 | ✅ Native 8种 | ✅ Native |
| **Dialects** | ❌ | ❌ | ❌ | ❌ | Cantonese | 上海/河南/四川/湖南/贵州 | ❌ | ✅ 多方言 |
| **Languages** | 100+ | CN/EN | CN | 100+ | CN/EN/Cantonese | CN/EN/JA | 40+ | **130+** |
| **Streaming** | ✅ WebSocket | ✅ WebSocket | ✅ | ✅ SDK | ✅ WebSocket | ✅ WebSocket | ❌ (REST only) | ✅ WebSocket |
| **Setup difficulty** | 零配置 | 中等 | 简单 | 中等 | 中等 | 简单 | 简单 | 中等 |
| **API key** | None | VOLCENGINE_* | DASHSCOPE_KEY | AZURE_KEY | TENCENT_* | BAIDU_* | MINIMAX_KEY | XUNFEI_* |

## Voice Guide

### Edge / Azure Chinese Voices (20+)

| Voice | Gender | Style | Best for |
|-------|--------|-------|----------|
| `zh-CN-XiaoxiaoNeural` | Female | Warm, standard | **Default** — general purpose |
| `zh-CN-YunxiNeural` | Male | Energetic, youthful | Narration, vlog |
| `zh-CN-YunjianNeural` | Male | Mature, authoritative | Sports, news |
| `zh-CN-XiaoyiNeural` | Female | Lively, cheerful | Short video, Douyin |
| `zh-CN-YunyangNeural` | Male | Deep, professional | Documentary, voiceover |
| `zh-CN-XiaochenNeural` | Female | Calm, gentle | Meditation, relaxation |
| `zh-CN-YunfengNeural` | Male | Resonant, deep | Movie trailer |
| `zh-CN-YunxiaNeural` | Female | Cute, playful | Children's content |
| `zh-CN-XiaohanNeural` | Female | Soft, tender | Storytelling, romance |
| `zh-CN-YunyeNeural` | Male | Young, bright | Tech, startup |
| `zh-CN-YunzeNeural` | Male | Refined, cultured | Education, science |

### CosyVoice Voices (Alibaba)

| Voice | Style | Best for |
|-------|-------|----------|
| `longxiaochun_v3` | Female, lively | Short video, social media |
| `longxiaoxia_v3` | Female, gentle | Storytelling, audiobook |
| `longxiaobai_v3` | Female, cute | Children, animation |
| `longlaotie_v3` | Male, humorous | Comedy, casual content |
| `longchen_v3` | Male, calm | Business, professional |

### Doubao Voices (ByteDance)

| Voice | Style | Best for |
|-------|-------|----------|
| `BV001_streaming` | Female, standard | General Mandarin |
| `BV002_streaming` | Male, standard | General Mandarin |

### Tencent Cloud Voices (380+, selected)

| Voice ID | Style | Best for |
|----------|-------|----------|
| `101001` | Female, warm | General purpose |
| `101002` | Male, standard | General purpose |
| `101004` | Female, cute | Children, storytelling |
| `101005` | Male, mature | News, broadcasting |

### Baidu AI Voices (30+, selected)

| Voice ID | Style | Best for |
|----------|-------|----------|
| `0` | Female, standard | General purpose |
| `1` | Male, standard | General purpose |
| `3` | Male, emotional (度逍遥) | Storytelling, emotion |
| `4` | Female, emotional (度丫丫) | Narration, emotion |
| `5003` | Female, sweet (度琪琪) | Customer service |
| `5118` | Male, gentle | Natural conversation |

### MiniMax Voices (300+, selected)

| Voice ID | Style | Best for |
|----------|-------|----------|
| `female-shaonv` | Female, youthful (少女) | General |
| `male-qn-qingse` | Male, clear (青涩青年) | Vlog, narration |
| `female-yujie` | Female, mature (御姐) | Professional |
| `presenter_male` | Male, broadcast (播音男) | News, documentary |
| `presenter_female` | Female, broadcast (播音女) | News, documentary |

### Xunfei Voices (500+, selected)

| Voice ID | Style | Best for |
|----------|-------|----------|
| `xiaoyan` | Female, sweet (甜美) | General (default) |
| `xiaoyu` | Female, natural (温柔) | Audiobook, meditation |
| `xiaofeng` | Male, mature (稳重) | News, documentary |
| `xiaomei` | Female, lively (活泼) | Short video |
| `xiaoqian` | Female, gentle (亲切) | Customer service |

## Usage

### Basic Usage

```bash
# Default (Edge TTS, free, Xiaoxiao voice)
python ~/.claude/skills/ttsCN/scripts/tts.py "你好世界" output.wav

# Specific voice
python ~/.claude/skills/ttsCN/scripts/tts.py --voice zh-CN-YunxiNeural "欢迎收听今天的节目" welcome.wav

# Specific backend
python ~/.claude/skills/ttsCN/scripts/tts.py --platform doubao "今天天气真好" weather.wav
python ~/.claude/skills/ttsCN/scripts/tts.py --platform minimax "高品质语音合成" hq.wav

# Adjust speed
python ~/.claude/skills/ttsCN/scripts/tts.py --rate +15% "快速播报" fast.wav
python ~/.claude/skills/ttsCN/scripts/tts.py --rate -10% "慢速朗读" slow.wav
```

### From File

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py --input script.txt output.wav
```

### Output Format

```bash
# MP3 output (compressed, smaller file)
python ~/.claude/skills/ttsCN/scripts/tts.py --format mp3 "你好" hello.mp3
```

### Preview (Dry Run)

```bash
# Preview without making API call — no package installs needed
python ~/.claude/skills/ttsCN/scripts/tts.py --dry-run "这是一段测试文本"
```

### List Options

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py --list
```

## Requirements

```bash
# Core (always needed)
pip install edge-tts  # For Edge (default, free)

# Optional backends — install only what you use
pip install dashscope                              # CosyVoice
pip install requests                               # Doubao, MiniMax
pip install azure-cognitiveservices-speech          # Azure
pip install tencentcloud-sdk-python-tts             # Tencent Cloud
pip install baidu-aip                               # Baidu AI
pip install websocket-client                        # Xunfei
```

System requirement: `ffmpeg`

## Environment Variables

```bash
# Global defaults (optional)
export TTS_BACKEND="edge"
export TTS_VOICE="zh-CN-XiaoxiaoNeural"
export TTS_RATE="+5%"

# ByteDance Volcano Ark (Doubao)
export VOLCENGINE_APPID="your_app_id"
export VOLCENGINE_ACCESS_TOKEN="your_token"

# Alibaba DashScope (CosyVoice)
export DASHSCOPE_API_KEY="your_api_key"

# Microsoft Azure
export AZURE_SPEECH_KEY="your_key"
export AZURE_SPEECH_REGION="eastasia"

# Tencent Cloud
export TENCENT_SECRET_ID="your_secret_id"
export TENCENT_SECRET_KEY="your_secret_key"

# Baidu AI
export BAIDU_APP_ID="your_app_id"
export BAIDU_API_KEY="your_api_key"
export BAIDU_SECRET_KEY="your_secret_key"

# MiniMax
export MINIMAX_API_KEY="your_api_key"

# iFlytek Xunfei
export XUNFEI_APP_ID="your_app_id"
export XUNFEI_API_KEY="your_api_key"
export XUNFEI_API_SECRET="your_api_secret"
```

Get API Keys:
- Volcano Ark: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
- DashScope: https://bailian.console.aliyun.com/
- Azure: https://portal.azure.com/
- Tencent Cloud: https://console.cloud.tencent.com/tts
- Baidu AI: https://console.bce.baidu.com/ai/#/ai/speech/overview
- MiniMax: https://platform.minimaxi.com
- Xunfei: https://www.xfyun.cn

## Config File (Optional)

Create `~/.ttsCN.json` for personal defaults, or `.ttsCN.json` in a project directory:

```json
{
  "backend": "minimax",
  "voice": "female-shaonv",
  "rate": "+10%"
}
```

Priority (highest first):
1. CLI arguments (`--platform`, `--voice`, `--rate`)
2. Project config (`.ttsCN.json` in current directory)
3. User config (`~/.ttsCN.json`)
4. Environment variables (`TTS_BACKEND`, `TTS_VOICE`, `TTS_RATE`)
5. Built-in defaults

## Examples

### Quick Narration (Free, Zero Setup)

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py \
  "人工智能正在改变我们的生活方式，从智能助手到自动驾驶，技术革新无处不在。" \
  ai_narration.wav
```

### Douyin Style Short Video Voice

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform doubao --voice BV001_streaming --rate +10% \
  "家人们，今天给大家推荐一个超好用的神器！" \
  douyin_style.wav
```

### Male Documentary Voice

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --voice zh-CN-YunyangNeural \
  "在遥远的非洲大草原上，生命的故事每天都在上演。" \
  documentary.wav
```

### Audiobook from Script File (CosyVoice)

```bash
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform cosyvoice --voice longxiaoxia_v3 \
  --input chapter1.txt chapter1.wav
```

### Bulk Generation at Lowest Cost (Tencent)

```bash
TENCENT_SECRET_ID="xxx" TENCENT_SECRET_KEY="xxx" \
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform tencent --voice 101001 \
  --input course_script.txt course_audio.wav
```

### Premium Quality with Emotion (MiniMax)

```bash
MINIMAX_API_KEY="xxx" \
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform minimax --voice female-shaonv \
  "这是一段充满感情的语音合成演示。" premium.wav
```

### Professional Education Voice (Xunfei)

```bash
XUNFEI_APP_ID="xxx" XUNFEI_API_KEY="xxx" XUNFEI_API_SECRET="xxx" \
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform xunfei --voice xiaoyu \
  "今天我们来讲一个有趣的故事..." education.wav
```

### Emotion Synthesis (Baidu)

```bash
BAIDU_APP_ID="xxx" BAIDU_API_KEY="xxx" BAIDU_SECRET_KEY="xxx" \
python ~/.claude/skills/ttsCN/scripts/tts.py \
  --platform baidu --voice 3 \
  "今天真是令人兴奋的一天！" emotion.wav
```
