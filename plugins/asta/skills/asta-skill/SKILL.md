---
name: asta-skill
description: Domain expertise for Ai2 Asta MCP tools (Semantic Scholar corpus). Intent-to-tool routing, safe defaults, workflow patterns, and pitfall warnings for academic paper search, citation traversal, and author discovery.
license: MIT
homepage: https://github.com/Agents365-ai/asta-skill
compatibility: Requires an MCP-capable host (Claude Code, Codex, Cursor, Windsurf, Hermes, OpenClaw/ClawHub) with the Asta MCP server registered at https://asta-tools.allen.ai/mcp/v1 using an x-api-key header. The skill does not make HTTP calls itself.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"env":["ASTA_API_KEY"]},"emoji":"🔭","mcp":{"name":"asta","type":"http","url":"https://asta-tools.allen.ai/mcp/v1","headers":{"x-api-key":"${ASTA_API_KEY}"}}},"hermes":{"tags":["asta","semantic-scholar","academic","paper-search","citation","mcp"],"category":"research","requires_tools":["mcp"],"related_skills":["semanticscholar-skill","literature-review"]},"pimo":{"category":"research","tags":["asta","semantic-scholar","academic","paper-search","citation","mcp"]},"author":"Agents365-ai","version":"0.3.3"}
---

# Asta MCP — Academic Paper Search

Asta is Ai2's Scientific Corpus Tool, exposing the Semantic Scholar academic graph over MCP (streamable HTTP transport). This skill tells agents **which Asta tool to call for which intent**, and how to compose them into useful workflows.

- **MCP endpoint:** `https://asta-tools.allen.ai/mcp/v1`
- **Auth:** `x-api-key` header (request key at https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm)
- **Transport:** streamable HTTP

## Prerequisite Check

Before invoking any tool, verify the Asta MCP server is registered in the host agent. Tool names will be prefixed by the MCP server name chosen at install time (commonly `asta__<tool>` or `mcp__asta__<tool>`). If no Asta tools are visible, direct the user to the **Installation** section below.

## Tool Map — Intent → Asta Tool

