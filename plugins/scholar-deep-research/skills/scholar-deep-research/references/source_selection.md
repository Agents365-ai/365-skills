# Source Selection

When you have four databases and limited rounds, where do you spend the queries? This is a one-page decision guide.

## Default — always run

| Source | Why |
|--------|-----|
| **OpenAlex** | Backbone. Free, no key, 240M+ works, citation counts, DOI, PDF URLs when OA. Run first on every cluster. |

## Add by domain

| If the question is about... | Add this source |
|-----------------------------|-----------------|
| Biology, medicine, public health, drugs, clinical trials | **PubMed** — MeSH terms, clinical trial filters, abstracts |
| Computer science, ML, AI, statistics, physics, math | **arXiv** — preprints with the latest unpublished work |
| A *specific* paper (have a DOI/title) | **Crossref** — authoritative metadata, journal lookup, version-of-record |
| Cross-disciplinary topics | All four (overlap is feature, not bug — dedupe handles it) |

## Add by question type

| Question type | Source priority |
|---------------|-----------------|
| "What is known about X?" (overview) | OpenAlex → +PubMed/arXiv by domain |
| "What's the latest in Y?" (recency) | arXiv (CS/ML/physics) or PubMed (bio) → OpenAlex |
| "Compare A vs B" | OpenAlex → cited-by graph from top results |
| "Who works on Z?" (people) | OpenAlex → search by author |
| "What is the seminal paper on W?" | OpenAlex → sort by citations descending |
| "Has X been replicated?" | OpenAlex (forward snowball) → look for "replication" / "reproduction" terms |
| "Are there critiques of paper P?" | Crossref + author search for the critic; OpenAlex cited-by |

## What about Semantic Scholar / Google Scholar / Web of Science?

- **Semantic Scholar** is excellent. We expose it as enrichment via the asta MCP tools when available. If those time out, you lose some semantic ranking but the rest of the pipeline keeps going. Treat it as a bonus, not a dependency.
- **Google Scholar** has no public API (scraping is against ToS and brittle). Skip.
- **Web of Science / Scopus** require institutional access. Mention in the report appendix as "not consulted" if your user explicitly cares about indexing rigor.
- **Brave Search** (web search MCP) is for *non-academic* sources — press releases, blog posts, community discussion of preprints. Only run when the question explicitly needs them.

## What each source is BAD at

- **OpenAlex**: occasional metadata errors (wrong author, wrong year). Verify the top-N before they enter the report.
- **arXiv**: no citation counts, no peer review.
- **Crossref**: only catalogs DOI-registered works; misses arXiv preprints and many gray-lit reports. Citation counts are incoming-only (not as semantic as OpenAlex).
- **PubMed**: biomedical only, and some preprints/non-MEDLINE journals are missing.

## Rate limits and politeness

| Source | Polite-pool ID | Notes |
|--------|----------------|-------|
| OpenAlex | `--email <you@host>` | Higher rate limit, faster queue |
| Crossref | `--email <you@host>` | Same |
| PubMed | `--api-key <key>` | 10 req/s with key, 3 req/s without |
| arXiv | `User-Agent` only | ~1 req/3s; the script doesn't paginate aggressively |

When in doubt, pass `--email`. It costs nothing and unblocks higher throughput.
