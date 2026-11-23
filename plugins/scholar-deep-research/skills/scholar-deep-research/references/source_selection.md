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

## Optional: Firecrawl for papers and clinical trials

Off by default, and the sources above stay the default. Reach for it when the user already has a `FIRECRAWL_API_KEY`.

- **Papers.** Firecrawl's research paper index holds PubMed, bioRxiv and medRxiv abstracts plus arXiv preprints. `firecrawl research search-papers "<query>"` runs a semantic search over the abstracts, and `firecrawl research related-papers <ids...> --intent "<intent>"` expands from seed papers. Results carry `pmid:`, `pmcid:`, `doi:` or `arxiv:` ids; pass a PMID, DOI or arXiv id to `scripts/resolve_id.py` to see which search script fetches its record.
- **Clinical trials.** [Firecrawl Alexandria](https://alexandria.firecrawl.dev/categories/life-sciences?utm_source=365-skills&utm_medium=integration) has a ClinicalTrials.gov provider: search studies by condition, intervention or sponsor, or fetch one study by NCT number. `firecrawl list clinicaltrials-gov` shows its tools.

Setup: `npx -y firecrawl-cli@latest init` installs the CLI and the core skills, including `firecrawl-research-index` and `firecrawl-alexandria`. For the skills alone, run `npx skills add firecrawl/skills`.

Firecrawl output is not a `search_*.py` envelope, so treat it like host-native web results: use it to find candidates, and let a paper enter `research_state.json` only through the search scripts.

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
