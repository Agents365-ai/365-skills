# Journal Meta — 论文元数据查询技能

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/journal-meta?style=flat&logo=github)](https://github.com/Agents365-ai/journal-meta/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/journal-meta?style=flat&logo=github)](https://github.com/Agents365-ai/journal-meta/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/journal-meta?logo=github)](https://github.com/Agents365-ai/journal-meta/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/journal-meta?logo=github)](https://github.com/Agents365-ai/journal-meta/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[English](README.md)

一个 Claude Code 技能：只需一个论文标识（**DOI、PMID、arXiv id、OpenAlex id 或标题**），
即可返回完整的元数据记录——标题、全部作者、第一作者、通讯作者、发表日期、期刊名称与
ISO-4 缩写、影响因子、卷/期/页码、DOI/PMID、被引次数和摘要。

## 工作流程

![Journal Meta 工作流程](docs/workflow_CN.drawio.png)

## 为什么需要它

| 字段 | 原生 Claude Code | Journal Meta |
| ------ | ------------------ | -------------- |
| 标题 / 作者 / 日期 / 期刊 | 凭记忆猜测 | 从 OpenAlex 解析（Crossref 兜底） |
| 第一作者 | 不明确 | `author_position == first` |
| 通讯作者 | 无法获取 | OpenAlex `is_corresponding`（绝不臆测） |
| 期刊缩写 | 人工猜测 | 委托 **journal-abbrev**（ISO-4，约 2.5 万期刊） |
| 影响因子 | 无法获取 | 委托 **journal-if**（JCR 精选数据） |
| 批量 DOI/PMID | 不支持 | `batch file.txt` |

## 工作原理

1. **OpenAlex**（免费、无需密钥）解析标识并提供几乎所有字段，包括通讯作者标记；
   对 OpenAlex 尚未收录的 DOI，用 **Crossref** 兜底。
2. 期刊名称在两个同级技能已安装时**委托它们**做增强：
   - [`journal-abbrev`](https://github.com/Agents365-ai/journal-abbrev) → ISO-4 期刊缩写；
   - [`journal-if`](https://github.com/Agents365-ai/journal-if) → JCR 精选影响因子；
   - 若未找到这两个技能，则自动回退到 AbbrevISO（缩写）与 OpenAlex 两年平均被引
     （近似影响因子）。`meta.sources` 始终标明数据来源。

## 用法

```bash
# 通过 DOI
python3 journal_meta.py "10.1038/s41586-020-2649-2"

# 通过 PMID / arXiv id / 标题
python3 journal_meta.py 32939066
python3 journal_meta.py 1706.03762
python3 journal_meta.py "Attention is all you need"

# 批量，每行一个标识
python3 journal_meta.py batch papers.txt

# 跳过增强，或强制 JSON 输出
python3 journal_meta.py <id> --no-if --no-abbrev
python3 journal_meta.py <id> --format json
```

在终端下输出人类可读的键值视图，管道/捕获时输出稳定的 JSON 信封。
`meta.sources` 记录缩写与影响因子的具体来源。

## 配置

| 环境变量 | 作用 |
| ---------- | ------ |
| `JOURNAL_META_MAILTO` / `OPENALEX_MAILTO` | OpenAlex 礼貌池所用邮箱（推荐设置）。 |
| `JOURNAL_ABBREV_CLI` | `journal-abbrev` 的 `jabbrv.py` 显式路径。 |
| `JOURNAL_IF_CLI` | `journal-if` 的 `journal_if.py` 显式路径。 |

## 注意事项

- **通讯作者**依赖 OpenAlex 的 `is_corresponding` 标记，仅当出版商提供时才有——
  空列表意味着「元数据未标注」，而非「没有通讯作者」。本技能绝不臆测。
- **影响因子**来自 `journal-if` 时为 JCR 精选值；回退值为 OpenAlex 近似值，并在
  `impact_factor_source` 中明确标注。
- **标题检索**只取 OpenAlex 排名第一的结果；如需正式版本，请优先用 DOI 或 PMID。

## 依赖

- Python 3（仅标准库，无需第三方包）。
- 推荐同时安装 `journal-abbrev` 与 `journal-if` 技能，以获得精选的缩写与影响因子。

**兼容：** Claude Code 以及任何可运行 Python CLI 的编码代理。

## ❤️ 支持

如果这个技能对你有帮助，欢迎支持作者：

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
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="打赏">
      <br>
      <b>打赏鼓励</b>
    </td>
  </tr>
</table>

## 👤 作者

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 许可证

CC BY-NC 4.0 — 非商业用途免费，商业用途需获得授权。
