# Installation

[← Back to README](../README.md)

## Quick install — ask any agent

The simplest install is to ask any code-capable agent (Claude Code, Codex, Cursor, Aider, Gemini CLI, …) to clone the repo into your platform's skills directory. Just hand it the URL and the destination path:

```
Clone https://github.com/Agents365-ai/agent-native-design into ~/.claude/skills/agent-native-design for me.
```

Substitute the destination for your platform — see the **Installation paths summary** table at the end of this page. Because the prompt names the exact path, this works for any agent regardless of whether it has built-in knowledge of skills conventions. For environments without an agent handy (CI, fresh machines, headless scripts), use the per-platform `git clone` commands below.

## Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.claude/skills/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git .claude/skills/agent-native-design
```

## OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install agent-native-design

# Manual install
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.openclaw/skills/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git skills/agent-native-design
```

## Hermes Agent

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.hermes/skills/engineering/agent-native-design
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/agent-native-design
```

## pi-mono

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.pimo/skills/agent-native-design
```

## OpenAI Codex

```bash
# User-level install (default CODEX_HOME)
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.codex/skills/agent-native-design

# Project-level install
git clone https://github.com/Agents365-ai/agent-native-design.git .codex/skills/agent-native-design
```

## SkillsMP

```bash
skills install agent-native-design
```

## Installation paths summary

| Platform | Global path | Project path |
|----------|-------------|--------------|
| Claude Code | `~/.claude/skills/agent-native-design/` | `.claude/skills/agent-native-design/` |
| OpenClaw | `~/.openclaw/skills/agent-native-design/` | `skills/agent-native-design/` |
| Hermes Agent | `~/.hermes/skills/engineering/agent-native-design/` | Via `external_dirs` config |
| pi-mono | `~/.pimo/skills/agent-native-design/` | — |
| OpenAI Codex | `~/.codex/skills/agent-native-design/` | `.codex/skills/agent-native-design/` |
