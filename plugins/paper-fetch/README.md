# paper-fetch — Download scientific paper PDFs by DOI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-paper-fetch-skills-paper-fetch-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/paper-fetch-pro-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
**English** · [中文](README_CN.md) · [📖 Online Docs](https://agents365-ai.github.io/paper-fetch/)

Resolve a DOI (or title) to a PDF via a 7-source fallback chain — [Unpaywall](https://unpaywall.org) → [Semantic Scholar](https://www.semanticscholar.org) → [arXiv](https://arxiv.org) → [PubMed Central](https://pmc.ncbi.nlm.nih.gov) → [bioRxiv](https://www.biorxiv.org)/[medRxiv](https://www.medrxiv.org) → publisher direct → [Sci-Hub](https://www.sci-hub.pub) mirrors. Pure Python stdlib, agent-native CLI with stable JSON envelopes.

## What it does

**Resolve a DOI (or title) to a PDF**

- 7-source fallback chain: [Unpaywall](https://unpaywall.org) → [Semantic Scholar](https://www.semanticscholar.org) → [arXiv](https://arxiv.org) → [PubMed Central](https://pmc.ncbi.nlm.nih.gov) → [bioRxiv](https://www.biorxiv.org)/[medRxiv](https://www.medrxiv.org) → publisher direct *(institutional opt-in)* → [Sci-Hub](https://www.sci-hub.pub) mirrors *(last resort, on by default)*
- Title-only input via `--title` — Crossref + Semantic Scholar resolution with confidence flags
- Auto-named output: `{first_author}_{year}_{journal_abbrev}_{short_title}.pdf`

**Batch + agent-friendly**

- `--batch dois.txt` or `--batch -` (stdin) for bulk download
- `--idempotency-key` replays the exact envelope on retry without network I/O
- `--stream` emits one NDJSON result per line as each DOI resolves
- Skips already-downloaded files unless `--overwrite`

**Built-in correctness**

- Stable JSON envelope on stdout, NDJSON progress on stderr, machine-readable `schema` subcommand
- TTY-aware format default, typed exit codes (`0`/`1`/`3`/`4`) for orchestrator routing
- SSRF defense + `%PDF` magic-byte check + 50 MB size cap on every fetch
- Zero runtime dependencies — pure Python stdlib

**Cloudflare-blocked PDFs** *(opt-in)*

- `PAPER_FETCH_CLOAK=1` retries any 403/429-blocked or JS-challenged PDF URL through [CloakBrowser](https://github.com/CloakHQ/CloakBrowser), a stealth Chromium that passes the challenge (approach borrowed from [cloakFetch](https://github.com/Agents365-ai/cloakFetch))
- Sits at the download layer, so it applies to every source; off by default, fails closed, operator-controlled
- Returned bytes re-validated through the same `%PDF` + size checks; result carries `via: "cloak"`

Works with Claude Code, Codex, Hermes, OpenClaw, ClawHub, pi-mono, and SkillsMP — any agent that supports the [Agent Skills](https://agentskills.io) format.

## Discipline coverage

The skill is **discipline-agnostic** — it works for any field, not just life sciences or CS.

| Source | Discipline scope |
| --- | --- |
| Unpaywall | ✅ All disciplines (every Crossref DOI — humanities, social sciences, physics, chemistry, economics) |
| Semantic Scholar | ✅ All disciplines (cross-domain academic graph) |
| arXiv | Physics, math, CS, statistics, quant finance, economics, EE |
| PubMed Central | Biomedical only |
| bioRxiv / medRxiv | Biology / medicine preprints only |
| Sci-Hub | ✅ All disciplines (last resort) |

In practice, **Unpaywall + Semantic Scholar alone cover OA papers in chemistry, materials, economics, psychology, humanities, and every other field** via institutional repositories, SSRN, RePEc, and publisher-hosted OA copies.

## Comparison

### vs. native agent (no skill)

| Feature | Native agent | This skill |
| --- | --- | --- |
| Resolve DOI to PDF | Ad-hoc web search | Deterministic 7-source chain |
| Title → DOI resolution | Manual | `--title` (Crossref + S2 fallback, confidence flags) |
| Batch download | ❌ | ✅ `--batch dois.txt` or `--batch -` |
| Consistent filenames | ❌ | ✅ `author_year_journal_title.pdf` |
| Machine-readable schema | ❌ | ✅ `fetch.py schema` |
| Structured output | ❌ | ✅ JSON envelope + NDJSON progress |
| Idempotent retries | ❌ | ✅ `--idempotency-key` |
| Typed exit codes | ❌ | ✅ `0`/`1`/`3`/`4` |
| SSRF + `%PDF` + size cap | ❌ | ✅ enforced |

## Prerequisites

- `python3` (3.8+, stdlib only — no `pip install` needed)
- (Recommended) An [Unpaywall contact email](https://unpaywall.org/products/api):

  ```bash
  export UNPAYWALL_EMAIL=you@example.com
  ```

Without it, Unpaywall is skipped and the remaining 6 sources still work.

## Installation

```bash
# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g

# Claude Code only
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install paper-fetch
```

Also published on [SkillsMP](https://skillsmp.com/) and [ClawHub](https://clawhub.ai/) — each handles updates through its own marketplace.

## Usage

Just describe what you want:

```
> Download the AlphaFold2 paper PDF to ~/papers

> Fetch DOI 10.1038/s41586-020-2649-2

> Batch-download every DOI from dois.txt

> Find a PDF for "Attention Is All You Need" and save it

> Preview the resolved PDF URL for 10.1126/science.abj8754 without downloading
```

Or call the script directly:

```bash
# Single DOI
python skills/paper-fetch/scripts/fetch.py 10.1038/s41586-021-03819-2

# By title (resolved to DOI via Crossref + S2 fallback)
python skills/paper-fetch/scripts/fetch.py --title "Highly accurate protein structure prediction with AlphaFold"

# Dry-run preview (no download)
python skills/paper-fetch/scripts/fetch.py 10.1038/s41586-020-2649-2 --dry-run

# Batch with idempotency
python skills/paper-fetch/scripts/fetch.py --batch dois.txt --out ~/papers \
    --idempotency-key monday-review-batch

# Pipe DOIs from another tool
echo 10.1038/s41586-021-03819-2 | python skills/paper-fetch/scripts/fetch.py --batch -

# Agent discovery
python skills/paper-fetch/scripts/fetch.py schema --pretty
```

Full flag reference and JSON envelope schema in [`skills/paper-fetch/SKILL.md`](skills/paper-fetch/SKILL.md).

## Institutional access (opt-in)

If your institution has a subscription, set `PAPER_FETCH_INSTITUTIONAL=1` to enable the publisher-direct fallback. Your IP / cookies / EZproxy authorize the fetch; the skill adds a 1 req/s rate limiter to keep batch jobs within publisher ToS.

```bash
export PAPER_FETCH_INSTITUTIONAL=1
```

## Cloudflare-blocked PDFs via CloakBrowser (opt-in)

Some publishers (e.g. `science.org`) sit behind Cloudflare, which serves a `403`/`429` or a "Just a moment…" JS challenge to plain HTTP clients instead of the PDF. Set `PAPER_FETCH_CLOAK=1` to retry those URLs through [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) — a stealth Chromium that passes the challenge. The approach is borrowed from [cloakFetch](https://github.com/Agents365-ai/cloakFetch).

```bash
# Requires a Python with `cloakbrowser` importable (pip install cloakbrowser)
export PAPER_FETCH_CLOAK=1
export CLOAKBROWSER_PYTHON="$HOME/github/CloakBrowser/.venv/bin/python"  # if not auto-detected
export PAPER_FETCH_CLOAK_HEADED=1   # for hard challenges (e.g. science.org) that defeat headless
```

The fallback lives at the download layer (so it covers every source), re-validates returned bytes through the same `%PDF` + 50 MB checks, fails closed when CloakBrowser is unavailable, and is operator-controlled — the agent cannot enable it. Successful cloak downloads carry `via: "cloak"` in the result.

By default the browser runs **headless**; harder challenges (e.g. `science.org`) get stuck on "Just a moment…" in headless mode, so set `PAPER_FETCH_CLOAK_HEADED=1` for a visible window that clears them (needs a display). The in-page fetch is **same-origin**, so it works for direct PDF links on the blocked host (e.g. `www.science.org/doi/pdf/…`); cross-origin-redirecting URLs fall through. See [`skills/paper-fetch/SKILL.md`](skills/paper-fetch/SKILL.md) (*CloakBrowser access*) for details.

## Known limitations

- **Some publisher redirects** return an HTML landing page; the `%PDF` header check rejects them
- **No browser automation** — no CAPTCHA solving, no Playwright, no stealth
- **SSRF defense** rejects private IPs, non-http(s) schemes, non-80/443 ports, cloud metadata hosts
- **50 MB cap** per PDF download

## 🔗 Related Skills

Part of the [Agents365-ai research-skill family](https://github.com/Agents365-ai) — pick the right tool for the job:

| Skill | Niche | When to use |
| --- | --- | --- |
| [semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) | Semantic Scholar API search | When you need to FIND papers before fetching |
| [asta-skill](https://github.com/Agents365-ai/asta-skill) | Same corpus via Ai2 Asta MCP | When your host supports MCP and you have an Asta API key |
| [scholar-deep-research](https://github.com/Agents365-ai/scholar-deep-research) | 8-phase literature review pipeline | When you want a structured cited report, not just PDFs |
| [zotero-research-assistant](https://github.com/Agents365-ai/zotero-research-assistant) | Zotero library workflows | When references go into Zotero |

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
