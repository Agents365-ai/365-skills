---
name: ttsCN
description: Multi-platform Chinese & multilingual TTS text-to-speech via Edge/Doubao/CosyVoice/Azure/Tencent/Baidu/MiniMax/Xunfei plus ElevenLabs/OpenAI/Google — 11 backends, word-level timestamps, [PAUSE:x] pause markers, pinyin pronunciation overrides
author: Agents365-ai
version: 1.4.0
created: 2026-07-08
updated: 2026-07-15
homepage: https://github.com/Agents365-ai/ttsCN
metadata: {"openclaw":{"requires":{"bins":["python3","ffmpeg"]},"emoji":"🔊"}}
---

# ttsCN — Multi-Platform Chinese TTS Skill

## Overview

Generate natural speech audio from text. **11 backends** — 8 China-friendly clouds plus 3 international (ElevenLabs / OpenAI / Google).

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
| 9 | **ElevenLabs** | Paid tiers (from $5/mo) | Top voice quality, instant cloning |
| 10 | **OpenAI TTS** | ~$15-30/M chars | 6 voices, multilingual, simple REST |
| 11 | **Google Cloud TTS** | ~$16/M chars (free tier) | 220+ voices, 40+ languages |

New in 1.4: **word-level timestamps** (edge/azure), **[PAUSE:x] + sound-tag markers** (all platforms), **--phonemes pronunciation overrides** (azure/minimax).

**Cross-platform**: Windows, macOS, Linux

## When to Use This Skill

Automatically activate this skill when:
- User wants to convert Chinese text to speech audio
- Generating voice narration or voiceover for videos
- Creating audiobook or podcast audio from text
- User asks to compare TTS providers, choose a TTS backend, or see what voices are available
- User asks about TTS pricing, features, or which provider supports cloning/SSML/dialects
- User mentions any of: TTS, text-to-speech, 语音合成, 文字转语音, Edge TTS, Doubao TTS, CosyVoice, 火山引擎, 阿里云语音, Azure TTS, 腾讯云TTS, 百度语音, MiniMax, 讯飞语音, ElevenLabs, OpenAI TTS, Google Cloud TTS
- User needs word-level timestamps/subtitles, pause control, or fixing mispronounced Chinese characters (多音字)
- Any task where Chinese text-to-speech would be helpful

## Provider Comparison Page

**When the user wants to browse, compare, or choose a TTS provider, ALWAYS open the
local HTML comparison page in their browser FIRST** — it's a visual, filterable table
that is much faster to scan than reading text output.

All paths in this document are relative to this skill's root directory (the
directory containing this SKILL.md) — resolve them against it.

```bash
# Open the comparison page (path relative to this skill's directory)
open docs/providers.html
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
open docs/providers.html
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
| **Best quality / cloning** | minimax | female-shaonv | speech-2.6-hd, voice design |
| **Education / pro** | xunfei | xiaoyan | MOS 4.8, 500+ voices |
| **Male narration** | edge | zh-CN-YunxiNeural | Energetic male voice |
| **Documentary** | azure | zh-CN-YunyangNeural | Deep, professional male |
| **Children's content** | edge | zh-CN-XiaomengNeural | Bright, youthful female |
| **Cost-sensitive** | edge | zh-CN-XiaoxiaoNeural | Completely free |
| **English, top quality** | elevenlabs | 21m00Tcm4TlvDq8ikWAM (Rachel) | Best-in-class English voices |
| **English, simple/cheap** | openai | alloy | tts-1-hd, one env var |
| **English, enterprise** | google | en-US-Neural2-F | 220+ voices, free tier |

### Full Capability Comparison

| Capability | Edge | Doubao | CosyVoice | Azure | Tencent | Baidu | MiniMax | Xunfei |
|------------|------|--------|-----------|-------|---------|-------|---------|--------|
| **Cost (per 10K chars)** | Free | ~1元 | ~2元 | ~$1/M chars | **0.75元** | 灵活 | ~$1 | ~2元 |
| **Built-in voices** | 20+ | 8 | 7 | 20+ | 380+ | 30+ | 300+ | 500+ |
| **Max chars / chunk** | 2000 | 280 | 400 | 2000 | 150 | 500 | **3000** | 200 |
| **Max duration / chunk** | ~10 min | ~1 min | ~2 min | ~10 min | ~30 s | ~2 min | ~5 min | ~1 min |
| **SSML** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Voice cloning** | ❌ | ✅ | ✅ **CLI built-in** | ✅ (gated) | ✅ | ✅ | ✅ **CLI built-in** | ✅ |
| **Clone method** | — | seed-icl-2.0, 5s audio | 音色复刻, 10-20s URL 音频 | Custom Neural Voice, 300+句 | 一句话(5-15s) / 基础版(10-20min) | 大模型复刻, 任意音频 | 10s-5min音频, 零样本 | 一句话(≈3s), 500万+已创建 |
| **Clone cost** | — | 150元/音色/年 | **免费**(合成正常计费) | 企业定制报价 | API调用费 | 按次预付费 | $1.5/音色(国内¥9.9首用) | 平台配额 |
| **Emotion** | Via SSML | Limited | Via style | Via SSML | Via SSML | ✅ Native 8种 | ✅ Native 8种 | ✅ Native |
| **Dialects** | ❌ | ❌ | ❌ | ❌ | Cantonese | 上海/河南/四川/湖南/贵州 | ❌ | ✅ 多方言 |
| **Languages** | 100+ | CN/EN | CN | 100+ | CN/EN/Cantonese | CN/EN/JA | 40+ | **130+** |
| **Streaming** | ✅ WebSocket | ✅ WebSocket | ✅ | ✅ SDK | ✅ WebSocket | ✅ WebSocket | ❌ (REST only) | ✅ WebSocket |
| **Setup difficulty** | 零配置 | 中等 | 简单 | 中等 | 中等 | 简单 | 简单 | 中等 |
| **API key** | None | VOLCENGINE_* | DASHSCOPE_KEY | AZURE_KEY | TENCENT_* | BAIDU_* | MINIMAX_KEY | XUNFEI_* |

### International Backends (need international network access)

| Capability | ElevenLabs | OpenAI TTS | Google Cloud TTS |
|------------|-----------|-----------|------------------|
| **Cost (approx.)** | Paid tiers, from $5/mo | ~$15-30/M chars | ~$16/M chars, 1M free/mo |
| **Default voice** | `21m00Tcm4TlvDq8ikWAM` (Rachel) | `alloy` | `en-US-Neural2-F` |
| **Voices** | 20+ preset + cloning | 6 | 220+ |
| **Languages** | 32 (multilingual v2) | 50+ auto-detect | 40+ (incl. cmn-CN) |
| **Voice cloning** | ✅ Instant (paid) | ❌ | ❌ |
| **API key** | ELEVENLABS_API_KEY | OPENAI_API_KEY | GOOGLE_TTS_API_KEY |
| **Model / language env** | ELEVENLABS_MODEL (default `eleven_multilingual_v2`) | OPENAI_TTS_MODEL (default `tts-1-hd`) | GOOGLE_TTS_LANGUAGE (default: derived from voice name, e.g. `en-US`) |

## Voice Cloning (`clone` command)

Create a custom voice from reference audio, store it under a name, then use
the name anywhere `--voice` is accepted. Built-in for **minimax** (local file
OK, 10s-5min audio, paid: ~$1.5/voice global site or ¥9.9 on first use China
site; a new clone is TEMPORARY until its first real synthesis — use it within
7 days [global site] / 48 h [China site] of creation or MiniMax deletes it,
previews don't count; permanent after first use) and **cosyvoice** (enrollment
free, audio must be a PUBLIC http(s) URL, 10-20s, voice expires after 1 year
unused).

```bash
# MiniMax — local file, paid, must confirm with --yes
python3 scripts/tts.py clone create --platform minimax --audio my_voice.wav --name myvoice --yes

