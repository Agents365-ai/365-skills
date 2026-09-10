---
name: yt2bb
description: Use when the user wants to repurpose a YouTube video for Bilibili, add bilingual (English-Chinese) subtitles to a video, or create hardcoded subtitle versions for Chinese platforms.
license: MIT
homepage: https://github.com/Agents365-ai/365-skills
compatibility: Requires Python 3, ffmpeg, yt-dlp, whisper (openai-whisper) on PATH. Self-check steps that need vision are gracefully skipped if unavailable.
platforms: [macos, linux, windows]
allowed-tools: Bash(python3:*) Bash(ffmpeg:*) Bash(whisper:*) Bash(yt-dlp:*) Bash(git:*) Read Write Edit
metadata: {"openclaw":{"requires":{"bins":["python3","ffmpeg","yt-dlp","whisper"]},"emoji":"🎬","os":["darwin","linux","win32"],"install":[{"id":"brew-ffmpeg","kind":"brew","formula":"ffmpeg","bins":["ffmpeg"],"label":"Install ffmpeg via Homebrew","os":["darwin"]},{"id":"apt-ffmpeg","kind":"apt","package":"ffmpeg","bins":["ffmpeg"],"label":"Install ffmpeg via apt","os":["linux"]},{"id":"brew-ytdlp","kind":"brew","formula":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp via Homebrew","os":["darwin"]},{"id":"pip-ytdlp","kind":"pip","package":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp via pip","os":["linux","win32"]},{"id":"pip-whisper","kind":"pip","package":"openai-whisper","bins":["whisper"],"label":"Install openai-whisper via pip"}]},"clawhub":{"requires":{"bins":["python3","ffmpeg","yt-dlp","whisper"]},"category":"media","install":[{"id":"brew-ffmpeg","kind":"brew","formula":"ffmpeg","bins":["ffmpeg"],"label":"Install ffmpeg via Homebrew","os":["darwin"]},{"id":"apt-ffmpeg","kind":"apt","package":"ffmpeg","bins":["ffmpeg"],"label":"Install ffmpeg via apt","os":["linux"]},{"id":"brew-ytdlp","kind":"brew","formula":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp via Homebrew","os":["darwin"]},{"id":"pip-ytdlp","kind":"pip","package":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp via pip","os":["linux","win32"]},{"id":"pip-whisper","kind":"pip","package":"openai-whisper","bins":["whisper"],"label":"Install openai-whisper via pip"}]},"hermes":{"tags":["youtube","bilibili","subtitles","bilingual","video","localization","whisper","yt-dlp"],"category":"media","requires_tools":["python3","ffmpeg","yt-dlp","whisper"],"related_skills":["ffmpeg","video-podcast-maker"]},"codex":{"requires":{"bins":["python3","ffmpeg","yt-dlp","whisper"]},"allowed-tools":["bash","read","write","edit"]},"claude-code":{"allowed-tools":"Bash(python3:*) Bash(ffmpeg:*) Bash(whisper:*) Bash(yt-dlp:*) Bash(git:*) Read Write Edit"},"pi":{"requires":{"bins":["python3","ffmpeg","yt-dlp","whisper"]},"allowed-tools":["bash","read","write","edit"]},"skillsmp":{"topics":["claude-code","claude-code-skill","claude-skills","agent-skills","skillsmp","openclaw","openclaw-skills","skill-md","pi-coding-agent","youtube","bilibili","subtitles","video"]},"author":"Agents365-ai","version":"2.6.2"}
---

# yt2bb — YouTube to Bilibili Video Repurposing

## Overview

Six-step pipeline: download → transcribe → translate → merge → burn subtitles → generate publish info. Produces a video with hardcoded bilingual (EN/ZH) subtitles and a `publish_info.md` with Bilibili upload metadata.

## When to Use

- User provides a YouTube URL (single video or playlist) and wants a Bilibili-ready version
- User needs bilingual EN-ZH subtitles burned into video
- User wants to repurpose English video content for Chinese audience

## Quick Reference

