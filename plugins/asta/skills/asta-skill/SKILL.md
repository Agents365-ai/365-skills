---
disable-model-invocation: true
name: asta-skill
description: Use when the user needs papers, citations, or authors from the Semantic Scholar corpus through AI2's Asta MCP tools, covering keyword or title search with venue/date filters, who cited a paper, author profiles and publications, ~500-word full-text snippets for evidence, and DOI/arXiv/PMID lookup. Trigger on "find papers on X", "who cited this paper", "papers by <author>", "recent work since 2024", "论文检索", "找论文", "文献综述", "谁引用了这篇", "某作者的论文". Also use for citation counts, h-index, or venue-scoped paper lists. Requires the Asta MCP server; routes intent to the right tool with context-safe limits and fields.
license: MIT
version: 0.4.0
---

# Asta MCP: Academic Paper Search

Asta is Ai2's Scientific Corpus Tool: the Semantic Scholar academic graph exposed over MCP (streamable HTTP). This skill tells agents **which Asta tool to call for which intent**, how to keep responses small enough to read, and which failure modes are silent.

- **MCP endpoint:** `https://asta-tools.allen.ai/mcp/v1`
- **Auth:** `x-api-key` header (request key at <https://share.hsforms.com/1L4hUh20oT3mu8iXJQMV77w3ioxm>)
- **Transport:** streamable HTTP, stateless (no session id, no server-side state between calls)
- **Behavior verified against:** Asta MCP server **v1.12.3**, 2026-10-01

## Prerequisite Check

Before invoking any tool, verify the Asta MCP server is registered in the host agent. Tool names are prefixed by the MCP server name chosen at install time (commonly `asta__<tool>` or `mcp__asta__<tool>`).

If no Asta tools are visible, do **not** make raw HTTP calls or invent results. Tell the user to register `https://asta-tools.allen.ai/mcp/v1` as a streamable HTTP MCP server with an `x-api-key` header, then restart/reload the host. Minimal setup hints:

- Codex CLI: add `[mcp_servers.asta] url = "https://asta-tools.allen.ai/mcp/v1"` and `env_http_headers = { "x-api-key" = "ASTA_API_KEY" }` to `~/.codex/config.toml`.
- Claude Code: run `claude mcp add -t http -s user asta https://asta-tools.allen.ai/mcp/v1 -H "x-api-key: $ASTA_API_KEY"`.
- Generic MCP clients: configure server URL `https://asta-tools.allen.ai/mcp/v1` with header `{ "x-api-key": "<YOUR_API_KEY>" }`.

## Tool Map: Intent → Asta Tool

| User intent | Asta tool | Defaults and shape |
| --- | --- | --- |
| Broad topic search | `search_papers_by_relevance` | `limit` default **50**; supports `venues` + `publication_date_range` |
| Known paper title | `search_paper_by_title` | A resolver, not a searcher: returns the single best match plus `matchScore` (a `limit` of 5 still returned 1 row); supports `venues` + `publication_date_range` |
| One known ID | `get_paper` | IDs must carry a prefix: `DOI:`, `ARXIV:`, `PMID:`, `PMCID:`, `CorpusId:`, `MAG:`, `ACL:`, `URL:`, or a bare 40-hex Semantic Scholar id. A bare arXiv id (`1706.03762`) fails with `Paper with id 1706.03762 not found` |
| Several known IDs | `get_paper_batch` | `ids` is a JSON **array**; unresolvable ids are silently dropped (3 ids in, 1 paper out, no error), so reconcile returned `paperId`s against your input |
| Who cited paper X | `get_citations` | Forward citations, `limit` default **100**; accepts `publication_date_range`, has **no** `venues`; each row is wrapped as `{"citingPaper": {...}}` |
| Find author by name | `search_authors_by_name` | `fields` default `"name"` returns only `name` + `authorId`; `limit` default **100** |
| An author's publications | `get_author_papers` | Field param is `paper_fields`; `limit` default **1000**, newest first; accepts `publication_date_range`, has **no** `venues` |
| Passages mentioning X | `snippet_search` | ~500-word excerpts (title/abstract/body, excludes captions and bibliography); `limit` default **20** and each row is heavy, and fewer rows than `limit` can come back; see its parameters below |

### Parameter names differ per tool (and unknown parameters are ignored, not rejected)

The server accepts unknown arguments silently, so a wrong parameter name produces an unfiltered but successful call. If results look unfiltered, suspect the parameter name before doubting the corpus.

- `get_author_papers` selects fields with **`paper_fields`**, not `fields`. Passing `fields=` is ignored and you get titles only.
- `get_citations` has no `venues`. Passing `venues=` is ignored and citer rows come back unfiltered.
- `snippet_search` has neither `fields` nor `publication_date_range`. It has **`inserted_before`** (corpus insertion date, formats `YYYY-MM-DD` / `YYYY-MM` / `YYYY`), **`paper_ids`** (comma-separated, up to 100 ids, to restrict snippets to specific papers), and `venues`.
- Every tool with a `fields` / `paper_fields` parameter defaults to `title`; omitting it is the quiet way to get an unrankable, unreadable result.
- No tool returns a total count of matches. Report the returned row count, never a corpus total.

### Row and payload budget (measured sizes)

| Call | Rows | Payload |
| --- | --- | --- |
| `search_papers_by_relevance`, `limit=50`, full preset with `abstract` | 50 | ~296 KB (~5.9 KB/row) |
| `get_citations`, default `limit=100`, `fields=title,year,venue` | 100 | ~56 KB (~0.6 KB/row) |
| `get_paper`, `fields=title,year,citations` (Attention Is All You Need) | 1 | ~200 KB |
| `get_paper`, `fields=title,year,references` (same paper, 41 references) | 1 | ~8 KB |
| `get_author_papers`, `limit=100`, `paper_fields=title,year` | 87 | ~33 KB (~0.4 KB/row even without `abstract`) |
| `search_authors_by_name`, `fields=name,paperCount,papers` | 1 author | ~30 KB (all 87 of that author's papers) |
| `snippet_search`, `limit=2` | 1 snippet | ~4.6 KB |

- Always pass an explicit `limit`: 20–50 for paper and citation lists, 5–10 for snippets. Defaults of 50, 100 and 1000 are context blowups.
- `snippet_search` is the one tool whose documented default disagrees with the live server: the published docs page says 250, the live schema says 20, and an unset `limit` measured 20 rows / ~85 KB. Trust the live schema and set `limit` explicitly.
- **Never request `citations` or `references` through `fields`** on `get_paper` / `get_paper_batch`: one highly cited paper returns 200 KB+. Use `get_citations` for forward citations (it paginates); for a reference list, request `references` only on papers you know have fewer than ~100.
- **Never request `papers`** on `search_authors_by_name`: it returns the author's entire publication list and ignores `limit`. Use `get_author_papers` with an explicit `limit` instead.
- Drop `abstract` when the output is a table or a ranking pass; fetch it only for the few papers you will actually describe.

Use task-specific field presets.

Metadata lookup:

```
title,year,authors,venue,tldr,url,abstract
```

Search/ranking/results tables:

```
title,year,authors,venue,tldr,url,abstract,citationCount,influentialCitationCount
```

DOI/export handoff:

```
title,year,authors,venue,tldr,url,externalIds
```

Add `journal`, `publicationDate`, `fieldsOfStudy`, `isOpenAccess` only when needed.

### Undocumented fields that do work (pass-through)

`externalIds`, `citationCount` and `influentialCitationCount` are absent from the documented field list but are transparently passed through to Semantic Scholar and return correctly (verified on v1.12.3). `externalIds` keys seen: `DOI`, `ArXiv`, `PubMed`, `PubMedCentral`, `CorpusId`, `MAG`, `DBLP`. Caveats:

- Not every paper has a DOI, especially arXiv preprints, which may carry only `ArXiv` + `CorpusId`.
- DOI lookup works for the ids tested (`DOI:10.1038/s41586-021-03819-2`, `DOI:10.1101/...`, `DOI:10.1371/journal.pone.0000308` all resolved), but treat it as best effort and fall back to a title search plus `externalIds`.
- `get_paper` also returns `paperId`, `isOpenAccess` and `openAccessPdf` when not requested; `journal` is often only `{"pages": ...}`.
- Treat all of this as best effort and degrade gracefully if a future Asta release drops it.

### Date and venue filters

`publication_date_range` accepts `YYYY-MM-DD:YYYY-MM-DD` with both terms optional, and year or month shorthand: `2021:`, `:2015-01`, `2015:2020`, `2019-03`. It works on `search_papers_by_relevance`, `search_paper_by_title`, `get_citations` and `get_author_papers` (verified correct for `get_author_papers`: `2024:2024` returned exactly the 7 in-range papers of an 87-paper author).

- Papers with an unknown exact date still keep `year`, while `publicationDate` comes back `null`. Unknown dates are treated as January 1 of their year, so boundary-year filtering is approximate.
- `venues` matches Semantic Scholar venue strings. Common abbreviations resolve (verified: `NeurIPS` and `ICML` both returned hits), and the `venue` field comes back canonical (`Neural Information Processing Systems`). Safest pattern: run one unfiltered keyword search, read the `venue` values, then filter with those exact strings.
- A venue string that matches nothing returns zero rows, not an error, so an empty result can mean a wrong venue string rather than a missing paper.

## Response Shapes (verified)

```
paper (get_paper, get_paper_batch, search_*, get_author_papers, get_citations):
  paperId, externalIds{DOI?, ArXiv?, PubMed?, PubMedCentral?, CorpusId?, MAG?, DBLP?},
  title, venue, year, publicationDate?, abstract?, tldr{model, text},
  authors[{authorId, name}], journal{pages?}, citationCount?, influentialCitationCount?,
  isOpenAccess, openAccessPdf, fieldsOfStudy[]

citing row (get_citations):   {"citingPaper": {paperId, title, year, ...}}
author (search_authors_by_name):  authorId, name, affiliations[] (often empty), homepage?,
  paperCount?, citationCount?, hIndex?, externalIds{DBLP: ["Name"]}
snippet (snippet_search):  {"data":[{"score":0.77,
  "paper":{"corpusId":..., "title":..., "authors":["Name", ...], "openAccessInfo":{...}},
  "snippet":{"text":"..."}}], "retrievalVersion":...}
```

- `authors` is a list of objects in paper tools but a list of plain strings inside snippets.
- Snippet papers carry `corpusId`, not `paperId`; look one up with `CorpusId:<corpusId>`.
- `search_paper_by_title` adds `matchScore`; higher is better, useful for accepting or rejecting a fuzzy title.

## Workflow Patterns

### Pattern 1: Topic Discovery

1. `search_papers_by_relevance(keyword, publication_date_range="<current_year-5>:", fields="title,year,authors,venue,tldr,url,citationCount,influentialCitationCount", limit=20)`, computing the lower bound from today's date (in 2026, pass `2021:`); drop or widen the filter if the user wants older work
2. Rank and present the top N by `citationCount` + recency
3. Offer follow-ups: `get_citations` on the most influential hit, or `snippet_search` for specific claims

### Pattern 2: Seed-Paper Expansion

1. `get_paper(DOI|ARXIV|...)` to verify the seed
2. `get_citations(paperId, fields="title,year,venue,citationCount", limit=50)` for forward expansion
3. Optionally `search_papers_by_relevance` with the seed's title terms for sideways discovery
4. Deduplicate by `paperId` before presenting

### Pattern 3: Author Deep-Dive

1. `search_authors_by_name(name, fields="name,affiliations,paperCount,citationCount,hIndex,externalIds", limit=10)`. **These fields must be requested**: the default returns only `name` + `authorId`. Disambiguate by `externalIds.ORCID` when present, then `paperCount` / `citationCount` / `hIndex`; `affiliations` is frequently empty even when requested (verified) and is only a tiebreaker. Name variants split the same person across ids (`F. Theis` and `Fabian J. Theis` were separate profiles), so check the top few candidates rather than the first row.
2. `get_author_papers(authorId, limit=50, paper_fields="title,year,authors,venue,tldr,url,citationCount", publication_date_range=?)` for a bounded first page, newest first
3. Filter client-side by topic keywords or date

### Pattern 4: Evidence Retrieval

1. `snippet_search(claim_query, limit=5)` to find passages making or supporting a claim
2. To ground a claim **within specific papers**, pass `paper_ids="<id1>,<id2>,…"` (≤100) so snippets come only from that set
3. For each hit, `get_paper("CorpusId:<corpusId>")` for full metadata

## Output & Interaction Rules

- Always report **which tool was used** and the returned row count (no tool exposes a total).
- Present up to 10 results as a table (title, year, venue, citations if fetched), then details for the most relevant few.
- If the user writes in Chinese, present summaries in Chinese; keep titles in their original language.
- After results, offer: **Details / Refine / Citations / Snippet / Export / Done**.

## Handling Asta Responses

| Situation | What to do |
| --- | --- |
| `isError: true` in the result | Failures arrive as a normal result with `isError: true` and a plain-text message while HTTP stays 200, so never trust the transport status. Examples: a bad key gives `Error executing tool get_paper: HTTP status 403 Forbidden.`; an unknown tool name gives `Unknown tool: get_references` |
| Empty `content` array | A legitimate empty result (for example a `venues` string that matches nothing). It is not an error |
| Stream carries only `: ping` keepalives and no result | Observed on zero-result queries: the server can hold the SSE stream open until the client times out instead of returning `content: []`. Set a client timeout, retry once, and only then report "no results"; do not silently hang |
| Empty `abstract` | Not all corpus papers have full text. Fall back to `snippet_search`, or present title + `tldr` |
| Author disambiguation uncertain | Request the ranking fields up front (Pattern 3); prefer `externalIds.ORCID`, then `paperCount` / `citationCount` / `hIndex`, with `affiliations` as a tiebreaker only |
| Date-filtered results | `publicationDate` can be `null` while `year` is always present, and unknown dates behave as January 1, so boundary-year filtering is approximate |
| `429 Too Many Requests` | Back off and batch with `get_paper_batch` instead of sequential `get_paper` calls |
| Need DOI / PubMed ID / arXiv ID | Add `externalIds` to `fields`; fall back to `ArXiv` when `DOI` is absent |

## Critical Rules

- **Prefer batched intent over ping-pong.** If a question needs two independent lookups, issue them as parallel MCP calls in one turn, not sequentially.
- **Never guess IDs.** A fuzzy title goes through `search_paper_by_title` first, and ids always carry their prefix.
- **Check `isError` before reading content**, since transport-level status is always 200.
- **Respect rate limits.** An API key buys higher limits but not unlimited ones; stop expanding citation graphs beyond what the user asked for.
- **Do not fabricate fields.** If Asta returns a null `abstract`, `venue` or `citationCount`, say so rather than inventing one.
