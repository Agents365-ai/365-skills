---
name: scholar-deep-research
description: Use when the user asks for a literature review, academic deep dive, research report, state-of-the-art survey, topic scoping, comparative analysis of methods/papers, grant background, or any request that needs multi-source scholarly evidence with citations. Also trigger proactively when a user question clearly requires academic grounding (e.g. "what's known about X", "compare approach A vs B in the literature", "summarize the field of Y"). Runs an 8-phase (Phase 0..7), script-driven research workflow across 7 federated sources (OpenAlex, arXiv, Crossref, PubMed, DBLP, bioRxiv, Exa) with optional Semantic Scholar / Brave MCP enrichment, with deduplication, transparent ranking, dual-backend citation chasing (OpenAlex + Semantic Scholar), self-critique, and structured report output with verifiable citations.
license: MIT
homepage: https://github.com/Agents365-ai/scholar-deep-research
compatibility: Requires Python 3.9+ with httpx and pypdf (see requirements.txt). Optional: `pip install docling` to enable layout-aware markdown PDF extraction (`extract_pdf.py --engine docling`); auto-used as a fallback for scanned/sparse PDFs. Works offline-first (no MCP required) but enriches with Semantic Scholar / Brave MCP tools when available.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["python3"]},"emoji":"🔬"},"hermes":{"tags":["research","literature-review","academic","papers","citations","survey"],"category":"research"},"pimo":{"tags":["research","literature-review","academic"],"category":"research"},"author":"Agents365-ai","version":"0.15.0"}
---

# Scholar Deep Research

End-to-end academic research workflow that turns a question into a cited, structured report. Built for depth: multi-source federation, transparent ranking, citation chasing, and a mandatory self-critique pass before the report ships.

## When to use

**Explicit triggers:** "literature review", "research report", "state of the art", "survey the field", "what's known about X", "deep research on Y", "systematic review", "scoping review", "compare papers on Z".

**Proactive triggers (use without being asked):**
- User asks a factual question whose honest answer is "it depends on the literature"
- User frames a research plan and needs the background section
- User is drafting a paper intro/related-work and hasn't yet scoped prior work
- User proposes a method and asks whether it's novel

**Do not use when:** a single known paper answers the question, the user wants a tutorial (not a survey), or they're debugging code.

## Guiding principles

1. **Scripts over vibes.** Every search, dedupe, rank, and export step runs through a script in `scripts/`. The same input should produce the same output. Do not improvise ranking or counting by eye.
2. **Sources are federated, not singular.** OpenAlex is the primary backbone (free, 240M+ works, no key). arXiv (CS/ML/physics preprints), Crossref (DOI metadata), PubMed (biomedical), DBLP (CS conferences/journals), bioRxiv (life-sci preprints via Europe PMC), and Exa (open-web, requires `EXA_API_KEY`) fill gaps. Semantic Scholar is also script-driven — `build_citation_graph.py --source s2|both` is the spine path for Phase 4, with better CS / arXiv / cross-disciplinary coverage than OpenAlex; the two graphs disagree more than you'd expect. The asta MCP tools (`mcp__asta__*`) and Brave Search are *skin* — used opportunistically for relevance ranking or non-academic context, never on the critical path. If MCP times out, research continues.
3. **State is persistent.** Everything goes through `research_state.json`. Queries ran, papers seen, decisions made, phase progress. Research becomes resumable and auditable.
4. **Citations are anchors, not decorations.** Every non-trivial claim in the draft carries `[^id]` where `id` matches a paper in state. Unanchored claims are treated as hallucinations and fail the gate.
5. **Saturation, not exhaustion, is the stop signal.** A phase ends when a new round of search adds <20% novel papers AND no new paper has >100 citations.
6. **Self-critique is a phase, not a checkbox.** Phase 6 reads the draft with adversarial intent. Its output goes into the report appendix.

## The 8-phase workflow (Phase 0..7)

```
Phase 0: Scope       → decompose question, pick archetype, init state
Phase 1: Discovery   → multi-source search, dedupe
Phase 2: Triage      → rank, select top-N for deep read
Phase 3: Deep read   → extract evidence per paper
Phase 4: Chasing     → citation graph (forward + backward)
Phase 5: Synthesis   → cluster by theme, map tensions
Phase 6: Self-critique → adversarial review, gap finding
Phase 7: Report      → render archetype template, export bibliography
```