| Step | Tool | Command | Output |
| ------ | ------ | --------- | -------- |
| 0. Update | `git` | Auto-check for skill updates | — |
| 1. Download | `yt-dlp` | `yt-dlp --cookies-from-browser chrome -f ... -o ...` | `{slug}.mp4` |
| 2. Transcribe | `whisper`* | `srt_utils.py check-whisper` then transcribe | `{slug}_{lang}.srt` |
| 2.5 Validate | `srt_utils.py` | `srt_utils.py validate / fix` | `{slug}_{lang}.srt` (fixed) |
| 3. Translate | AI | SRT-aware batch translation | `{slug}_zh.srt` |
| 4. Merge | `srt_utils.py` | `srt_utils.py merge ...` | `{slug}_bilingual.srt` |
| 4.5 Style | `srt_utils.py` | `srt_utils.py to_ass --preset netflix\|clean\|glow` | `{slug}_bilingual.ass` |
| 5. Burn | `ffmpeg` | `ffmpeg -c:v libx264 -vf ass=...` | `{slug}_bilingual.mp4` |
| 6. Publish | AI | Analyze content, generate metadata | `publish_info.md` |

## Resolve the skill directory

Resolve `SKILL_DIR` for use by later pipeline steps:

```bash
# Find the skill dir: a 'yt2bb' folder that actually contains SKILL.md.
# Works whether installed flat (~/.claude/skills/yt2bb) or pulled from this repo (skills/yt2bb).
SKILL_DIR="$(find ~/.claude/skills ~/.openclaw/skills ~/.hermes/skills ~/.pi/agent/skills ~/.agents/skills ~/myagents/myskills -type d -name 'yt2bb' -exec test -f '{}/SKILL.md' \; -print 2>/dev/null | head -1)"
```

## Pipeline Details

### Step 1: Download

**Single video:**

```bash
slug="video-name"  # or: slug=$(python3 "$SKILL_DIR/srt_utils.py" slugify "Video Title")
mkdir -p "${slug}"
yt-dlp --cookies-from-browser chrome \
  -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" \
  -o "${slug}/${slug}.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Playlist / series:**

```bash
yt-dlp --cookies-from-browser chrome \
  -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" \
  -o "%(playlist_index)03d-%(title)s/%(playlist_index)03d-%(title)s.mp4" \
  "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

After downloading, rename each folder to a clean slug and run Steps 2–6 for each video sequentially.

- `-f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]"`: ensure mp4 output, avoid webm
- `%(playlist_index)03d`: zero-padded index to preserve playlist order
- If `--cookies-from-browser` fails, export cookies first — see Troubleshooting

### Step 2: Transcribe

**First run the environment check** to detect your platform and get a tailored whisper command:

```bash
python3 "$SKILL_DIR/srt_utils.py" check-whisper
```

This auto-detects OS, GPU (CUDA/Metal/CPU), memory, and installed backends, then recommends the best backend + model for your hardware. If memory detection is unavailable, it falls back conservatively instead of assuming a low-memory machine. Use the command it prints.

**Manual fallback** (openai-whisper, works everywhere):

```bash
src_lang="en"      # Change to ja/ko/es/etc. based on source video
whisper_model="medium"  # check-whisper recommends the best model for your hardware
whisper "${slug}/${slug}.mp4" \
  --model "$whisper_model" \
  --language "$src_lang" \
  --word_timestamps True \
  --condition_on_previous_text False \
  --output_format srt \
  --max_line_width 40 --max_line_count 1 \
  --output_dir "${slug}"
mv "${slug}/${slug}.srt" "${slug}/${slug}_${src_lang}.srt"
```

**Supported backends:**

| Backend | Best for | Install |
| --------- | ---------- | --------- |
| `mlx-whisper` | macOS Apple Silicon (fastest) | `pip install mlx-whisper` |
| `whisper-ctranslate2` | Windows/Linux CUDA, or CPU (~4x faster) | `pip install whisper-ctranslate2` |
| `openai-whisper` | Universal fallback | `pip install openai-whisper` |

**Model selection** (auto-recommended by `check-whisper`):

