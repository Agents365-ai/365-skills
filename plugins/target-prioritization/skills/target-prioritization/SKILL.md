---
name: target-prioritization
description: Prioritize drug targets from a ranked gene list (e.g., scRNA-seq DE output) by orchestrating parallel API queries against UniProt, OpenTargets (with integrated DepMap CRISPR essentiality + gnomAD constraint), PubMed, the Human Protein Atlas (HPA), and ChEMBL tool compounds, then re-ranking by a composite score combining protein localization, druggability, disease genetics, tissue specificity (safety), focus-cell-type expression, CRISPR essentiality, LoF safety constraint, and research maturity. Use whenever the user wants to filter, triage, prioritize, or "do due diligence" on a list of candidate genes for drug discovery, especially after a DE / DEG analysis when they say things like "which of these should I follow up on", "filter for druggable targets", "make a target dossier", "rank these for tractability", "annotate these genes for druggability", or "build a target report". Trigger even when the user says just "filter these candidate genes" or hands over a CSV from a DE pipeline.
metadata: {"openclaw":{"requires":{"bins":["python3","curl"]},"emoji":"🎯"},"version":"0.4.0"}
---

# Target Prioritization

A multi-source drug-target due-diligence pipeline for ranked gene lists.

## When this skill triggers

The user has a list of candidate genes (typically from a DE / DEG / scRNA-seq
analysis) and wants a per-gene dossier across multiple evidence dimensions
plus a composite re-ranking. The DE statistical rank is just the entry
point; the final priority is informed by protein biology, genetics,
druggability, and research maturity.

Common input shapes:
- A CSV with a `gene` column (DE output like `expression_table_pass_either_1s.csv`)
- A plain-text gene list (one symbol per line)
- A list of symbols inline in the user's message

## Output

Three files inside `<output_dir>/`:
1. **`targets_report.md`** — one section per gene, sorted by composite score, with a
   short LLM-written rationale and recommended next step
2. **`targets_summary.csv`** — flat table for sorting/filtering in Excel/pandas
3. **`raw_data/<source>.json`** — raw API responses (audit trail, reusable across
   future re-scorings)

## Pipeline

```
input gene list
   │
   ▼
scripts/orchestrate.py
   │
   ├─► fetch_uniprot.py        → protein localization, surface, MHC, coding
   ├─► fetch_opentargets.py    → tractability, approved drugs, associated
   │                              diseases (subsumes GWAS Catalog via OT's
   │                              integrated genetics evidence), DepMap CRISPR
   │                              essentiality, gnomAD LOEUF / pLI constraint
   ├─► fetch_pubmed.py         → paper counts (total + focus_disease + cell_context)
   ├─► fetch_hpa.py            → HPA tissue / single-cell specificity + nCPM,
   │                              expression cluster, cancer prognostics
   └─► fetch_chembl.py         → top-potency tool compounds per gene (pIC50,
                                  IC50 nM, mechanism) — dossier-only, no score
   │
   ▼
scripts/aggregate.py
   │
   ▼
output_dir/
  ├─ raw_data/*.json
  ├─ targets_summary.csv       ← composite-score-ranked
  └─ targets_report.md         ← Claude fills the rationale sections
```

## How to invoke

```bash
python3 ~/myagents/myskills/target-prioritization/scripts/orchestrate.py \
    --input <gene_list.csv_or_txt> \
    --output <output_dir> \
    [--gene-col gene] \
    [--top 50]
```

- `--input` accepts a CSV (with `--gene-col`, default `gene`), a `.txt`/`.tsv`,
  or any file where the first column has gene symbols. Skips header if first
  cell is `gene`/`symbol`/case-insensitive.
- `--top` limits the dossier to the top N input genes (default 50) — input
  order is preserved up to that cut, then composite-score re-ranks within.

`orchestrate.py` runs the five fetchers in parallel (Python threads, since
all calls are I/O-bound). Each writes a self-contained JSON to
`<output_dir>/raw_data/<source>.json`. Then `aggregate.py` merges them,
computes the composite score using `weights.yaml`, writes
`targets_summary.csv`, and emits a `targets_report.md` skeleton with one
section per gene — the **rationale and risks fields are left blank for
Claude to fill**.

## Composite score

Weights live in `weights.yaml` and can be overridden per-run with `--weights`.
Defaults aim for "find druggable, genetically supported targets with clean
therapeutic window and expression in the cell of interest":

