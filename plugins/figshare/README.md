# figshare-skill — Figshare v2 API from the Command Line

[中文文档](README_CN.md) | [Figshare API Docs](https://docs.figshare.com/)

## What it does

- **Search** public Figshare articles with field operators (`:title:`, `:author:`, `:tag:`, `:category:`, `:doi:`)
- **Batch-download** every file of a public article from an ID, DOI, or `figshare.com` URL
- **List / create / update / publish** your own articles, including draft and version workflows
- **Multi-part upload** for large files — wraps the 3-step `initiate → PUT parts → complete` flow with md5 + part sizing handled automatically
- **New-version publishing** for already-published articles (published versions are frozen)
- **Collections and Projects** management
- Triggers automatically whenever the user mentions Figshare, a `figshare.com` URL, or a `10.6084/m9.figshare.*` DOI

## Multi-Platform Support

Works with all major AI coding agents that support the [Agent Skills](https://agentskills.io) format:

| Platform | Status | Details |
| ---------- | -------- | --------- |
| **Codex** | ✅ Full support | Native `SKILL.md` plus `agents/openai.yaml` UI metadata |
| **Claude Code** | ✅ Full support | Native SKILL.md format |
| **OpenClaw** | ✅ Full support | `metadata.openclaw` namespace |
| **SkillsMP** | ✅ Indexed | GitHub topics configured |

## Comparison

### vs No Skill (native agent)

| Feature | Native agent | This skill |
| --------- | ------------- | ------------ |
| Knows the Figshare base URL & auth header | Maybe | ✅ |
| Search field operators (`:title:`, `:author:`...) | ❌ | ✅ |
| Public batch download from ID / DOI / URL | ❌ | ✅ helper script |
| Multi-part upload (`initiate → parts → complete`) | ⚠️ reinvents per run | ✅ `upload.sh` |
| md5 / size / part layout handled | ❌ | ✅ automatic |
| New-version publishing | ❌ | ✅ `new-version.sh` |
| Safe-by-default publish / delete | ❌ | ✅ asks first |
| Concrete `curl` + `jq` recipes | ❌ | ✅ inlined |

## Prerequisites

- `curl`
- `jq`
- A [Figshare Personal Token](https://figshare.com/account/applications) for anything that touches `/account/...` or uploads:

  ```bash
  export FIGSHARE_TOKEN=xxxxxxxxxxxxxxxx
  ```

Public search / article / download endpoints work with no token at all.

## Skill Installation

The skill lives in the Agents365-ai skills monorepo; clone the monorepo and
link the skill directory into your agent's skills path:

### Codex

```bash
# Global install (auto-discovered by Codex)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.codex/skills/figshare-skill
```

### Claude Code

```bash
# Global install (available in all projects)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.claude/skills/figshare-skill

# Project-level install
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" .claude/skills/figshare-skill
```

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.openclaw/skills/figshare-skill

# Project-level
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" skills/figshare-skill
```

### SkillsMP

Browse on [SkillsMP](https://skillsmp.com) or:

```bash
skills install figshare-skill
```

### Installation paths summary

| Platform | Global path | Project path |
| ---------- | ------------- | -------------- |
| Codex | `~/.codex/skills/figshare-skill/` | N/A |
| Claude Code | `~/.claude/skills/figshare-skill/` | `.claude/skills/figshare-skill/` |
| OpenClaw | `~/.openclaw/skills/figshare-skill/` | `skills/figshare-skill/` |
| SkillsMP | N/A (installed via CLI) | N/A |

## Usage

Just describe what you want:

```
> Use $figshare-skill to search Figshare for "single cell" datasets and show me the top 10

> Search figshare for "single cell" datasets and show me the top 10

> Download every file of https://figshare.com/articles/dataset/xxx/31957606 into ./data

> Upload ./results.zip to my draft figshare article 31957803

> Publish a new version of figshare article 12345678 with ./v2.csv
```

The skill picks the right endpoint, fills in authentication, and uses the bundled helper scripts for multi-part uploads.

## Helper Scripts

| Script | Purpose |
| -------- | --------- |
| `scripts/upload.sh <article_id> <file>` | 3-step multi-part upload to a draft article |
| `scripts/download.sh <id_or_url> [dir]` | Batch-download every file from a public article |
| `scripts/new-version.sh <article_id> <file>` | Reserve, upload, and publish a new version |

All scripts read `FIGSHARE_TOKEN` from the environment and depend only on `curl` + `jq`.

## Files

- `SKILL.md` — **the only required file**. Loaded by all platforms as the skill instructions.
- `agents/openai.yaml` — Codex UI metadata for skill discovery and prompt chips
- `scripts/upload.sh` — multi-part upload helper
- `scripts/download.sh` — batch downloader
- `scripts/new-version.sh` — new-version workflow
- `README.md` — this file (English, displayed on GitHub homepage)
- `README_CN.md` — Chinese documentation

## Known Limitations

- **`dd bs=1` is slow for huge parts**: good enough for datasets up to a few GB per part. Very large single files would benefit from a `bs=1M` + `skip=`/`count=` rewrite
- **Rate limiting**: Figshare does not publish a hard limit but recommends ≤1 req/sec. The helpers do not throttle
- **Published versions are immutable**: edits require `new-version.sh`, not `update`
- **Categories / licenses are numeric IDs**: use `GET /v2/categories` and `GET /v2/licenses` to look up the ID you need before creating an article

## License

MIT

## Support

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
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>