Each phase writes to `research_state.json` before advancing. If the user pauses or a session crashes, the next run reads the state and picks up from the last completed phase.

### Phase 0 — Scope

Before searching anything, decompose the question.

1. **Restate the question** in one sentence. Surface ambiguities.
2. **PICO-style decomposition** (or equivalent for non-biomedical fields):
   - **P**opulation / **P**roblem — what system, species, setting, or phenomenon?
   - **I**ntervention / **I**ndependent var — what method, factor, or manipulation?
   - **C**omparison — against what baseline or alternative?
   - **O**utcome — what is being measured or claimed?
3. **Pick an archetype** that matches user intent (see `references/report_templates.md`):
   - `literature_review` — what is known about X (default)
   - `systematic_review` — rigorous PRISMA-lite, comparison of many studies on one narrow question
   - `scoping_review` — what has been studied and how (breadth over depth)
   - `comparative_analysis` — X vs Y, head-to-head
   - `grant_background` — narrative background + gap for a proposal
4. **Draft keyword clusters** — 3-5 Boolean clusters covering synonyms, acronyms, and variant spellings. Include a "negative" cluster (terms to exclude).
5. **Initialize state:**
   ```bash
   python scripts/research_state.py --state research_state.json init \
     --question "<restated question>" \
     --archetype literature_review
   ```
   (`--state` is top-level and applies to every subcommand; `init` itself takes `--question`, `--archetype`, and optional `--force`.)

When in doubt about archetype, ask the user. The choice shapes everything downstream.

### Phase 1 — Discovery

Run searches across all available sources, in parallel where the source can take it. OpenAlex is primary; the others fill gaps.

**Where parallelism actually pays off.** The right place to fan out is **Phase 3** (one agent per paper to read PDFs concurrently — see `references/agent_prompts/phase3_deep_read.md`). At Phase 1 the bottleneck is the upstream API, not local compute, and parallel fan-out across the same source mostly buys 429s and sticky cooldowns. The skill's bias should be: parallel between *different* sources, serial within *one* source. Concretely:
- **Parallel-friendly**: OpenAlex (polite-pool, very tolerant), Crossref (polite-pool), Exa (paid quota), bioRxiv (Europe PMC).
- **Self-serialised** (file-locked, automatic): arXiv (≥3s/req), PubMed (≥0.34s/req without `NCBI_API_KEY`, ≥0.10s with), DBLP (1s buffer to avoid SSL EOF flakes).

The serialised sources use a per-source file lock under `${SCHOLAR_CACHE_DIR:-.scholar_cache}/rate/<source>.lock`, so even N parallel `search_arxiv.py` invocations from the same agent will queue automatically and sleep the right gap — no agent-side coordination required, but parallel calls don't speed those sources up either, just don't error.

```bash
# Primary (no API key, always available)
python scripts/search_openalex.py --query "<cluster 1>" --limit 50 --state research_state.json
python scripts/search_openalex.py --query "<cluster 2>" --limit 50 --state research_state.json

# Domain-specific (use when relevant)
python scripts/search_arxiv.py    --query "<cluster>" --limit 50 --state research_state.json  # CS/ML/physics preprints
python scripts/search_dblp.py     --query "<cluster>" --limit 50 --state research_state.json  # CS gold-standard bibliography (no abstracts)
python scripts/search_pubmed.py   --query "<cluster>" --limit 50 --state research_state.json  # biomedical (PubMed)
python scripts/search_biorxiv.py  --query "<cluster>" --limit 50 --state research_state.json  # life-sci preprints (bioRxiv + medRxiv via Europe PMC)
python scripts/search_crossref.py --query "<cluster>" --limit 50 --state research_state.json  # DOI-backed metadata

# Open-web coverage (optional, requires EXA_API_KEY) — finds material the
# scholarly APIs miss: lab sites, institutional PDFs, conference mirrors,
# preprints parked outside arXiv, NGO/government reports.
python scripts/search_exa.py --query "<cluster>" --limit 50 --state research_state.json

# Dedupe across sources (DOI-first, title-similarity fallback)
python scripts/dedupe_papers.py --state research_state.json
```

**MCP enrichment (optional, run if available):** call `mcp__asta__search_papers_by_relevance` and `mcp__asta__snippet_search` and feed results via `scripts/research_state.py ingest`. If the MCP call errors or times out, do not retry — move on.

**Iterate.** Read the state file. Are there keyword gaps? Are there authors appearing 3+ times whose other work you haven't pulled? Run another round. Stop when saturation hits — **every source, not just the last one queried:**

```bash
python scripts/research_state.py saturation --state research_state.json
# Returns { "per_source": {...}, "overall_saturated": true/false, ... }
```

`overall_saturated` is true only when every queried source has run at least `--min-rounds` (default 2) rounds AND each is individually below the new-paper percentage and new-citation thresholds. A source that has been queried only once cannot be declared saturated, which rules out the failure mode where a single quiet source falsely ends discovery. Use `--source openalex` to check one source in isolation.

**Budget caps and broad-topic escape hatches.** Phase 1 has two hard caps to prevent runaway agents: `SCHOLAR_PHASE1_MAX_ROUNDS` (default 10 rounds per source) and `SCHOLAR_PHASE1_MAX_REQUESTS_PER_SOURCE` (default 20 ingests per source). Hitting either returns `phase1_budget_exhausted` with a `next:` hint. For genuinely broad topics that cross subfields (e.g. CS-ML topics with multiple keyword clusters), the saturation thresholds can also fail to converge under the defaults — relax them with `SCHOLAR_SATURATION_NEW_PCT` (default 20.0), `SCHOLAR_SATURATION_MAX_CITATIONS` (default 100), and `SCHOLAR_SATURATION_NEW_AUTHORS_PCT` / `SCHOLAR_SATURATION_NEW_VENUES_PCT`. These env vars are honored both by `python scripts/research_state.py saturation` *and* by the G2 gate, so raising them lets the gate accept "good enough" coverage on topics where the default is unreachable.

### Phase 2 — Triage

Rank the deduplicated corpus and pick the top-N for deep reading.

```bash
python scripts/rank_papers.py \
  --state research_state.json \
  --question "<phase 0 question>" \
  --alpha 0.4 --beta 0.3 --gamma 0.2 --delta 0.1 \
  --top 20
```

The formula is transparent — the script prints it and writes the components to state so the report can cite its own methodology:

```
score = α·relevance + β·log10(citations+1)/3 + γ·recency_decay(half-life=5yr) + δ·venue_prior
```

Defaults target a literature review. For a *scoping* review prefer higher `α` (relevance) and lower `β` (citations). For a *systematic* review of a narrow question, lower `α` and higher `β`.

Write the top-N selection to state:

```bash
python scripts/research_state.py select --state research_state.json --top 20
```

**Triage the selection into deep / skim / defer tiers** before advancing. Phase 3 fan-out is the most expensive stage of the workflow; not every selected paper deserves a full agent dispatch:

```bash
python scripts/skim_papers.py --state research_state.json \
  --deep-ratio 0.5 --skim-ratio 0.5
```

Defaults split the top-N evenly: top half → `deep` (agent dispatch in Phase 3), bottom half → `skim` (abstract-derived evidence stub auto-filled, `depth=shallow`). For tighter budgets, use `--deep-ratio 0.3 --skim-ratio 0.5` — the remaining 20% gets `tier=defer` and is removed from `selected_ids` (still queryable as candidates for citation chase).

The script emits `data.deep_tier_preview` listing the deep-tier papers by triage_score. **Show this to the user before advancing** so they can hand-override before agents fan out (re-run with different ratios, or manually re-rank in state). Triage is required before G3 passes — the gate's `triage_applied` check rejects the advance otherwise.

**Optional but recommended — prefetch deep-tier PDFs** before agent fan-out:

```bash
python scripts/prefetch_pdfs.py --state research_state.json \
  --tier deep --concurrency 4
```

Fetches every deep-tier paper's PDF into `${SCHOLAR_CACHE_DIR:-.scholar_cache}/pdfs/<id-hash>/` via `paper-fetch` (with Unpaywall fallback), in parallel waves, and writes `pdf_path` / `pdf_status` / `pdf_source` / `pdf_bytes` per paper. Phase 3 agents then **read the local file directly** instead of each running its own download — Agent context stays focused on reading + reasoning, not on retrying paywalls.

Failures land as `pdf_status='failed'` with a `pdf_failure_code` (`paper_fetch_error`, `no_open_access_pdf`, `pdf_download_failed`, …); papers without a DOI get `pdf_status='no_doi'`. Phase 3 agents check `pdf_path` first and only fall back to `extract_pdf.py --doi` if the prefetched path is missing. Re-running prefetch is cheap: papers with an existing `pdf_path` on disk are skipped (`pdf_status='cached'`).

**Human-in-loop for paywalled PDFs.** When automatic fetch fails (paywall, OA chain exhausted, no DOI), surface a hand-fetch list to the user via `--emit-manifest` (read-only):

```bash
python scripts/prefetch_pdfs.py --state research_state.json --emit-manifest
# Returns { needs_user_download: [{id, doi, title, drop_at, alt_urls}, ...] }
```

The user downloads each PDF (institutional VPN, ResearchGate, etc.) and drops it at the listed `drop_at` path (any `*.pdf` filename in that subdir works). On the next normal `prefetch_pdfs.py` run, dropped files are auto-absorbed as `pdf_source='user_provided'` without re-fetching.

Skip prefetch entirely when paper-fetch is not installed AND you don't want Unpaywall traffic — Phase 3 agents will then download per-paper inside their own contexts (slower, noisier, but functionally identical).

### Phase 3 — Deep read (parallel agent fan-out)

Phase 3 splits by tier:

- **`tier=skim`** — `apply_triage()` already wrote an abstract-derived evidence stub with `depth=shallow`. No further action needed.
- **`tier=deep`** — dispatch one agent per paper, in parallel waves of 8–10. Each agent reads the PDF, writes structured evidence back to state, and returns one JSON line. The host's main context never sees the full PDF text.

The agent prompt template lives at `references/agent_prompts/phase3_deep_read.md`. Load it once, instantiate per paper, and dispatch all N tool_use calls in a **single message** so they fan out concurrently. Per-agent contract:

- **Input:** `paper_id`, `doi`, `pdf_url`, `abstract`, `question`, `state_path`
- **Action:** `extract_pdf.py --doi <doi> --output <tmp>` → read text → write `evidence --depth full`
- **Output:** one line `{"paper_id": "...", "status": "ok"|"evidence_unavailable", ...}`

The state CLI is exclusive-locked, so N agents writing concurrent `evidence` calls are serialized automatically — no coordination needed.

```bash
# After all wave(s) complete, verify deep-tier coverage:
python scripts/research_state.py advance --state research_state.json \
  --to 4 --check-only
```

If `deep_tier_full_evidence` is failing, dispatch a follow-up wave for the missing ids only. If a paper's full text is genuinely unreachable (paywall, exhausted OA chain), the agent should write a `depth=shallow` record with `method` starting `evidence_unavailable:` per the prompt's failure-mode section — that record satisfies `depth_marks_valid` without inflating the deep-tier coverage count.

**Manual fallback (no agents available).** Hosts that cannot dispatch parallel agents (some non-CC platforms) can run Phase 3 sequentially in the main session: for each `tier=deep` paper, `extract_pdf.py --doi <doi>` then `research_state.py evidence --id <pid> --depth full ...`. Slower and burns more context, but the gate logic is identical.

### Phase 4 — Citation chasing

Take the top 5-10 highest-ranked papers and expand the graph.

```bash
# Preview the request count first — this is the most expensive command
python scripts/build_citation_graph.py \
  --state research_state.json \
  --seed-top 8 --direction both --depth 1 --dry-run

# Run with an idempotency key so a retry after a network blip is free
python scripts/build_citation_graph.py \
  --state research_state.json \
  --seed-top 8 --direction both --depth 1 \
  --idempotency-key "chase-$(date -u +%Y%m%dT%H%M)"
```

The script pulls backward references (what did this paper cite?) and forward citations (who cited this paper?), deduplicates against existing state, and writes new candidate papers with `discovered_via: citation_chase`. Run rank + deep read again on any new high-scoring additions.

**Dual backend.** `--source openalex|s2|both` (default `both`). OpenAlex covers most fields well; Semantic Scholar (S2) has better CS / arXiv / cross-disciplinary coverage. The two graphs disagree more than you'd expect — running both then deduping by id surfaces real coverage gaps. S2 needs a DOI / arXiv id / PMID on each seed (it doesn't accept OpenAlex ids); seeds without one skip the S2 backend. `S2_API_KEY` env var raises the S2 quota; without it the public quota of ~1 req/s applies.

**Idempotency.** When `--idempotency-key <k>` is set, the first successful run writes `{response, signature}` to `.scholar_cache/<hash>.json`. A retried run with the same key replays the cached response without re-hitting OpenAlex or re-mutating state. Reusing the same key with different arguments returns `idempotency_key_mismatch` rather than silently serving stale data. Cache directory: `SCHOLAR_CACHE_DIR` env var, default `.scholar_cache/`.

