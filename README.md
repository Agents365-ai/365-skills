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

### Drawing & diagrams

| Plugin | Description |
|---|---|
| `drawio` | Draw.io diagrams — PNG/SVG/PDF export with visual review loop |
| `mermaid` | Mermaid diagrams — text-based, GitHub-native, auto-layout |
| `excalidraw` | Excalidraw — hand-drawn whiteboard style |
| `plantuml` | PlantUML — UML, C4, sequence, class diagrams |
| `tldraw` | Tldraw — infinite canvas, sketch-style |

### Scientific research

| Plugin | Description |
|---|---|
| `semanticscholar` | Semantic Scholar — academic paper search, citation graph, recommendations, BibTeX export |
| `paper-fetch` | Paper PDF downloader by DOI / title — 7-source fallback (Unpaywall, S2, arXiv, PMC, bioRxiv, publisher, Sci-Hub) with batch mode and idempotent retries |
| `scholar-deep-research` | End-to-end literature review pipeline — 8-phase script-driven workflow, 7 federated sources (OpenAlex, arXiv, Crossref, PubMed, DBLP, bioRxiv, Exa), cross-source dedup, dual-backend citation chasing, parallel deep-read fan-out, mandatory self-critique, cited reports across 5 archetypes |

## Install plugins

```
/plugin install drawio
```

## Development

Plugin skills are direct copies of the source repos (not submodules). To update a plugin:

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

### Auto-sync (semanticscholar, paper-fetch, scholar-deep-research)

`semanticscholar-skill`, `paper-fetch`, and `scholar-deep-research` each ship a GitHub Actions workflow (`.github/workflows/sync-365-skills.yml`) that automatically pushes any change under their respective `skills/<name>/**` here, and bumps the version field in `marketplace.json`. Requires each source repo to have a `SYNC_365_SKILLS_TOKEN` secret with `Contents: write` on this repo.

## Source repos

Each plugin mirrors a standalone skill repo — file issues there for plugin-specific bugs:

| Plugin | Source |
|---|---|
| `drawio` | [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) |
| `mermaid` | [Agents365-ai/mermaid-skill](https://github.com/Agents365-ai/mermaid-skill) |
| `excalidraw` | [Agents365-ai/excalidraw-skill](https://github.com/Agents365-ai/excalidraw-skill) |
| `plantuml` | [Agents365-ai/plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) |
| `tldraw` | [Agents365-ai/tldraw-skill](https://github.com/Agents365-ai/tldraw-skill) |
| `semanticscholar` | [Agents365-ai/semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) |
| `paper-fetch` | [Agents365-ai/paper-fetch](https://github.com/Agents365-ai/paper-fetch) |
| `scholar-deep-research` | [Agents365-ai/scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) |

## Discord

Join the Discord community: [https://discord.gg/pCV3P9hNY](https://discord.gg/pCV3P9hNY)

## WeChat Community

Scan the QR code below to join the WeChat group for help, Q&A, and updates:

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="WeChat Community Group">
</p>

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

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai

## Other resources

- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) — community collection of scientific-research skills
- [anthropics/life-sciences](https://github.com/anthropics/life-sciences) — Anthropic's life-sciences skills
