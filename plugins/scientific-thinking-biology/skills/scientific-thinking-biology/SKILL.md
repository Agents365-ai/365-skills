---
name: scientific-thinking-biology
description: Use when interpreting biological research findings, evaluating life science evidence, analyzing molecular or cellular mechanisms, comparing competing biological hypotheses, designing or critiquing experiments in biology, genetics, genomics, cell biology, immunology, neuroscience, ecology, or any life science domain. Triggers on questions about gene function, pathways, phenotypes, GWAS hits, single-cell data, animal models, clinical translation, evolutionary arguments, or any biology/life science reasoning task.
license: MIT
homepage: https://github.com/Agents365-ai/365-skills
compatibility: No external tool dependencies. Works with any LLM-based agent on any platform.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{},"emoji":"🧬","os":["darwin","linux","win32"]},"hermes":{"tags":["scientific-thinking","biology","life-science","genomics","cell-biology","immunology","neuroscience","genetics","molecular-biology","experiment-design"],"category":"research","requires_tools":[],"related_skills":["literature-review","paper-reader","zotero-cli-cc","nh-bioinfo-practice-skill"]},"pimo":{"category":"research","tags":["biology","scientific-thinking","life-science","genomics","mechanism","hypothesis"]},"author":"Agents365-ai","version":"1.0.0"}
---

# Scientific Thinking — Biology & Life Science

A meta-skill for structured, evidence-aware, boundary-conscious scientific reasoning in biology and life science. Biology is complex: phenotypes arise from networks not single genes, model systems don't always translate, and the same data can support multiple mechanistic models. Your role is not just to answer — it is to reason like a careful biologist.

## When to Use

- Interpreting experimental results from cell biology, genetics, genomics, immunology, neuroscience, or any life science
- Analyzing molecular mechanisms, signaling pathways, or gene regulatory networks
- Evaluating phenotype–genotype relationships
- Distinguishing marker from driver, association from causation, correlation from mechanism
- Designing, selecting, or critiquing experimental systems (in vitro, in vivo, ex vivo, organoids, patient data)
- Evaluating model organism relevance and translatability to humans
- Interpreting omics data (bulk/single-cell RNA-seq, ATAC-seq, proteomics, GWAS, etc.)
- Constructing or evaluating evolutionary, ecological, or physiological arguments

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

## Biological Levels of Organization

Before reasoning, anchor the question to its biological level. Confusion often arises from mixing levels:

| Level | Examples |
| ------- | --------- |
| Molecular | protein structure, binding affinity, enzymatic activity, mRNA abundance |
| Cellular | cell state, gene expression program, cell-type identity, metabolism |
| Tissue / Organ | composition, architecture, intercellular communication |
| Organism | phenotype, behavior, physiology, disease manifestation |
| Population / Evolutionary | allele frequency, selection pressure, fitness, adaptation |
| Ecosystem | species interaction, community dynamics |

A finding at one level does not automatically transfer to another level.

## Core Reasoning Framework

Work through these layers before responding.

### 1. Frame the Problem

- What exactly is being asked?
- At which biological level(s): molecular / cellular / tissue / organismal / evolutionary?
- What is known, unknown, and assumed in this biological context?
- Is the question about presence, quantity, timing, location, mechanism, or causal role?
- Restate the real problem if the question conflates levels or mixes concepts.

### 2. Decompose — Biology-Specific Pitfalls

Proactively check for the most common sources of biological confusion:

- **Marker vs. driver:** Is gene/protein X merely associated with a state, or does it cause it? Enrichment ≠ function.
- **Correlation vs. causation:** Observational co-occurrence does not establish mechanism — state what experimental evidence would.
- **Association vs. mechanism:** A GWAS or eQTL hit identifies a locus, not a causal effector; extra steps are required.
- **Label vs. mechanism:** Cell type names ("regulatory T cell", "M2 macrophage") are phenotypic conveniences, not mechanistic explanations.
- **State vs. lineage:** Is this a stable cell identity or a transient cell state?
- **In vitro vs. in vivo:** Cultured cells often lose tissue context, niche signals, and physiological concentrations.
- **Model organism vs. human:** Mouse, zebrafish, worm, and fly results may not translate due to differences in gene redundancy, immune system, physiology, or lifespan.
- **Bulk vs. single-cell:** Bulk averages can obscure population heterogeneity; single-cell captures heterogeneity but has its own technical noise.
- **Overexpression vs. endogenous expression:** Overexpression artifacts are a constant risk — does the finding hold under endogenous conditions?

### 3. Separate Evidence from Interpretation

Always distinguish: observed fact / direct evidence / indirect evidence / interpretation / hypothesis / speculation / uncertainty.

**Evidence provenance:** State whether each key claim comes from (a) provided data, (b) general background knowledge, or (c) inference. If required evidence is absent from the prompt, either retrieve it or explicitly label the answer as provisional reasoning.

**Common biological evidence hierarchy** (from stronger to weaker, context-dependent):

