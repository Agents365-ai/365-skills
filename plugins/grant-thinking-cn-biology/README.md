# grant-thinking-cn-biology — Biology Grant Reasoning for China's Funding Context

[中文文档](README_CN.md)

## What it does

- Evaluates biology grant ideas for fundability in Chinese grant systems (NSFC, MOST, etc.)
- Distinguishes descriptive projects from mechanism-driven proposals
- Separates background, gap, question, hypothesis, aims, content, and methods — preventing structural collapse
- Identifies real biological innovation vs. decorative novelty language
- Assesses feasibility as biological-question fit, not method or platform abundance
- Surfaces likely reviewer concerns specific to Chinese biology grant panels
- Adapts reasoning to project level: youth (青年), general (面上), key (重点/课题)
- Delivers both strongest funding logic and main rejection risk in every substantive response
- Diagnoses before rewriting — reasoning precedes expression

## Multi-Platform Support

Works with all major AI agents that support the [Agent Skills](https://agentskills.io) format:

| Platform | Status | Details |
| ---------- | -------- | --------- |
| **Claude Code** | ✅ Full support | Native SKILL.md format |
| **OpenClaw / ClawHub** | ✅ Full support | `metadata.openclaw` namespace |
| **Hermes Agent** | ✅ Full support | `metadata.hermes` namespace, category: research |
| **Pi-Mo** | ✅ Full support | `metadata.pimo` namespace |
| **OpenAI Codex** | ✅ Full support | `agents/openai.yaml` sidecar |
| **SkillsMP** | ✅ Indexed | GitHub topics configured |

## Comparison: with vs. without this skill

| Capability | Native agent | This skill |
| ------------ | ------------- | ------------ |
| Distinguish interesting from fundable (biology) | No | Yes — explicit diagnosis |
| Detect descriptive vs. mechanism-driven project | No | Always |
| Separate background / gap / question / hypothesis / aims / content / methods | Inconsistent | Always |
| Evaluate innovation as real vs. decorative | No | Yes |
| Assess feasibility as biological-question fit | No | Yes |
| Identify likely reviewer concerns (Chinese context) | Rarely | Always |
| Match project to appropriate funding level | No | Yes |
| Detect overclaiming or inflated scope | No | Yes — explicit scope control |
| Both strongest logic and rejection risk in one response | No | Always |
| Diagnose proposal before rewriting | Rarely | Always |

## When to use

- Evaluating a new biology grant idea before investing writing effort
- Diagnosing why a proposal feels descriptive, scattered, or unconvincing
- Framing a project for NSFC, MOST, or similar Chinese grant panels
- Deciding whether a project belongs at youth, general, or key level
- Strengthening innovation claims without overclaiming
- Checking feasibility logic and identifying biology-specific bottlenecks
- Preparing the mechanistic spine before writing any section
- Getting reviewer-aware feedback on a title, outline, or draft
- Deciding what to cut, downgrade, or bound in the proposal

## Relationship to grant-thinking-general

This skill extends `grant-thinking-general` with four key layers:

1. **Chinese funding context** — project level fit, reviewer expectations, NSFC logic
2. **Biology-specific problem structure** — phenomenon / mechanism / regulatory logic / causal chains / model-system fit
3. **Mechanism-orientation constraint** — actively flags: differential expression ≠ mechanism, multi-omics ≠ depth, complex technology ≠ scientific maturity
4. **Cross-project-type adaptation** — adjusts reasoning for youth / general / key level without hard-coding one template

## Skill Installation

### Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.claude/skills/grant-thinking-cn-biology

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" .claude/skills/grant-thinking-cn-biology
```

### OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install grant-thinking-cn-biology

# Manual install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.openclaw/skills/grant-thinking-cn-biology

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" skills/grant-thinking-cn-biology
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.hermes/skills/research/grant-thinking-cn-biology
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/grant-thinking-cn-biology
```

### Pi-Mo

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.pimo/skills/grant-thinking-cn-biology
```

### OpenAI Codex

```bash
# User-level install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.agents/skills/grant-thinking-cn-biology

# Project-level install
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" .agents/skills/grant-thinking-cn-biology
```

### SkillsMP

```bash
skills install grant-thinking-cn-biology
```

### Installation paths summary

| Platform | Global path | Project path |
| ---------- | ------------- | -------------- |
| Claude Code | `~/.claude/skills/grant-thinking-cn-biology/` | `.claude/skills/grant-thinking-cn-biology/` |
| OpenClaw | `~/.openclaw/skills/grant-thinking-cn-biology/` | `skills/grant-thinking-cn-biology/` |
| Hermes Agent | `~/.hermes/skills/research/grant-thinking-cn-biology/` | Via `external_dirs` config |
| Pi-Mo | `~/.pimo/skills/grant-thinking-cn-biology/` | — |
| OpenAI Codex | `~/.agents/skills/grant-thinking-cn-biology/` | `.agents/skills/grant-thinking-cn-biology/` |

## Files

- `SKILL.md` — **the only required file**. Loaded by all platforms as the skill instructions.
- `agents/openai.yaml` — OpenAI Codex-specific configuration (display, policy, capabilities)
- `checks.md` — 12-point self-check list
- `examples.md` — 8 annotated examples
- `README.md` — this file (English)
- `README_CN.md` — Chinese documentation

> **Note:** Only `SKILL.md` is needed for the skill to work. All other files are supplementary.

## Related skills in the series

```
grant-thinking-general/          ← top-level fundable logic (any field)
grant-thinking-cn-biology/       ← this skill: Chinese biology grants
```

Planned extensions:

- `grant-thinking-cn-biology-youth/` — youth-level (青年科学基金) focused
- `grant-thinking-cn-biology-general-program/` — general program (面上项目) focused
- `grant-thinking-cn-biomedicine/` — translational/clinical biology variant

## GitHub Topics

For SkillsMP indexing, the Agents365-ai/365-skills monorepo uses the following topics:

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `grant-thinking` `grant-writing` `proposal` `research-funding` `reviewer-thinking` `feasibility` `biology` `nsfc` `china-grants` `mechanism`

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

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>
