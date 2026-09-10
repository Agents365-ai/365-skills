# grant-thinking-general — Fundability-First Grant Reasoning for AI Agents

[中文文档](README_CN.md)

## What it does

- Evaluates whether a project idea is fundable, not just scientifically interesting
- Separates background, gap, question, aims, content, and approach — preventing structural collapse
- Identifies real innovation vs. decorative novelty language
- Assesses feasibility as logic-to-question fit, not method abundance
- Surfaces likely reviewer concerns and rejection risks
- Controls scope and detects overclaiming
- Delivers both strongest funding logic and main rejection risk in every substantive response
- Diagnoses before rewriting — reasoning precedes expression

## Multi-Platform Support

Works with all major AI agents that support the [Agent Skills](https://agentskills.io) format:

| Platform | Status | Details |
|----------|--------|---------|
| **Claude Code** | ✅ Full support | Native SKILL.md format |
| **OpenClaw / ClawHub** | ✅ Full support | `metadata.openclaw` namespace |
| **Hermes Agent** | ✅ Full support | `metadata.hermes` namespace, category: research |
| **Pi-Mo** | ✅ Full support | `metadata.pimo` namespace |
| **OpenAI Codex** | ✅ Full support | `agents/openai.yaml` sidecar |
| **SkillsMP** | ✅ Indexed | GitHub topics configured |

## Comparison: with vs. without this skill

| Capability | Native agent | This skill |
|------------|-------------|------------|
| Distinguish interesting from fundable | No | Yes — explicit diagnosis |
| Separate background / gap / question / aims / approach | Inconsistent | Always |
| Evaluate innovation as real vs. decorative | No | Yes |
| Assess feasibility as logic-to-question fit | No | Yes |
| Identify likely reviewer concerns | Rarely | Always |
| Detect overclaiming or inflated scope | No | Yes — explicit scope control |
| Both strongest logic and rejection risk in one response | No | Always |
| Diagnose proposal before rewriting | Rarely | Always |
| Distinguish scientific value from proposal viability | No | Yes |
| Identify project-breaking structural failures | No | Yes |

## When to use

- Evaluating a new grant idea before investing writing effort
- Diagnosing why a proposal feels weak, scattered, or unconvincing
- Framing a project for a specific funding scheme or panel
- Strengthening innovation claims without overclaiming
- Checking feasibility logic and identifying project-breaking risks
- Preparing the conceptual spine before writing any section
- Getting reviewer-aware feedback on a draft or outline
- Deciding what to cut, downgrade, or bound in the proposal

## Skill Installation

### Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.claude/skills/grant-thinking-general

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" .claude/skills/grant-thinking-general
```

### OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install grant-thinking-general

# Manual install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.openclaw/skills/grant-thinking-general

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" skills/grant-thinking-general
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.hermes/skills/research/grant-thinking-general
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/grant-thinking-general
```

### Pi-Mo

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.pimo/skills/grant-thinking-general
```

### OpenAI Codex

```bash
# User-level install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.agents/skills/grant-thinking-general

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" .agents/skills/grant-thinking-general
```

### SkillsMP

```bash
skills install grant-thinking-general
```

### Installation paths summary

| Platform | Global path | Project path |
|----------|-------------|--------------|
| Claude Code | `~/.claude/skills/grant-thinking-general/` | `.claude/skills/grant-thinking-general/` |
| OpenClaw | `~/.openclaw/skills/grant-thinking-general/` | `skills/grant-thinking-general/` |
| Hermes Agent | `~/.hermes/skills/research/grant-thinking-general/` | Via `external_dirs` config |
| Pi-Mo | `~/.pimo/skills/grant-thinking-general/` | — |
| OpenAI Codex | `~/.agents/skills/grant-thinking-general/` | `.agents/skills/grant-thinking-general/` |

## Files

- `SKILL.md` — **the only required file**. Loaded by all platforms as the skill instructions.
- `agents/openai.yaml` — OpenAI Codex-specific configuration (display, policy, capabilities)
- `checks.md` — 10-point self-check list referenced by SKILL.md
- `examples.md` — 7 annotated examples referenced by SKILL.md
- `README.md` — this file (English)
- `README_CN.md` — Chinese documentation

> **Note:** Only `SKILL.md` is needed for the skill to work. All other files are supplementary.

## GitHub Topics

For SkillsMP indexing, the Agents365-ai/365-skills monorepo uses the following topics:

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `grant-thinking` `grant-writing` `proposal` `research-funding` `reviewer-thinking` `feasibility`

## License

MIT

## Support

If this skill helps your research, consider supporting the author:

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

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai
