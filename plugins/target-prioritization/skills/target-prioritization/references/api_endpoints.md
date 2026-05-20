# API endpoints used by target-prioritization

All endpoints are free and require no API key.

## UniProt REST

- Base: `https://rest.uniprot.org/uniprotkb/search`
- Query format: `(gene:SYMBOL) AND (organism_id:9606) AND (reviewed:true)`
- Fields requested (comma-separated):
  `accession, gene_names, protein_name, cc_subcellular_location,
  protein_existence, keyword, ft_topo_dom, ft_transmem, ft_signal,
  cc_function`
- Rate: ~100 req/sec; we sleep 0.1s between calls to be polite.
- Docs: https://www.uniprot.org/help/api_queries

## OpenTargets GraphQL

- Endpoint: `https://api.platform.opentargets.org/api/v4/graphql`
- Two queries:
  1. `search(queryString: SYMBOL, entityNames: ["target"])` to resolve
     symbol → Ensembl ID
  2. `target(ensemblId: ENSG…)` to get tractability,
     `drugAndClinicalCandidates` (returns rows with
     `maxClinicalStage` like `APPROVAL`, `PHASE_3`, etc.), and
     `associatedDiseases` (integrates GWAS Catalog + other genetics
     evidence sources — so we do NOT call GWAS Catalog directly)
- Stage tokens are uppercase: `APPROVAL` (=approved), `PHASE_4..PHASE_1`,
  `EARLY_PHASE_1`, `PRECLINICAL`, `WITHDRAWN`, `UNKNOWN`. Mapping lives
  in `PHASE_MAP` inside `fetch_opentargets.py`.
- Tractability modality codes: `SM` (small molecule), `AB` (antibody),
  `PR` (protein degrader/other), `OC` (other clinical). Each modality has
  ordered tier labels — we pick the highest tier with `value=True`.
- Rate: generous; 0.2s sleep between targets to avoid hammering.
- Docs: https://platform-docs.opentargets.org/data-access/graphql-api

## Human Protein Atlas

- Symbol → Ensembl resolver:
  `https://www.proteinatlas.org/api/search_download.php?search=SYMBOL&format=json&columns=g,eg&compress=no`
- Per-entry JSON: `https://www.proteinatlas.org/<ENSG>.json` (≈100 fields)
- Subcellular fields are **not** consumed here — UniProt is authoritative.
  HPA contributes:
  - `RNA tissue specificity` (tag like `Tissue enriched / Group enriched
    / Tissue enhanced / Low tissue specificity / Not detected`) and
    `RNA tissue specific nTPM` (dict tissue→nTPM)
  - `RNA single cell type specificity` (analogous tag) and
    `RNA single cell type specific nCPM` (dict cell-type→nCPM)
  - `Single cell expression cluster` (label of HPA's UMAP cluster)
  - `Cancer prognostics - <cancer name>` per-cancer dicts — aggregated into
    `n_prognostic_cancers` + top-3 cancers with `prognostic type` + `p_val`,
    plus the global `RNA cancer specificity` tag
- `FOCUS_CELL_TYPES` in `scripts/aggregate.py` must match HPA's exact
  cell-type strings (e.g. `"T-cells"`, `"Hepatocytes"`, `"Microglial cells"`).
- No documented rate limit; fetcher sleeps 0.15s between calls.
- Docs: https://www.proteinatlas.org/about/help/dataaccess

## PubMed E-utilities

- Endpoint: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
- Three queries per gene: `total`, `focus_disease`, `cell_context`. The
  `focus_disease` and `cell_context` query templates live in
  `scripts/fetch_pubmed.py::CONTEXTS` and can be re-pointed to any
  domain (oncology, neurodegeneration, metabolic, etc.) by editing the
  string.
- Rate: **3 req/sec without API key**; we sleep 0.34s between requests.
  With an NCBI API key (env `NCBI_API_KEY`), up to 10 req/sec — not
  implemented here, easy to add.
- Maturity bins (configurable thresholds):
  - `<5` = uncharted
  - `5-29` = novel
  - `30-99` = moderate
  - `100-499` = well_studied
  - `≥500` = saturated

## Adding a new source

To plug in another evidence source (e.g. DGIdb, OMIM, OpenTargets Genetics,
Reactome):

1. Write `scripts/fetch_<source>.py` accepting `--genes SYM,SYM,…` and
   `--output PATH.json`, writing `{gene: {fields}}`.
2. Add the (name, script_path) tuple to `FETCHERS` in `orchestrate.py`.
3. Add a component term to `compute_components` in `aggregate.py`.
4. Add corresponding `weights:` and (if needed) `flags:` keys to
   `weights.yaml`.
5. Surface the new fields in the markdown skeleton in `aggregate.py`.

No re-fetch needed for downstream re-runs — the raw JSON cache makes
re-scoring effectively free.