- `tiny` — fast draft, low accuracy, CPU-friendly (~1 GB)
- `medium` — **default**, good balance (~5 GB)
- `large-v3` — best accuracy, recommended for JA/KO/ZH source (~10 GB)

**Notes:**

- `--language`: explicitly set to avoid misdetection; supports `en`, `ja`, `ko`, `es`, etc.
- `--word_timestamps True`: more precise subtitle timing
- `--condition_on_previous_text False`: prevent hallucination loops
- If output is garbled or repeated, add anti-hallucination flags — see Troubleshooting

### Step 2.5: Validate & Fix (optional)

```bash
python3 "$SKILL_DIR/srt_utils.py" validate "${slug}/${slug}_${src_lang}.srt"
# If issues found:
python3 "$SKILL_DIR/srt_utils.py" fix "${slug}/${slug}_${src_lang}.srt" "${slug}/${slug}_${src_lang}.srt"
```

### Step 3: Translate

Read `{slug}_{src_lang}.srt` and translate to Chinese. **Critical rules:**

These rules are modeled on the Netflix Simplified Chinese Timed Text Style Guide; follow them to produce broadcast-grade subtitles.

1. **Keep SRT format intact** — preserve index numbers, timestamps (`-->` lines) exactly as-is
2. **1:1 entry mapping** — every source entry must produce exactly one translated entry (same count)
3. **Optimize for bottom subtitles** — keep each Chinese entry to **1 line whenever possible** so the final bilingual subtitle stays compact near the bottom of the frame
4. **Max 16 full-width characters per line** (Netflix SC spec). Prefer 12–16; if a cue is very short (< 1 s) compress further so reading speed stays ≤ 9 characters/second
5. **Shorten with judgment, not mechanically** — remove filler words, repeated subjects, weak interjections, and redundant politeness before dropping key meaning
6. **Match subtitle duration** — the line must feel readable within the time on screen; if the cue is very short, compress more aggressively
7. **No trailing punctuation** on Chinese cues — drop ending `。`, `！`, `？`; keep mid-sentence `，`, `、`, `；` only when they add clarity
8. **Use full-width Chinese punctuation** inside cues (`，。！？、；：`); use **「」** for inner quotes, not `""` or `''`
9. **Half-width digits and Latin** — numbers, units, product names, and code identifiers stay half-width (`GPT-4`, `30fps`, `2026`); only punctuation is full-width
10. **Each cue reads as one complete, self-contained line** — every displayed line should be a whole sentence or a short unit of meaning, never a truncated clause, exactly like the bilingual subtitles you see in movies or TV dramas. In practice: don't break after function words (`的`, `了`, `吗`, `呢`, `吧`, `啊`); don't split an English phrasal unit across a break; keep modifiers with their heads
11. **Keep terminology consistent** — technical terms, names, product names, and recurring phrases should be translated the same way across batches. Maintain an inline glossary if needed
12. **Adapt, don't transliterate** — preserve register, tone, and intent over literal word matching; idioms become natural Chinese equivalents
13. **Translate in batches of 10 entries** — output each batch in valid SRT format, then continue
14. **Do NOT merge or split entries** — maintain original segmentation
15. Save as `{slug}/{slug}_zh.srt`

### Step 4: Merge

```bash
python3 "$SKILL_DIR/srt_utils.py" merge \
  "${slug}/${slug}_${src_lang}.srt" "${slug}/${slug}_zh.srt" "${slug}/${slug}_bilingual.srt"
```

### Step 4.25: Netflix Lint (recommended)

Run `lint` on the merged bilingual SRT to catch Netflix Timed Text Style Guide violations that `validate` doesn't cover — reading speed (CPS), per-line length, inter-cue gaps, and line count.

```bash
python3 "$SKILL_DIR/srt_utils.py" lint "${slug}/${slug}_bilingual.srt"
```

**Defaults (all overridable via flags):**

