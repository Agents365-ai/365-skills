# Installation

[← Back to README](../README.md)

> **Note (v1.3.5):** The SKILL.md and reference files now live under `skills/agent-native-design/` inside the repo. The install commands below copy only that subdirectory into your skills path. Marketplace installs (`/plugin install`, `clawhub install`, `skills install`) handle this automatically.

## Quick install — ask any agent

The simplest install is to ask any code-capable agent (Claude Code, Codex, Cursor, Aider, Gemini CLI, …) to clone the repo and copy the skill into your platform's skills directory:

```
Clone https://github.com/Agents365-ai/agent-native-design into /tmp/agent-native-design, then copy skills/agent-native-design into ~/.claude/skills/agent-native-design for me.
```

Substitute the destination for your platform — see the **Installation paths summary** table at the end of this page. For environments without an agent handy (CI, fresh machines, headless scripts), use the per-platform commands below.

## Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design ~/.claude/skills/ && \
  rm -rf /tmp/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design .claude/skills/ && \
  rm -rf /tmp/agent-native-design
```

## OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install agent-native-design

# Manual install
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design ~/.openclaw/skills/ && \
  rm -rf /tmp/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design skills/ && \
  rm -rf /tmp/agent-native-design
```

## Hermes Agent

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design ~/.hermes/skills/engineering/ && \
  rm -rf /tmp/agent-native-design
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/agent-native-design
```

## pi-mono

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design ~/.pimo/skills/ && \
  rm -rf /tmp/agent-native-design
```

## OpenAI Codex

```bash
# User-level install (default CODEX_HOME)
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design ~/.codex/skills/ && \
  rm -rf /tmp/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git /tmp/agent-native-design && \
  cp -r /tmp/agent-native-design/skills/agent-native-design .codex/skills/ && \
  rm -rf /tmp/agent-native-design
```

## SkillsMP

```bash
skills install agent-native-design
```

## Installation paths summary

| Platform | Global path | Project path |
| ---------- | ------------- | -------------- |
| Claude Code | `~/.claude/skills/agent-native-design/` | `.claude/skills/agent-native-design/` |
| OpenClaw | `~/.openclaw/skills/agent-native-design/` | `skills/agent-native-design/` |
| Hermes Agent | `~/.hermes/skills/engineering/agent-native-design/` | Via `external_dirs` config |
| pi-mono | `~/.pimo/skills/agent-native-design/` | — |
| OpenAI Codex | `~/.codex/skills/agent-native-design/` | `.codex/skills/agent-native-design/` |
