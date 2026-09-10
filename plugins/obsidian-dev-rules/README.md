# obsidian-dev-rules

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

**English** · [中文](README_CN.md)

A Claude Code / OpenClaw / Pi skill that packages the **Obsidian developer documentation**
(https://docs.obsidian.md) as an on-demand reference, so an agent can build and review Obsidian
plugins and themes without re-fetching the docs.

Mirrors the Obsidian developer docs, fetched 2026-05-24.

## What's inside

- `SKILL.md` — overview, when-to-use, cheat sheet, hard rules, reference index.
- `references/plugin-basics.md` — project setup, `manifest.json`, Plugin lifecycle, resource
  registration/cleanup, the event system, dev workflow / hot reload, debugging.
- `references/vault-and-editor.md` — Vault API (read/cachedRead/create/modify/process/delete,
  TFile/TFolder, adapter, normalizePath), Editor API, Markdown post-processing & code-block
  processors, CodeMirror 6 editor extensions.
- `references/ui.md` — commands (callback variants, hotkeys), settings (PluginSettingTab,
  load/saveData, Setting controls), modals (Modal/SuggestModal/FuzzySuggestModal), views (ItemView,
  registerView, workspace leaves), ribbon/status bar.
- `references/themes-and-release.md` — themes (CSS variables, theme.css/manifest, body classes,
  snippets), submitting plugins & themes, developer policies & guidelines.

## Install

| Platform | Path |
|----------|------|
| Claude Code (global) | `~/.claude/skills/obsidian-dev-rules/` |
| Claude Code (project) | `.claude/skills/obsidian-dev-rules/` |
| OpenClaw (global) | `~/.openclaw/skills/obsidian-dev-rules/` |
| Pi (global) | `~/.pi/agent/skills/obsidian-dev-rules/` |
| Pi (project) | `.pi/skills/obsidian-dev-rules/` |

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/obsidian-dev-rules/skills/obsidian-dev-rules" ~/.claude/skills/obsidian-dev-rules
```

## Related skills

Complements the Obsidian *usage* skills (obsidian-cli, obsidian-markdown, json-canvas,
obsidian-bases) — this one is the **developer reference** for the Plugin/Vault/Editor APIs, themes,
and the community submission process.

## Updating

Re-fetch the pages under https://docs.obsidian.md and regenerate `references/`; bump
`metadata.fetched` in `SKILL.md`.

## Support

If this skill is helpful, consider supporting the author:

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
  </tr>
</table>

## Author

**Agents365-ai** &mdash; building open-source skills for AI coding agents.

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## License

[MIT](LICENSE) (this skill's packaging). Obsidian docs content © Dynalist Inc. / the Obsidian team.
