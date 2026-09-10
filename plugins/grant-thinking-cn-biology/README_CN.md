# grant-thinking-cn-biology — 面向中国生物学基金申请的 AI 智能体战略推理 skill

[English](README.md)

## 功能说明

- 在中国基金体系（国自然、科技部等）语境下评估生物学项目是否真正可立项
- 区分描述性项目与机制驱动型申请书
- 分离背景、研究空白、科学问题、科学假设、研究目标、研究内容、技术路线——防止逻辑层次崩塌
- 识别真实生物学创新与装饰性新颖语言
- 以"逻辑是否回答生物学问题"而非"方法是否丰富"来评估可行性
- 暴露中国生物学评审专家可能的疑虑和否决风险
- 适应不同项目层级：青年科学基金、面上项目、重点项目/课题
- 每次实质性回应都同时给出：最强立项逻辑 + 最大否决风险
- 先诊断再改写——推理先于表达

## 多平台支持

兼容所有主流支持 [Agent Skills](https://agentskills.io) 格式的 AI 智能体：

| 平台 | 支持状态 | 说明 |
| ------ | ---------- | ------ |
| **Claude Code** | ✅ 完全支持 | 原生 SKILL.md 格式 |
| **OpenClaw / ClawHub** | ✅ 完全支持 | `metadata.openclaw` 命名空间 |
| **Hermes Agent** | ✅ 完全支持 | `metadata.hermes` 命名空间，category: research |
| **Pi-Mo** | ✅ 完全支持 | `metadata.pimo` 命名空间 |
| **OpenAI Codex** | ✅ 完全支持 | `agents/openai.yaml` 侧车文件 |
| **SkillsMP** | ✅ 可索引 | GitHub topics 已配置 |

## 有 skill 与无 skill 的对比

| 能力 | 原生智能体 | 本 skill |
| ------ | ----------- | --------- |
| 区分"有趣"与"可资助"（生物学语境） | 否 | 是 — 显式诊断 |
| 识别描述性项目 vs 机制驱动型申请 | 否 | 始终 |
| 分离背景 / 空白 / 问题 / 假设 / 目标 / 内容 / 方案 | 不稳定 | 始终 |
| 区分真实创新与装饰性新颖语言 | 否 | 是 |
| 以逻辑-问题匹配度评估可行性 | 否 | 是 |
| 识别中国生物学评审语境下的疑虑 | 少见 | 始终 |
| 将项目与合适的资助层级匹配 | 否 | 是 |
| 检测过度承诺或范围膨胀 | 否 | 是 — 显式范围控制 |
| 同时给出最强逻辑与最大否决风险 | 否 | 始终 |
| 先诊断再改写 | 少见 | 始终 |

## 适用场景

- 在投入写作前评估一个生物学基金申请想法是否可立项
- 诊断标书为何显得描述性过强、零散或缺乏说服力
- 为国自然、科技部或类似中国基金机构进行项目定位
- 判断项目适合青年、面上还是重点层级
- 在不过度承诺的前提下加强创新点表述
- 检验可行性逻辑，识别生物学层面的瓶颈和破坏性风险
- 在撰写任何章节之前搭建机制主线骨架
- 对题目、提纲或草稿进行评审视角的反馈
- 决定申请书中哪些内容需要删减、降级或设定边界

## 与 grant-thinking-general 的关系

本 skill 在 `grant-thinking-general` 的基础上增加了四个关键维度：

1. **中国基金语境** — 项目层级适配、评审专家预期、国自然逻辑
2. **生物学问题结构** — 现象 / 机制 / 调控逻辑 / 因果链条 / 模型系统适配性
3. **机制导向约束** — 主动标记：差异表达 ≠ 机制、多组学 ≠ 深度、技术复杂 ≠ 科学成熟
4. **跨项目类型适配** — 针对青年 / 面上 / 重点层级调整推理，不锁死单一模板

## skill 安装

### Claude Code

```bash
# 全局安装（在所有项目中可用）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.claude/skills/grant-thinking-cn-biology

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" .claude/skills/grant-thinking-cn-biology
```

### OpenClaw / ClawHub

```bash
# 通过 ClawHub
clawhub install grant-thinking-cn-biology

# 手动安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.openclaw/skills/grant-thinking-cn-biology

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" skills/grant-thinking-cn-biology
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.hermes/skills/research/grant-thinking-cn-biology
```

或在 `~/.hermes/config.yaml` 中添加：

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
# 用户级安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" ~/.agents/skills/grant-thinking-cn-biology

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/grant-thinking-cn-biology/skills/grant-thinking-cn-biology" .agents/skills/grant-thinking-cn-biology
```

### SkillsMP

```bash
skills install grant-thinking-cn-biology
```

### 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
| ------ | ---------- | ---------- |
| Claude Code | `~/.claude/skills/grant-thinking-cn-biology/` | `.claude/skills/grant-thinking-cn-biology/` |
| OpenClaw | `~/.openclaw/skills/grant-thinking-cn-biology/` | `skills/grant-thinking-cn-biology/` |
| Hermes Agent | `~/.hermes/skills/research/grant-thinking-cn-biology/` | 通过 `external_dirs` 配置 |
| Pi-Mo | `~/.pimo/skills/grant-thinking-cn-biology/` | — |
| OpenAI Codex | `~/.agents/skills/grant-thinking-cn-biology/` | `.agents/skills/grant-thinking-cn-biology/` |

## 文件说明

- `SKILL.md` — **唯一必需文件**。所有平台均加载此文件作为 skill 指令。
- `agents/openai.yaml` — OpenAI Codex 专用配置（显示名称、策略、能力列表）
- `checks.md` — 12 项自检清单
- `examples.md` — 8 个标注示例
- `README.md` — 英文文档
- `README_CN.md` — 本文件（中文）

> **注意：** 只需要 `SKILL.md` 即可使 skill 正常工作，其他文件均为辅助文件。

## skill 系列关系

```
grant-thinking-general/          ← 顶层通用可立项推理（跨领域）
grant-thinking-cn-biology/       ← 本 skill：中国生物学基金
```

规划中的扩展：

- `grant-thinking-cn-biology-youth/` — 专注青年科学基金
- `grant-thinking-cn-biology-general-program/` — 专注面上项目
- `grant-thinking-cn-biomedicine/` — 转化 / 临床生物学变体

## GitHub Topics

用于 SkillsMP 索引，本仓库使用以下 topics：

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `grant-thinking` `grant-writing` `proposal` `research-funding` `reviewer-thinking` `feasibility` `biology` `nsfc` `china-grants` `mechanism`

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

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>