```
composite_score = w1 * druggability_score          (approved drugs, tractability, clin trials)
                + w2 * disease_genetics_score      (OpenTargets disease associations + focus-disease bonus)
                + w3 * tractability_bonus          (surface or secreted vs intracellular)
                + w4 * tissue_specificity          (HPA tissue tag — narrow expression = cleaner window)
                + w5 * cell_context_score          (HPA single-cell nCPM rank in FOCUS_CELL_TYPES)
                + w6 * essentiality_score          (DepMap CRISPR % essential, pan-essentials capped)
                + w7 * safety_constraint_score     (gnomAD LOEUF — high = LoF tolerated → safer to inhibit)
                + w8 * expression_score            (from input DE if present)
                + w9 * novelty_bonus               (favors moderately studied)
                - w10 * over_studied_penalty       (PubMed total > cap → diminishing returns)
```

ChEMBL contributes dossier columns (`chembl_target_id`, `chembl_best_pchembl`,
`chembl_best_ic50_nm`, `chembl_top_compounds`) but no score component — its
job is to surface concrete tool compounds for the "Suggested next step" slot.

Each component is normalized to [0, 1]. The composite is therefore
roughly in [-w7, sum(w1..w6)] and is min-max rescaled before reporting.
**Read `weights.yaml` for the current defaults.**

## Writing the rationale

After `aggregate.py` produces `targets_report.md` with blank rationale
slots, Claude reads the per-gene dossier rows and writes a 2-3 sentence
rationale per gene. Use the template in `prompts/rationale_template.md` —
it specifies the structure (one line on the most compelling evidence, one
line on the main risk, one line on the suggested next experimental step).

For the top 5–10 genes by composite score, also write a short executive
summary at the top of the report. Keep it factual and grounded in the
dossier data; do not hallucinate beyond what the JSONs contain.

## Data source notes

All free, no API key needed. Rate limits handled in fetchers:
- **UniProt REST** — 100 req/sec, batched via `accession` query
- **OpenTargets GraphQL** — generous, single endpoint; provides disease genetics signal via integrated `associatedDiseases`
- **PubMed E-utilities** — 3 req/sec without key; fetchers respect this
- **Human Protein Atlas** — `search_download.php` for symbol→ENSG, then per-ENSG `/<ENSG>.json`; no rate limit documented, fetcher sleeps 0.15s/gene
- **DepMap CRISPR essentiality** — fetched via `target.depMapEssentiality` inside the OpenTargets call (no separate endpoint)
- **gnomAD constraint** — fetched via `target.geneticConstraint` inside the OpenTargets call (avoids gnomAD's WAF on direct API access)
- **ChEMBL REST** — `target/search.json` then `activity.json`; ~5 req/sec friendly, fetcher sleeps 0.2s/gene

For deeper API details and field mappings, see
`references/api_endpoints.md`.

## Retargeting the focus disease + cell context

The skill ships with an autoimmunity / T-cell default but is intentionally
disease-agnostic. Three edits switch the focus:

- `scripts/fetch_opentargets.py` and `scripts/aggregate.py` — change
  `FOCUS_DISEASE_TERMS` to the lowercased substrings that should mark a
  drug or disease association as "in-scope" (e.g.
  `("cancer", "carcinoma", "lymphoma")` for oncology;
  `("alzheimer", "parkinson", "huntington", "als")` for neurodegeneration;
  `("diabetes", "obesity", "fatty liver", "nash")` for metabolic disease).
- `scripts/aggregate.py` — change `FOCUS_CELL_TYPES` to the HPA single-cell
  type names that should drive `cell_context_score`. Must match HPA's exact
  strings (case-sensitive); see comment block above the tuple for examples
  per domain.
- `scripts/fetch_pubmed.py` — adjust the `focus_disease` and
  `cell_context` queries in `CONTEXTS` (these power the PubMed counts in
  the dossier).

No other code changes are needed; the CSV column names already use the
neutral `focus_disease_*` / `cell_context` prefixes.

## When NOT to use this skill

- Single-gene look-ups (overkill — just ask Claude to web-search)
- Non-human genes (most APIs are human-only; fetchers will silently return empty)
- Pure literature review without target ambition — use `scholar-deep-research` or `literature-review` instead

## Iteration tips

The pipeline is designed to be re-runnable cheaply:
- Raw JSON cache means re-scoring with different `weights.yaml` is a one-second `aggregate.py` rerun
- To add a new evidence source, add `scripts/fetch_<source>.py` that writes
  `raw_data/<source>.json` with the same `{gene: {fields}}` shape, then add
  a corresponding term in `aggregate.py::compute_composite_score`.
