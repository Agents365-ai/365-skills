# scientific-thinking-biology — Structured Scientific Reasoning for Biology & Life Science

[中文文档](README_CN.md)

A biology-specific adaptation of [scientific-thinking-general](https://github.com/Agents365-ai/365-skills/tree/main/plugins/scientific-thinking-biology/skills/scientific-thinking-biology), with domain-specific reasoning layers for molecular biology, genetics, genomics, cell biology, immunology, neuroscience, ecology, and all life science research.

## What it does

- Anchors reasoning to the correct biological level (molecular → cellular → tissue → organism → evolutionary)
- Distinguishes marker from driver, correlation from causation, enrichment from mechanism
- Evaluates the experimental system: in vitro / in vivo / ex vivo / clinical relevance and limits
- Applies a biological evidence hierarchy (genetic perturbation > biochemical > pharmacological > correlative omics)
- Flags biology-specific confounders: redundancy, compensation, composition bias, model organism gaps, overexpression artifacts, batch effects
- Calibrates claim language to evidence strength using biology-appropriate language
- Defines interpretation boundaries: species scope, cell type scope, disease context
- Suggests the lowest-cost next experiment that would discriminate between explanations

## Multi-Platform Support

Works with all major AI agents that support the [Agent Skills](https://agentskills.io) format:

| Platform | Status | Details |
| ---------- | -------- | --------- |
| **Claude Code** | ✅ Full support | Native SKILL.md format |
| **OpenClaw / ClawHub** | ✅ Full support | `metadata.openclaw` namespace |
| **Hermes Agent** | ✅ Full support | `metadata.hermes` namespace, category: research |
| **Pi-Mo** | ✅ Full support | `metadata.pimo` namespace |
| **SkillsMP** | ✅ Indexed | GitHub topics configured |

## Comparison: with vs. without this skill

| Capability | Native agent | This skill |
| ------------ | ------------- | ------------ |
| Distinguish marker from driver | No | Yes — requires functional perturbation |
| Evaluate experimental system | No | Yes — in vitro / in vivo / clinical |
| Apply biological evidence hierarchy | No | Yes — 8-level hierarchy |
| Flag model organism translation gap | No | Yes — species scope stated |
| Detect composition confound in omics | No | Yes — checks before concluding pathway |
| Handle null phenotypes correctly | No | Yes — redundancy/compensation considered |
| Separate enrichment from activity | No | Yes — enrichment ≠ pathway activation |
| Label claim provenance | No | Yes — data / background / inference |
| Calibrate language to evidence | No | Yes — 6-level scale |
| Suggest discriminating next experiment | No | Yes |

## When to use

- Interpreting results from cell biology, genetics, genomics, immunology, neuroscience, or any life science
- Analyzing molecular mechanisms, signaling pathways, or gene regulatory networks
- Evaluating phenotype–genotype relationships
- Designing or critiquing experimental systems
- Interpreting omics data (bulk/scRNA-seq, ATAC-seq, proteomics, GWAS, etc.)
- Evaluating model organism relevance and human translatability
- Constructing scientific arguments for research writing
- Reconciling conflicting findings across papers or experimental systems
- Any biology question where overclaiming a mechanism is a risk

## Skill Installation

### Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.claude/skills/scientific-thinking-biology

# Project-level install
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" .claude/skills/scientific-thinking-biology
```

### OpenClaw / ClawHub

```bash
# Via ClawHub
clawhub install scientific-thinking-biology

# Manual install
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.openclaw/skills/scientific-thinking-biology

# Project-level install
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" skills/scientific-thinking-biology
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.hermes/skills/research/scientific-thinking-biology
```

Or add to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/myskills/scientific-thinking-biology
```

### Pi-Mo

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.pimo/skills/scientific-thinking-biology
```

### SkillsMP

```bash
skills install scientific-thinking-biology
```

### Installation paths summary

| Platform | Global path | Project path |
| ---------- | ------------- | -------------- |
| Claude Code | `~/.claude/skills/scientific-thinking-biology/` | `.claude/skills/scientific-thinking-biology/` |
| OpenClaw | `~/.openclaw/skills/scientific-thinking-biology/` | `skills/scientific-thinking-biology/` |
| Hermes Agent | `~/.hermes/skills/research/scientific-thinking-biology/` | Via `external_dirs` config |
| Pi-Mo | `~/.pimo/skills/scientific-thinking-biology/` | — |

## Files

- `SKILL.md` — **the only required file**. Loaded by all platforms as the skill instructions.
- `checks.md` — 15-point biology checklist referenced by SKILL.md (general + biology-specific checks)
- `examples.md` — 10 annotated biology examples referenced by SKILL.md
- `README.md` — this file (English)
- `README_CN.md` — Chinese documentation

> **Note:** Only `SKILL.md` is needed for the skill to work. All other files are supplementary.

## Related Skills

- [scientific-thinking-general](https://github.com/Agents365-ai/365-skills/tree/main/plugins/scientific-thinking-biology/skills/scientific-thinking-biology) — the general-domain version this skill is based on
- [literature-review](https://github.com/Agents365-ai/zotero-research-assistant) — systematic literature review workflows
- [nh-bioinfo-practice-skill](https://github.com/Agents365-ai) — single-cell and spatial omics analysis

## GitHub Topics

For SkillsMP indexing, the Agents365-ai/365-skills monorepo uses the following topics:

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `scientific-thinking` `biology` `life-science` `genomics` `cell-biology` `immunology` `neuroscience` `research` `reasoning`

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