**Special case — a highly cited paper has never been challenged.** If rank says a paper is top-3 by citations but no critiques appear in the corpus, search explicitly for `"<first author> <year>" critique OR limitations OR reanalysis OR failed replication`. This is the confirmation-bias backstop.

### Phase 5 — Synthesis

No scripts here — this is where the agent earns its keep. Cluster and structure:

1. **Thematic clustering.** Group the top-N into 3-6 themes that map onto the report outline. Themes should be orthogonal: a paper can be primary to one, secondary to at most one other.
2. **Tension map.** Where do papers disagree? For each disagreement, note: which papers, on what, and whether the disagreement is empirical (different data), methodological (different tools), or theoretical (different framings).
3. **Timeline.** When relevant, a chronological arc: seminal paper → consolidation → refinement → current frontier.
4. **Venn / gap.** What has been studied well, partially, and not at all? The gap is the pivot for Phase 7.

### Phase 6 — Self-critique

**This is not optional.** Load `assets/prompts/self_critique.md` and run the full checklist against your draft (still unpublished). The checklist covers:

- Single-source claims (any claim backed by only one paper?)
- Citation/recency skew (is the latest-2-years window covered?)
- Venue bias (is the corpus dominated by one journal/venue?)
- Author bias (does one lab dominate the citations?)
- Untested high-citation papers (anyone cite a paper without reading a critique?)
- Contradictions buried (any tension in Phase 5 that got glossed over?)
- Archetype fit (does the structure match the chosen archetype?)
- Unanchored claims (any statement without a `[^id]` anchor?)

Write findings to `research_state.json` under `self_critique` and fix blockers before Phase 7. Findings go into the report appendix verbatim — the reader deserves to see what the research process doubted itself about.

### Phase 7 — Report

Render an archetype scaffold from state, then fill the agent-prose
slots and validate anchors:

```bash
# Generate the scaffold — fills header, themes, tensions, methodology
# appendix, self-critique appendix, and bibliography anchor index from
# state. Leaves `<!-- AGENT: ... -->` placeholders for prose.
python scripts/render_report.py --state research_state.json
# → reports/<slug>_<YYYYMMDD>.md by default; pass --output PATH to override.

# After filling in the prose, lint every [^id] anchor against
# state.papers. Catches typo'd anchors before the report ships.
python scripts/render_report.py --state research_state.json \
  --lint reports/<slug>_<YYYYMMDD>.md

# Export bibliography in the user's preferred format
python scripts/export_bibtex.py --state research_state.json --format bibtex --output refs.bib
python scripts/export_bibtex.py --state research_state.json --format csl-json --output refs.json
```

The scaffold's body uses `[^id]` anchors (the paper id from state). The
bibliography section at the bottom carries one definition per selected
paper. The lint mode flags `unknown_anchors_used` (typos) and
`undefined_in_text` (anchors with no footnote definition); both are
blockers. `unused_definitions` is a soft signal — selected papers that
ended up not cited inline.

**Save path convention:** `reports/<slug>_<YYYYMMDD>.md`. The skill does not write outside the working directory unless the user specifies a path.

## Report archetype selection

| Archetype | When to use | Primary output shape |
|-----------|-------------|----------------------|
| `literature_review` | User wants to know what's established about a topic | Thematic sections + synthesis + gap |
| `systematic_review` | Narrow question, many studies, need rigorous comparison | PRISMA-lite flow + extraction table + pooled findings |
| `scoping_review` | Broad topic, "what has been studied?" | Coverage map + methods inventory + research gap |
| `comparative_analysis` | "A vs B" — methods, models, approaches | Axes of comparison + per-axis verdict + recommendation |
| `grant_background` | Narrative for a proposal introduction | Problem significance + what's known + what's missing + why our approach |

Templates live in `assets/templates/<archetype>.md`. Load only the one you need.

## Scripts reference

