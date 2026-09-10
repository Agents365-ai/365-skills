# scientific-thinking — Structured Scientific Reasoning for AI Agents

[中文文档](README_CN.md)

## What it does

- Frames and decomposes research questions before answering
- Distinguishes observed fact / direct evidence / indirect evidence / hypothesis / speculation
- Labels claim provenance: provided data vs. background knowledge vs. inference
- Ranks competing explanations by available support
- Calibrates conclusion language to evidence strength
- Defines interpretation boundaries and unresolved uncertainty
- Suggests the lowest-cost next step that would discriminate between explanations

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
| Distinguish fact from interpretation | Sometimes | Always, explicitly labeled |
| Label claim provenance | No | Yes — data / background / inference |
| Consider alternative explanations | Inconsistent | Yes — ranked by support |
| Calibrate language to evidence | No | Yes — 5-level scale |
| State interpretation boundary | Rarely | Always |
| Suggest discriminating next step | No | Yes |
| Handle null results correctly | No | Yes — absence ≠ evidence of absence |
| Reconcile conflicting papers | No | Yes — maps experimental differences |
| Evidence provenance for missing data | No | Yes — labels answer as provisional |

## When to use

- Interpreting experimental results or paper conclusions
- Evaluating competing hypotheses
- Analyzing mechanisms or pathways
- Designing or critiquing experiments
- Constructing scientific arguments for writing
- Reconciling conflicting findings
- Any research question where overclaiming is a risk

## Skill Installation

### Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.claude/skills/scientific-thinking

# Project-level install
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" .claude/skills/scientific-thinking
```

### OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install scientific-thinking

# Manual install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.openclaw/skills/scientific-thinking

# Project-level install
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" skills/scientific-thinking
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.hermes/skills/research/scientific-thinking
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/scientific-thinking
```

### Pi-Mo

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.pimo/skills/scientific-thinking
```

### OpenAI Codex

```bash
# User-level install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.agents/skills/scientific-thinking

# Project-level install
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" .agents/skills/scientific-thinking
```

### SkillsMP

```bash
skills install scientific-thinking
```

### Installation paths summary

| Platform | Global path | Project path |
| ---------- | ------------- | -------------- |
| Claude Code | `~/.claude/skills/scientific-thinking/` | `.claude/skills/scientific-thinking/` |
| OpenClaw | `~/.openclaw/skills/scientific-thinking/` | `skills/scientific-thinking/` |
| Hermes Agent | `~/.hermes/skills/research/scientific-thinking/` | Via `external_dirs` config |
| Pi-Mo | `~/.pimo/skills/scientific-thinking/` | — |
| OpenAI Codex | `~/.agents/skills/scientific-thinking/` | `.agents/skills/scientific-thinking/` |

## Files

- `SKILL.md` — **the only required file**. Loaded by all platforms as the skill instructions.
- `agents/openai.yaml` — OpenAI Codex-specific configuration (display, policy, capabilities)
- `checks.md` — 10-point self-check list referenced by SKILL.md
- `examples.md` — 8 annotated examples referenced by SKILL.md
- `README.md` — this file (English)
- `README_CN.md` — Chinese documentation

> **Note:** Only `SKILL.md` is needed for the skill to work. All other files are supplementary.

## GitHub Topics

For SkillsMP indexing, the Agents365-ai/365-skills monorepo uses the following topics:

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `scientific-thinking` `research` `reasoning` `evidence-evaluation`

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
