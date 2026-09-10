# zotero-dev-rules

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

**English** · [中文](README_CN.md)

A Claude Code / OpenClaw / Pi skill that packages the **Zotero developer documentation**
(<https://www.zotero.org/support/dev>) as an on-demand reference, so an agent can use the Web API,
build plugins, write translators, and create citation styles without re-fetching the docs.

Mirrors the Zotero dev docs (Web API **v3**), fetched 2026-08-18.

<p align="center">
  <img src="assets/workflow.png" width="560" alt="zotero-dev-rules workflow">
</p>

## What's inside

- `SKILL.md` — overview, when-to-use, cheat sheet, hard rules, reference index.
- `references/web-api.md` — base URL, auth/API keys, versioning, read & write requests, batch, file
  upload, item types/fields, the version-based syncing algorithm, streaming API, OAuth.
- `references/client-and-plugins.md` — the client's internal JavaScript API (Items/Search/DB/Notifier),
  Run JavaScript, Zotero 7 bootstrapped plugin development, and Zotero 10 migration notes.
- `references/translators.md` — translator metadata, detectWeb/doWeb/doImport/doExport/doSearch,
  scraping helpers, HTTP request helpers, calling other translators, Scaffold/testing.
- `references/citation-styles.md` — CSL, citeproc-js / citeproc-node, the style repo, style editing,
  rendering via the Web API.
- `references/plugin-gallery.md` — snapshot of the zotero-chinese plugin-store registry (137 plugins
  by tag + deprecated list): find similar open-source plugins and study their code before building.

## Install

| Platform | Path |
| ---------- | ------ |
| Claude Code (global) | `~/.claude/skills/zotero-dev-rules/` |
| Claude Code (project) | `.claude/skills/zotero-dev-rules/` |
| OpenClaw (global) | `~/.openclaw/skills/zotero-dev-rules/` |
| Pi (global) | `~/.pi/agent/skills/zotero-dev-rules/` |
| Pi (project) | `.pi/skills/zotero-dev-rules/` |

The skill lives in the Agents365-ai skills monorepo; clone the monorepo and link or copy
the skill directory into your agent's skills path:

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zotero-dev-rules/skills/zotero-dev-rules" ~/.claude/skills/zotero-dev-rules
```

## Related skills

Pairs with [`zotero-manager`](https://github.com/Agents365-ai/zotero-manager) and
[`zotero-research-assistant`](https://github.com/Agents365-ai/zotero-research-assistant) (workflow
skills); this one is the **developer reference** for the API, plugins, translators, and CSL.

## Updating

Re-fetch the pages under <https://www.zotero.org/support/dev> and regenerate `references/`; bump
`metadata.fetched` in `SKILL.md`.

## Support

If this project helps you, consider supporting the author:

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
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Tip Author">
      <br>
      <b>Tip Author</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## License

[CC BY-NC 4.0](LICENSE) — free for non-commercial use. Commercial use requires permission.

Zotero docs content © the Corporation for Digital Scholarship; Zotero translators are AGPL v3;
CSL styles are CC BY-SA.
