---
name: journal-if
description: Use when looking up journal impact factors (JCR IF), checking a journal's impact factor by name, comparing IF across journals, or answering questions about "影响因子" / "impact factor" / "IF". Triggers on "impact factor", "journal IF", "影响因子", "JCR", "IF score", "journal rank", "which journal has higher IF", "what is the IF of". PROACTIVELY USE when user mentions journal prestige, publication venue quality, or manuscript submission target evaluation.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
# --- Claude Code fields above, OpenClaw/SkillsMP fields below ---
author: Agents365-ai
category: Academic Research
version: 1.0.0
created: 2026-07-14
updated: 2026-07-14
github: https://github.com/Agents365-ai/journal-if
homepage: https://github.com/Agents365-ai/journal-if
metadata:
  version: 1.0.0
  openclaw:
    requires:
      bins:
        - python3
    emoji: "📊"
    homepage: https://github.com/Agents365-ai/journal-if
    os: ["macos", "linux", "windows"]
---

# Journal Impact Factor Lookup

Look up journal impact factors using a two-source cascade: bundled CSV cache (~200 common journals) → OpenAlex API (approximate 2-year IF for any journal).

**Critical rule:** Always use `journal_if.py` for lookups. Never guess impact factors — they change yearly and vary by edition.

## Quick Reference

| User wants... | Tier | Command |
|---------------|------|---------|
| Look up IF of a journal | read | `python3 journal_if.py lookup "Nature Medicine"` |
| Search for a journal | read | `python3 journal_if.py search "cancer immunology"` |
| Process a list of journals | read | `python3 journal_if.py batch journals.txt` |
| Cache-only (no network) | read | `python3 journal_if.py --offline lookup "Cell"` |
| Inspect cache state | read | `python3 journal_if.py cache status` |
| Refresh upstream CSV | write | `python3 journal_if.py cache update` |
| Machine-readable CLI contract | read | `python3 journal_if.py schema` |
| Schema for one subcommand | read | `python3 journal_if.py schema lookup` |

### Output format

Stdout is a stable JSON envelope when the CLI is **not** attached to a terminal
(piped or captured by an agent), and a human-readable view when run on a TTY.
To force a format: `--format json|table|human|auto`. `--json` is a back-compat
alias for `--format json`.

Envelope shape:

- Success: `{ "ok": true, "data": {...}, "meta": { "schema_version", "cli_version", "latency_ms" } }`
- Partial success (batch): `{ "ok": "partial", "data": { "succeeded": [...], "failed": [...] }, "meta": {...} }`
- Error: `{ "ok": false, "error": { "code", "message", "retryable", ... }, "meta": {...} }`

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | success (including partial success) |
| `1`  | runtime / upstream error |
| `2`  | validation / bad input (missing file, bad flag) |
| `3`  | not found (no journal matched) |

### Error codes (inside `error.code`)

| Code | Retryable | Exit | Meaning |
|------|-----------|------|---------|
| `not_found` | no | 3 | Lookup completed but no source matched |
| `upstream_unavailable` | **yes** | 1 | OpenAlex API failed transiently; retry later or use `--offline` |
| `file_not_found` | no | 2 | Input file path does not exist |
| `validation_error` | no | 2 | Bad argument or flag combination |
| `runtime_error` | yes | 1 | Unexpected internal error |

## Data Sources

1. **Bundled CSV** — ~200 top journals across life sciences, medicine, chemistry, physics, and engineering. Curated from JCR data, shipped with the skill. Always available, instant.

2. **OpenAlex API** — Free, open API that computes an approximate 2-year impact factor from citation counts. Covers virtually all academic journals. The number **differs from the official JCR IF** — it's a citation-rate metric computed from the same formula (citations in year Y to items published in Y-1 and Y-2, divided by citable items in those two years) but using OpenAlex's own article classification. Adequate for ranking and comparison; do not cite as "the JCR impact factor" in formal contexts.

### When to use which

| Scenario | Source |
|----------|--------|
| Quick check of a major journal | Bundled CSV (instant) |
| Niche or newer journal | OpenAlex fallback (automatic) |
| Formal submission / grant | Note: OpenAlex IF ≠ official JCR IF. Cite only as approximate. |
| Batch processing many journals | CSV for cached ones, OpenAlex for misses |
| Offline / air-gapped | `--offline` flag (bundled CSV only) |

## Workflow

### Step 1: Detect Intent

| Intent | Action |
|--------|--------|
| "What's the IF of Nature?" | `lookup "Nature"` |
| "Compare IF of Cell and Science" | Run `lookup` twice, compare results |
| "Which immunology journals have IF > 20?" | `search "immunology"` then filter |
| "Process this list of journals" | `batch journals.txt` |
| "Is this a high-impact journal?" | `lookup` then interpret IF in field context |

### Step 2: Execute

Run the appropriate `journal_if.py` command. The script handles:

1. **Local CSV lookup** (instant, ~200 curated journals)
2. **OpenAlex API fallback** (automatic, approximate 2-year IF)
3. **Fuzzy matching** — catches minor name variations

### Step 3: Present Results

- Show the journal name, impact factor, and data year
- Note the source (CSV cache vs OpenAlex approximate)
- For search results: show a table with IF, year, and category

## Understanding Impact Factor

| IF Range | Typical Tier | Example |
|----------|-------------|---------|
| > 30 | Elite (top 0.1%) | Nature (64.8), Science (56.9), Cell (64.5) |
| 20–30 | Exceptional (top 1%) | Cancer Cell (50.3), Immunity (32.4) |
| 10–20 | Excellent (top 5%) | Nature Communications (16.6), Sci Adv (13.6) |
| 5–10 | Strong (top 15%) | eLife (7.7), Cell Reports (8.8) |
| 2–5 | Solid | PLOS ONE (3.7), Sci Rep (4.6) |
| < 2 | Niche / new | Many field-specific and new journals |

**Caveats:**
- IF varies dramatically by field — a top mathematics journal may have IF < 5 while a mid-tier oncology journal has IF > 10.
- Always compare IF within the same field.
- The IF data year matters; values shift annually.
- OpenAlex approximate IF differs from official JCR IF; treat as a ranking metric, not a certified number.

## Batch Processing

Create a text file with one journal name per line:

```
Nature Medicine
Journal of Biological Chemistry
Proceedings of the National Academy of Sciences
```

Then run:

```bash
python3 journal_if.py batch journals.txt
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| "No data found" | Try a shorter/alternative name; use `search` for fuzzy matching |
| OpenAlex returns 0 or None IF | The journal may be too new (needs 2+ years of data); use `--offline` to check cache only |
| OpenAlex IF differs from JCR | Expected — OpenAlex uses its own article classification. Use for ranking, not formal citation. |
| Cache download fails | Check network; the bundled CSV still works offline |
| Wrong journal matched | Use more specific name; the fuzzy matcher picks the closest substring match |
