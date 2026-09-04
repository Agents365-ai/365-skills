# 365 Skills

Production-grade Claude Code skills by [Agents365-ai](https://github.com/Agents365-ai).

English | [中文](README_CN.md)

## Install

```bash
# Claude Code plugin marketplace
/plugin marketplace add Agents365-ai/365-skills

# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g
```

## Available plugins

### Development & CLI design

| Plugin | Description |
| --- | --- |
| `agent-native-design` | CLI design for AI agents — evaluate, design, and refactor CLIs to serve humans, agents, and orchestration systems simultaneously |
| `pi-plugin-cc` | Drive the Pi coding agent from Claude Code — model-agnostic delegation and code review. `/pi:review` with structured findings, `/pi:adversarial-review`, `/pi:rescue`, `/pi:parallel-rescue`, racing/fallback across providers, incremental review |

### Drawing & diagrams

| Plugin | Description |
| --- | --- |
| `drawio` | Draw.io diagrams — PNG/SVG/PDF export with visual review loop |
| `mermaid` | Mermaid diagrams — text-based, GitHub-native, auto-layout |
| `excalidraw` | Excalidraw — hand-drawn whiteboard style |
| `plantuml` | PlantUML — UML, C4, sequence, class diagrams |
| `tldraw` | Tldraw — infinite canvas, sketch-style |

### Scientific research

| Plugin | Description |
| --- | --- |
| `semanticscholar` | Semantic Scholar — academic paper search, citation graph, recommendations, BibTeX export |
| `paper-fetch` | Paper PDF downloader by DOI / title — 7-source fallback (Unpaywall, S2, arXiv, PMC, bioRxiv, publisher, Sci-Hub) with batch mode and idempotent retries |
| `scholar-deep-research` | End-to-end literature review pipeline — 8-phase script-driven workflow, 7 federated sources (OpenAlex, arXiv, Crossref, PubMed, DBLP, bioRxiv, Exa), cross-source dedup, dual-backend citation chasing, parallel deep-read fan-out, mandatory self-critique, cited reports across 5 archetypes |
| `asta` | Ai2 Asta MCP — Semantic Scholar academic graph over MCP (no Python). Intent-to-tool routing, safe `fields` defaults, citation traversal, snippet evidence retrieval, and DOI/arXiv/PMID via `externalIds` |
| `journal-abbrev` | Journal name abbreviation lookup — ISO 4 + MEDLINE, multi-source cascade (JabRef → AbbrevISO → NLM), BibTeX rewrite with `--idempotency-key`, atomic cache rebuild, agent-native JSON envelope with stable error codes and dry-run |
| `target-prioritization` | Multi-source drug-target due-diligence — turn a ranked gene list (e.g. scRNA-seq DE output) into a per-gene dossier across UniProt, OpenTargets, and PubMed, plus a local cross-lineage DE scan, then re-rank by a configurable composite score (cross-lineage convergence + druggability + disease genetics + tractability + novelty). Disease-agnostic |

### Knowledge & notes

| Plugin | Description |
|---|---|
| `obsidian-organizer` | Keep a large Obsidian vault tidy — file new notes into the best-fit folder and audit/reorganize existing structure, driven by a single source-of-truth map note (`00_Index/Folder_Map.md`) inside the vault. Link-safe by design (moves go through the `obsidian` CLI so wikilinks auto-repair), propose-then-confirm for bulk changes |

### Media & creative

| Plugin | Description |
| --- | --- |
| `ttscn` | Multi-platform Chinese TTS text-to-speech — 14 backends (Edge/Doubao/CosyVoice/Qwen/StepFun/Zhipu/Azure/Tencent/Baidu/MiniMax/Xunfei/ElevenLabs/OpenAI/Google), agent-native CLI with JSON envelope, schema introspection, voice cloning, SSML, emotion, dialects, filterable HTML comparison page |
| `imagencn` | AI image generation via Alibaba Bailian, ByteDance Volcano Ark & Tencent Hunyuan — 23 models, Chinese text excellence, rich terminal UI, smart config |
| `videogencn` | AI video clip generation with Chinese video models — text-to-video, image-to-video, first/last-frame and reference-to-video across Bailian (Wan/PixVerse/Kling/Vidu), Jimeng (doubao-seedance), MiniMax (Hailuo), Hunyuan |
| `assetseeker` | Search free commercial-use creative assets — photos, illustrations, icons, video footage, music, sound effects, and fonts across Pexels, Unsplash, Pixabay, Iconify, Freesound, Google Fonts and more |
| `video-podcast-maker` | Automated topic-driven video podcast creation — research → script → TTS (7 backends) → 4K Remotion render → BGM mix → Remotion-native subtitles. Multi-platform output (Bilibili / YouTube / Xiaohongshu / Douyin / WeChat Channels), horizontal long-form (16:9 4K) and vertical shorts (9:16), 15-step workflow with mandatory Studio preview |
| `bangumi-frames` | Bilibili anime frame & character organizer — download a bangumi/UP video (or local file), extract scene-change keyframes, split scenery vs character crops, cluster by CCIP identity or pull one character via a reference folder; optional OCR+LaMa subtitle/watermark removal |
| `yt2bb` | Repurpose YouTube videos for Bilibili — download via yt-dlp, transcribe with whisper, generate bilingual (English-Chinese) SRT subtitles, hardcode them with ffmpeg |

## Install plugins

```
/plugin install drawio
```

## Development

Plugin skills are direct copies of the source repos (not submodules). This repo is the central distribution point: update the source skill repo first, then copy the update here and bump the plugin's `version` in `.claude-plugin/marketplace.json`:

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
# bump "version" for the plugin in .claude-plugin/marketplace.json
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

Most source repos are now private; for those plugins this marketplace is the only distribution channel.

## Source repos

Each plugin mirrors a standalone skill repo — file issues there for plugin-specific bugs (private repos accept issues from collaborators only):

| Plugin | Source |
| --- | --- |
| `agent-native-design` | [Agents365-ai/agent-native-design](https://github.com/Agents365-ai/agent-native-design) |
| `drawio` | [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) |
| `scholar-deep-research` | [Agents365-ai/scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) |
| `journal-abbrev` | [Agents365-ai/journal-abbrev](https://github.com/Agents365-ai/journal-abbrev) |
| `video-podcast-maker` | [Agents365-ai/video-podcast-maker](https://github.com/Agents365-ai/video-podcast-maker) |
| `obsidian-organizer` | [Agents365-ai/obsidian-organizer](https://github.com/Agents365-ai/obsidian-organizer) |
| `asta` | Agents365-ai/asta-skill (private) |
| `bangumi-frames` | Agents365-ai/bangumi-frames (private) |
| `excalidraw` | Agents365-ai/excalidraw-skill (private) |
| `imagencn` | Agents365-ai/imagencn (private) |
| `mermaid` | Agents365-ai/mermaid-skill (private) |
| `paper-fetch` | Agents365-ai/paper-fetch (private) |
| `pi-plugin-cc` | Agents365-ai/pi-plugin-cc (private) |
| `plantuml` | Agents365-ai/plantuml-skill (private) |
| `semanticscholar` | Agents365-ai/semanticscholar-skill (private) |
| `target-prioritization` | Agents365-ai/target-prioritization (private) |
| `tldraw` | Agents365-ai/tldraw-skill (private) |
| `ttscn` | Agents365-ai/ttscn (private) |
| `videogencn` | distributed via this repo only |
| `yt2bb` | Agents365-ai/yt2bb (private) |

## Support

If this skill set is helpful, consider supporting the author:

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
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Tip">
      <br>
      <b>Tip</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## Other resources

- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) — community collection of scientific-research skills
- [anthropics/life-sciences](https://github.com/anthropics/life-sciences) — Anthropic's life-sciences skills
