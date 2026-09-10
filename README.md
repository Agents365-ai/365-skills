# 365 Skills

[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

Production-grade skills for AI coding agents by [Agents365-ai](https://github.com/Agents365-ai). Agent-agnostic, works with Claude Code, Cursor, Copilot, OpenClaw & more.

English | [中文](README_CN.md)

## Install

```bash
# Agent-agnostic — any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g

# Claude Code plugin marketplace (optional)
/plugin marketplace add Agents365-ai/365-skills
```

Install a single plugin (Claude Code): `/plugin install <plugin-name>`, e.g. `/plugin install drawio`.

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
| `journal-if` | Journal impact factor (JCR IF) lookup — find a journal's IF by name, compare IF across journals, and rank publication venue quality, backed by a bundled `journals_if.csv` dataset |
| `target-prioritization` | Multi-source drug-target due-diligence — turn a ranked gene list (e.g. scRNA-seq DE output) into a per-gene dossier across UniProt, OpenTargets, and PubMed, plus a local cross-lineage DE scan, then re-rank by a configurable composite score (cross-lineage convergence + druggability + disease genetics + tractability + novelty). Disease-agnostic |
| `figshare` | Figshare v2 REST API — search public datasets/articles, batch-download files by ID/DOI/URL, and create, update, publish, or multi-part-upload to your own articles (large-file 3-step upload flow) |
| `zenodo` | Zenodo REST API — deposit, publish, version, and search research artifacts (datasets, software, papers) with a citable DOI; sandbox-first, bucket-API uploads, full metadata reference and end-to-end shell examples |
| `grant-thinking-general` | Grant proposal reasoning meta-skill — reviewer-aware logic, fundability framing (significance, innovation, feasibility), scope control, and section-by-section diagnosis before any NSFC/NIH-style proposal is written |

### Knowledge & notes

| Plugin | Description |
|---|---|
| `obsidian-organizer` | Keep a large Obsidian vault tidy — file new notes into the best-fit folder and audit/reorganize existing structure, driven by a single source-of-truth map note (`00_Index/Folder_Map.md`) inside the vault. Link-safe by design (moves go through the `obsidian` CLI so wikilinks auto-repair), propose-then-confirm for bulk changes |
| `zotero-dev-rules` | Zotero developer reference — Web API v3 (read/write, file upload, syncing, streaming, OAuth), the desktop client's internal JavaScript API, plugin development (Zotero 7–10), translators, and CSL citation styles |
| `obsidian-dev-rules` | Obsidian developer reference — packaging of docs.obsidian.md for building/reviewing TypeScript plugins (Plugin lifecycle, Vault/Editor APIs, events, modals, views, CodeMirror 6) and CSS themes, plus community submission policies |

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

## Development

Plugin skills are direct copies of the source repos (not submodules). This repo is the central distribution point: update the source skill repo first, then copy the update here and bump the plugin's `version` in `.claude-plugin/marketplace.json`:

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
# bump "version" for the plugin in .claude-plugin/marketplace.json
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

Most source repos are now private; for those plugins this marketplace is the only distribution channel.

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