# CosyVoice — free, but --audio must be a public URL; --target-model must
# match the synthesis model (default: $COSYVOICE_MODEL or cosyvoice-v3-flash)
python3 scripts/tts.py clone create --platform cosyvoice --audio https://example.com/my.wav --name myvoice

# Manage
python3 scripts/tts.py clone list
python3 scripts/tts.py clone delete --name myvoice [--remote]   # --remote: cosyvoice only

# Use it — the stored name resolves to the platform voice_id automatically
python3 scripts/tts.py "用我的声音说这句话" out.wav --platform minimax --voice myvoice
```

Rules the agent MUST follow:
- MiniMax creation is paid — never run `clone create --platform minimax`
  without the user's explicit confirmation (the CLI enforces `--yes`).
- Only clone the user's own voice or one they are authorized to use — both
  platforms contractually prohibit cloning third parties without consent.
- Reference audio: clean single-speaker speech, no BGM, 10-20s is ideal.
- Named voices live in `~/.ttsCN.json` under `cloned_voices`.

Other platforms (Doubao/Tencent/Baidu/Xunfei/Azure) support cloning via
their consoles — the resulting voice id also works as a plain `--voice`.

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

### International Voices (ElevenLabs / OpenAI / Google, selected)

| Backend | Voice ID | Style | Best for |
|---------|----------|-------|----------|
| elevenlabs | `21m00Tcm4TlvDq8ikWAM` (Rachel) | Female, calm | General English (default) |
| openai | `alloy` | Neutral | General (default) |
| openai | `nova` / `onyx` | Female bright / Male deep | Narration |
| google | `en-US-Neural2-F` | Female, natural | General English (default) |
| google | `cmn-CN-Wavenet-A` | Female, Mandarin | Chinese via Google |

## Usage

### Basic Usage

```bash
# Default (Edge TTS, free, Xiaoxiao voice)
python3 scripts/tts.py "你好世界" output.wav

# Specific voice
python3 scripts/tts.py --voice zh-CN-YunxiNeural "欢迎收听今天的节目" welcome.wav

# Specific backend
python3 scripts/tts.py --platform doubao "今天天气真好" weather.wav
python3 scripts/tts.py --platform minimax "高品质语音合成" hq.wav

# Adjust speed
python3 scripts/tts.py --rate +15% "快速播报" fast.wav
python3 scripts/tts.py --rate -10% "慢速朗读" slow.wav
```

### From File

```bash
python3 scripts/tts.py --input script.txt output.wav
```

### Output Format

```bash
# MP3 output (compressed, smaller file)
python3 scripts/tts.py --format mp3 "你好" hello.mp3
```

### Preview (Dry Run)

```bash
# Preview without making API call — no package installs needed
python3 scripts/tts.py --dry-run "这是一段测试文本"
```

### List Options

```bash
python3 scripts/tts.py --list
```

## Expressiveness Markers

Input text may contain markers on **any** platform — they are rendered natively
where supported and stripped everywhere else (never read aloud). The chunker
never splits inside a `[...]` marker.

| Marker | Syntax | azure | minimax | all other platforms |
|--------|--------|-------|---------|---------------------|
| Pause | `[PAUSE:x]` — x = seconds, 0.01-99.99 | `<break time="xs"/>` (SSML) | `<#x#>` | stripped |
| Sound tags | `(laughs)` `(chuckle)` `(sighs)` `(breath)` `(inhale)` `(exhale)` `(coughs)` | stripped | voiced **only if** `MINIMAX_MODEL` starts with `speech-2.8` (else stripped + stderr warning) | stripped |

