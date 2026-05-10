# Report Templates

Five archetypes. Pick one in Phase 0 based on user intent. Each template lives in `assets/templates/<archetype>.md`. This file explains *which* to choose and *why*.

## Decision tree

```
Is the user's question about a single narrow effect with many studies?
  ├── yes ─> systematic_review
  └── no ─>
     │
     Are they asking "what has been studied in this area"?
       ├── yes ─> scoping_review
       └── no ─>
          │
          Is it "X vs Y, which is better/different"?
            ├── yes ─> comparative_analysis
            └── no ─>
               │
               Is the output going into a grant or proposal?
                 ├── yes ─> grant_background
                 └── no ─> literature_review (default)
```

## Archetype profiles

### literature_review (default)

**Use when:** the user wants to understand what's known about a topic, with synthesis and gaps.

**Structure:**
1. Executive summary (3-5 bullets)
2. Background and definitions
3. Thematic sections (one per Phase 5 theme)
4. Synthesis (what we collectively know)
5. Open questions and gaps
6. Methodology appendix (search, ranking, self-critique findings)
7. Bibliography

**Citation style:** narrative, with `[^id]` anchors after each non-trivial claim.

### systematic_review

**Use when:** the question is narrow, many studies exist, and the user needs rigor (PRISMA-lite). Common in medicine, psych, education.

**Structure:**
1. Background and rationale
2. Question (PICO)
3. Methods (search strategy, inclusion/exclusion, risk of bias)
4. PRISMA-lite flow diagram (descriptive, not the formal one)
5. Extraction table (one row per included study)
6. Synthesis (narrative; meta-analysis only if numerical)
7. Quality of evidence (GRADE-style)
8. Conclusions
9. Bibliography

**Citation style:** dense, with extraction-table cross-references.

### scoping_review

**Use when:** the user wants to map a field — what topics, what methods, what populations have been studied. Breadth over depth.

**Structure:**
1. Background and rationale
2. Scope question
3. Methods (broad search; minimal exclusion)
4. Coverage map (matrix of subtopic × method)
5. Methods inventory
6. Population/setting inventory
7. Research gap (what hasn't been studied)
8. Recommendations for future work
9. Bibliography

**Citation style:** more enumerative than narrative. Tables dominate prose.

### comparative_analysis

**Use when:** "X vs Y" — methods, models, frameworks, treatments, technologies.

**Structure:**
1. Executive summary with verdict
2. What's being compared (X and Y, scope)
3. Axes of comparison (each with subsection)
4. Per-axis verdict
5. Overall recommendation with caveats
6. When the verdict flips (edge cases)
7. Bibliography

**Citation style:** every comparison cell needs an anchor. Side-by-side tables are standard.

### grant_background

**Use when:** the output is the "Background and Significance" or "Prior work" section of a research proposal.

**Structure:**
1. The problem (why it matters, who is affected, scale)
2. What is known (succinct synthesis with anchors)
3. What is missing (the gap — this becomes the proposal's hook)
4. Why our approach is positioned to fill it (one-paragraph segue)
5. Bibliography

**Citation style:** narrative-first, citation-supporting. Persuasive prose with sources, not a literature dump.

## Cross-cutting requirements (all archetypes)

Every report:

- Has a methodology appendix listing the queries run, sources consulted, ranking weights, and dedupe stats. Pull from `state.queries` and `state.ranking`.
- Has a self-critique appendix copied verbatim from `state.self_critique.appendix`.
- Includes preprint flags inline (`[^id, preprint]`).
- Resolves every `[^id]` anchor against the bibliography. The host LLM is responsible for this check during Phase 7 — the export script emits entries for `state.papers`, but does not scan the report body for anchors.
- Saves as `reports/<slug>_<YYYYMMDD>.md` and writes the path back to `state.report_path`.
