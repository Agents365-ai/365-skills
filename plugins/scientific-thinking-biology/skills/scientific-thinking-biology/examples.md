# Scientific Thinking — Biology Response Style Examples

## Example 1: Gene as a marker of a cell state

**User:** Is gene X a marker of exhausted T cells?

**Pattern:**
- Clarify that "marker" may mean enrichment marker, defining marker, or functional driver
- State what evidence supports each interpretation
- Explain that expression association alone supports enrichment, not functional importance
- Mention context dependence (tumor vs. chronic infection, human vs. mouse)

**Preferred style:**
"Gene X may qualify as an exhaustion-associated enrichment marker if it is reproducibly enriched in exhausted-like T cells across relevant contexts (from background knowledge). However, enrichment alone does not show that it defines exhaustion or drives the exhausted state — those require functional perturbation (knockdown/knockout and rescue). The claim should be stated as 'enrichment marker' unless: (1) expression is required for exhaustion-defining features, (2) perturbation alters the exhaustion program, and (3) findings hold in more than one model. Context also matters: exhaustion in chronic LCMV infection (mouse) may differ from tumor-infiltrating T cell exhaustion or human HIV settings."

---

## Example 2: Pathway enrichment in responders

**User:** Why is this pathway elevated in responders?

**Pattern:**
- Clarify whether this is descriptive (enrichment) or mechanistic (causation)
- Name the experimental system and its limits
- Offer plausible alternatives ranked by support, including composition confound
- Suggest most informative next step

**Preferred style:**
"The pathway elevation in responders is a correlation (from provided data, bulk RNA-seq). At least three explanations remain plausible: (1) the pathway is biologically active and contributes to response [leading hypothesis if supported by prior functional work]; (2) the pathway elevation reflects a cell-type composition difference — responders may harbor more of the cell type that normally expresses this pathway; (3) the elevation is driven by an upstream event associated with response, not the pathway itself. Before concluding the pathway is mechanistically relevant, the most important step is to check whether the signal persists after correcting for composition (deconvolution or single-cell data). If it does, functional perturbation in a relevant model would be the next step."

---

## Example 3: Knockout null phenotype

**User:** The knockout showed no phenotype. Does gene Y not matter?

**Pattern:**
- Distinguish absence of evidence from evidence of absence
- List biology-specific reasons a null phenotype may not mean no function
- Propose the most informative follow-up considering biological context

**Preferred style:**
"A null phenotype in this context is consistent with gene Y being dispensable under these conditions, but it does not establish that gene Y has no function (from background knowledge). In biology, several mechanisms routinely mask phenotypes: genetic redundancy with a paralog, transcriptional compensation triggered by the knockout itself, context-dependence (the phenotype may require stress, infection, aging, or a specific developmental window), or insufficient sensitivity of the readout in the model used. The most informative next step depends on which alternative is most likely: if redundancy is suspected, test double knockouts; if context-dependence is likely, challenge the animal with the relevant stimulus; if the readout was insufficiently sensitive, try more granular measures (scRNA-seq, functional assays, or aged animals)."

---

## Example 4: Experimental design choice

**User:** Should I use bulk RNA-seq or scRNA-seq to study this?

**Pattern:**
- Clarify what the scientific question requires at which biological level
- Map each design to what it can and cannot answer
- State the leading recommendation and the key assumption it rests on
- Note relevant practical tradeoffs

**Preferred style:**
"The right choice depends on the biological question. If your question is about average gene expression differences across a relatively homogeneous population (e.g., a purified cell type before and after treatment), bulk RNA-seq provides higher sensitivity per gene and better statistical power at lower cost. If the question involves cellular heterogeneity — mixed populations, rare cell states, cell-type composition changes, or cell-state transitions — scRNA-seq is necessary because bulk averaging obscures those differences. The leading recommendation is scRNA-seq if your sample contains mixed or heterogeneous cells, or if you don't yet know the composition. The key assumption is that you have enough cells and sufficient depth to detect the subpopulations of interest; if budget or cell number is limited, a tiered approach (bulk first, single-cell on a subset) is worth considering."

---

## Example 5: GWAS hit and causal inference

**User:** This GWAS hit implicates protein Z as a driver of disease risk.

**Pattern:**
- Separate GWAS association from causal inference
- List the steps required to move from locus to causal effector
- State clearly what current evidence supports and what it does not

**Preferred style:**
"A GWAS hit shows that a variant near the protein Z locus is statistically associated with disease risk at the population level (from provided data). This supports that the locus is involved, but does not establish protein Z as the causal effector — several steps are required to make that move: (1) fine-mapping to identify the functional variant(s) within the locus; (2) eQTL or pQTL analysis to link the variant to protein Z expression or function; (3) Mendelian randomization to test causal directionality; (4) functional perturbation in a relevant cell type or animal model. Until those steps are taken, the correct statement is 'the protein Z locus is associated with disease risk'; the 'driver' claim requires additional evidence. It is also possible the causal gene in the locus is not protein Z itself but a neighboring gene in LD."

---

## Example 6: Reconciling conflicting papers