```bash
python3 scripts/tts.py --platform azure \
  "大家好。[PAUSE:0.8] 今天我们聊一个新话题。" out.wav

MINIMAX_MODEL=speech-2.8-hd python3 scripts/tts.py --platform minimax \
  "这也太好笑了 (laughs) 好，我们继续。" out.wav
```

## Pronunciation Overrides (`--phonemes`)

Fix polyphonic Chinese characters (多音字) with a JSON dict mapping words to
space-separated pinyin — tone-numbered (`hang2 zhang3`) or tone-marked
(`háng zhǎng`). Keys starting with `_` are comments.

```json
{
  "_comment": "pronunciation overrides for bank-themed script",
  "行长": "hang2 zhang3",
  "重庆": "chóng qìng"
}
```

```bash
python3 scripts/tts.py --platform azure --phonemes phonemes.json \
  "行长在重庆开会。" out.wav
```

Per-platform: **azure** → SSML `<phoneme alphabet="sapi">` tags; **minimax** →
inline pinyin annotations like `重(chong2)庆(qing4)`; all other platforms
silently ignore the flag.

## Requirements

```bash
# Core (always needed)
pip install edge-tts  # For Edge (default, free)

# Optional backends — install only what you use
pip install dashscope                              # CosyVoice
pip install requests                               # Doubao, MiniMax, ElevenLabs, OpenAI, Google
pip install azure-cognitiveservices-speech          # Azure
pip install tencentcloud-sdk-python-tts             # Tencent Cloud
pip install baidu-aip chardet                       # Baidu AI
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
export TTS_STYLE="gentle"              # optional: mstts:express-as style; unset = plain prosody

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

# ElevenLabs (international)
export ELEVENLABS_API_KEY="your_api_key"
export ELEVENLABS_MODEL="eleven_multilingual_v2"   # optional, this is the default

# OpenAI TTS (international)
export OPENAI_API_KEY="your_api_key"
export OPENAI_TTS_MODEL="tts-1-hd"                 # optional, this is the default

# Google Cloud TTS (international)
export GOOGLE_TTS_API_KEY="your_api_key"
export GOOGLE_TTS_LANGUAGE="en-US"                 # optional, auto-derived from voice name
```

Get API Keys:
- Volcano Ark: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
- DashScope: https://bailian.console.aliyun.com/
- Azure: https://portal.azure.com/
- Tencent Cloud: https://console.cloud.tencent.com/tts
- Baidu AI: https://console.bce.baidu.com/ai/#/ai/speech/overview
- MiniMax: https://platform.minimaxi.com
- Xunfei: https://www.xfyun.cn
- ElevenLabs: https://elevenlabs.io/app/settings/api-keys
- OpenAI: https://platform.openai.com/api-keys
- Google Cloud: https://console.cloud.google.com/apis/credentials

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
python3 scripts/tts.py \
  "人工智能正在改变我们的生活方式，从智能助手到自动驾驶，技术革新无处不在。" \
  ai_narration.wav
```

### Douyin Style Short Video Voice

```bash
python3 scripts/tts.py \
  --platform doubao --voice BV001_streaming --rate +10% \
  "家人们，今天给大家推荐一个超好用的神器！" \
  douyin_style.wav
```

### Male Documentary Voice

```bash
python3 scripts/tts.py \
  --voice zh-CN-YunyangNeural \
  "在遥远的非洲大草原上，生命的故事每天都在上演。" \
  documentary.wav
```

### Audiobook from Script File (CosyVoice)

```bash
python3 scripts/tts.py \
  --platform cosyvoice --voice longxiaoxia_v3 \
  --input chapter1.txt chapter1.wav
```

### Bulk Generation at Lowest Cost (Tencent)

```bash
TENCENT_SECRET_ID="xxx" TENCENT_SECRET_KEY="xxx" \
python3 scripts/tts.py \
  --platform tencent --voice 101001 \
  --input course_script.txt course_audio.wav