| User intent | Asta tool | Notes |
|---|---|---|
| Broad topic search | `search_papers_by_relevance` | Supports venue + date filters |
| Known paper title | `search_paper_by_title` | Optional `venues` + `publication_date_range` filters |
| Known DOI / arXiv / PMID / CorpusId / MAG / ACL / SHA / URL | `get_paper` | Single-paper lookup |
| Multiple known IDs at once | `get_paper_batch` | Batch lookup — pass `ids` as a **JSON array** (not a comma-separated string, unlike `snippet_search`'s `paper_ids`); prefer over N sequential `get_paper` calls; unresolvable IDs are silently dropped (no null/error), so reconcile returned `paperId`s against your input |
| Who cited paper X | `get_citations` | Forward citations, paginated; accepts `publication_date_range` but **not** `venues`; `limit` defaults to 100 |
| Find author by name | `search_authors_by_name` | Default `fields="name"` returns only `name` + `authorId` — **explicitly request** `affiliations,paperCount,citationCount,hIndex,externalIds` to get anything rankable; `externalIds` carries ORCID/DBLP |
| An author's publications | `get_author_papers` | Pass author id; field param is **`paper_fields`** (not `fields`); `limit` defaults to **1000** — set it explicitly |
| Find passages mentioning X | `snippet_search` | ~500-word excerpts (title/abstract/body, excludes captions & bibliography); see snippet-specific params below |

Most search/citation tools accept **`publication_date_range`** (format `YYYY-MM-DD:YYYY-MM-DD`; year shorthand like `"2021:"`, `":2015-01"`, `"2015:2020"` is also accepted), **`venues`**, and **`fields`** for field selection — pass them whenever the user's intent constrains scope (e.g., "recent", "since 2022", "at NeurIPS"). `venues` matches Semantic Scholar's **exact** venue strings (comma-separated, e.g. `"Nature,N. Engl. J. Med."`); a casual name like "NeurIPS" may not match, so fall back to a date/keyword filter when a venue lookup returns empty.

**Per-tool parameter exceptions** (verified against the live server — getting these wrong yields a malformed or silently-ignored argument):
- `get_author_papers` names its field-selection param **`paper_fields`**, not `fields` (passing `fields=` is silently ignored — you get titles only), and accepts **no** `venues` filter, so narrow its results by topic/venue client-side.
- `get_citations` accepts `publication_date_range` but **not** `venues`.
- `snippet_search` accepts **neither** `fields` nor `publication_date_range`. Instead it has: **`inserted_before`** (date filter, `YYYY-MM-DD`/`YYYY-MM`/`YYYY`), **`paper_ids`** (comma-separated list of ≤100 IDs to restrict snippets to specific papers), and `venues`.

### ⚠️ `fields` parameter — avoid context blowups

`get_paper` / `get_paper_batch` accept a `fields` string. **Never request `citations` or `references`** via `fields` — a single highly-cited paper (e.g. *Attention Is All You Need*) returns 200k+ characters and will overflow the agent's context window. Use the dedicated `get_citations` tool for forward citations (it paginates). Asta does not provide a dedicated `get_references` tool — to retrieve a paper's reference list, use `get_paper` with `fields=references` only for papers you know have a small reference list (typically < 100).

**Watch row counts too**, not just per-row size: default `limit`s are large — `get_author_papers` returns up to **1000**, `get_citations` **100**, `search_papers_by_relevance` **50**, and `snippet_search` **20** (each snippet is ~500 words, making it the heaviest tool per row). Pass an explicit small `limit` — e.g. 20–50 for paper/citation lists, ~5–10 for snippets — unless the user asked for the full list.

Safe default `fields` for `get_paper`:
```
title,year,authors,venue,tldr,url,abstract
```
Add `journal`, `publicationDate`, `fieldsOfStudy`, `isOpenAccess` only when needed.

**Example call** (topic search, ranked by citations, DOI exposed for downstream fetch):
```
search_papers_by_relevance(
  keyword="mixture of experts routing",
  publication_date_range="2023:",
  fields="title,year,authors,venue,tldr,url,externalIds,citationCount",
  limit=20,
)
```

### Retrieving DOI / external IDs (undocumented but supported)

Asta's official `fields` list does **not** include `externalIds`, but the field is transparently passed through to the underlying Semantic Scholar API and works in practice. Add `externalIds` to `fields` to retrieve `DOI`, `PubMed`, `PubMedCentral`, `ArXiv`, `MAG`, `DBLP`, `CorpusId`. The same pass-through applies to **`citationCount`** and **`influentialCitationCount`** (also absent from the official list but verified to return) — request them when ranking results by citations. Caveats:
- Not all papers have a DOI — pure arXiv preprints often only return `ArXiv` + `CorpusId`.
- `get_paper("DOI:...")` lookup is not 100% reliable; some valid DOIs return `not found`. Prefer searching by title first, then reading `externalIds` off the result.
- Since this is undocumented, treat it as best-effort and degrade gracefully if a future Asta release drops it.

## Workflow Patterns

### Pattern 1 — Topic Discovery
1. `search_papers_by_relevance(keyword, publication_date_range="<current_year-5>:", venues=?)` → initial hits (compute the lower bound from today's date — e.g., in 2026 pass `publication_date_range="2021:"`; adjust or drop the filter if the user asks for older work)
2. Rank/present top N by citationCount + recency
3. Offer follow-ups: `get_citations` on the most influential, or `snippet_search` for specific claims

### Pattern 2 — Seed-Paper Expansion
1. `get_paper(DOI|arXiv|...)` → verify seed
2. `get_citations(paperId)` → forward expansion
3. Optionally `search_papers_by_relevance` with seed title terms for sideways discovery
4. Deduplicate by paperId before presenting

### Pattern 3 — Author Deep-Dive
1. `search_authors_by_name(name, fields="name,affiliations,paperCount,citationCount,hIndex,externalIds")` → pick correct profile. **You must request these fields** — the default `fields="name"` returns only `name` + `authorId`, leaving nothing to rank on. Disambiguate by `externalIds.ORCID` when present (strongest signal), then `paperCount`/`citationCount`/`hIndex`; `affiliations` is often empty even when requested, so use it only as a tiebreaker
2. `get_author_papers(authorId)` → full publication list
3. Filter client-side by topic keywords or date

### Pattern 4 — Evidence Retrieval
1. `snippet_search(claim_query)` → find passages making/supporting a claim
2. To ground a claim **within specific papers**, pass `paper_ids="<id1>,<id2>,…"` (≤100) so snippets are drawn only from that set
3. For each hit, optionally `get_paper(id)` for full metadata

## Output & Interaction Rules

- Always report **total count** and **which tool was used**.
- Present top 10 as a table (title, year, venue, citations), then details for the most relevant.
- If the user writes in Chinese, present summaries in Chinese; keep titles in original language.
- After results, offer: **Details / Refine / Citations / Snippet / Export / Done**.

## Critical Rules

- **Prefer batched intent over ping-pong.** If the user's question needs two independent lookups, issue them as parallel MCP tool calls in one turn, not sequentially.
- **Never guess IDs.** If a user gives a fuzzy title, use `search_paper_by_title` before `get_paper`.
- **Respect rate limits.** An API key buys higher limits but not unlimited — stop expanding citation graphs beyond what the user asked for.
- **Do not fabricate fields.** If Asta returns null `abstract` or `venue`, say so rather than inventing.

## Handling Asta responses

| Situation | What to do |
|---|---|
| Empty `abstract` | Not all corpus papers have full text — use `snippet_search`, or fall back to title + TLDR |
| Author disambiguation uncertain | Request the ranking fields up front (see Pattern 3 — they are **not** returned by default); prefer `externalIds.ORCID`, then `paperCount`/`citationCount`/`hIndex`, with `affiliations` only as a tiebreaker |
| Date-filtered results | A `publication_date_range` filter can return records whose `publicationDate` is `null` (only `year` is guaranteed), and papers with unknown dates are treated as published **Jan 1** of their year — so boundary-year filtering is approximate |
| `429 Too Many Requests` | Back off; batch with `get_paper_batch` instead of sequential `get_paper` calls |
| Need DOI / PubMed ID / arXiv ID | Add `externalIds` to `fields` (see "Retrieving DOI" above); fall back to `ArXiv` ID when `DOI` is absent |