| Script | Purpose |
|--------|---------|
| `research_state.py` | Init, read, write, query the state file. Central to every phase. |
| `search_openalex.py` | Primary search (no key, 240M works, citation counts). |
| `search_arxiv.py` | arXiv API — preprints and CS/ML/physics. |
| `search_crossref.py` | Crossref REST — authoritative DOI metadata. |
| `search_pubmed.py` | NCBI E-utilities — biomedical corpus with MeSH. |
| `search_exa.py` | Exa neural web search (optional, key-gated) — open-web coverage the scholarly APIs miss. |
| `list_sources.py` | Registry of all `search_*.py` sources with their capabilities (domain, index type, freshness lag, auth requirement, …). Filter by `--domain`, `--auth`, `--index-type`, or `--needs-relevance-filter` so an orchestrator can pick the right sources for the question. Schema defined in `_search_meta.py`. |
| `dedupe_papers.py` | DOI normalization + title similarity merging across sources. |
| `rank_papers.py` | Transparent scoring formula. Prints the formula and per-paper components. |
| `skim_papers.py` | Phase-3 triage. Splits selected papers into `deep` / `skim` / `defer` tiers on cheap deterministic signals, refines `selected_ids`, auto-fills evidence stubs for skim tier. Runs at the close of Phase 2 before G3. |
| `prefetch_pdfs.py` | Optional. Pulls deep-tier PDFs into a stable cache via paper-fetch (with Unpaywall fallback) before Phase 3 agent fan-out. Concurrent (`--concurrency`), idempotent on re-run, fail-soft per paper. Writes `pdf_path` / `pdf_status` per paper so agents read a local file instead of re-downloading. |
| `build_citation_graph.py` | Forward/backward snowballing via OpenAlex. |
| `extract_pdf.py` | Full-text extraction. `--engine auto` (default) tries pypdf first and auto-upgrades to **docling** (markdown output, layout-aware, OCR for scanned regions) when pypdf result looks scanned/sparse — install with `pip install docling`. Force with `--engine pypdf\|docling`. Tune docling's OCR with `--ocr-backend {auto,rapidocr,ocrmac,easyocr,tesseract,none}` and `--ocr-lang <list>` (per-backend lang vocab — see `--help`). Accepts `--input`, `--url`, or `--doi`. DOI mode resolves via [paper-fetch](https://github.com/Agents365-ai/paper-fetch) skill if installed, falls back to Unpaywall. `--idempotency-key` caches extracted text so retries skip re-extraction. |
| `export_bibtex.py` | BibTeX / CSL-JSON / RIS export from state. |
| `render_report.py` | Phase 7 — render an archetype scaffold from `state.themes` / `state.tensions` / `state.queries` / `state.ranking` / `state.self_critique`, with `<!-- AGENT: ... -->` slots for prose. `--lint <report.md>` validates every `[^id]` anchor against `state.papers`. |

All scripts accept `--help`, `--schema`, emit a structured JSON envelope on stdout, and use `research_state.json` as the single source of truth. Every script is idempotent on the state file (network-layer idempotency is P1 work).

### CLI contract, env vars, and state schema

Three details that agents discover by running scripts and reading the JSON envelopes — kept out of the body to save context. Load on demand:

- `references/cli_contract.md` — the success/failure envelope shape, exit codes, `--schema` introspection, and idempotency cache semantics.
- `references/env_vars.md` — the trust-boundary env vars (`SCHOLAR_*`, `NCBI_API_KEY`, `EXA_API_KEY`, `S2_API_KEY`, `PAPER_FETCH_SCRIPT`). Agents should never set these — surface to the user when a script reports a missing one.
- `references/state_schema.md` — the `research_state.json` shape. Prefer `python scripts/research_state.py --schema` for the live, machine-readable version.

## Completion gates

Each phase transition has a gate (G1..G7). Advance ONLY via:

```bash
python scripts/research_state.py --state <path> advance          # advance by 1
python scripts/research_state.py --state <path> advance --check-only   # preview only
```

The gate predicates are enforced in `scripts/_gates.py`. Direct `set --field phase` is rejected — the `phase` field is no longer settable. If the gate fails, the envelope lists the failing checks by name so you know exactly what's missing.

