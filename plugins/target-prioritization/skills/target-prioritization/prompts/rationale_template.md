# Per-gene rationale template

When filling the **Rationale** and **Suggested next step** slots in
`targets_report.md`, follow this template per gene. Keep it tight — 2-3
sentences total for rationale, 1 sentence for next step.

## Rationale (2-3 sentences)

Sentence 1 — **most compelling evidence** (pick the single strongest signal
from the dossier row):
- If `is_focus_disease_associated` → "OpenTargets surfaces a focus-disease
  association (score [max_focus_disease_assoc_score]) — likely backed by
  GWAS / text-mining evidence…"
- Else if `any_focus_disease_drug` → "Already targeted by an approved
  focus-disease drug ([drug name])…"
- Else if `hpa_focus_cell_hits` non-empty AND `cell_context_score >= 0.7`
  → "HPA single-cell data ranks [cell type] in the top-2 expressing cell
  types for this gene (nCPM [val]) — strong target-cell expression…"
- Else if `tissue_specificity == 1.0` (HPA `Tissue enriched` / `Group
  enriched`) → "Narrow tissue expression in [top tissue] (HPA enriched) —
  cleaner therapeutic window than a broadly expressed target…"
- Else if `is_surface` AND `highest_clinical_phase >= 3` → "Surface protein
  with phase III drugs in adjacent indications…"
- Else if `is_surface` AND `maturity_tag in {novel, moderate}` → "Surface
  protein with moderate prior literature ([N] PubMed hits) —
  tractable for antibody / CAR / ADC approaches…"
- Else use whatever component scores highest in the breakdown row.

Sentence 2 — **main risk or caveat**:
- `maturity_tag = uncharted` → "Very thin literature ([N] hits) — risk of
  unknown off-target biology."
- `maturity_tag = saturated` → "Heavily studied ([N] hits); likely IP
  crowded."
- `is_mhc = True` → "MHC-family gene — broad-spectrum effects, hard to
  inhibit selectively."
- `composite` driven by single dimension only → "Score concentrated in one
  dimension — confirm with orthogonal evidence before pursuing."
- No disease association → "Stat signal from DE only; lacks genetic
  corroboration."
- `tissue_specificity <= 0.2` (HPA `Low tissue specificity`) → "Broadly
  expressed across tissues — narrow therapeutic window unlikely without a
  delivery / targeting strategy."
- `cell_context_score == 0` and `hpa_focus_cell_hits` empty → "Not in the
  top-expressing cell types per HPA single-cell data — efficacy in the
  target population uncertain."

Sentence 3 (optional) — **specific project context** if obvious from the
dossier (e.g. "Persists in non-responder cells at post-treatment,
consistent with [pathway] escape"; "Co-expressed with [marker] in the
tumour microenvironment dataset"; "Up in [region] but absent from
healthy control biopsies").

## Suggested next step (1 sentence)

Be concrete and adapted to the user's experimental context. Examples
across domains:
- **Functional genomics**: "siRNA / CRISPRi knockdown in the relevant
  primary cell type; readout the disease-relevant secreted protein or
  phosphorylation marker by ELISA / flow."
- **Histology**: "IHC / RNAscope on patient vs healthy tissue from the
  matching anatomical site to confirm protein-level upregulation."
- **Pharmacology**: "Treat ex-vivo with [tool compound from approved_drugs]
  and compare against the standard-of-care arm."
- **Replication**: "Cross-check expression in an independent public
  cohort with matched contrast (e.g. a GEO / ArrayExpress dataset)."
- **Chemistry**: "If no tool compound exists: structure-based virtual
  screen against UniProt:[id], or commission a fragment-screen pilot."

## Executive summary (top 5–10 genes)

3–5 sentences total at the top of the report. Cover:
1. How many genes scored Tier-1 vs Tier-2.
2. The 2–3 most compelling individual candidates and the headline reason.
3. Any pattern across the top genes (e.g. "5/10 are surface receptors in
   the same signalling cassette, suggesting [pathway] is the dominant
   axis").
4. Caveats / what's missing (e.g. "All candidates derive from a single
   contrast — recommend cross-checking against an orthogonal one").

Keep it factual. Do not invent biology not supported by the dossier rows
or the original DE context.