**User:** Paper A found pathway X is activated; paper B found it is suppressed. Which is right?

**Pattern:**
- Do not assume one paper is wrong
- Systematically identify experimental differences that could explain the conflict
- Propose a resolution strategy

**Preferred style:**
"Before concluding one paper is wrong, examine whether the experimental differences could legitimately produce opposite results: different cell types or tissues (pathway X may be activated in epithelial cells but suppressed in immune cells), different timepoints (transient activation followed by suppression is common in signaling), different disease stages, different species or strains, different stimuli or doses, different readout methods measuring different nodes of the pathway, or different genetic backgrounds. The most productive next step is to map these variables across both papers and identify the most likely source of the discrepancy. If all major variables appear identical, a direct head-to-head comparison in the same controlled system — with both labs' reagents — is the only way to resolve a genuine contradiction."

---

## Example 7: In vitro finding and translatability

**User:** We showed that compound X kills tumor cells in culture. Can we move forward with this?

**Pattern:**
- Name what in vitro evidence does and does not establish
- List the biological gaps between cell culture and in vivo efficacy
- Recommend the next stage of validation without being dismissive

**Preferred style:**
"The in vitro result shows that compound X has cytotoxic or growth-inhibitory activity in cultured tumor cells under these conditions (from provided data). This is a necessary first step, but in vitro results frequently fail to predict in vivo efficacy for well-understood reasons: cultured cells lack the tumor microenvironment (stromal, immune, vascular components), pharmacokinetics and bioavailability are not captured, concentration in culture may not be achievable in vivo, and cell lines may carry genetic alterations that sensitize them atypically. Before moving forward, the minimum next steps are: (1) confirm activity in more representative models (patient-derived organoids or PDX if feasible); (2) assess selectivity against normal cells; (3) test in vivo with pharmacokinetically informed dosing. If those hurdles are cleared, the compound has a meaningful case for further development."

---

## Example 8: Single-cell cluster interpretation

**User:** I see a cluster in my scRNA-seq data that expresses Foxp3 and Il2ra. Is this regulatory T cells?

**Pattern:**
- Distinguish marker-based labeling from validated cell identity
- List what additional evidence would strengthen the annotation
- Note potential confounders specific to scRNA-seq

**Preferred style:**
"A cluster expressing Foxp3 and Il2ra (CD25) is consistent with regulatory T cells — these are canonical Treg markers. However, in scRNA-seq, cluster labels based on marker gene expression are phenotypic annotations, not validated identities. Foxp3 can be transiently upregulated in activated non-Treg T cells, and Il2ra is also expressed on recently activated effector T cells. To strengthen the annotation: (1) check for the broader Treg gene signature (Ctla4, Ikzf2/Helios, Entpd1/CD39, Tnfrsf18/GITR) rather than two markers alone; (2) assess the cluster in a reference-based annotation tool (e.g., SingleR with a validated Treg reference); (3) if possible, validate with protein-level co-staining (FACS or CITE-seq). Also check for doublet contamination if the cluster has an unusually broad or mixed profile."

---

## Example 9: Mouse model to human biology

**User:** This pathway is essential in mouse models of this disease. Does it work the same way in humans?

**Pattern:**
- Acknowledge the mouse evidence
- Enumerate known translation gaps for this type of biology
- Suggest what human evidence would be needed

**Preferred style:**
"Mouse model evidence establishes that this pathway is necessary for disease progression in that experimental system (from provided data/background knowledge). However, translation to human biology requires caution — mouse and human biology differ in ways that often matter: immune system composition and regulation differ substantially (e.g., mouse NK cells, neutrophil proportions, cytokine biology); some pathways are redundant in humans but essential in mice (or vice versa); disease kinetics, organ architecture, and metabolic rates differ. To evaluate whether the same pathway is operative in humans, look for: (1) genetic evidence in human GWAS or Mendelian disease linking this pathway to disease; (2) expression or activity differences in human patient samples vs. controls; (3) ex vivo functional evidence in primary human cells; (4) clinical trial data with a pathway inhibitor. Mouse results justify the hypothesis; they are not sufficient by themselves to confirm human relevance."

---

## Example 10: Evolutionary argument in biology

**User:** Gene W is conserved across vertebrates — does that mean it's essential?

**Pattern:**
- Clarify what evolutionary conservation implies and does not imply
- Distinguish sequence conservation from functional conservation
- Note that essentiality may be context-dependent

**Preferred style:**
"Sequence conservation across vertebrates is consistent with purifying selection and suggests that the gene has been maintained because mutations are costly — this is evidence of functional importance, not proof of strict essentiality (from background knowledge). Several caveats apply: (1) essentiality depends on context — some highly conserved genes have subtle or conditional phenotypes when knocked out; (2) conservation at the sequence level does not guarantee conservation of function — a conserved gene may serve different roles in different organisms; (3) pleiotropy may constrain a gene's evolution even if its role in any specific process is not essential. The strongest evidence for essentiality is a severe loss-of-function phenotype across multiple genetic perturbations and species. Conservation raises the prior probability that perturbation will matter — it is a strong motivation to test, not a substitute for testing."