| Target | Gate (enforced) |
|--------|-----------------|
| G1 (→ 1) | Question set, archetype valid, state initialized. *`≥3 keyword clusters` is host-checked.* |
| G2 (→ 2) | `overall_saturated == true` across all queried sources AND ≥3 distinct sources in `state.queries`. |
| G3 (→ 3) | `state.ranking` recorded; `selected_ids` non-empty; every selected paper has `score_components`; `state.triage_complete=true` (run `skim_papers.py`). |
| G4 (→ 4) | All selected papers have `depth ∈ {full, shallow}` AND every `tier=deep` paper either (a) has `depth=full`, or (b) has `depth=shallow` *with* `evidence.method` starting one of two documented escape-hatch prefixes: `evidence_unavailable:` (PDF unreachable — paywall, exhausted OA chain, scanned) or `topic_mismatch:` (PDF read fully but off-topic — Phase 2 ranking false-positive). Skim-tier `depth=shallow` is by design and does not block. |
| G5 (→ 5) | ≥1 query whose `source` contains `citation_chase` (any backend layout — `openalex_citation_chase`, `s2_citation_chase`, or the default dual `openalex_s2_citation_chase`) AND `hits > 0`. |
| G6 (→ 6) | `len(themes) ≥ 3` AND (`len(tensions) ≥ 1` OR a critique finding mentioning "no tensions"). |
| G7 (→ 7) | `state.self_critique.appendix` non-empty; `len(resolved) ≥ len(findings)`. |

## Enrichment with MCP tools

Semantic Scholar coverage is *not* one of these — it is reached through the script path (`build_citation_graph.py --source s2|both`) and is a first-class Phase 4 backend, not enrichment. The MCP tools below are the genuine skin layer: they may time out, get renamed, or be absent entirely, and no phase output depends on them.

If the session has asta or Brave Search MCP tools available, use them as enrichment:

- `mcp__asta__search_papers_by_relevance` — good for dense relevance ranking on top of the script searches
- `mcp__asta__get_citations` — lighter weight than `build_citation_graph.py` for spot-checking a single seed paper
- `mcp__asta__snippet_search` — grep-like search across abstracts
- Brave Search — non-academic sources (blog posts, press releases, pre-print discussion)

**Treat MCP tools as unreliable by design** — they may timeout or be unavailable. Never place a phase-critical step behind an MCP call. Scripts are the spine; MCP is the skin.

## Pitfalls (short list; see `references/pitfalls.md` for detail)

1. **Treating the first page of search results as "the literature"** — run multiple keyword clusters and chase citations.
2. **Unanchored claims** — every non-trivial statement in the report needs a `[^id]` pointing to a paper in state.
3. **Confirmation bias** — actively search for critiques of top-cited papers; see Phase 4 special case.
4. **Preprint conflation** — arXiv/bioRxiv are preprints; tag them as such in the report and weight evidence accordingly. Lint-safe convention: place the anchor and marker separately — `[^id] *(preprint)*`, not `[^id, preprint]` (commas inside footnote brackets break Markdown parsing and the `render_report.py --lint` check).
5. **Venue monoculture** — if >60% of top-N come from one journal/venue, broaden sources.
6. **Author monoculture** — same for a single lab or author.
7. **Recency collapse** — the last 2 years matter for "state of the art" framings; check explicit coverage.
8. **Stale MCP tool names** — MCP servers rename tools; always list available tools before assuming names. Script paths are stable; MCP names are not.
9. **Single-shot search** — budget for ≥3 search rounds per cluster, not one.
10. **Skipping self-critique** — the temptation to ship a clean draft is exactly when Phase 6 catches the most.

## Example interaction

A complete walk-through (CRISPR base editing for DMD — Phase 0 question restate through Phase 7 report and bibliography) lives in `references/example_run.md`. Read it once when you want to see what a healthy run looks like end-to-end; it's not load-bearing for routine sessions.

## References

Modular documentation, loaded only when needed:

- `references/search_strategies.md` — Boolean clusters, PICO, snowballing, saturation math
- `references/source_selection.md` — which database for which question
- `references/quality_assessment.md` — CRAAP, journal tier, retraction check, preprint handling
- `references/report_templates.md` — the 5 archetypes with section-by-section guidance
- `references/pitfalls.md` — long-form version of the pitfalls list with examples
- `references/cli_contract.md` — JSON envelope shape, exit codes, `--schema` introspection, idempotency cache
- `references/env_vars.md` — trust-boundary configuration (SCHOLAR_*, NCBI_API_KEY, EXA_API_KEY, S2_API_KEY, PAPER_FETCH_SCRIPT)
- `references/state_schema.md` — `research_state.json` shape and ID-normalization rules
- `references/example_run.md` — full end-to-end example (CRISPR base editing for DMD)
- `references/agent_prompts/phase3_deep_read.md` — per-paper prompt for parallel agent fan-out in Phase 3