| Rule | Threshold | Flag |
| ------ | ----------- | ------ |
| Reading speed (English) | ≤ 17 CPS | `--max-cps-en` |
| Reading speed (Simplified Chinese) | ≤ 9 CPS | `--max-cps-zh` |
| Min cue duration | 833 ms (5/6 s) | `--min-duration-ms` |
| Max cue duration | 7000 ms | `--max-duration-ms` |
| Min inter-cue gap | 83 ms (2 frames @ 24 fps) | `--min-gap-ms` |
| Max chars/line (English) | 42 | `--max-chars-en` |
| Max chars/line (Chinese, full-width) | 16 | `--max-chars-zh` |
| Max lines per cue | 2 | — |

**Severity model:**

- **Errors** (exit code 2): duration out of bounds, CPS over limit, > 2 lines per cue. These break Netflix acceptance and should be fixed before burning.
- **Warnings** (exit 0 unless errors also exist): per-line length, tight gaps. These are recommendations — address if feasible, but they don't block delivery.

**When CPS errors fire**, the fix is almost always upstream — go back to Step 3 and rewrite the offending Chinese entry to fit the time window. Do **not** solve CPS by extending the cue past the source's spoken duration.

**Agent-friendly output:**

```bash
python3 "$SKILL_DIR/srt_utils.py" lint "${slug}/${slug}_bilingual.srt" --format json
```

Returns `{ok, error_count, warning_count, issues: [{index, code, severity, message}, ...]}` for programmatic filtering.

### Step 4.5: Style — Convert to ASS

Convert the bilingual SRT to an ASS file. ASS enables per-line color, font size, and glow effects that are impossible with SRT `force_style`. Layout rule: **subtitles always stay at the bottom**. Default stack: ZH on the upper line of the bottom stack, EN on the lower line. The presets are tuned to keep the block readable while reducing overlap risk with lower-screen content.

> **IMPORTANT — Ask before proceeding.** Present the preset table below to the user and ask which style they prefer. Do NOT silently pick a default. If the user has no preference, use `clean`.

**Available presets:**

| Preset | Look | Best for |
| -------- | ------ | ---------- |
| `netflix` | **Pure white text, thin black outline, soft drop shadow, no box** — modeled on the Netflix Timed Text Style Guide | Professional, broadcast-grade look. Best default for documentaries, interviews, long-form content, and anything that should feel "streaming-platform native". Use with `--font "Source Han Sans SC"` on Linux / `"PingFang SC"` on macOS for closest Netflix Sans feel |
| `clean` | **Yellow text on gray box** — golden ZH + light yellow EN, semi-transparent light gray background | Readability safety net for busy or mixed-brightness footage where `netflix`'s outline-only text could get visually lost. The gray box guarantees a readable contrast pad |
| `glow` | **Yellow ZH + white EN with colored glow** — bright yellow ZH + white EN, blurred outer glow, no background box | Entertainment, vlogs, energetic edits. Most eye-catching, but weakest on bright or busy backgrounds |

**Example prompt to user:**
> 字幕有三套样式可选：
>
> 1. `netflix` — 纯白字体 + 细黑描边 + 柔和阴影（默认推荐，Netflix 专业观感，适合纪录片/访谈/长内容）
> 2. `clean` — 黄色字体 + 灰色半透明底框（亮背景或花背景的兜底选项，底框保证对比度）
> 3. `glow` — 黄色/白色字体 + 彩色外发光（更抢眼，适合娱乐/Vlog）
> 4. **自定义** — 提供 `.ass` 样式文件，完全控制字体、颜色、大小（可用 [Aegisub](https://aegisub.org/) 可视化编辑）
>
> 选哪个？默认推荐 `netflix`；如果画面特别花哨或底部信息多，可改用 `clean`。

```bash
# Netflix-grade default (white + outline + soft shadow), ZH on top
python3 "$SKILL_DIR/srt_utils.py" to_ass \
  "${slug}/${slug}_bilingual.srt" "${slug}/${slug}_bilingual.ass" \
  --preset netflix

# Gray-box fallback for busy backgrounds, EN on top
python3 "$SKILL_DIR/srt_utils.py" to_ass \
  "${slug}/${slug}_bilingual.srt" "${slug}/${slug}_bilingual.ass" \
  --preset clean --top en

# Vibrant glow (B站 entertainment style)
python3 "$SKILL_DIR/srt_utils.py" to_ass \
  "${slug}/${slug}_bilingual.srt" "${slug}/${slug}_bilingual.ass" \
  --preset glow
```

**Custom style file** — for full control, provide an external `.ass` file with your own `[V4+ Styles]` section. It must contain styles named `EN` and `ZH`, or `to_ass` will fail early with a validation error. You can design styles visually with [Aegisub](https://aegisub.org/) and export.

```bash
python3 "$SKILL_DIR/srt_utils.py" to_ass \
  "${slug}/${slug}_bilingual.srt" "${slug}/${slug}_bilingual.ass" \
  --style-file my_styles.ass
```

Optionally add `; en_tag=` and `; zh_tag={\blur5}` comment lines in the `.ass` file to inject ASS override tags per language.

**Font** — omit `--font` to auto-pick the best installed CJK font for your OS; pass `--font` to override (ignored when using `--style-file`):

| Platform | Auto-picked |
| ---------- | ------ |
| macOS | `PingFang SC` |
| Linux | `Noto Sans CJK SC` (best of installed) |
| Windows | `Microsoft YaHei` |

**Other options:**

- `--top zh|en` — which language on the **upper line of the bottom stack** (default: `zh`)
- `--res WxH` — video resolution (default: `1920x1080`)
- `--fade <ms>` — fade in/out, in milliseconds (default `150`; `0` disables). Soft cinema-style in/out instead of a hard cut
- `--reflow` — split each cue into complete-sentence lines (rule 10), so no displayed line is a truncated fragment
- `--safe-area <frac>` — fraction of frame height kept clear at the bottom (default `0.06`), keeps subtitles off platform UI / progress bars

**Readability notes for all presets:**

- Presets stay bottom-aligned at all times; they do **not** move to the top automatically
- Font size, outline, and vertical margins scale with `--res` so 720p and 1080p keep similar visual balance
- `clean` is the safest choice when you must keep subtitles at the bottom in every shot

### Step 5: Burn Subtitles

Use the `ass=` filter (not `subtitles=`) — all styling comes from the ASS file.

```bash
ffmpeg -i "${slug}/${slug}.mp4" \
  -vf "ass='${slug}/${slug}_bilingual.ass'" \
  -c:v libx264 -crf 23 -preset medium \
  -c:a copy "${slug}/${slug}_bilingual.mp4"
```

- `-c:v libx264 -crf 23`: good quality with reasonable file size
- `-preset medium`: balance between speed and compression (use `fast` for quicker encode)
- No `force_style` needed — styles are embedded in the ASS file

### Step 6: Generate Publish Info

Based on the video content (from `{slug}_{src_lang}.srt` and `{slug}_zh.srt`), generate `{slug}/publish_info.md`.

All output in this file must be in **Chinese** (targeting Bilibili audience).

```markdown
# Publish Info

## Source
{YouTube URL}

## Titles (5 variants)
1. {Suspense/question style — spark curiosity}
2. {Data/achievement driven — emphasize results}
3. {Controversial/opinion style — spark discussion}
4. {Tutorial/practical style — emphasize utility}
5. {Emotional/relatable style — connect with audience}

## Tags
{~10 comma-separated keywords covering topic, technology, domain}

## Description
{3-5 sentences summarizing core content and highlights}

## Chapter Timestamps
00:00 {chapter name}
...
```

**Generation rules:**

- Title style must match Bilibili conventions: conversational tone, suspense hooks, liberal use of symbols (【】, ?, !)
- Tags should cover both Chinese and English keywords for discoverability
- Timestamps extracted from `{slug}_bilingual.srt` at topic transition points
- Description needs a strong hook — first two sentences determine whether users expand to read

## Output Structure

```
{slug}/
├── {slug}.mp4              # Source video
├── {slug}_{src_lang}.srt   # Source language subtitles
├── {slug}_zh.srt           # Chinese subtitles
├── {slug}_bilingual.srt    # Merged bilingual
├── {slug}_bilingual.mp4    # Final output
└── publish_info.md         # Bilibili upload metadata
```

## Utility: srt_utils.py

```bash
python3 "$SKILL_DIR/srt_utils.py" merge en.srt zh.srt output.srt          # Merge bilingual
python3 "$SKILL_DIR/srt_utils.py" merge --dry-run en.srt zh.srt output.srt # Pre-check without writing
python3 "$SKILL_DIR/srt_utils.py" validate input.srt                       # Check timing issues
python3 "$SKILL_DIR/srt_utils.py" fix input.srt output.srt                 # Fix timing/overlaps (multi-pass)
python3 "$SKILL_DIR/srt_utils.py" slugify "Video Title"                    # Generate slug
python3 "$SKILL_DIR/srt_utils.py" to_ass input.srt output.ass              # Convert to styled ASS (default: clean, ZH on top)
python3 "$SKILL_DIR/srt_utils.py" to_ass --dry-run input.srt output.ass    # Pre-check without writing
python3 "$SKILL_DIR/srt_utils.py" to_ass input.srt output.ass --preset glow --top en
python3 "$SKILL_DIR/srt_utils.py" to_ass input.srt output.ass --style-file custom.ass  # User-defined styles
python3 "$SKILL_DIR/srt_utils.py" check-whisper                    # Detect platform, recommend whisper backend + model
```

## Common Mistakes

- **Mismatched entry counts**: Merge fails by default — fix translation or use `--pad-missing` to pad
- **Font not found**: Ensure PingFang SC is installed (macOS default) or substitute (see Troubleshooting)

## Troubleshooting

### yt-dlp: Cookie Auth Failure

`--cookies-from-browser chrome` requires Chrome to be closed (or uses a snapshot of the profile). If it fails:

```bash
# Export cookies once, then reuse the file
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download "URL"
yt-dlp --cookies cookies.txt -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" -o "${slug}/${slug}.mp4" "URL"
```

For 429 / rate-limit errors, add `--sleep-interval 3 --max-sleep-interval 8`.

### whisper: Wrong Language or Hallucination Loops

Symptoms: repeated phrases, garbled characters, or near-empty SRT despite clear audio.

```bash
whisper "${slug}/${slug}.mp4" \
  --model medium \
  --language "$src_lang" \
  --condition_on_previous_text False \
  --no_speech_threshold 0.6 \
  --logprob_threshold -1.0 \
  --compression_ratio_threshold 2.0 \
  --output_format srt \
  --output_dir "${slug}"
```

If language is still misdetected, the audio likely has long silence or non-speech segments — add `--vad_filter True` to suppress them.

### ffmpeg: Font Not Found / CJK Boxes

Pass the correct font via `--font` in the `to_ass` step (Step 4.5). The ASS file embeds the font name, so ffmpeg needs it installed at burn time.

| Platform | Font | Install |
| ---------- | ------ | --------- |
| macOS | `PingFang SC` | pre-installed |
| Linux | `Noto Sans CJK SC` | `sudo apt install fonts-noto-cjk` |
| Linux (alt) | `WenQuanYi Micro Hei` | `sudo apt install fonts-wqy-microhei` |
| Windows | `Microsoft YaHei` | pre-installed |

Regenerate the ASS file with the correct `--font` flag, then re-run the burn step.

## Privacy & Data Flow

- **Browser cookies**: Step 1 uses `yt-dlp --cookies-from-browser chrome` to access age-gated or private videos. This reads Chrome cookies locally — no cookies are transmitted beyond YouTube's own servers. To avoid this, export cookies to a file first (see Troubleshooting above).
- **Transcripts & translation**: Step 3 (translate) and Step 6 (publish info) are performed by the AI agent in the conversation. Transcripts are sent to whatever model/service the agent uses (e.g. Claude API). If the video contains sensitive content, use a local model for those steps.
- **No telemetry**: `srt_utils.py` makes no network requests. All processing (SRT parsing, merging, ASS generation, hardware detection) is fully local.