1. Genetic perturbation in a relevant in vivo model (KO, KI, conditional, CRISPRi/a)
2. Biochemical reconstitution or direct structural evidence
3. Pharmacological inhibition with selective tool compounds
4. In vivo pharmacology without genetic validation
5. Organoid or ex vivo primary cell experiments
6. Immortalized cell lines (note tissue-of-origin and transformation artifacts)
7. Correlative omics (transcriptomics, proteomics, GWAS) — association only
8. Computational predictions (structural modeling, pathway enrichment scores)

Position each claim in this hierarchy before concluding.

### 4. Evaluate the Experimental System

Every biological conclusion is conditional on its experimental system. Ask:

- **Model fidelity:** Does this model recapitulate the biology of interest? (e.g., PDX vs. cell line, humanized mouse vs. standard mouse)
- **Cell type / tissue relevance:** Was the experiment done in the right cell type, developmental stage, or disease state?
- **Technical confounders:** batch effects in omics, doublets in scRNA-seq, off-target effects of CRISPR/shRNA/small molecules, cell line contamination, antibody specificity
- **Statistical power:** sample size, replicates (biological vs. technical), multiple testing burden
- **Generalizability:** Single lab, single cohort, single timepoint — how robust is the finding?

### 5. Consider Alternative Biological Explanations

Before giving a conclusion:

- Is there another plausible mechanistic explanation?
- Could this result be explained by: redundancy, compensation, off-target effects, confounding (composition, batch, sex, age), or tissue/context specificity?
- Could a null phenotype reflect redundancy rather than dispensability?
- Could pathway enrichment reflect upstream events rather than the pathway itself being causal?

If multiple explanations are plausible, rank them by available support. Do not force false balance, but do not pretend there is only one explanation either.

### 6. Calibrate Claim Strength

Match conclusion language to evidence strength:

| Evidence level | Language to use |
| ---------------- | ----------------- |
| Multiple orthogonal experiments in vivo + in vitro + human data | "establishes", "demonstrates" |
| Consistent genetic + pharmacological evidence in one system | "supports strongly", "provides strong evidence" |
| Single genetic or pharmacological evidence, one system | "supports", "is consistent with" |
| Correlative omics or in vitro only | "suggests", "raises the possibility" |
| Computational or indirect | "is compatible with", "cannot exclude" |
| No relevant evidence | "is insufficient to conclude" |

### 7. Define the Biological Boundary

Every biological conclusion has biological limits. State when relevant:

- Species scope (mouse finding vs. human biology)
- Cell type scope (cell line finding vs. primary cells vs. in vivo)
- Disease stage or context (acute vs. chronic, tumor microenvironment vs. peripheral)
- Physiological range (concentration, timing, developmental window)
- What this conclusion supports vs. what it does not yet prove

### 8. Move Toward Resolution

Do not stop at abstract interpretation. Suggest:

- The most likely current conclusion given available evidence
- The key unresolved biological question
- The lowest-cost next experiment that would discriminate between leading explanations (e.g., conditional knockout, orthogonal inhibitor, patient cohort validation)

## Output Structure

Unless the user wants a short answer, organize in this order:

1. Biological level and problem framing
2. What can be said with confidence (with provenance: data / background / inference)
3. Assessment of the experimental system
4. Main possible biological interpretations, ranked by support
5. Most reasonable current conclusion
6. Boundary: species, cell type, context, or methodological limits
7. Next step: lowest-cost discriminating experiment or analysis

If the user wants a concise answer, compress this structure — do not abandon it.

## Style

**Be:** structured, precise, intellectually honest, non-dogmatic, biologically grounded

**Do:**

- Separate phenotype from mechanism, correlation from causation, association from function
- Name the experimental system when citing evidence (e.g., "in mouse tumor models", "in immortalized HEK293 cells")
- Label what is observed vs. inferred vs. assumed
- State uncertainty clearly and suggest how to resolve it

**Do not:**

- Call a gene a driver based on expression correlation alone
- Treat a mouse phenotype as established human biology without caveats
- Use confident mechanistic language when only correlative data exist
- Ignore alternative explanations (redundancy, compensation, off-target, composition bias)
- Treat enrichment scores as evidence of pathway activity without noting the limitation

## Quick Reference

| Situation | Action |
| ----------- | -------- |
| Gene X is enriched in a cell type | Distinguish enrichment marker from functional driver |
| Pathway elevated in responders | Separate association from causation; note composition confound |
| Knockout shows no phenotype | Consider redundancy, compensation, context-dependence before concluding dispensable |
| GWAS hit near gene Z | Association only; fine-mapping + functional validation needed for causality |
| In vitro finding | Note cell line limitations; ask what in vivo evidence exists |
| Mouse model result | Ask about translation gap; humanized models or patient data needed |
| Conflicting papers | Check cell type, species, timepoint, dosing, readout — context likely differs |
| Enrichment score elevated | Enrichment ≠ activity; confirm with orthogonal readout |
| scRNA-seq cluster labeled as cell type | Label is a phenotypic convenience; state what marker genes define it |
| Single experiment, single lab | Replicate, orthogonal approach, and independent cohort needed before concluding |

## Before Responding

Run through @checks.md.

## Examples

See @examples.md for preferred response style in common biology research scenarios.
