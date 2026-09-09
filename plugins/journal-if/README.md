# Journal IF — Journal Impact Factor Lookup Skill

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/journal-if?style=flat&logo=github)](https://github.com/Agents365-ai/journal-if/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/journal-if?style=flat&logo=github)](https://github.com/Agents365-ai/journal-if/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/journal-if?logo=github)](https://github.com/Agents365-ai/journal-if/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/journal-if?logo=github)](https://github.com/Agents365-ai/journal-if/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[中文](README_CN.md)

A Claude Code skill for looking up journal impact factors (JCR IF). Bundled with ~200 top journals and backed by OpenAlex API fallback for any journal worldwide.

<img src="https://raw.githubusercontent.com/Agents365-ai/journal-if/main/docs/workflow.drawio.png" width="600" alt="Workflow">

## Features

| Feature | Native Claude Code | Journal IF |
| --------- | ------------------- | ------------ |
| Impact factor lookup | Hallucination / stale data | Curated CSV + real-time API, accurate |
| Batch processing | Not supported | One journal per line, partial-success envelope |
| Fuzzy search | Not supported | Substring matching, paginated |
| Offline lookup | Not supported | Bundled CSV works with `--offline` flag |
| Agent-native output | — | Stable JSON envelope, distinct exit codes, retryable errors |

## Data Sources

1. **Bundled CSV** — ~200 top journals across life sciences, medicine, chemistry, physics, and engineering. Curated from JCR 2023 data, shipped with the skill. Instant, always available.

2. **OpenAlex API** — Free, open API that computes an approximate 2-year impact factor from citation counts. Covers virtually all academic journals. The number differs from the official JCR IF — adequate for ranking and comparison; cite as approximate in formal contexts.

## Installation

The skill bundle lives at `skills/journal-if/` (containing `SKILL.md` and
`journal_if.py`). The recommended path is the plugin marketplace — it handles
updates for you:

```bash
# Claude Code plugin marketplace (recommended)
/plugin marketplace add Agents365-ai/365-skills
/plugin install journal-if

# Any agent (Claude Code, Cursor, Copilot, …)
npx skills add Agents365-ai/365-skills -g
```

Also published on [ClawHub](https://clawhub.ai/) and
[SkillsMP](https://skillsmp.com) — each handles updates through its own
marketplace.

Or install the skill bundle manually into any `SKILL.md`-aware platform:

| Platform | Install |
| --- | --- |
| **Claude Code** (global) | `git clone https://github.com/Agents365-ai/journal-if.git /tmp/ji && cp -r /tmp/ji/skills/journal-if ~/.claude/skills/ && rm -rf /tmp/ji` |
| **Claude Code** (project) | `git clone https://github.com/Agents365-ai/journal-if.git /tmp/ji && cp -r /tmp/ji/skills/journal-if .claude/skills/ && rm -rf /tmp/ji` |
| **OpenClaw** (global) | replace `~/.claude/skills/` with `~/.openclaw/skills/` in the recipe above |

Or just clone the repo and run the CLI directly — it is pure Python 3.9+
standard library with no third-party dependencies, and works on macOS, Linux,
and Windows:

```bash
git clone https://github.com/Agents365-ai/journal-if.git
cd journal-if/skills/journal-if
python3 journal_if.py lookup "Nature Medicine"
python3 journal_if.py schema              # full machine-readable CLI contract
```

## Usage

### Natural Language

Ask Claude directly:

- "What's the impact factor of Nature Medicine?"
- "Compare the IF of Cell and Science"
- "Which immunology journals have IF > 20?"
- "Look up IF for this list of journals"

### Command Line

```bash
# Single journal lookup
python3 journal_if.py lookup "Nature Medicine"

# Fuzzy search (paginated)
python3 journal_if.py search "immunology" --limit 10 --offset 0

# Batch lookup (one journal per line)
python3 journal_if.py batch journals.txt

# Cache-only mode (no network)
python3 journal_if.py --offline lookup "Cell"

# Cache management
python3 journal_if.py cache status                # inspect local cache
python3 journal_if.py cache update                # refresh upstream CSV

# Machine-readable CLI contract (for AI agents and automation)
python3 journal_if.py schema
python3 journal_if.py schema lookup
```

### Agent-native output contract

Stdout is a stable JSON envelope when not attached to a terminal (piped or
captured by an agent runtime), and a human table/indent view when run on a TTY.
Every response carries the same shape:

- Success: `{"ok": true, "data": ..., "meta": {"schema_version", "cli_version", "latency_ms"}}`
- Partial (batch): `{"ok": "partial", "data": {"succeeded": [...], "failed": [...]}}`
- Error: `{"ok": false, "error": {"code", "message", "retryable", ...}}`

The `error.code` field is stable. Notable codes:

| Code | Retryable | Exit | Meaning |
| ------ | ----------- | ------ | --------- |
| `not_found` | no | 3 | Lookup completed but no source matched |
| `upstream_unavailable` | **yes** | 1 | OpenAlex API failed transiently; retry later or use `--offline` |
| `file_not_found` / `validation_error` | no | 2 | Bad input |
| `runtime_error` | yes | 1 | Unexpected internal failure |

Branch on `error.code` + `error.retryable` rather than exit code alone — exit
`1` covers both transient and runtime errors. Force a format with
`--format json|table|human` (or the back-compat `--json`); flags may appear
before or after the subcommand.

### Understanding Impact Factor

| IF Range | Typical Tier | Example |
| ---------- | ------------- | --------- |
| > 30 | Elite (top 0.1%) | Nature (64.8), Science (56.9), Cell (64.5) |
| 20–30 | Exceptional (top 1%) | Cancer Cell (50.3), Immunity (32.4) |
| 10–20 | Excellent (top 5%) | Nature Communications (16.6), Sci Adv (13.6) |
| 5–10 | Strong (top 15%) | eLife (7.7), Cell Reports (8.8) |
| 2–5 | Solid | PLOS ONE (3.7), Sci Rep (4.6) |
| < 2 | Niche / new | Many field-specific and new journals |

**Caveat:** IF varies dramatically by field — always compare within the same
discipline. OpenAlex approximate IF differs from official JCR IF; use for
ranking, not formal citation.

## Requirements

- Python 3.9+ (no third-party packages required)

## ❤️ Support

If this skill helps you, consider supporting the author:

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

## 👤 Author

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 License

CC BY-NC 4.0 — Free for non-commercial use. Commercial use requires permission.
