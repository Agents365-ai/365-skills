# Journal IF — 期刊影响因子查询技能

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/journal-if?style=flat&logo=github)](https://github.com/Agents365-ai/journal-if/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/journal-if?style=flat&logo=github)](https://github.com/Agents365-ai/journal-if/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/journal-if?logo=github)](https://github.com/Agents365-ai/journal-if/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/journal-if?logo=github)](https://github.com/Agents365-ai/journal-if/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[English](README.md)

一个用于查询期刊影响因子（JCR IF）的 Claude Code 技能。内置 ~200 本顶级期刊数据，并通过 OpenAlex API 回退覆盖全球任意期刊。

<img src="https://raw.githubusercontent.com/Agents365-ai/journal-if/main/docs/workflow_CN.drawio.png" width="600" alt="工作流程">

## 功能特性

| 功能 | 原生 Claude Code | Journal IF |
| ------ | ----------------- | ------------ |
| 影响因子查询 | 可能产生幻觉 / 数据过时 | 精选 CSV + 实时 API，结果准确 |
| 批量处理 | 不支持 | 每行一个期刊名，部分成功信封 |
| 模糊搜索 | 不支持 | 子串匹配，支持分页 |
| 离线查询 | 不支持 | `--offline` 参数使用内置 CSV |
| Agent-native 输出 | — | 稳定 JSON 信封，独立退出码，可重试错误 |

## 数据来源

1. **内置 CSV** — ~200 本顶级期刊，涵盖生命科学、医学、化学、物理和工程领域。精选自 JCR 2023 数据，随技能附带。即时查询，始终可用。

2. **OpenAlex API** — 免费开放的 API，基于引用计数计算近似的 2 年影响因子。覆盖几乎所有学术期刊。该数值与官方 JCR IF 有所不同 —— 适合排名和比较，在正式场合请注明为近似值。

## 安装

技能本体位于 `skills/journal-if/`（包含 `SKILL.md` 和 `journal_if.py`）。
推荐通过插件市场安装，会自动处理升级：

```bash
# Claude Code 插件市场（推荐）
/plugin marketplace add Agents365-ai/365-skills
/plugin install journal-if

# 任意 Agent（Claude Code、Cursor、Copilot 等）
npx skills add Agents365-ai/365-skills -g
```

也发布在 [ClawHub](https://clawhub.ai/) 与 [SkillsMP](https://skillsmp.com)
上 —— 各自的市场都会处理升级。

也可以手动把 skill bundle 安装到任意支持 `SKILL.md` 的平台：

| 平台 | 安装命令 |
| --- | --- |
| **Claude Code**（全局） | `git clone https://github.com/Agents365-ai/journal-if.git /tmp/ji && cp -r /tmp/ji/skills/journal-if ~/.claude/skills/ && rm -rf /tmp/ji` |
| **Claude Code**（项目） | `git clone https://github.com/Agents365-ai/journal-if.git /tmp/ji && cp -r /tmp/ji/skills/journal-if .claude/skills/ && rm -rf /tmp/ji` |
| **OpenClaw**（全局） | 把上面命令里的 `~/.claude/skills/` 换成 `~/.openclaw/skills/` |

或者直接克隆仓库运行 CLI —— 纯 Python 3.9+ 标准库实现，
无任何第三方依赖，在 macOS、Linux、Windows 上均可运行：

```bash
git clone https://github.com/Agents365-ai/journal-if.git
cd journal-if/skills/journal-if
python3 journal_if.py lookup "Nature Medicine"
python3 journal_if.py schema              # 完整机器可读的 CLI 契约
```

## 使用方法

### 自然语言

直接向 Claude 提问：

- "Nature Medicine 的影响因子是多少？"
- "比较一下 Cell 和 Science 的影响因子"
- "免疫学领域有哪些 IF > 20 的期刊？"
- "帮我查一下这个期刊列表的影响因子"

### 命令行

```bash
# 单本期刊查询
python3 journal_if.py lookup "Nature Medicine"

# 模糊搜索（支持分页）
python3 journal_if.py search "免疫" --limit 10 --offset 0

# 批量查询（每行一个期刊名）
python3 journal_if.py batch journals.txt

# 纯离线模式（不访问网络）
python3 journal_if.py --offline lookup "Cell"

# 缓存管理
python3 journal_if.py cache status                # 查看本地缓存状态
python3 journal_if.py cache update                # 刷新上游 CSV

# 机器可读的命令契约（供 AI 智能体或自动化工具使用）
python3 journal_if.py schema
python3 journal_if.py schema lookup
```

### Agent-native 输出契约

当标准输出不是终端（例如被管道捕获、被智能体运行时读取）时，`stdout` 默认输出
稳定的 JSON 信封；在终端下则输出人类友好的表格或缩进视图。所有响应共用同一信封结构：

- 成功: `{"ok": true, "data": ..., "meta": {"schema_version", "cli_version", "latency_ms"}}`
- 部分成功（batch）: `{"ok": "partial", "data": {"succeeded": [...], "failed": [...]}}`
- 错误: `{"ok": false, "error": {"code", "message", "retryable", ...}}`

`error.code` 字段稳定。主要的错误码：

| 错误码 | 可重试 | 退出码 | 含义 |
| -------- | -------- | -------- | ------ |
| `not_found` | 否 | 3 | 查询完成，但所有数据源都未命中 |
| `upstream_unavailable` | **是** | 1 | OpenAlex API 瞬时失败；稍后重试或使用 `--offline` |
| `file_not_found` / `validation_error` | 否 | 2 | 输入不合法 |
| `runtime_error` | 是 | 1 | 未预期的内部错误 |

请基于 `error.code` + `error.retryable` 来分支重试逻辑，不要只看退出码 —— 退出
`1` 同时覆盖瞬时错误和运行时错误。可用 `--format json|table|human` 强制格式
（`--json` 是旧版兼容别名）；所有全局参数可以放在子命令前或后。

### 影响因子解读

| IF 范围 | 典型层级 | 示例 |
| --------- | --------- | ------ |
| > 30 | 顶级（前 0.1%） | Nature (64.8)、Science (56.9)、Cell (64.5) |
| 20–30 | 卓越（前 1%） | Cancer Cell (50.3)、Immunity (32.4) |
| 10–20 | 优秀（前 5%） | Nature Communications (16.6)、Sci Adv (13.6) |
| 5–10 | 良好（前 15%） | eLife (7.7)、Cell Reports (8.8) |
| 2–5 | 扎实 | PLOS ONE (3.7)、Sci Rep (4.6) |
| < 2 | 细分/新刊 | 许多领域专刊和新创期刊 |

**注意：** 影响因子因学科差异巨大 —— 请始终在同一领域内比较。
OpenAlex 近似 IF 与官方 JCR IF 不同；用于排名参考，不用于正式引用。

## 依赖

- Python 3.9+（无需安装第三方包）

## ❤️ 支持

如果这个技能对你有帮助，欢迎打赏支持作者：

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
      <b>打赏</b>
    </td>
  </tr>
</table>

## 👤 作者

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- B站: <https://space.bilibili.com/441831884>

## 📄 License

CC BY-NC 4.0 — 非商业用途免费。商业用途需授权。
