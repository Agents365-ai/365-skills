# asta-skill — 通过 Ai2 Asta MCP 访问 Semantic Scholar

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/asta-skill?style=flat&logo=github)](https://github.com/Agents365-ai/asta-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/asta-skill?style=flat&logo=github)](https://github.com/Agents365-ai/asta-skill/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/asta-skill?logo=github)](https://github.com/Agents365-ai/asta-skill/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/asta-skill?logo=github)](https://github.com/Agents365-ai/asta-skill/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-asta-skill-skills-asta-skill-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/asta-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[English](README.md) · **中文** · [Asta MCP 介绍](https://allenai.org/asta/resources/mcp) · [申请 API Key](https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm)

Ai2 的 Asta MCP server(Semantic Scholar)可在**任意支持 MCP 的 agent** 上运行 —— 本仓库在其之上额外提供一个*可选*的纯指令包技能,把自然语言研究问题转换为规范的工具调用:负责意图路由 → 工具选择、安全默认值填充、工作流编排,并提示常见陷阱。只要注册好 MCP server,就能在 **Claude Code、Cursor、Codex、Windsurf、Trae、Qoder、CodeBuddy/WorkBuddy、Hermes、opencode、OpenClaw、pi-mono** 以及任何支持 MCP 的 agent 上调用 Asta;在任意兼容 [Agent Skills](https://agentskills.io) 的 host 上再加载本技能可获得更精准的结果。

## 功能特性

- **搜索** Semantic Scholar 学术语料库,支持关键词、标题、作者、全文片段多种检索方式
- **查论文** —— 支持 DOI、arXiv、PMID、PMCID、CorpusId、MAG、ACL、SHA、URL 等任意 ID 格式
- **引用遍历** —— 查找某篇论文被谁引用,支持过滤与分页
- **批量查找** —— 通过 `get_paper_batch` 一次查询多篇论文
- **片段检索** —— 从论文正文中提取 ~500 词的相关段落,用于证据溯源
- **作者检索** —— 查找研究者并列出其发表论文
- **零代码集成** —— 本技能是纯指令包,所有 I/O 通过 Asta MCP server 完成
- 当用户提出论文、引用、学术搜索、文献发现相关需求且 Asta 工具已注册时自动触发

## 多平台支持

**任何支持 MCP 的工具都能调用 Asta** —— 本技能只是其上一个可选的 [Agent Skills](https://agentskills.io) 层。已在 **Claude Code、Codex、Cursor、Devin Desktop(原 Windsurf)、Hermes、opencode、OpenClaw/ClawHub、[pi-mono](https://github.com/badlogic/pi-mono)** 上验证,并收录于 **SkillsMP**。下方[安装](#安装)一节还提供了 **Gemini CLI、GitHub Copilot、Cline、Trae、通义灵码 Lingma、CodeBuddy/WorkBuddy、Qoder、Claude Desktop、LM Studio** 的可复制配置。不自动加载 skills 的桌面端(Claude Desktop、LM Studio)连上 MCP 后工具即可用 —— 把 `SKILL.md` 粘到 system prompt 即可补上路由层。

`SKILL.md` 的 frontmatter 仅在顶层保留 `name`、`description`、`license`,其余字段全部嵌套在 `metadata` 下,因此能通过 Codex 等更严格的 skill frontmatter 解析器的校验。

## 前置条件

- 任意支持 MCP 的 agent host(Claude Code、Cursor、Codex、Gemini CLI、GitHub Copilot、Cline、Devin Desktop、Trae、通义灵码 Lingma、CodeBuddy/WorkBuddy、Qoder、opencode、OpenClaw/ClawHub、pi-mono 等)
- Asta API key —— [点此申请](https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm)

  ```bash
  export ASTA_API_KEY=xxxxxxxxxxxxxxxx
  ```

## 安装

**注册 MCP server 就够了** —— Asta 可在**任意支持 MCP 的 agent** 上运行,server 一连上工具即可用。[第 2 步](#第-2-步安装技能可选)只是加了一个*可选*的指令层(意图路由 → 工具选择、安全默认值、陷阱提示),没有它工具照样能用。

### 第 1 步：注册 Asta MCP 服务器

所有 host 都指向同一个端点 —— **`https://asta-tools.allen.ai/mcp/v1`**,streamable HTTP,用 **`x-api-key`** 请求头鉴权。唯一的坑是各家字段名不一样(`url` / `serverUrl` / `httpUrl`,`mcpServers` / `servers`),还有少数无法附加自定义请求头 —— 这些改用 [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) 桥接。展开你用的 agent:

**终端 / CLI**

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add -t http -s user asta https://asta-tools.allen.ai/mcp/v1 \
  -H "x-api-key: $ASTA_API_KEY"
```

重启 Claude Code,MCP 工具会在会话启动时加载。

</details>

<details>
<summary><b>Codex CLI</b></summary>

编辑 `~/.codex/config.toml`:

```toml
[mcp_servers.asta]
url = "https://asta-tools.allen.ai/mcp/v1"
env_http_headers = { "x-api-key" = "ASTA_API_KEY" }
```

Codex 通过 `url` 自动识别 streamable HTTP。`env_http_headers` 把请求头映射到**读取其值的环境变量名** —— 需 export `ASTA_API_KEY`。若想写死 key,改用 `http_headers = { "x-api-key" = "<YOUR_API_KEY>" }`。

</details>

<details>
<summary><b>Gemini CLI</b></summary>

编辑 `~/.gemini/settings.json` —— 注意 Gemini CLI 用 **`httpUrl`** 表示 streamable HTTP:

```json
{
  "mcpServers": {
    "asta": {
      "httpUrl": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "<YOUR_API_KEY>" }
    }
  }
}
```

</details>

<details>
<summary><b>GitHub Copilot CLI</b></summary>

一行命令（或交互式 `/mcp add`）：

```bash
copilot mcp add --transport http --header "x-api-key: <YOUR_API_KEY>" \
  asta https://asta-tools.allen.ai/mcp/v1
```

或编辑 `~/.copilot/mcp-config.json`：

```json
{
  "mcpServers": {
    "asta": {
      "type": "http",
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "<YOUR_API_KEY>" },
      "tools": ["*"]
    }
  }
}
```

（旧的 `gh copilot` 扩展 —— `suggest`/`explain` —— 只是命令建议助手,不托管 MCP。）

</details>

**编辑器 / IDE**

<details>
<summary><b>Cursor</b></summary>

编辑 `~/.cursor/mcp.json`(全局)或 `.cursor/mcp.json`(项目级):

```json
{
  "mcpServers": {
    "asta": {
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "${env:ASTA_API_KEY}" }
    }
  }
}
```

Cursor 会从 shell 展开 `${env:ASTA_API_KEY}`(或直接写死 key)。重载后在 **Settings → MCP** 里确认该 server 变绿。

</details>

<details>
<summary><b>GitHub Copilot(VS Code / Visual Studio)</b></summary>

新建 `.vscode/mcp.json` —— VS Code 的根键是 **`servers`**,不是 `mcpServers`:

```json
{
  "servers": {
    "asta": {
      "type": "http",
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "${env:ASTA_API_KEY}" }
    }
  }
}
```

在 Copilot Chat 里打开 **Agent 模式**,再从 `mcp.json` 的行号旁操作启动该 server。

</details>

<details>
<summary><b>Cline</b></summary>

MCP Servers → **Remote Servers**,或编辑 `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "asta": {
      "type": "streamableHttp",
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "<YOUR_API_KEY>" }
    }
  }
}
```

务必显式写 `"type": "streamableHttp"` —— 不写会回退到旧的 SSE 传输。

</details>

<details>
<summary><b>Devin Desktop(原 Windsurf)</b></summary>

Windsurf 已于 2026-06-02 更名为 **Devin Desktop**,原有 MCP 配置自动迁移。编辑 `mcp_config.json`(迁移前的 Windsurf 路径:`~/.codeium/windsurf/mcp_config.json`)—— 注意键名是 **`serverUrl`**,不是 `url`:

```json
{
  "mcpServers": {
    "asta": {
      "serverUrl": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "${env:ASTA_API_KEY}" }
    }
  }
}
```

然后在 MCP 面板点 **Refresh**。(单独发布的 *Windsurf Plugin*(VS Code / JetBrains 插件)保留原名,用下方通用块即可。)

</details>

**国内 IDE**

<details>
<summary><b>Trae(字节跳动)</b></summary>

AI 侧边栏 → **MCP** → **Add** → **Add Manually**,粘贴:

```json
{
  "mcpServers": {
    "asta": {
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "<YOUR_API_KEY>" }
    }
  }
}
```

</details>

<details>
<summary><b>通义灵码 Lingma(阿里云)</b></summary>

MCP 面板 → **添加 MCP** → 表单配置:传输方式选 **SSE / streamable HTTP**,URL 填 `https://asta-tools.allen.ai/mcp/v1`,再加一个请求头 `x-api-key` = `<YOUR_API_KEY>`。灵码也支持脚本(JSON)配置,格式为标准的 `mcpServers` + `url` + `headers`。

</details>

<details>
<summary><b>CodeBuddy / WorkBuddy(腾讯)</b></summary>

编辑 `~/.codebuddy/.mcp.json`(用户级)或 `<项目根>/.mcp.json`:

```json
{
  "mcpServers": {
    "asta": {
      "type": "http",
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "${ASTA_API_KEY}" }
    }
  }
}
```

`${ASTA_API_KEY}` 会从环境变量展开。WorkBuddy 兼容 OpenClaw,所以可选技能也能从其 OpenClaw 技能目录加载。

</details>

<details>
<summary><b>Qoder(阿里)</b></summary>

Qoder 的远程 server JSON 不支持自定义请求头,需用 [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) 桥接(需 [Node.js](https://nodejs.org))。设置(`⌘⇧,`)→ **MCP** → **+ Add**:

```json
{
  "mcpServers": {
    "asta": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://asta-tools.allen.ai/mcp/v1", "--header", "x-api-key:${ASTA_API_KEY}"],
      "env": { "ASTA_API_KEY": "<YOUR_API_KEY>" }
    }
  }
}
```

`x-api-key:${ASTA_API_KEY}` 冒号后**不要加空格**。

</details>

**桌面端 / 本地** —— 连上 MCP 后工具即可用,但这些 host 不自动加载技能,需手动把 `SKILL.md` 粘进去以获得路由层。

<details>
<summary><b>Claude Desktop</b></summary>

Claude Desktop 自带的 **Add custom connector**(添加自定义连接器)界面只支持 OAuth —— 无法附加 Asta 所需的 `x-api-key` 请求头,在那里添加的服务器会注册失败。请改用 [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) 桥接、通过配置文件注册(需安装 [Node.js](https://nodejs.org))。

编辑 `claude_desktop_config.json`(macOS:`~/Library/Application Support/Claude/`,Windows:`%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "asta": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://asta-tools.allen.ai/mcp/v1",
        "--header",
        "x-api-key:${ASTA_API_KEY}"
      ],
      "env": { "ASTA_API_KEY": "<YOUR_API_KEY>" }
    }
  }
}
```

请求头要写成 `x-api-key:${ASTA_API_KEY}`,冒号后**不要加空格** —— Claude Desktop 会按空格拆分 `--header` 参数 —— 并通过 `env` 传入实际 key。然后彻底退出并重开 Claude Desktop。若想要技能的意图路由 / 安全默认值,把 [`skills/asta-skill/SKILL.md`](skills/asta-skill/SKILL.md) 的正文粘贴到某个 Project 的指令中即可。

</details>

<details>
<summary><b>LM Studio</b></summary>

LM Studio(0.3.17+)已支持 MCP,但不会自动加载 Agent Skills。两步即可使用:

1. **注册 MCP server** —— App Settings → Program → Integrations → 编辑 `mcp.json`:

    ```json
    {
      "mcpServers": {
        "asta": {
          "url": "https://asta-tools.allen.ai/mcp/v1",
          "headers": { "x-api-key": "YOUR_ASTA_API_KEY" }
        }
      }
    }
    ```

2. **手动注入技能指令** —— 把 [`skills/asta-skill/SKILL.md`](skills/asta-skill/SKILL.md) 的正文复制到聊天的 System Prompt,让模型按意图路由表和安全默认值调用工具。

需使用**支持 function calling 的本地模型**(如 Qwen2.5-Instruct、Llama 3.1 Instruct、Mistral Nemo、GPT-OSS),纯 chat 模型无法调用 MCP 工具。

</details>

<details>
<summary><b>其他任意 MCP host</b></summary>

指向标准的 streamable HTTP 配置:

```json
{
  "mcpServers": {
    "asta": {
      "url": "https://asta-tools.allen.ai/mcp/v1",
      "headers": { "x-api-key": "<YOUR_API_KEY>" }
    }
  }
}
```

若你的客户端无法给远程 server 附加自定义请求头,用 [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) 桥接(参考上面的 **Qoder** 或 **Claude Desktop** 块)。

</details>

### 第 2 步：安装技能（可选）

跳过这步工具照样能用 —— 这一层只是让工具选择和默认值更精准。技能正文位于仓库内的 `skills/asta-skill/SKILL.md`。最简单的安装方式是通过插件市场。

#### 插件市场(推荐)

```bash
# 任意 agent(Claude Code、Cursor、Copilot 等)
npx skills add Agents365-ai/365-skills -g

# 仅 Claude Code
/plugin marketplace add Agents365-ai/365-skills
/plugin install asta
```

同时收录于 [SkillsMP](https://skillsmp.com/) 与 [ClawHub](https://clawhub.ai/) —— 各自通过自己的市场处理更新。

#### 手动克隆(任意 host)

```bash
git clone https://github.com/Agents365-ai/asta-skill.git /tmp/asta-skill
cp -r /tmp/asta-skill/skills/asta-skill <你的-host-的-skills-目录>/asta-skill
```

### 验证

注册好 MCP server、安装好技能并重启 host 后,向 agent 提问:

> "用 Asta 查论文 ARXIV:1706.03762,字段要 title,year,authors,venue,tldr"

成功调用应返回 *Attention Is All You Need*,NeurIPS 2017,Vaswani 等人,含 TLDR。

## 使用方式

直接用自然语言描述需求即可:

```
> 用 Asta 查一下 DOI 10.48550/arXiv.1706.03762 这篇论文

> 在 Asta 上搜索 2023 年以来 NeurIPS 的 mixture-of-experts 论文

> "Attention Is All You Need" 被哪些论文引用?按引用数排前 20

> 在 Asta 语料库中查找提到 "flash attention latency" 的段落

> 在 Asta 上找 Yann LeCun,列出他 2024 年的论文
```

技能会选对 Asta 工具、附上安全的 `fields` 参数,并遵循文档中的工作流模板。

### 示例：检索 + 批量下载（与 `paper-fetch` 联用）

`asta-skill` 只负责**检索和元数据获取**,不下载 PDF。如果要从搜索结果直接拿到本地 PDF,可与 `paper-fetch` 技能(或任意基于 DOI 的下载工具)串联使用:

```
> 用 Asta 检索 2022 年以来 "single-cell ATAC-seq batch correction" 引用最高的 5 篇论文,
  然后把 DOI 交给 paper-fetch 批量下载到 ./papers/ 目录
```

底层流程:

1. **asta-skill** → 调用 `search_papers_by_relevance`,参数 `publication_date_range="2022:"`,`fields=title,year,authors,venue,tldr,externalIds`(注意带上 `externalIds` 才能拿到 DOI)
2. Agent 从结果中提取 `externalIds.DOI`；没有 DOI 时回退到 `externalIds.ArXiv`
3. **paper-fetch** → 批量按 Unpaywall → Semantic Scholar → arXiv → PubMed Central → bioRxiv/medRxiv → publisher-direct → Sci-Hub 顺序解析每个 DOI/arXiv ID
4. PDF 落到 `./papers/`,每篇一个文件

`paper-fetch` 是独立技能,需要下载能力时单独安装。`asta-skill` 本身职责仅限 Semantic Scholar 语料。

**Step 1 — Asta 返回 Top 5 论文(含 DOI)：**

![Asta 检索结果](assets/asta-search.png)

**Step 2 — paper-fetch 把 5 篇 PDF 全部下载到 `./papers/`：**

![paper-fetch 批量下载](assets/asta-paper-fetch.png)

## 🔗 相关技能

属于 [Agents365-ai 科研技能家族](https://github.com/Agents365-ai) —— 按场景挑选合适工具:

| 技能 | 定位 | 何时使用 |
| --- | --- | --- |
| [semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) | 直连 Semantic Scholar API(Python) | 无法使用 MCP,或更想脚本化访问时 |
| [paper-fetch](https://github.com/Agents365-ai/paper-fetch) | DOI → PDF,7 源回退 | 找到引用后需要全文时 |
| [scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) | 8 阶段文献综述流水线 | 用户需要结构化、带引用的综述报告时 |

## ❤️ 支持

如果这个技能对你有帮助,欢迎打赏支持作者:

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
