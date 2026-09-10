# paper-fetch — 按 DOI 自动下载论文 PDF

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-paper-fetch-skills-paper-fetch-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/paper-fetch-pro-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[English](README.md) · **中文** · [📖 在线文档](https://agents365-ai.github.io/paper-fetch/zh.html)

将 DOI（或标题）解析为 PDF — 7 源回退链：[Unpaywall](https://unpaywall.org) → [Semantic Scholar](https://www.semanticscholar.org) → [arXiv](https://arxiv.org) → [PubMed Central](https://pmc.ncbi.nlm.nih.gov) → [bioRxiv](https://www.biorxiv.org)/[medRxiv](https://www.medrxiv.org) → 出版商直链 → [Sci-Hub](https://www.sci-hub.pub) 镜像。纯 Python 标准库，agent 原生 CLI，稳定 JSON 信封。

## 功能简介

**DOI（或标题）→ PDF**

- 7 源回退链：[Unpaywall](https://unpaywall.org) → [Semantic Scholar](https://www.semanticscholar.org) → [arXiv](https://arxiv.org) → [PubMed Central](https://pmc.ncbi.nlm.nih.gov) → [bioRxiv](https://www.biorxiv.org)/[medRxiv](https://www.medrxiv.org) → 出版商直链 *（机构模式启用）* → [Sci-Hub](https://www.sci-hub.pub) 镜像 *（默认开启的兜底）*
- 仅有标题时通过 `--title` 解析 — Crossref + Semantic Scholar 双路回退，附置信度标记
- 自动命名：`{第一作者}_{年份}_{期刊简称}_{简短标题}.pdf`

**批量 + Agent 友好**

- `--batch dois.txt` 或 `--batch -`（stdin）批量下载
- `--idempotency-key` 重试时直接复用原信封，无任何网络 I/O
- `--stream` 在每个 DOI 解析完成时立即输出一行 NDJSON
- 已下载文件默认跳过；`--overwrite` 强制覆盖

**内置正确性保障**

- stdout 稳定 JSON 信封，stderr NDJSON 进度，机器可读的 `schema` 子命令
- `--format` 自动识别 TTY,退出码分类（`0`/`1`/`3`/`4`)便于 orchestrator 路由
- 每次外部抓取都执行 SSRF 防护 + `%PDF` 魔数校验 + 50 MB 体积上限
- 零运行时依赖 — 纯 Python 标准库

**Cloudflare 拦截的 PDF** *(可选)*

- `PAPER_FETCH_CLOAK=1` 会将被 403/429 拦截或遇到 JS 挑战的 PDF 链接,改用 [CloakBrowser](https://github.com/CloakHQ/CloakBrowser)(可通过挑战的隐身 Chromium)重试(方案借鉴自 [cloakFetch](https://github.com/Agents365-ai/cloakFetch))
- 位于下载层,因此对所有源生效;默认关闭、失败时静默回退、仅由操作者控制
- 返回的字节仍经过相同的 `%PDF` + 体积校验;结果带 `via: "cloak"` 标记

兼容 Claude Code、Codex、Hermes、OpenClaw、ClawHub、pi-mono、SkillsMP — 所有支持 [Agent Skills](https://agentskills.io) 格式的 Agent。

## 学科覆盖

本 skill **学科无关**,不限于生命科学或 CS。

| 来源 | 学科范围 |
| --- | --- |
| Unpaywall | ✅ 全学科(覆盖 Crossref 所有 DOI — 人文、社科、物理、化学、经济等) |
| Semantic Scholar | ✅ 全学科(跨领域学术图谱) |
| arXiv | 物理、数学、CS、统计、定量金融、经济学、EE |
| PubMed Central | 仅生物医学 |
| bioRxiv / medRxiv | 仅生物 / 医学预印本 |
| Sci-Hub | ✅ 全学科(兜底) |

实际使用中，**仅 Unpaywall + Semantic Scholar 两个源就足以覆盖化学、材料、经济、心理学、人文社科等任何领域的 OA 论文** — 它们会自动命中机构知识库、SSRN、RePEc 以及出版商自托管的 OA 版本。

## 对比

### vs 原生 agent(无 skill)

| 功能 | 原生 agent | 本 skill |
| --- | --- | --- |
| DOI → PDF | 临时网络搜索 | 确定性 7 源链 |
| 标题 → DOI | 手动 | `--title`(Crossref + S2 回退,附置信度标记) |
| 批量下载 | ❌ | ✅ `--batch dois.txt` 或 `--batch -` |
| 一致的文件命名 | ❌ | ✅ `author_year_journal_title.pdf` |
| 机器可读 schema | ❌ | ✅ `fetch.py schema` |
| 结构化输出 | ❌ | ✅ JSON 信封 + NDJSON 进度 |
| 幂等重试 | ❌ | ✅ `--idempotency-key` |
| 退出码分类 | ❌ | ✅ `0`/`1`/`3`/`4` |
| SSRF + `%PDF` + 体积上限 | ❌ | ✅ 强制启用 |

## 环境要求

- `python3`(3.8+,仅标准库,无需 `pip install`)
- (推荐)[Unpaywall 联系邮箱](https://unpaywall.org/products/api):

  ```bash
  export UNPAYWALL_EMAIL=you@example.com
  ```

未设置时跳过 Unpaywall,其余 6 个源仍正常工作。

## 安装

```bash
# 任意 Agent(Claude Code、Cursor、Copilot 等)
npx skills add Agents365-ai/365-skills -g

# 仅 Claude Code
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install paper-fetch
```

也已发布到 [SkillsMP](https://skillsmp.com/) 与 [ClawHub](https://clawhub.ai/),它们各自的市场负责更新。

## 使用

直接用自然语言告诉 Agent:

```
> 把 AlphaFold2 论文的 PDF 下载到 ~/papers

> 帮我下 DOI 10.1038/s41586-020-2649-2

> 把 dois.txt 里的全部 DOI 批量下载

> 找 "Attention Is All You Need" 这篇论文的 PDF 并保存

> 不下载,只预览 10.1126/science.abj8754 解析出的 PDF 链接
```

或直接调用脚本:

```bash
# 单个 DOI
python skills/paper-fetch/scripts/fetch.py 10.1038/s41586-021-03819-2

# 仅有标题(经 Crossref + S2 回退解析为 DOI 后下载)
python skills/paper-fetch/scripts/fetch.py --title "Highly accurate protein structure prediction with AlphaFold"

# 干跑预览(不下载)
python skills/paper-fetch/scripts/fetch.py 10.1038/s41586-020-2649-2 --dry-run

# 批量 + 幂等键
python skills/paper-fetch/scripts/fetch.py --batch dois.txt --out ~/papers \
    --idempotency-key monday-review-batch

# 从其他工具用管道传 DOI
echo 10.1038/s41586-021-03819-2 | python skills/paper-fetch/scripts/fetch.py --batch -

# Agent 自描述
python skills/paper-fetch/scripts/fetch.py schema --pretty
```

完整参数与 JSON 信封 schema 见 [`skills/paper-fetch/SKILL.md`](skills/paper-fetch/SKILL.md)。

## 机构访问(可选)

如所在机构有出版商订阅,设 `PAPER_FETCH_INSTITUTIONAL=1` 启用出版商直链回退。授权由你的 IP / cookies / EZproxy 完成;为避免触发出版商 ToS, skill 会自动加 1 req/s 限速。

```bash
export PAPER_FETCH_INSTITUTIONAL=1
```

## 通过 CloakBrowser 抓取 Cloudflare 拦截的 PDF(可选)

部分出版商(如 `science.org`)位于 Cloudflare 之后,会向普通 HTTP 客户端返回 `403`/`429` 或 "Just a moment…" JS 挑战页,而非 PDF。设 `PAPER_FETCH_CLOAK=1` 即可将这些链接改用 [CloakBrowser](https://github.com/CloakHQ/CloakBrowser)(可通过挑战的隐身 Chromium)重试。方案借鉴自 [cloakFetch](https://github.com/Agents365-ai/cloakFetch)。

```bash
# 需要一个可 import cloakbrowser 的 Python(pip install cloakbrowser)
export PAPER_FETCH_CLOAK=1
export CLOAKBROWSER_PYTHON="$HOME/github/CloakBrowser/.venv/bin/python"  # 若未自动识别
export PAPER_FETCH_CLOAK_HEADED=1   # 针对 headless 无法通过的强挑战(如 science.org)
```

该回退位于下载层(覆盖所有源),返回字节仍经过相同的 `%PDF` + 50 MB 校验,CloakBrowser 不可用时静默回退,且仅由操作者控制 —— Agent 无法自行启用。成功的 cloak 下载结果带 `via: "cloak"`。

浏览器默认 **headless**;较强的挑战(如 `science.org`)在 headless 下会卡在 "Just a moment…",此时设 `PAPER_FETCH_CLOAK_HEADED=1` 用可见窗口通过(需要显示环境)。页面内 fetch 为 **同源**,因此适用于被拦截主机上的直链 PDF(如 `www.science.org/doi/pdf/…`);跨源重定向的链接会静默回退。详见 [`skills/paper-fetch/SKILL.md`](skills/paper-fetch/SKILL.md)(*CloakBrowser access*)。

## 已知限制

- **部分出版商重定向**会返回 HTML 落地页,`%PDF` 魔数校验会拒绝
- **默认不做浏览器自动化** — 不解 CAPTCHA、不用 Playwright、不做反指纹绕过。(浏览器自动化是独立的可选项:上面 `PAPER_FETCH_CLOAK` 控制的 CloakBrowser 回退。)
- **SSRF 防护**会拒绝私网 IP、非 http(s) 协议、非 80/443 端口、云元数据主机
- **每个 PDF 体积上限 50 MB**

## 🔗 相关 Skills

属于 [Agents365-ai 学术研究 skill 系列](https://github.com/Agents365-ai) —— 按需挑选合适的工具：

| Skill | 定位 | 何时使用 |
| --- | --- | --- |
| [semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) | Semantic Scholar API 检索 | 下载前先 **找** 论文时 |
| [asta-skill](https://github.com/Agents365-ai/asta-skill) | 经 Ai2 Asta MCP 访问相同语料 | 宿主支持 MCP 且有 Asta API key 时 |
| [scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) | 8 阶段文献综述流水线 | 需要的不只是 PDF，而是带引用的结构化报告 |
| [zotero-research-assistant](https://github.com/Agents365-ai/zotero-research-assistant) | Zotero 文献库工作流 | 把文献存进 Zotero 时 |

## ❤️ 支持作者

如果这个 skill 对你有帮助，欢迎打赏支持作者：

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
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 License

[MIT](LICENSE)