```

### Premium Quality with Emotion (MiniMax)

```bash
MINIMAX_API_KEY="xxx" \
python3 scripts/tts.py \
  --platform minimax --voice female-shaonv \
  "这是一段充满感情的语音合成演示。" premium.wav
```

### Professional Education Voice (Xunfei)

```bash
XUNFEI_APP_ID="xxx" XUNFEI_API_KEY="xxx" XUNFEI_API_SECRET="xxx" \
python3 scripts/tts.py \
  --platform xunfei --voice xiaoyu \
  "今天我们来讲一个有趣的故事..." education.wav
```

### Emotion Synthesis (Baidu)

```bash
BAIDU_APP_ID="xxx" BAIDU_API_KEY="xxx" BAIDU_SECRET_KEY="xxx" \
python3 scripts/tts.py \
  --platform baidu --voice 3 \
  "今天真是令人兴奋的一天！" emotion.wav
```

## Agent-Native CLI Reference

ttsCN follows the [agent-native-design](https://github.com/Agents365-ai/agent-native-design) contract.
It serves **humans** (readable terminal output), **AI agents** (structured JSON on stdout), and
**orchestrators** (distinct exit codes + idempotency) simultaneously.

### JSON Mode

```bash
# Explicit JSON mode
tts.py --format json "你好" out.wav

# Auto-detect: pipe to jq → JSON automatically
tts.py --list | jq .data.backends[0].name

# Error envelope always structured
tts.py --format json --platform doubao "test" out.wav
# → {"ok":false, "error":{"code":"auth_missing_env","message":"...","retryable":false,...}}
```

### Output Envelope

```json
// Success
{"ok":true, "data":{...}, "meta":{"version":"...","schema_version":"1.2.0","timestamp":"...","ms":123}}

// Error
{"ok":false, "error":{"code":"auth_missing_env","message":"VOLCENGINE_APPID not set","retryable":false,"field":"VOLCENGINE_APPID","backend":"doubao"}, "meta":{...}}
```

### Word Boundaries (edge / azure only)

For **edge** and **azure**, the success envelope includes native word-level
timestamps under `data.word_boundaries` — absolute seconds within the output
file, ascending, 3-decimal rounding. The key is absent for other platforms.

```json
{"ok":true, "data":{
  "output_file": "out.wav",
  "word_boundaries": [
    {"text": "你好", "offset_sec": 0.1,   "duration_sec": 0.45},
    {"text": "世界", "offset_sec": 0.562, "duration_sec": 0.5}
  ]
}}
```

Use these for subtitle/SRT generation or beat-synced animation without a
separate forced-alignment pass.

### Exit Codes

| Code | Meaning | Agent action |
|------|---------|-------------|
| **0** | Success | Parse `data`, proceed |
| **1** | Internal / runtime error | Report to user, do not retry |
| **2** | Validation / fixable error (bad input, missing package) | Fix input or install package, retry allowed |
| **3** | Auth / missing credentials | Ask user for API key, do not retry |
| **4** | Backend API error | Retry with backoff |

### Schema Introspection

```bash
tts.py schema backends              # All 11 backends (compact by default)
tts.py schema backends --full       # All fields (22 per backend)
tts.py schema backends.doubao       # Single backend full detail
tts.py schema voices                # All voice presets per backend
tts.py schema tags                  # Tag definitions
tts.py schema version               # Version + providers data freshness

# Field filtering for low-token-cost queries
tts.py schema backends --fields name,cost,supports_clone,supports_ssml
```

### Idempotency

```bash
# Orchestrators: retried calls return cached result — no double-billing
tts.py --idempotency-key "daily-podcast-2026-07-08" --input script.txt out.wav

# Cache at ~/.ttscn_idem/, 7-day TTL, SHA-256 keyed
```

### Agent Compatibility Flags

```bash
# No-ops accepted for agent runtime compatibility (ttsCN never prompts)
tts.py --yes --no-input "text" out.wav
```
