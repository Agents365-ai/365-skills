# grant-thinking-general — AI 智能体的基金申请战略思维 skill

[English](README.md)

## 功能说明

- 评判项目是否真正可立项资助，而不只是科学上有趣
- 分离背景、空白、科学问题、研究目标、研究内容、研究方案——防止逻辑层次崩塌
- 识别真实创新与装饰性新颖语言
- 以"逻辑是否回答问题"而非"方法是否丰富"来评估可行性
- 暴露评审人可能的疑虑和否决风险
- 控制申请范围，检测过度承诺
- 每次实质性回应都同时给出：最强立项逻辑 + 最大否决风险
- 先诊断再改写——推理先于表达

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
| 区分"有趣"与"可资助" | 否 | 是 — 显式诊断 |
| 分离背景 / 空白 / 问题 / 目标 / 内容 / 方案 | 不稳定 | 始终 |
| 区分真实创新与装饰性新颖语言 | 否 | 是 |
| 以逻辑-问题匹配度评估可行性 | 否 | 是 |
| 识别评审人可能的疑虑 | 少见 | 始终 |
| 检测过度承诺或范围膨胀 | 否 | 是 — 显式范围控制 |
| 同时给出最强逻辑与最大否决风险 | 否 | 始终 |
| 先诊断再改写 | 少见 | 始终 |
| 区分科学价值与立项可行性 | 否 | 是 |
| 识别破坏项目结构的致命缺陷 | 否 | 是 |

## 适用场景

- 在投入写作前评估一个新的基金申请想法
- 诊断标书为何感觉薄弱、零散或缺乏说服力
- 为特定资助机构或评审专家组进行项目定位
- 在不过度承诺的前提下加强创新点表述
- 检验可行性逻辑，识别项目层面的致命风险
- 在撰写任何章节之前搭建概念骨架
- 对草稿或提纲进行评审视角的反馈
- 决定申请书中哪些内容需要删减、降级或设定边界

## skill 安装

### Claude Code

```bash
# 全局安装（在所有项目中可用）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.claude/skills/grant-thinking-general

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" .claude/skills/grant-thinking-general
```

### OpenClaw / ClawHub

```bash
# 通过 ClawHub
clawhub install grant-thinking-general

# 手动安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.openclaw/skills/grant-thinking-general

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" skills/grant-thinking-general
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.hermes/skills/research/grant-thinking-general
```

或在 `~/.hermes/config.yaml` 中添加：

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
# 用户级安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" ~/.agents/skills/grant-thinking-general

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-general/skills/grant-thinking-general" .agents/skills/grant-thinking-general
```

### SkillsMP

```bash
skills install grant-thinking-general
```

### 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
|------|----------|----------|
| Claude Code | `~/.claude/skills/grant-thinking-general/` | `.claude/skills/grant-thinking-general/` |
| OpenClaw | `~/.openclaw/skills/grant-thinking-general/` | `skills/grant-thinking-general/` |
| Hermes Agent | `~/.hermes/skills/research/grant-thinking-general/` | 通过 `external_dirs` 配置 |
| Pi-Mo | `~/.pimo/skills/grant-thinking-general/` | — |
| OpenAI Codex | `~/.agents/skills/grant-thinking-general/` | `.agents/skills/grant-thinking-general/` |

## 文件说明

- `SKILL.md` — **唯一必需文件**。所有平台均加载此文件作为 skill 指令。
- `agents/openai.yaml` — OpenAI Codex 专用配置（显示名称、策略、能力列表）
- `checks.md` — SKILL.md 引用的 10 项自检清单
- `examples.md` — SKILL.md 引用的 7 个标注示例
- `README.md` — 英文文档
- `README_CN.md` — 本文件（中文）

> **注意：** 只需要 `SKILL.md` 即可使 skill 正常工作，其他文件均为辅助文件。

## GitHub Topics

用于 SkillsMP 索引，本仓库使用以下 topics：

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `grant-thinking` `grant-writing` `proposal` `research-funding` `reviewer-thinking` `feasibility`

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
