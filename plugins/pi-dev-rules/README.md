# pi-dev-rules

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/pi-dev-rules?style=flat&logo=github)](https://github.com/Agents365-ai/pi-dev-rules/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/pi-dev-rules?style=flat&logo=github)](https://github.com/Agents365-ai/pi-dev-rules/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/pi-dev-rules?logo=github)](https://github.com/Agents365-ai/pi-dev-rules/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/pi-dev-rules?logo=github)](https://github.com/Agents365-ai/pi-dev-rules/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

**English** · [中文](README_CN.md)

A coding-agent skill that packages the **latest [Pi](https://pi.dev) documentation**
(`@earendil-works/pi-coding-agent`) as an on-demand reference, so an agent can install, configure,
run, and **extend Pi** without re-fetching the docs.

Mirrors <https://pi.dev/docs/latest> (fetched 2026-07-26).

Works with Claude Code, Cursor, Codex, Copilot, Windsurf, Cline / Roo Code, Gemini CLI,
Aider, Zed, OpenCode, OpenClaw / ClawHub, Hermes, pi-mono — plus major Chinese agents
(Trae, Qwen Code / Tongyi Lingma, Baidu Comate, CodeGeeX) — and any agent that reads
`AGENTS.md` or the [Agent Skills](https://agentskills.io) format.

<p align="center">
  <img src="assets/workflow-en.png" width="700" alt="pi-dev-rules workflow">
</p>

## What's inside

- `SKILL.md` — overview, when-to-use, cheat sheet, hard rules, reference index.
- `references/cli-and-usage.md` — install, auth, CLI flags, slash commands, message queue, context
  files, env vars, sessions, keybindings.
- `references/providers-and-models.md` — providers (30+), `auth.json` (+ scoped `env`), cloud
  providers, custom `models.json`, `compat`, custom-provider extensions.
- `references/settings-and-compaction.md` — `settings.json` (trust/analytics/retry/transport),
  auto/manual compaction, branch summaries.
- `references/extending-pi.md` — extensions API, skills (SKILL.md), prompt templates, themes, packages.
- `references/tui-components.md` — TUI component system for custom extension/tool UIs.
- `references/security-and-containerization.md` — project-trust model, no built-in sandbox, Gondolin
  micro-VM, Docker, OpenShell.
- `references/session-format.md` — session JSONL schema, message/entry types, SessionManager API.
- `references/programmatic.md` — SDK, RPC mode, JSON event-stream mode.
- `references/platform-setup.md` — Windows, Termux, tmux, per-terminal setup, shell aliases,
  build-from-source.
- `references/development.md` — building Pi from source, monorepo structure, forking/rebranding,
  debugging.
- `references/philosophy-and-design.md` (the creator's design manifesto, Mario Zechner's blog post,
  2025-11-30): why minimal, the 4-tool philosophy, YOLO by default, the explicit non-features (no
  MCP / plan mode / to-dos / sub-agents / background bash) with their intended alternatives.

## Install

| Platform | Path |
| ---------- | ------ |
| Claude Code (global) | `~/.claude/skills/pi-dev-rules/` |
| Claude Code (project) | `.claude/skills/pi-dev-rules/` |
| OpenClaw (global) | `~/.openclaw/skills/pi-dev-rules/` |
| Pi (global) | `~/.pi/agent/skills/pi-dev-rules/` |
| Pi (project) | `.pi/skills/pi-dev-rules/` |

```bash
cp -r pi-dev-rules ~/.claude/skills/      # example: Claude Code, global
```

## Updating

Re-fetch the pages under <https://pi.dev/docs/latest> and regenerate the `references/` files; bump
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
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## License

[MIT](LICENSE)
