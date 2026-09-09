# Journal Meta — Paper Metadata Lookup Skill

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/journal-meta?style=flat&logo=github)](https://github.com/Agents365-ai/journal-meta/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/journal-meta?style=flat&logo=github)](https://github.com/Agents365-ai/journal-meta/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/journal-meta?logo=github)](https://github.com/Agents365-ai/journal-meta/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/journal-meta?logo=github)](https://github.com/Agents365-ai/journal-meta/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[中文](README_CN.md)

A Claude Code skill that turns a single paper identifier — **DOI, PMID, arXiv id,
OpenAlex id, or title** — into one complete metadata record: title, full author
list, first author, corresponding author(s), publication date, journal name +
ISO-4 abbreviation, impact factor, volume/issue/pages, DOI/PMID, citation count,
and abstract.

## Workflow

![Journal Meta workflow](docs/workflow.drawio.png)

## Why

| Field | Native Claude Code | Journal Meta |
| ------- | -------------------- | -------------- |
| Title / authors / date / venue | Guessed from memory | Resolved from OpenAlex (+ Crossref fallback) |
| First author | Ambiguous | `author_position == first` |
| Corresponding author | Not available | OpenAlex `is_corresponding` (never guessed) |
| Journal abbreviation | Manual guessing | Delegated to **journal-abbrev** (ISO-4, ~25K journals) |
| Impact factor | Not available | Delegated to **journal-if** (curated JCR) |
| Batch of DOIs/PMIDs | Not supported | `batch file.txt` |

## How it works

1. **OpenAlex** (free, no key) resolves the identifier and supplies nearly every
   field, including the corresponding-author flag. **Crossref** is a fallback for
   DOIs OpenAlex hasn't indexed yet.
2. The journal name is enriched by **delegating to two sibling skills** when they
   are installed:
   - [`journal-abbrev`](https://github.com/Agents365-ai/journal-abbrev) → ISO-4 abbreviation.
   - [`journal-if`](https://github.com/Agents365-ai/journal-if) → curated JCR impact factor.
   - Fallbacks (AbbrevISO, OpenAlex 2-year mean citedness) kick in automatically
     if those skills aren't found. `meta.sources` always tells you which was used.

## Usage

```bash
# From a DOI
python3 journal_meta.py "10.1038/s41586-020-2649-2"

# From a PMID / arXiv id / title
python3 journal_meta.py 32939066
python3 journal_meta.py 1706.03762
python3 journal_meta.py "Attention is all you need"

# A list, one identifier per line
python3 journal_meta.py batch papers.txt

# Skip enrichment, or force JSON
python3 journal_meta.py <id> --no-if --no-abbrev
python3 journal_meta.py <id> --format json
```

Output is a human key-value view on a TTY and a stable JSON envelope when piped.
`meta.sources` records the provenance of the abbreviation and impact factor.

## Configuration

| Env var | Effect |
| --------- | -------- |
| `JOURNAL_META_MAILTO` / `OPENALEX_MAILTO` | Email for OpenAlex's polite pool (recommended). |
| `JOURNAL_ABBREV_CLI` | Explicit path to `journal-abbrev`'s `jabbrv.py`. |
| `JOURNAL_IF_CLI` | Explicit path to `journal-if`'s `journal_if.py`. |

## Caveats

- **Corresponding author** relies on OpenAlex's `is_corresponding` flag, which is
  only present when the publisher supplied it — an empty list means "not marked,"
  not "none." The skill never infers one.
- **Impact factor** from `journal-if` is the curated JCR value; the fallback is an
  OpenAlex approximation and is labelled as such in `impact_factor_source`.
- **Title search** returns OpenAlex's single top hit; prefer a DOI or PMID for the
  version of record.

## Requirements

- Python 3 (standard library only — no third-party packages).
- Optional but recommended: the `journal-abbrev` and `journal-if` skills installed
  alongside this one for curated abbreviations and impact factors.

**Works with:** Claude Code and any coding agent that can run a Python CLI.

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

CC BY-NC 4.0 — Free for non-commercial use. Commercial use requires permission.
