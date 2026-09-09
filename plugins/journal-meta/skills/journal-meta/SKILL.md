---
name: journal-meta
description: Use when the user wants full metadata for a paper — from a DOI, PMID, arXiv id, OpenAlex id, or title. Returns title, author list, first author, corresponding author(s), publication date, journal name + ISO-4 abbreviation, impact factor, volume/issue/pages, DOI/PMID, citation count, and abstract in one record. Triggers on "paper metadata", "who is the corresponding author", "first author of", "what journal / impact factor for this DOI/PMID", "cite this paper", "文献元数据", "通讯作者", "第一作者", "影响因子". PROACTIVELY USE when the user pastes a DOI/PMID/arXiv id or paper title and asks about its authors, venue, or impact.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
# --- Claude Code fields above, OpenClaw/SkillsMP fields below ---
author: Agents365-ai
category: Academic Research
version: 0.1.0
created: 2026-07-14
updated: 2026-07-14
github: https://github.com/Agents365-ai/journal-meta
homepage: https://github.com/Agents365-ai/journal-meta
metadata:
  version: 0.1.0
  openclaw:
    requires:
      bins:
        - python3
    emoji: "🗂️"
    homepage: https://github.com/Agents365-ai/journal-meta
    os: ["macos", "linux", "windows"]
---

# Paper Metadata Lookup

Resolve one paper identifier into a full metadata record. Primary source is
**OpenAlex** (free, no API key); **Crossref** is a fallback for DOIs OpenAlex
hasn't indexed. The journal name is enriched by delegating to two sibling
skills when installed:

- **`journal-abbrev`** → ISO-4 / MEDLINE journal abbreviation (JabRef cache, ~25K journals)
- **`journal-if`** → curated JCR impact factor

If those skills aren't found, it falls back to AbbrevISO (abbreviation) and
OpenAlex `2yr_mean_citedness` (approximate IF) automatically.

**Critical rule:** Always use `journal_meta.py`. Never fabricate authors,
corresponding authors, dates, or impact factors — resolve them.

## Quick Reference

| User wants... | Command |
| --------------- | --------- |
| Metadata from a DOI | `python3 journal_meta.py "10.1038/s41586-020-2649-2"` |
| Metadata from a PMID | `python3 journal_meta.py 32939066` |
| Metadata from an arXiv id | `python3 journal_meta.py 1706.03762` |
| Metadata from a title | `python3 journal_meta.py "Attention is all you need"` |
| Process a list | `python3 journal_meta.py batch papers.txt` |
| Skip impact-factor lookup | `python3 journal_meta.py <id> --no-if` |
| Skip abbreviation lookup | `python3 journal_meta.py <id> --no-abbrev` |
| Machine-readable contract | `python3 journal_meta.py schema` |

The subcommand `lookup` is optional — a bare identifier works. Identifier type
(DOI / PMID / arXiv / OpenAlex id / title) is auto-detected.

### Output format

Stdout is a stable JSON envelope when piped/captured, and a human key-value
view on a TTY. Force it with `--format json|human|auto` (`--json` = `--format json`).

Envelope: `{ "ok": true, "data": {...}, "meta": { "schema_version", "cli_version", "sources", "latency_ms" } }`.
`meta.sources` records where each field came from (e.g. `journal-abbrev (JabRef)`,
`journal-if (local cache)`, or a fallback), so you can tell curated data from approximations.

### Data fields (`data`)

`title`, `authors` (list), `author_count`, `first_author`, `corresponding_authors`
(list; empty if OpenAlex has no corresponding flag for the record),
`publication_date`, `year`, `journal`, `journal_abbrev`, `impact_factor`,
`impact_factor_source`, `impact_factor_year`, `volume`, `issue`, `pages`,
`doi`, `pmid`, `openalex`, `issn`, `type`, `is_oa`, `cited_by_count`, `abstract`.

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | success |
| `1`  | runtime / upstream error (retryable) |
| `2`  | validation / bad input (missing file, empty query) |
| `3`  | not found (no paper matched) |

## Workflow

1. **Identify the input.** A DOI (`10.x/...`), PMID (digits), arXiv id
   (`NNNN.NNNNN`), OpenAlex id (`W...`), or a title string — all auto-detected.
   Prefer a DOI or PMID: **title search returns OpenAlex's single top match**,
   which for very common titles can be a preprint or re-indexed copy rather than
   the version of record. Confirm the returned DOI/year if the user gave a title.
2. **Run** `python3 journal_meta.py <id>`.
3. **Present** the fields the user asked for. For a full citation, use
   `first_author`, `journal_abbrev`, `year`, `volume`, `issue`, `pages`, `doi`.
   State the `impact_factor_source` when reporting IF — a curated JCR number and
   an OpenAlex approximation are not the same thing.

## Notes & caveats

- **Corresponding author** comes from OpenAlex's `is_corresponding` flag, which
  is only populated when the publisher supplied it. An empty list means "not
  marked in the metadata," not "there is none" — say so rather than guessing.
- **Impact factor** from `journal-if` is curated JCR; the fallback is OpenAlex's
  2-year mean citedness, which differs from the official JCR IF. Cite formally
  only the curated value, and flag approximations.
- **arXiv** ids resolve via the arXiv DataCite DOI (`10.48550/arXiv.<id>`); if a
  preprint isn't indexed there, it falls back to a title search.

## Environment variables

| Variable | Effect |
| ---------- | -------- |
| `JOURNAL_META_MAILTO` / `OPENALEX_MAILTO` | Email for OpenAlex's polite pool (faster, recommended). |
| `JOURNAL_ABBREV_CLI` | Explicit path to `journal-abbrev`'s `jabbrv.py` (skips auto-discovery). |
| `JOURNAL_IF_CLI` | Explicit path to `journal-if`'s `journal_if.py`. |

If the sibling skills live in a non-standard location, set these so enrichment
uses their curated data instead of the built-in fallbacks.

## Troubleshooting

| Issue | Solution |
| ------- | ---------- |
| IF shows "OpenAlex ... (approx)" not JCR | `journal-if` not found — install it or set `JOURNAL_IF_CLI`. |
| Abbreviation looks wrong / same as full name | Single-word titles (Nature, Cell, Science) are not abbreviated per ISO 4. For others, `journal-abbrev` gives the ISO-4 form. |
| Title search returned the wrong paper | Use the DOI or PMID instead — title search takes OpenAlex's top hit only. |
| `not_found` on a brand-new DOI | OpenAlex indexing lags; the Crossref fallback covers most, but the newest DOIs may need a day. |
| `corresponding_authors` is empty | The publisher didn't mark it in the metadata; don't infer one. |
