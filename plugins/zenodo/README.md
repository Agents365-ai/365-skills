# zenodo-skill

English | [中文](README_CN.md)

A Claude Code / OpenClaw skill for the [Zenodo REST API](https://developers.zenodo.org). Deposit, publish, version, and search research artifacts on Zenodo — and get a citable DOI for every release.

## Features

- **Full deposit lifecycle** — create deposition → upload files via the bucket API → set metadata → publish
- **New version workflow** — release updated data/code under the same concept-DOI
- **Search** — Elasticsearch-style queries against published records (no auth required)
- **Sandbox-first** — defaults to `sandbox.zenodo.org` so you don't accidentally publish irreversibly to production
- **Bucket file upload** — uses the new files API (50 GB total, 100 files/record), not the legacy 100 MB endpoint
- **Metadata reference** — full schema for `upload_type`, license codes, conditional fields, related identifiers
- **End-to-end shell examples** — copy-pasteable scripts for dataset upload, software release, new version, batch download

## Installation

The skill lives in the Agents365-ai skills monorepo; clone the monorepo and
link the skill directory into your agent's skills path:

### Claude Code

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zenodo/skills/zenodo-skill" ~/.claude/skills/zenodo-skill
```

Or per-project: link into `.claude/skills/zenodo-skill/`.

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zenodo/skills/zenodo-skill" ~/.openclaw/skills/zenodo-skill
```

### SkillsMP

Indexed automatically once the repo has the standard topics — install via the SkillsMP marketplace.

## Prerequisites

- `curl` (and `jq` recommended for the example scripts)
- A Zenodo personal access token with `deposit:write` and `deposit:actions` scopes
  - **Sandbox** (testing): https://sandbox.zenodo.org/account/settings/applications/tokens/new/
  - **Production**: https://zenodo.org/account/settings/applications/tokens/new/

Set environment variables before use:

```bash
export ZENODO_TOKEN=...
export ZENODO_BASE=https://sandbox.zenodo.org/api   # or https://zenodo.org/api
```

## Usage

Just describe what you want — the skill triggers on Zenodo-related requests:

- "Upload this dataset to Zenodo and give me a DOI"
- "Publish a new version of my Zenodo record 1234567 with these files"
- "Search Zenodo for single-cell RNA datasets published this year"
- "Deposit this code release to sandbox Zenodo first"

The skill walks the deposit through create → upload → metadata → publish, asks for confirmation before any irreversible production publish, and returns the DOI and record URL.

## What's in this skill

| File | Purpose |
|---|---|
| `SKILL.md` | Workflow, setup, and core API calls |
| `references/metadata.md` | Full deposition metadata schema, `upload_type` values, license codes, examples |
| `references/search.md` | Elasticsearch query syntax and search parameters |
| `references/examples.md` | End-to-end shell scripts (upload+publish, new version, list drafts, download) |

## Safety

- Defaults to sandbox; production publish requires explicit confirmation
- Tokens are read from `$ZENODO_TOKEN` — never inlined into commands
- Reviews metadata + files with you before calling `actions/publish`
- Production publish is irreversible — files cannot be removed and records cannot be deleted

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

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai
