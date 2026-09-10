# scientific-thinking — AI 智能体的结构化科研思维 skill

[English](README.md)

## 功能说明

- 在回答前先对研究问题进行框架构建与问题分解
- 区分：观察事实 / 直接证据 / 间接证据 / 解释 / 假设 / 推测
- 标注声明来源：来自提供的数据 / 背景知识 / 推断
- 按现有支持程度对竞争性解释排序
- 根据证据强度校准结论语言
- 明确界定解释的边界和未解决的不确定性
- 建议最低成本的下一步，用于区分各竞争解释

## 多平台支持

兼容所有主流支持 [Agent Skills](https://agentskills.io) 格式的 AI 智能体：

| 平台 | 支持状态 | 说明 |
|------|----------|------|
| **Claude Code** | ✅ 完全支持 | 原生 SKILL.md 格式 |
| **OpenClaw / ClawHub** | ✅ 完全支持 | `metadata.openclaw` 命名空间 |
| **Hermes Agent** | ✅ 完全支持 | `metadata.hermes` 命名空间，category: research |
| **Pi-Mo** | ✅ 完全支持 | `metadata.pimo` 命名空间 |
| **OpenAI Codex** | ✅ 完全支持 | `agents/openai.yaml` 侧车文件 |
| **SkillsMP** | ✅ 可索引 | GitHub topics 已配置 |

## 有 skill 与无 skill 的对比

| 能力 | 原生智能体 | 本 skill |
|------|-----------|---------|
| 区分事实与解释 | 偶尔 | 始终，明确标注 |
| 标注声明来源 | 否 | 是 — 数据 / 背景知识 / 推断 |
| 考虑替代解释 | 不稳定 | 是 — 按支持程度排序 |
| 校准语言到证据 | 否 | 是 — 5 级量表 |
| 说明解释边界 | 少见 | 始终 |
| 建议鉴别性下一步 | 否 | 是 |
| 正确处理阴性结果 | 否 | 是 — 无证据 ≠ 证据缺失 |
| 调和矛盾文献 | 否 | 是 — 梳理实验变量差异 |
| 证据缺失时的处理 | 否 | 是 — 标注为初步推断 |

## 适用场景

- 解读实验结果或论文结论
- 评估竞争性假设
- 分析机制或通路
- 设计或评估实验方案
- 构建学术论证
- 调和相互矛盾的研究发现
- 任何存在过度解读风险的研究问题

## skill 安装

### Claude Code

```bash
# 全局安装（在所有项目中可用）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.claude/skills/scientific-thinking

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" .claude/skills/scientific-thinking
```

### OpenClaw / ClawHub

```bash
# 通过 ClawHub
clawhub install scientific-thinking

# 手动安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.openclaw/skills/scientific-thinking

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" skills/scientific-thinking
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.hermes/skills/research/scientific-thinking
```

或在 `~/.hermes/config.yaml` 中添加：

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
# 用户级安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" ~/.agents/skills/scientific-thinking

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-general/skills/scientific-thinking" .agents/skills/scientific-thinking
```

### SkillsMP

```bash
skills install scientific-thinking
```

### 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
|------|----------|----------|
| Claude Code | `~/.claude/skills/scientific-thinking/` | `.claude/skills/scientific-thinking/` |
| OpenClaw | `~/.openclaw/skills/scientific-thinking/` | `skills/scientific-thinking/` |
| Hermes Agent | `~/.hermes/skills/research/scientific-thinking/` | 通过 `external_dirs` 配置 |
| Pi-Mo | `~/.pimo/skills/scientific-thinking/` | — |
| OpenAI Codex | `~/.agents/skills/scientific-thinking/` | `.agents/skills/scientific-thinking/` |

## 文件说明

- `SKILL.md` — **唯一必需文件**。所有平台均加载此文件作为 skill 指令。
- `agents/openai.yaml` — OpenAI Codex 专用配置（显示名称、策略、能力列表）
- `checks.md` — SKILL.md 引用的 10 项自检清单
- `examples.md` — SKILL.md 引用的 8 个示例
- `README.md` — 英文文档
- `README_CN.md` — 本文件（中文）

> **注意：** 只需要 `SKILL.md` 即可使 skill 正常工作，其他文件均为辅助文件。

## GitHub Topics

用于 SkillsMP 索引，本仓库使用以下 topics：

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `scientific-thinking` `research` `reasoning` `evidence-evaluation`

## 开源协议

MIT

## 支持作者

如果这个 skill 对你的科研有帮助，欢迎支持作者：

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="微信支付">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="支付宝">
      <br>
      <b>支付宝</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai
