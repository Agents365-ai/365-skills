---
name: semanticscholar-skill
description: Use when searching academic papers, looking up citations, finding authors, or getting paper recommendations using the Semantic Scholar API. Triggers on queries about research papers, academic search, citation analysis, or literature discovery.
license: MIT
homepage: https://github.com/Agents365-ai/semanticscholar-skill
compatibility: Requires python3 and the `requests` package. Set S2_API_KEY for higher rate limits (request at https://www.semanticscholar.org/product/api#api-key). Works unauthenticated with strict rate limits.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["S2_API_KEY"]},"emoji":"📚"},"hermes":{"tags":["semantic-scholar","academic","paper-search","citation","literature","research"],"category":"research","requires_tools":["python3"],"related_skills":["asta-skill","zotero-research-assistant","literature-review","paper-reader"]},"author":"Agents365-ai","version":"0.5.1"}
---

# Semantic Scholar Search Workflow

Search academic papers via the Semantic Scholar API using a structured 4-phase workflow.

**Critical rule:** NEVER make multiple sequential Bash calls for API requests. Always write ONE Python script that runs all searches, then execute it once. All rate limiting is handled inside `s2.py` automatically.

## Update check

Throttle to one check per 24 hours per installation; never mutate the skill directory without explicit user consent.

1. If `<this-skill-dir>/.last_update` exists and is less than 24 hours old, skip this step entirely.

2. Otherwise, fetch the latest tag from upstream:

   ```bash
   git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
     | awk '{print $2}' | sed 's|refs/tags/||' \
     | sort -V | tail -1
   ```

3. Compare with this skill's `metadata.version` from the frontmatter. If the upstream tag is strictly newer (semver), tell the user one line and ask:

   > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

   If they say yes, run `git -C <this-skill-dir> pull --ff-only`. Refresh `.last_update` either way so the prompt doesn't repeat for 24 hours.

4. If upstream is the same or older, refresh `.last_update` silently and continue.

5. On any failure (offline, not a git checkout — e.g. ClawHub-installed copy, read-only path, no permission), swallow the error silently and continue with the user's task. Do not mention the failure.

## Phase 1: Understand & Plan

Parse the user's intent and choose a search strategy:

### Decision Tree

| User wants... | Strategy | Function |
|---------------|----------|----------|
| Broad topic exploration | Relevance search | `search_relevance()` |
| Precise technical terms, exact phrases | Bulk search with boolean operators | `search_bulk()` with `build_bool_query()` |
| Specific passages or methods | Snippet search | `search_snippets()` |
| Known paper by title | Title match | `match_title()` |
| Known paper by DOI/PMID/ArXiv | Direct lookup | `get_paper()` |
| Papers citing a known work | Citation traversal | `get_citations()` |
| Related to one paper | Single-seed recommendations | `find_similar()` |
| Related to multiple papers | Multi-seed recommendations | `recommend()` |
| Find a researcher | Author search | `search_authors()` |
| Researcher's profile | Author details | `get_author()` |
| Researcher's publications | Author papers | `get_author_papers()` |

### Query Construction Rules

- **Ambiguous terms** (e.g., "stem cells" could mean mesenchymal or stem-like T cells): Use `build_bool_query()` with exact phrases and exclusions
  - Example: `build_bool_query(phrases=["stem-like T cells"], required=["CD4", "TCF7"], excluded=["mesenchymal", "hematopoietic stem cell"])`
- **Multi-context queries** (e.g., "topic X in cancer AND autoimmunity"): Plan separate searches, deduplicate with `deduplicate()`
- **Broad topics**: Use `search_relevance()` with filters (year, venue, fieldsOfStudy, minCitationCount)

### Plan Filters

| Filter | Use when |
|--------|----------|
| `year="2020-"` | Recent work only |
| `publication_date="2024-01-01:2024-06-30"` | Precise date range (YYYY-MM-DD) |
| `fields_of_study="Medicine"` | Restrict to domain |
| `min_citations=10` | Only established papers |
| `pub_types="Review"` | Find reviews/meta-analyses |
| `pub_types="ClinicalTrial"` | Clinical trials only |
| `open_access=True` | Only open access papers |

**Checkpoint:** Before proceeding, verify: (1) search strategy matches user intent, (2) filters are appropriate, (3) query is specific enough to avoid irrelevant results.

## Phase 2: Execute Search

Write ONE Python script that begins with the **standard prelude** below, then runs all searches:

```python
# --- Standard prelude (use in every script) ---
import sys, os, glob
_candidates = [
    os.path.expanduser("~/.claude/skills/semanticscholar-skill"),
    os.path.expanduser("~/.openclaw/skills/semanticscholar-skill"),
    *glob.glob(os.path.expanduser("~/.claude/plugins/**/semanticscholar-skill"), recursive=True),
    *glob.glob(os.path.expanduser("~/.codex/skills/semanticscholar-skill")),
    ".",
]
SKILL_DIR = next((p for p in _candidates if os.path.isfile(os.path.join(p, "s2.py"))), None)
if SKILL_DIR is None:
    raise RuntimeError("Cannot locate semanticscholar-skill (s2.py not found)")
sys.path.insert(0, SKILL_DIR)
from s2 import *
# --- end prelude ---

# Build precise query
q = build_bool_query(
    phrases=["stem-like T cells"],
    required=["CD4", "IBD"],
    excluded=["mesenchymal"]
)
papers = search_bulk(q, max_results=30, year="2018-", fields_of_study="Medicine")
papers = deduplicate(papers)

print(format_results(papers, "Stem-like CD4 T cells in IBD"))
```

Save to `/tmp/s2_search.py`, then run with `python3 /tmp/s2_search.py` in a single Bash call. Rate limiting, retries, and backoff are automatic inside `s2.py`.

**Checkpoint:** Verify the script ran successfully (no exceptions) and returned results. If 0 results, broaden the query or relax filters before presenting.

### Worked Examples

Each example below assumes the **standard prelude** from Phase 2 is at the top of the script.

**Example 1: Author workflow** — "Find papers by Yann LeCun on self-supervised learning"

```python
authors = search_authors("Yann LeCun", max_results=5)
print(format_authors(authors))

# Use the first match's ID to get their papers
author_id = authors[0]["authorId"]
papers = get_author_papers(author_id, max_results=50)
# Filter locally for topic
ssl_papers = [p for p in papers if "self-supervised" in (p.get("title") or "").lower()]
print(format_results(ssl_papers, "Yann LeCun - Self-Supervised Learning"))
```

**Example 2: Citation chain with intent** — "Who cited the Transformer paper and how did they use it?"

```python
paper = get_paper("DOI:10.48550/arXiv.1706.03762")
print(f"Title: {paper['title']}, Citations: {paper['citationCount']}")

# Citation envelopes carry contextsWithIntent — keep them, don't flatten.
citing = get_citations(paper["paperId"], max_results=50)
citing.sort(key=lambda c: (c.get("citingPaper") or {}).get("citationCount", 0), reverse=True)
print(format_citations(citing, max_items=10))  # renders intent labels + context snippet
```

**Example 3: Multi-seed recommendations with BibTeX export** — "Find papers like these two but not about NLP"

```python
recs = recommend(
    positive_ids=["DOI:10.1038/nature14539", "ARXIV:2010.11929"],
    negative_ids=["ARXIV:1706.03762"],
    limit=20
)
print(format_results(recs, "Vision papers like Deep Learning & ViT, excluding NLP"))

# Export BibTeX for top results
bib_data = batch_papers([r["paperId"] for r in recs[:10]], fields="title,citationStyles")
print(export_bibtex(bib_data))
```

## Phase 3: Summarize & Present

- Use `format_results()` for consistent output (summary table + top-10 details)
- If user's language is Chinese, present summaries in Chinese
- Always note total results count and search strategy used
- Highlight most relevant papers based on the user's specific question

## Phase 4: User Interaction Loop

After presenting results, **always offer these options:**

1. **Translate** — titles/summaries to Chinese (or other language)
2. **Details** — full abstract for specific paper numbers
3. **Refine** — narrow or expand search with different terms/filters
4. **Similar** — find papers similar to a specific result (`find_similar()`)
5. **Citations** — who cited a specific paper and how (`get_citations()` + `format_citations()` for intent labels)
6. **Export** — save results via `export_bibtex()`, `export_markdown()`, or `export_json()`
7. **Done** — end search session

Loop until user says done. Each follow-up uses the same single-script pattern.

---

## API Quick Reference

### Helper Module (`s2.py`)

Use the **standard prelude** from Phase 2 at the top of every script. Then call any of the functions below — the module's docstring (`help(s2)` or read `s2.py`) lists each by phase with one-line summaries.

### Paper Search Functions

| Function | Purpose | Max Results |
|----------|---------|-------------|
| `search_relevance(query, **filters)` | Simple broad search | 1,000 |
| `search_bulk(query, sort=..., **filters)` | Boolean precise search | 10,000,000 |
| `search_snippets(query, paper_ids=, authors=, inserted_before=, **filters)` | Full-text passage search | 1,000 |
| `match_title(title)` | Exact title match | 1 |
| `paper_autocomplete(query)` | Query-completion suggestions | — |
| `get_paper(paper_id)` | Single paper details | — |
| `get_citations(paper_id, max_results, publication_date=)` | Who cited this | 10,000 |
| `get_references(paper_id, max_results)` | What this cites | 10,000 |
| `find_similar(paper_id, limit, pool)` | Single-seed recommendations | 500 |
| `recommend(positive_ids, negative_ids, limit)` | Multi-seed recommendations | 500 |
| `batch_papers(ids, fields)` | Batch lookup (≤500) | — |

### Author Functions

| Function | Purpose | Max Results |
|----------|---------|-------------|
| `search_authors(query, max_results)` | Find researchers by name | 1,000 |
| `get_author(author_id)` | Author profile (affiliations, h-index) | — |
| `get_author_papers(author_id, max_results, publication_date=)` | Author's publications | 10,000 |
| `get_paper_authors(paper_id, max_results)` | Paper's author list | 1,000 |
| `batch_authors(ids, fields)` | Batch author lookup (≤1000) | — |

### Filter Parameters (kwargs)

snake_case kwargs are translated to S2 camelCase params automatically (`fields_of_study` → `fieldsOfStudy`, `min_citations` → `minCitationCount`, `publication_date` → `publicationDateOrYear`, `pub_types` → `publicationTypes`, `open_access` → `openAccessPdf`). Use snake_case here.

`year`, `publication_date`, `venue`, `fields_of_study`, `min_citations`, `pub_types`, `open_access`

- `year`: `"2020-"`, `"-2019"`, `"2016-2020"`
- `publication_date`: `"2024-01-01:2024-06-30"` (YYYY-MM-DD range, open-ended OK)
- `pub_types`: `Review`, `JournalArticle`, `Conference`, `ClinicalTrial`, `MetaAnalysis`, `Dataset`, `Book`, `CaseReport`, `Editorial`, `LettersAndComments`, `News`, `Study`, `BookSection`

### Boolean Query Syntax (bulk search only)

| Syntax | Example | Meaning |
|--------|---------|---------|
| `"..."` | `"deep learning"` | Exact phrase |
| `+` | `+transformer` | Must include |
| `-` | `-survey` | Exclude |
| `\|` | `CNN \| RNN` | OR |
| `*` | `neuro*` | Prefix wildcard |
| `()` | `(CNN \| RNN) +attention` | Grouping |

Use `build_bool_query(phrases, required, excluded, or_terms)` to construct safely.

### Output Functions

| Function | Purpose |
|----------|---------|
| `format_table(papers, max_rows=30)` | Markdown summary table |
| `format_details(papers, max_papers=10)` | Detailed entries with TLDR/abstract |
| `format_citations(citations, max_items=10)` | Citation envelopes with intent labels + context snippet |
| `format_results(papers, query_desc)` | Combined: summary + table + details |
| `format_authors(authors, max_rows=20)` | Author table (name, affiliations, h-index) |
| `export_bibtex(papers)` | BibTeX entries (requires `citationStyles` field) |
| `export_markdown(papers, query_desc)` | Full markdown report saved to file |
| `export_json(papers, path)` | JSON export saved to file |
| `deduplicate(papers)` | Remove duplicates by paperId |

### Supported ID Formats

`DOI:10.1038/...`, `ARXIV:2106.15928`, `PMID:19872477`, `PMCID:PMC2323569`, `CorpusId:215416146`, `ACL:2020.acl-main.447`, `DBLP:conf/acl/...`, `MAG:3015453090`, `URL:https://...`

### Paper Fields

Default: `title,year,citationCount,authors,venue,externalIds,tldr`

Additional: `abstract`, `references`, `citations`, `openAccessPdf`, `publicationDate`, `publicationVenue`, `fieldsOfStudy`, `s2FieldsOfStudy`, `journal`, `isOpenAccess`, `referenceCount`, `influentialCitationCount`, `citationStyles`, `embedding`, `textAvailability`

Author fields: `name`, `affiliations`, `paperCount`, `citationCount`, `hIndex`, `homepage`, `externalIds`, `papers`

### Rate Limiting

Handled automatically by `s2.py`: 1.1s gap between requests, exponential backoff (2s→4s→8s→16s→32s, max 60s) on 429/504 errors, up to 5 retries.

### Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `HTTPError 403` | Missing or invalid API key | Verify `S2_API_KEY` is set: `echo $S2_API_KEY` |
| `HTTPError 429` after 5 retries | Sustained rate limit exceeded | Wait 60s, reduce `max_results`, or split into smaller batches |
| `ModuleNotFoundError: s2` | Skill directory not on path | Verify skill is installed at `~/.claude/skills/`, `~/.openclaw/skills/`, or as a Claude Code plugin under `~/.claude/plugins/` |
| `ModuleNotFoundError: requests` | `requests` not installed | `pip install requests` or `uv pip install requests` |
| 0 results returned | Query too specific or filters too narrow | Broaden query, remove filters, try `search_relevance()` instead of `search_bulk()` |
| `KeyError: 'data'` | Endpoint returned error object | Check `r.get("message")` for API error details |
| `tldr` field is empty | Not all papers have TLDR | Fall back to `abstract` field; bulk search never returns `tldr` |
