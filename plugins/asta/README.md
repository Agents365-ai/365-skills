# asta-skill — Semantic Scholar via Ai2 Asta MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/asta-skill?style=flat&logo=github)](https://github.com/Agents365-ai/asta-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/asta-skill?style=flat&logo=github)](https://github.com/Agents365-ai/asta-skill/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/asta-skill?logo=github)](https://github.com/Agents365-ai/asta-skill/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/asta-skill?logo=github)](https://github.com/Agents365-ai/asta-skill/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-asta-skill-skills-asta-skill-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/asta-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
**English** · [中文](README_CN.md) · [Asta MCP Overview](https://allenai.org/asta/resources/mcp) · [Request API Key](https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm)

Ai2's Asta MCP server (Semantic Scholar) runs on **any MCP-capable agent** — this repo adds an *optional* pure instruction-pack skill on top that turns natural-language research questions into well-formed tool calls: it routes intent → tool, fills safe defaults, chains workflows, and warns you off the usual pitfalls. Register the MCP server and you can call Asta from **Claude Code, Cursor, Codex, Windsurf, Trae, Qoder, CodeBuddy/WorkBuddy, Hermes, opencode, OpenClaw, pi-mono**, and anything else that speaks MCP; add the skill (on any [Agent Skills](https://agentskills.io)-compatible host) for sharper results.

## What it does

- **Search** the Semantic Scholar academic corpus by keyword, title, author, or full-text snippet
- **Look up** a paper from any ID (DOI, arXiv, PMID, PMCID, CorpusId, MAG, ACL, SHA, URL)
- **Traverse citations** — find who cited a given paper, with filtering and pagination
- **Batch-lookup** multiple papers in one call via `get_paper_batch`
- **Snippet search** — retrieve ~500-word passages from paper bodies for evidence grounding
- **Author discovery** — find researchers and list their publications
- **Zero-code integration** — the skill is a pure instruction pack; all I/O goes through the Asta MCP server
- Triggers automatically whenever the user asks for papers, citations, academic search, or literature discovery and Asta tools are registered

## Multi-Platform Support

**Anything that speaks MCP can call Asta** — the skill is just an optional [Agent Skills](https://agentskills.io) layer on top. Verified on **Claude Code, Codex, Cursor, Devin Desktop (ex-Windsurf), Hermes, opencode, OpenClaw/ClawHub,** and **[pi-mono](https://github.com/badlogic/pi-mono)**; indexed on **SkillsMP**. The [Installation](#installation) section below has copy-paste setup for those plus **Gemini CLI, GitHub Copilot, Cline, Trae, 通义灵码 Lingma, CodeBuddy/WorkBuddy, Qoder, Claude Desktop,** and **LM Studio**. Desktop hosts that don't auto-load skills (Claude Desktop, LM Studio) still get the tools over MCP — paste `SKILL.md` into the system prompt to add the routing layer.

`SKILL.md`'s frontmatter keeps only `name`, `description`, and `license` at the top level (all other fields are nested under `metadata`), so it validates cleanly under stricter skill-frontmatter parsers such as Codex's.

## Prerequisites

- An agent host with MCP support (Claude Code, Cursor, Codex, Gemini CLI, GitHub Copilot, Cline, Devin Desktop, Trae, 通义灵码 Lingma, CodeBuddy/WorkBuddy, Qoder, opencode, OpenClaw/ClawHub, pi-mono, etc.)
- An Asta API key — [request here](https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm)

  ```bash
  export ASTA_API_KEY=xxxxxxxxxxxxxxxx
  ```

## Installation

**Registering the MCP server is all you strictly need** — Asta runs on **any MCP-capable agent**, and the tools work the moment the server connects. [Step 2](#step-2-install-the-skill-optional) adds an *optional* instruction layer (intent→tool routing, safe defaults, pitfall guards); the tools work fine without it.

### Step 1: Register the Asta MCP Server

Every host points at the same endpoint — **`https://asta-tools.allen.ai/mcp/v1`**, streamable HTTP, authenticated with an **`x-api-key`** header. The only catch is that hosts name the fields differently (`url` vs `serverUrl` vs `httpUrl`, `mcpServers` vs `servers`), and a few can't attach a custom header at all — those bridge through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote). Expand your agent:

**Terminal / CLI**

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add -t http -s user asta https://asta-tools.allen.ai/mcp/v1 \
  -H "x-api-key: $ASTA_API_KEY"
```

Restart Claude Code so the MCP tools load at session start.

</details>

<details>
<summary><b>Codex CLI</b></summary>

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.asta]
url = "https://asta-tools.allen.ai/mcp/v1"
env_http_headers = { "x-api-key" = "ASTA_API_KEY" }
```

Codex infers streamable HTTP from `url`. `env_http_headers` maps the header to the **env-var name** to read from — export `ASTA_API_KEY`. For a literal key, use `http_headers = { "x-api-key" = "<YOUR_API_KEY>" }`.

</details>

<details>
<summary><b>Gemini CLI</b></summary>

Edit `~/.gemini/settings.json` — note Gemini CLI uses **`httpUrl`** for streamable HTTP:

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

One command (or `/mcp add` interactively):

```bash
copilot mcp add --transport http --header "x-api-key: <YOUR_API_KEY>" \
  asta https://asta-tools.allen.ai/mcp/v1
```

Or edit `~/.copilot/mcp-config.json`:

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

(The older `gh copilot` extension — `suggest`/`explain` — is a command helper, not an MCP host.)

</details>

**Editors & IDEs**

<details>
<summary><b>Cursor</b></summary>

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

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

Cursor expands `${env:ASTA_API_KEY}` from your shell (or hardcode the key). Reload, then confirm the server turns green in **Settings → MCP**.

</details>

<details>
<summary><b>GitHub Copilot (VS Code / Visual Studio)</b></summary>

Create `.vscode/mcp.json` — VS Code's root key is **`servers`**, not `mcpServers`:

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

Turn on **Agent mode** in Copilot Chat, then start the server from the `mcp.json` gutter action.

</details>

<details>
<summary><b>Cline</b></summary>

MCP Servers → **Remote Servers**, or edit `cline_mcp_settings.json`:

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

Set `"type": "streamableHttp"` explicitly — omitting it falls back to legacy SSE.

</details>

<details>
<summary><b>Devin Desktop (formerly Windsurf)</b></summary>

Windsurf was rebranded **Devin Desktop** on 2026-06-02; existing MCP settings carry over. Edit `mcp_config.json` (migrated Windsurf path: `~/.codeium/windsurf/mcp_config.json`) — note the key is **`serverUrl`**, not `url`:

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

Then press **Refresh** in the MCP panel. (The separately-shipped *Windsurf Plugin* for VS Code / JetBrains kept its old name — use the generic block below for it.)

</details>

**IDE (China)**

<details>
<summary><b>Trae (ByteDance)</b></summary>

AI sidebar → **MCP** → **Add** → **Add Manually**, then paste:

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
<summary><b>通义灵码 Lingma (Alibaba)</b></summary>

MCP panel → **Add MCP** → form config: set transport to **SSE / streamable HTTP**, URL `https://asta-tools.allen.ai/mcp/v1`, and add a header `x-api-key` = `<YOUR_API_KEY>`. Lingma also accepts the script (JSON) form with the standard `mcpServers` + `url` + `headers` shape.

</details>

<details>
<summary><b>CodeBuddy / WorkBuddy (Tencent)</b></summary>

Edit `~/.codebuddy/.mcp.json` (user scope) or `<project>/.mcp.json`:

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

`${ASTA_API_KEY}` expands from the environment. WorkBuddy is OpenClaw-compatible, so the optional skill also loads from its OpenClaw skills directory.

</details>

<details>
<summary><b>Qoder (Alibaba)</b></summary>

Qoder's remote-server JSON doesn't expose a custom-header field, so bridge through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) (requires [Node.js](https://nodejs.org)). Settings (`⌘⇧,`) → **MCP** → **+ Add**:

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

Write `x-api-key:${ASTA_API_KEY}` with **no space** after the colon.

</details>

**Desktop & local** — MCP tools work once connected, but these hosts don't auto-load skills, so paste `SKILL.md` in manually for the routing layer.

<details>
<summary><b>Claude Desktop</b></summary>

Claude Desktop's built-in **Add custom connector** UI only supports OAuth — it can't attach the `x-api-key` header Asta needs, so a server added there fails to register. Register through the config file using the [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) bridge instead (requires [Node.js](https://nodejs.org)).

Edit `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):

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

Write the header as `x-api-key:${ASTA_API_KEY}` with **no space** after the colon — Claude Desktop splits `--header` args on spaces — and supply the value via `env`. Then fully quit and reopen Claude Desktop. To add the skill's intent routing / safe defaults, paste the body of [`skills/asta-skill/SKILL.md`](skills/asta-skill/SKILL.md) into a Project's instructions.

</details>

<details>
<summary><b>LM Studio</b></summary>

LM Studio (0.3.17+) speaks MCP but does not auto-discover Agent Skills. Two steps:

1. **Register the MCP server** — App Settings → Program → Integrations → edit `mcp.json`:

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

2. **Paste the skill instructions** — copy the body of [`skills/asta-skill/SKILL.md`](skills/asta-skill/SKILL.md) into the chat's System Prompt so the model follows the intent routing and safe defaults.

Use a **tool-calling-capable** local model (e.g. Qwen2.5-Instruct, Llama 3.1 Instruct, Mistral Nemo, GPT-OSS). Plain chat models cannot invoke MCP tools.

</details>

<details>
<summary><b>Any other MCP host</b></summary>

Point it at the standard streamable-HTTP config:

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

If your client can't attach a custom header to a remote server, bridge through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) (see the **Qoder** or **Claude Desktop** blocks).

</details>

### Step 2: Install the Skill (optional)

Skip this and the tools still work — this layer only sharpens tool selection and defaults. The skill body lives at `skills/asta-skill/SKILL.md`. The easiest path is the plugin marketplace.

#### Plugin marketplace (recommended)

```bash
# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g

# Claude Code only
/plugin marketplace add Agents365-ai/365-skills
/plugin install asta
```

Also indexed on [SkillsMP](https://skillsmp.com/) and [ClawHub](https://clawhub.ai/) — each handles updates through its own marketplace.

#### Manual clone (any host)

```bash
git clone https://github.com/Agents365-ai/asta-skill.git /tmp/asta-skill
cp -r /tmp/asta-skill/skills/asta-skill <your-host's-skills-dir>/asta-skill
```

### Verification

After registering the MCP server, installing the skill, and restarting your host, ask:

> "Use Asta to get the paper ARXIV:1706.03762 with fields title,year,authors,venue,tldr"

A successful call returns *Attention Is All You Need*, NeurIPS 2017, Vaswani et al., with TLDR.

## Usage

Just describe what you want:

```
> Use Asta to get the paper with DOI 10.48550/arXiv.1706.03762

> Search Asta for recent papers on mixture-of-experts at NeurIPS since 2023

> Who cited "Attention Is All You Need"? Show me the top 20 by citation count

> Find snippets in the Asta corpus that mention "flash attention latency"

> Look up Yann LeCun on Asta and list his 2024 papers
```

The skill picks the right Asta tool, attaches safe `fields`, and follows the documented workflow patterns.

### Example: Search + Batch Download (chained with `paper-fetch`)

`asta-skill` only handles **search and metadata**; it does not download PDFs. To go from a search query to local PDFs, chain it with a `paper-fetch` skill (or any DOI-based downloader of your choice):

```
> Use Asta to find the 5 most cited papers on "single-cell ATAC-seq batch correction"
  since 2022, then hand the DOIs to paper-fetch to download all PDFs into ./papers/
```

What happens under the hood:

1. **asta-skill** → `search_papers_by_relevance` with `publication_date_range="2022:"` and `fields=title,year,authors,venue,tldr,externalIds` (note `externalIds` to expose DOI)
2. Agent extracts `externalIds.DOI` for each hit; falls back to `externalIds.ArXiv` when DOI is absent
3. **paper-fetch** → batch-resolves each DOI/arXiv ID through the Unpaywall → Semantic Scholar → arXiv → PubMed Central → bioRxiv/medRxiv → publisher-direct → Sci-Hub fallback chain
4. PDFs land in `./papers/`, one per paper

`paper-fetch` is a separate skill — install it if you need download capability. `asta-skill` itself stays scoped to the Semantic Scholar corpus.

**Step 1 — Asta returns the top 5 papers with DOIs:**

![Asta search result](assets/asta-search.png)

**Step 2 — paper-fetch downloads all 5 PDFs into `./papers/`:**

![paper-fetch batch download](assets/asta-paper-fetch.png)

## 🔗 Related Skills

Part of the [Agents365-ai research-skill family](https://github.com/Agents365-ai) — pick the right tool for the job:

| Skill | Niche | When to use |
| --- | --- | --- |
| [semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) | Direct Semantic Scholar API (Python) | When MCP isn't available or you prefer scripted access |
| [paper-fetch](https://github.com/Agents365-ai/paper-fetch) | DOI → PDF, 7-source fallback | When you need full text after finding citations |
| [scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) | 8-phase literature review pipeline | When the user wants a structured cited report |

## ❤️ Support

If this skill helps you, consider supporting the author:

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
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## 👤 Author

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 License

[MIT](LICENSE)
