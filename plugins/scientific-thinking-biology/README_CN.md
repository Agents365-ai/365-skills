# scientific-thinking-biology — 面向生物与生命科学的结构化科研思维 skill

[English](README.md)

本 skill 是 [scientific-thinking-general](https://github.com/Agents365-ai/365-skills/tree/main/plugins/scientific-thinking-biology/skills/scientific-thinking-biology) 的生物学专项适配版，针对分子生物学、遗传学、基因组学、细胞生物学、免疫学、神经科学、生态学等生命科学研究领域，加入了领域专属的推理层次与常见陷阱检查。

## 功能说明

- 将推理锚定到正确的生物层次（分子 → 细胞 → 组织 → 个体 → 进化）
- 区分标志物与驱动因子、相关性与因果性、富集与机制
- 评估实验系统的适用范围：体外 / 体内 / 离体 / 临床数据的局限性
- 应用生物学证据等级（遗传扰动 > 生化重建 > 药理 > 相关性组学）
- 识别生物学特有混杂因素：基因冗余、代偿效应、细胞组成偏差、模式生物转化差距、过表达伪影、批次效应
- 根据证据强度校准结论语言
- 明确界定解释边界：物种范围、细胞类型范围、疾病背景
- 建议最低成本的鉴别性下一步实验

## 多平台支持

兼容所有主流支持 [Agent Skills](https://agentskills.io) 格式的 AI 智能体：

| 平台 | 支持状态 | 说明 |
| ------ | ---------- | ------ |
| **Claude Code** | ✅ 完全支持 | 原生 SKILL.md 格式 |
| **OpenClaw / ClawHub** | ✅ 完全支持 | `metadata.openclaw` 命名空间 |
| **Hermes Agent** | ✅ 完全支持 | `metadata.hermes` 命名空间，category: research |
| **Pi-Mo** | ✅ 完全支持 | `metadata.pimo` 命名空间 |
| **SkillsMP** | ✅ 可索引 | GitHub topics 已配置 |

## 有 skill 与无 skill 的对比

| 能力 | 原生智能体 | 本 skill |
| ------ | ----------- | --------- |
| 区分标志物与驱动因子 | 否 | 是 — 需要功能性扰动验证 |
| 评估实验系统 | 否 | 是 — 体外 / 体内 / 临床范围 |
| 应用生物学证据等级 | 否 | 是 — 8 级证据层次 |
| 标注模式生物转化差距 | 否 | 是 — 明确物种范围 |
| 识别组学中的组成偏差 | 否 | 是 — 排除成分混杂后再得出结论 |
| 正确处理阴性表型 | 否 | 是 — 考虑冗余与代偿 |
| 区分富集与通路活性 | 否 | 是 — 富集分数 ≠ 通路激活 |
| 标注声明来源 | 否 | 是 — 数据 / 背景知识 / 推断 |
| 校准语言到证据 | 否 | 是 — 6 级量表 |
| 建议鉴别性下一步实验 | 否 | 是 |

## 适用场景

- 解读细胞生物学、遗传学、基因组学、免疫学、神经科学等领域的实验结果
- 分析分子机制、信号通路或基因调控网络
- 评估表型–基因型关系
- 设计或评估实验系统
- 解读组学数据（bulk/scRNA-seq、ATAC-seq、蛋白质组学、GWAS 等）
- 评估模式生物研究结果向人类的转化潜力
- 构建学术写作中的科学论证
- 调和不同文献或实验系统之间相互矛盾的发现
- 任何存在过度解读机制风险的生物学问题

## skill 安装

### Claude Code

```bash
# 全局安装（在所有项目中可用）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.claude/skills/scientific-thinking-biology

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" .claude/skills/scientific-thinking-biology
```

### OpenClaw / ClawHub

```bash
# 通过 ClawHub
clawhub install scientific-thinking-biology

# 手动安装
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.openclaw/skills/scientific-thinking-biology

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" skills/scientific-thinking-biology
```

### Hermes Agent

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/scientific-thinking-biology/skills/scientific-thinking-biology" ~/.hermes/skills/research/scientific-thinking-biology
```

或在 `~/.hermes/config.yaml` 中添加：

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

### 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
| ------ | ---------- | ---------- |
| Claude Code | `~/.claude/skills/scientific-thinking-biology/` | `.claude/skills/scientific-thinking-biology/` |
| OpenClaw | `~/.openclaw/skills/scientific-thinking-biology/` | `skills/scientific-thinking-biology/` |
| Hermes Agent | `~/.hermes/skills/research/scientific-thinking-biology/` | 通过 `external_dirs` 配置 |
| Pi-Mo | `~/.pimo/skills/scientific-thinking-biology/` | — |

## 文件说明

- `SKILL.md` — **唯一必需文件**。所有平台均加载此文件作为 skill 指令。
- `checks.md` — SKILL.md 引用的 15 项自检清单（通用 + 生物学专项）
- `examples.md` — SKILL.md 引用的 10 个生物学场景示例
- `README.md` — 英文文档
- `README_CN.md` — 本文件（中文）

> **注意：** 只需要 `SKILL.md` 即可使 skill 正常工作，其他文件均为辅助文件。

## 相关 skill

- [scientific-thinking-general](https://github.com/Agents365-ai/365-skills/tree/main/plugins/scientific-thinking-biology/skills/scientific-thinking-biology) — 本 skill 所基于的通用领域版本
- [literature-review](https://github.com/Agents365-ai/zotero-research-assistant) — 系统性文献综述工作流
- [nh-bioinfo-practice-skill](https://github.com/Agents365-ai) — 单细胞与空间组学分析

## GitHub Topics

用于 SkillsMP 索引，本仓库使用以下 topics：

`claude-code` `claude-code-skill` `claude-skills` `agent-skills` `skillsmp` `skill-md` `scientific-thinking` `biology` `life-science` `genomics` `cell-biology` `immunology` `neuroscience` `research` `reasoning`

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
